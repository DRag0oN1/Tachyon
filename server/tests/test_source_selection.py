"""Definition selection uses original non-VEX fixtures, never manufacturer CAD.

Native BReps, XCAF labels, STEP import, and GLB conversion are exercised here.
All generated geometry and receipts stay in pytest's temporary directories.
"""
import hashlib
import json
from dataclasses import dataclass
from importlib.metadata import version

import numpy as np
import pytest
from pydantic import ValidationError

from fixture_support import digest, load_json, save_json
from tachyon.cad import native
from tachyon.cad.catalog import Catalog
from tachyon.cad.prepare import prepare_component, prepare_components
from tachyon.cad.validation import geometry_validation
from tachyon.errors import TachyonError
from tachyon.models import Bounds, SourceSelection


def expect_error(code, action):
    with pytest.raises(TachyonError) as caught:
        action()
    assert caught.value.code == code


def bounds(shape):
    box = shape.BoundingBox()
    return {"min": [box.xmin, box.ymin, box.zmin],
            "max": [box.xmax, box.ymax, box.zmax]}


def selection_for(node, *, occurrence=False):
    return SourceSelection.model_validate({
        "sourceLabel" if occurrence else "definitionLabel": node.metadata[
            "sourceLabel" if occurrence else "definitionLabel"],
        "expectedDefinitionName": node.metadata["definitionName"],
    })


@pytest.fixture
def native_definitions():
    import cadquery as cq
    from cadquery.occ_impl.assembly import toCAF
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid

    leaf = cq.Workplane().box(4, 6, 8, centered=False).val().translate((2, -3, 5))
    # A genuinely invalid open solid makes the aggregate invalid independently
    # of the valid, repeated leaf. No isValid() result is mocked.
    builder = BRep_Builder()
    shell, solid = TopoDS_Shell(), TopoDS_Solid()
    builder.MakeShell(shell)
    for face in leaf.Faces()[:-1]:
        builder.Add(shell, face.wrapped)
    builder.MakeSolid(solid)
    builder.Add(solid, shell)
    source = cq.Assembly(name="original_fixture_root",
                         loc=cq.Location(cq.Vector(17, -8, 21), cq.Vector(1, 0, 0), 33))
    source.add(leaf, name="original_fixture_leaf", loc=cq.Location(cq.Vector(100, 30, -40)))
    group = cq.Assembly(name="original_fixture_group")
    group.add(leaf, name="original_fixture_repeat",
              loc=cq.Location(cq.Vector(-120, 50, 60), cq.Vector(0, 0, 1), 90))
    source.add(group, loc=cq.Location(cq.Vector(10, 20, 30), cq.Vector(0, 1, 0), 45))
    source.add(cq.Shape.cast(solid), name="original_fixture_invalid")
    _, document = toCAF(source, True)
    return native._load_source_document("original-in-memory-fixture", document)


@pytest.mark.parametrize("occurrence", [False, True])
def test_selection_isolates_valid_definition_from_invalid_root_without_moving_brep(native_definitions, occurrence):
    assembly = native_definitions
    leaf = next(n for n in assembly.objects.values() if n.name == "original_fixture_leaf")
    selection = selection_for(leaf, occurrence=occurrence)
    before = bounds(assembly.toCompound())
    assert not assembly.toCompound().isValid()
    selected = native.select_source_definition(assembly, selection)
    shape = selected.toCompound()
    assert selected.obj.isEqual(leaf.obj)
    assert not selected.children and len(shape.Solids()) == 1
    np.testing.assert_allclose(bounds(shape)["min"], [2, -3, 5], atol=1e-7)
    np.testing.assert_allclose(bounds(shape)["max"], [6, 3, 13], atol=1e-7)
    assert geometry_validation(selected, shape, detailed=True)["nativeBrepValid"] is True
    assert bounds(assembly.toCompound()) == before
    assert not assembly.toCompound().isValid()
    assert selected.metadata is not leaf.metadata


def test_repeated_occurrences_resolve_one_definition_not_an_arbitrary_occurrence(native_definitions):
    nodes = [n for n in native_definitions.objects.values()
             if n.metadata.get("definitionName") == "original_fixture_leaf"]
    assert len(nodes) == 2
    assert len({n.metadata["sourceLabel"] for n in nodes}) == 2
    assert len({n.metadata["definitionLabel"] for n in nodes}) == 1
    for node in nodes:
        selected = native.select_source_definition(native_definitions, selection_for(node))
        assert selected.obj.isEqual(nodes[0].obj)
        assert bounds(selected.toCompound()) == bounds(nodes[0].obj)


def test_selection_requires_exact_labels_and_definition_name(native_definitions):
    leaf = next(n for n in native_definitions.objects.values() if n.name == "original_fixture_leaf")
    selection = selection_for(leaf)
    expect_error("SOURCE_SELECTION_NOT_FOUND", lambda: native.select_source_definition(
        native_definitions, selection.model_copy(update={"definition_label": "0:999999"})))
    expect_error("SOURCE_SELECTION_MISMATCH", lambda: native.select_source_definition(
        native_definitions, selection.model_copy(update={"expected_definition_name": "incorrect_name"})))
    expect_error("SOURCE_SELECTION_NOT_FOUND", lambda: native.select_source_definition(
        native_definitions, selection.model_copy(update={"source_label": "0:999999"})))
    # Explicit root selection retains its tree; it does not turn an invalid
    # aggregate into a valid part or silently flatten the source assembly.
    root = native.select_source_definition(native_definitions, selection_for(native_definitions))
    assert root.obj is None and root.children
    assert not root.toCompound().isValid()


def test_ambiguous_labels_never_pick_first_match(native_definitions):
    leaf = next(n for n in native_definitions.objects.values() if n.name == "original_fixture_leaf")
    invalid = next(n for n in native_definitions.objects.values() if n.name == "original_fixture_invalid")
    # Corrupt metadata at the native boundary: one source label now points to
    # different definitions. A matching name must not resolve that ambiguity.
    invalid.metadata["sourceLabel"] = leaf.metadata["sourceLabel"]
    invalid.metadata["definitionName"] = leaf.metadata["definitionName"]
    expect_error("AMBIGUOUS_SOURCE_SELECTION", lambda: native.select_source_definition(
        native_definitions, selection_for(leaf, occurrence=True)))
    invalid.metadata["definitionLabel"] = leaf.metadata["definitionLabel"]
    expect_error("AMBIGUOUS_SOURCE_SELECTION", lambda: native.select_source_definition(
        native_definitions, selection_for(leaf)))


@pytest.fixture
def native_subassemblies():
    import cadquery as cq
    from cadquery.occ_impl.assembly import toCAF
    from cadquery.occ_impl.importers.assembly import _get_name
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    purchased = cq.Assembly(name="original_purchased_fixture")
    purchased.add(cq.Workplane().box(4, 6, 8, centered=False).translate((2, -3, 5)),
                  name="original_fixture_hub", loc=cq.Location(cq.Vector(9, 8, 7)))
    inner = cq.Assembly(name="original_fixture_inner")
    inner.add(cq.Workplane().box(2, 3, 5, centered=False), name="original_fixture_insert",
              loc=cq.Location(cq.Vector(4, 0, 1)))
    purchased.add(inner, loc=cq.Location(cq.Vector(-11, 5, 2), cq.Vector(0, 0, 1), 90))
    source = cq.Assembly(name="original_fixture_robot",
                         loc=cq.Location(cq.Vector(20, -30, 40), cq.Vector(1, 0, 0), 37))
    source.add(purchased, loc=cq.Location(cq.Vector(100, 50, 30), cq.Vector(0, 0, 1), 90))
    _, document = toCAF(source, True)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots, children = TDF_LabelSequence(), TDF_LabelSequence()
    tool.GetFreeShapes(roots)
    root = roots.Value(1)
    if tool.IsReference_s(root):
        referred = TDF_Label()
        assert tool.GetReferredShape_s(root, referred)
        root = referred
    tool.GetComponents_s(root, children)
    purchased_definition = TDF_Label()
    assert tool.GetReferredShape_s(children.Value(1), purchased_definition)
    assert _get_name(purchased_definition) == "original_purchased_fixture"
    repeated = tool.AddComponent(root, purchased_definition,
                                 cq.Location(cq.Vector(-200, 25, 60), cq.Vector(0, 1, 0), 53).wrapped)
    TDataStd_Name.Set_s(repeated, TCollection_ExtendedString("original_purchased_repeat"))
    tool.UpdateAssemblies()
    return native._load_source_document("original-subassembly-fixture", document)


@pytest.mark.parametrize("occurrence", [False, True])
def test_subassembly_selection_retains_children_frames_breps_and_provenance(native_subassemblies, occurrence):
    assembly = native_subassemblies
    nodes = [n for n in assembly.objects.values()
             if n.metadata.get("definitionName") == "original_purchased_fixture"]
    assert len(nodes) == 2
    assert len({n.metadata["definitionLabel"] for n in nodes}) == 1
    before = bounds(assembly.toCompound())

    def assert_same_tree(original, copied, *, root=False):
        assert original.metadata == copied.metadata
        assert original.metadata is not copied.metadata
        if not root:
            np.testing.assert_allclose(original.loc.toTuple(), copied.loc.toTuple(), atol=1e-10)
        if original.obj is not None:
            assert original.obj.isEqual(copied.obj)
        assert len(original.children) == len(copied.children)
        for a, b in zip(original.children, copied.children):
            assert_same_tree(a, b)

    for node in nodes:
        selected = native.select_source_definition(assembly, selection_for(node, occurrence=occurrence))
        assert selected.obj is None and len(selected.children) == 2
        assert selected.parent is None
        np.testing.assert_allclose(selected.loc.toTuple(), [(0, 0, 0), (0, 0, 0)], atol=1e-10)
        np.testing.assert_allclose(bounds(selected.toCompound())["min"], [-14, 5, 3], atol=1e-7)
        np.testing.assert_allclose(bounds(selected.toCompound())["max"], [15, 11, 20], atol=1e-7)
        assert len(selected.toCompound().Solids()) == 2
        assert selected.toCompound().isValid()
        # A definition-only selector has one canonical source occurrence;
        # an explicit sourceLabel retains that particular occurrence's metadata.
        original = node if occurrence else nodes[0]
        assert_same_tree(original, selected, root=True)
        selected.metadata["definitionLocation"][3] = 1000
        assert node.metadata["definitionLocation"][3] != 1000
        inner = next(n for n in selected.objects.values() if n.name == "original_fixture_inner")
        assert inner.obj is None and len(inner.children) == 1
        inner.metadata["test_local_note"] = "selected copy only"
        assert all("test_local_note" not in n.metadata for n in assembly.objects.values())
    assert bounds(assembly.toCompound()) == before


@pytest.mark.parametrize("value", [
    {}, {"expectedDefinitionName": "name_only"},
    {"definitionLabel": "0:1:2"},
    {"definitionLabel": "0:1:2", "expectedDefinitionName": "   "},
    {"sourceLabel": "name_instead_of_label", "expectedDefinitionName": "part"},
])
def test_selector_schema_rejects_incomplete_or_name_only_selection(value):
    with pytest.raises(ValidationError):
        SourceSelection.model_validate(value)


@dataclass
class SelectedWorkspace:
    workspace: object
    components: list


@pytest.fixture
def selected_workspace(calibration_workspace):
    workspace = calibration_workspace
    assembly = native.import_source(workspace.source_path)
    components = []
    for name in ("calibration_base", "calibration_offset_block"):
        node = next(n for n in assembly.objects.values() if n.metadata.get("definitionName") == name)
        components.append(workspace.component.model_copy(update={
            "id": "selected_" + name, "name": name + " [test_fixture, non-VEX]",
            "source_selection": selection_for(node), "ports": [],
            "expected_bounds_mm": Bounds.model_validate(bounds(node.obj)),
        }))
    manifest = load_json(workspace.manifest_path)
    manifest["components"] = [c.json_data() for c in components]
    save_json(workspace.manifest_path, manifest)
    return SelectedWorkspace(workspace, components)


def test_batch_reuses_import_but_keeps_distinct_local_geometry_and_selection_receipts(selected_workspace, monkeypatch):
    workspace, components = selected_workspace.workspace, selected_workspace.components
    original_import = native.import_source
    imports = []

    def import_once(path):
        imports.append(path)
        return original_import(path)

    monkeypatch.setattr(native, "import_source", import_once)
    before = digest(workspace.source_path)
    catalog = workspace.catalog()
    records = prepare_components(catalog, components)
    assert len(imports) == 1
    assert len({r["meshSha256"] for r in records}) == 2
    assert len({r["catalogFingerprint"] for r in records}) == 2
    for component, record in zip(components, records):
        assert record["sourceSha256"] == before
        assert record["sourceSelection"] == component.source_selection.json_data()
        assert record["solidCount"] == 1
        assert record["geometryValidation"]["nativeBrepValid"] is True
        assert record["conversion"]["sourceBoundsBasis"] == "native_measurement"
        assert sum(n["hasMesh"] for n in record["nativeHierarchy"]) == 1
        for side in ("min", "max"):
            np.testing.assert_allclose(record["sourceBoundsMm"][side], component.expected_bounds_mm.json_data()[side], atol=1e-7)
        assert catalog.prepared(component)["sourceSelection"] == record["sourceSelection"]
    assert digest(workspace.source_path) == before


def test_batch_records_a_failed_selector_and_still_prepares_independent_parts(selected_workspace):
    workspace,components=selected_workspace.workspace,selected_workspace.components
    bad=components[0].model_copy(update={"source_selection":SourceSelection(definition_label="0:999:1",expected_definition_name="missing")})
    errors=[]
    result=prepare_components(workspace.catalog(),[bad,components[1]],on_error=lambda c,e: errors.append((c.id,e.code)))
    assert errors==[(bad.id,"SOURCE_SELECTION_NOT_FOUND")]
    assert len(result)==1 and result[0]["id"]==components[1].id
    assert workspace.catalog().prepared(components[1])["meshSha256"]==result[0]["meshSha256"]


def test_reused_receipt_still_rechecks_source_bytes_and_conversion_rights(selected_workspace,monkeypatch):
    catalog=selected_workspace.workspace.catalog();component=selected_workspace.components[0]
    original=prepare_component(catalog,component)
    def unexpected_import(path):
        pytest.fail("A current cached receipt should not re-import unchanged geometry")
    monkeypatch.setattr(native,"import_source",unexpected_import)
    reused=prepare_components(catalog,[component],reuse_existing=True)[0]
    from tachyon.models import PreparedComponent
    assert PreparedComponent.model_validate(reused).mesh_sha256==original["meshSha256"]
    assert "qualifiedOperations" not in reused
    from tachyon.models import Operation
    catalog.policy.records[component.source_sha256].operations[Operation.conversion].status="disallowed"
    expect_error("SOURCE_NOT_QUALIFIED",lambda: prepare_components(catalog,[component],reuse_existing=True))


def test_selected_preparation_validates_leaf_after_selection_even_for_reference(selected_workspace, native_definitions, monkeypatch):
    component = selected_workspace.components[0]
    leaf = next(n for n in native_definitions.objects.values() if n.name == "original_fixture_leaf")
    component = component.model_copy(update={
        "source_selection": selection_for(leaf), "reference_only": True,
        "expected_bounds_mm": Bounds.model_validate(bounds(leaf.obj)),
    })
    assert not native_definitions.toCompound().isValid()
    monkeypatch.setattr(native, "import_source", lambda path: native_definitions)
    record = prepare_component(selected_workspace.workspace.catalog(), component)
    assert record["solidCount"] == 1 and record["geometryValidation"]["nativeBrepValid"] is True
    assert record["geometryValidation"]["qualifiedForRobotGeneration"] is False
    invalid = next(n for n in native_definitions.objects.values() if n.name == "original_fixture_invalid")
    component = component.model_copy(update={"source_selection": selection_for(invalid)})
    expect_error("INVALID_GEOMETRY", lambda: prepare_component(selected_workspace.workspace.catalog(), component))


@pytest.mark.parametrize("change", ["missing", "label", "name", "hash"])
def test_receipt_source_hash_and_selector_tampering_are_rejected(selected_workspace, change):
    workspace, components = selected_workspace.workspace, selected_workspace.components
    catalog, component = workspace.catalog(), components[0]
    record = prepare_component(catalog, component)
    if change == "missing":
        del record["sourceSelection"]
    elif change == "label":
        record["sourceSelection"] = components[1].source_selection.json_data()
    elif change == "name":
        record["sourceSelection"]["expectedDefinitionName"] = "wrong_name"
    else:
        record["sourceSha256"] = "1" * 64
    save_json(catalog.receipt_path(component), record)
    expect_error("STALE_MESH", lambda: catalog.prepared(component))


@pytest.mark.parametrize("operation", ["acquisition_storage", "conversion"])
def test_batch_rechecks_rights_before_reusing_import(selected_workspace, monkeypatch, operation):
    workspace, components = selected_workspace.workspace, selected_workspace.components
    from tachyon.cad import prepare

    original_write = prepare.write_json
    catalog = workspace.catalog()

    def revoke_after_first(path, record):
        original_write(path, record)
        catalog.policy.records[components[0].source_sha256].operations[operation].status = "disallowed"

    monkeypatch.setattr(prepare, "write_json", revoke_after_first)
    expect_error("SOURCE_NOT_QUALIFIED", lambda: prepare_components(catalog, components))
    assert not catalog.receipt_path(components[1]).exists()


@pytest.mark.parametrize("when", ["before_import", "during_import", "between_components"])
def test_batch_rechecks_whole_file_hash_even_with_selection_and_import_reuse(selected_workspace, monkeypatch, when):
    workspace, components = selected_workspace.workspace, selected_workspace.components
    from tachyon.cad import prepare

    original_import, original_write = native.import_source, prepare.write_json
    imports = []

    def change_source():
        workspace.source_path.write_bytes(workspace.source_path.read_bytes() + b"\nchanged original fixture\n")

    def counted_import(path):
        imports.append(path)
        result = original_import(path)
        if when == "during_import":
            change_source()
        return result

    def change_after_first(path, record):
        original_write(path, record)
        if when == "between_components":
            change_source()

    monkeypatch.setattr(native, "import_source", counted_import)
    monkeypatch.setattr(prepare, "write_json", change_after_first)
    if when == "before_import":
        change_source()
    catalog = workspace.catalog()
    expect_error("SOURCE_HASH_MISMATCH", lambda: prepare_components(catalog, components))
    assert len(imports) == (0 if when == "before_import" else 1)
    assert not catalog.receipt_path(components[1]).exists()
    if when != "between_components":
        assert not list(workspace.data_dir.glob("catalog/prepared/*.json"))


def test_selection_is_bound_to_catalog_fingerprint(selected_workspace):
    workspace, components = selected_workspace.workspace, selected_workspace.components
    catalog = workspace.catalog()
    first = components[0]
    changed = first.model_copy(update={"source_selection": components[1].source_selection})
    record = prepare_component(catalog, first)
    assert catalog.fingerprint(first) != catalog.fingerprint(changed)
    expect_error("MESH_NOT_PREPARED", lambda: catalog.prepared(changed))
    save_json(catalog.receipt_path(changed), record)
    expect_error("STALE_MESH", lambda: catalog.prepared(changed))


def test_prepare_preserves_native_subassembly_as_one_catalog_component(calibration_workspace):
    workspace = calibration_workspace
    assembly = native.import_source(workspace.source_path)
    group = next(n for n in assembly.objects.values()
                 if n.metadata.get("definitionName") == "calibration_offset_group")
    component = workspace.component.model_copy(update={
        "source_selection": selection_for(group), "ports": [],
        "expected_bounds_mm": Bounds(min=(10, 35, 3), max=(22, 43, 9)),
    })
    catalog = workspace.catalog()
    record = prepare_component(catalog, component)
    assert record["sourceSelection"] == component.source_selection.json_data()
    assert record["geometryValidation"]["nativeBrepValid"] is True
    assert record["solidCount"] == 1
    assert record["sourceBoundsMm"] == {"min": [10, 35, 3], "max": [22, 43, 9]}
    group_nodes = [n for n in record["nativeHierarchy"] if n["name"] == "calibration_offset_group"]
    assert len(group_nodes) == 1 and group_nodes[0]["hasMesh"] is False
    leaf = next(n for n in record["nativeHierarchy"] if n["name"] == "calibration_offset_block")
    assert leaf["hasMesh"] is True and leaf["parentId"] == group_nodes[0]["id"]
    assert catalog.prepared(component)["sourceSelection"] == record["sourceSelection"]


def test_converter_version_change_invalidates_only_selected_geometry(selected_workspace, monkeypatch):
    import tachyon.cad.catalog as catalog_module

    workspace, components = selected_workspace.workspace, selected_workspace.components
    catalog = workspace.catalog()
    selected = components[0]
    whole = selected.model_copy(update={"source_selection": None})
    previous_selected, previous_whole = catalog.fingerprint(selected), catalog.fingerprint(whole)
    prepare_component(catalog, selected)
    monkeypatch.setattr(catalog_module, "DEFINITION_CONVERTER", "native-definition-selection-test-next")
    assert catalog.fingerprint(selected) != previous_selected
    assert catalog.fingerprint(whole) == previous_whole
    expect_error("MESH_NOT_PREPARED", lambda: catalog.prepared(selected))


def test_legacy_whole_file_fingerprint_and_receipt_remain_compatible(prepared_workspace):
    workspace = prepared_workspace
    component, catalog = workspace.component, workspace.catalog()
    assert "sourceSelection" not in component.json_data()
    assert "sourceSelection" not in component.model_dump(by_alias=True)
    assert "source_selection" not in component.model_dump()
    assert "sourceSelection" not in catalog.manifest.json_data()["components"][0]
    legacy_component = component.json_data()
    legacy_component.pop("sourceSelection", None)
    # Frozen pre-extension converter digest, not a digest of today's edited files.
    legacy_identity = {
        "component": legacy_component, "cadquery": version("cadquery"),
        "ocp": version("cadquery-ocp"),
        "converterCode": "692216dbfc550bcb749a18e7196c684e616117e03e977377f6e118350bac5524",
    }
    expected = hashlib.sha256(json.dumps(legacy_identity, sort_keys=True).encode()).hexdigest()
    assert catalog.fingerprint(component) == expected
    path = catalog.receipt_path(component)
    record = load_json(path)
    assert "sourceSelection" not in record
    assert catalog.prepared(component)["solidCount"] == 2
    # Explicit null and the old missing optional field are equivalent.
    record["sourceSelection"] = None
    save_json(path, record)
    assert "sourceSelection" not in catalog.prepared(component)
    assert catalog.fingerprint(component.model_copy(update={"source_selection": None})) == expected
