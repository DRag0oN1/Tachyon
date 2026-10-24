"""Revision-exact strategy links and original annotations from assembly anchors.

Link validity only means the named components exist. It establishes no handling,
reach, scoring or motion capability. Rebinding is explicit after engineering edits.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import Field, model_validator

from .assemblies import (
    AssemblyRevision, Record, _fail, _port, _unique, content_hash, stable_id,
    validate_revision, world_transforms,
)
from .models import Vector3


class BindingAnchor(Record):
    id: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)
    port_id: str | None = None
    local_point_m: Vector3 = (0., 0., 0.)

    @model_validator(mode="after")
    def one_anchor_frame(self):
        if self.port_id is not None and self.local_point_m != (0., 0., 0.):
            raise ValueError("Choose a measured port or a component-local point")
        return self


class ActionBinding(Record):
    action_id: str = Field(min_length=1)
    subsystem_id: str = Field(min_length=1)
    instance_ids: tuple[str, ...] = ()  # empty resolves the subsystem's actual members
    joint_ids: tuple[str, ...] = ()
    anchors: tuple[BindingAnchor, ...] = ()


class WorldAnchor(Record):
    id: str
    instance_id: str
    component_id: str
    port_id: str | None
    world_point_m: Vector3


class BoundAction(Record):
    action_id: str
    subsystem_id: str
    instance_ids: tuple[str, ...]
    component_ids: tuple[str, ...]
    joint_ids: tuple[str, ...]
    anchors: tuple[WorldAnchor, ...]
    # No task capability has been qualified by this graph/binding layer.
    capability_status: Literal["unsupported"] = "unsupported"
    capability_reason: str = "Component links do not qualify competition task or motion support"


class BindingSnapshot(Record):
    schema_version: Literal[1] = 1
    design_id: str
    competition_id: str
    strategy_id: str
    revision_id: str
    engineering_hash: str
    bindings_hash: str
    definitions: tuple[ActionBinding, ...]
    actions: tuple[BoundAction, ...]


class Annotation(Record):
    id: str
    action_id: str
    subsystem_id: str
    revision_id: str
    engineering_hash: str
    bindings_hash: str
    anchor: WorldAnchor
    dependency_ids: tuple[str, ...]
    label: str = "Assembly anchor; task capability unsupported"


def _payload(snapshot):
    data = snapshot.json_data()
    data.pop("bindingsHash")
    return data


def bind_actions(revision: AssemblyRevision, *, competition_id: str, strategy_id: str,
                 actions: Iterable[ActionBinding]) -> BindingSnapshot:
    validate_revision(revision)
    if not competition_id.strip() or not strategy_id.strip():
        _fail("INVALID_STRATEGY_CONTEXT", "Bindings require a competition and strategy identity")
    actions = tuple(sorted(actions, key=lambda action: action.action_id))
    if len({action.action_id for action in actions}) != len(actions):
        _fail("DUPLICATE_ID", "An action can have only one binding")
    nodes = {node.id: node for node in revision.assembly.instances}
    joints = {rel.id: rel for rel in revision.assembly.relationships if rel.kind != "fixed"}
    world, resolved = world_transforms(revision.assembly), []
    normalized = []
    for action in actions:
        members = {node.id for node in nodes.values() if node.subsystem_id == action.subsystem_id}
        if not members:
            _fail("INVALID_BINDING", "Action refers to an absent subsystem")
        selected = tuple(sorted(action.instance_ids or members))
        if len(set(selected)) != len(selected) or not set(selected) <= members:
            _fail("INVALID_BINDING", "Action members must exist in its named subsystem")
        if len(set(action.joint_ids)) != len(action.joint_ids):
            _fail("DUPLICATE_ID", "Duplicate binding joint identity")
        for joint_id in action.joint_ids:
            joint = joints.get(joint_id)
            if joint is None or not set(joint.moving_member_ids) & set(selected):
                _fail("INVALID_BINDING", "Action joint must exist and move a bound component")
        _unique(action.anchors, "anchor")
        anchors = []
        for anchor in sorted(action.anchors, key=lambda anchor: anchor.id):
            if anchor.instance_id not in selected:
                _fail("INVALID_BINDING", "Annotation anchor must belong to a bound component")
            point = anchor.local_point_m
            if anchor.port_id is not None:
                _, port = _port(revision.assembly, anchor.instance_id, anchor.port_id)
                point = port.frame.point()
            anchors.append(WorldAnchor(id=stable_id("anchor", revision.assembly.design_id, competition_id,
                                                   strategy_id, action.action_id, anchor.id),
                                       instance_id=anchor.instance_id,
                                       component_id=nodes[anchor.instance_id].component_id,
                                       port_id=anchor.port_id,
                                       world_point_m=world[anchor.instance_id].point(point)))
        definition = action.json_data()
        # Preserve empty instanceIds as "follow this subsystem" when rederived.
        definition["instanceIds"] = sorted(action.instance_ids)
        definition["jointIds"] = sorted(action.joint_ids)
        definition["anchors"] = sorted(definition["anchors"], key=lambda anchor: anchor["id"])
        normalized.append(ActionBinding.model_validate(definition))
        resolved.append(BoundAction(action_id=action.action_id, subsystem_id=action.subsystem_id,
                                    instance_ids=selected,
                                    component_ids=tuple(sorted({nodes[key].component_id for key in selected})),
                                    joint_ids=tuple(sorted(action.joint_ids)), anchors=tuple(anchors)))
    snapshot = BindingSnapshot(design_id=revision.assembly.design_id, competition_id=competition_id,
                               strategy_id=strategy_id, revision_id=revision.id,
                               engineering_hash=revision.engineering_hash, bindings_hash="",
                               definitions=tuple(normalized), actions=tuple(resolved))
    return BindingSnapshot.model_validate({**snapshot.json_data(), "bindingsHash": content_hash(_payload(snapshot))})


def _current(revision: AssemblyRevision, bindings: BindingSnapshot):
    validate_revision(revision)
    if (bindings.design_id, bindings.revision_id, bindings.engineering_hash) != (
            revision.assembly.design_id, revision.id, revision.engineering_hash):
        _fail("STALE_BINDINGS", "Binding queries require the exact assembly revision")
    expected = bind_actions(revision, competition_id=bindings.competition_id,
                            strategy_id=bindings.strategy_id, actions=bindings.definitions)
    if bindings != expected:
        _fail("BINDINGS_HASH_MISMATCH", "Binding content or derived anchors have changed")


def rebind_actions(revision: AssemblyRevision, previous: BindingSnapshot) -> BindingSnapshot:
    """Explicitly rederive valid intent against a changed assembly of the same design."""
    if previous.design_id != revision.assembly.design_id:
        _fail("WRONG_DESIGN", "Cannot carry strategy bindings into another design")
    if content_hash(_payload(previous)) != previous.bindings_hash:
        _fail("BINDINGS_HASH_MISMATCH", "Cannot rebind tampered strategy definitions")
    return bind_actions(revision, competition_id=previous.competition_id,
                        strategy_id=previous.strategy_id, actions=previous.definitions)


def resolve_action(revision: AssemblyRevision, bindings: BindingSnapshot, action_id: str) -> BoundAction:
    _current(revision, bindings)
    action = next((action for action in bindings.actions if action.action_id == action_id), None)
    if action is None:
        _fail("INVALID_BINDING", "Unknown strategy action")
    return action


def actions_for_component(revision: AssemblyRevision, bindings: BindingSnapshot,
                          instance_id: str) -> tuple[BoundAction, ...]:
    _current(revision, bindings)
    if instance_id not in {node.id for node in revision.assembly.instances}:
        _fail("INVALID_BINDING", "Unknown component instance")
    return tuple(action for action in bindings.actions if instance_id in action.instance_ids)


def derive_annotations(revision: AssemblyRevision, bindings: BindingSnapshot,
                       action_id: str) -> tuple[Annotation, ...]:
    action = resolve_action(revision, bindings, action_id)
    dependencies = tuple(sorted(set((*action.instance_ids, *action.component_ids, *action.joint_ids))))
    return tuple(Annotation(id=anchor.id, action_id=action.action_id, subsystem_id=action.subsystem_id,
                            revision_id=revision.id, engineering_hash=revision.engineering_hash,
                            bindings_hash=bindings.bindings_hash, anchor=anchor,
                            dependency_ids=dependencies) for anchor in action.anchors)
