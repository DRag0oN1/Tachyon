"""Native measurement uses original authored calibration geometry, never VEX."""
import numpy as np
import pytest

from fixture_support import digest, load_json, save_json
from tachyon.cad.qualification import measure_source
from tachyon.errors import TachyonError


def test_measurement_preserves_source_identity_native_hierarchy_and_mm(calibration_workspace):
    w = calibration_workspace
    c = w.component
    source = w.settings.source_path(c.source_path)
    before = digest(source)
    result = measure_source(w.settings, str(source), str(w.rights_path))
    np.testing.assert_allclose(result["boundsMm"]["min"], c.expected_bounds_mm.min, atol=1e-7)
    np.testing.assert_allclose(result["boundsMm"]["max"], c.expected_bounds_mm.max, atol=1e-7)
    assert result["sourceSha256"] == before == digest(source)
    assert result["solidCount"] == 2
    nodes = result["nativeHierarchy"]
    assert len(nodes) >= 4
    assert len({n["id"] for n in nodes}) == len(nodes)
    assert all(n["parentId"] is None or n["parentId"] in {m["id"] for m in nodes} for n in nodes)
    assert any(any(abs(n["matrixMmZUp"][i]) > 0 for i in (12, 13, 14)) for n in nodes)
    assert all(len(n["matrixMmZUp"]) == 16 for n in nodes)
    assert result["convertedMesh"] is False and result["completeRobot"] is False
    assert result["geometryIncluded"] is False
    assert not (w.settings.data_dir / "meshes").exists()


@pytest.mark.parametrize("operation", ["acquisition_storage", "conversion"])
def test_unverified_operation_blocks_before_native_import(calibration_workspace, monkeypatch, operation):
    w = calibration_workspace
    rights = load_json(w.rights_path)
    rights["records"][0]["operations"][operation]["status"] = "unverified"
    save_json(w.rights_path, rights)
    from tachyon.cad import native
    monkeypatch.setattr(native, "import_source", lambda *_: pytest.fail("Unverified source reached native conversion"))
    with pytest.raises(TachyonError, match="Permission is unresolved"):
        measure_source(w.settings, w.component.source_path, str(w.rights_path))
    assert not (w.settings.data_dir / "meshes").exists()


def test_changed_source_cannot_use_previous_hash_grant(calibration_workspace):
    w = calibration_workspace
    source = w.settings.source_path(w.component.source_path)
    with source.open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(TachyonError, match="No reviewed rights record"):
        measure_source(w.settings, str(source), str(w.rights_path))
