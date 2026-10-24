"""Original, metadata-only assembly placement; no CAD loading or motion certification.

Matrices are local-to-placement-parent, column-major, metres/Y-up (like Three.js).
Placement hierarchy and declared attachments are deliberately separate. A native
import parent is never evidence of a physical mate. This service checks rigid
placements and port closure, not fit, hardware completeness, collision, actuation,
or competition task suitability. Those missing qualifications keep readiness
incomplete, even for a graph made entirely from imported components.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
import math
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from .errors import TachyonError
from .models import Model, PreparedComponent, Vector3


class Record(Model):
    model_config = ConfigDict(frozen=True)


def content_hash(value) -> str:
    """Canonical JSON hash; callers supply already ordered engineering records."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def stable_id(namespace: str, *keys: str) -> str:
    return namespace + "-" + content_hash(list(keys))[:24]


def _fail(code, message):
    raise TachyonError(code, message)


def _unit(axis):
    if len(axis) != 3 or not all(math.isfinite(v) for v in axis) or abs(sum(v*v for v in axis) - 1) > 1e-8:
        raise ValueError("Axis must be a finite unit vector")
    return axis


class RigidTransform(Record):
    matrix: tuple[float, ...] = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.)

    @field_validator("matrix", mode="before")
    @classmethod
    def rigid(cls, values):
        if not isinstance(values, (tuple, list)) or len(values) != 16:
            raise ValueError("Transform must have 16 column-major values")
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
            raise ValueError("Transform values must be finite real numbers")
        if any(abs(values[i] - expected) > 1e-9 for i, expected in ((3, 0), (7, 0), (11, 0), (15, 1))):
            raise ValueError("Transform must be affine, with homogeneous row [0,0,0,1]")
        cols = [values[4*c:4*c+3] for c in range(3)]
        if any(abs(sum(a*b for a, b in zip(cols[i], cols[j])) - float(i == j)) > 1e-8
               for i in range(3) for j in range(3)):
            raise ValueError("Transform rotation must be orthonormal; scale/shear are forbidden")
        a, b, c = cols
        determinant = a[0]*(b[1]*c[2]-b[2]*c[1]) - b[0]*(a[1]*c[2]-a[2]*c[1]) + c[0]*(a[1]*b[2]-a[2]*b[1])
        if abs(determinant - 1) > 1e-8:
            raise ValueError("Transform rotation must preserve handedness")
        normalized = [0. if abs(v) < 5e-13 else round(v, 12) for v in values]
        for index, expected in ((3, 0.), (7, 0.), (11, 0.), (15, 1.)):
            normalized[index] = expected
        return tuple(normalized)

    @classmethod
    def translation(cls, x: float, y: float, z: float):
        return cls(matrix=(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1))

    @classmethod
    def rotation(cls, axis: Vector3, angle_rad: float):
        x, y, z = _unit(axis)
        c, s, d = math.cos(angle_rad), math.sin(angle_rad), 1-math.cos(angle_rad)
        return cls(matrix=(c+x*x*d, y*x*d+z*s, z*x*d-y*s, 0,
                           x*y*d-z*s, c+y*y*d, z*y*d+x*s, 0,
                           x*z*d+y*s, y*z*d-x*s, c+z*z*d, 0, 0, 0, 0, 1))

    def compose(self, other: RigidTransform) -> RigidTransform:
        a, b = self.matrix, other.matrix
        return RigidTransform(matrix=tuple(sum(a[4*k+r]*b[4*c+k] for k in range(4))
                                           for c in range(4) for r in range(4)))

    def inverse(self) -> RigidTransform:
        m = self.matrix
        return RigidTransform(matrix=tuple(m[4*r+c] if c < 3 and r < 3 else
                                           -sum(m[4*r+k]*m[12+k] for k in range(3)) if c == 3 and r < 3 else
                                           float(c == r) for c in range(4) for r in range(4)))

    def point(self, point: Vector3 = (0., 0., 0.)) -> Vector3:
        return tuple(sum(self.matrix[4*c+r]*point[c] for c in range(3)) + self.matrix[12+r] for r in range(3))


class AttachmentPort(Record):
    id: str = Field(min_length=1)
    kind: Literal["mount", "shaft", "bearing", "revolute", "prismatic"]
    frame: RigidTransform
    evidence: str = Field(min_length=1)
    frame_basis: Literal["measured", "axis_only"] = "measured"
    position_tolerance_m: float = Field(default=1e-5, gt=0, le=.001)
    angle_tolerance_rad: float = Field(default=1e-4, gt=0, le=.01)

    @field_validator("evidence")
    @classmethod
    def evidence_present(cls, value):
        if not value.strip():
            raise ValueError("Port needs measurement evidence")
        return value


class InvalidGeometryInstance(Record):
    path: str
    name: str
    definition_name: str


class GeometryValidation(Record):
    status: Literal["valid", "source_defects", "unknown"] = "unknown"
    native_brep_valid: bool | None = None
    invalid_component_instances: tuple[InvalidGeometryInstance, ...] = ()
    invalid_definition_count: int | None = Field(default=0, ge=0)
    diagnostics: str | None = None
    native_bounds_max_error_mm: float | None = Field(default=None, ge=0)
    qualified_for_robot_generation: bool | None = None
    limitations: tuple[str, ...] = ()


class ComponentDefinition(Record):
    """Immutable identity/geometry references, never source bytes or CAD parents.

    from_prepared accepts the existing importer receipt. Legacy position/axis
    ports receive a deterministic roll only for placement, labeled axis_only.
    Supply measured full frames explicitly before claiming a verified mate.
    Operation qualification is supplied by the caller's current rights check;
    a display receipt alone never grants assembly-placement permission.
    In particular, call RightsPolicy.require for assembly_placement before
    supplying that operation; private-inspection terms cannot authorize it.
    """
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    sku: str | None = None
    source_url: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    mesh_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    mesh_url: str = Field(min_length=1)
    catalog_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    origin_kind: Literal["manufacturer_cad", "community_component_model", "tachyon_authored"]
    geometry_class: Literal["verified_imported_component", "conceptual", "placeholder", "test_fixture"]
    declared_use: str = Field(min_length=1)
    qualified_operations: tuple[str, ...] = ()
    attribution: str = ""
    ports: tuple[AttachmentPort, ...] = ()
    reference_only: bool = False
    geometry_validation: GeometryValidation = GeometryValidation()

    @field_validator("ports")
    @classmethod
    def ordered_ports(cls, values):
        return tuple(sorted(values, key=lambda port: port.id))

    @field_validator("qualified_operations")
    @classmethod
    def ordered_operations(cls, values):
        return tuple(sorted(set(values)))

    @model_validator(mode="after")
    def identities(self):
        _unique(self.ports, "port")
        if self.origin_kind == "tachyon_authored" and self.geometry_class == "verified_imported_component":
            raise ValueError("Authored fixtures are not imported manufacturer components")
        return self

    @classmethod
    def from_prepared(cls, prepared: PreparedComponent | Mapping, *, ports=None, qualified_operations=None):
        data = prepared.json_data() if isinstance(prepared, PreparedComponent) else dict(prepared)
        operations = data.pop("qualifiedOperations", ())
        receipt = PreparedComponent.model_validate(data)
        if ports is None:
            ports = []
            for port in receipt.ports:
                # Columns x,y,z; local +Z follows the measured interface axis.
                norm = math.sqrt(sum(v*v for v in port.axis))
                z = tuple(v/norm for v in port.axis)
                seed = (1., 0., 0.) if abs(z[0]) < .9 else (0., 1., 0.)
                dot = sum(a*b for a, b in zip(seed, z))
                x = tuple(a-dot*b for a, b in zip(seed, z))
                norm = math.sqrt(sum(v*v for v in x))
                x = tuple(v/norm for v in x)
                y = (z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0])
                ports.append(AttachmentPort(id=port.id, kind=port.kind, evidence=port.evidence,
                                            frame_basis="axis_only", frame=RigidTransform(matrix=(
                                                *x, 0, *y, 0, *z, 0, *port.position_m, 1))))
        keys = ("id", "name", "sku", "source_url", "source_sha256", "mesh_sha256", "mesh_url",
                "catalog_fingerprint", "origin_kind", "geometry_class", "declared_use", "attribution")
        return cls(**{key: getattr(receipt, key) for key in keys}, ports=tuple(ports),
                   reference_only=receipt.reference_only,
                   geometry_validation=GeometryValidation.model_validate(receipt.geometry_validation),
                   qualified_operations=tuple(sorted(set(operations if qualified_operations is None else qualified_operations))))


class ComponentInstance(Record):
    id: str = Field(min_length=1)
    component_id: str = Field(min_length=1)
    subsystem_id: str = Field(min_length=1)
    parent_id: str | None = None
    transform: RigidTransform = RigidTransform()


class Subsystem(Record):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class MateVerification(Record):
    """Caller-supplied physical-mate evidence for these exact sources and ports."""
    parent_source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    child_source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    parent_port_id: str = Field(min_length=1)
    child_port_id: str = Field(min_length=1)
    kind: Literal["fixed", "revolute", "prismatic"] = "fixed"
    mate_transform: RigidTransform = RigidTransform()
    evidence: str = Field(pattern=r"\S")


class Relationship(Record):
    id: str = Field(min_length=1)
    parent_instance_id: str
    parent_port_id: str
    child_instance_id: str
    child_port_id: str
    kind: Literal["fixed", "revolute", "prismatic"] = "fixed"
    mate_transform: RigidTransform = RigidTransform()
    axis: Vector3 | None = None  # in the parent port frame
    limits: tuple[float, float] | None = None  # radians or metres, by kind
    position: float = 0.
    moving_member_ids: tuple[str, ...] = ()
    verification: MateVerification | None = None

    @model_validator(mode="after")
    def joint_contract(self):
        if self.parent_instance_id == self.child_instance_id:
            raise ValueError("A component cannot attach to itself")
        if self.kind == "fixed":
            if self.axis is not None or self.limits is not None or self.moving_member_ids or self.position != 0:
                raise ValueError("Fixed attachments cannot declare joint motion")
        elif self.axis is None or self.limits is None or not self.moving_member_ids:
            raise ValueError("Joints need an axis, limits and explicit moving members")
        else:
            _unit(self.axis)
            if self.limits[0] >= self.limits[1] or not self.limits[0] <= self.position <= self.limits[1]:
                raise ValueError("Joint limits must be ordered and contain its position")
            if len(set(self.moving_member_ids)) != len(self.moving_member_ids):
                raise ValueError("Duplicate joint moving member")
        return self

    def offset(self):
        motion = RigidTransform()
        if self.kind == "revolute":
            motion = RigidTransform.rotation(self.axis, self.position)
        elif self.kind == "prismatic":
            motion = RigidTransform.translation(*(v*self.position for v in self.axis))
        return motion.compose(self.mate_transform)


class AssemblySnapshot(Record):
    schema_version: Literal[1] = 1
    design_id: str = Field(min_length=1)
    recipe_id: str = Field(min_length=1)
    configuration_id: str = Field(min_length=1)
    units: Literal["m"] = "m"
    up_axis: Literal["Y"] = "Y"
    matrix_layout: Literal["column-major"] = "column-major"
    root_instance_id: str
    required_instance_ids: tuple[str, ...]
    components: tuple[ComponentDefinition, ...]
    instances: tuple[ComponentInstance, ...]
    subsystems: tuple[Subsystem, ...]
    relationships: tuple[Relationship, ...]


class AssemblyRevision(Record):
    schema_version: Literal[1] = 1
    id: str
    parent_revision_id: str | None = None
    engineering_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    assembly: AssemblySnapshot


class ReadinessReport(Record):
    status: Literal["incomplete"] = "incomplete"
    graph_valid: Literal[True] = True
    complete_robot: Literal[False] = False
    blockers: tuple[str, ...]
    limitations: tuple[str, ...] = (
        "Port closure is a geometric check, not verified physical fit or simulation.",
        "Hardware completeness, interference, drive paths and task capabilities are not qualified.",
        "Joint metadata does not enable certified motion or a mechanism pose solver.",
        "Source bytes, mesh availability and operation rights require current caller-side checks.",
    )


def _unique(records, label):
    if len({record.id for record in records}) != len(records):
        _fail("DUPLICATE_ID", f"Duplicate {label} identity")


def _ordered(snapshot):
    data = snapshot.json_data()
    for key in ("components", "instances", "subsystems", "relationships"):
        data[key] = sorted(data[key], key=lambda row: row["id"])
    for component in data["components"]:
        component["ports"] = sorted(component["ports"], key=lambda row: row["id"])
        component["qualifiedOperations"] = sorted(set(component["qualifiedOperations"]))
    for relationship in data["relationships"]:
        relationship["movingMemberIds"] = sorted(relationship["movingMemberIds"])
    data["requiredInstanceIds"] = sorted(data["requiredInstanceIds"])
    return data


def descendants(snapshot: AssemblySnapshot, instance_id: str) -> frozenset[str]:
    found = {instance_id}
    while True:
        more = {node.id for node in snapshot.instances if node.parent_id in found} - found
        if not more:
            return frozenset(found)
        found.update(more)


def world_transforms(snapshot: AssemblySnapshot) -> dict[str, RigidTransform]:
    """Resolve placement parents only; this creates no attachment relationships."""
    _unique(snapshot.instances, "instance")
    pending = {node.id: node for node in snapshot.instances}
    world = {}
    while pending:
        ready = [node for node in pending.values() if node.parent_id is None or node.parent_id in world]
        if not ready:
            _fail("INVALID_PLACEMENT_HIERARCHY", "Placement parents contain a cycle or dangling reference")
        for node in ready:
            world[node.id] = node.transform if node.parent_id is None else world[node.parent_id].compose(node.transform)
            del pending[node.id]
    return world


def _port(snapshot, instance_id, port_id):
    instance = next((i for i in snapshot.instances if i.id == instance_id), None)
    if instance is None:
        _fail("DANGLING_REFERENCE", f"Unknown component instance: {instance_id}")
    component = next((c for c in snapshot.components if c.id == instance.component_id), None)
    if component is None:
        _fail("MISSING_COMPONENT", f"Missing prepared definition: {instance.component_id}")
    port = next((p for p in component.ports if p.id == port_id), None)
    if port is None:
        _fail("MISSING_PORT", f"Unknown attachment port: {instance_id}/{port_id}")
    return component, port


def validate_assembly(snapshot: AssemblySnapshot) -> ReadinessReport:
    """Reject invalid engineering graphs. A successful check is never readiness."""
    for label in ("components", "instances", "subsystems", "relationships"):
        _unique(getattr(snapshot, label), label)
    nodes = {node.id: node for node in snapshot.instances}
    definitions = {c.id: c for c in snapshot.components}
    subsystems = {s.id for s in snapshot.subsystems}
    root = nodes.get(snapshot.root_instance_id)
    if root is None or root.parent_id is not None:
        _fail("INVALID_ROOT", "Assembly needs an existing unparented root")
    if len(set(snapshot.required_instance_ids)) != len(snapshot.required_instance_ids):
        _fail("DUPLICATE_ID", "Duplicate required component instance identity")
    if set(snapshot.required_instance_ids) - nodes.keys():
        _fail("MISSING_REQUIRED_PART", "A recipe-required component instance is missing")
    for node in nodes.values():
        if node.component_id not in definitions:
            _fail("MISSING_COMPONENT", f"Missing prepared definition: {node.component_id}")
        definition = definitions[node.component_id]
        if definition.reference_only:
            _fail("REFERENCE_ONLY_COMPONENT", "Reference inspection geometry cannot become an assembly design part")
        quality = definition.geometry_validation
        if (quality.qualified_for_robot_generation is False or quality.native_brep_valid is False
                or quality.invalid_definition_count or quality.invalid_component_instances):
            _fail("GEOMETRY_NOT_QUALIFIED", "Source geometry diagnostics prohibit assembly generation")
        if "assembly_placement" not in definition.qualified_operations:
            _fail("ASSEMBLY_RIGHTS_NOT_QUALIFIED", "A display receipt does not authorize assembly placement")
        if node.subsystem_id not in subsystems:
            _fail("DANGLING_REFERENCE", f"Unknown subsystem: {node.subsystem_id}")
        if node.id != root.id and node.parent_id is None:
            _fail("INVALID_PLACEMENT_HIERARCHY", "Every non-root placement needs an explicit parent")
    if subsystems != {node.subsystem_id for node in nodes.values()}:
        _fail("EMPTY_SUBSYSTEM", "A named subsystem has no component members")
    world = world_transforms(snapshot)
    neighbors = {key: set() for key in nodes}
    for rel in snapshot.relationships:
        parent, pp = _port(snapshot, rel.parent_instance_id, rel.parent_port_id)
        child, cp = _port(snapshot, rel.child_instance_id, rel.child_port_id)
        neighbors[rel.parent_instance_id].add(rel.child_instance_id)
        neighbors[rel.child_instance_id].add(rel.parent_instance_id)
        allowed = {"fixed": {"mount", "shaft", "bearing"},
                   "revolute": {"shaft", "bearing", "revolute"}, "prismatic": {"prismatic"}}[rel.kind]
        if pp.kind not in allowed or cp.kind not in allowed:
            _fail("INCOMPATIBLE_PORT", f"Port kinds do not support declared {rel.kind} relationship")
        if rel.kind != "fixed":
            moving = descendants(snapshot, rel.child_instance_id)
            if set(rel.moving_member_ids) != moving or rel.parent_instance_id in moving:
                _fail("INVALID_JOINT_MEMBERS", "Moving members must exactly name the child placement subtree")
        expected = world[rel.parent_instance_id].compose(pp.frame).compose(rel.offset())
        actual = world[rel.child_instance_id].compose(cp.frame)
        delta = expected.inverse().compose(actual).matrix
        distance = math.sqrt(sum(v*v for v in delta[12:15]))
        angle = math.acos(max(-1., min(1., (delta[0]+delta[5]+delta[10]-1)/2)))
        if distance > min(pp.position_tolerance_m, cp.position_tolerance_m) or angle > min(pp.angle_tolerance_rad, cp.angle_tolerance_rad):
            _fail("PORT_ALIGNMENT", f"Attachment ports do not close: {rel.id}")
        if rel.verification:
            v = rel.verification
            if (v.parent_source_sha256, v.child_source_sha256, v.parent_port_id, v.child_port_id, v.kind, v.mate_transform) != (
                    parent.source_sha256, child.source_sha256, pp.id, cp.id, rel.kind, rel.mate_transform) or "axis_only" in (pp.frame_basis, cp.frame_basis):
                _fail("STALE_MATE_EVIDENCE", "Verified mates need matching sources, ports and measured full frames")
    reached, pending = set(), [root.id]
    while pending:
        current = pending.pop()
        if current not in reached:
            reached.add(current)
            pending.extend(neighbors[current] - reached)
    if reached != set(nodes):
        _fail("DISCONNECTED_ASSEMBLY", "Every component must connect to the root through explicit attachments")
    blockers = ["UNQUALIFIED_HARDWARE_COMPLETENESS", "UNQUALIFIED_TASK_CAPABILITIES", "UNQUALIFIED_CLEARANCE_AND_DRIVE_PATHS"]
    if any(c.geometry_class != "verified_imported_component" for c in snapshot.components):
        blockers.append("NON_AUTHENTIC_GEOMETRY")
    if any(c.geometry_validation.qualified_for_robot_generation is None for c in snapshot.components):
        blockers.append("GEOMETRY_QUALIFICATION_UNKNOWN")
    if any(rel.verification is None for rel in snapshot.relationships):
        blockers.append("UNVERIFIED_PHYSICAL_MATES")
    return ReadinessReport(blockers=tuple(blockers))


def validate_revision(revision: AssemblyRevision) -> ReadinessReport:
    report = validate_assembly(revision.assembly)
    digest = content_hash(_ordered(revision.assembly))
    expected_id = stable_id("revision", revision.assembly.design_id, revision.parent_revision_id or "", digest)
    if revision.engineering_hash != digest or revision.id != expected_id:
        _fail("REVISION_HASH_MISMATCH", "Revision content does not match its engineering identity")
    return report


def _revision(snapshot, parent=None):
    validate_assembly(snapshot)
    snapshot = AssemblySnapshot.model_validate(_ordered(snapshot))
    digest = content_hash(snapshot.json_data())
    return AssemblyRevision(id=stable_id("revision", snapshot.design_id, parent or "", digest),
                            parent_revision_id=parent, engineering_hash=digest, assembly=snapshot)


class AssemblyService:
    """Small pure service. The caller owns rights/asset rechecks and persistence."""
    def __init__(self, components: Iterable[ComponentDefinition]):
        components = tuple(components)
        _unique(components, "component definition")
        self._components = {component.id: component for component in components}

    def build(self, *, design_id: str, recipe_id: str, configuration_id: str,
              root_instance_id: str, instances: Iterable[ComponentInstance],
              subsystems: Iterable[Subsystem], relationships: Iterable[Relationship],
              required_instance_ids: Iterable[str] | None = None) -> AssemblyRevision:
        instances = tuple(instances)
        used = {node.component_id for node in instances}
        if used - self._components.keys():
            _fail("MISSING_COMPONENT", "Required prepared component definitions are unavailable")
        return _revision(AssemblySnapshot(design_id=design_id, recipe_id=recipe_id,
                         configuration_id=configuration_id, root_instance_id=root_instance_id,
                         required_instance_ids=tuple(sorted(node.id for node in instances)) if required_instance_ids is None
                                               else tuple(sorted(required_instance_ids)),
                         components=tuple(self._components[key] for key in sorted(used)),
                         instances=instances, subsystems=tuple(subsystems), relationships=tuple(relationships)))

    def validate(self, revision: AssemblyRevision) -> ReadinessReport:
        report = validate_revision(revision)
        for definition in revision.assembly.components:
            if self._components.get(definition.id) != definition:
                _fail("CATALOG_CHANGED", "Revision component metadata differs from the current prepared catalog")
        return report

    def place(self, revision: AssemblyRevision, instance_id: str, transform: RigidTransform,
              *, configuration_id: str | None = None) -> AssemblyRevision:
        """Change a local placement, carrying descendants; all attachments must close.

        Root movement is supported. Remount a connected child with align_ports;
        arbitrary movement which breaks a declared attachment is rejected.
        """
        self.validate(revision)
        if instance_id not in {node.id for node in revision.assembly.instances}:
            _fail("DANGLING_REFERENCE", "Cannot place an unknown component instance")
        data = revision.assembly.json_data()
        data["configurationId"] = configuration_id or revision.assembly.configuration_id
        for node in data["instances"]:
            if node["id"] == instance_id:
                node["transform"] = transform.json_data()
        return _revision(AssemblySnapshot.model_validate(data), revision.id)

    def align_ports(self, revision: AssemblyRevision, relationship_id: str, *,
                    parent_port_id: str | None = None, child_port_id: str | None = None,
                    mate_transform: RigidTransform | None = None,
                    configuration_id: str | None = None) -> AssemblyRevision:
        """Solve Wchild = Wparent Pparent Joint(q) Mate inverse(Pchild).

        Descendants keep their local transforms. Cross-subtree constraints are
        rechecked and rejected if opened. Remounting clears prior physical-mate
        evidence; geometrical alignment never manufactures verification.
        """
        self.validate(revision)
        rel = next((r for r in revision.assembly.relationships if r.id == relationship_id), None)
        if rel is None:
            _fail("DANGLING_REFERENCE", "Unknown attachment relationship")
        if rel.parent_instance_id in descendants(revision.assembly, rel.child_instance_id):
            _fail("UNSUPPORTED_PLACEMENT", "An attachment cannot move its own placement ancestor")
        data = rel.json_data()
        data.update(parentPortId=parent_port_id or rel.parent_port_id,
                    childPortId=child_port_id or rel.child_port_id, verification=None)
        if mate_transform is not None:
            data["mateTransform"] = mate_transform.json_data()
        updated = Relationship.model_validate(data)
        _, pp = _port(revision.assembly, updated.parent_instance_id, updated.parent_port_id)
        _, cp = _port(revision.assembly, updated.child_instance_id, updated.child_port_id)
        world = world_transforms(revision.assembly)
        target = world[updated.parent_instance_id].compose(pp.frame).compose(updated.offset()).compose(cp.frame.inverse())
        node = next(n for n in revision.assembly.instances if n.id == updated.child_instance_id)
        local = target if node.parent_id is None else world[node.parent_id].inverse().compose(target)
        assembly = revision.assembly.json_data()
        assembly["configurationId"] = configuration_id or revision.assembly.configuration_id
        assembly["relationships"] = [updated.json_data() if r["id"] == rel.id else r for r in assembly["relationships"]]
        for instance in assembly["instances"]:
            if instance["id"] == node.id:
                instance["transform"] = local.json_data()
        return _revision(AssemblySnapshot.model_validate(assembly), revision.id)


def build_fixture_demonstrator(service: AssemblyService, *, base_component_id: str,
                                carrier_component_id: str, tool_component_id: str,
                                configuration_id: Literal["lower", "raised"] = "lower",
                                design_id: str = "tachyon-port-fixture") -> AssemblyRevision:
    """Original three-part attachment recipe; computational demonstration only.

    Requires caller-provided, authored test_fixture metadata, never VEX parts or
    invented geometry references. Base ports: lower/raised; carrier: mount/tool;
    tool: mount. Both configurations use the exact supplied local port frames.
    This is neither a robot recipe nor an authentic-CAD acceptance demonstration.
    """
    if configuration_id not in ("lower", "raised"):
        _fail("UNSUPPORTED_CONFIGURATION", "Fixture supports lower and raised attachments only")
    definitions = []
    for key in (base_component_id, carrier_component_id, tool_component_id):
        definition = service._components.get(key)
        if definition is None:
            _fail("MISSING_COMPONENT", "Original demonstrator component is unavailable")
        if definition.origin_kind != "tachyon_authored" or definition.geometry_class != "test_fixture":
            _fail("NOT_ORIGINAL_FIXTURE", "This demonstrator accepts only original, explicitly labeled test fixtures")
        definitions.append(definition)

    def frame(component, key):
        port = next((p for p in component.ports if p.id == key and p.kind == "mount"), None)
        if port is None:
            _fail("MISSING_PORT", f"Fixture needs a measured mount port: {component.id}/{key}")
        return port.frame

    base, carrier, tool = definitions
    carrier_local = frame(base, configuration_id).compose(frame(carrier, "mount").inverse())
    tool_local = frame(carrier, "tool").compose(frame(tool, "mount").inverse())
    base_id, carrier_id, tool_id = (stable_id("instance", design_id, role) for role in ("base", "carrier", "tool"))
    return service.build(design_id=design_id, recipe_id="tachyon-original-port-fixture-v1",
                         configuration_id=configuration_id, root_instance_id=base_id,
                         subsystems=(Subsystem(id="support", name="Original fixture support"),
                                     Subsystem(id="carrier", name="Original fixture carrier")),
                         instances=(ComponentInstance(id=base_id, component_id=base.id, subsystem_id="support"),
                                    ComponentInstance(id=carrier_id, component_id=carrier.id, subsystem_id="carrier",
                                                      parent_id=base_id, transform=carrier_local),
                                    ComponentInstance(id=tool_id, component_id=tool.id, subsystem_id="carrier",
                                                      parent_id=carrier_id, transform=tool_local)),
                         relationships=(Relationship(id="carrier-mount", parent_instance_id=base_id,
                                                     parent_port_id=configuration_id, child_instance_id=carrier_id,
                                                     child_port_id="mount"),
                                        Relationship(id="tool-mount", parent_instance_id=carrier_id,
                                                     parent_port_id="tool", child_instance_id=tool_id,
                                                     child_port_id="mount")))
