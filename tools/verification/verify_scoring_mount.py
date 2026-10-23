"""Pre-build feasibility probe, not Tachyon application or a rights grant.

Read user-supplied original STEP locally; never download or export geometry.
Reproduce with cadquery-ocp==8.0.1.1.0 (Python 3.12). Mount and lifecycle
checks are limited to this static scoring cassette, not a complete robot.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.STEPControl import STEPControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_WIRE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label
from OCP.gp import gp_Trsf

TOL = 1e-4  # mm; numerical matching tolerance, not manufacturing tolerance
EXPECTED = {
    "channel": "b47702c2710611256b80b3efadd53b3c6a502602d3d0c3151f45c5bf5ad07d56",
    "claw": "76ddd073429280482a4538c4750d2234d0ed173d6a8649d013c6669e96f39213",
}
RC = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
RL = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
SR = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def engineering_hash(snapshot):
    return digest({k: v for k, v in snapshot.items() if k != "bindings"})


def point(instance, local):
    return [sum(a * b for a, b in zip(row, local)) + instance["t"][i]
            for i, row in enumerate(instance["R"])]


def explore(shape, kind):
    e = TopExp_Explorer(shape, kind)
    while e.More():
        yield e.Current()
        e.Next()


def bounds(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, b)
    return list(b.CornerMin().Coord()), list(b.CornerMax().Coord())


def load(path, role):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED[role], f"Changed {role} source"
    r = STEPControl_Reader()
    assert r.ReadFile(str(path)) == IFSelect_RetDone
    r.SetSystemLengthUnit(1.0)  # OCCT target mm, including INCH channel source
    assert r.TransferRoots() > 0
    shape = r.OneShape()
    assert BRepCheck_Analyzer(shape).IsValid(), f"Invalid {role} BRep"
    return shape


def openings(shape, axis, plane):
    """Read real inner wires on a measured planar face; no modeled fake holes."""
    found = []
    for s in explore(shape, TopAbs_FACE):
        face = TopoDS.Face(s)
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() != GeomAbs_Plane:
            continue
        lo, hi = bounds(face)
        if abs(lo[axis] - plane) > TOL or abs(hi[axis] - plane) > TOL:
            continue
        outer = BRepTools.OuterWire_s(face)
        for w in explore(face, TopAbs_WIRE):
            if w.IsSame(outer):
                continue
            low, high = bounds(w)
            found.append({"center": [(a + b) / 2 for a, b in zip(low, high)],
                          "extent": [b - a for a, b in zip(low, high)]})
    return found


def hardware_from_claw(path):
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    d = TDocStd_Document(TCollection_ExtendedString("Tachyon feasibility inspection"))
    assert r.ReadFile(str(path)) == IFSelect_RetDone and r.Transfer(d)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(d.Main())
    labels = Sequence_TDF_Label()
    tool.GetShapes(labels)
    required = {"_8-32_Hex_Nut_275-1028": "nut",
                "_8-32_x_1_5000_Star_Drive_Screw_276-4998_No Threads": "screw"}
    found = {}
    for i in range(1, labels.Length() + 1):
        label, name = labels.Value(i), TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), name):
            identity = name.Get().ToExtString()
            if identity in required:
                found[required[identity]] = tool.GetShape_s(label)
    assert set(found) == set(required.values()), "Actual source hardware missing"
    return found


def place(shape, rotation, translation):
    t = gp_Trsf()
    t.SetValues(*[v for i, row in enumerate(rotation) for v in (*row, translation[i])])
    return BRepBuilderAPI_Transform(shape, t, False).Shape()  # assembly placement in memory


def intersection_volume(a, b):
    common = BRepAlgoAPI_Common(a, b)
    assert common.IsDone(), "Boolean intersection failed"
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(common.Shape(), props)
    return abs(props.Mass())


def main():
    if not __debug__:
        raise RuntimeError("Run this verification probe with Python assertions enabled")
    p = argparse.ArgumentParser(description=__doc__)
    for role in EXPECTED:
        p.add_argument(f"--{role}", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    shapes = {role: load(getattr(args, role), role) for role in EXPECTED}
    shapes.update(hardware_from_claw(args.claw))
    nut = shapes["nut"]
    shape_bounds = {role: bounds(s) for role, s in shapes.items()}
    channel_lo, channel_hi = shape_bounds["channel"]
    length = channel_hi[0] - channel_lo[0]
    assert abs(length - 444.5) < TOL
    web = sorted(h["center"][0] for h in openings(shapes["channel"], 2, 0)
                 if abs(h["center"][1]) < TOL)
    assert len(web) == 34 and all(abs(b - a - 12.7) < TOL for a, b in zip(web, web[1:]))
    for plane in (-15.2625, -13.2625, 13.2625, 15.2625):
        holes = openings(shapes["claw"], 1, plane)
        for x in (-6.35, 6.35):
            matches = [h for h in holes if abs(h["center"][0] - x) < TOL
                       and abs(h["center"][2] + 25.4) < TOL]
            assert len(matches) == 1
            bore = 4.6228 if abs(plane) == 15.2625 else 4.2
            assert abs(matches[0]["extent"][0] - bore) < TOL
    thickness = 1.5748
    nut_lo, nut_hi = bounds(nut)
    nut_thickness = nut_hi[1] - nut_lo[1]
    screw_length = -shape_bounds["screw"][0][1]
    thread_projection = screw_length - thickness - 30.525 - nut_thickness
    assert thread_projection >= 2 * 25.4 / 32  # nominal pitches beyond full hex nut
    nut_half = nut_thickness / 2

    def build(configuration):
        height = {"standard": 209.55, "raised": 260.35}[configuration]
        instances = {"support": {"source": "channel", "R": RL, "t": [15.2625, -25.4, length / 2]},
                     "scorer": {"source": "claw", "R": RC, "t": [0, 0, height]}}
        connections = []
        for index, offset in enumerate((-6.35, 6.35)):
            z = height + offset
            hole = min(range(len(web)), key=lambda i: abs(web[i] + length / 2 - z))
            assert abs(web[hole] + length / 2 - z) < TOL
            key = str(index)
            instances[f"screw-{key}"] = {"source": "screw", "R": SR,
                "t": [-15.2625, -25.4, z]}
            instances[f"nut-{key}"] = {"source": "nut", "R": SR,
                "t": [15.2625 + thickness + nut_half, -25.4, z]}
            connections.append({"support": "support", "channelHoleIndex": hole,
                "scorer": "scorer", "clawMountX": offset,
                "hardware": [f"screw-{key}", f"nut-{key}"], "worldZmm": z})
        return {"configuration": configuration, "instances": instances,
                "connections": connections, "joints": [], "sourceHashes": EXPECTED, "nativeDefinitions": {"screw": "_8-32_x_1_5000_Star_Drive_Screw_276-4998_No Threads", "nut": "_8-32_Hex_Nut_275-1028"},
                "bindings": {"score": {"mechanism": "scorer", "anchorMm": [0, 0, height],
                    "sketchHeightMm": height, "capability": "static_mount_only"}}}

    reports = {}
    for config in ("standard", "raised"):
        data = build(config)
        actual = {k: place(shapes[v["source"]], v["R"], v["t"])
                  for k, v in data["instances"].items()}
        # Check all instance pairs except the two declared threaded mates.
        from itertools import combinations
        threaded = {frozenset((f"screw-{i}", f"nut-{i}")) for i in range(2)}
        pairs = [(a, b) for a, b in combinations(actual, 2) if frozenset((a, b)) not in threaded]
        for i in range(2):
            # The entire nut is on the shaft, far from the under-head fillet.
            nut_start = 30.525 + thickness
            assert nut_start > 1 and nut_start + nut_thickness < screw_length
        overlaps = {f"{a}/{b}": intersection_volume(actual[a], actual[b]) for a, b in pairs}
        assert max(overlaps.values()) < 1e-3, overlaps
        edges = {key: set() for key in actual}
        for c in data["connections"]:
            rail_port = point(data["instances"][c["support"]], [web[c["channelHoleIndex"]], 0, 0])
            claw_port = point(data["instances"]["scorer"], [c["clawMountX"], 15.2625, -25.4])
            assert max(abs(a - b) for a, b in zip(rail_port, claw_port)) < TOL
            for member in [c["scorer"], *c["hardware"]]:
                assert member in actual
                edges[c["support"]].add(member)
                edges[member].add(c["support"])
        seen, todo = set(), ["support"]
        while todo:
            current = todo.pop()
            if current not in seen:
                seen.add(current)
                todo.extend(edges[current] - seen)
        assert seen == set(actual)
        reports[config] = {"engineeringHash": engineering_hash(data), "bindingsHash": digest(data["bindings"]), "componentInstances": len(actual),
            "mountReferenceHeightMm": data["bindings"]["score"]["anchorMm"][2],
            "channelHoleIndices": [c["channelHoleIndex"] for c in data["connections"]],
            "checkedAllPairsExceptThreadedMates": True, "excludedThreadedPairs": 2,
            "checkedNonMatingPairs": len(pairs), "maxIntersectionMm3": max(overlaps.values())}

    # Independent reference lifecycle, deliberately not an application service test.
    accepted = build("standard")
    initial = engineering_hash(accepted)
    initial_bindings = digest(accepted["bindings"])
    preview = copy.deepcopy(build("raised"))
    assert engineering_hash(accepted) == initial
    assert abs(preview["instances"]["scorer"]["t"][2] - accepted["instances"]["scorer"]["t"][2] - 50.8) < TOL
    discarded = None
    preview = discarded
    assert engineering_hash(accepted) == initial and digest(accepted["bindings"]) == initial_bindings
    preview = build("raised")
    prior = copy.deepcopy(accepted)
    accepted = copy.deepcopy(preview)
    assert accepted == preview and engineering_hash(accepted) != initial
    assert digest(accepted["bindings"]) != initial_bindings
    assert accepted["connections"] != prior["connections"]
    assert accepted["bindings"]["score"]["anchorMm"][2] == 260.35
    assert accepted["bindings"]["score"]["sketchHeightMm"] == 260.35
    assert accepted["bindings"]["score"]["mechanism"] in accepted["instances"]
    assert accepted["instances"]["scorer"]["t"] != prior["instances"]["scorer"]["t"]
    assert [c["channelHoleIndex"] for c in accepted["connections"]] != [c["channelHoleIndex"] for c in prior["connections"]]
    assert accepted == json.loads(json.dumps(accepted))
    accepted = copy.deepcopy(prior)
    assert engineering_hash(accepted) == initial and digest(accepted["bindings"]) == initial_bindings
    report = {"probe": "Tachyon pre-build static scoring-mount feasibility", "date": "2026-10-23",
        "probeScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tool": "cadquery-ocp==8.0.1.1.0; Python 3.12",
        "units": "mm; right-handed Z-up fixture; planned app conversion to metre Y-up is untested",
        "nativeDefinitions": accepted["nativeDefinitions"],
        "intersectionVolumeToleranceMm3": 1e-3,
        "sourceHashes": EXPECTED, "sourceValidSolids": {role: len(list(explore(s, TopAbs_SOLID)))
            for role, s in shapes.items()}, "channelLengthMm": round(length, 4),
        "channelCenterlineHoleCount": len(web), "holePitchMm": 12.7,
        "clawMountSpacingMm": 12.7, "clawMountBoreMm": 4.2,
        "nativeScrewLengthMm": screw_length, "clawThroughStackMm": 30.525,
        "hexNutThicknessMm": nut_thickness, "nominalAxialTipProjectionBeyondNutMm": thread_projection,
        "configurations": reports, "heightDeltaMm": 50.8,
        "referenceLifecycle": {"previewKeepsAccepted": True, "discardKeepsAccepted": True,
            "applyUsesExactCandidate": True, "applyChangesPortsAndTransforms": True,
            "linksAndSketchAnchorUpdated": True, "serializationRoundTrip": True,
            "undoRestoresEngineeringAndBindings": True},
        "geometryExported": False, "sourceFilesChanged": False,
        "rightsStatus": "conversion/modification/redistribution/hosting unverified",
        "limits": ["static cassette only, no complete robot", "no motor, powered lift, load or physical tests",
            "no Override object-handling/scoring/legality qualification", "no browser/app/AI lifecycle tested",
            "numerical fit tolerance is not a manufacturing tolerance", "hex nuts require assembly tightening; no locking claim"]}
    for role in EXPECTED:
        assert hashlib.sha256(getattr(args, role).read_bytes()).hexdigest() == EXPECTED[role]
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        for role in EXPECTED:
            source = getattr(args, role)
            assert args.output.resolve() != source.resolve(), "Output aliases input"
            assert not args.output.exists() or not args.output.samefile(source), "Output hardlinks input"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output)


if __name__ == "__main__":
    main()
