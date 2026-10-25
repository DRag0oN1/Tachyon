#!/usr/bin/env python3
"""Bounded connectivity/interference audit of original development STEP only.

Run with .venv/bin/python -B tools/verification/check_generated_assembly.py.
Reads the private profile without starting the app or changing its database,
catalog, rights, recipes or geometry. Writes numerical JSON only. A connected
graph is not physical mounting proof; neither endpoint certifies a motion path.
Exit 1 means collisions were found; exit 2 means qualification/audit incomplete.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server"))

# Explicit component scope; no matching-pair or declared-mate ignore list.
MAJOR = frozenset("""
dev_channel dev_short_channel dev_angle dev_motor dev_omni dev_traction
dev_gripper dev_brain dev_battery dev_battery_clip dev_cup_bridge dev_cup_rail
dev_pin_handoff dev_cup_alignment
""".split())
ENGAGEMENT_OR_SMALL = frozenset("""
dev_bearing dev_shaft_long dev_shaft_medium dev_shaft_short dev_shaft_insert
dev_gear84 dev_gear12 dev_bolt dev_bolt_short dev_bolt_mid dev_bolt_long
dev_bolt25 dev_nut dev_washer dev_spacer dev_brace dev_standoff
dev_standoff_short dev_collar dev_cup_screw dev_cup_collar dev_cup_input_shaft
""".split())
DEFERRED_CUP_CONTACT = frozenset(("dev_cup_jaw_left", "dev_cup_jaw_right", "dev_operation_cup"))
REQUIRED_OPERATIONS = ("acquisition_storage", "conversion", "assembly_placement", "loopback_display")
INPUT_SHAFT = "dev_cup_input_shaft"


def audit_input_shaft(snapshot, worlds, shapes, major_nodes, label):
    """Separate exception to the ordinary shaft exclusion; never mask body hits.

    Only directly declared Cup-transmission motor/bearing/gear/axial hardware
    engagements are exempted. Other motors and every structural major body stay
    in scope. Nonmajor fasteners/engagement hardware remain outside this check.
    """
    from tachyon.cad.native import native_bounds_mm
    from tachyon.robots.source_pack import DISPLAY

    shafts = [n for n in snapshot.instances if n.component_id == INPUT_SHAFT]
    result = {"status": "not_present", "possiblePairCount": 0, "aabbOverlapPairCount": 0,
              "exactIntersectionAttemptCount": 0, "exactIntersectionCompletedCount": 0,
              "overThresholdCollisionCount": 0, "collisions": [], "exactIntersections": [],
              "errors": [], "declaredEngagementExclusions": [],
              "scope": "Input shaft versus nonmating major bodies only; no dynamics or engagement-fit qualification"}
    if not shafts:
        return result
    if len(shafts) != 1:
        raise ValueError("Separate Cup input-shaft audit requires exactly one shaft instance")
    shaft = shafts[0]
    nodes = {n.id: n for n in snapshot.instances}
    excluded = {}
    engagement_components = {"dev_motor", "dev_bearing", "dev_gear12", "dev_gear84",
                             "dev_shaft_insert", "dev_collar", "dev_cup_collar", "dev_cup_screw",
                             "dev_shaft_long", "dev_shaft_medium", "dev_shaft_short"}
    for rel in snapshot.relationships:
        if rel.parent_instance_id == shaft.id:
            other = nodes[rel.child_instance_id]
        elif rel.child_instance_id == shaft.id:
            other = nodes[rel.parent_instance_id]
        else:
            continue
        if (other.subsystem_id == "cup_cradle" and other.component_id in engagement_components
                and (other.component_id != "dev_motor" or other.id == "cup-grip-motor")):
            entry = excluded.setdefault(other.id, {**identity(other), "relationshipIds": [],
                "reason": "Directly declared intended Cup-transmission engagement; physical fit not audited"})
            entry["relationshipIds"].append(rel.id)
    result["declaredEngagementExclusions"] = list(excluded.values())
    targets = [n for n in major_nodes if n.id != shaft.id and n.id not in excluded]
    result["possiblePairCount"] = len(targets)
    result["shaft"] = identity(shaft)
    located, error = world_shape(shapes[INPUT_SHAFT], worlds[shaft.id], DISPLAY)
    shaft_bounds = native_bounds_mm(located)
    result["shaftBoundsWorldMm"] = shaft_bounds
    for node in targets:
        body, e = world_shape(shapes[node.component_id], worlds[node.id], DISPLAY)
        error = max(error, e)
        bounds = native_bounds_mm(body)
        if not all(min(shaft_bounds[1][i], bounds[1][i])-max(shaft_bounds[0][i], bounds[0][i]) > 0 for i in range(3)):
            continue
        result["aabbOverlapPairCount"] += 1
        result["exactIntersectionAttemptCount"] += 1
        pair = {"shaft": identity(shaft), "body": identity(node), "bodyBoundsWorldMm": bounds}
        try:
            volume = common_volume(located, body)
            pair.update(status="computed", intersectionVolumeMm3=volume, exceedsReportThreshold=volume > 1.)
            result["exactIntersectionCompletedCount"] += 1
            if volume > 1.:
                result["collisions"].append(pair)
                print(f"{label}: INPUT SHAFT COLLISION / {node.id}: {volume:.6f} mm^3", flush=True)
        except Exception as exc:
            pair.update(status="error", errorType=type(exc).__name__)
            result["errors"].append(pair)
        result["exactIntersections"].append(pair)
    result["maxWorldCenterCheckErrorMm"] = error
    result["overThresholdCollisionCount"] = len(result["collisions"])
    result["status"] = ("incomplete_exact_intersections" if result["errors"] else "collisions_found"
                        if result["collisions"] else "no_over_threshold_overlap_in_audited_subset")
    print(f"{label}: separate input shaft: {result['aabbOverlapPairCount']} AABB candidates, "
          f"{result['overThresholdCollisionCount']} overlaps >1 mm^3", flush=True)
    return result


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def private_path(path):
    path = Path(path).expanduser().resolve()
    if not path.is_relative_to(ROOT / ".local"):
        raise ValueError("Inputs and JSON output must remain inside this project's private .local directory")
    return path


def connectivity(snapshot):
    neighbors = {node.id: set() for node in snapshot.instances}
    for rel in snapshot.relationships:
        neighbors[rel.parent_instance_id].add(rel.child_instance_id)
        neighbors[rel.child_instance_id].add(rel.parent_instance_id)
    reached, pending = set(), [snapshot.root_instance_id]
    while pending:
        key = pending.pop()
        if key not in reached:
            reached.add(key)
            pending.extend(neighbors[key] - reached)
    return {"rootInstanceId": snapshot.root_instance_id, "instanceCount": len(neighbors),
            "relationshipCount": len(snapshot.relationships), "reachableInstanceCount": len(reached),
            "unreachableInstanceIds": sorted(set(neighbors) - reached),
            "isolatedInstanceIds": sorted(k for k, v in neighbors.items() if not v),
            "basis": "Explicit attachment graph and production port-closure validation; not physical support/fit"}


def identity(node):
    return {"instanceId": node.id, "componentId": node.component_id, "subsystemId": node.subsystem_id}


def world_shape(shape, world, display):
    import cadquery as cq
    from OCP.gp import gp_Trsf

    # Native BRep coordinates are mm. world*DISPLAY has a rigid rotation and
    # metre translation: scale ONLY the translation by 1000, never the rotation.
    pose = world.compose(display)
    m = pose.matrix
    trsf = gp_Trsf()
    trsf.SetValues(*(m[4*c+r] * (1000 if c == 3 else 1) for r in range(3) for c in range(4)))
    located = shape.moved(cq.Location(trsf))
    center = shape.Center().toTuple()
    expected = tuple(v * 1000 for v in pose.point(tuple(v / 1000 for v in center)))
    error = math.dist(expected, located.Center().toTuple())
    if error > 1e-5:
        raise ValueError("Native-to-world millimetre center check failed")
    return located, error


def common_volume(left, right):
    import cadquery as cq
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

    operation = BRepAlgoAPI_Common(left.wrapped, right.wrapped)
    if not operation.IsDone() or operation.Shape().IsNull():
        raise ValueError("BRep common operation did not complete")
    result = cq.Shape.cast(operation.Shape())
    if not result.isValid():
        raise ValueError("BRep common result is invalid")
    volume = abs(result.Volume())
    if not math.isfinite(volume):
        raise ValueError("BRep common volume is not finite")
    return volume


def qualified_profile(data_dir):
    from tachyon import realization as R
    from tachyon.cad.catalog import Catalog
    from tachyon.config import Settings
    from tachyon.models import Operation

    # No external CAD/rights root: even registered paths/symlinks must stay in
    # this explicitly selected profile. Native import occurs only after checks.
    settings = Settings(ROOT, data_dir)
    catalog = Catalog(settings)
    if not catalog.manifest.components:
        raise ValueError("The development profile has no components")
    for component in catalog.manifest.components:
        if (component.origin_kind != "tachyon_authored" or component.geometry_class != "test_fixture"
                or component.reference_only or component.source_selection is not None):
            raise ValueError("Stop: this audit accepts only whole-source original non-VEX development fixtures")
        record = catalog.policy.records.get(component.source_sha256)
        if record is None or any(record.operations.get(Operation(op)) is None or
                                 record.operations[Operation(op)].basis != "self_authored"
                                 for op in REQUIRED_OPERATIONS):
            raise ValueError("Stop: original-authorship operation records are required")
        catalog.source(component, [Operation(op) for op in REQUIRED_OPERATIONS])
    recipe = R.load_recipe(settings, "A")
    if recipe is None or set(recipe.configurations) != {"lower", "raised"}:
        raise ValueError("An A recipe with lower and raised configurations is required")
    service, receipts = R.qualified_catalog(settings, recipe)
    return settings, catalog, recipe, service, receipts


def original_shape(catalog, component):
    from tachyon.cad.native import import_source, native_bounds_mm
    from tachyon.models import Operation

    path = catalog.source(component, [Operation(op) for op in REQUIRED_OPERATIONS])
    shape = import_source(path).toCompound()
    if not shape.isValid() or not shape.Solids() or shape.Volume() <= 0:
        raise ValueError("Stop: invalid or empty original BRep: " + component.id)
    bounds = native_bounds_mm(shape)
    expected = component.expected_bounds_mm
    if max(abs(a-b) for a, b in zip(bounds[0]+bounds[1], (*expected.min, *expected.max))) > component.measurement_tolerance_mm:
        raise ValueError("Stop: native bounds differ from the registered measurements: " + component.id)
    if sha(path) != component.source_sha256:
        raise ValueError("Stop: source changed during native import: " + component.id)
    return shape


def audit(data_dir, report):
    from tachyon import assemblies as A, realization as R
    from tachyon.cad.native import native_bounds_mm
    from tachyon.models import Operation
    from tachyon.robots.source_pack import DISPLAY

    settings, catalog, recipe, service, receipts = qualified_profile(data_dir)
    used = {node.component_id for node in recipe.template.instances}
    unknown = used - MAJOR - ENGAGEMENT_OR_SMALL - DEFERRED_CUP_CONTACT
    if unknown:
        raise ValueError("Explicit audit classification needed for: " + ", ".join(sorted(unknown)))
    report.update(recipeId=recipe.id, recipeHash=A.content_hash(recipe.json_data()),
                  inputs={"manifestSha256": sha(catalog.manifest_path), "rightsSha256": sha(catalog.rights_path),
                          "recipeFileSha256": sha(data_dir / "catalog/assembly-recipes.json")},
                  components=[{"componentId": r["id"], "sourceSha256": r["sourceSha256"],
                               "meshSha256": r["meshSha256"], "catalogFingerprint": r["catalogFingerprint"]}
                              for r in receipts])
    revisions = {key: R.build_pose(service, recipe, "development-interference-audit", key)
                 for key in ("lower", "raised")}
    for key, revision in revisions.items():
        result = connectivity(revision.assembly)
        result["productionGraphValid"] = service.validate(revision).graph_valid
        report["configurations"][key] = {"revisionId": revision.id,
                                          "engineeringHash": revision.engineering_hash,
                                          "connectivity": result}
        if result["unreachableInstanceIds"]:
            raise ValueError("Stop: declared assembly has disconnected instances")
    print(f"Qualified own profile: {len(receipts)} definitions; "
          f"{len(recipe.template.instances)} connected instances in both endpoint graphs", flush=True)

    sources = {c.id: c for c in catalog.manifest.components}
    shapes = {}
    for key in sorted(used & (MAJOR | {INPUT_SHAFT})):
        shapes[key] = original_shape(catalog, sources[key])
    print(f"Imported {len(shapes)} own major-part definitions; no geometry exported", flush=True)

    for configuration, revision in revisions.items():
        snapshot = revision.assembly
        nodes = {n.id: n for n in snapshot.instances}
        selected = [n for n in snapshot.instances if n.component_id in MAJOR]
        excluded = [{**identity(n), "reason": "Cup body/jaw contact deferred until v3 profile" if n.component_id in DEFERRED_CUP_CONTACT
                     else "Fastener/small support or shaft/gear/screw engagement outside this bounded audit"}
                    for n in snapshot.instances if n.component_id not in MAJOR]
        worlds = A.world_transforms(snapshot)
        located, bounds, max_error = {}, {}, 0.
        for node in selected:
            located[node.id], error = world_shape(shapes[node.component_id], worlds[node.id], DISPLAY)
            max_error = max(max_error, error)
            bounds[node.id] = native_bounds_mm(located[node.id])
        result = report["configurations"][configuration]
        result.update(majorInstanceCount=len(selected), possibleMajorPairCount=len(selected)*(len(selected)-1)//2,
                      majorInstances=[{**identity(n), "boundsWorldMm": bounds[n.id]} for n in selected],
                      excludedInstances=excluded, excludedCounts=dict(Counter(n["componentId"] for n in excluded)),
                      maxWorldCenterCheckErrorMm=max_error, aabbOverlapPairCount=0,
                      exactIntersectionAttemptCount=0, exactIntersectionCompletedCount=0,
                      positiveIntersectionCount=0, overThresholdCollisionCount=0,
                      exactIntersections=[], collisions=[], errors=[])
        broad = []
        for left, right in combinations(selected, 2):
            lo, hi = bounds[left.id], bounds[right.id]
            extents = [min(lo[1][i], hi[1][i])-max(lo[0][i], hi[0][i]) for i in range(3)]
            if all(value > 0 for value in extents):
                broad.append((left, right, math.prod(extents)))
        result["aabbOverlapPairCount"] = len(broad)
        print(f"{configuration}: {len(selected)} major instances, {len(broad)} AABB candidates "
              f"of {result['possibleMajorPairCount']} possible pairs", flush=True)
        for index, (left, right, aabb_volume) in enumerate(broad, 1):
            pair = {"a": identity(left), "b": identity(right), "aabbOverlapVolumeMm3": aabb_volume}
            result["exactIntersectionAttemptCount"] += 1
            try:
                volume = common_volume(located[left.id], located[right.id])
                pair.update(status="computed", intersectionVolumeMm3=volume,
                            exceedsReportThreshold=volume > report["thresholdMm3"])
                result["exactIntersectionCompletedCount"] += 1
                result["positiveIntersectionCount"] += int(volume > 0)
                if volume > report["thresholdMm3"]:
                    pair["declaredRelationshipIds"] = [r.id for r in snapshot.relationships
                        if {r.parent_instance_id, r.child_instance_id} == {left.id, right.id}]
                    result["collisions"].append(pair)
                    print(f"{configuration}: COLLISION {left.id} / {right.id}: {volume:.6f} mm^3", flush=True)
            except Exception as error:
                pair.update(status="error", errorType=type(error).__name__)
                result["errors"].append(pair)
            result["exactIntersections"].append(pair)
            if index % 20 == 0:
                print(f"{configuration}: exact operations {index}/{len(broad)}", flush=True)
        result["overThresholdCollisionCount"] = len(result["collisions"])
        result["cupInputShaftAudit"] = audit_input_shaft(snapshot, worlds, shapes, selected, configuration)

    # Recheck input identity before publishing the numerical report. A concurrent
    # operation-UI change is harmless; changed geometry/recipes invalidate it.
    for key, expected in report["inputs"].items():
        path = {"manifestSha256": catalog.manifest_path, "rightsSha256": catalog.rights_path,
                "recipeFileSha256": data_dir / "catalog/assembly-recipes.json"}[key]
        if sha(path) != expected:
            raise ValueError("Audit inputs changed during the run: " + key)
    for component in catalog.manifest.components:
        catalog.source(component, [Operation(op) for op in REQUIRED_OPERATIONS])
    if any(c["errors"] or c["cupInputShaftAudit"]["errors"] for c in report["configurations"].values()):
        report["status"] = "incomplete_exact_intersections"
        return 2
    collisions = sum(c["overThresholdCollisionCount"] + c["cupInputShaftAudit"]["overThresholdCollisionCount"]
                     for c in report["configurations"].values())
    report["status"] = "collisions_found" if collisions else "no_over_threshold_overlap_in_audited_subset"
    return 1 if collisions else 0


def audit_operation(data_dir, model_path, report):
    """Cup versus major robot bodies/jaws at exactly three recorded keyframes."""
    from tachyon import assemblies as A, realization as R
    from tachyon.cad.native import native_bounds_mm
    from tachyon.models import Operation
    from tachyon.robots.source_pack import DISPLAY

    settings, catalog, recipe, service, receipts = qualified_profile(data_dir)
    model_path = settings.local_path(str(model_path))
    model_hash = sha(model_path)
    model = json.loads(model_path.read_text())
    if (model.get("kind") != "development_cup_kinematics" or model.get("recipeId") != recipe.id
            or (model.get("units"), model.get("upAxis"), model.get("matrixLayout")) != ("m", "Y", "column-major")):
        raise ValueError("Stop: operation model kind, recipe or frame mismatch")
    baselines = [R.build_pose(service, recipe, model["designId"], k) for k in ("lower", "raised")]
    if model["engineeringHash"] not in {r.engineering_hash for r in baselines}:
        raise ValueError("Stop: operation model is stale against the current recipe/catalog")
    expected_ids = {n.id for n in recipe.template.instances}
    # Carry is the translated, upright pose over the target, not the earlier
    # lift frame at the pickup location. Release occurs at 'place', before open.
    stages = (("capture_grip", "grip"), ("carry", "translate"), ("release", "place"))
    frames = []
    for label, stage in stages:
        matches = [f for f in model["keyframes"] if f["stageId"] == stage]
        if len(matches) != 1:
            raise ValueError("Operation model must have one keyframe for " + stage)
        frame = matches[0]
        variant = recipe.model_copy(update={
            "template": recipe.template.model_copy(update={"root_transform": A.RigidTransform.model_validate(frame["rootTransform"])}),
            "configurations": {"lower": R.Pose(joint_positions=frame["jointPositions"])}})
        revision = R.build_pose(service, variant, model["designId"], "lower")
        service.validate(revision)
        worlds = A.world_transforms(revision.assembly)
        if set(frame["worldTransforms"]) != expected_ids:
            raise ValueError("Stop: operation keyframe omits or invents robot instances")
        matrix_error = max(abs(a-b) for key, pose in worlds.items()
                           for a, b in zip(pose.matrix, A.RigidTransform(matrix=frame["worldTransforms"][key]).matrix))
        if matrix_error > 1e-8:
            raise ValueError("Stop: recorded keyframe matrices disagree with production FK")
        frames.append((label, frame, revision, worlds, matrix_error))
    sources = {c.id: c for c in catalog.manifest.components}
    object_ids = {model["object"]["componentId"], *(o["componentId"] for o in model["staticObjects"])}
    for receipt in model["objectComponents"]:
        component = sources.get(receipt["id"])
        if component is None:
            raise ValueError("Stop: operation object missing from current own catalog")
        current = catalog.prepared(component)
        for key in ("sourceSha256", "meshSha256", "catalogFingerprint", "originKind", "geometryClass", "referenceOnly"):
            if receipt[key] != current[key]:
                raise ValueError("Stop: operation object receipt is stale: " + receipt["id"])
        if R._quality_reasons(component_receipt(current)):
            raise ValueError("Stop: operation object geometry is not qualified")
    if object_ids != {r["id"] for r in model["objectComponents"]}:
        raise ValueError("Stop: operation object receipt coverage mismatch")
    major_ids = MAJOR | {"dev_cup_jaw_left", "dev_cup_jaw_right"}
    selected = [n for n in recipe.template.instances if n.component_id in major_ids]
    used = {n.component_id for n in recipe.template.instances}
    if used - major_ids - ENGAGEMENT_OR_SMALL:
        raise ValueError("Stop: unclassified robot component in operation audit")
    shape_ids = {n.component_id for n in selected} | object_ids | (used & {INPUT_SHAFT})
    shapes = {key: original_shape(catalog, sources[key]) for key in sorted(shape_ids)}
    report.update(kind="bounded_original_cup_operation_interference_audit", operationModelSha256=model_hash,
                  recipeId=recipe.id, recipeHash=A.content_hash(recipe.json_data()),
                  inputs={"manifestSha256": sha(catalog.manifest_path), "rightsSha256": sha(catalog.rights_path),
                          "recipeFileSha256": sha(data_dir / "catalog/assembly-recipes.json")},
                  sources=[{"componentId": key, "sourceSha256": sources[key].source_sha256} for key in sorted(shapes)],
                  objectAssumptions={k: model["object"].get(k) for k in ("diameterM", "heightM", "dividerNativeYM", "dividerGeometryStatus")},
                  staticObjects=model["staticObjects"])
    print(f"Operation audit: {len(selected)} robot major parts including both jaws; three recorded keyframes", flush=True)
    cup_id = model["object"]["componentId"]
    for label, frame, revision, worlds, matrix_error in frames:
        cup, error = world_shape(shapes[cup_id], A.RigidTransform.model_validate(frame["objectTransform"]), DISPLAY)
        cup_bounds = native_bounds_mm(cup)
        result = {"stageId": frame["stageId"], "timeS": frame["timeS"], "objectState": frame["objectState"],
                  "connectivity": connectivity(revision.assembly), "recordedWorldMatrixMaxError": matrix_error,
                  "cupBoundsWorldMm": cup_bounds, "majorInstanceCount": len(selected),
                  "possibleCupRobotPairCount": len(selected), "aabbOverlapPairCount": 0,
                  "exactIntersectionAttemptCount": 0, "exactIntersectionCompletedCount": 0,
                  "robotExactIntersectionAttemptCount": 0, "robotExactIntersectionCompletedCount": 0,
                  "staticAabbOverlapPairCount": 0, "staticExactIntersectionAttemptCount": 0,
                  "staticExactIntersectionCompletedCount": 0,
                  "collisions": [], "exactIntersections": [], "errors": [], "staticGeometryChecks": [],
                  "excludedCounts": dict(Counter(n.component_id for n in recipe.template.instances if n.component_id not in major_ids))}
        report["configurations"][label] = result
        pairs = []
        for node in selected:
            body, e = world_shape(shapes[node.component_id], worlds[node.id], DISPLAY)
            error = max(error, e)
            pairs.append((identity(node), body, "robot_major"))
        for obj in model["staticObjects"]:
            body, e = world_shape(shapes[obj["componentId"]], A.RigidTransform.model_validate(obj["transform"]), DISPLAY)
            error = max(error, e)
            bounds = native_bounds_mm(body)
            if obj["componentId"] == "dev_operation_pin":
                result["cupBottomAbovePinTopMm"] = cup_bounds[0][1] - bounds[1][1]
            pairs.append(({k: obj[k] for k in ("instanceId", "componentId")}, body, "static_geometry"))
        result["maxWorldCenterCheckErrorMm"] = error
        for other, body, kind in pairs:
            bounds = native_bounds_mm(body)
            extents = [min(cup_bounds[1][i], bounds[1][i])-max(cup_bounds[0][i], bounds[0][i]) for i in range(3)]
            candidate = all(v > 0 for v in extents)
            pair = {"cupInstanceId": model["object"]["instanceId"], "other": other, "kind": kind,
                    "aabbOverlap": candidate, "otherBoundsWorldMm": bounds}
            if kind == "static_geometry":
                result["staticGeometryChecks"].append(pair)
            if not candidate:
                continue
            if kind == "robot_major":
                result["aabbOverlapPairCount"] += 1
                prefix = "robot"
            else:
                result["staticAabbOverlapPairCount"] += 1
                prefix = "static"
            result[prefix + "ExactIntersectionAttemptCount"] += 1
            result["exactIntersectionAttemptCount"] += 1
            try:
                volume = common_volume(cup, body)
                pair.update(status="computed", intersectionVolumeMm3=volume, exceedsReportThreshold=volume > 1.)
                result["exactIntersectionCompletedCount"] += 1
                result[prefix + "ExactIntersectionCompletedCount"] += 1
                if volume > 1.:
                    result["collisions"].append(pair)
                    print(f"{label}: CUP COLLISION / {other['instanceId']}: {volume:.6f} mm^3", flush=True)
            except Exception as exc:
                pair.update(status="error", errorType=type(exc).__name__)
                result["errors"].append(pair)
            result["exactIntersections"].append(pair)
        result["overThresholdCollisionCount"] = len(result["collisions"])
        result["robotCollisionCount"] = sum(p["kind"] == "robot_major" for p in result["collisions"])
        result["staticCollisionCount"] = sum(p["kind"] == "static_geometry" for p in result["collisions"])
        result["cupInputShaftAudit"] = audit_input_shaft(revision.assembly, worlds, shapes, selected, label)
        print(f"{label} ({frame['stageId']} t={frame['timeS']}): {result['aabbOverlapPairCount']} robot AABB candidates; "
              f"{result['robotCollisionCount']} robot overlaps >1 mm^3; "
              f"Cup-bottom minus Pin-top {result['cupBottomAbovePinTopMm']:.6f} mm", flush=True)
    if sha(model_path) != model_hash:
        raise ValueError("Stop: operation model changed during audit")
    for key, expected in report["inputs"].items():
        path = {"manifestSha256": catalog.manifest_path, "rightsSha256": catalog.rights_path,
                "recipeFileSha256": data_dir / "catalog/assembly-recipes.json"}[key]
        if sha(path) != expected:
            raise ValueError("Stop: operation audit input changed: " + key)
    for component in catalog.manifest.components:
        catalog.source(component, [Operation(op) for op in REQUIRED_OPERATIONS])
    if any(c["errors"] or c["cupInputShaftAudit"]["errors"] for c in report["configurations"].values()):
        report["status"] = "incomplete_exact_intersections"
        return 2
    collisions = sum(c["overThresholdCollisionCount"] + c["cupInputShaftAudit"]["overThresholdCollisionCount"]
                     for c in report["configurations"].values())
    report["status"] = "collisions_found" if collisions else "no_over_threshold_overlap_in_three_audited_keyframes"
    return 1 if collisions else 0


def component_receipt(value):
    from tachyon.models import PreparedComponent
    value = dict(value)
    value.pop("qualifiedOperations", None)
    return PreparedComponent.model_validate(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".local/generated-robot-a-v2")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/verification/generated-robot-a-v2-audit.json")
    parser.add_argument("--operation-model", type=Path, help="Audit only grip/translated carry/release Cup keyframes")
    args = parser.parse_args()
    data_dir, output = private_path(args.data_dir), private_path(args.output)
    if output.suffix != ".json" or output.is_relative_to(data_dir):
        raise ValueError("Choose a JSON report outside the input profile, within .local")
    start = time.monotonic()
    report = {"schemaVersion": 1, "kind": "bounded_original_development_assembly_audit",
              "createdAt": datetime.now(timezone.utc).isoformat(), "profile": str(data_dir.relative_to(ROOT)),
              "auditScriptSha256": sha(Path(__file__)), "thresholdMm3": 1., "status": "incomplete",
              "transform": "Native mm -> rigid world*DISPLAY; multiply translation only by 1000; world millimetres",
              "configurations": {}, "completeRobot": False, "physicalPerformanceVerified": False,
              "geometryExported": False, "limitations": [
                  "Original non-VEX development CAD only; no authentic-VEX acceptance",
                  "Graph connectivity/port closure do not establish physical mounting, support or load paths",
                  "Lower/raised endpoints only; no continuous motion, dynamics, tolerances or contact physics",
                  "Explicit fastener/small support and shaft/gear/screw engagement exclusions; not audited collision-free",
                  "Separate Cup input-shaft/nonmating-major-body checks apply when that component is present; intended direct engagements explicitly listed",
                  "Cup body/jaw contacts deferred until v3 profile; unused Cup source is not inserted into this assembly",
                  "All audited pairs over 1 mm^3 are findings, including declared mates; no blanket collision ignores"]}
    if args.operation_model:
        report["limitations"][2] = "Three recorded keyframes only; no dynamics, sweep, friction, force or physical grasp/release proof"
        report["limitations"][5] = "Cup and both jaws included; provisional divider/Pin/development fixture are authored geometry assumptions"
    try:
        code = audit_operation(data_dir, private_path(args.operation_model), report) if args.operation_model else audit(data_dir, report)
    except Exception as error:
        report.update(status="blocked_or_incomplete", errorType=type(error).__name__,
                      errorCode=getattr(error, "code", None), error=str(error))
        code = 2
    report["elapsedSeconds"] = time.monotonic() - start
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"{report['status']}: {output.relative_to(ROOT)}", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
