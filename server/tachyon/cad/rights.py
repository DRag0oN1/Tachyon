from __future__ import annotations

import hashlib
from datetime import date

from ..config import Settings
from ..errors import TachyonError
from ..models import Operation, RightsManifest


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class RightsPolicy:
    def __init__(self, settings: Settings, manifest: RightsManifest):
        self.settings = settings
        self.records = {r.source_sha256: r for r in manifest.records}
        if len(self.records) != len(manifest.records):
            raise TachyonError("INVALID_RIGHTS_RECORD", "Duplicate source rights record")

    def require(self, source_hash: str, operations: list[Operation]):
        record = self.records.get(source_hash)
        if not record:
            raise TachyonError("SOURCE_NOT_QUALIFIED", "No reviewed rights record exists for this source")
        for operation in operations:
            decision = record.operations.get(operation)
            if not decision or decision.status != "qualified":
                raise TachyonError("SOURCE_NOT_QUALIFIED", f"Permission is unresolved for {operation.value}")
            if decision.basis == "terms_interpretation" and (
                decision.use_scope != "private_local_inspection" or operation not in (
                    Operation.acquisition_storage, Operation.conversion, Operation.loopback_display)):
                raise TachyonError("RIGHTS_SCOPE_MISMATCH", "A private inspection interpretation cannot authorize assembly edits, LAN transmission or public distribution")
            if decision.basis == "user_attestation":
                # Software acceptance of a recorded user statement, not
                # verification of a manufacturer license or rightsholder grant.
                if decision.use_scope != "private_local_assembly" or operation not in (
                        Operation.acquisition_storage, Operation.conversion,
                        Operation.assembly_placement, Operation.loopback_display):
                    raise TachyonError("RIGHTS_SCOPE_MISMATCH", "A user attestation is limited to private local assembly placement and inspection")
                if not record.attribution.strip():
                    raise TachyonError("RIGHTS_EVIDENCE_MISSING", "Source attribution is required for a user attestation")
            if not all((decision.rightsholder.strip(), decision.basis,
                        decision.reviewed_by.strip(), decision.reviewed_on,
                        decision.evidence_path, decision.evidence_sha256)):
                raise TachyonError("RIGHTS_EVIDENCE_MISSING", f"Reviewed evidence is required for {operation.value}")
            if decision.reviewed_on > date.today() or (decision.expires_on and decision.expires_on < date.today()):
                raise TachyonError("RIGHTS_EVIDENCE_EXPIRED", f"Permission is not current for {operation.value}")
            evidence = self.settings.rights_path(decision.evidence_path)
            if sha256_file(evidence) != decision.evidence_sha256:
                raise TachyonError("RIGHTS_EVIDENCE_CHANGED", "Permission evidence no longer matches its reviewed identity")
        return record

    def operation_status(self, source_hash: str):
        """Recheck evidence per operation; never trust a cached qualified label."""
        result = {}
        record = self.records.get(source_hash)
        for operation in Operation:
            permission = record.operations.get(operation) if record else None
            if permission and permission.status == "disallowed":
                result[operation.value] = {"status": "disallowed", "code": "SOURCE_OPERATION_DISALLOWED"}
                continue
            try:
                self.require(source_hash, [operation])
                result[operation.value] = {"status": "qualified", "code": None}
            except TachyonError as error:
                result[operation.value] = {"status": "unverified", "code": error.code}
            except OSError:
                result[operation.value] = {"status": "unverified", "code": "RIGHTS_EVIDENCE_UNREADABLE"}
        return result
