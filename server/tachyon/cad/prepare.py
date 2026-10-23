from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from ..errors import TachyonError
from .catalog import Catalog, write_json, PREPARE_OPERATIONS
from .glb import inspect_glb, normalize_mm_to_m
from .rights import sha256_file


def prepare_component(catalog: Catalog, component):
    source = catalog.source(component, PREPARE_OPERATIONS)  # fail before importing/converting any geometry
    import cadquery as cq

    try:
        from .native import import_source
        assembly = import_source(source)
        shape = assembly.toCompound()
        solids = shape.Solids()
        if not solids or not shape.isValid():
            raise TachyonError("INVALID_GEOMETRY", "Source must contain valid solid component geometry")
        bb = shape.BoundingBox()
        low = np.array([bb.xmin, bb.ymin, bb.zmin])
        high = np.array([bb.xmax, bb.ymax, bb.zmax])
        expected = component.expected_bounds_mm
        if max(np.max(np.abs(low - expected.min)), np.max(np.abs(high - expected.max))) > component.measurement_tolerance_mm:
            raise TachyonError("SOURCE_DIMENSION_MISMATCH", "Native geometry does not match the measured source bounds")
        # The tested exporter changes Z-up to Y-up but retains millimetre values.
        # Normalize its generated display asset once, preserving native placements.
        expected_min = np.array([low[0], low[2], -high[1]]) / 1000
        expected_max = np.array([high[0], high[2], -low[1]]) / 1000
        cache = catalog.settings.data_dir / "meshes"
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as temp:
            output = Path(temp) / "component.glb"
            wrapper = component.id + "__display"
            while wrapper in assembly.objects:
                wrapper += "_wrapper"
            display = cq.Assembly(name=wrapper)
            display.add(assembly)
            display.export(str(output), exportType="GLTF", tolerance=0.05, angularTolerance=0.1)
            normalize_mm_to_m(output)
            info = inspect_glb(output)
            # Check actual GLB scene, including node matrices; prevent double scaling/rotation.
            delta = max(np.max(np.abs(np.array(info["boundsM"]["min"]) - expected_min)),
                        np.max(np.abs(np.array(info["boundsM"]["max"]) - expected_max)))
            if delta > 0.0001:
                raise TachyonError("MESH_FRAME_MISMATCH", "Converted mesh units/frame differ from the measured source")
            mesh_hash = sha256_file(output)
            output.replace(cache / (mesh_hash + ".glb"))
        if sha256_file(source) != component.source_sha256:
            raise TachyonError("SOURCE_HASH_MISMATCH", "Source changed during preparation")
        record = {
            "id": component.id, "name": component.name, "sku": component.sku,
            "originKind": component.origin_kind, "geometryClass": component.geometry_class,
            "sourceUrl": component.source_url, "sourceSha256": component.source_sha256,
            "meshSha256": mesh_hash, "meshUrl": f"/api/assets/{mesh_hash}.glb",
            "catalogFingerprint": catalog.fingerprint(component), "boundsM": info["boundsM"],
            "solidCount": len(solids), "nativeHierarchy": info["hierarchy"],
            "ports": [p.json_data() for p in component.ports], "rightsStatus": "qualified_for_declared_use",
            "declaredUse": "user_provided_local", "sourceBoundsMm": {"min": low.tolist(), "max": high.tolist()},
            "conversion": {"tool": "CadQuery", "version": cq.__version__, "linearDeflectionMm": 0.05,
                           "angularDeflectionRad": 0.1, "frame": "native STEP to mm; exporter Z-up to Y-up; explicit mm-to-m root conversion once",
                           "maxBoundsErrorM": float(delta), "displayMeshOnly": True},
            "attribution": catalog.policy.records[component.source_sha256].attribution,
            "completeRobot": False}
        write_json(catalog.receipt_path(component), record)
        return record
    except TachyonError:
        raise
    except Exception:
        raise TachyonError("CAD_PREPARATION_FAILED", "STEP import or local tessellation failed; inspect the source and its component selection") from None
