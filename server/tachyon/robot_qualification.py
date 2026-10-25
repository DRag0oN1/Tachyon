"""Bounded architecture-A conceptual hardware qualification, without CAD I/O.

The private Recipe contains ``robot: RobotContract | None``. Call
``qualify_robot(revision, recipe.robot, prepared_components=public)``
after current catalog, source-byte and rights rechecks. Full current prepared
receipts are required only for selected OEM integrated units. This module does
not grant rights or inspect assets. Facts are declarations tied to exact prepared catalog fingerprints;
the caller remains responsible for their metrology/provenance review.

completeRobot means the seven-role conceptual hardware contract passes. It does
not assert object handling, collision-free motion, payload, speed or simulation.
No caller qualification/performance booleans are accepted. JSON uses camelCase;
``RobotContract.model_json_schema(by_alias=True)`` is the exact input DTO.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import math
import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from . import assemblies as A
from .errors import TachyonError
from .models import Model, PreparedComponent


Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]
Evidence = Annotated[str, Field(min_length=1, max_length=4096, pattern=r"\S")]
Sha = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Positive = Annotated[float, Field(gt=0, le=2, strict=True)]
Ids = Annotated[tuple[Identifier, ...], Field(min_length=1, max_length=512)]
Role = Literal["chassis", "drive", "pin_intake", "pin_transfer", "scorer", "cup_cradle", "stack_interface"]
Purpose = Literal["structure", "wheel", "motor", "shaft", "gear", "bearing", "retainer",
                  "fastener", "gripper", "guide", "control", "power", "roller", "gate",
                  "cradle", "latch", "spacer", "coupler", "sensor"]
ROLES = ("chassis", "drive", "pin_intake", "pin_transfer", "scorer", "cup_cradle", "stack_interface")
VALIDATOR_VERSION = "architecture-a-hardware-3"


class BOMItem(Model):
    instance_id: Identifier
    component_id: Identifier
    catalog_fingerprint: Sha
    purpose: Purpose
    evidence: Evidence


class PortRef(Model):
    instance_id: Identifier
    port_id: Identifier

    def key(self):
        return self.instance_id, self.port_id


class MountGroup(Model):
    id: Identifier
    member_ids: Ids
    support_ids: Ids
    fastener_ids: Ids
    relationship_ids: Ids
    evidence: Evidence


class ShaftSupport(Model):
    id: Identifier
    shaft_id: Identifier
    start_port_id: Identifier
    end_port_id: Identifier
    bearings: tuple[PortRef, ...] = Field(min_length=2, max_length=8)
    retainer_ids: Ids
    relationship_ids: Ids
    evidence: Evidence


class TransmissionStage(Model):
    id: Identifier
    kind: Literal["shaft", "gear_mesh"]
    driver: PortRef
    driven: PortRef
    speed_ratio: float = Field(strict=True, ge=-1e6, le=1e6)  # driven / driver about each port's +Z
    driver_teeth: int | None = Field(default=None, gt=0, le=500, strict=True)
    driven_teeth: int | None = Field(default=None, gt=0, le=500, strict=True)
    module_m: Positive | None = None
    engagement_m: Positive | None = None
    tolerance_m: float = Field(default=.0001, gt=0, le=.001, strict=True)
    evidence: Evidence

    @model_validator(mode="after")
    def stage_facts(self):
        if self.driver.instance_id == self.driven.instance_id or self.speed_ratio == 0:
            raise ValueError("A stage needs different component instances and a nonzero ratio")
        if self.kind == "gear_mesh":
            if None in (self.driver_teeth, self.driven_teeth, self.module_m) or self.engagement_m is not None:
                raise ValueError("Gear mesh needs source tooth counts/module, without shaft engagement")
        elif self.engagement_m is None or any(v is not None for v in (self.driver_teeth, self.driven_teeth, self.module_m)):
            raise ValueError("Shaft stage needs engagementM, without gear facts")
        return self


class Transmission(Model):
    id: Identifier
    actuator: PortRef
    outputs: tuple[PortRef, ...] = Field(min_length=1, max_length=32)
    stages: tuple[TransmissionStage, ...] = Field(min_length=1, max_length=128)
    evidence: Evidence


class DriveSide(Model):
    id: Literal["left", "right"]
    wheel_instance_ids: tuple[Identifier, Identifier]
    transmission_id: Identifier


class FourBar(Model):
    ground_id: Identifier
    link_ids: tuple[Identifier, Identifier]
    carrier_id: Identifier
    gripper_id: Identifier
    joint_ids: tuple[Identifier, Identifier, Identifier, Identifier]


class Mechanism(Model):
    role: Literal["pin_intake", "pin_transfer", "scorer", "cup_cradle", "stack_interface"]
    kind: Literal["opposed_rollers", "gated_handoff", "four_bar_gripper", "independent_cup", "stack_alignment"]
    member_ids: Ids
    joint_ids: tuple[Identifier, ...] = Field(default=(), max_length=32)
    transmission_ids: tuple[Identifier, ...] = Field(default=(), max_length=16)
    four_bar: FourBar | None = None
    # Intended motor-output commands, not measured/achieved speeds. Required to
    # compare independent intake motors; shared mechanical drives need no command.
    motor_speeds_rpm: dict[Identifier, Annotated[float, Field(strict=True, ge=-600, le=600)]] = Field(default_factory=dict, max_length=16)
    retention_member_ids: tuple[Identifier, ...] = Field(default=(), max_length=32)
    release_joint_id: Identifier | None = None
    evidence: Evidence


class ObjectDimensions(Model):
    kind: Literal["pin", "cup"]
    diameter_m: Positive | None = None
    height_m: Positive | None = None
    source_url: Evidence
    uncertainty: Evidence


class OEMChildDefinition(Model):
    definition_label: str = Field(pattern=r"^[0-9]+(?::[0-9]+)*$")
    definition_name: Evidence
    purpose: Literal["motor", "gear", "jaw", "structure", "fastener", "shaft", "bearing", "retainer", "spacer"]
    quantity: int = Field(gt=0, le=512, strict=True)
    teeth: int | None = Field(default=None, gt=0, le=500, strict=True)


class OEMIntegratedUnit(Model):
    """Reviewed source inventory, cross-checked against a current catalog receipt.

    Child roles/counts are source-bound metrology declarations, not inferred
    motion or object-handling performance. Native hierarchy hashes use exactly
    ``A.content_hash([n.json_data() for n in receipt.native_hierarchy])``.
    """
    kind: Literal["vex_claw_kit_v2"] = "vex_claw_kit_v2"
    instance_id: Identifier
    component_id: Identifier
    catalog_fingerprint: Sha
    source_sha256: Sha
    definition_label: str = Field(pattern=r"^[0-9]+(?::[0-9]+)*$")
    definition_name: Evidence
    native_hierarchy_sha256: Sha
    children: tuple[OEMChildDefinition, ...] = Field(min_length=5, max_length=128)
    evidence: Evidence

    @model_validator(mode="after")
    def distinct_children(self):
        if len({c.definition_label for c in self.children}) != len(self.children):
            raise ValueError("Aggregate repeated child occurrences into one definition quantity")
        if any(c.definition_label == self.definition_label for c in self.children):
            raise ValueError("A selected unit cannot be its own child")
        return self


class RobotContract(Model):
    schema_version: Literal[1] = 1
    architecture: Literal["A"] = "A"
    bom: tuple[BOMItem, ...] = Field(min_length=1, max_length=512)
    mounts: tuple[MountGroup, ...] = Field(default=(), max_length=128)
    shaft_supports: tuple[ShaftSupport, ...] = Field(default=(), max_length=128)
    transmissions: tuple[Transmission, ...] = Field(default=(), max_length=32)
    drive_sides: tuple[DriveSide, ...] = Field(default=(), max_length=2)
    mechanisms: tuple[Mechanism, ...] = Field(default=(), max_length=5)
    objects: tuple[ObjectDimensions, ...] = Field(default=(), max_length=2)
    integrated_units: tuple[OEMIntegratedUnit, ...] = Field(default=(), max_length=4)

    @model_validator(mode="after")
    def identities(self):
        for rows, key in ((self.bom, "instance_id"), (self.mounts, "id"),
                          (self.shaft_supports, "shaft_id"), (self.transmissions, "id"),
                          (self.drive_sides, "id"), (self.mechanisms, "role"), (self.objects, "kind"),
                          (self.integrated_units, "instance_id")):
            if len({getattr(row, key) for row in rows}) != len(rows):
                raise ValueError(f"Duplicate contract {key}")
        for transmission in self.transmissions:
            if len({s.id for s in transmission.stages}) != len(transmission.stages):
                raise ValueError("Duplicate transmission stage ID")
            if len({p.key() for p in transmission.outputs}) != len(transmission.outputs):
                raise ValueError("Duplicate transmission output")
        return self


class Missing(Model):
    role: str
    code: str
    message: str
    instance_ids: tuple[str, ...] = ()


class Provenance(Model):
    instance_id: str
    component_id: str
    catalog_fingerprint: str
    source_sha256: str
    source_url: str
    sku: str | None
    matches_bom: bool


class RobotQualificationReport(Model):
    validator_version: str = VALIDATOR_VERSION
    scope: Literal["architecture_a_conceptual_hardware"] = "architecture_a_conceptual_hardware"
    design_id: str
    revision_id: str
    engineering_hash: str
    contract_hash: str | None
    report_hash: str
    status: Literal["ready", "incomplete"]
    graph_valid: bool
    hardware_qualified: bool
    complete_robot: bool
    missing: tuple[Missing, ...]
    provenance: tuple[Provenance, ...]
    counts: dict[str, int]
    role_counts: dict[str, int]
    transmission_ratios: dict[str, dict[str, float]]
    integrated_units: tuple[OEMIntegratedUnit, ...] = ()
    integrated_unit_counts: dict[str, int] = Field(default_factory=dict)
    task_capability_status: Literal["unverified"] = "unverified"
    physical_performance_verified: Literal[False] = False
    uncertainties: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "Conceptual hardware checks only; no payload, collision, motion or physical-performance certification.",
        "Source bytes, mesh availability and current rights must be rechecked by the integrating catalog service.",
        "BOM purposes and mechanical dimensions are source-bound declarations, not independently measured by this validator.",
        "OEM internal inventories qualify purchased hardware only; internal animation and object gripping remain unverified.",
    )


def _canonical(value):
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [_canonical(v) for v in value]
        if items and all(isinstance(v, (dict, str)) for v in items):
            import json
            items.sort(key=lambda v: json.dumps(v, sort_keys=True))
        return items
    return value


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _norm(a):
    return math.sqrt(_dot(a, a))


def qualify_robot(revision: A.AssemblyRevision, contract: RobotContract | None, *,
                  prepared_components: Iterable[PreparedComponent | dict] = ()) -> RobotQualificationReport:
    """Recompute a deterministic report for this exact revision; no file or DB I/O."""
    checker = _Checker(revision, contract, prepared_components)
    return checker.run()


class _Checker:
    def __init__(self, revision, contract, prepared_components=()):
        self.revision, self.contract = revision, contract
        self.snapshot = revision.assembly
        self.nodes = {n.id: n for n in self.snapshot.instances}
        self.defs = {d.id: d for d in self.snapshot.components}
        self.rels = {r.id: r for r in self.snapshot.relationships}
        self.bom = {b.instance_id: b for b in contract.bom} if contract else {}
        self.world = {}
        self.missing = []
        self.ratios = {}
        self.provenance = []
        self.supports = {}
        self.prepared_components = prepared_components
        self.integrated_units = {}

    def issue(self, role, code, message, *ids):
        self.missing.append(Missing(role=role, code=code, message=message, instance_ids=tuple(sorted(set(ids)))))

    def purpose(self, identity):
        item = self.bom.get(identity)
        return item.purpose if item else None

    def port(self, ref, role):
        node = self.nodes.get(ref.instance_id)
        definition = self.defs.get(node.component_id) if node else None
        port = next((p for p in definition.ports if p.id == ref.port_id), None) if definition else None
        if port is None:
            self.issue(role, "MISSING_PORT", "Declared mechanical port does not exist", ref.instance_id)
            return None
        if port.frame_basis != "measured":
            self.issue(role, "UNMEASURED_PORT", "Mechanical qualification requires measured full port frames", ref.instance_id)
        frame = self.world[ref.instance_id].compose(port.frame)
        return frame.point(), frame.matrix[8:11], port

    def connected_group(self, ids, relationship_ids, role):
        wanted = set(ids)
        neighbors = {i: set() for i in wanted}
        for identity in relationship_ids:
            rel = self.rels.get(identity)
            if rel is None:
                self.issue(role, "MISSING_RELATIONSHIP", "Declared support/mount relationship is absent", *wanted)
                continue
            a, b = rel.parent_instance_id, rel.child_instance_id
            if a not in wanted or b not in wanted:
                self.issue(role, "GROUP_RELATIONSHIP_SCOPE", "Mount/support relationship leaves its declared members", a, b)
                continue
            neighbors[a].add(b)
            neighbors[b].add(a)
        reached, pending = set(), list(wanted)[:1]
        while pending:
            node = pending.pop()
            if node not in reached:
                reached.add(node)
                pending.extend(neighbors[node] - reached)
        if reached != wanted or wanted - self.nodes.keys():
            self.issue(role, "DISCONNECTED_SUPPORT", "Declared mount/support hardware is not connected by its relationships", *wanted)

    def check_bom(self):
        if set(self.bom) != set(self.nodes):
            self.issue("robot", "BOM_COVERAGE", "BOM must exactly cover every assembly instance", *(set(self.bom) ^ set(self.nodes)))
        for identity, node in sorted(self.nodes.items()):
            definition = self.defs[node.component_id]
            item = self.bom.get(identity)
            matches = bool(item and (item.component_id, item.catalog_fingerprint) == (definition.id, definition.catalog_fingerprint))
            if not matches:
                self.issue(node.subsystem_id, "STALE_BOM_FINGERPRINT", "BOM identity/fingerprint does not match this revision's component", identity)
            self.provenance.append(Provenance(instance_id=identity, component_id=definition.id,
                catalog_fingerprint=definition.catalog_fingerprint, source_sha256=definition.source_sha256,
                source_url=definition.source_url, sku=definition.sku, matches_bom=matches))
            source = urlsplit(definition.source_url)
            host = source.hostname or ""
            if (definition.origin_kind != "manufacturer_cad" or definition.geometry_class != "verified_imported_component"
                    or definition.reference_only or not re.fullmatch(r"(?:276|275|228)-[A-Za-z0-9-]+", definition.sku or "")
                    or source.scheme != "https" or not (host == "vexrobotics.com" or host.endswith(".vexrobotics.com"))):
                self.issue(node.subsystem_id, "NON_AUTHENTIC_VEX_COMPONENT", "A manufacturer VEX component with source identity is required; fixtures/references never qualify", identity)
            q = definition.geometry_validation
            if (q.status != "valid" or q.native_brep_valid is not True or q.qualified_for_robot_generation is not True
                    or q.invalid_definition_count != 0 or q.invalid_component_instances):
                self.issue(node.subsystem_id, "GEOMETRY_NOT_QUALIFIED", "Component lacks affirmative native geometry qualification", identity)

    def check_mounts(self):
        covered = {self.snapshot.root_instance_id}
        for group in self.contract.mounts:
            ids = set((*group.member_ids, *group.support_ids, *group.fastener_ids))
            if any(self.purpose(i) != "structure" for i in group.support_ids):
                self.issue("robot", "MOUNT_STRUCTURE_REQUIRED", "Mount supports must be BOM structure", *group.support_ids)
            if any(self.purpose(i) != "fastener" for i in group.fastener_ids):
                self.issue("robot", "MOUNT_FASTENER_REQUIRED", "Mount fasteners must be actual BOM fastener instances", *group.fastener_ids)
            self.connected_group(ids, group.relationship_ids, "robot")
            covered.update(ids)
        if set(self.nodes) - covered:
            self.issue("robot", "MOUNT_COVERAGE", "Every non-root part needs an explicit supported hardware mount group", *(set(self.nodes)-covered))

    def check_integrated_units(self):
        if not self.contract.integrated_units:
            return
        receipts = {}
        for raw in self.prepared_components:
            try:
                if isinstance(raw, PreparedComponent):
                    receipt = raw
                else:
                    data = dict(raw)
                    # Catalog.prepared adds current display operations. They are
                    # not accepted as rights grants or persisted engineering facts.
                    data.pop("qualifiedOperations", None)
                    receipt = PreparedComponent.model_validate(data)
            except (ValueError, TypeError):
                self.issue("scorer", "OEM_RECEIPT_INVALID", "OEM qualification needs full current prepared catalog receipts")
                continue
            if receipt.id in receipts:
                self.issue("scorer", "OEM_RECEIPT_DUPLICATE", "Current component receipt identities must be unique")
            receipts[receipt.id] = receipt
        for unit in sorted(self.contract.integrated_units, key=lambda u: u.instance_id):
            previous = len(self.missing)
            node = self.nodes.get(unit.instance_id)
            definition = self.defs.get(node.component_id) if node else None
            receipt = receipts.get(unit.component_id)
            item = self.bom.get(unit.instance_id)
            if (definition is None or item is None or item.purpose != "gripper" or node.subsystem_id != "scorer"
                    or (unit.component_id, unit.catalog_fingerprint, unit.source_sha256) !=
                       (definition.id, definition.catalog_fingerprint, definition.source_sha256)):
                self.issue("scorer", "OEM_IDENTITY_MISMATCH", "Integrated gripper must match this revision's actual BOM identity, fingerprint and source", unit.instance_id)
                continue
            if receipt is None:
                self.issue("scorer", "OEM_RECEIPT_MISSING", "Supply the selected OEM component's current full prepared receipt", unit.instance_id)
                continue
            keys = ("id", "catalog_fingerprint", "source_sha256", "mesh_sha256", "source_url", "sku", "origin_kind", "geometry_class", "reference_only")
            if any(getattr(receipt,k) != getattr(definition,k) for k in keys):
                self.issue("scorer", "OEM_STALE_RECEIPT", "Current OEM receipt differs from this exact revision", unit.instance_id)
            quality = receipt.geometry_validation
            if (receipt.origin_kind != "manufacturer_cad" or receipt.geometry_class != "verified_imported_component"
                    or receipt.reference_only or quality.get("status") != "valid"
                    or quality.get("nativeBrepValid") is not True or quality.get("qualifiedForRobotGeneration") is not True):
                self.issue("scorer", "OEM_GEOMETRY_NOT_QUALIFIED", "Inspection references, authored fixtures and unqualified native geometry cannot be OEM hardware evidence", unit.instance_id)
            selection = receipt.source_selection
            if (selection is None or selection.definition_label != unit.definition_label
                    or selection.expected_definition_name != unit.definition_name
                    or not unit.definition_name.startswith("276-6010-100 ")
                    or not (receipt.sku or "").startswith("276-6010")):
                self.issue("scorer", "OEM_SELECTION_MISMATCH", "Only the exact selected Claw Kit v2 subassembly qualifies; whole robots and unlabeled imports do not", unit.instance_id)
            hierarchy = [n.json_data() for n in receipt.native_hierarchy]
            nodes = {n.id:n for n in receipt.native_hierarchy}
            if (A.content_hash(hierarchy) != unit.native_hierarchy_sha256 or len(nodes) != len(hierarchy)
                    or sum(n.has_mesh for n in nodes.values()) < 5):
                self.issue("scorer", "OEM_HIERARCHY_MISMATCH", "OEM evidence must retain the exact prepared native child hierarchy", unit.instance_id)
            for child in nodes.values():
                seen = set()
                while child.parent_id is not None:
                    if child.id in seen or child.parent_id not in nodes:
                        self.issue("scorer", "OEM_HIERARCHY_MISMATCH", "OEM native hierarchy has missing parents or cycles", unit.instance_id)
                        break
                    seen.add(child.id)
                    child = nodes[child.parent_id]
            motor = sum(c.quantity for c in unit.children if c.purpose == "motor" and c.definition_name.startswith("276-4840-"))
            pinions = sum(c.quantity for c in unit.children if c.purpose == "gear" and c.teeth == 12 and c.definition_name.startswith("276-6010-011 "))
            gears = sum(c.quantity for c in unit.children if c.purpose == "gear" and c.teeth == 35 and c.definition_name.startswith("276-6010-003 "))
            jaws = sum(c.quantity for c in unit.children if c.purpose == "jaw" and c.definition_name.startswith("276-6010-"))
            hardware = sum(c.quantity for c in unit.children if c.purpose in ("fastener", "shaft", "bearing", "retainer"))
            if motor != 1 or pinions < 1 or gears < 2 or jaws < 2 or hardware < 2:
                self.issue("scorer", "OEM_INTERNAL_HARDWARE_MISSING", "Source inventory must identify the motor, 12T pinion, paired 35T gears/jaws and supporting hardware", unit.instance_id)
            if previous == len(self.missing):
                self.integrated_units[unit.instance_id] = OEMIntegratedUnit.model_validate(_canonical(unit.json_data()))

    def check_supports(self):
        for support in self.contract.shaft_supports:
            shaft = support.shaft_id
            start = self.port(PortRef(instance_id=shaft, port_id=support.start_port_id), "robot")
            end = self.port(PortRef(instance_id=shaft, port_id=support.end_port_id), "robot")
            if self.purpose(shaft) != "shaft":
                self.issue("robot", "SHAFT_REQUIRED", "Shaft support must identify a BOM shaft", shaft)
            if start is None or end is None:
                continue
            vector = _sub(end[0], start[0]); length = _norm(vector)
            if length <= 1e-5:
                self.issue("robot", "SHAFT_SPAN", "Measured shaft endpoints must define a nonzero span", shaft)
                continue
            axis = tuple(v/length for v in vector)
            if any(p[2].kind != "shaft" or abs(_dot(p[1], axis)) < 1-1e-6 for p in (start, end)):
                self.issue("robot", "SHAFT_ENDPOINT_AXES", "Measured shaft endpoint port axes must follow its physical span", shaft)
            self.supports[shaft] = (start[0], axis, length)
            projections = []
            for ref in support.bearings:
                bearing = self.port(ref, "robot")
                if self.purpose(ref.instance_id) != "bearing":
                    self.issue("robot", "BEARING_REQUIRED", "Shaft support needs actual bearing instances", ref.instance_id)
                if bearing is None:
                    continue
                delta = _sub(bearing[0], start[0]); along = _dot(delta, axis)
                radial = _norm(tuple(d-along*a for d, a in zip(delta, axis)))
                if (bearing[2].kind not in ("shaft", "bearing", "revolute") or radial > .0001
                        or abs(_dot(bearing[1], axis)) < 1-1e-6 or not -.0001 <= along <= length+.0001):
                    self.issue("robot", "SHAFT_SUPPORT_ALIGNMENT", "Bearing axes/locations must lie on the measured shaft span", shaft, ref.instance_id)
                projections.append(along)
            if len({r.instance_id for r in support.bearings}) < 2 or not projections or max(projections)-min(projections) <= .0001:
                self.issue("robot", "TWO_SEPARATED_BEARINGS_REQUIRED", "Shaft needs two distinct, axially separated bearing supports", shaft)
            if any(self.purpose(i) != "retainer" for i in support.retainer_ids):
                self.issue("robot", "SHAFT_RETENTION_REQUIRED", "Shaft needs actual BOM retainer hardware", shaft)
            members = {shaft, *(r.instance_id for r in support.bearings), *support.retainer_ids}
            self.connected_group(members, support.relationship_ids, "robot")
        absent = {i for i in self.bom if self.purpose(i) == "shaft"} - self.supports.keys()
        if absent:
            self.issue("robot", "SHAFT_SUPPORT_MISSING", "Every shaft requires measured endpoints, bearings and retention", *absent)

    def check_stage(self, stage, role):
        driver, driven = self.port(stage.driver, role), self.port(stage.driven, role)
        if driver is None or driven is None:
            return
        if any(p[2].kind not in ("shaft", "bearing", "revolute") for p in (driver, driven)):
            self.issue(role, "TRANSMISSION_PORT_KIND", "Transmission endpoints must identify shaft axes")
        dot = _dot(driver[1], driven[1])
        if abs(dot) < 1-1e-6:
            self.issue(role, "SHAFT_AXIS_ALIGNMENT", "Transmission shaft axes must be parallel")
        delta = _sub(driven[0], driver[0]); axial = _dot(delta, driver[1])
        radial = _norm(tuple(d-axial*a for d, a in zip(delta, driver[1])))
        sign = 1 if dot >= 0 else -1
        if stage.kind == "gear_mesh":
            if any(self.purpose(p.instance_id) != "gear" for p in (stage.driver, stage.driven)):
                self.issue(role, "GEAR_REQUIRED", "Gear mesh endpoints must be BOM gears")
            expected = stage.module_m * (stage.driver_teeth + stage.driven_teeth) / 2
            if (radial <= stage.tolerance_m or expected <= stage.tolerance_m
                    or abs(radial-expected) > stage.tolerance_m or abs(axial) > stage.tolerance_m):
                self.issue(role, "GEAR_PITCH_ALIGNMENT", "Gear centers must match pitch radii and share a pitch plane", stage.driver.instance_id, stage.driven.instance_id)
            ratio = -sign * stage.driver_teeth / stage.driven_teeth
            # Gear engagement belongs here, not in a fictitious coincident mate.
            if any(r.kind == "fixed" and {r.parent_instance_id, r.child_instance_id} == {stage.driver.instance_id, stage.driven.instance_id}
                   for r in self.rels.values()):
                self.issue(role, "FAKE_FIXED_GEAR_CONTACT", "Separate meshing gears cannot be declared fixed to each other")
        else:
            ratio = float(sign)
            shafts = [p.instance_id for p in (stage.driver, stage.driven) if self.purpose(p.instance_id) == "shaft"]
            if radial > stage.tolerance_m or not shafts:
                self.issue(role, "SHAFT_AXIS_ALIGNMENT", "Shaft connections need a real coaxial BOM shaft")
            for shaft in shafts:
                span = self.supports.get(shaft)
                if span is None:
                    self.issue(role, "SHAFT_SUPPORT_MISSING", "Transmission shaft lacks qualified support declarations", shaft)
                    continue
                start, axis, length = span
                if abs(_dot(driver[1], axis)) < 1-1e-6 or abs(_dot(driven[1], axis)) < 1-1e-6:
                    self.issue(role, "SHAFT_AXIS_ALIGNMENT", "Connection axes must follow the supported physical shaft", shaft)
                for point in (driver[0], driven[0]):
                    along = _dot(_sub(point, start), axis)
                    if along-stage.engagement_m/2 < -stage.tolerance_m or along+stage.engagement_m/2 > length+stage.tolerance_m:
                        self.issue(role, "SHAFT_ENGAGEMENT", "Connection engagement must fit within the measured shaft span", shaft)
        if not math.isclose(stage.speed_ratio, ratio, rel_tol=1e-6, abs_tol=1e-8):
            self.issue(role, "TRANSMISSION_RATIO", "Declared ratio disagrees with shaft direction or gear tooth counts")

    def check_transmissions(self):
        supported_rotors = set()
        for transmission in self.contract.transmissions:
            role = self.nodes[transmission.actuator.instance_id].subsystem_id if transmission.actuator.instance_id in self.nodes else "robot"
            if self.purpose(transmission.actuator.instance_id) != "motor":
                self.issue(role, "ACTUATOR_MOTOR_REQUIRED", "Transmission must originate at a BOM motor", transmission.actuator.instance_id)
            self.port(transmission.actuator, role)
            ratios = {transmission.actuator.key(): 1.}
            pending = list(transmission.stages)
            for stage in pending:
                self.check_stage(stage, role)
                if stage.kind == "shaft" and any(self.purpose(p.instance_id) == "shaft" for p in (stage.driver, stage.driven)):
                    supported_rotors.update((stage.driver.instance_id, stage.driven.instance_id))
            while pending:
                available = [s for s in pending if s.driver.key() in ratios]
                if not available:
                    self.issue(role, "DISCONNECTED_TRANSMISSION", "Transmission contains a stage disconnected from its actuator")
                    break
                for stage in available:
                    value = ratios[stage.driver.key()] * stage.speed_ratio
                    if not math.isfinite(value):
                        self.issue(role, "TRANSMISSION_RATIO_OVERFLOW", "Transmission ratio product exceeds finite numeric bounds")
                        value = 0.
                    previous = ratios.get(stage.driven.key())
                    if previous is not None and not math.isclose(previous, value, rel_tol=1e-6, abs_tol=1e-8):
                        self.issue(role, "TRANSMISSION_RATIO_CONFLICT", "Transmission paths imply inconsistent output ratios")
                    ratios[stage.driven.key()] = value
                    pending.remove(stage)
            outputs = {}
            for output in transmission.outputs:
                self.port(output, role)
                if output.key() not in ratios or output.key() == transmission.actuator.key():
                    self.issue(role, "UNPOWERED_OUTPUT", "Required output lacks an explicit actuator-to-output stage path", output.instance_id)
                else:
                    outputs["/".join(output.key())] = ratios[output.key()]
            self.ratios[transmission.id] = dict(sorted(outputs.items()))
        unsupported = {i for i in self.bom if self.purpose(i) in ("gear", "wheel", "roller")} - supported_rotors
        if unsupported:
            self.issue("robot", "ROTATING_PART_SUPPORT", "Every gear, wheel and roller needs an explicit supported shaft connection", *unsupported)

    def check_roles(self):
        role_ids = {role: {i for i, n in self.nodes.items() if n.subsystem_id == role} for role in ROLES}
        if set(n.subsystem_id for n in self.nodes.values()) != set(ROLES):
            self.issue("robot", "ARCHITECTURE_ROLES", "Architecture A requires exactly its seven populated subsystem roles")
        def require(role, purpose, count):
            ids = {i for i in role_ids[role] if self.purpose(i) == purpose}
            if len(ids) < count:
                self.issue(role, "ROLE_HARDWARE_MISSING", f"{role} requires at least {count} {purpose} instance(s)")
            return ids
        require("chassis", "structure", 4)
        for purpose in ("control", "power"):
            if not any(self.purpose(i) == purpose for i in self.nodes):
                self.issue("robot", "CONTROL_POWER_MISSING", f"Robot requires mounted {purpose} hardware")
        wheels, motors = require("drive", "wheel", 4), require("drive", "motor", 2)
        transmissions = {t.id: t for t in self.contract.transmissions}
        if len(wheels) != 4 or len(motors) != 2:
            self.issue("drive", "DRIVE_COUNTS", "Architecture A requires exactly four drive wheels and two drive motors")
        if {s.id for s in self.contract.drive_sides} != {"left", "right"}:
            self.issue("drive", "DRIVE_SIDES", "Drive requires explicit left and right linked sides")
        used_wheels, used_motors = set(), set()
        for side in self.contract.drive_sides:
            ids = set(side.wheel_instance_ids); transmission = transmissions.get(side.transmission_id)
            if len(ids) != 2 or not ids <= wheels or ids & used_wheels:
                self.issue("drive", "DRIVE_SIDE_WHEELS", "Each side needs two distinct wheels, without sharing sides")
            used_wheels.update(ids)
            if transmission is None:
                self.issue("drive", "DRIVE_TRANSMISSION_MISSING", "Each side needs an explicit transmission")
                continue
            actuator = transmission.actuator.instance_id
            if actuator not in motors or actuator in used_motors:
                self.issue("drive", "INDEPENDENT_DRIVE_MOTORS", "Left/right sides require distinct drive motors")
            used_motors.add(actuator)
            powered = {key.split("/")[0] for key in self.ratios.get(transmission.id, {})}
            if not ids <= powered or not any(s.kind == "gear_mesh" for s in transmission.stages):
                self.issue("drive", "DRIVE_LINKAGE", "Both wheels on each side need a gear/shaft path from its motor")
            outputs = [p for p in transmission.outputs if p.instance_id in ids]
            if len(outputs) == 2:
                frames = [self.port(p, "drive") for p in outputs]
                values = self.ratios.get(transmission.id, {})
                if all(frames) and all("/".join(p.key()) in values for p in outputs):
                    a, b = (values["/".join(p.key())] for p in outputs)
                    if a*b*_dot(frames[0][1], frames[1][1]) <= 0 or not math.isclose(abs(a), abs(b), rel_tol=1e-6):
                        self.issue("drive", "DRIVE_WHEEL_DIRECTION", "Linked wheels on a side must have matching world angular direction and ratio")
        if used_wheels != wheels:
            self.issue("drive", "DRIVE_WHEEL_COVERAGE", "Every drive wheel must belong to exactly one powered side")
        kinds = {"pin_intake": "opposed_rollers", "pin_transfer": "gated_handoff", "scorer": "four_bar_gripper",
                 "cup_cradle": "independent_cup", "stack_interface": "stack_alignment"}
        mechanisms = {m.role: m for m in self.contract.mechanisms}
        for role, kind in kinds.items():
            mechanism = mechanisms.get(role)
            if mechanism is None or mechanism.kind != kind:
                self.issue(role, "MECHANISM_REQUIRED", f"Architecture A requires {kind}")
                continue
            members = set(mechanism.member_ids)
            if members - self.nodes.keys() or not role_ids[role] <= members:
                self.issue(role, "MECHANISM_MEMBERS", "Mechanism must cover its actual subsystem members")
            joints = [self.rels.get(i) for i in mechanism.joint_ids]
            if len(set(mechanism.joint_ids)) != len(joints) or any(j is None or j.kind == "fixed" for j in joints):
                self.issue(role, "MECHANISM_JOINTS", "Mechanism joints must be distinct existing moving relationships")
            for joint in joints:
                if joint and (joint.child_instance_id not in members or not set(joint.moving_member_ids) & members):
                    self.issue(role, "MECHANISM_JOINT_SCOPE", "Mechanism joint must move its declared members")
            selected = [transmissions.get(i) for i in mechanism.transmission_ids]
            powered = {key.split("/")[0] for t in selected if t for key in self.ratios.get(t.id, {})}
            if any(t is None for t in selected):
                self.issue(role, "MECHANISM_TRANSMISSION", "Mechanism references a missing transmission")
            if role != "stack_interface" and (not selected or not powered & members):
                self.issue(role, "MECHANISM_UNPOWERED", "Actuated mechanism needs a transmission output within its members")
            if role not in ("scorer", "stack_interface"):
                for joint in joints:
                    if joint and not set(joint.moving_member_ids) & powered:
                        self.issue(role, "JOINT_UNPOWERED", "Each required mechanism joint needs a driven moving member", joint.child_instance_id)
            if role == "pin_intake":
                rollers = require(role, "roller", 2); require(role, "guide", 1)
                if len(rollers) != 2 or not rollers <= powered or sum(j is not None and j.kind == "revolute" for j in joints) < 2:
                    self.issue(role, "ROLLER_DRIVE", "Two rotating, powered opposed rollers are required")
                self.check_roller_direction(rollers, selected, mechanism.motor_speeds_rpm)
            elif role == "pin_transfer":
                require(role, "gate", 1); require(role, "guide", 1)
                if not joints:
                    self.issue(role, "GATE_JOINT_REQUIRED", "Single-Pin handoff requires a moving gate")
            elif role == "scorer":
                require(role, "gripper", 1)
                self.check_four_bar(mechanism)
            elif role == "cup_cradle":
                cradles = require(role, "cradle", 1)
                if mechanism.retention_member_ids or mechanism.release_joint_id is not None:
                    retainers = set(mechanism.retention_member_ids)
                    if (not retainers or len(retainers) != len(mechanism.retention_member_ids)
                            or not retainers <= members & role_ids[role]
                            or any(self.purpose(i) not in ("retainer", "guide", "latch") for i in retainers)):
                        self.issue(role, "CUP_RETENTION_HARDWARE", "Cup retention needs distinct actual guide/retainer/latch members in its own subsystem")
                    release = self.rels.get(mechanism.release_joint_id)
                    if (release is None or release.kind != "revolute" or release.id not in mechanism.joint_ids
                            or not cradles.intersection(release.moving_member_ids)
                            or not powered.intersection(release.moving_member_ids)):
                        self.issue(role, "CUP_RELEASE_JOINT", "Cup tilt release must be a declared powered revolute joint moving the cradle")
                    self.connected_group(members, [r.id for r in self.rels.values()
                        if r.parent_instance_id in members and r.child_instance_id in members], role)
                else:
                    require(role, "latch", 1)
                    if len(joints) < 2:
                        self.issue(role, "CUP_LATCH_TILT", "Independent Cup retention/release requires latch and tilt joints, or declared retaining hardware and tilt release")
                other = {t.actuator.instance_id for m in self.contract.mechanisms if m.role in ("pin_intake", "pin_transfer", "scorer")
                         for i in m.transmission_ids if (t := transmissions.get(i))}
                if any(t and t.actuator.instance_id in other for t in selected):
                    self.issue(role, "CUP_NOT_INDEPENDENT", "Cup actuator must be independent of the Pin path actuators")
            else:
                require(role, "guide", 1)

    def check_roller_direction(self, rollers, transmissions, motor_speeds):
        actuators = {t.actuator.instance_id for t in transmissions if t}
        if len(actuators) > 1 and (set(motor_speeds) != actuators or any(v == 0 for v in motor_speeds.values())):
            self.issue("pin_intake", "ROLLER_MOTOR_COMMANDS", "Independent rollers require nonzero signed intended motor RPM for each actual actuator")
            return
        velocities = {}
        for transmission in transmissions:
            if transmission is None:
                continue
            outputs = [p for p in transmission.outputs if p.instance_id in rollers]
            ratios = self.ratios.get(transmission.id, {})
            rpm = motor_speeds.get(transmission.actuator.instance_id, 1.)
            for output in outputs:
                frame = self.port(output, "pin_intake")
                ratio = ratios.get("/".join(output.key()))
                if frame and ratio is not None:
                    velocity = tuple(a*ratio*rpm for a in frame[1])
                    previous = velocities.get(output.instance_id)
                    if previous and _dot(previous, velocity) <= 0:
                        self.issue("pin_intake", "ROLLER_COMMAND_CONFLICT", "Actuator paths disagree on the same roller's intended direction", output.instance_id)
                    velocities[output.instance_id] = velocity
        if len(rollers) == 2 and set(velocities) == rollers:
            a, b = (velocities[i] for i in sorted(rollers))
            if _norm(a) > 0 and _norm(b) > 0 and _dot(a, b)/(_norm(a)*_norm(b)) < -1+1e-6:
                return
        self.issue("pin_intake", "ROLLER_DIRECTION", "Powered rollers must have opposite world angular directions under the declared mechanical path or motor commands")

    def check_four_bar(self, mechanism):
        bar = mechanism.four_bar
        if bar is None:
            self.issue("scorer", "FOUR_BAR_REQUIRED", "Scorer requires explicit ground, two links, carrier, gripper and four pivot joints")
            return
        ground, carrier = bar.ground_id, bar.carrier_id
        l1, l2 = bar.link_ids
        members = {ground, l1, l2, carrier, bar.gripper_id}
        if len(members) != 5 or not members <= set(mechanism.member_ids):
            self.issue("scorer", "FOUR_BAR_MEMBERS", "Four-bar needs distinct, explicitly declared physical members")
        if any(self.purpose(i) != "structure" for i in (ground, l1, l2, carrier)) or self.purpose(bar.gripper_id) != "gripper":
            self.issue("scorer", "FOUR_BAR_PARTS", "Ground, links and carrier need real structure; tool needs a gripper")
        expected = {frozenset(pair) for pair in ((ground,l1), (l1,carrier), (carrier,l2), (l2,ground))}
        actual, axes, pivots = set(), [], {}
        for identity in bar.joint_ids:
            joint = self.rels.get(identity)
            if joint is None or joint.kind != "revolute":
                self.issue("scorer", "FOUR_BAR_PIVOTS", "Four-bar must contain four actual revolute pivot relationships")
                continue
            actual.add(frozenset((joint.parent_instance_id, joint.child_instance_id)))
            for instance_id, port_id in ((joint.parent_instance_id, joint.parent_port_id), (joint.child_instance_id, joint.child_port_id)):
                pivot = self.port(PortRef(instance_id=instance_id, port_id=port_id), "scorer")
                if pivot:
                    pivots.setdefault(instance_id, []).append(pivot[0])
            port = self.port(PortRef(instance_id=joint.parent_instance_id, port_id=joint.parent_port_id), "scorer")
            if port:
                frame = self.world[joint.parent_instance_id].compose(port[2].frame)
                axis = tuple(sum(frame.matrix[4*c+r]*joint.axis[c] for c in range(3)) for r in range(3))
                axes.append(axis)
        if actual != expected or len(set(bar.joint_ids)) != 4 or not set(bar.joint_ids) <= set(mechanism.joint_ids):
            self.issue("scorer", "FOUR_BAR_LOOP", "Pivot graph must close ground → link → carrier → other link → ground")
        powered = {key.split("/")[0] for tid in mechanism.transmission_ids for key in self.ratios.get(tid, {})}
        if not powered.intersection((l1, l2)):
            self.issue("scorer", "FOUR_BAR_UNPOWERED", "Scorer transmission must drive a linkage member, not merely a nearby part")
        tool_joints = [self.rels.get(i) for i in mechanism.joint_ids if i not in bar.joint_ids]
        if (bar.gripper_id not in self.integrated_units and
                not any(j and bar.gripper_id in j.moving_member_ids and set(j.moving_member_ids) & powered for j in tool_joints)):
            self.issue("scorer", "GRIPPER_ACTUATION", "Scoring gripper requires a driven opening/retention joint beyond the four-bar pivots", bar.gripper_id)
        if bar.gripper_id in self.integrated_units:
            allowed = set(mechanism.member_ids) - {ground, l1, l2}
            reached, pending = set(), [carrier]
            while pending:
                current = pending.pop()
                if current in reached:
                    continue
                reached.add(current)
                for rel in self.rels.values():
                    a, b = rel.parent_instance_id, rel.child_instance_id
                    if rel.kind == "fixed" and a in allowed and b in allowed:
                        if a == current: pending.append(b)
                        if b == current: pending.append(a)
            if bar.gripper_id not in reached:
                self.issue("scorer", "OEM_CARRIER_MOUNT_REQUIRED", "Purchased gripper must attach to the four-bar carrier through explicit fixed mounting hardware", bar.gripper_id)
        if axes and any(abs(_dot(axes[0], axis)) < 1-1e-6 for axis in axes[1:]):
            self.issue("scorer", "FOUR_BAR_AXES", "Four-bar revolute axes must be parallel in world coordinates")
        lengths = {}
        for identity in (ground, l1, l2, carrier):
            points = pivots.get(identity, [])
            if len(points) != 2 or math.dist(*points) <= .0001:
                self.issue("scorer", "FOUR_BAR_PIVOT_SPAN", "Each four-bar member needs two separated measured pivots", identity)
            else:
                lengths[identity] = math.dist(*points)
        if len(lengths) == 4 and (abs(lengths[ground]-lengths[carrier]) > .0001 or abs(lengths[l1]-lengths[l2]) > .0001):
            self.issue("scorer", "FOUR_BAR_PARALLELOGRAM", "This bounded recipe requires equal parallel-link lengths and matching ground/carrier pivot spacing")
        # Assembly.validate_revision has already checked closure at this pose.
        # Real grippers may mount through sourced brackets, shafts and adapters;
        # require their explicit mechanism graph rather than a fictitious direct
        # carrier-to-gripper mate that omits the intervening hardware.
        mounted_members = set(mechanism.member_ids)
        self.connected_group(mounted_members, [r.id for r in self.rels.values()
            if r.parent_instance_id in mounted_members and r.child_instance_id in mounted_members], "scorer")

    def run(self):
        graph_valid = True
        try:
            A.validate_revision(self.revision)
            self.world = A.world_transforms(self.snapshot)
        except (TachyonError, ValueError) as error:
            graph_valid = False
            self.issue("robot", getattr(error, "code", "INVALID_ASSEMBLY"), str(error))
        if self.contract is None:
            self.issue("robot", "ROBOT_CONTRACT_MISSING", "Supply a source-bound architecture-A hardware contract")
        elif graph_valid:
            self.check_bom()
            self.check_integrated_units()
            self.check_mounts()
            self.check_supports()
            self.check_transmissions()
            self.check_roles()
        issues = {A.content_hash(i.json_data()): i for i in self.missing}
        missing = tuple(sorted(issues.values(), key=lambda i: (i.role, i.code, i.instance_ids, i.message)))
        uncertainties = ["Pin/Cup object interaction, orientation and physical retention are unverified."]
        objects = {o.kind: o for o in self.contract.objects} if self.contract else {}
        for kind in ("pin", "cup"):
            obj = objects.get(kind)
            if obj is None or obj.diameter_m is None or obj.height_m is None:
                uncertainties.append(f"{kind}: official dimensions are unspecified; no dimensions were invented.")
            if obj:
                uncertainties.append(f"{kind}: declared source {obj.source_url}; {obj.uncertainty}")
        complete = graph_valid and self.contract is not None and not missing
        embedded_counts = Counter()
        for unit in self.integrated_units.values():
            for child in unit.children:
                embedded_counts[child.purpose] += child.quantity
        report = RobotQualificationReport(design_id=self.snapshot.design_id, revision_id=self.revision.id,
            engineering_hash=self.revision.engineering_hash,
            contract_hash=A.content_hash(_canonical(self.contract.json_data())) if self.contract else None,
            report_hash="", status="ready" if complete else "incomplete", graph_valid=graph_valid,
            hardware_qualified=complete, complete_robot=complete, missing=missing,
            provenance=tuple(self.provenance), counts=dict(sorted(Counter(b.purpose for b in self.bom.values()).items())),
            role_counts={role: sum(n.subsystem_id == role for n in self.nodes.values()) for role in ROLES},
            transmission_ratios=dict(sorted(self.ratios.items())),
            integrated_units=tuple(self.integrated_units.values()),
            integrated_unit_counts=dict(sorted(embedded_counts.items())),
            uncertainties=tuple(uncertainties))
        data = report.json_data(); data.pop("reportHash")
        return report.model_copy(update={"report_hash": A.content_hash(data)})
