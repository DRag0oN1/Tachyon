from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from ..errors import TachyonError
from .catalog import Catalog, write_json, PREPARE_OPERATIONS
from .glb import inspect_glb, normalize_mm_to_m
from .rights import sha256_file


def prepare_component(catalog: Catalog, component):
    return _prepare_component(catalog, component, {})


def prepare_components(catalog: Catalog, components, *, reuse_existing=False, on_error=None):
    """Prepare a batch, importing each checked source hash at most once.

    The cache is private to this call; callers cannot inject an assembly in
    place of the registered bytes. Every component still passes source/rights
    checks before reuse and a source hash check before writing its receipt.
    """
    imported_sources = {}
    prepared=[]
    for component in components:
        try:
            if reuse_existing:
                catalog.source(component, PREPARE_OPERATIONS)
                try:
                    cached=dict(catalog.prepared(component))
                    cached.pop("qualifiedOperations",None)  # display context is not a conversion receipt
                    cached["declaredUse"]="user_provided_local"
                    prepared.append(cached)
                    continue
                except TachyonError:
                    pass  # Reconvert stale/missing receipts, subject to rights.
            prepared.append(_prepare_component(catalog, component, imported_sources))
        except TachyonError as error:
            if on_error is None:
                raise
            on_error(component,error)
    return prepared


def _prepare_component(catalog: Catalog, component, imported_sources):
    source = catalog.source(component, PREPARE_OPERATIONS)  # fail before importing/converting any geometry
    import cadquery as cq

    try:
        from .native import import_source, select_source_definition, native_bounds_mm
        if component.source_sha256 not in imported_sources:
            imported = import_source(source)
            if sha256_file(source) != component.source_sha256:
                raise TachyonError("SOURCE_HASH_MISMATCH", "Source changed during native import")
            imported_sources[component.source_sha256] = imported
        assembly = imported_sources[component.source_sha256]
        if component.source_selection is not None:
            assembly = select_source_definition(assembly, component.source_selection)
        shape = assembly.toCompound()
        solids = shape.Solids()
        from .validation import geometry_validation
        whole_file_reference = component.reference_only and component.source_selection is None
        validation = geometry_validation(assembly, shape, detailed=not whole_file_reference)
        if not solids or (not validation["nativeBrepValid"] and not whole_file_reference):
            raise TachyonError("INVALID_GEOMETRY", "Source must contain valid solid component geometry")
        expected = component.expected_bounds_mm
        if whole_file_reference:
            # Explicit references retain the previously reviewed, source-hash-
            # bound measurements. Validate actual converted world vertices below.
            # Re-solving whole-assembly BSpline extrema adds minutes without
            # providing a new independent dimension source.
            low, high = np.array(expected.min), np.array(expected.max)
        else:
            low,high=map(np.array,native_bounds_mm(shape))
        if max(np.max(np.abs(low - expected.min)), np.max(np.abs(high - expected.max))) > component.measurement_tolerance_mm:
            raise TachyonError("SOURCE_DIMENSION_MISMATCH", "Native geometry does not match the measured source bounds")
        # The tested exporter changes Z-up to Y-up but retains millimetre values.
        # Normalize its generated display asset once, preserving native placements.
        expected_min = np.array([low[0], low[2], -high[1]]) / 1000
        expected_max = np.array([high[0], high[2], -low[1]]) / 1000
        conservative_bounds=None
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
            if delta > .0001 and component.source_selection is not None:
                # Trimmed BSpline surface envelopes can overestimate actual
                # BRep support. Check six independent source-geometry extrema;
                # the strict mesh tolerance stays unchanged.
                from .metrology import support_bounds_mm
                refined_low,refined_high=map(np.array,support_bounds_mm(shape))
                if np.any(refined_low<low-.002) or np.any(refined_high>high+.002):
                    raise TachyonError("SOURCE_BOUNDS_UNAVAILABLE", "Refined source envelope escaped the conservative BRep bounds")
                conservative_bounds={"min":low.tolist(),"max":high.tolist()}
                low,high=refined_low,refined_high
                expected_min=np.array([low[0],low[2],-high[1]])/1000
                expected_max=np.array([high[0],high[2],-low[1]])/1000
                delta=max(np.max(np.abs(np.array(info["boundsM"]["min"])-expected_min)),np.max(np.abs(np.array(info["boundsM"]["max"])-expected_max)))
            if delta > 0.0001:
                raise TachyonError("MESH_FRAME_MISMATCH", f"Converted mesh {component.id} differs from the source bounds by {delta:.9f} m")
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
            "conversion": {"tool": "CadQuery", "version": cq.__version__, "linearDeflectionMm": None,
                           "meshingMode": "relative", "relativeDeflection": .05,
                           "angularDeflectionRad": 0.1, "frame": "native STEP to mm; exporter Z-up to Y-up; explicit mm-to-m root conversion once",
                           "sourceBoundsBasis": "reviewed_registration_measurement" if whole_file_reference else "native_measurement",
                           "maxBoundsErrorM": float(delta), "displayMeshOnly": True},
            "attribution": catalog.policy.records[component.source_sha256].attribution,
            "completeRobot": False, "referenceOnly": component.reference_only,
            "geometryValidation": {**validation, "qualifiedForRobotGeneration": validation["nativeBrepValid"] and not component.reference_only}}
        if component.source_selection is not None:
            record["sourceSelection"] = component.source_selection.json_data()
        if conservative_bounds is not None:
            record["conversion"].update(sourceBoundsBasis="native_extremum_support",
                conservativeSourceBoundsMm=conservative_bounds,sourceExtremumErrorMm=.001)
        write_json(catalog.receipt_path(component), record)
        return record
    except TachyonError:
        raise
    except Exception:
        raise TachyonError("CAD_PREPARATION_FAILED", "STEP import or local tessellation failed; inspect the source and its component selection") from None
