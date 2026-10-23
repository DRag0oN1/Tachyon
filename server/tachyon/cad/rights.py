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
            if not all((decision.rightsholder.strip(), decision.basis,
                        decision.reviewed_by.strip(), decision.reviewed_on,
                        decision.evidence_path, decision.evidence_sha256)):
                raise TachyonError("RIGHTS_EVIDENCE_MISSING", f"Reviewed evidence is required for {operation.value}")
            if decision.reviewed_on > date.today() or (decision.expires_on and decision.expires_on < date.today()):
                raise TachyonError("RIGHTS_EVIDENCE_EXPIRED", f"Permission is not current for {operation.value}")
            evidence = self.settings.local_path(decision.evidence_path)
            if sha256_file(evidence) != decision.evidence_sha256:
                raise TachyonError("RIGHTS_EVIDENCE_CHANGED", "Permission evidence no longer matches its reviewed identity")
        return record
