"""Original Tachyon calibration geometry; never a manufacturer component.

Shared by pytest and the opt-in verification seeder. All paths and evidence refer
only to the files generated here. No source libraries or research CAD are read.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tachyon.cad.catalog import Catalog
from tachyon.config import Settings


FIXTURE_ID = "tachyon_calibration_assembly"
FIXTURE_NAME = "Tachyon calibration assembly [test_fixture, non-VEX]"
LOCAL_OPERATIONS = (
    "acquisition_storage", "conversion", "assembly_placement", "loopback_display",
)
# Independently calculated from the two boxes and the nested 90-degree transform.
SOURCE_BOUNDS_MM = {"min": [-39.0, 3.0, -4.0], "max": [23.0, 29.0, 20.0]}
BROWSER_BOUNDS_M = {"min": [-0.039, -0.004, -0.029], "max": [0.023, 0.020, -0.003]}
MEMBER_NAMES = {"calibration_base", "calibration_offset_group", "calibration_offset_block"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text())


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


@dataclass(frozen=True)
class FixtureWorkspace:
    settings: Settings

    @property
    def data_dir(self):
        return self.settings.data_dir

    @property
    def manifest_path(self):
        return self.data_dir / "catalog/manifest.json"

    @property
    def rights_path(self):
        return self.data_dir / "catalog/rights.json"

    @property
    def source_path(self):
        return self.data_dir / "sources/calibration.step"

    @property
    def evidence_path(self):
        return self.data_dir / "evidence/calibration-authorship.txt"

    def catalog(self):
        return Catalog(self.settings)

    @property
    def component(self):
        return self.catalog().manifest.components[0]

    def update_component(self, **changes):
        document = load_json(self.manifest_path)
        document["components"][0].update(changes)
        save_json(self.manifest_path, document)

    def update_permission(self, operation="conversion", **changes):
        document = load_json(self.rights_path)
        document["records"][0]["operations"][operation].update(changes)
        save_json(self.rights_path, document)


def create_calibration_workspace(root: Path, data_dir: Path) -> FixtureWorkspace:
    """Generate two original solids with measured bounds and scoped authorship.

    Refusing a nonempty destination prevents the seeder from replacing any user
    catalog, evidence, source geometry, or an earlier reviewed fixture workspace.
    """
    settings = Settings(root=root, data_dir=data_dir)
    if data_dir.exists() and any(data_dir.iterdir()):
        raise FileExistsError("Calibration destination must be new or empty")
    import cadquery as cq

    workspace = FixtureWorkspace(settings)
    workspace.source_path.parent.mkdir(parents=True, exist_ok=True)
    source = cq.Assembly(name="tachyon_calibration_source")
    source.add(cq.Workplane("XY").box(40, 20, 10, centered=False),
               name="calibration_base", loc=cq.Location(cq.Vector(-17, 9, -4)),
               color=cq.Color(0.18, 0.56, 0.82))
    group = cq.Assembly(name="calibration_offset_group")
    group.add(cq.Workplane("XY").box(12, 8, 6, centered=False),
              name="calibration_offset_block", loc=cq.Location(cq.Vector(10, 35, 3)),
              color=cq.Color(0.95, 0.52, 0.12))
    source.add(group, loc=cq.Location(cq.Vector(4, -7, 11), cq.Vector(0, 0, 1), 90))
    source.export(str(workspace.source_path), exportType="STEP")

    # Measure the written native document, not the pre-export workplane.
    native = cq.Assembly.load(str(workspace.source_path)).toCompound()
    bounds = native.BoundingBox()
    measured = {"min": [bounds.xmin, bounds.ymin, bounds.zmin],
                "max": [bounds.xmax, bounds.ymax, bounds.zmax]}
    for side in ("min", "max"):
        if any(abs(a - b) > 1e-5 for a, b in zip(measured[side], SOURCE_BOUNDS_MM[side])):
            raise RuntimeError("Calibration STEP differs from its authored dimensions")
    if len(native.Solids()) != 2 or not native.isValid():
        raise RuntimeError("Calibration STEP must contain two valid original solids")
    source_hash = digest(workspace.source_path)
    evidence = (
        "Tachyon-authored calibration fixture, version 1.\n"
        "Purpose: converter and renderer tests only. test_fixture; non-VEX.\n"
        "This original geometry was authored by Tachyon's fixture generator.\n"
        "No manufacturer, community, VEX, or user CAD was used or licensed here.\n"
        "This is not an authentic component or a complete robot.\n"
        f"Source: sources/calibration.step; SHA-256: {source_hash}\n"
        "Base: 40x20x10 mm at (-17,9,-4).\n"
        "Offset block: 12x8x6 mm at (10,35,3), nested under a group at\n"
        "(4,-7,11) with a 90-degree rotation about native Z.\n"
        "Rightsholder: Tachyon calibration fixture authors.\n"
        "Self-authored permission applies only to this source hash for:\n"
        "acquisition_storage, conversion, assembly_placement, loopback_display.\n"
        "LAN, public depiction, redistribution, and public hosting are not granted.\n"
        f"Reviewed by: Tachyon fixture generator (authorship only); {date.today().isoformat()}.\n"
    )
    workspace.evidence_path.parent.mkdir(parents=True, exist_ok=True)
    workspace.evidence_path.write_text(evidence)
    permission = {
        "status": "qualified", "basis": "self_authored",
        "rightsholder": "Tachyon calibration fixture authors",
        "evidencePath": "evidence/calibration-authorship.txt",
        "evidenceSha256": digest(workspace.evidence_path),
        "reviewedBy": "Tachyon fixture generator (authorship only)",
        "reviewedOn": date.today().isoformat(),
    }
    save_json(workspace.rights_path, {"schemaVersion": 1, "records": [{
        "sourceSha256": source_hash,
        "attribution": "Original Tachyon calibration test_fixture; non-VEX; converter/render tests only.",
        "operations": {operation: dict(permission) for operation in LOCAL_OPERATIONS},
    }]})
    save_json(workspace.manifest_path, {"schemaVersion": 1, "components": [{
        "id": FIXTURE_ID, "name": FIXTURE_NAME, "sku": None,
        "sourceUrl": "tachyon-fixture:calibration-assembly-v1",
        "sourcePath": "sources/calibration.step", "sourceSha256": source_hash,
        "originKind": "tachyon_authored", "geometryClass": "test_fixture",
        "expectedBoundsMm": measured, "measurementToleranceMm": 0.01,
        "ports": [{"id": "calibration_reference", "kind": "mount",
                   "positionM": [0.003, 0.006, -0.019], "axis": [0, 1, 0],
                   "evidence": "Authored base top centre (3,19,6) mm mapped to browser metres/Y-up; test reference only"}],
    }]})
    return workspace


def author_source_variant(workspace: FixtureWorkspace, variant: str):
    """Author alternate native documents solely from original calibration shapes.

    Tests use this for importer formats and product-root handling. Every variant
    gets its own source hash and matching authorship evidence. This function has
    no path/input argument for outside or manufacturer CAD.
    """
    import cadquery as cq

    if workspace.component.id != FIXTURE_ID or workspace.component.geometry_class != "test_fixture":
        raise ValueError("Variants require the original calibration test_fixture workspace")
    if variant == "multiple_free_roots":
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer

        base = cq.Workplane("XY").box(40, 20, 10, centered=False).val().translate((-17, 9, -4))
        offset = (cq.Workplane("XY").box(12, 8, 6, centered=False).val()
                  .translate((10, 35, 3)).rotate((0, 0, 0), (0, 0, 1), 90).translate((4, -7, 11)))
        writer = STEPControl_Writer()
        for original in (base, offset):
            assert writer.Transfer(original.wrapped, STEPControl_AsIs) == IFSelect_RetDone
        assert writer.Write(str(workspace.source_path)) == IFSelect_RetDone
        expected = SOURCE_BOUNDS_MM
    elif variant == "inch_unit_part":
        # These numeric coordinates are inches, and the native STEP declares INCH.
        original = cq.Workplane("XY").box(2, 1, 0.25, centered=False).translate((-0.5, 0.2, 0.75))
        cq.exporters.export(original, str(workspace.source_path), exportType="STEP",
                            unit="INCH", outputUnit="INCH")
        expected = {"min": [-12.7, 5.08, 19.05], "max": [38.1, 30.48, 25.4]}
    elif variant == "rotated_prism":
        angle = math.radians(37)
        original = cq.Workplane("XY").polyline([(0, 0), (30, 0), (0, 10)]).close().extrude(5)
        assembly = cq.Assembly(name="tachyon_rotated_prism_source")
        assembly.add(original, name="calibration_triangular_prism",
                     loc=cq.Location(cq.Vector(-7, 3, -2), cq.Vector(0, 0, 1), 37))
        assembly.export(str(workspace.source_path), exportType="STEP")
        expected = {"min": [-7 - 10 * math.sin(angle), 3, -2],
                    "max": [-7 + 30 * math.cos(angle), 3 + 30 * math.sin(angle), 3]}
    elif variant in ("standalone_part", "wrapper_name_collision"):
        original = cq.Workplane("XY").box(7, 11, 13, centered=False).translate((2, -9, 4))
        if variant == "standalone_part":
            cq.exporters.export(original, str(workspace.source_path), exportType="STEP")
        else:
            assembly = cq.Assembly(name=FIXTURE_ID)
            assembly.add(original, name="calibration_collision_solid")
            assembly.export(str(workspace.source_path), exportType="STEP")
        expected = {"min": [2, -9, 4], "max": [9, 2, 17]}
    else:
        raise ValueError("Unknown original calibration variant")
    source_hash = digest(workspace.source_path)
    workspace.evidence_path.write_text(
        f"Original Tachyon-authored test_fixture variant: {variant}; non-VEX.\n"
        f"Source: sources/calibration.step; SHA-256: {source_hash}\n"
        "Authored solely from new calibration geometry, with no external CAD.\n"
        "Rightsholder: Tachyon calibration fixture authors.\n"
        "Self-authored acquisition_storage, conversion, assembly_placement and loopback_display only.\n"
        "Not an authentic component, complete robot, or qualification of any other source.\n"
        f"Reviewed by Tachyon fixture generator (authorship only), {date.today().isoformat()}.\n")
    rights = load_json(workspace.rights_path)
    rights["records"][0]["sourceSha256"] = source_hash
    for permission in rights["records"][0]["operations"].values():
        permission["evidenceSha256"] = digest(workspace.evidence_path)
    save_json(workspace.rights_path, rights)
    workspace.update_component(sourceSha256=source_hash, expectedBoundsMm=expected)
    return expected
