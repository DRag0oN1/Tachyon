"""Slice 1 contracts using original non-VEX calibration CAD only.

Checklist command: python -m pytest server/tests/test_catalog.py server/tests/test_asset_api.py
Native CadQuery/OCP is required: these are real STEP-to-GLB tests, not mocks of
successful conversion. Passing them never qualifies authentic VEX acceptance.
"""
from copy import deepcopy
from datetime import date, timedelta
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from fixture_support import (
    BROWSER_BOUNDS_M, FIXTURE_ID, LOCAL_OPERATIONS, MEMBER_NAMES, SOURCE_BOUNDS_MM,
    author_source_variant, create_calibration_workspace, digest, load_json, save_json,
)
from glb_support import change_glb_document, read_glb
from tachyon.cad.catalog import Catalog
from tachyon.cad.prepare import prepare_component
from tachyon.cad.rights import RightsPolicy
from tachyon.config import Settings
from tachyon.errors import TachyonError
from tachyon.models import Operation, RightsManifest


def assert_error(code, action):
    with pytest.raises(TachyonError) as caught:
        action()
    assert caught.value.code == code
    assert caught.value.public()["retryable"] is False


def forbid_native_import(monkeypatch):
    import cadquery as cq
    from tachyon.cad import native

    def forbidden(*args, **kwargs):
        pytest.fail("Disqualified input reached the native STEP importer")

    monkeypatch.setattr(cq.Assembly, "load", forbidden)
    monkeypatch.setattr(native, "import_source", forbidden)


def assert_no_prepared_output(workspace):
    assert not list(workspace.data_dir.glob("meshes/*.glb"))
    assert not list(workspace.data_dir.glob("catalog/prepared/*.json"))


def test_fixture_has_original_scoped_authorship_and_measured_native_bounds(calibration_workspace):
    import cadquery as cq

    workspace = calibration_workspace
    component = workspace.component
    assert component.geometry_class == "test_fixture"
    assert component.origin_kind == "tachyon_authored"
    assert "non-VEX" in component.name and "test_fixture" in component.name
    assert component.sku is None
    assert digest(workspace.source_path) == component.source_sha256
    assembly = cq.Assembly.load(str(workspace.source_path))
    native = assembly.toCompound()
    bounds = native.BoundingBox()
    np.testing.assert_allclose([bounds.xmin, bounds.ymin, bounds.zmin], SOURCE_BOUNDS_MM["min"], atol=1e-7)
    np.testing.assert_allclose([bounds.xmax, bounds.ymax, bounds.zmax], SOURCE_BOUNDS_MM["max"], atol=1e-7)
    assert len(native.Solids()) == 2 and native.isValid()
    assert MEMBER_NAMES <= {part.name for part in assembly.objects.values()}
    rights = load_json(workspace.rights_path)
    assert len(rights["records"]) == 1
    record = rights["records"][0]
    assert record["sourceSha256"] == component.source_sha256
    assert set(record["operations"]) == set(LOCAL_OPERATIONS)
    for permission in record["operations"].values():
        assert permission["basis"] == "self_authored" and permission["status"] == "qualified"
        assert permission["rightsholder"] and permission["reviewedBy"]
        assert permission["reviewedOn"] == date.today().isoformat()
        assert not Path(permission["evidencePath"]).is_absolute()
        assert permission["evidenceSha256"] == digest(workspace.evidence_path)
    assert component.source_sha256 in workspace.evidence_path.read_text()


def test_register_checks_identity_without_import_or_conversion(calibration_workspace, monkeypatch):
    workspace = calibration_workspace
    before = workspace.source_path.read_bytes()
    forbid_native_import(monkeypatch)
    results = workspace.catalog().register()
    assert results == [{"componentId": FIXTURE_ID, "status": "registered", "converted": False}]
    assert load_json(workspace.data_dir / "catalog/registration.json") == {
        "manifestPath": "catalog/manifest.json", "rightsPath": "catalog/rights.json"}
    assert load_json(workspace.data_dir / "catalog/registration-report.json")["results"] == results
    assert workspace.catalog().manifest.components[0].id == FIXTURE_ID
    assert workspace.source_path.read_bytes() == before
    assert_no_prepared_output(workspace)


@pytest.mark.parametrize("operation", ["acquisition_storage", "conversion"])
@pytest.mark.parametrize("status", [None, "unverified", "disallowed"])
def test_every_operation_requires_qualification_before_native_import(calibration_workspace, monkeypatch, operation, status):
    workspace = calibration_workspace
    rights = load_json(workspace.rights_path)
    if status is None:
        del rights["records"][0]["operations"][operation]
    else:
        rights["records"][0]["operations"][operation]["status"] = status
    save_json(workspace.rights_path, rights)
    forbid_native_import(monkeypatch)
    catalog = workspace.catalog()
    assert_error("SOURCE_NOT_QUALIFIED", lambda: prepare_component(catalog, workspace.component))
    assert catalog.register()[0]["status"] == ("blocked" if operation == "acquisition_storage" else "registered")
    assert_no_prepared_output(workspace)


@pytest.mark.parametrize("field,value", [
    ("rightsholder", " "), ("basis", None), ("reviewedBy", ""),
    ("reviewedOn", None), ("evidencePath", ""), ("evidenceSha256", ""),
])
def test_qualified_label_requires_complete_evidence(calibration_workspace, field, value):
    workspace = calibration_workspace
    workspace.update_permission(**{field: value})
    catalog = workspace.catalog()
    assert_error("RIGHTS_EVIDENCE_MISSING", lambda: catalog.policy.require(workspace.component.source_sha256, [Operation.conversion]))


@pytest.mark.parametrize("field,offset", [("expiresOn", -1), ("reviewedOn", 1)])
def test_expired_and_future_review_dates_block(calibration_workspace, field, offset):
    workspace = calibration_workspace
    workspace.update_permission(**{field: (date.today() + timedelta(days=offset)).isoformat()})
    assert_error("RIGHTS_EVIDENCE_EXPIRED", lambda: workspace.catalog().policy.require(workspace.component.source_sha256, [Operation.conversion]))


def test_permission_expiring_today_is_current(calibration_workspace):
    workspace = calibration_workspace
    workspace.update_permission(expiresOn=date.today().isoformat())
    assert workspace.catalog().policy.require(workspace.component.source_sha256, [Operation.conversion])


def test_evidence_bytes_and_source_identity_are_checked(calibration_workspace):
    workspace = calibration_workspace
    rights = load_json(workspace.rights_path)
    rights["records"][0]["sourceSha256"] = "1" * 64
    save_json(workspace.rights_path, rights)
    assert_error("SOURCE_NOT_QUALIFIED", lambda: workspace.catalog().source(workspace.component))
    rights["records"][0]["sourceSha256"] = workspace.component.source_sha256
    save_json(workspace.rights_path, rights)
    workspace.evidence_path.write_text("Different evidence is not the reviewed authorship evidence.\n")
    assert_error("RIGHTS_EVIDENCE_CHANGED", lambda: workspace.catalog().source(workspace.component))


def test_evidence_path_cannot_escape_private_data(calibration_workspace):
    workspace = calibration_workspace
    outside = workspace.settings.root / "outside-evidence.txt"
    outside.write_bytes(workspace.evidence_path.read_bytes())
    workspace.update_permission(evidencePath="../outside-evidence.txt")
    assert_error("INVALID_LOCAL_PATH", lambda: workspace.catalog().policy.require(workspace.component.source_sha256, [Operation.conversion]))
    (workspace.data_dir / "evidence-link.txt").symlink_to(outside)
    workspace.update_permission(evidencePath="evidence-link.txt")
    assert_error("INVALID_LOCAL_PATH", lambda: workspace.catalog().policy.require(workspace.component.source_sha256, [Operation.conversion]))


def test_duplicate_rights_records_are_ambiguous(calibration_workspace):
    workspace = calibration_workspace
    rights = load_json(workspace.rights_path)
    rights["records"].append(deepcopy(rights["records"][0]))
    assert_error("INVALID_RIGHTS_RECORD", lambda: RightsPolicy(workspace.settings, RightsManifest.model_validate(rights)))


@pytest.mark.parametrize("mutation,code", [
    ("changed_bytes", "SOURCE_HASH_MISMATCH"),
    ("invalid_signature", "INVALID_STEP"),
    ("unsupported_format", "UNSUPPORTED_CAD_FORMAT"),
    ("missing_source", "LOCAL_FILE_MISSING"),
    ("forged_imported_class", "INVALID_GEOMETRY_CLASS"),
    ("path_escape", "INVALID_LOCAL_PATH"),
])
def test_bad_source_is_rejected_before_native_import(calibration_workspace, monkeypatch, mutation, code):
    workspace = calibration_workspace
    if mutation == "changed_bytes":
        workspace.source_path.write_bytes(workspace.source_path.read_bytes() + b"\nchanged\n")
    elif mutation == "invalid_signature":
        workspace.source_path.write_text("not an ISO STEP document")
    elif mutation == "unsupported_format":
        unsupported = workspace.source_path.with_suffix(".f3d")
        unsupported.write_bytes(workspace.source_path.read_bytes())
        workspace.update_component(sourcePath="sources/calibration.f3d")
    elif mutation == "missing_source":
        workspace.source_path.unlink()
    elif mutation == "forged_imported_class":
        workspace.update_component(geometryClass="verified_imported_component")
    else:
        workspace.update_component(sourcePath="../outside.step")
    forbid_native_import(monkeypatch)
    assert_error(code, lambda: prepare_component(workspace.catalog(), workspace.component))
    assert_no_prepared_output(workspace)


@pytest.mark.parametrize("changes", [
    {"sourceSha256": "not-a-sha256"}, {"sourceSha256": "A" * 64},
    {"geometryClass": "authentic_vex"}, {"originKind": "unknown_source"},
    {"expectedBoundsMm": {"min": [1, 0, 0], "max": [0, 0, 0]}},
])
def test_malformed_manifest_and_unsupported_class_fail_closed(calibration_workspace, changes):
    workspace = calibration_workspace
    workspace.update_component(**changes)
    assert_error("INVALID_MANIFEST", workspace.catalog)


def test_settings_rejects_data_outside_root(tmp_path):
    with pytest.raises(ValueError, match="inside the project"):
        Settings(root=tmp_path / "project", data_dir=tmp_path / "outside")


def test_native_prepare_preserves_source_and_real_glb_hierarchy(calibration_workspace):
    workspace = calibration_workspace
    source_before = workspace.source_path.read_bytes()
    catalog = workspace.catalog()
    record = prepare_component(catalog, workspace.component)
    mesh = catalog.asset(record["meshSha256"])
    decoded = read_glb(mesh)
    assert record["geometryClass"] == "test_fixture" and record["originKind"] == "tachyon_authored"
    assert record["solidCount"] == 2
    assert record["completeRobot"] is False and record["conversion"]["displayMeshOnly"] is True
    assert record["conversion"]["tool"] == "CadQuery" and record["conversion"]["version"]
    assert record["conversion"]["maxBoundsErrorM"] < 1e-6
    assert record["ports"] == workspace.component.json_data()["ports"]
    assert workspace.source_path.read_bytes() == source_before
    assert record["sourceSha256"] == digest(workspace.source_path)
    assert record["meshSha256"] == digest(mesh)
    for side in ("min", "max"):
        np.testing.assert_allclose(record["sourceBoundsMm"][side], SOURCE_BOUNDS_MM[side], atol=1e-7)
        np.testing.assert_allclose(record["boundsM"][side], BROWSER_BOUNDS_M[side], atol=1e-7)
        np.testing.assert_allclose(decoded["boundsM"][side], BROWSER_BOUNDS_M[side], atol=1e-7)
    assert decoded["triangleCount"] == 24  # two boxes, six faces, two triangles/face
    nodes = {node["name"]: node for node in decoded["hierarchy"]}
    assert MEMBER_NAMES <= nodes.keys()
    assert nodes["calibration_base"]["hasMesh"] is True
    assert nodes["calibration_offset_block"]["hasMesh"] is True
    assert nodes["calibration_offset_block"]["parentId"] == nodes["calibration_offset_group"]["id"]
    public_nodes = {node["name"]: node for node in record["nativeHierarchy"]}
    for name, node in nodes.items():
        assert public_nodes[name]["parentId"] == node["parentId"]
        np.testing.assert_allclose(np.array(public_nodes[name]["matrix"]).reshape(4, 4, order="F"), node["matrix"], atol=1e-10)
    prepared = catalog.prepared(workspace.component)
    assert prepared["meshSha256"] == record["meshSha256"]
    assert prepared["nativeHierarchy"] == record["nativeHierarchy"]
    assert prepared["declaredUse"] == "loopback_source_inspection"
    assert prepared["qualifiedOperations"] == ["acquisition_storage", "loopback_display"]
    assert catalog.public()["blockers"] == []


@pytest.mark.parametrize("factor", [0.001, 25.4, 1000.0])
def test_prepare_refuses_wrong_source_units(calibration_workspace, factor):
    workspace = calibration_workspace
    workspace.update_component(expectedBoundsMm={side: [value * factor for value in values]
                                               for side, values in SOURCE_BOUNDS_MM.items()})
    assert_error("SOURCE_DIMENSION_MISMATCH", lambda: prepare_component(workspace.catalog(), workspace.component))
    assert_no_prepared_output(workspace)


def test_prepare_rejects_double_unit_conversion_in_actual_glb(calibration_workspace, monkeypatch):
    import cadquery as cq

    original_export = cq.Assembly.export

    def wrong_scale(assembly, path, *args, **kwargs):
        result = original_export(assembly, path, *args, **kwargs)
        if Path(path).suffix == ".glb":
            def change(document):
                root = document["scenes"][document.get("scene", 0)]["nodes"][0]
                node = document["nodes"][root]
                # The real exporter may use a matrix or TRS; scale either form.
                if "matrix" in node:
                    matrix = np.array(node["matrix"]).reshape(4, 4, order="F")
                    scale = np.diag([0.001, 0.001, 0.001, 1])
                    node["matrix"] = (scale @ matrix).flatten(order="F").tolist()
                else:
                    node["scale"] = [value * 0.001 for value in node.get("scale", [1, 1, 1])]
                    node["translation"] = [value * 0.001 for value in node.get("translation", [0, 0, 0])]
            change_glb_document(Path(path), change)
        return result

    monkeypatch.setattr(cq.Assembly, "export", wrong_scale)
    assert_error("MESH_FRAME_MISMATCH", lambda: prepare_component(calibration_workspace.catalog(), calibration_workspace.component))
    assert_no_prepared_output(calibration_workspace)


def test_source_change_during_conversion_never_creates_receipt(calibration_workspace, monkeypatch):
    import cadquery as cq

    workspace = calibration_workspace
    original_export = cq.Assembly.export

    def source_changed(assembly, *args, **kwargs):
        result = original_export(assembly, *args, **kwargs)
        workspace.source_path.write_bytes(workspace.source_path.read_bytes() + b"\nsource changed during export\n")
        return result

    monkeypatch.setattr(cq.Assembly, "export", source_changed)
    assert_error("SOURCE_HASH_MISMATCH", lambda: prepare_component(workspace.catalog(), workspace.component))
    assert not list(workspace.data_dir.glob("catalog/prepared/*.json"))
    assert workspace.catalog().public()["components"] == []


def test_local_preparation_does_not_qualify_lan_or_public_uses(prepared_workspace):
    workspace = prepared_workspace
    catalog = workspace.catalog()
    assert catalog.prepared(workspace.component)["id"] == FIXTURE_ID
    for operation in (Operation.lan_display, Operation.public_depiction, Operation.original_redistribution,
                      Operation.mesh_redistribution, Operation.public_hosting, Operation.part_modification):
        assert_error("SOURCE_NOT_QUALIFIED", lambda: catalog.policy.require(workspace.component.source_sha256, [operation]))
    assert_error("SOURCE_NOT_QUALIFIED", lambda: catalog.prepared(workspace.component, lan=True))


def test_mesh_tampering_is_rejected_even_with_existing_receipt(prepared_workspace):
    workspace = prepared_workspace
    catalog = workspace.catalog()
    record = catalog.prepared(workspace.component)
    mesh = catalog.asset(record["meshSha256"])
    mesh.write_bytes(mesh.read_bytes() + b"tampered mesh")
    assert_error("MESH_HASH_MISMATCH", lambda: catalog.prepared(workspace.component))
    assert_error("MESH_HASH_MISMATCH", lambda: catalog.asset(record["meshSha256"]))
    assert catalog.public()["components"] == []


@pytest.mark.parametrize("field,value", [
    ("geometryClass", "verified_imported_component"), ("originKind", "manufacturer_cad"),
    ("name", "Claimed authentic part"), ("sku", "invented-part"),
    ("sourceSha256", "1" * 64), ("catalogFingerprint", "1" * 64),
])
def test_receipt_cannot_change_source_or_fixture_classification(prepared_workspace, field, value):
    workspace = prepared_workspace
    catalog = workspace.catalog()
    receipt = catalog.receipt_path(workspace.component)
    record = load_json(receipt)
    record[field] = value
    save_json(receipt, record)
    assert_error("STALE_MESH", lambda: catalog.prepared(workspace.component))
    assert catalog.public()["components"] == []


@pytest.mark.parametrize("contents", ["not json", '{"meshSha256":"../outside"}', "{}", "null", "[]", "42", '{"meshSha256":null}'])
def test_invalid_receipt_fails_closed(prepared_workspace, contents):
    catalog = prepared_workspace.catalog()
    catalog.receipt_path(prepared_workspace.component).write_text(contents)
    assert_error("INVALID_RECEIPT", lambda: catalog.prepared(prepared_workspace.component))
    state = catalog.public()
    assert state["components"] == []
    assert state["blockers"][0]["code"] == "INVALID_RECEIPT"


def test_changed_catalog_requires_new_preparation(prepared_workspace):
    workspace = prepared_workspace
    old_fingerprint = workspace.catalog().fingerprint(workspace.component)
    workspace.update_component(name="Renamed test_fixture (non-VEX)")
    catalog = workspace.catalog()
    assert catalog.fingerprint(workspace.component) != old_fingerprint
    assert_error("MESH_NOT_PREPARED", lambda: catalog.prepared(workspace.component))


def test_generator_refuses_to_replace_existing_private_data(calibration_workspace):
    workspace = calibration_workspace
    before = {path.relative_to(workspace.data_dir): path.read_bytes()
              for path in workspace.data_dir.rglob("*") if path.is_file()}
    with pytest.raises(FileExistsError):
        create_calibration_workspace(workspace.settings.root, workspace.data_dir)
    assert before == {path.relative_to(workspace.data_dir): path.read_bytes()
                      for path in workspace.data_dir.rglob("*") if path.is_file()}


def test_registration_requires_storage_but_never_infers_other_operations(calibration_workspace, monkeypatch):
    workspace = calibration_workspace
    rights = load_json(workspace.rights_path)
    rights["records"][0]["operations"] = {
        "acquisition_storage": rights["records"][0]["operations"]["acquisition_storage"]}
    save_json(workspace.rights_path, rights)
    forbid_native_import(monkeypatch)
    catalog = workspace.catalog()
    assert catalog.register()[0]["status"] == "registered"
    assert_error("SOURCE_NOT_QUALIFIED", lambda: prepare_component(catalog, workspace.component))
    for operation in (Operation.conversion, Operation.assembly_placement, Operation.loopback_display, Operation.lan_display):
        assert_error("SOURCE_NOT_QUALIFIED", lambda: catalog.policy.require(workspace.component.source_sha256, [operation]))
    assert_no_prepared_output(workspace)


def test_conversion_needs_no_display_or_assembly_permission(calibration_workspace):
    workspace = calibration_workspace
    rights = load_json(workspace.rights_path)
    for operation in ("loopback_display", "assembly_placement"):
        del rights["records"][0]["operations"][operation]
    save_json(workspace.rights_path, rights)
    catalog = workspace.catalog()
    record = prepare_component(catalog, workspace.component)
    assert record["geometryClass"] == "test_fixture" and record["completeRobot"] is False
    assert digest(workspace.data_dir / "meshes" / (record["meshSha256"] + ".glb")) == record["meshSha256"]
    assert_error("SOURCE_NOT_QUALIFIED", lambda: catalog.prepared(workspace.component))
    assert_error("SOURCE_NOT_QUALIFIED", lambda: catalog.asset(record["meshSha256"]))


def test_display_uses_its_scope_without_requiring_conversion_or_assembly(prepared_workspace):
    workspace = prepared_workspace
    rights = load_json(workspace.rights_path)
    for operation in ("conversion", "assembly_placement"):
        rights["records"][0]["operations"][operation]["status"] = "disallowed"
    save_json(workspace.rights_path, rights)
    catalog = workspace.catalog()
    record = catalog.prepared(workspace.component)
    assert catalog.asset(record["meshSha256"]).is_file()
    assert_error("SOURCE_NOT_QUALIFIED", lambda: prepare_component(catalog, workspace.component))
    assert_error("SOURCE_NOT_QUALIFIED", lambda: catalog.policy.require(workspace.component.source_sha256, [Operation.assembly_placement]))


def test_explicit_rights_override_is_not_lost_to_saved_registration(calibration_workspace):
    workspace = calibration_workspace
    workspace.catalog().register()
    rights = load_json(workspace.rights_path)
    rights["records"][0]["operations"]["acquisition_storage"]["status"] = "disallowed"
    override = workspace.data_dir / "catalog/override-rights.json"
    save_json(override, rights)
    catalog = Catalog(workspace.settings, rights_path=override)
    assert catalog.rights_path == override
    assert catalog.register()[0]["status"] == "blocked"
    assert catalog.register()[0]["code"] == "SOURCE_NOT_QUALIFIED"


@pytest.mark.parametrize("extension", ["step", "stp", "STEP", "STP"])
def test_native_assembly_accepts_supported_step_extensions(calibration_workspace, extension):
    workspace = calibration_workspace
    alternate = workspace.source_path.with_name(f"calibration-alias.{extension}")
    alternate.write_bytes(workspace.source_path.read_bytes())
    workspace.update_component(sourcePath=f"sources/calibration-alias.{extension}")
    record = prepare_component(workspace.catalog(), workspace.component)
    assert record["solidCount"] == 2
    assert record["sourceSha256"] == digest(alternate)


@pytest.mark.parametrize("variant,solid_count,triangles", [
    ("standalone_part", 1, 12), ("wrapper_name_collision", 1, 12),
    ("rotated_prism", 1, 8), ("inch_unit_part", 1, 12),
])
def test_native_source_roots_and_non_axis_aligned_geometry_are_preserved(calibration_workspace, variant, solid_count, triangles):
    workspace = calibration_workspace
    expected = author_source_variant(workspace, variant)
    before = workspace.source_path.read_bytes()
    catalog = workspace.catalog()
    record = prepare_component(catalog, workspace.component)
    assert record["solidCount"] == solid_count
    assert record["geometryClass"] == "test_fixture" and record["completeRobot"] is False
    decoded = read_glb(catalog.asset(record["meshSha256"]))
    assert decoded["triangleCount"] == triangles
    assert sum(node["hasMesh"] for node in decoded["hierarchy"]) == solid_count
    expected_browser = {
        "min": [expected["min"][0] / 1000, expected["min"][2] / 1000, -expected["max"][1] / 1000],
        "max": [expected["max"][0] / 1000, expected["max"][2] / 1000, -expected["min"][1] / 1000],
    }
    for side in ("min", "max"):
        np.testing.assert_allclose(record["sourceBoundsMm"][side], expected[side], atol=1e-6)
        np.testing.assert_allclose(record["boundsM"][side], expected_browser[side], atol=1e-7)
        np.testing.assert_allclose(decoded["boundsM"][side], expected_browser[side], atol=1e-7)
    assert workspace.source_path.read_bytes() == before
    if variant == "inch_unit_part":
        assert "CONVERSION_BASED_UNIT('INCH'" in workspace.source_path.read_text()


def test_multiple_free_roots_require_explicit_source_selection(calibration_workspace):
    workspace = calibration_workspace
    author_source_variant(workspace, "multiple_free_roots")
    before = workspace.source_path.read_bytes()
    assert_error("AMBIGUOUS_STEP_ROOTS", lambda: prepare_component(workspace.catalog(), workspace.component))
    assert_no_prepared_output(workspace)
    assert workspace.source_path.read_bytes() == before


@pytest.mark.parametrize("field,value", [("completeRobot", True), ("nativeHierarchy", None),
                                         ("boundsM", []), ("conversion", "not-a-receipt")])
def test_invalid_receipt_fields_cannot_invent_geometry_or_robot_readiness(prepared_workspace, field, value):
    workspace = prepared_workspace
    catalog = workspace.catalog()
    path = catalog.receipt_path(workspace.component)
    record = load_json(path)
    record[field] = value
    save_json(path, record)
    assert_error("INVALID_RECEIPT", lambda: catalog.prepared(workspace.component))
    assert catalog.public()["components"] == []


def test_normalization_cannot_be_applied_twice(prepared_workspace):
    from tachyon.cad.glb import normalize_mm_to_m

    workspace = prepared_workspace
    catalog = workspace.catalog()
    record = catalog.prepared(workspace.component)
    mesh = catalog.asset(record["meshSha256"])
    before = mesh.read_bytes()
    assert_error("DOUBLE_UNIT_CONVERSION", lambda: normalize_mm_to_m(mesh))
    assert mesh.read_bytes() == before


def test_changed_converter_dependency_invalidates_preparation(prepared_workspace, monkeypatch):
    import tachyon.cad.catalog as catalog_module

    workspace = prepared_workspace
    catalog = workspace.catalog()
    old_fingerprint = catalog.fingerprint(workspace.component)
    current_version = catalog_module.version
    monkeypatch.setattr(catalog_module, "version", lambda name: current_version(name) + ".test-change")
    assert catalog.fingerprint(workspace.component) != old_fingerprint
    assert_error("MESH_NOT_PREPARED", lambda: catalog.prepared(workspace.component))


def test_seeder_cli_creates_separate_fixture_workspace_and_refuses_overwrite(tmp_path):
    project = Path(__file__).resolve().parents[2]
    # Exercise the actual CLI in a new disposable project so repeated pytest runs
    # never overwrite the browser-verification seed or the user's default data.
    temporary_project = tmp_path / "disposable-project"
    script = temporary_project / "tools/verification/seed_fixture.py"
    script.parent.mkdir(parents=True)
    script.write_bytes((project / "tools/verification/seed_fixture.py").read_bytes())
    private_default = temporary_project / ".local/catalog/manifest.json"
    private_default.parent.mkdir(parents=True)
    private_default.write_text("Existing default user data must remain unchanged.\n")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join([str(project / "server"), str(project / "server/tests")])
    environment["XDG_CACHE_HOME"] = str(tmp_path / "cache")
    completed = subprocess.run([sys.executable, str(script), "--prepare"], cwd=temporary_project,
                               env=environment, capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "Converter/render test_fixture (non-VEX): Tachyon calibration assembly [test_fixture, non-VEX]\n"
    assert completed.stderr == ""
    data_dir = temporary_project / ".local/verification-workspace"
    catalog = Catalog(Settings(temporary_project, data_dir))
    component = catalog.manifest.components[0]
    record = catalog.prepared(component)
    assert record["geometryClass"] == "test_fixture" and record["completeRobot"] is False
    assert record["solidCount"] == 2
    assert set(catalog.policy.records) == {component.source_sha256}
    assert Operation.lan_display not in catalog.policy.records[component.source_sha256].operations
    assert private_default.read_text() == "Existing default user data must remain unchanged.\n"
    before = {path.relative_to(data_dir): path.read_bytes() for path in data_dir.rglob("*") if path.is_file()}
    repeated = subprocess.run([sys.executable, str(script), "--prepare"], cwd=temporary_project,
                              env=environment, capture_output=True, text=True, timeout=60)
    assert repeated.returncode == 2
    assert repeated.stdout == ""
    assert repeated.stderr == "Calibration test_fixture destination must be new or empty.\n"
    assert before == {path.relative_to(data_dir): path.read_bytes() for path in data_dir.rglob("*") if path.is_file()}
