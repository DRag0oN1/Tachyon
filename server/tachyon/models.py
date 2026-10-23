from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True,
                             alias_generator=to_camel, allow_inf_nan=False)

    def json_data(self):
        return self.model_dump(mode="json", by_alias=True)


class Operation(StrEnum):
    acquisition_storage = "acquisition_storage"
    conversion = "conversion"
    assembly_placement = "assembly_placement"
    part_modification = "part_modification"
    loopback_display = "loopback_display"
    lan_display = "lan_display"
    public_depiction = "public_depiction"
    original_redistribution = "original_redistribution"
    mesh_redistribution = "mesh_redistribution"
    public_hosting = "public_hosting"


Sha = str
Vector3 = tuple[float, float, float]


class Bounds(Model):
    min: Vector3
    max: Vector3

    @model_validator(mode="after")
    def ordered(self):
        if any(a > b for a, b in zip(self.min, self.max)):
            raise ValueError("Bounds must be ordered")
        return self


class Permission(Model):
    status: Literal["qualified", "unverified", "disallowed"] = "unverified"
    rightsholder: str = ""
    basis: Literal["license", "written_permission", "self_authored"] | None = None
    evidence_path: str = ""
    evidence_sha256: str = ""
    reviewed_by: str = ""
    reviewed_on: date | None = None
    expires_on: date | None = None


class RightsRecord(Model):
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    attribution: str = ""
    operations: dict[Operation, Permission] = Field(default_factory=dict)


class RightsManifest(Model):
    schema_version: Literal[1] = 1
    records: list[RightsRecord] = Field(default_factory=list)


class InterfacePort(Model):
    id: str
    kind: Literal["mount", "shaft", "bearing", "revolute", "prismatic"]
    position_m: Vector3
    axis: Vector3
    evidence: str

    @model_validator(mode="after")
    def unit_axis(self):
        if abs(sum(x*x for x in self.axis) - 1) > 1e-5:
            raise ValueError("Port axis must be a unit vector")
        if not self.evidence.strip():
            raise ValueError("Ports require measurement evidence")
        return self


class ComponentInput(Model):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    name: str = Field(min_length=1)
    sku: str | None = None
    source_url: str
    source_path: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    origin_kind: Literal["manufacturer_cad", "community_component_model", "tachyon_authored"]
    geometry_class: Literal["verified_imported_component", "conceptual", "placeholder", "test_fixture"]
    expected_bounds_mm: Bounds
    measurement_tolerance_mm: float = Field(default=0.05, gt=0, le=1)
    ports: list[InterfacePort] = Field(default_factory=list)


class CatalogManifest(Model):
    schema_version: Literal[1] = 1
    components: list[ComponentInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique(self):
        if len({c.id for c in self.components}) != len(self.components):
            raise ValueError("Duplicate component identity")
        return self


class NativeNode(Model):
    id: str
    name: str
    parent_id: str | None
    matrix: list[float] = Field(min_length=16, max_length=16)
    has_mesh: bool


class ConversionReceipt(Model):
    tool: Literal["CadQuery"]
    version: str
    linear_deflection_mm: float
    angular_deflection_rad: float
    frame: str
    max_bounds_error_m: float = Field(ge=0)
    display_mesh_only: Literal[True]


class PreparedComponent(Model):
    id: str
    name: str
    sku: str | None
    origin_kind: Literal["manufacturer_cad", "community_component_model", "tachyon_authored"]
    geometry_class: Literal["verified_imported_component", "conceptual", "placeholder", "test_fixture"]
    source_url: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    mesh_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    mesh_url: str
    catalog_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    bounds_m: Bounds
    source_bounds_mm: Bounds
    solid_count: int = Field(gt=0)
    native_hierarchy: list[NativeNode]
    ports: list[InterfacePort]
    rights_status: Literal["qualified_for_declared_use"]
    declared_use: str
    conversion: ConversionReceipt
    attribution: str
    complete_robot: Literal[False]


class Preferences(Model):
    theme: Literal["snap", "shift"] = "snap"
    mode: Literal["simple", "advanced"] = "simple"


class PreferencesPatch(Model):
    theme: Literal["snap", "shift"] | None = None
    mode: Literal["simple", "advanced"] | None = None


class WorkspacePatch(Model):
    preferences: PreferencesPatch | None = None
    active_component_id: str | None = None
