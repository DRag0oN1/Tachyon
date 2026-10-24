"""Revision-exact strategy links using original non-VEX graph fixtures only."""
import math

from pydantic import ValidationError
import pytest

from tachyon.assemblies import (
    AssemblyRevision, AssemblyService, ComponentDefinition, ComponentInstance,
    Relationship, RigidTransform, Subsystem, world_transforms,
)
from tachyon.bindings import (
    ActionBinding, BindingAnchor, BindingSnapshot, actions_for_component,
    bind_actions, derive_annotations, rebind_actions, resolve_action,
)
from test_assemblies import assembly_case, demo, error, prepared_metadata


def bindings_for(revision, ids):
    return bind_actions(revision, competition_id="original-test-competition", strategy_id="original-test-strategy",
                        actions=(ActionBinding(action_id="carry-test-object", subsystem_id="carrier", anchors=(
                            BindingAnchor(id="tool-tip", instance_id=ids["tool"], local_point_m=(0, .02, 0)),
                            BindingAnchor(id="carrier-mount", instance_id=ids["carrier"], port_id="mount"))),
                                 ActionBinding(action_id="inspect-carrier", subsystem_id="carrier",
                                               instance_ids=(ids["carrier"],))))


def test_action_to_subsystem_actual_instance_and_component_ids_and_reverse_query(assembly_case):
    _, lower, ids = assembly_case
    links = bindings_for(lower, ids)
    action = resolve_action(lower, links, "carry-test-object")
    assert action.subsystem_id == "carrier"
    assert set(action.instance_ids) == {ids["carrier"], ids["tool"]}
    assert set(action.component_ids) == {"tachyon_fixture_carrier", "tachyon_fixture_tool"}
    assert action.capability_status == "unsupported"
    assert [a.action_id for a in actions_for_component(lower, links, ids["tool"])] == ["carry-test-object"]
    assert {a.action_id for a in actions_for_component(lower, links, ids["carrier"])} == {"carry-test-object", "inspect-carrier"}
    assert actions_for_component(lower, links, ids["base"]) == ()
    assert links.engineering_hash == lower.engineering_hash and links.revision_id == lower.id
    assert BindingSnapshot.model_validate_json(links.model_dump_json()) == links
    assert bindings_for(lower, ids) == links
    error("INVALID_BINDING", lambda: actions_for_component(lower, links, "missing"))
    error("INVALID_BINDING", lambda: resolve_action(lower, links, "missing"))


def test_annotations_derive_from_full_world_transform_and_measured_ports(assembly_case):
    service, lower, ids = assembly_case
    transform = RigidTransform.translation(1, 2, 3).compose(RigidTransform.rotation((0, 1, 0), math.pi/2))
    moved = service.place(lower, ids["base"], transform)
    links = bindings_for(moved, ids)
    artifacts = derive_annotations(moved, links, "carry-test-object")
    by_port = {artifact.anchor.port_id: artifact for artifact in artifacts}
    assert by_port[None].anchor.world_point_m == pytest.approx((1, 2.19, 2.97))
    assert by_port["mount"].anchor.world_point_m == pytest.approx((1, 2.1, 3))
    for artifact in artifacts:
        assert artifact.revision_id == moved.id
        assert artifact.bindings_hash == links.bindings_hash
        assert artifact.engineering_hash == moved.engineering_hash
        assert {ids["carrier"], ids["tool"], "tachyon_fixture_carrier", "tachyon_fixture_tool"} <= set(artifact.dependency_ids)


def test_links_preserved_and_anchors_rederived_after_remount_and_restore(assembly_case):
    service, lower, ids = assembly_case
    links = bindings_for(lower, ids)
    before = links.model_dump_json()
    old_artifacts = derive_annotations(lower, links, "carry-test-object")
    raised = service.align_ports(lower, "carrier-mount", parent_port_id="raised", configuration_id="raised")
    error("STALE_BINDINGS", lambda: resolve_action(raised, links, "carry-test-object"))
    error("STALE_BINDINGS", lambda: derive_annotations(raised, links, "carry-test-object"))
    raised_links = rebind_actions(raised, links)
    assert links.model_dump_json() == before
    old_action = resolve_action(lower, links, "carry-test-object")
    raised_action = resolve_action(raised, raised_links, "carry-test-object")
    assert old_action.instance_ids == raised_action.instance_ids
    assert old_action.component_ids == raised_action.component_ids
    assert raised_links.bindings_hash != links.bindings_hash
    new_artifacts = derive_annotations(raised, raised_links, "carry-test-object")
    assert [a.id for a in old_artifacts] == [a.id for a in new_artifacts]
    for old, new in zip(old_artifacts, new_artifacts):
        assert new.anchor.world_point_m[1] - old.anchor.world_point_m[1] == pytest.approx(.15)
        assert new.revision_id != old.revision_id
    assert actions_for_component(raised, raised_links, ids["tool"])[0].action_id == "carry-test-object"
    restored = service.align_ports(raised, "carrier-mount", parent_port_id="lower", configuration_id="lower")
    restored_links = rebind_actions(restored, raised_links)
    assert restored.engineering_hash == lower.engineering_hash
    assert restored_links.actions == links.actions
    assert restored_links.revision_id != links.revision_id
    error("STALE_BINDINGS", lambda: resolve_action(restored, links, "carry-test-object"))


@pytest.mark.parametrize("action", [
    ActionBinding(action_id="x", subsystem_id="missing"),
    ActionBinding(action_id="x", subsystem_id="carrier", instance_ids=("missing",)),
    ActionBinding(action_id="x", subsystem_id="carrier", joint_ids=("missing-joint",)),
    ActionBinding(action_id="x", subsystem_id="carrier", anchors=(BindingAnchor(id="x", instance_id="missing"),)),
])
def test_absent_subsystems_components_joints_and_anchors_rejected(assembly_case, action):
    _, lower, _ = assembly_case
    error("INVALID_BINDING", lambda: bind_actions(lower, competition_id="test", strategy_id="test", actions=(action,)))


def test_wrong_subsystem_and_missing_ports_rejected(assembly_case):
    _, lower, ids = assembly_case
    wrong = ActionBinding(action_id="x", subsystem_id="carrier", instance_ids=(ids["base"],))
    error("INVALID_BINDING", lambda: bind_actions(lower, competition_id="test", strategy_id="test", actions=(wrong,)))
    missing = ActionBinding(action_id="x", subsystem_id="carrier", anchors=(BindingAnchor(
        id="missing-port", instance_id=ids["tool"], port_id="missing"),))
    error("MISSING_PORT", lambda: bind_actions(lower, competition_id="test", strategy_id="test", actions=(missing,)))
    with pytest.raises(ValidationError):
        BindingAnchor(id="ambiguous", instance_id=ids["tool"], port_id="mount", local_point_m=(0, 1, 0))


def test_tampered_bindings_engineering_and_cross_design_rejected(assembly_case):
    service, lower, ids = assembly_case
    links = bindings_for(lower, ids)
    data = links.json_data()
    data["actions"][0]["anchors"][0]["worldPointM"] = [99, 99, 99]
    tampered = BindingSnapshot.model_validate(data)
    error("BINDINGS_HASH_MISMATCH", lambda: resolve_action(lower, tampered, "carry-test-object"))
    error("BINDINGS_HASH_MISMATCH", lambda: rebind_actions(lower, tampered))
    data = lower.json_data()
    data["assembly"]["configurationId"] = "tampered"
    error("REVISION_HASH_MISMATCH", lambda: resolve_action(AssemblyRevision.model_validate(data), links, "carry-test-object"))
    other = demo(service, design_id="other-design")
    error("WRONG_DESIGN", lambda: rebind_actions(other, links))


def test_duplicate_actions_and_anchors_rejected_and_order_is_canonical(assembly_case):
    _, lower, ids = assembly_case
    links = bindings_for(lower, ids)
    assert bind_actions(lower, competition_id=links.competition_id, strategy_id=links.strategy_id,
                        actions=reversed(links.definitions)) == links
    action = links.definitions[0]
    error("DUPLICATE_ID", lambda: bind_actions(lower, competition_id="test", strategy_id="test", actions=(action, action)))
    anchor = BindingAnchor(id="duplicate", instance_id=ids["tool"])
    bad = ActionBinding(action_id="x", subsystem_id="carrier", anchors=(anchor, anchor))
    error("DUPLICATE_ID", lambda: bind_actions(lower, competition_id="test", strategy_id="test", actions=(bad,)))


def test_joint_links_use_actual_moving_members_and_cannot_omit_a_dependent_child(assembly_case):
    _, lower, ids = assembly_case
    definitions = []
    for definition in lower.assembly.components:
        data = definition.json_data()
        if definition.id in ("tachyon_fixture_post", "tachyon_fixture_carrier"):
            for port in data["ports"]:
                if port["id"] in ("lower", "raised", "mount"):
                    port["kind"] = "shaft"
        definitions.append(ComponentDefinition.model_validate(data))
    service = AssemblyService(definitions)
    relationships = []
    for rel in lower.assembly.relationships:
        data = rel.json_data()
        if rel.id == "carrier-mount":
            data.update(kind="revolute", axis=[0, 0, 1], limits=[-.5, .5],
                        movingMemberIds=[ids["carrier"], ids["tool"]])
        relationships.append(Relationship.model_validate(data))
    def build(rels):
        return service.build(design_id=lower.assembly.design_id, recipe_id="original-joint-fixture", configuration_id="lower",
                             root_instance_id=ids["base"], instances=lower.assembly.instances,
                             subsystems=lower.assembly.subsystems, relationships=rels)
    revision = build(relationships)
    action = ActionBinding(action_id="inspect-joint", subsystem_id="carrier", joint_ids=("carrier-mount",))
    links = bind_actions(revision, competition_id="test", strategy_id="test", actions=(action,))
    assert resolve_action(revision, links, "inspect-joint").joint_ids == ("carrier-mount",)
    data = relationships[0].json_data()
    data["movingMemberIds"] = [ids["carrier"]]
    error("INVALID_JOINT_MEMBERS", lambda: build((Relationship.model_validate(data), relationships[1])))


def test_rebinding_rejects_a_removed_linked_component(assembly_case):
    service, lower, ids = assembly_case
    links = bind_actions(lower, competition_id="test", strategy_id="test", actions=(ActionBinding(
        action_id="inspect-tip", subsystem_id="carrier", instance_ids=(ids["tool"],)),))
    reduced = service.build(design_id=lower.assembly.design_id, recipe_id="intentionally-incomplete-fixture", configuration_id="reduced",
                            root_instance_id=ids["base"], instances=tuple(n for n in lower.assembly.instances if n.id != ids["tool"]),
                            subsystems=lower.assembly.subsystems, relationships=tuple(r for r in lower.assembly.relationships if r.id != "tool-mount"))
    error("INVALID_BINDING", lambda: rebind_actions(reduced, links))


def test_prepared_fixture_occurrences_render_matrices_and_rebound_port_annotations():
    # Same public API as the integration example; original metadata only, no CAD.
    part = ComponentDefinition.from_prepared(prepared_metadata(), qualified_operations=("assembly_placement",))
    port = part.ports[0]
    mate = RigidTransform.rotation((1, 0, 0), math.pi)
    child = port.frame.compose(mate).compose(port.frame.inverse())
    service = AssemblyService((part,))
    revision = service.build(
        design_id="original-fixture-demo", recipe_id="declared-fixture-attachment", configuration_id="first",
        root_instance_id="base", subsystems=(Subsystem(id="fixture", name="Original fixture attachment"),),
        instances=(ComponentInstance(id="base", component_id=part.id, subsystem_id="fixture"),
                   ComponentInstance(id="attached", component_id=part.id, subsystem_id="fixture", parent_id="base", transform=child)),
        relationships=(Relationship(id="mount", parent_instance_id="base", parent_port_id=port.id,
                                    child_instance_id="attached", child_port_id=port.id, mate_transform=mate),))
    links = bind_actions(revision, competition_id="fixture-demo", strategy_id="fixture-inspection", actions=(ActionBinding(
        action_id="inspect-attachment", subsystem_id="fixture", instance_ids=("attached",),
        anchors=(BindingAnchor(id="attachment", instance_id="attached", port_id=port.id),)),))
    assert len(world_transforms(revision.assembly)) == 2
    assert derive_annotations(revision, links, "inspect-attachment")[0].anchor.world_point_m == pytest.approx((.01, .02, .03))
    candidate = service.align_ports(revision, "mount", configuration_id="second",
                                    mate_transform=RigidTransform.rotation((0, 1, 0), math.pi))
    new_links = rebind_actions(candidate, links)
    assert candidate.engineering_hash != revision.engineering_hash
    assert candidate.assembly.instances != revision.assembly.instances
    assert resolve_action(candidate, new_links, "inspect-attachment").instance_ids == ("attached",)
    assert derive_annotations(candidate, new_links, "inspect-attachment")[0].anchor.world_point_m == pytest.approx((.01, .02, .03))
