"""Compile measured component ports into the existing assembly recipe contract.

This module creates no geometry. A part pack consists of current local catalog
identities and measured full attachment frames. All placements pass through
realization.build_pose/AssemblyService, including non-tree mechanism closure.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
import math

from .. import assemblies as A
from ..errors import TachyonError

T = A.RigidTransform


@dataclass(frozen=True)
class Part:
    component_id: str
    source_sha256: str
    catalog_fingerprint: str
    ports: dict[str, A.AttachmentPort]
    purpose: str


class RecipeBuilder:
    """A small authoring adapter; never an alternative placement/validation engine."""

    def __init__(self, recipe_id, alternative, parts):
        self.recipe_id, self.alternative, self.parts = recipe_id, alternative, parts
        self.instances, self.relationships, self.actions = [], [], []
        self.poses = {"lower": {}, "raised": {}}
        self.nominal_world = {}
        self.purposes = {}
        self.root = None

    def root_part(self, name, part, subsystem, world=T()):
        if self.root is not None:
            raise ValueError("Only one root is permitted")
        self.root, self.root_world = name, world
        self._instance(name, part, subsystem, None, world)
        return name

    def _instance(self, name, part, subsystem, parent, world):
        if name in self.nominal_world or part not in self.parts:
            raise ValueError("Duplicate instance or unavailable measured part")
        self.instances.append({"id": name, "componentId": self.parts[part].component_id,
                               "subsystemId": subsystem, **({"parentId": parent} if parent else {})})
        self.nominal_world[name] = (part, world)
        self.purposes[name] = self.parts[part].purpose

    def port(self, instance, port):
        part, world = self.nominal_world[instance]
        frame = self.parts[part].ports.get(port)
        if frame is None:
            raise TachyonError("MISSING_PORT", f"Measured port unavailable: {part}/{port}")
        return world.compose(frame.frame)

    def attached(self, name, part, subsystem, parent, parent_port, child_port, *,
                 mate=T(), kind="fixed", axis=(0., 0., 1.), limits=None,
                 lower=0., raised=0., joint_id=None):
        parent_frame = self.port(parent, parent_port)
        child = self.parts[part].ports.get(child_port)
        if child is None:
            raise TachyonError("MISSING_PORT", f"Measured port unavailable: {part}/{child_port}")
        motion = T.rotation(axis, lower) if kind == "revolute" else T.translation(*(v*lower for v in axis)) if kind == "prismatic" else T()
        world = parent_frame.compose(motion).compose(mate).compose(child.frame.inverse())
        self._instance(name, part, subsystem, parent, world)
        relation = {"id": joint_id or name + "-mount", "parentInstanceId": parent,
                    "parentPortId": parent_port, "childInstanceId": name, "childPortId": child_port,
                    "kind": kind, "mateTransform": mate.json_data()}
        self.instances[-1]["placementRelationshipId"] = relation["id"]
        if kind != "fixed":
            if limits is None:
                raise ValueError("A generated joint requires explicit limits")
            relation.update(axis=list(axis), limits=list(limits), movingMemberIds=[])
            self.poses["lower"][relation["id"]] = lower
            self.poses["raised"][relation["id"]] = raised
        self.relationships.append(relation)
        return name

    def attach_at(self, name, part, subsystem, parent, parent_port, child_port, world,
                  *, axial_stack_m=0., angular_tolerance=1e-5):
        """Fixed placement must coincide at a measured mate, or declared axial stack.

        This rejects arbitrary mesh locations disguised as attachment edges. A
        nonzero stack still needs its own real spacers/fasteners in robot BOM.
        """
        desired = world.compose(self.parts[part].ports[child_port].frame)
        mate = self.port(parent, parent_port).inverse().compose(desired)
        x, y, z = mate.point()
        angle = math.acos(max(-1., min(1., (mate.matrix[0]+mate.matrix[5]+mate.matrix[10]-1)/2)))
        if math.hypot(x, y) > 1e-5 or abs(z-axial_stack_m) > 1e-5 or angle > angular_tolerance:
            raise TachyonError("NON_MATING_PLACEMENT", "Generated fixed placement does not coincide with its measured mounting frames")
        return self.attached(name, part, subsystem, parent, parent_port, child_port, mate=mate)

    def constraint(self, identity, parent, parent_port, child, child_port, *, mate=T(),
                   kind="fixed", axis=(0., 0., 1.), limits=None, lower=0., raised=0.):
        rel = {"id": identity, "parentInstanceId": parent, "parentPortId": parent_port,
               "childInstanceId": child, "childPortId": child_port, "kind": kind, "mateTransform": mate.json_data()}
        if kind != "fixed":
            rel.update(axis=list(axis), limits=list(limits), movingMemberIds=[])
            self.poses["lower"][identity] = lower
            self.poses["raised"][identity] = raised
        self.relationships.append(rel)

    def bind(self, action_id, subsystem_id, members, joints=(), anchors=()):
        self.actions.append({"actionId": action_id, "subsystemId": subsystem_id,
                             "instanceIds": list(members), "jointIds": list(joints), "anchors": list(anchors)})

    def compile(self, *, reach, robot=None, edit_group=None):
        if self.root is None:
            raise ValueError("Generated recipe has no root")
        # Moving sets are derived from real parent membership, not caller flags.
        children = defaultdict(list)
        for node in self.instances:
            if node.get("parentId"):
                children[node["parentId"]].append(node["id"])
        def descendants(key):
            result, pending = set(), [key]
            while pending:
                item = pending.pop()
                if item in result:
                    raise ValueError("Invalid generated placement tree")
                result.add(item); pending.extend(children[item])
            return sorted(result)
        for rel in self.relationships:
            if rel["kind"] != "fixed":
                rel["movingMemberIds"] = descendants(rel["childInstanceId"])
        roles = defaultdict(set)
        for node in self.instances:
            roles[node["subsystemId"]].add(node["componentId"])
        used = {node["componentId"] for node in self.instances}
        result = {"id": self.recipe_id, "alternative": self.alternative,
                  "roleComponentIds": {key: sorted(values) for key, values in roles.items()},
                  "portFrames": {p.component_id: {"sourceSha256": p.source_sha256,
                      "catalogFingerprint": p.catalog_fingerprint,
                      "ports": [port.json_data() for port in p.ports.values()]}
                      for p in self.parts.values() if p.component_id in used},
                  "template": {"rootInstanceId": self.root, "rootTransform": self.root_world.json_data(),
                      "instances": self.instances,
                      "subsystems": [{"id": key, "name": key.replace('_', ' ').title()} for key in roles],
                      "relationships": self.relationships},
                  "actions": self.actions,
                  "configurations": {key: {"jointPositions": positions, "reach": reach[key]} for key, positions in self.poses.items()}}
        if robot is not None:
            result["robot"] = robot
        if edit_group is not None:
            result["editGroup"] = edit_group
        return result
