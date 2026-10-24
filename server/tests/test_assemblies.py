"""Original metadata-only fixtures. No CAD bytes or authentic-VEX acceptance.

The deliberately synthetic hashes/URLs identify test records, not existing meshes.
Their coordinate measurements are authored test inputs for graph mathematics.
"""
from copy import deepcopy
import math

from pydantic import ValidationError
import pytest

from tachyon.assemblies import (
    AssemblyRevision, AssemblyService, AssemblySnapshot, AttachmentPort,
    ComponentDefinition, ComponentInstance, MateVerification, Relationship,
    RigidTransform, Subsystem, build_fixture_demonstrator, stable_id,
    validate_assembly, validate_revision, world_transforms,
)
from tachyon.errors import TachyonError


def error(code, action):
    with pytest.raises(TachyonError) as caught:
        action()
    assert caught.value.code == code


def port(key, point=(0., 0., 0.), *, kind="mount", rotation=None):
    frame = RigidTransform.translation(*point)
    if rotation is not None:
        frame = frame.compose(rotation)
    return AttachmentPort(id=key, kind=kind, frame=frame,
                          evidence="Original metadata fixture coordinate; graph test only")


def fixture_definitions():
    def definition(key, ports):
        return ComponentDefinition(id=key, name=f"Original non-VEX graph fixture: {key}",
                                   source_url="tachyon-test-metadata:" + key,
                                   source_sha256="1"*64, mesh_sha256="2"*64,
                                   mesh_url="tachyon-test-metadata:nonexistent-mesh",
                                   catalog_fingerprint="3"*64, origin_kind="tachyon_authored",
                                   geometry_class="test_fixture", declared_use="graph_unit_test_only",
                                   qualified_operations=("assembly_placement",),
                                   attribution="Original Tachyon test metadata; no source geometry",
                                   ports=ports)
    return (definition("tachyon_fixture_post", (port("lower", (0, .1, 0)), port("raised", (0, .25, 0)))),
            definition("tachyon_fixture_carrier", (port("mount", (0, -.02, 0)), port("tool", (.03, .04, 0)))),
            definition("tachyon_fixture_tool", (port("mount", (0, -.01, 0)),)))


def demo(service, configuration_id="lower", design_id="fixture-design"):
    return build_fixture_demonstrator(service, base_component_id="tachyon_fixture_post",
                                       carrier_component_id="tachyon_fixture_carrier",
                                       tool_component_id="tachyon_fixture_tool",
                                       configuration_id=configuration_id, design_id=design_id)


@pytest.fixture
def assembly_case():
    service = AssemblyService(fixture_definitions())
    lower = demo(service)
    ids = {role: stable_id("instance", "fixture-design", role) for role in ("base", "carrier", "tool")}
    return service, lower, ids


def changed(snapshot, mutate):
    data = snapshot.json_data()
    mutate(data)
    return AssemblySnapshot.model_validate(data)


def test_two_original_configurations_close_and_preserve_exact_identities(assembly_case):
    service, lower, ids = assembly_case
    raised = demo(service, "raised")
    assert {n.id for n in lower.assembly.instances} == {n.id for n in raised.assembly.instances}
    assert world_transforms(lower.assembly)[ids["carrier"]].point() == pytest.approx((0, .12, 0))
    assert world_transforms(raised.assembly)[ids["carrier"]].point() == pytest.approx((0, .27, 0))
    assert world_transforms(raised.assembly)[ids["tool"]].point() == pytest.approx((.03, .32, 0))
    assert lower.engineering_hash != raised.engineering_hash
    for revision in (lower, raised):
        report = service.validate(revision)
        assert report.graph_valid and not report.complete_robot and report.status == "incomplete"
        assert {"NON_AUTHENTIC_GEOMETRY", "GEOMETRY_QUALIFICATION_UNKNOWN", "UNVERIFIED_PHYSICAL_MATES"} <= set(report.blockers)
        assert revision.assembly.units == "m" and revision.assembly.up_axis == "Y"
        assert revision.assembly.components == tuple(sorted(fixture_definitions(), key=lambda c: c.id))
    error("UNSUPPORTED_CONFIGURATION", lambda: demo(service, "fictional-height"))


def test_remount_carries_descendants_without_mutating_accepted_revision(assembly_case):
    service, lower, ids = assembly_case
    before = lower.model_dump_json()
    raised = service.align_ports(lower, "carrier-mount", parent_port_id="raised", configuration_id="raised")
    assert lower.model_dump_json() == before
    assert raised.parent_revision_id == lower.id
    assert raised.engineering_hash == demo(service, "raised").engineering_hash
    assert raised.id != demo(service, "raised").id  # history is separate from engineering content
    old_nodes = {n.id: n for n in lower.assembly.instances}
    new_nodes = {n.id: n for n in raised.assembly.instances}
    assert old_nodes[ids["tool"]] == new_nodes[ids["tool"]]
    assert world_transforms(raised.assembly)[ids["tool"]].point()[1] - world_transforms(lower.assembly)[ids["tool"]].point()[1] == pytest.approx(.15)
    assert service.align_ports(lower, "carrier-mount", parent_port_id="raised", configuration_id="raised") == raised
    restored = service.align_ports(raised, "carrier-mount", parent_port_id="lower", configuration_id="lower")
    assert restored.engineering_hash == lower.engineering_hash
    assert restored.id != lower.id
    assert AssemblyRevision.model_validate_json(raised.model_dump_json()) == raised
    with pytest.raises(ValidationError):
        lower.assembly.configuration_id = "mutated"


def test_rigid_math_and_root_placement_use_rotation_and_translation(assembly_case):
    service, lower, ids = assembly_case
    rotation = RigidTransform.rotation((0, 1, 0), math.pi/2)
    transform = RigidTransform.translation(1, 2, 3).compose(rotation)
    assert transform.point((1, 0, 0)) == pytest.approx((1, 2, 2))
    assert transform.inverse().point(transform.point((.2, -.7, .8))) == pytest.approx((.2, -.7, .8))
    moved = service.place(lower, ids["base"], transform)
    assert world_transforms(moved.assembly)[ids["tool"]].point() == pytest.approx((1, 2.17, 2.97))
    assert world_transforms(lower.assembly)[ids["tool"]].point() == pytest.approx((.03, .17, 0))
    error("PORT_ALIGNMENT", lambda: service.place(lower, ids["carrier"], RigidTransform.translation(0, .5, 0)))
    error("DANGLING_REFERENCE", lambda: service.place(lower, "missing", transform))


@pytest.mark.parametrize("mutation", [
    lambda m: m.__setitem__(0, 2),  # scaling
    lambda m: m.__setitem__(4, .1),  # shear
    lambda m: m.__setitem__(0, -1),  # reflection
    lambda m: m.__setitem__(3, .1),  # projective matrix
    lambda m: m.__setitem__(15, 0),
    lambda m: m.__setitem__(12, float("nan")),
    lambda m: m.__setitem__(13, float("inf")),
    lambda m: m.__setitem__(0, True),
    lambda m: m.__setitem__(12, "0.1"),
    lambda m: m.pop(),
])
def test_non_rigid_or_non_finite_transforms_rejected(mutation):
    matrix = list(RigidTransform().matrix)
    mutation(matrix)
    with pytest.raises(ValidationError):
        RigidTransform(matrix=matrix)


@pytest.mark.parametrize("mutate,code", [
    (lambda d: d["components"].pop(), "MISSING_COMPONENT"),
    (lambda d: d["instances"].append(d["instances"][0]), "DUPLICATE_ID"),
    (lambda d: d["relationships"].clear(), "DISCONNECTED_ASSEMBLY"),
    (lambda d: d["relationships"][0].update(childInstanceId="absent"), "DANGLING_REFERENCE"),
    (lambda d: d["relationships"][0].update(parentPortId="missing-port"), "MISSING_PORT"),
    (lambda d: d["instances"][0].update(subsystemId="absent"), "DANGLING_REFERENCE"),
    (lambda d: d.update(rootInstanceId="absent"), "INVALID_ROOT"),
    (lambda d: d["subsystems"].append({"id": "empty", "name": "Empty"}), "EMPTY_SUBSYSTEM"),
])
def test_dangling_or_disconnected_graph_rejected(assembly_case, mutate, code):
    _, lower, _ = assembly_case
    error(code, lambda: validate_assembly(changed(lower.assembly, mutate)))


def test_placement_parent_does_not_imply_physical_attachment(assembly_case):
    _, lower, ids = assembly_case
    no_mate = changed(lower.assembly, lambda d: d.update(relationships=[]))
    assert world_transforms(no_mate)[ids["tool"]].point() == pytest.approx((.03, .17, 0))
    error("DISCONNECTED_ASSEMBLY", lambda: validate_assembly(no_mate))
    for bad_parent in ("absent", ids["tool"]):
        data = lower.assembly.json_data()
        next(n for n in data["instances"] if n["id"] == ids["carrier"])["parentId"] = bad_parent
        error("INVALID_PLACEMENT_HIERARCHY", lambda: validate_assembly(AssemblySnapshot.model_validate(data)))


def test_rotated_full_port_alignment_solves_inverse_child_frame():
    parent = ComponentDefinition.model_validate({**fixture_definitions()[0].json_data(), "ports": [
        port("lower", (.1, .2, .3), rotation=RigidTransform.rotation((0, 1, 0), math.pi/2)).json_data(),
        port("raised", (.1, .4, .3), rotation=RigidTransform.rotation((0, 1, 0), math.pi/2)).json_data()]})
    carrier = ComponentDefinition.model_validate({**fixture_definitions()[1].json_data(), "ports": [
        port("mount", (0, -.02, 0), rotation=RigidTransform.rotation((0, 0, 1), math.pi/2)).json_data(),
        port("tool", (.03, .04, 0)).json_data()]})
    service = AssemblyService((parent, carrier, fixture_definitions()[2]))
    lower = demo(service)
    raised = service.align_ports(lower, "carrier-mount", parent_port_id="raised", configuration_id="raised")
    child_id = next(n.id for n in raised.assembly.instances if n.component_id == carrier.id)
    # Ry(90) * inverse(Rz(90)): local +X maps to world -Y.
    world = world_transforms(raised.assembly)[child_id]
    assert world.point((1, 0, 0)) == pytest.approx((.1, -.6, .28))
    assert world.point((0, -.02, 0)) == pytest.approx((.1, .4, .3))
    service.validate(raised)


@pytest.mark.parametrize("kind,port_kind,position", [("revolute", "revolute", .3), ("prismatic", "prismatic", .03)])
def test_joint_axis_limits_moving_members_and_static_pose(kind, port_kind, position):
    definitions = fixture_definitions()[:2]
    definitions = tuple(ComponentDefinition.model_validate({**d.json_data(), "ports": [port("joint", kind=port_kind).json_data()]}) for d in definitions)
    service = AssemblyService(definitions)
    joint = Relationship(id="joint", parent_instance_id="base", parent_port_id="joint", child_instance_id="child",
                         child_port_id="joint", kind=kind, axis=(0, 1, 0), limits=(-.5, .5), position=position,
                         moving_member_ids=("child",))
    revision = service.build(design_id="joint-test", recipe_id="original-static-joint", configuration_id="sample",
                             root_instance_id="base", subsystems=(Subsystem(id="s", name="Fixture"),),
                             instances=(ComponentInstance(id="base", component_id=definitions[0].id, subsystem_id="s"),
                                        ComponentInstance(id="child", component_id=definitions[1].id, subsystem_id="s",
                                                          parent_id="base", transform=joint.offset())), relationships=(joint,))
    assert service.validate(revision).status == "incomplete"
    if kind == "prismatic":
        assert world_transforms(revision.assembly)["child"].point() == pytest.approx((0, .03, 0))
    else:
        assert world_transforms(revision.assembly)["child"].point((1, 0, 0)) == pytest.approx((math.cos(.3), 0, -math.sin(.3)))
    for updates in ({"axis": [0, 2, 0]}, {"limits": [1, -1]}, {"position": .6}, {"movingMemberIds": []}, {"axis": None}):
        with pytest.raises(ValidationError):
            Relationship.model_validate({**joint.json_data(), **updates})
    bad = changed(revision.assembly, lambda d: d["relationships"][0].update(movingMemberIds=["absent"]))
    error("INVALID_JOINT_MEMBERS", lambda: validate_assembly(bad))


def test_cross_subtree_attachment_prevents_a_remount_opening_a_loop(assembly_case):
    service, lower, ids = assembly_case
    world = world_transforms(lower.assembly)
    # An additional explicit fixed constraint from root to tool closes this graph loop.
    pp = fixture_definitions()[0].ports[0].frame
    cp = fixture_definitions()[2].ports[0].frame
    offset = world[ids["base"]].compose(pp).inverse().compose(world[ids["tool"]].compose(cp))
    data = lower.assembly.json_data()
    data["relationships"].append(Relationship(id="root-tool-brace", parent_instance_id=ids["base"],
                                 parent_port_id="lower", child_instance_id=ids["tool"], child_port_id="mount",
                                 mate_transform=offset).json_data())
    assembly = AssemblySnapshot.model_validate(data)
    constrained = service.build(design_id=assembly.design_id, recipe_id=assembly.recipe_id,
                                configuration_id=assembly.configuration_id, root_instance_id=ids["base"],
                                instances=assembly.instances, subsystems=assembly.subsystems,
                                relationships=assembly.relationships)
    error("PORT_ALIGNMENT", lambda: service.align_ports(constrained, "carrier-mount", parent_port_id="raised"))


def test_canonical_hash_tampering_and_changed_prepared_source(assembly_case):
    service, lower, ids = assembly_case
    shuffled = service.build(design_id=lower.assembly.design_id, recipe_id=lower.assembly.recipe_id,
                              configuration_id="lower", root_instance_id=ids["base"],
                              instances=reversed(lower.assembly.instances), subsystems=reversed(lower.assembly.subsystems),
                              relationships=reversed(lower.assembly.relationships))
    assert shuffled == lower
    data = lower.json_data()
    data["assembly"]["configurationId"] = "tampered"
    error("REVISION_HASH_MISMATCH", lambda: validate_revision(AssemblyRevision.model_validate(data)))
    definitions = list(fixture_definitions())
    definitions[0] = ComponentDefinition.model_validate({**definitions[0].json_data(), "sourceSha256": "9"*64})
    error("CATALOG_CHANGED", lambda: AssemblyService(definitions).validate(lower))
    error("MISSING_COMPONENT", lambda: demo(AssemblyService(definitions[:1])))
    reordered_definitions = []
    for definition in fixture_definitions():
        data = definition.json_data()
        data["ports"].reverse()
        data["qualifiedOperations"] = ["loopback_display", "assembly_placement", "loopback_display"]
        reordered_definitions.append(ComponentDefinition.model_validate(data))
    reordered_service = AssemblyService(reversed(reordered_definitions))
    assert reordered_service.validate(demo(reordered_service)).graph_valid


def test_verified_mate_needs_explicit_evidence_and_remount_clears_it(assembly_case):
    service, lower, ids = assembly_case
    data = lower.assembly.json_data()
    proof = MateVerification(parent_source_sha256="1"*64, child_source_sha256="1"*64,
                             parent_port_id="lower", child_port_id="mount",
                             evidence="Fixture-only declared test proof; no real fit certification")
    data["relationships"][0]["verification"] = proof.json_data()
    assembly = AssemblySnapshot.model_validate(data)
    verified = service.build(design_id=assembly.design_id, recipe_id=assembly.recipe_id,
                             configuration_id=assembly.configuration_id, root_instance_id=ids["base"],
                             instances=assembly.instances, subsystems=assembly.subsystems, relationships=assembly.relationships)
    changed_revision = service.align_ports(verified, "carrier-mount", parent_port_id="raised")
    assert next(r for r in changed_revision.assembly.relationships if r.id == "carrier-mount").verification is None
    data["relationships"][0]["verification"]["parentSourceSha256"] = "9"*64
    error("STALE_MATE_EVIDENCE", lambda: validate_assembly(AssemblySnapshot.model_validate(data)))


def prepared_metadata():
    # Existing PreparedComponent wire contract, with no geometry or filesystem access.
    return {"id": "original_metadata_fixture", "name": "Original non-VEX receipt fixture", "sku": None,
            "originKind": "tachyon_authored", "geometryClass": "test_fixture", "sourceUrl": "tachyon-test:receipt",
            "sourceSha256": "1"*64, "meshSha256": "2"*64, "meshUrl": "tachyon-test:no-mesh",
            "catalogFingerprint": "3"*64, "boundsM": {"min": [0, 0, 0], "max": [.01, .02, .03]},
            "sourceBoundsMm": {"min": [0, 0, 0], "max": [10, 20, 30]}, "solidCount": 1,
            "nativeHierarchy": [{"id": "native-0", "name": "Import root", "parentId": None,
                                 "matrix": list(RigidTransform().matrix), "hasMesh": True}],
            "ports": [{"id": "mount", "kind": "mount", "positionM": [.01, .02, .03], "axis": [0, 1, 0],
                       "evidence": "Original receipt test coordinates only"}],
            "rightsStatus": "qualified_for_declared_use", "declaredUse": "loopback_source_inspection",
            "conversion": {"tool": "CadQuery", "version": "test-metadata-only", "linearDeflectionMm": .05,
                           "angularDeflectionRad": .1, "frame": "metres/Y-up", "maxBoundsErrorM": 0,
                           "displayMeshOnly": True}, "attribution": "Original metadata fixture", "completeRobot": False}


def test_prepared_adapter_preserves_source_mesh_and_does_not_infer_roll_rights_or_mates():
    data = prepared_metadata()
    before = deepcopy(data)
    definition = ComponentDefinition.from_prepared(data)
    assert data == before
    assert definition.source_sha256 == data["sourceSha256"] and definition.mesh_sha256 == data["meshSha256"]
    assert definition.mesh_url == data["meshUrl"] and definition.catalog_fingerprint == data["catalogFingerprint"]
    assert not definition.qualified_operations
    assert definition.ports[0].frame_basis == "axis_only"
    assert definition.ports[0].frame.point() == pytest.approx((.01, .02, .03))
    assert definition.ports[0].frame.matrix[8:11] == pytest.approx((0, 1, 0))
    data["qualifiedOperations"] = ["assembly_placement"]
    assert ComponentDefinition.from_prepared(data).qualified_operations == ("assembly_placement",)
    measured = ComponentDefinition.from_prepared(data, ports=(port("mount"),), qualified_operations=())
    assert measured.ports[0].frame_basis == "measured" and not measured.qualified_operations
    with pytest.raises(ValidationError):
        ComponentDefinition.model_validate({**definition.json_data(), "geometryClass": "verified_imported_component"})


@pytest.mark.parametrize("updates,code", [
    ({"referenceOnly": True}, "REFERENCE_ONLY_COMPONENT"),
    ({"geometryValidation": {"qualifiedForRobotGeneration": False}}, "GEOMETRY_NOT_QUALIFIED"),
    ({"geometryValidation": {"nativeBrepValid": False}}, "GEOMETRY_NOT_QUALIFIED"),
    ({"qualifiedOperations": ["acquisition_storage", "conversion", "loopback_display"]}, "ASSEMBLY_RIGHTS_NOT_QUALIFIED"),
])
def test_reference_geometry_and_inspection_only_permissions_cannot_enter_an_assembly(updates, code):
    definitions = list(fixture_definitions())
    definitions[0] = ComponentDefinition.model_validate({**definitions[0].json_data(), **updates})
    error(code, lambda: demo(AssemblyService(definitions)))


def test_reference_diagnostics_from_importer_are_preserved_and_rejected_for_placement():
    data = prepared_metadata()
    data["referenceOnly"] = True
    data["geometryValidation"] = {
        "status": "source_defects", "nativeBrepValid": False, "qualifiedForRobotGeneration": False,
        "invalidDefinitionCount": 1,
        "invalidComponentInstances": [{"path": "root/test", "name": "test", "definitionName": "defective-fixture"}],
        "limitations": ["Synthetic defect diagnostic; inspection-only test metadata"],
        "diagnostics": "per_definition", "nativeBoundsMaxErrorMm": 0.0,
    }
    definition = ComponentDefinition.from_prepared(data, qualified_operations=("assembly_placement",))
    assert definition.reference_only
    assert definition.geometry_validation.json_data() == data["geometryValidation"]
    service = AssemblyService((definition,))
    error("REFERENCE_ONLY_COMPONENT", lambda: service.build(
        design_id="reference-test", recipe_id="not-a-robot", configuration_id="inspection-only",
        root_instance_id="root", instances=(ComponentInstance(id="root", component_id=definition.id, subsystem_id="s"),),
        subsystems=(Subsystem(id="s", name="Reference"),), relationships=()))


def test_required_part_manifest_catches_removed_leaf_and_units_are_explicit(assembly_case):
    _, lower, ids = assembly_case
    data = lower.assembly.json_data()
    data["instances"] = [node for node in data["instances"] if node["id"] != ids["tool"]]
    data["relationships"] = [rel for rel in data["relationships"] if rel["id"] != "tool-mount"]
    error("MISSING_REQUIRED_PART", lambda: validate_assembly(AssemblySnapshot.model_validate(data)))
    for field, value in (("units", "mm"), ("upAxis", "Z"), ("matrixLayout", "row-major"), ("completeRobot", True)):
        data = lower.assembly.json_data()
        data[field] = value
        with pytest.raises(ValidationError):
            AssemblySnapshot.model_validate(data)


def test_incompatible_port_and_unmeasured_verified_frame_rejected(assembly_case):
    _, lower, _ = assembly_case
    def replace_port(data, **updates):
        base = next(c for c in data["components"] if c["id"] == "tachyon_fixture_post")
        next(p for p in base["ports"] if p["id"] == "lower").update(updates)
    error("INCOMPATIBLE_PORT", lambda: validate_assembly(changed(lower.assembly, lambda d: replace_port(d, kind="prismatic"))))
    data = lower.assembly.json_data()
    replace_port(data, frameBasis="axis_only")
    data["relationships"][0]["verification"] = MateVerification(
        parent_source_sha256="1"*64, child_source_sha256="1"*64, parent_port_id="lower",
        child_port_id="mount", evidence="Graph test only").json_data()
    error("STALE_MATE_EVIDENCE", lambda: validate_assembly(AssemblySnapshot.model_validate(data)))
