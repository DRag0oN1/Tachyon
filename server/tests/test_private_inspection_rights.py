from copy import deepcopy

import pytest

from fixture_support import load_json, save_json
from tachyon.cad.catalog import Catalog
from tachyon.errors import TachyonError
from tachyon.models import Operation


def policy(workspace):
    rights = load_json(workspace.rights_path)
    for permission in rights["records"][0]["operations"].values():
        permission["basis"] = "terms_interpretation"
        permission["useScope"] = "private_local_inspection"
    save_json(workspace.rights_path, rights)
    return workspace.catalog().policy


def test_private_inspection_is_not_coupled_to_redistribution(calibration_workspace):
    p = policy(calibration_workspace)
    p.require(calibration_workspace.component.source_sha256,
              [Operation.acquisition_storage, Operation.conversion, Operation.loopback_display])


@pytest.mark.parametrize("operation", [Operation.assembly_placement, Operation.part_modification,
    Operation.lan_display, Operation.public_depiction, Operation.original_redistribution,
    Operation.mesh_redistribution, Operation.public_hosting])
def test_private_terms_interpretation_cannot_qualify_other_operations(calibration_workspace, operation):
    w = calibration_workspace
    p = policy(w)
    # Even a mistakenly marked qualified label cannot extend the bounded scope.
    original = deepcopy(p.records[w.component.source_sha256].operations[Operation.conversion])
    p.records[w.component.source_sha256].operations[operation] = original
    with pytest.raises(TachyonError) as caught:
        p.require(w.component.source_sha256, [operation])
    assert caught.value.code == "RIGHTS_SCOPE_MISMATCH"


def test_interpretation_requires_explicit_private_scope(calibration_workspace):
    w = calibration_workspace
    p = policy(w)
    p.records[w.component.source_sha256].operations[Operation.conversion].use_scope = None
    with pytest.raises(TachyonError) as caught:
        p.require(w.component.source_sha256, [Operation.conversion])
    assert caught.value.code == "RIGHTS_SCOPE_MISMATCH"
