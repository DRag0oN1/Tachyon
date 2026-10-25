"""Original in-memory metadata only: no VEX CAD, rights, catalog or physics proof."""
from copy import deepcopy
import json
import math

import pytest

from tachyon import assemblies as A, realization as R
from tachyon.errors import TachyonError
from tachyon.operation import build_operation, INPUTS, INPUT_PHASE
from tachyon.robots.builder import Part, RecipeBuilder
from tachyon.robots.source_pack import DISPLAY

T = A.RigidTransform
EVIDENCE = "Original synthetic operation metadata; no CAD or physical validation"


def operation_case():
    """Closed parallel linkage, thirty coupled lift joints, two jaws and screw.

    Every frame below is independently authored test data. Dimensions exercise
    the declared development scenario; they do not authenticate any component.
    """
    def part(identity, ports):
        return Part("dev_"+identity, "a"*64, A.content_hash(identity),
                    {key: A.AttachmentPort(id=key, kind=kind, frame=frame, evidence=EVIDENCE)
                     for key, (kind, frame) in ports.items()}, "structure")

    hinge_frame = T(matrix=(0, 0, 1, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1))
    parts = {"base": part("base", {
        "lower": ("revolute", T.translation(0, .3, 0).compose(hinge_frame)),
        "upper": ("revolute", T.translation(0, .3762, 0).compose(hinge_frame)),
        "spin": ("shaft", T())}),
        "link": part("link", {"back": ("revolute", T()), "front": ("revolute", T.translation(.2921, 0, 0))}),
        "carrier": part("carrier", {"lower": ("revolute", T()), "upper": ("revolute", T.translation(0, -.0762, 0)),
            "cup": ("mount", hinge_frame.inverse().compose(T.translation(-.0762, -.0635, .0127)))}),
        "cup": part("cup_bridge", {"mount": ("mount", T()), "screw": ("shaft", T.translation(.02, .01, 0)),
            "left-support": ("mount", T.translation(.02, .01, -.02)),
            "right-support": ("mount", T.translation(.02, .01, .02))}),
        "screw": part("cup_screw", {"axis": ("shaft", T()),
            "left": ("shaft", T.translation(0, 0, -.02)), "right": ("shaft", T.translation(0, 0, .02))}),
        "input": part("cup_input_shaft", {"axis": ("shaft", T()),
            "left": ("shaft", T.translation(0, 0, -.02)), "right": ("shaft", T.translation(0, 0, .02))}),
        "support": part("support", {"mount": ("mount", T()), "bore": ("bearing", T())}),
        "rotor": part("rotor", {"axis": ("shaft", T())})}
    jaw_frame = T.rotation((0, 1, 0), math.pi/2)
    for side, sign in (("left", -1), ("right", 1)):
        parts["cup"].ports[side] = A.AttachmentPort(id=side, kind="prismatic", evidence=EVIDENCE,
            frame=T.translation(*DISPLAY.point((.0762+sign*.044, .0127, -.0127))).compose(jaw_frame))
        parts[side] = part("cup_jaw_"+side, {"slide": ("prismatic", jaw_frame)})
    b = RecipeBuilder("development-operation-metadata", "A", parts)
    b.root_part("base", "base", "chassis")
    low, high = -.65, .4
    controls = []
    for level in ("lower", "upper"):
        joint = "right-"+level+"-ground-pivot"
        b.attached(level+"-link", "link", "scorer", "base", level, "back", kind="revolute",
                   axis=(0, 0, -1), limits=(-.75, .5), lower=low, raised=high, joint_id=joint)
        controls.append((joint, 1., 0.))
    b.attached("carrier", "carrier", "scorer", "lower-link", "front", "lower", kind="revolute",
               axis=(0, 0, -1), limits=(-.5, .75), lower=-low, raised=-high, joint_id="carrier-pivot")
    b.constraint("carrier-closure", "upper-link", "front", "carrier", "upper", kind="revolute",
                 axis=(0, 0, -1), limits=(-.5, .75), lower=-low, raised=-high)
    controls.extend([("carrier-pivot", -1., 0.), ("carrier-closure", -1., 0.)])
    for index in range(26):
        ratio, offset = (-7. if index % 2 else 7.), math.pi/12
        joint = "lift-rotor-"+str(index)
        b.attached(joint, "rotor", "scorer", "base", "spin", "axis", kind="revolute", axis=(0, 0, 1),
                   limits=(-10., 10.), lower=ratio*low+offset, raised=ratio*high+offset, joint_id=joint+"-spin")
        controls.append((joint+"-spin", ratio, offset))
    b.attached("cup-grip-frame", "cup", "cup_cradle", "carrier", "cup", "mount")
    b.attached("cup-opposed-screw", "screw", "cup_cradle", "cup-grip-frame", "screw", "axis", kind="revolute",
               axis=(0, 0, 1), limits=(-40., 40.), joint_id="cup-grip-screw-spin")
    parts['cup'].ports['input']=A.AttachmentPort(id='input',kind='shaft',frame=T.translation(.02,.0608,0.),evidence=EVIDENCE)
    b.attached('cup-transmission-input-shaft','input','cup_cradle','cup-grip-frame','input','axis',kind='revolute',
        axis=(0,0,1),limits=(-100.,100.),lower=INPUT_PHASE,raised=INPUT_PHASE,joint_id=INPUTS[0])
    for side in ("left", "right"):
        support = "cup-"+side+"-support"
        b.attached(support, "support", "cup_cradle", "cup-grip-frame", side+"-support", "mount")
        b.constraint("cup-screw-"+side+"-support", support, "bore", "cup-opposed-screw", side,
                     kind="revolute", axis=(0, 0, 1), limits=(-40., 40.))
        parts['cup'].ports[side+'-input']=A.AttachmentPort(id=side+'-input',kind='mount',
            frame=T.translation(.02,.0608,-.02 if side=='left' else .02),evidence=EVIDENCE)
        b.attached('input-'+support,'support','cup_cradle','cup-grip-frame',side+'-input','mount')
        b.constraint('cup-input-'+side+'-support','input-'+support,'bore','cup-transmission-input-shaft',side,
            kind='revolute',axis=(0,0,1),limits=(-100.,100.),lower=INPUT_PHASE,raised=INPUT_PHASE)
        b.attached("cup-"+side+"-jaw", side, "cup_cradle", "cup-grip-frame", side, "slide", kind="prismatic",
                   axis=(0, 0, 1), limits=(-.01, .000001) if side == "left" else (-.000001, .01),
                   joint_id="cup-"+side+"-jaw-slide")
    edit = dict(id="scoring-group", driverJointId=controls[0][0], members=[n["id"] for n in b.instances if n["id"] != "base"],
                coupling=[dict(jointId=j, ratio=ratio, offset=offset) for j, ratio, offset in controls])
    reach = {key: None for key in ("lower", "raised")}
    recipe = R.Recipe.model_validate(b.compile(reach=reach, edit_group=edit))
    definitions = [A.ComponentDefinition(id=p.component_id, name=EVIDENCE, source_url="urn:synthetic-operation",
        source_sha256=p.source_sha256, mesh_sha256="b"*64, mesh_url="urn:no-asset",
        catalog_fingerprint=p.catalog_fingerprint, origin_kind="tachyon_authored", geometry_class="test_fixture",
        declared_use="metadata_test", qualified_operations=("assembly_placement",), ports=tuple(p.ports.values()))
        for p in parts.values()]
    service = A.AssemblyService(definitions)
    accepted = R.build_pose(service, recipe, "synthetic-operation", "lower")
    context = R.ArchitectureContext(proposal=dict(id="synthetic-A", alternative="A"), spec={})
    facts = dict(fourBar=dict(sourcePivotSpanM=.2921, lowerAngleRad=low, raisedAngleRad=high),
                 handling=dict(kind="original_parallel_cup_clamp", modeledObjectDiameterM=.08,
                               modeledObjectHeightM=.1645, screwLeadM=.008,inputJoints=list(INPUTS),
                               transmission=dict(inputRatio=-7.,inputOffsetRad=INPUT_PHASE),
                               anchor=dict(id="cup-clamp-center", instanceId="cup-grip-frame",
                                           localPointM=list(DISPLAY.point((.0762, .0127, .0635))))))
    public = [dict(id="dev_operation_"+kind, originKind="tachyon_authored", geometryClass="test_fixture")
              for kind in ("cup", "pin", "target")]
    return service, context, recipe, accepted, public, facts


@pytest.fixture(scope="module")
def result():
    return build_operation(*operation_case())


def test_all_eight_stages_close_with_thirty_lift_couplings_and_no_input_mutation():
    case = operation_case()
    service, context, recipe, accepted, public, facts = case
    before = (recipe.json_data(), accepted.json_data(), deepcopy(public), deepcopy(facts))
    operation = build_operation(*case)
    assert (recipe.json_data(), accepted.json_data(), public, facts) == before
    assert [s["id"] for s in operation["stages"]] == ["approach", "grip", "lift", "translate", "alignment", "place", "open", "retract"]
    assert len(operation["coupling"]) == 30
    assert operation["validation"]["sampleCount"] == 33
    assert len(operation["keyframes"]) == 9
    assert all(s["graphValid"] for s in operation["validation"]["samples"])
    assert operation["revisionId"] == accepted.id
    json.dumps(operation, allow_nan=False)
    for keyframe in operation["keyframes"]:
        q = keyframe["jointPositions"]
        theta = q[recipe.edit_group.driver_joint_id]
        for coupling in recipe.edit_group.coupling:
            assert q[coupling.joint_id] == pytest.approx(coupling.ratio*theta+coupling.offset)
        for screw in ("cup-grip-screw-spin", "cup-screw-left-support", "cup-screw-right-support"):
            assert q["cup-left-jaw-slide"] == pytest.approx(.008*q[screw]/(2*math.pi))
            assert q["cup-right-jaw-slide"] == pytest.approx(-.008*q[screw]/(2*math.pi))
            for joint in INPUTS:
                assert q[joint] == pytest.approx(-7*q[screw]+INPUT_PHASE)


def test_floor_capture_carry_contact_release_and_frozen_retraction(result):
    frames = {f["stageId"]: f for f in result["keyframes"]}
    cup = result["object"]
    initial, target = [T.model_validate(cup[key]) for key in ("initialTransform", "targetTransform")]
    assert initial.point()[1] == 0
    assert initial.point(cup["gripPointLocalM"])[1] == pytest.approx(frames["grip"]["anchorWorldPointM"][1])
    assert 0 < frames["grip"]["anchorWorldPointM"][1] < .1645
    for stage, height in (("lift", .290), ("translate", .290), ("alignment", .290), ("place", .20375)):
        assert T.model_validate(frames[stage]["objectTransform"]).point()[1] == pytest.approx(height)
    for stage in ("translate", "alignment", "place"):
        assert T.model_validate(frames[stage]["objectTransform"]).point()[2] == pytest.approx(.60)
    relative = T.model_validate(cup["heldRelativeTransform"])
    for frame in result["keyframes"]:
        actual = T.model_validate(frame["objectTransform"])
        if frame["objectState"] == "held":
            anchor = T(matrix=frame["worldTransforms"]["cup-grip-frame"]).compose(T.translation(*cup["anchor"]["localPointM"]))
            assert actual.matrix == pytest.approx(anchor.compose(relative).matrix)
        elif frame["objectState"] == "placed":
            assert actual == target
        else:
            assert actual == initial
    assert frames["place"]["objectState"] == "placed"
    assert frames["place"]["jointPositions"]["cup-left-jaw-slide"] == 0
    assert frames["open"]["jointPositions"]["cup-left-jaw-slide"] == pytest.approx(-.01)
    assert result["events"] == [dict(type="capture", timeS=3., objectState="held"), dict(type="release", timeS=11., objectState="placed")]


def test_declared_pin_fixture_coface_nesting_and_provisional_geometry_are_explicit(result):
    target = result["target"]
    assert target["positionM"] == pytest.approx([0., .20375, .6])
    assert target["liftAngleRad"] == pytest.approx(math.asin(math.sin(-.65)+.20375/.2921))
    assert target["nestingDepthM"] == pytest.approx(.08125)
    assert target["radialClearanceM"] == pytest.approx(.018)
    assert target["supportCofaceErrorM"] < 1e-12
    assert target["dividerLowerFaceYM"] == pytest.approx(.285)
    static = {o["componentId"]: T.model_validate(o["transform"]) for o in result["staticObjects"]}
    assert static["dev_operation_pin"].point(DISPLAY.point((0., .165, 0.))) == pytest.approx([0., .285, .60])
    assert static["dev_operation_target"].point() == pytest.approx([0., 0., .60])
    assert result["object"]["dividerGeometryStatus"] == "provisional_pending_figure_confirmation"
    assert result["validation"]["approachClearanceOverPinTopM"] == pytest.approx(.005)
    assert result["validation"]["missing"] == []
    assert result["target"]["fixtureStatus"] == "modeled_development_fixture_not_official_goal"
    assert not result["validation"]["physicalPerformanceVerified"]
    assert not result["validation"]["scoringVerified"]
    assert not result["validation"]["authenticCadAcceptance"]


def test_exported_graph_reconstructs_every_keyframe_using_scalar_fk(result):
    graph = result["kinematicGraph"]
    edges = {edge["childInstanceId"]: edge for edge in graph["treeRelationships"]}
    for keyframe in result["keyframes"]:
        world = {graph["rootInstanceId"]: T.model_validate(keyframe["rootTransform"])}
        pending = dict(edges)
        while pending:
            ready = [edge for edge in pending.values() if edge["parentInstanceId"] in world]
            assert ready
            for edge in ready:
                if edge["kind"] == "fixed":
                    local = T(matrix=edge["fixedLocalMatrix"])
                else:
                    q = keyframe["jointPositions"][edge["id"]]
                    motion = T.rotation(edge["axis"], q) if edge["kind"] == "revolute" else T.translation(*(q*v for v in edge["axis"]))
                    local = T.model_validate(edge["parentPortFrame"]).compose(motion).compose(T(matrix=edge["postMatrix"]))
                world[edge["childInstanceId"]] = world[edge["parentInstanceId"]].compose(local)
                del pending[edge["childInstanceId"]]
        assert set(world) == set(keyframe["worldTransforms"])
        for identity, transform in world.items():
            assert transform.matrix == pytest.approx(keyframe["worldTransforms"][identity], abs=1e-9)


def test_object_receipts_are_returned_intact_for_mesh_loading():
    case = operation_case()
    public = case[4]
    for index, receipt in enumerate(public):
        receipt.update(meshUrl=f"/api/assets/{index}.glb", sourceSha256="c"*64,
                       attribution="Synthetic metadata only; no asset exists")
    public.append(dict(id="unrelated", meshUrl="urn:unrelated"))
    result = build_operation(*case)
    assert result["objectComponents"] == public[:3]
    assert {c["id"] for c in result["objectComponents"]} == {
        result["object"]["componentId"], *(o["componentId"] for o in result["staticObjects"])}


def test_original_cup_revision_has_connected_fabrications_and_clear_guide_underpasses():
    """Native original BReps only; no source files, rights records or meshes."""
    import cadquery as cq
    from tachyon.robots.cup_handling import development_parts
    parts = development_parts()
    for alias in ('cup_bridge', 'cup_screw', 'cup_input_shaft', 'pin_handoff', 'cup_alignment'):
        shape = parts[alias].toCompound()
        assert shape.isValid(), alias
        assert len(shape.Solids()) == 1, alias
    shaft = parts['cup_input_shaft'].toCompound().BoundingBox()
    assert (shaft.xlen, shaft.ylen, shaft.zlen) == pytest.approx((3.175, 3.175, 209.55))
    bridge = parts['cup_bridge'].toCompound()
    guide = parts['cup_rail'].toCompound()
    stop = parts['cup_alignment'].toCompound().moved(cq.Location(cq.Vector(0., 3.175, 0.)))
    assert abs(bridge.intersect(guide).Volume()) < 1e-6
    assert abs(stop.intersect(guide).Volume()) < 1e-6


@pytest.mark.parametrize("fault,code", [("object", "OBJECT_MISSING"), ("dimension", "UNSUPPORTED"),
                                       ("recipe", "UNSUPPORTED"), ("stale", "STALE_REVISION"),
                                       ("capture", "CAPTURE_FAILED"), ("limit", "POSE_INVALID"),
                                       ("sample-closure", "POSE_INVALID")])
def test_rejects_missing_unsupported_stale_nonfitting_or_open_graphs(fault, code):
    service, context, recipe, accepted, public, facts = operation_case()
    if fault == "object":
        public.pop()
    elif fault == "dimension":
        facts["handling"]["modeledObjectDiameterM"] = .09
    elif fault == "recipe":
        recipe = recipe.model_copy(update={"alternative": "B"})
    elif fault == "stale":
        accepted = service.place(accepted, "base", T.translation(.01, 0., 0.))
    else:
        raw = recipe.json_data()
        if fault == "capture":
            port = next(p for p in raw["portFrames"]["dev_cup_bridge"]["ports"] if p["id"] == "left")
            port["frame"]["matrix"][12] -= .001
            definition = service._components["dev_cup_bridge"]
            service._components[definition.id] = A.ComponentDefinition.model_validate({**definition.json_data(),
                "ports": raw["portFrames"][definition.id]["ports"]})
        elif fault == "limit":
            joint = next(r for r in raw["template"]["relationships"] if r["id"] == "cup-left-jaw-slide")
            joint["limits"][0] = -.005
        else:
            # Closed endpoints alone cannot qualify the opened clamp path.
            joint = next(r for r in raw["template"]["relationships"] if r["id"] == "cup-screw-right-support")
            joint["axis"] = [1., 0., 0.]
        recipe = R.Recipe.model_validate(raw)
        accepted = R.build_pose(service, recipe, accepted.assembly.design_id, "lower")
    with pytest.raises(TachyonError) as caught:
        build_operation(service, context, recipe, accepted, public, facts)
    assert caught.value.code == "OPERATION_"+code
    if fault == "sample-closure":
        assert "PORT_ALIGNMENT" in caught.value.message


def test_non_development_geometry_cannot_use_the_fixture_scenario():
    service, context, recipe, accepted, public, facts = operation_case()
    definition = service._components["dev_base"]
    service._components[definition.id] = definition.model_copy(update={"origin_kind": "manufacturer_cad"})
    accepted = R.build_pose(service, recipe, accepted.assembly.design_id, "lower")
    with pytest.raises(TachyonError, match="original development") as caught:
        build_operation(service, context, recipe, accepted, public, facts)
    assert caught.value.code == "OPERATION_UNSUPPORTED"


def test_raised_accepted_revision_still_derives_capture_from_the_lower_reference():
    service, context, recipe, accepted, public, facts = operation_case()
    accepted = R.build_pose(service, recipe, accepted.assembly.design_id, "raised")
    result = build_operation(service, context, recipe, accepted, public, facts)
    assert result["revisionId"] == accepted.id
    assert result["keyframes"][0]["jointPositions"][recipe.edit_group.driver_joint_id] == -.65
    assert T.model_validate(result["object"]["initialTransform"]).point()[1] == 0


@pytest.mark.parametrize("height", [.165, .125, float("nan"), float("inf"), -.01, True, "120"])
def test_tall_or_unsupported_fixture_is_rejected_instead_of_claiming_a_clear_approach(height):
    with pytest.raises(TachyonError) as caught:
        build_operation(*operation_case(), fixture_height=height)
    assert caught.value.code == "OPERATION_UNSUPPORTED"
    if height == .165:
        assert "clearance shortfall" in caught.value.message
