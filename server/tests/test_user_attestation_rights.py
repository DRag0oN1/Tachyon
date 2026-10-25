"""Software acceptance of fixture user statements; no manufacturer grant inferred.

Only disposable fixture records are constructed. Real user records stay intact.
"""
from copy import deepcopy
from datetime import date, timedelta

import pytest

from tachyon.cad.rights import RightsPolicy
from tachyon.errors import TachyonError
from tachyon.models import Operation, Permission, RightsManifest


ALLOWED = (Operation.acquisition_storage, Operation.conversion,
           Operation.assembly_placement, Operation.loopback_display)
EXCLUDED = tuple(operation for operation in Operation if operation not in ALLOWED)


@pytest.fixture
def attestation_policy(calibration_workspace):
    workspace = calibration_workspace
    original = workspace.catalog().policy.records[workspace.component.source_sha256]
    record = original.model_copy(deep=True)
    for decision in record.operations.values():
        decision.basis = "user_attestation"
        decision.use_scope = "private_local_assembly"
    manifest = RightsManifest.model_validate_json(RightsManifest(records=[record]).model_dump_json())
    return RightsPolicy(workspace.settings, manifest)


def reject(code, policy, source_hash, operation):
    with pytest.raises(TachyonError) as caught:
        policy.require(source_hash, [operation])
    assert caught.value.code == code


@pytest.mark.parametrize("operation", ALLOWED)
def test_attestation_accepts_only_recorded_private_local_operations(calibration_workspace, attestation_policy, operation):
    source_hash = calibration_workspace.component.source_sha256
    before = attestation_policy.records[source_hash].model_dump()
    record = attestation_policy.require(source_hash, [operation])
    assert record.operations[operation].basis == "user_attestation"
    assert record.operations[operation].use_scope == "private_local_assembly"
    assert record.model_dump() == before


@pytest.mark.parametrize("operation", EXCLUDED)
def test_qualified_attestation_cannot_extend_to_modification_or_sharing(calibration_workspace, attestation_policy, operation):
    source_hash = calibration_workspace.component.source_sha256
    record = attestation_policy.records[source_hash]
    record.operations[operation] = deepcopy(record.operations[Operation.conversion])
    reject("RIGHTS_SCOPE_MISMATCH", attestation_policy, source_hash, operation)
    assert attestation_policy.operation_status(source_hash)[operation.value] == {
        "status": "unverified", "code": "RIGHTS_SCOPE_MISMATCH"}


@pytest.mark.parametrize("scope", [None, "private_local_inspection"])
def test_attestation_requires_explicit_assembly_scope(calibration_workspace, attestation_policy, scope):
    source_hash = calibration_workspace.component.source_sha256
    attestation_policy.records[source_hash].operations[Operation.conversion].use_scope = scope
    reject("RIGHTS_SCOPE_MISMATCH", attestation_policy, source_hash, Operation.conversion)


@pytest.mark.parametrize("field,value", [
    ("rightsholder", " "), ("reviewed_by", ""), ("reviewed_on", None),
    ("evidence_path", ""), ("evidence_sha256", ""),
])
def test_attestation_retains_required_evidence_checks(calibration_workspace, attestation_policy, field, value):
    source_hash = calibration_workspace.component.source_sha256
    setattr(attestation_policy.records[source_hash].operations[Operation.conversion], field, value)
    reject("RIGHTS_EVIDENCE_MISSING", attestation_policy, source_hash, Operation.conversion)


@pytest.mark.parametrize("attribution", ["", "   "])
def test_attestation_requires_source_attribution(calibration_workspace, attestation_policy, attribution):
    source_hash = calibration_workspace.component.source_sha256
    attestation_policy.records[source_hash].attribution = attribution
    reject("RIGHTS_EVIDENCE_MISSING", attestation_policy, source_hash, Operation.assembly_placement)


@pytest.mark.parametrize("field,value", [
    ("reviewed_on", date.today() + timedelta(days=1)),
    ("expires_on", date.today() - timedelta(days=1)),
])
def test_attestation_rejects_future_or_expired_reviews(calibration_workspace, attestation_policy, field, value):
    source_hash = calibration_workspace.component.source_sha256
    setattr(attestation_policy.records[source_hash].operations[Operation.conversion], field, value)
    reject("RIGHTS_EVIDENCE_EXPIRED", attestation_policy, source_hash, Operation.conversion)


def test_attestation_rechecks_evidence_hash_and_source_identity(calibration_workspace, attestation_policy):
    source_hash = calibration_workspace.component.source_sha256
    reject("SOURCE_NOT_QUALIFIED", attestation_policy, "1" * 64, Operation.conversion)
    calibration_workspace.evidence_path.write_text("A changed fixture statement is not the recorded evidence.\n")
    reject("RIGHTS_EVIDENCE_CHANGED", attestation_policy, source_hash, Operation.assembly_placement)


@pytest.mark.parametrize("status", ["unverified", "disallowed"])
def test_attestation_does_not_promote_unaccepted_records(calibration_workspace, attestation_policy, status):
    source_hash = calibration_workspace.component.source_sha256
    attestation_policy.records[source_hash].operations[Operation.assembly_placement].status = status
    reject("SOURCE_NOT_QUALIFIED", attestation_policy, source_hash, Operation.assembly_placement)
    del attestation_policy.records[source_hash].operations[Operation.conversion]
    reject("SOURCE_NOT_QUALIFIED", attestation_policy, source_hash, Operation.conversion)


def test_new_scope_does_not_expand_terms_interpretation_or_rewrite_old_permissions(calibration_workspace):
    workspace = calibration_workspace
    policy = workspace.catalog().policy
    record = policy.records[workspace.component.source_sha256]
    before = record.model_dump()
    policy.require(workspace.component.source_sha256, list(ALLOWED))
    assert record.model_dump() == before
    for operation in ALLOWED:
        record.operations[operation] = Permission.model_validate({
            **record.operations[operation].json_data(),
            "basis": "terms_interpretation", "useScope": "private_local_assembly",
        })
        reject("RIGHTS_SCOPE_MISMATCH", policy, workspace.component.source_sha256, operation)
