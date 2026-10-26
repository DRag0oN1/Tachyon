"""Private recipe realization of the pinned eb1265c architecture proposals.

Only Catalog.prepared receipts and current RightsPolicy decisions supply component
identity/qualification. Recipes supply measured full frames for *existing* ports,
an explicit placement/attachment graph, and scalar joint positions. They cannot
grant rights, promote inspection references, or certify robot/task completeness.

Private input: settings.data_dir/catalog/assembly-recipes.json. RecipeBook is the
strict, bounded schema (RecipeBook.model_json_schema(by_alias=True)). Instances
have no caller transforms; rootTransform is shared by every configuration. A
configuration's reach names an ActionBinding anchor and its expected world point
in metres/Y-up; it is checked against the derived point, never treated as proof
of physical reach. Joint positions are metres (prismatic) or radians (revolute).

RealizationService(settings, store, lan=False) is the app integration entry point.
Persistence uses Store.connect and its own table, without changing Store or the
manual assembly-draft lifecycle. All returned components are full public prepared
receipts, not ComponentDefinitions. No source geometry is written here.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import dataclass
import json
import math
from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator, model_serializer

from . import assemblies as A, bindings as B, strategy_runtime as SR
from .cad.catalog import Catalog
from .config import Settings
from .errors import TachyonError
from .models import Model, Operation, PreparedComponent, Vector3
from .store import Store
from .robot_qualification import RobotContract, qualify_robot


MAX_RECIPE_BYTES = 1024 * 1024
MAX_UNDO = 64
Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]
Evidence = Annotated[str, Field(min_length=1, max_length=4096, pattern=r"\S")]
Role = Literal["chassis", "drive", "pin_intake", "pin_transfer", "scorer", "cup_cradle", "stack_interface"]
Configuration = Literal["lower", "raised"]


class MeasuredPorts(Model):
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    catalog_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    ports: tuple[A.AttachmentPort, ...] = Field(min_length=1, max_length=128)


class CoupledJoint(Model):
    joint_id: Identifier
    ratio: float
    offset: float = 0.


class EditGroup(Model):
    id: Identifier
    driver_joint_id: Identifier
    members: tuple[Identifier, ...] = Field(min_length=1, max_length=512)
    coupling: tuple[CoupledJoint, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.members)) != len(self.members) or len({c.joint_id for c in self.coupling}) != len(self.coupling):
            raise ValueError("Coupled group members and joints must be unique")
        if self.driver_joint_id not in {c.joint_id for c in self.coupling}:
            raise ValueError("Coupled group must declare its driver joint")
        return self


class TemplateInstance(Model):
    id: Identifier
    component_id: Identifier
    subsystem_id: Role
    parent_id: Identifier | None = None
    placement_relationship_id: Identifier | None = None


class AssemblyTemplate(Model):
    root_instance_id: Identifier
    root_transform: A.RigidTransform = A.RigidTransform()
    instances: tuple[TemplateInstance, ...] = Field(min_length=1, max_length=512)
    subsystems: tuple[A.Subsystem, ...] = Field(min_length=1, max_length=7)
    relationships: tuple[A.Relationship, ...] = Field(max_length=1024)


class Reach(Model):
    action_id: Identifier
    anchor_id: Identifier
    world_point_m: Vector3
    evidence: Evidence
    tolerance_m: float = Field(default=1e-5, gt=0, le=.001)


class Pose(Model):
    joint_positions: dict[Identifier, float] = Field(max_length=1024)
    reach: Reach | None = None


class Recipe(Model):
    id: Identifier
    alternative: Literal["A", "B"]
    role_component_ids: dict[Role, Annotated[tuple[Identifier, ...], Field(min_length=1, max_length=128)]] = Field(max_length=7)
    port_frames: dict[Identifier, MeasuredPorts] = Field(max_length=128)
    template: AssemblyTemplate
    actions: tuple[B.ActionBinding, ...] = Field(default=(), max_length=32)
    configurations: dict[Configuration, Pose] = Field(min_length=1, max_length=2)
    robot: RobotContract | None = None
    edit_group: EditGroup | None = None

    @model_serializer(mode="wrap")
    def preserve_existing_recipe_identity(self, handler):
        data = handler(self)
        # New optional contracts must not change persisted v1 recipe hashes.
        for key in ("robot", "editGroup", "edit_group"):
            if data.get(key) is None:
                data.pop(key, None)
        for frames in data.get("portFrames", data.get("port_frames", {})).values():
            for key in ("catalogFingerprint", "catalog_fingerprint"):
                if frames.get(key) is None:
                    frames.pop(key, None)
        return data

    @model_validator(mode="after")
    def graph_contract(self):
        t = self.template
        if self.robot is not None and self.alternative != self.robot.architecture:
            raise ValueError("Robot hardware contract must describe this architecture alternative")
        for records in (t.instances, t.subsystems, t.relationships):
            if len({r.id for r in records}) != len(records):
                raise ValueError("Duplicate template identity")
        if len({a.action_id for a in self.actions}) != len(self.actions):
            raise ValueError("Duplicate action binding")
        nodes = {n.id: n for n in t.instances}
        root = nodes.get(t.root_instance_id)
        if root is None or root.parent_id is not None:
            raise ValueError("An existing unparented root is required")
        if {s.id for s in t.subsystems} != {n.subsystem_id for n in nodes.values()}:
            raise ValueError("Subsystems must exactly describe instance membership")
        if {n.subsystem_id for n in nodes.values()} != set(self.role_component_ids):
            raise ValueError("Role mapping must exactly describe template subsystems")
        for role, ids in self.role_component_ids.items():
            if len(set(ids)) != len(ids) or set(ids) != {n.component_id for n in nodes.values() if n.subsystem_id == role}:
                raise ValueError("Role components must exactly name that subsystem's parts")
        if set(self.port_frames) - {n.component_id for n in nodes.values()}:
            raise ValueError("Unused component frames are not allowed")
        for ports in self.port_frames.values():
            if len({p.id for p in ports.ports}) != len(ports.ports):
                raise ValueError("Duplicate measured port identity")
            if any(p.frame_basis != "measured" for p in ports.ports):
                raise ValueError("Full measured port frames are required")
        joints = {r.id for r in t.relationships if r.kind != "fixed"}
        if "lower" not in self.configurations:
            raise ValueError("A lower baseline configuration is required")
        for pose in self.configurations.values():
            if set(pose.joint_positions) != joints:
                raise ValueError("Each configuration must specify every nonfixed joint, and no fixed joints")
        return self


class RecipeBook(Model):
    schema_version: Literal[1] = 1
    recipes: tuple[Recipe, ...] = Field(max_length=2)

    @model_validator(mode="after")
    def unique(self):
        if len({r.id for r in self.recipes}) != len(self.recipes) or len({r.alternative for r in self.recipes}) != len(self.recipes):
            raise ValueError("One uniquely identified recipe per architecture alternative")
        return self


def _bounded_json(raw):
    if len(raw) > MAX_RECIPE_BYTES:
        raise ValueError("Recipe byte limit")
    value = SR.decode_json(raw)
    pending, count = [(value, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if depth > 20 or count > 50000:
            raise ValueError("Recipe complexity limit")
        if isinstance(node, str) and len(node) > 4096:
            raise ValueError("Recipe string limit")
        if isinstance(node, dict):
            if any(len(key) > 100 for key in node):
                raise ValueError("Recipe key limit")
            pending.extend((v, depth + 1) for v in node.values())
        elif isinstance(node, list):
            pending.extend((v, depth + 1) for v in node)
    return value


def load_recipe(settings, alternative):
    path = settings.local_path("catalog/assembly-recipes.json", must_exist=False)
    if not path.is_file():
        return None
    try:
        with path.open("rb") as stream:
            value = _bounded_json(stream.read(MAX_RECIPE_BYTES + 1))
        # Strict JSON validation retains JSON arrays for tuple fields but rejects
        # string/bool numbers, unexpected fields, and caller qualification flags.
        book = RecipeBook.model_validate_json(json.dumps(value), strict=True)
    except (OSError, ValueError, TypeError, RecursionError):
        raise TachyonError("INVALID_ASSEMBLY_RECIPES", "The private recipe file fails the bounded assembly recipe schema") from None
    return next((r for r in book.recipes if r.alternative == alternative), None)


@dataclass(frozen=True)
class ArchitectureContext:
    proposal: dict
    spec: dict

    @property
    def roles(self):
        return tuple(s["id"] for s in self.proposal["subsystems"])


def architecture_context(root, architecture_id):
    """Verify the fixed public manifests, proposal and real StrategySpec, offline.

    Geometry realization does not depend on Torch, inference, checkpoint files or
    the episode archive. None of those can substitute for this pinned design.
    """
    try:
        handoff = SR._json_file(root, SR.HANDOFF / "manifest.json", SR.MANIFEST_PINS[SR.HANDOFF / "manifest.json"])
        design = SR._json_file(root, SR.HANDOFF / "design/manifest.json", SR.MANIFEST_PINS[SR.HANDOFF / "design/manifest.json"])
        proposals = SR._json_file(root, SR.PROPOSALS, handoff["files"]["design/architecture-proposals.json"])
        spec = SR._json_file(root, SR.SPEC, handoff["files"]["strategy-spec-v2.json"])
        if (design["artifacts"]["architecture-proposals.json"]["sha256"] != handoff["files"]["design/architecture-proposals.json"]
                or design["strategyId"] != SR.SPEC_ID or spec["id"] != SR.SPEC_ID
                or spec["competition"]["id"] != SR.COMPETITION_ID
                or design["strategySpecSha256"] != SR.canonical_hash(spec)
                or design["completeRobot"] is not False or design["cadGenerated"] is not False
                or [p["id"] for p in proposals] != design["architectureIDs"]
                or {p["alternative"] for p in proposals} != {"A", "B"}
                or any(p["strategyId"] != spec["id"] or p["completeRobot"] is not False
                       or p["source"]["strategySpecSha256"] != SR.canonical_hash(spec) for p in proposals)):
            raise ValueError("Architecture provenance mismatch")
    except (SR.StrategyRuntimeError, OSError, ValueError, KeyError, TypeError, RecursionError):
        raise TachyonError("ARCHITECTURE_DATASET_UNVERIFIED", "The fixed eb1265c architecture handoff is missing or fails manifest checksum verification", 503) from None
    proposal = next((p for p in proposals if p["id"] == architecture_id), None)
    if proposal is None:
        raise TachyonError("ARCHITECTURE_NOT_FOUND", "Choose an architecture ID from the verified public design bridge", 404)
    return ArchitectureContext(proposal, spec)


def missing(role, code, message):
    return {"role": role, "code": code, "message": message}


class QualificationBlocked(Exception):
    def __init__(self, reasons):
        self.reasons = reasons


def _quality_reasons(receipt):
    reasons = []
    if receipt.reference_only:
        reasons.append(("REFERENCE_ONLY_COMPONENT", "Inspection references cannot become generated assembly parts"))
    q = A.GeometryValidation.model_validate(receipt.geometry_validation)
    if (q.status != "valid" or q.native_brep_valid is not True or q.qualified_for_robot_generation is not True
            or q.invalid_component_instances or q.invalid_definition_count != 0):
        reasons.append(("GEOMETRY_NOT_QUALIFIED", "Current source geometry must have valid BRep quality and assembly-generation qualification"))
    if receipt.geometry_class in ("conceptual", "placeholder"):
        reasons.append(("NON_COMPONENT_GEOMETRY", "Conceptual and placeholder geometry cannot substitute for real components"))
    return reasons


def _measured_definition(receipt, frames):
    if frames is None:
        raise TachyonError("MISSING_PORT_FRAMES", f"Measured full frames for existing ports are missing: {receipt.id}")
    if frames.source_sha256 != receipt.source_sha256:
        raise TachyonError("STALE_PORT_FRAMES", "Measured port frames refer to a different component source")
    if frames.catalog_fingerprint is not None and frames.catalog_fingerprint != receipt.catalog_fingerprint:
        raise TachyonError("STALE_PORT_FRAMES", "Measured frames no longer identify the same selected source component")
    if getattr(receipt, "source_selection", None) is not None and frames.catalog_fingerprint is None:
        raise TachyonError("STALE_PORT_FRAMES", "Selected source definitions require component-fingerprint-bound measured frames")
    registered = {p.id: p for p in receipt.ports}
    for port in frames.ports:
        actual = registered.get(port.id)
        if actual is None:
            raise TachyonError("MISSING_PORT", f"Measured port is absent from the current component: {receipt.id}/{port.id}")
        if (port.kind != actual.kind or any(abs(a - b) > 1e-8 for a, b in zip(port.frame.point(), actual.position_m))
                or any(abs(a - b) > 1e-8 for a, b in zip(port.frame.matrix[8:11], actual.axis))):
            raise TachyonError("PORT_FRAME_MISMATCH", "Measured full frames must preserve the existing port's kind, origin and +Z axis")
    definition = A.ComponentDefinition.from_prepared(receipt, ports=frames.ports, qualified_operations=("assembly_placement",))
    # Display context can change between loopback and a separately authorized
    # LAN client. Engineering identity describes the rechecked assembly use.
    return definition.model_copy(update={"declared_use": "assembly_placement"})


def qualified_catalog(settings, recipe, *, lan=False):
    """Return current definitions AND complete public receipts; never trust flags."""
    try:
        catalog = Catalog(settings)
    except TachyonError as error:
        raise QualificationBlocked([missing("catalog", error.code, error.message)]) from None
    definitions, public, reasons = [], [], []
    roles = {}
    if recipe:
        for role, ids in recipe.role_component_ids.items():
            for key in ids:
                roles.setdefault(key, []).append(role)
    else:
        roles = {c.id: ["catalog"] for c in catalog.manifest.components}
    for key, member_roles in sorted(roles.items()):
        component = next((c for c in catalog.manifest.components if c.id == key), None)
        problems = []
        if component is None:
            problems.append(("MISSING_COMPONENT", f"Required catalog component is missing: {key}"))
        else:
            # Inspect these separately so reference-only, missing ports and rights
            # gaps remain visible even if another qualification also fails.
            if component.reference_only:
                problems.append(("REFERENCE_ONLY_COMPONENT", f"{key}: Inspection references cannot become generated assembly parts"))
            if not component.ports:
                problems.append(("MISSING_PORT", f"{key} has no registered attachment ports"))
            try:
                catalog.policy.require(component.source_sha256, [Operation.assembly_placement])
            except TachyonError as error:
                problems.append((error.code, f"{key}: {error.message}"))
            except OSError:
                problems.append(("RIGHTS_EVIDENCE_UNREADABLE", "Current assembly-placement evidence cannot be read"))
            try:
                prepared = dict(catalog.prepared(component, lan=lan))
                prepared.pop("qualifiedOperations", None)
                receipt = PreparedComponent.model_validate(prepared)
                problems.extend((code, f"{key}: {message}") for code, message in _quality_reasons(receipt))
                if not problems and recipe:
                    definitions.append(_measured_definition(receipt, recipe.port_frames.get(key)))
                    # Full PreparedComponent JSON contains bounds, hierarchy,
                    # mesh URL/hash and source metadata needed by the renderer.
                    public.append(receipt.json_data())
            except TachyonError as error:
                problems.append((error.code, error.message))
            except (OSError, ValueError, TypeError):
                problems.append(("INVALID_RECEIPT", "Current prepared component metadata cannot be qualified"))
        reasons.extend(missing(role, code, message) for role in member_roles for code, message in problems)
    if reasons:
        raise QualificationBlocked(_dedupe(reasons))
    return A.AssemblyService(definitions), public


def _dedupe(reasons):
    return [dict(zip(("role", "code", "message"), row)) for row in dict.fromkeys(tuple(r[k] for k in ("role", "code", "message")) for r in reasons)]


def _check_actions(context, recipe):
    names = set(context.spec["behavior"]["inference"]["actionNames"])
    intent = {}
    for action in context.proposal["bindingIntent"]["actions"]:
        # Mechanical-requirement support references encode their action name as
        # sourceValue; observed behavior references carry an explicit action.
        name = action.get("action", action.get("sourceValue"))
        if isinstance(name, str) and name in names:
            intent.setdefault(name, set()).update(action["subsystemIDs"])
    for action in recipe.actions:
        if action.action_id not in names or action.subsystem_id not in intent.get(action.action_id, set()):
            raise TachyonError("INVALID_STRATEGY_BINDING", "Recipe actions must name a real StrategySpec action and one of its proposed subsystems")


def build_pose(service, recipe, design_id, configuration_id, parent=None):
    pose = recipe.configurations.get(configuration_id)
    if pose is None:
        raise TachyonError("UNSUPPORTED_CONFIGURATION", "This recipe does not register the requested joint configuration")
    relationships = []
    for rel in recipe.template.relationships:
        data = rel.json_data()
        if rel.kind != "fixed":
            data["position"] = pose.joint_positions[rel.id]
        relationships.append(A.Relationship.model_validate(data))
    nodes = {n.id: n for n in recipe.template.instances}
    placed = {}
    pending = dict(nodes)
    while pending:
        available = [n for n in pending.values() if n.parent_id is None or n.parent_id in placed]
        if not available:
            raise TachyonError("INVALID_PLACEMENT_HIERARCHY", "Template parents contain a cycle or missing reference")
        for node in available:
            transform = recipe.template.root_transform
            if node.parent_id is None and node.id != recipe.template.root_instance_id:
                raise TachyonError("INVALID_PLACEMENT_HIERARCHY", "Only the declared root may be unparented")
            if node.parent_id is not None:
                mates = [r for r in relationships if r.parent_instance_id == node.parent_id and r.child_instance_id == node.id]
                if node.placement_relationship_id is not None:
                    mates = [r for r in mates if r.id == node.placement_relationship_id]
                if len(mates) != 1:
                    raise TachyonError("MISSING_TREE_RELATIONSHIP", f"Placement child needs exactly one declared parent mate: {node.id}")
                rel = mates[0]
                parent_def = service._components.get(nodes[node.parent_id].component_id)
                child_def = service._components.get(node.component_id)
                if parent_def is None or child_def is None:
                    raise TachyonError("MISSING_COMPONENT", "A template component is unavailable")
                pp = next((p for p in parent_def.ports if p.id == rel.parent_port_id), None)
                cp = next((p for p in child_def.ports if p.id == rel.child_port_id), None)
                if pp is None or cp is None:
                    raise TachyonError("MISSING_PORT", f"A declared relationship port is unavailable: {rel.id}")
                transform = pp.frame.compose(rel.offset()).compose(cp.frame.inverse())
            placed[node.id] = A.ComponentInstance(id=node.id, component_id=node.component_id, subsystem_id=node.subsystem_id,
                                                   parent_id=node.parent_id, transform=transform)
            del pending[node.id]
    # AssemblyService checks all non-tree constraints too. Sequentially editing
    # individual joints would spuriously open coupled loops between updates.
    revision = service.build(design_id=design_id, recipe_id=recipe.id, configuration_id=configuration_id,
                             root_instance_id=recipe.template.root_instance_id, instances=placed.values(),
                             subsystems=recipe.template.subsystems, relationships=relationships)
    return A._revision(revision.assembly, parent) if parent else revision


def _links(context, recipe, revision):
    return B.bind_actions(revision, competition_id=context.spec["competition"]["id"],
                          strategy_id=context.spec["id"], actions=recipe.actions)


def _reach(recipe, revision, links):
    declaration = recipe.configurations[revision.assembly.configuration_id].reach
    if declaration is None:
        return None
    action = next((a for a in links.definitions if a.action_id == declaration.action_id), None)
    anchor = next((a for a in action.anchors if a.id == declaration.anchor_id), None) if action else None
    if anchor is None:
        raise TachyonError("INVALID_REACH_ANCHOR", "Configuration reach must name an existing bound action anchor")
    resolved = B.resolve_action(revision, links, action.action_id)
    anchor_id = A.stable_id("anchor", revision.assembly.design_id, links.competition_id, links.strategy_id, action.action_id, anchor.id)
    world = next(a for a in resolved.anchors if a.id == anchor_id)
    if math.dist(world.world_point_m, declaration.world_point_m) > declaration.tolerance_m:
        raise TachyonError("REACH_ANCHOR_MISMATCH", "Declared pose reach does not match the recomputed assembly anchor")
    return {"configurationId": revision.assembly.configuration_id, "actionId": action.action_id,
            "anchorId": world.id, "instanceId": anchor.instance_id, "worldPointM": list(world.world_point_m),
            "heightM": world.world_point_m[1], "evidence": declaration.evidence,
            "revisionId": revision.id, "engineeringHash": revision.engineering_hash,
            "capabilityStatus": "unverified", "basis": "Derived assembly anchor; physical task reach unverified"}


def _annotations(revision, links):
    """Include placement ancestors and moving joints as annotation dependencies."""
    nodes = {n.id: n for n in revision.assembly.instances}
    result = []
    for action in links.actions:
        for annotation in B.derive_annotations(revision, links, action.action_id):
            dependencies = set(annotation.dependency_ids)
            node = nodes[annotation.anchor.instance_id]
            while node:
                dependencies.update((node.id, node.component_id))
                dependencies.update(r.id for r in revision.assembly.relationships if r.child_instance_id == node.id)
                node = nodes.get(node.parent_id)
            result.append(annotation.model_copy(update={"dependency_ids": tuple(sorted(dependencies))}).json_data())
    return result


def edit_qualification(service, context, recipe, design_id):
    """Qualify the two discrete endpoint poses, not continuous motion or hardware."""
    if set(recipe.configurations) != {"lower", "raised"}:
        return False, [missing("scorer", "TWO_POSES_REQUIRED", "Edits require both lower and raised joint configurations")]
    try:
        revisions = [build_pose(service, recipe, design_id, key) for key in ("lower", "raised")]
        links = [_links(context, recipe, revision) for revision in revisions]
        reaches = [_reach(recipe, r, b) for r, b in zip(revisions, links)]
        changed = {key for key, value in recipe.configurations["lower"].joint_positions.items()
                   if abs(value - recipe.configurations["raised"].joint_positions[key]) > 1e-9}
        worlds = [A.world_transforms(r.assembly) for r in revisions]
        if not changed or worlds[0] == worlds[1]:
            raise TachyonError("DISTINCT_JOINT_POSES_REQUIRED", "Two names or static mounts do not establish different mechanism joint poses")
        if (not all(reaches) or (reaches[0]["actionId"], reaches[0]["anchorId"]) != (reaches[1]["actionId"], reaches[1]["anchorId"])
                or math.dist(reaches[0]["worldPointM"], reaches[1]["worldPointM"]) <= 1e-8):
            raise TachyonError("DISTINCT_REACH_REQUIRED", "Two poses need distinct recomputed points for the same mechanism anchor")
        action = next(a for a in recipe.actions if a.action_id == reaches[0]["actionId"])
        moving_anchor_joints = {r.id for r in revisions[0].assembly.relationships if reaches[0]["instanceId"] in r.moving_member_ids}
        if action.subsystem_id != "scorer" or not changed.intersection(action.joint_ids, moving_anchor_joints):
            raise TachyonError("SCORER_JOINT_BINDING_REQUIRED", "The reach anchor must belong to a scorer action bound to a changing joint")
        selected = next(a for a in links[0].actions if a.action_id == action.action_id)
        affected = {member for r in revisions[0].assembly.relationships if r.id in changed for member in r.moving_member_ids}
        if recipe.edit_group is None:
            if not changed.issubset(set(action.joint_ids) & moving_anchor_joints):
                raise TachyonError("EDIT_SCOPE_VIOLATION", "Every changing joint must be bound to the scoring action and move its reach anchor")
            if not affected.issubset(selected.instance_ids):
                raise TachyonError("EDIT_SCOPE_VIOLATION", "The height edit must not move instances outside the scoring action's declared members")
        else:
            group = recipe.edit_group
            nodes = {node.id: node for node in revisions[0].assembly.instances}
            joint_ids = {item.joint_id for item in group.coupling}
            if (not changed.issubset(joint_ids) or not joint_ids.issubset(action.joint_ids)
                    or affected != set(group.members)
                    or any(nodes[member].subsystem_id not in {"scorer", "cup_cradle", "stack_interface"} for member in group.members)):
                raise TachyonError("EDIT_SCOPE_VIOLATION", "Coupled edits must name exactly the affected scoring mechanism and carried members")
            for pose in recipe.configurations.values():
                driver = pose.joint_positions[group.driver_joint_id]
                if any(abs(pose.joint_positions[item.joint_id] - (item.ratio*driver+item.offset)) > 1e-8 for item in group.coupling):
                    raise TachyonError("INVALID_JOINT_COUPLING", "Every endpoint must satisfy the declared mechanism coupling")
        if reaches[1]["heightM"] <= reaches[0]["heightM"] + 1e-8:
            raise TachyonError("RAISED_HEIGHT_REQUIRED", "The raised configuration must place the same tool anchor above the lower configuration in metres/Y-up")
        for revision, binding in zip(revisions, links):
            _annotations(revision, binding)
    except TachyonError as error:
        return False, [missing("scorer", error.code, error.message)]
    except (ValueError, KeyError):
        return False, [missing("scorer", "INVALID_JOINT_CONFIGURATION", "A declared joint pose fails its limits or metadata validation")]
    return True, []


def _plan(context, recipe):
    return {"alternative": context.proposal["alternative"], "requiredRoles": list(context.roles),
            "subsystems": context.proposal["subsystems"], "requirements": context.proposal["requirements"],
            "attachmentAndJointIntents": context.proposal["attachmentAndJointIntents"],
            "qualificationRequired": context.proposal["qualificationRequired"],
            "roleComponentIds": recipe.json_data()["roleComponentIds"] if recipe else {},
            "recipeId": recipe.id if recipe else None}


def _role_gaps(context, recipe):
    return [missing(role, "REQUIRED_ROLE_UNREALIZED", f"No qualified component recipe supplies the required {role} subsystem")
            for role in context.roles if recipe is None or role not in recipe.role_component_ids]


def _empty(design_id, context, recipe, reasons):
    return {"designId": design_id, "architectureId": context.proposal["id"], "strategyId": context.spec["id"],
            "status": "blocked", "missing": _dedupe([*_role_gaps(context, recipe), *reasons]), "canEdit": False,
            "revisionId": None, "accepted": None, "candidate": None, "bindings": None, "candidateBindings": None,
            "previous": None, "previousBindings": None, "worldTransforms": {}, "candidateWorldTransforms": {},
            "components": [], "annotations": [], "candidateAnnotations": [],
            "qualification": {"completeRobot": False, "graphValid": False, "capabilityStatus": "unverified",
                              "hardwareQualified": False, "physicalPerformanceVerified": False},
            "plan": _plan(context, recipe)}


class RealizationService:
    def __init__(self, settings: Settings, store: Store, *, lan=False):
        self.settings, self.store, self.lan = settings, store, lan
        with closing(store.connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS design_realizations (id TEXT PRIMARY KEY, data TEXT NOT NULL)")

    @contextmanager
    def _database(self, *, write=False):
        with closing(self.store.connect()) as db, db:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db

    def design_catalog(self):
        """Read-only discovery, never a cached geometry or rights approval.

        Fixed public proposals and strict private recipes supply availability.
        Missing inputs do not hide saved work. SQLite projects only navigation
        metadata; opening a saved design still goes through read/_current.
        """
        try:
            path = SR.HANDOFF / "design/manifest.json"
            manifest = SR._json_file(self.settings.root, path, SR.MANIFEST_PINS[path])
            contexts = [architecture_context(self.settings.root, identity)
                        for identity in manifest["architectureIDs"]]
        except (TachyonError, SR.StrategyRuntimeError, OSError, ValueError, KeyError, TypeError):
            contexts = []
        architectures = []
        for context in sorted(contexts, key=lambda c: c.proposal["alternative"]):
            alternative = context.proposal["alternative"]
            try:
                recipe = load_recipe(self.settings, alternative)
            except TachyonError:
                recipe = None
            architectures.append({
                "architectureId": context.proposal["id"],
                "alternative": alternative, "recipeAvailable": recipe is not None,
                "recipeKind": "authored_component_recipe" if recipe else "none",
                "requestedPlacements": len(recipe.template.instances) if recipe else 0,
                "roleIds": sorted(recipe.role_component_ids) if recipe else [],
                "qualification": "not_checked",
            })
        with self._database() as db:
            rows = db.execute("""
                SELECT id, json_extract(data, '$.architectureId'),
                       json_extract(data, '$.strategyId'),
                       json_extract(data, '$.accepted.id'),
                       COALESCE(json_type(data, '$.candidate') = 'object', 0)
                FROM design_realizations WHERE json_valid(data)
                  AND json_type(data, '$.architectureId') = 'text'
                  AND json_type(data, '$.strategyId') = 'text'
                  AND (json_type(data, '$.accepted.id') IS NULL
                       OR json_type(data, '$.accepted.id') IN ('text', 'null'))
                ORDER BY rowid DESC LIMIT 8
            """).fetchall()
        saved = [{"designId": identity, "architectureId": architecture, "strategyId": strategy,
                  "revisionId": revision, "hasCandidate": bool(candidate)}
                 for identity, architecture, strategy, revision, candidate in rows
                 if all(isinstance(value, str) for value in (identity, architecture, strategy))
                 and (revision is None or isinstance(revision, str))]
        return {"schemaVersion": 1, "kind": "tachyon.design_catalog",
                "architectures": architectures, "saved": saved,
                "canGenerateAdditionalArchitectures": False}

    def _load(self, db, design_id):
        row = db.execute("SELECT data FROM design_realizations WHERE id = ?", (design_id,)).fetchone()
        if row is None:
            raise TachyonError("DESIGN_NOT_FOUND", "This local design does not exist", 404)
        try:
            data = SR.decode_json(row[0])
            digest = A.content_hash(data["recipe"]) if data["recipe"] is not None else None
            if data["designId"] != design_id or digest != data["recipeHash"]:
                raise ValueError()
            if data["recipe"] is not None:
                Recipe.model_validate(data["recipe"])
            return data
        except (ValueError, KeyError, TypeError):
            raise TachyonError("DESIGN_STATE_INVALID", "Persisted design metadata fails validation; accepted data was retained", 409) from None

    def _save(self, db, data):
        db.execute("INSERT INTO design_realizations (id, data) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                   (data["designId"], json.dumps(data, allow_nan=False)))

    def _context(self, data):
        context = architecture_context(self.settings.root, data["architectureId"])
        recipe = Recipe.model_validate(data["recipe"]) if data["recipe"] is not None else None
        if (context.spec["id"] != data["strategyId"] or (recipe is not None and recipe.alternative != context.proposal["alternative"])
                or data["designId"] != A.stable_id("design", context.proposal["id"], data["recipeHash"] or "missing")):
            raise TachyonError("DESIGN_CONTEXT_MISMATCH", "Stored design does not match its verified architecture and recipe", 409)
        return context, recipe

    def _blocked(self, context, recipe, reasons):
        """Persist a reloadable observation without replacing accepted work."""
        digest = A.content_hash(recipe.json_data()) if recipe else None
        design_id = A.stable_id("design", context.proposal["id"], digest or "missing")
        with self._database(write=True) as db:
            row = db.execute("SELECT data FROM design_realizations WHERE id = ?", (design_id,)).fetchone()
            if row is None or not SR.decode_json(row[0]).get("accepted"):
                self._save(db, {"designId": design_id, "architectureId": context.proposal["id"],
                                "strategyId": context.spec["id"], "recipeHash": digest,
                                "recipe": recipe.json_data() if recipe else None, "accepted": None,
                                "bindings": None, "candidate": None, "candidateBindings": None, "undo": []})
        return _empty(design_id, context, recipe, reasons)

    def _read_blocked(self, data, context, recipe):
        """Recheck blocked inputs; GET never silently creates an accepted robot."""
        try:
            current = load_recipe(self.settings, context.proposal["alternative"])
            digest = A.content_hash(current.json_data()) if current else None
            if digest != data["recipeHash"]:
                return _empty(data["designId"], context, recipe, [missing("recipe", "RECIPE_CHANGED", "Private recipe inputs changed; realize the current recipe as a new design")])
            reasons = []
            if recipe is None:
                reasons.append(missing("recipe", "ASSEMBLY_RECIPE_MISSING", "Supply a private assembly recipe for this architecture alternative"))
            try:
                service, _ = qualified_catalog(self.settings, recipe, lan=self.lan)
                if recipe:
                    _check_actions(context, recipe)
                    revision = build_pose(service, recipe, data["designId"], "lower")
                    _reach(recipe, revision, _links(context, recipe, revision))
                    reasons.append(missing("recipe", "REALIZATION_REQUIRED", "Inputs are now available; realize this recipe to create its accepted revision"))
            except QualificationBlocked as blocked:
                reasons.extend(blocked.reasons)
            return _empty(data["designId"], context, recipe, reasons)
        except TachyonError as error:
            return _empty(data["designId"], context, recipe, [missing("recipe", error.code, error.message)])
        except (ValidationError, KeyError):
            return _empty(data["designId"], context, recipe, [missing("recipe", "INVALID_JOINT_CONFIGURATION", "Recipe baseline joint positions or graph metadata fail validation")])

    def _current(self, data, context, recipe):
        try:
            current = load_recipe(self.settings, context.proposal["alternative"])
        except TachyonError as error:
            raise QualificationBlocked([missing("recipe", error.code, error.message)]) from None
        if current is None or A.content_hash(current.json_data()) != data["recipeHash"]:
            raise QualificationBlocked([missing("recipe", "RECIPE_CHANGED", "The current private recipe is missing or changed; realize it as a new design")])
        service, public = qualified_catalog(self.settings, recipe, lan=self.lan)
        _check_actions(context, recipe)
        pairs = [(data["accepted"], data["bindings"])]
        if data.get("candidate"):
            pairs.append((data["candidate"], data["candidateBindings"]))
        pairs.extend((h["revision"], h["bindings"]) for h in data["undo"])
        for raw, bindings in pairs:
            try:
                revision = A.AssemblyRevision.model_validate(raw)
                service.validate(revision)
                expected = build_pose(service, recipe, data["designId"], revision.assembly.configuration_id)
                if revision.assembly.design_id != data["designId"] or revision.engineering_hash != expected.engineering_hash:
                    raise TachyonError("REVISION_RECIPE_MISMATCH", "Stored engineering content differs from the registered recipe", 409)
                links = B.BindingSnapshot.model_validate(bindings)
                B._current(revision, links)
                if links != _links(context, recipe, revision):
                    raise TachyonError("BINDINGS_CONTEXT_MISMATCH", "Stored links differ from the real strategy and private recipe", 409)
                _reach(recipe, revision, links)
            except TachyonError as error:
                if error.code == "CATALOG_CHANGED":
                    raise QualificationBlocked([missing("catalog", error.code, error.message)]) from None
                raise
            except (ValueError, KeyError, TypeError):
                raise TachyonError("DESIGN_STATE_INVALID", "Persisted revision or bindings fail validation", 409) from None
        if data.get("candidate") and data["candidate"]["parentRevisionId"] != data["accepted"]["id"]:
            raise TachyonError("CANDIDATE_CONFLICT", "Stored candidate no longer belongs to the accepted revision", 409)
        return service, public

    def _reply(self, data, context, recipe, service, public):
        accepted = A.AssemblyRevision.model_validate(data["accepted"])
        bindings = B.BindingSnapshot.model_validate(data["bindings"])
        candidate = A.AssemblyRevision.model_validate(data["candidate"]) if data.get("candidate") else None
        candidate_bindings = B.BindingSnapshot.model_validate(data["candidateBindings"]) if candidate else None
        can_edit, edit_gaps = edit_qualification(service, context, recipe, data["designId"])
        if len(data["undo"]) >= MAX_UNDO:
            can_edit = False
            edit_gaps.append(missing("recipe", "DESIGN_HISTORY_LIMIT", "Undo an accepted edit before adding to this bounded design history"))
        report = service.validate(accepted)
        robot_report = qualify_robot(accepted, recipe.robot, prepared_components=public) if recipe.robot else None
        candidate_report = qualify_robot(candidate, recipe.robot, prepared_components=public) if recipe.robot and candidate else None
        gaps = [*_role_gaps(context, recipe), *edit_gaps]
        if robot_report:
            gaps.extend(missing(m.role, m.code, m.message) for m in robot_report.missing)
            if candidate_report:
                gaps.extend(missing(m.role, "CANDIDATE_"+m.code, m.message) for m in candidate_report.missing)
        else:
            gaps.append(missing("robot", "HARDWARE_QUALIFICATION_INCOMPLETE", "BOM completeness, supporting hardware, actuation, clearance and competition task capability remain unverified"))
        fixture = any(c.geometry_class == "test_fixture" for c in accepted.assembly.components)
        reach = _reach(recipe, accepted, bindings)
        candidate_reach = _reach(recipe, candidate, candidate_bindings) if candidate else None
        target_reach = context.spec["capabilityRequirements"]["targets"]["reachM"]
        available_height = reach["heightM"] if reach else None
        if recipe.robot or recipe.edit_group:
            # A lowered acquisition pose is not the mechanism's maximum reach.
            # Recompute the registered raised endpoint rather than inventing a
            # capability from the proposal's desired height.
            try:
                raised = build_pose(service, recipe, data["designId"], "raised") if "raised" in recipe.configurations else accepted
                raised_reach = _reach(recipe, raised, _links(context, recipe, raised))
                if raised_reach:
                    available_height = max(available_height or 0., raised_reach["heightM"])
            except (TachyonError, ValidationError):
                # A rejected optional edit must not hide the valid accepted
                # assembly. edit_qualification supplies its precise reason.
                gaps.append(missing("scorer", "RAISED_ENDPOINT_INVALID", "The raised endpoint failed validation; the accepted assembly remains available"))
        if available_height is not None and available_height < target_reach:
            gaps.append(missing("scorer", "MODELED_REACH_TARGET_UNMET",
                                "The declared tool anchor is below the strategy's modeled height target; geometric height alone does not verify scoring capability"))
        if fixture:
            gaps.append(missing("robot", "TEST_FIXTURE_ONLY", "Original fixture assemblies exercise software; they do not pass authentic VEX robot acceptance"))
        complete = bool(robot_report and robot_report.complete_robot and not fixture
                        and (candidate_report is None or candidate_report.complete_robot)
                        and not any(gap["code"]!="DESIGN_HISTORY_LIMIT" for gap in gaps)
                        and available_height is not None and available_height >= target_reach)
        return {"designId": data["designId"], "architectureId": context.proposal["id"], "strategyId": context.spec["id"],
                "status": "ready" if complete else "partial", "missing": _dedupe(gaps), "canEdit": can_edit, "revisionId": accepted.id,
                "accepted": accepted.json_data(), "candidate": candidate.json_data() if candidate else None,
                "bindings": bindings.json_data(), "candidateBindings": candidate_bindings.json_data() if candidate else None,
                "previous": data["undo"][-1]["revision"] if data["undo"] else None,
                "previousBindings": data["undo"][-1]["bindings"] if data["undo"] else None,
                "worldTransforms": {key: list(value.matrix) for key, value in A.world_transforms(accepted.assembly).items()},
                "candidateWorldTransforms": {key: list(value.matrix) for key, value in A.world_transforms(candidate.assembly).items()} if candidate else {},
                "components": public, "annotations": _annotations(accepted, bindings),
                "candidateAnnotations": _annotations(candidate, candidate_bindings) if candidate else [],
                "qualification": {"completeRobot": complete, "graphValid": True, "hardwareQualified": bool(robot_report and robot_report.hardware_qualified),
                                  "physicalPerformanceVerified": False, "capabilityStatus": "unverified", "testFixtureOnly": fixture,
                                  "blockers": list(report.blockers),
                                  "limitations": [text for text in report.limitations if "pose solver" not in text],
                                  "poseValidation": "Declared endpoints only; no continuous motion or collision certification",
                                  "reach": reach, "candidateReach": candidate_reach,
                                  "modeledReachTargetM": target_reach,
                                  "availableEndpointHeightM": available_height,
                                  "robotReport": robot_report.json_data() if robot_report else None,
                                  "candidateRobotReport": candidate_report.json_data() if candidate_report else None,
                                  "anchorHeightMeetsModeledTarget": reach["heightM"] >= target_reach if reach else None,
                                  "heightComparisonBasis": "Declared metres/Y-up pose and abstract target only; physical floor, contact and scoring capability unverified"},
                "plan": _plan(context, recipe)}

    def realize(self, architecture_id):
        context = architecture_context(self.settings.root, architecture_id)
        recipe = None
        try:
            recipe = load_recipe(self.settings, context.proposal["alternative"])
            if recipe is None:
                reasons = [missing("recipe", "ASSEMBLY_RECIPE_MISSING", "Supply a private assembly recipe for this architecture alternative")]
                try:
                    qualified_catalog(self.settings, None, lan=self.lan)
                except QualificationBlocked as blocked:
                    reasons.extend(blocked.reasons)
                return self._blocked(context, None, reasons)
            recipe_hash = A.content_hash(recipe.json_data())
            design_id = A.stable_id("design", architecture_id, recipe_hash)
            with self._database(write=True) as db:
                row = db.execute("SELECT 1 FROM design_realizations WHERE id = ?", (design_id,)).fetchone()
                data = self._load(db, design_id) if row else None
                if data and data["accepted"]:
                    service, public = self._current(data, context, recipe)
                else:
                    service, public = qualified_catalog(self.settings, recipe, lan=self.lan)
                    _check_actions(context, recipe)
                    revision = build_pose(service, recipe, design_id, "lower")
                    links = _links(context, recipe, revision)
                    _reach(recipe, revision, links)
                    data = {"designId": design_id, "architectureId": architecture_id, "strategyId": context.spec["id"],
                            "recipeHash": recipe_hash, "recipe": recipe.json_data(), "accepted": revision.json_data(),
                            "bindings": links.json_data(), "candidate": None, "candidateBindings": None, "undo": []}
                    self._save(db, data)
                return self._reply(data, context, recipe, service, public)
        except QualificationBlocked as blocked:
            return self._blocked(context, recipe, blocked.reasons)
        except TachyonError as error:
            if error.code in {"REVISION_HASH_MISMATCH", "BINDINGS_HASH_MISMATCH", "DESIGN_STATE_INVALID"}:
                raise
            return self._blocked(context, recipe, [missing("recipe", error.code, error.message)])
        except (ValidationError, KeyError):
            return self._blocked(context, recipe, [missing("recipe", "INVALID_JOINT_CONFIGURATION", "Recipe baseline joint positions or graph metadata fail validation")])

    def read(self, design_id):
        with self._database() as db:
            data = self._load(db, design_id)
        context, recipe = self._context(data)
        if data["accepted"] is None:
            return self._read_blocked(data, context, recipe)
        try:
            service, public = self._current(data, context, recipe)
        except QualificationBlocked as blocked:
            return _empty(design_id, context, recipe, blocked.reasons)
        return self._reply(data, context, recipe, service, public)

    def preview(self, design_id, base_revision_id, configuration_id):
        if configuration_id not in ("lower", "raised"):
            raise TachyonError("UNSUPPORTED_CONFIGURATION", "Only registered lower and raised joint poses are supported")
        with self._database(write=True) as db:
            data = self._load(db, design_id)
            context, recipe = self._context(data)
            if data["accepted"] is None:
                return self._read_blocked(data, context, recipe)
            if data["accepted"]["id"] != base_revision_id:
                raise TachyonError("REVISION_CONFLICT", "The accepted design changed; refresh before previewing", 409)
            try:
                service, public = self._current(data, context, recipe)
            except QualificationBlocked as blocked:
                return _empty(design_id, context, recipe, blocked.reasons)
            if len(data["undo"]) >= MAX_UNDO:
                raise TachyonError("DESIGN_HISTORY_LIMIT", "Undo an accepted edit before previewing another", 409)
            can_edit, _ = edit_qualification(service, context, recipe, design_id)
            if not can_edit:
                raise TachyonError("UNSUPPORTED_CONFIGURATION", "This mechanism does not have two qualified distinct joint poses and reach anchors")
            accepted = A.AssemblyRevision.model_validate(data["accepted"])
            candidate = build_pose(service, recipe, design_id, configuration_id, accepted.id)
            if candidate.engineering_hash == accepted.engineering_hash:
                raise TachyonError("CONFIGURATION_UNCHANGED", "The requested joint pose is already accepted")
            links = B.rebind_actions(candidate, B.BindingSnapshot.model_validate(data["bindings"]))
            _reach(recipe, candidate, links)
            data.update(candidate=candidate.json_data(), candidateBindings=links.json_data())
            self._save(db, data)
            return self._reply(data, context, recipe, service, public)

    def decide(self, design_id, base_revision_id, action, candidate_revision_id=None):
        if action not in ("apply", "discard", "undo"):
            raise TachyonError("UNSUPPORTED_DECISION", "Choose apply, discard or undo")
        with self._database(write=True) as db:
            data = self._load(db, design_id)
            context, recipe = self._context(data)
            if data["accepted"] is None:
                return self._read_blocked(data, context, recipe)
            try:
                service, public = self._current(data, context, recipe)
            except QualificationBlocked as blocked:
                return _empty(design_id, context, recipe, blocked.reasons)
            accepted = A.AssemblyRevision.model_validate(data["accepted"])
            # Exact apply retry is idempotent, after all source/rights/hash checks.
            if action == "apply" and accepted.id == candidate_revision_id and accepted.parent_revision_id == base_revision_id:
                return self._reply(data, context, recipe, service, public)
            if accepted.id != base_revision_id:
                raise TachyonError("REVISION_CONFLICT", "The accepted design changed; no revision was overwritten", 409)
            if action == "undo":
                if candidate_revision_id is not None:
                    raise TachyonError("INVALID_DECISION", "Undo uses the accepted revision and no candidate ID")
                if not data["undo"]:
                    raise TachyonError("UNDO_UNAVAILABLE", "There is no preceding accepted edit", 409)
                prior = data["undo"].pop()
                restore = A.AssemblyRevision.model_validate(prior["revision"])
                compensation = A._revision(restore.assembly, accepted.id)
                links = B.rebind_actions(compensation, B.BindingSnapshot.model_validate(prior["bindings"]))
                data.update(accepted=compensation.json_data(), bindings=links.json_data())
            else:
                candidate = data.get("candidate")
                if candidate is None or (candidate_revision_id is not None and candidate["id"] != candidate_revision_id):
                    raise TachyonError("CANDIDATE_CONFLICT", "The requested preview is not the current candidate", 409)
                if action == "apply":
                    if candidate_revision_id is None:
                        raise TachyonError("CANDIDATE_CONFLICT", "Apply must identify the exact previewed revision", 409)
                    if len(data["undo"]) >= MAX_UNDO:
                        raise TachyonError("DESIGN_HISTORY_LIMIT", "This bounded design has reached its accepted-edit history limit", 409)
                    data["undo"].append({"revision": data["accepted"], "bindings": data["bindings"]})
                    data.update(accepted=candidate, bindings=data["candidateBindings"])
            data.update(candidate=None, candidateBindings=None)
            self._save(db, data)
            return self._reply(data, context, recipe, service, public)
