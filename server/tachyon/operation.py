"""Bounded development-Cup kinematics, using the existing recipe pose engine.

Call after RealizationService._current has validated the catalog, rights, recipe
and accepted revision. ``public`` must also contain the three current prepared
development object receipts. This pure function reads/writes no assets or state.
Its samples prove joint limits and graph closure, not contact, scoring or physics.
"""
from __future__ import annotations

import math

from pydantic import ValidationError

from . import assemblies as A
from . import realization as R
from .errors import TachyonError
from .robots.source_pack import DISPLAY, native_pose

T = A.RigidTransform
LEFT, RIGHT = "cup-left-jaw-slide", "cup-right-jaw-slide"
SCREWS = ("cup-grip-screw-spin", "cup-screw-left-support", "cup-screw-right-support")
INPUTS = ("cup-input-shaft-spin", "cup-input-left-support", "cup-input-right-support")
OBJECT_IDS = ("dev_operation_cup", "dev_operation_pin", "dev_operation_target")
DIAMETER, HEIGHT, WALL = .080, .1645, .002
PIN_DIAMETER, PIN_HEIGHT = .040, .165
DIVIDER_BOTTOM, DIVIDER_TOP = .08125, .08325  # provisional development geometry
TARGET_Z, CARRY_Y = .60, .290
SPAN, LOW, HIGH, LEAD = .2921, -.65, .4, .008
INPUT_RATIO, INPUT_PHASE = -7., math.pi/12
OPEN_SPIN = -.010 * 2*math.pi/LEAD
SUBSTEPS = 4
TOLERANCE = 1e-5


def _fail(code, message):
    raise TachyonError("OPERATION_" + code, message)


def _close(a, b, tolerance=TOLERANCE):
    return math.dist(a, b) <= tolerance


def _anchor(world, anchor):
    return world[anchor["instanceId"]].compose(T.translation(*anchor["localPointM"]))


def _placement_graph(recipe, accepted):
    """The frontend can use the same Pparent Motion(q) Mate inverse(Pchild)."""
    nodes = {n.id: n for n in recipe.template.instances}
    frames = {key: {p.id: p.frame for p in value.ports} for key, value in recipe.port_frames.items()}
    tree, constraints, placement_ids = [], [], {}
    for node in nodes.values():
        if node.parent_id is None:
            continue
        candidates = [r for r in recipe.template.relationships
                      if (r.parent_instance_id, r.child_instance_id) == (node.parent_id, node.id)
                      and (node.placement_relationship_id is None or r.id == node.placement_relationship_id)]
        if len(candidates) != 1:
            _fail("UNSUPPORTED", "Every operation placement needs one unambiguous tree relationship")
        placement_ids[node.id] = candidates[0].id
    for rel in recipe.template.relationships:
        record = rel.json_data()
        record["parentPortFrame"] = frames[nodes[rel.parent_instance_id].component_id][rel.parent_port_id].json_data()
        record["childPortFrame"] = frames[nodes[rel.child_instance_id].component_id][rel.child_port_id].json_data()
        post = rel.mate_transform.compose(frames[nodes[rel.child_instance_id].component_id][rel.child_port_id].inverse())
        record["postMatrix"] = list(post.matrix)
        if rel.kind == "fixed":
            record["fixedLocalMatrix"] = list(frames[nodes[rel.parent_instance_id].component_id][rel.parent_port_id].compose(post).matrix)
        (tree if placement_ids.get(rel.child_instance_id) == rel.id else constraints).append(record)
    return dict(rootInstanceId=recipe.template.root_instance_id,
                rootTransform=recipe.template.root_transform.json_data(),
                instances=[dict(id=n.id, componentId=n.component_id, parentId=n.parent_id,
                                placementRelationshipId=placement_ids.get(n.id),
                                acceptedRelativeTransform=next(i.transform.json_data() for i in accepted.assembly.instances if i.id == n.id))
                           for n in nodes.values()],
                treeRelationships=tree, constraints=constraints,
                formula="Wchild = Wparent * parentPortFrame * Motion(q) * mateTransform * inverse(childPortFrame)")


def build_operation(service, context, recipe, accepted, public, facts, *, fixture_height=.120):
    """Return nine keyframes/eight stages for the original development clamp.

    Matrices are column major, metres/Y-up, in prepared-display frames. Interpolate
    all joint scalars and root translation linearly, then run FK; do not interpolate
    member matrices. Capture is at the grip endpoint; release is at the start of
    opening, after the held Cup coincides with the predeclared fixture target.
    No accepted revision, recipe configuration or rights record is changed.
    """
    if (not isinstance(fixture_height, (int, float)) or isinstance(fixture_height, bool)
            or not math.isfinite(fixture_height) or fixture_height < 0):
        _fail("UNSUPPORTED", "Development fixture height must be a finite nonnegative metre value")
    clearance = CARRY_Y-(fixture_height+PIN_HEIGHT)
    if clearance < .005-TOLERANCE:
        _fail("UNSUPPORTED", f"Fixture approach clearance is {clearance:.6f} m; at least 0.005 m is required. The 165 mm fixture has a clearance shortfall")
    if abs(fixture_height-.120) > 1e-9:
        _fail("UNSUPPORTED", "This bounded operation uses the modeled 120 mm development fixture")
    target_y = fixture_height+PIN_HEIGHT-DIVIDER_BOTTOM
    accepted = A.AssemblyRevision.model_validate(accepted)
    service.validate(accepted)
    group = recipe.edit_group
    if (recipe.alternative != "A" or context.proposal.get("alternative") != "A" or group is None
            or any(not c.id.startswith("dev_") or c.origin_kind != "tachyon_authored"
                   or c.geometry_class != "test_fixture" for c in accepted.assembly.components)):
        _fail("UNSUPPORTED", "Cup operation is limited to the original development architecture A")
    receipts = {p["id"]: p for p in public}
    for identity in OBJECT_IDS:
        receipt = receipts.get(identity)
        if (receipt is None or receipt.get("originKind") != "tachyon_authored"
                or receipt.get("geometryClass") != "test_fixture"):
            _fail("OBJECT_MISSING", f"Current original development object receipt required: {identity}")
    expected = R.build_pose(service, recipe, accepted.assembly.design_id, accepted.assembly.configuration_id)
    if accepted.engineering_hash != expected.engineering_hash:
        _fail("STALE_REVISION", "Accepted engineering content differs from the current recipe")

    handling, four_bar = facts.get("handling", {}), facts.get("fourBar", {})
    anchor = handling.get("anchor", {})
    local_anchor = DISPLAY.point((.0762, .0127, .0635))
    nodes = {n.id: n for n in recipe.template.instances}
    expected_members = {"cup-grip-frame": "dev_cup_bridge", "cup-left-jaw": "dev_cup_jaw_left",
                        "cup-right-jaw": "dev_cup_jaw_right", "cup-opposed-screw": "dev_cup_screw",
                        "cup-transmission-input-shaft": "dev_cup_input_shaft"}
    if (handling.get("kind") != "original_parallel_cup_clamp"
            or anchor.get("instanceId") != "cup-grip-frame"
            or anchor.get("localPointM") is None or not _close(anchor["localPointM"], local_anchor)
            or any(key not in nodes or nodes[key].component_id != value for key, value in expected_members.items())):
        _fail("UNSUPPORTED", "Operation requires the current original Cup frame, jaw and screw interfaces")
    for actual, declared in ((four_bar.get("sourcePivotSpanM"), SPAN),
                             (four_bar.get("lowerAngleRad"), LOW), (four_bar.get("raisedAngleRad"), HIGH),
                             (handling.get("modeledObjectDiameterM"), DIAMETER),
                             (handling.get("modeledObjectHeightM"), HEIGHT), (handling.get("screwLeadM"), LEAD)):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool) or not math.isfinite(actual) or abs(actual-declared) > 1e-9:
            _fail("UNSUPPORTED", "Operation dimensions, lift endpoints or screw lead differ from the bounded development model")
    transmission = handling.get("transmission", {})
    if (handling.get("inputJoints") != list(INPUTS) or transmission.get("inputRatio") != INPUT_RATIO
            or abs(transmission.get("inputOffsetRad", 0.)-INPUT_PHASE) > 1e-9):
        _fail("UNSUPPORTED", "The original Cup transfer must declare its three coupled 7:1 input joints and phase")
    joints = {r.id: r for r in recipe.template.relationships if r.kind != "fixed"}
    if (any(j not in joints for j in (LEFT, RIGHT, *SCREWS, *INPUTS, group.driver_joint_id))
            or any(joints[j].kind != "prismatic" for j in (LEFT, RIGHT))
            or any(joints[j].kind != "revolute" for j in (*SCREWS, *INPUTS, group.driver_joint_id))
            or {c.joint_id for c in group.coupling} - joints.keys()
            or {LEFT, RIGHT, *SCREWS, *INPUTS} & {c.joint_id for c in group.coupling}):
        _fail("UNSUPPORTED", "The lift and opposed-screw joint schema is unavailable or ambiguous")
    driver = next((c for c in group.coupling if c.joint_id == group.driver_joint_id), None)
    if driver is None or driver.ratio != 1 or driver.offset != 0:
        _fail("UNSUPPORTED", "The scoring driver must be the lift angle itself")
    for name, angle in (("lower", LOW), ("raised", HIGH)):
        if name not in recipe.configurations:
            _fail("UNSUPPORTED", "Both registered lift endpoints are required")
        positions = recipe.configurations[name].joint_positions
        if (abs(positions[group.driver_joint_id]-angle) > 1e-9
                or any(not math.isfinite(c.ratio) or not math.isfinite(c.offset)
                       or abs(positions[c.joint_id]-(c.ratio*angle+c.offset)) > 1e-9 for c in group.coupling)):
            _fail("UNSUPPORTED", "Registered lift endpoints do not satisfy their declared couplings")

    def positions(theta, closure, travel=0.):
        result = dict(recipe.configurations["lower"].joint_positions)
        result.update({c.joint_id: c.ratio*theta+c.offset for c in group.coupling})
        result.update({LEFT: -.01*(1-closure), RIGHT: .01*(1-closure),
                       **{j: OPEN_SPIN*(1-closure) for j in SCREWS},
                       **{j: INPUT_RATIO*OPEN_SPIN*(1-closure)+INPUT_PHASE for j in INPUTS}})
        # Prescribed rolling kinematics through the actual linked drive joints;
        # this is not traction/contact dynamics or achieved motor performance.
        for side,sign in (("right",1.),("left",-1.)):
            for station in ("rear","middle","front"):
                joint=f"{side}-{station}-shaft-mount"
                if joint in result:result[joint]=sign*(-1. if station=="middle" else 1.)*travel/.0508
        return result

    def pose(joint_positions, root, stage):
        try:
            current = recipe.model_copy(update={
                "template": recipe.template.model_copy(update={"root_transform": root}),
                "configurations": {"lower": R.Pose(joint_positions=joint_positions)}})
            revision = R.build_pose(service, current, accepted.assembly.design_id, "lower")
            service.validate(revision)
            return A.world_transforms(revision.assembly)
        except (TachyonError, ValidationError, ValueError, KeyError) as error:
            code = error.code if isinstance(error, TachyonError) else "INVALID_JOINT_CONFIGURATION"
            _fail("POSE_INVALID", f"{stage}: {code}; recipe limits and all graph closures must hold")

    root = recipe.template.root_transform
    lower_world = pose(positions(LOW, 1.), root, "lower reference")
    lower_anchor = _anchor(lower_world, anchor).point()
    grip_y = lower_anchor[1]
    if not 0 < grip_y < HEIGHT:
        _fail("CAPTURE_FAILED", "The floor-standing Cup cannot meet the lower grip inside its modeled height")
    grip_point = DISPLAY.point((0., grip_y, 0.))
    initial = native_pose((lower_anchor[0]*1000, 0., lower_anchor[2]*1000))
    held_relative = _anchor(lower_world, anchor).inverse().compose(initial)
    # Independent of the achieved endpoint: declared fixture height and target Z.
    target = native_pose((lower_anchor[0]*1000, target_y*1000, TARGET_Z*1000))
    target_anchor = target.point(grip_point)
    def angle_for_height(height):
        argument = math.sin(LOW) + height/SPAN
        if not -1 <= argument <= 1:
            _fail("TARGET_UNREACHABLE", "Fixture height exceeds the modeled lift span")
        angle = math.asin(argument)
        if not LOW <= angle <= HIGH:
            _fail("TARGET_UNREACHABLE", "Fixture operation requires an angle outside the registered lift endpoints")
        return angle

    goal, carry = angle_for_height(target_y), angle_for_height(CARRY_Y)
    high_world = pose(positions(carry, 1.), root, "carry reference")
    goal_world = pose(positions(goal, 1.), root, "placement reference")
    high_anchor = _anchor(high_world, anchor).point()
    goal_anchor = _anchor(goal_world, anchor).point()
    if not _close(goal_anchor, (lower_anchor[0], grip_y+target_y, goal_anchor[2])):
        _fail("TARGET_UNREACHABLE", "Actual recipe FK does not realize the declared four-bar height equation")
    travel_high, travel_goal = TARGET_Z-high_anchor[2], TARGET_Z-goal_anchor[2]

    # Endpoint tuples: stage, time, theta, closure, prescribed root Z travel.
    plan = [("start", 0., LOW, 0., -.12), ("approach", 2., LOW, 0., 0.),
            ("grip", 3., LOW, 1., 0.), ("lift", 5., carry, 1., 0.),
            ("translate", 8., carry, 1., travel_high), ("alignment", 9., carry, 1., travel_high),
            ("place", 11., goal, 1., travel_goal), ("open", 12., goal, 0., travel_goal),
            ("retract", 14., carry, 0., travel_goal-.12)]
    capture_time, release_time = plan[2][1], plan[6][1]
    keyframes, samples = [], []
    captured = False
    placement_error = 0.

    def evaluate(stage, time, theta, closure, travel, *, endpoint=False):
        nonlocal captured, placement_error
        q = positions(theta, closure, travel)
        root_pose = T.translation(0., 0., travel).compose(root)
        world = pose(q, root_pose, stage)
        anchor_pose = _anchor(world, anchor)
        if time < capture_time:
            object_pose, state = initial, "floor"
        elif time < release_time:
            object_pose, state = anchor_pose.compose(held_relative), "held"
        else:
            object_pose, state = target, "placed"
        # Source pad points of the two ORIGINAL development jaws, not AABBs.
        left = world["cup-left-jaw"].point(DISPLAY.point((.004, 0., .0762)))
        right = world["cup-right-jaw"].point(DISPLAY.point((-.004, 0., .0762)))
        gap = math.dist(left, right)
        if abs(gap-(DIAMETER+.020*(1-closure))) > TOLERANCE:
            _fail("CAPTURE_FAILED", f"{stage}: actual jaw pad FK disagrees with opposed-screw span")
        midpoint = tuple((a+b)/2 for a, b in zip(left, right))
        if not _close(midpoint, anchor_pose.point()) or abs(left[1]-right[1]) > TOLERANCE:
            _fail("CAPTURE_FAILED", f"{stage}: pad center/axis does not match the horizontal Cup grip")
        if time == capture_time:
            if abs(gap-DIAMETER) > TOLERANCE or not _close(object_pose.point(grip_point), anchor_pose.point()):
                _fail("CAPTURE_FAILED", "Closed pads must fit the 80 mm Cup at its declared grip point")
            captured = True
        if capture_time <= time <= release_time:
            held = anchor_pose.compose(held_relative)
            if not _close(held.point(grip_point), anchor_pose.point()):
                _fail("CAPTURE_FAILED", "Held Cup must follow the actual moving anchor")
            if any(abs(held.matrix[i]-initial.matrix[i]) > TOLERANCE for i in range(12)):
                _fail("UNSUPPORTED", "This operation supports upright Cup translation, not independent tilt")
            if time == release_time:
                placement_error = max(abs(a-b) for a, b in zip(held.matrix, target.matrix))
                if placement_error > TOLERANCE:
                    _fail("PLACEMENT_FAILED", "Held Cup does not coincide with the independently declared target at release")
        samples.append(dict(timeS=time, stageId=stage, graphValid=True, jawSpanM=gap,
                            objectState=state, objectTransform=object_pose.json_data()))
        if endpoint:
            keyframes.append(dict(timeS=time, stageId=stage, jointPositions=q,
                                  rootTransform=root_pose.json_data(),
                                  worldTransforms={key: list(value.matrix) for key, value in world.items()},
                                  anchorWorldPointM=list(anchor_pose.point()), objectState=state,
                                  objectTransform=object_pose.json_data()))

    evaluate(*plan[0], endpoint=True)
    for previous, current in zip(plan, plan[1:]):
        for index in range(1, SUBSTEPS+1):
            fraction = index/SUBSTEPS
            values = [a+(b-a)*fraction for a, b in zip(previous[1:], current[1:])]
            evaluate(current[0], *values, endpoint=index == SUBSTEPS)
    if not captured:
        _fail("CAPTURE_FAILED", "Operation did not pass its capture predicate")

    pin_top = fixture_height + PIN_HEIGHT
    high_bottom = _anchor(high_world, anchor).compose(held_relative).point()[1]
    clearance = high_bottom-pin_top
    gaps = []
    if clearance < .005-TOLERANCE:
        _fail("UNSUPPORTED", "Actual recipe carry pose does not provide the required 5 mm nominal Pin-top clearance")
    return dict(schemaVersion=1, kind="development_cup_kinematics", status="kinematic_preview",
                designId=accepted.assembly.design_id, revisionId=accepted.id,
                engineeringHash=accepted.engineering_hash, recipeId=recipe.id,
                architectureId=context.proposal["id"], units="m", upAxis="Y", matrixLayout="column-major",
                durationS=plan[-1][1],
                stages=[dict(id=current[0], startTimeS=previous[1], endTimeS=current[1])
                        for previous, current in zip(plan, plan[1:])],
                joints=[dict(id=j.id, kind=j.kind, axis=list(j.axis), limits=list(j.limits),
                             movingMemberIds=list(j.moving_member_ids)) for j in joints.values()],
                coupling=[c.json_data() for c in group.coupling],
                screwCoupling=dict(jointIds=list(SCREWS), leadM=LEAD,
                                   leftTravelPerRadianM=LEAD/(2*math.pi), rightTravelPerRadianM=-LEAD/(2*math.pi),
                                   inputJointIds=list(INPUTS), inputRatio=INPUT_RATIO, inputOffsetRad=INPUT_PHASE),
                kinematicGraph=_placement_graph(recipe, accepted), keyframes=keyframes,
                interpolation="Linear joint scalars and root translation between keyframes, then placement-graph FK",
                objectComponents=[receipts[identity] for identity in OBJECT_IDS],
                object=dict(instanceId="operation-cup", componentId=OBJECT_IDS[0], diameterM=DIAMETER, heightM=HEIGHT,
                            initialTransform=initial.json_data(), targetTransform=target.json_data(),
                            gripPointLocalM=list(grip_point), anchor=anchor, heldRelativeTransform=held_relative.json_data(),
                            dividerNativeYM=[DIVIDER_BOTTOM, DIVIDER_TOP], dividerGeometryStatus="provisional_pending_figure_confirmation"),
                staticObjects=[dict(instanceId="operation-pin", componentId=OBJECT_IDS[1],
                                    transform=native_pose((lower_anchor[0]*1000, fixture_height*1000, TARGET_Z*1000)).json_data()),
                               dict(instanceId="operation-target", componentId=OBJECT_IDS[2],
                                    transform=native_pose((lower_anchor[0]*1000, 0., TARGET_Z*1000)).json_data())],
                target=dict(positionM=list(target.point()), gripWorldPointM=list(target_anchor), liftAngleRad=goal,
                            carryHeightM=CARRY_Y, carryLiftAngleRad=carry,
                            fixtureHeightM=fixture_height, fixtureStatus="modeled_development_fixture_not_official_goal",
                            pinBaseYM=fixture_height, pinTopYM=pin_top, nestingDepthM=pin_top-target_y,
                            radialClearanceM=(DIAMETER/2-WALL)-PIN_DIAMETER/2,
                            dividerLowerFaceYM=target_y+DIVIDER_BOTTOM,
                            supportCofaceErrorM=abs(target_y+DIVIDER_BOTTOM-pin_top),
                            ruleBasis="SC2 requires partial nesting of an already Placed Pin; this is an explicitly modeled fixture",
                            pinPlacementStatus="assumed_preplaced_on_development_fixture"),
                events=[dict(type="capture", timeS=capture_time, objectState="held"),
                        dict(type="release", timeS=release_time, objectState="placed")],
                validation=dict(engine="realization.build_pose / AssemblyService.validate", graphValid=True,
                                keyframeCount=len(keyframes), sampleCount=len(samples), samples=samples,
                                capturePredicatePassed=captured, releaseTargetMaxMatrixError=placement_error,
                                approachClearanceOverPinTopM=clearance, missing=gaps,
                                assemblyClearanceStatus=handling.get('clearanceStatus','not_qualified'),
                                physicalPerformanceVerified=False, scoringVerified=False,
                                authenticCadAcceptance=False),
                limitations=["Whole-robot clearance is unqualified; known body/shaft intersections prevent a successful physical-operation or complete-robot claim",
                             "Sampled graph closure and joint limits only; no collision/contact, force, friction or wheel traction validation",
                             "Cup divider and ideal opposed-lead screw are provisional development geometry",
                             "Pin is assumed already placed on a development fixture; this does not establish legal goal placement or SC2 scoring",
                             "Robot root travel is prescribed; no independent Cup tilt or physics simulation"])
