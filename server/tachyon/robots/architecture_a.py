"""The bounded four-bar/roller robot from the saved architecture-A requirements.

Only supplied measured source components are instantiated. Dimensions marked as
realization choices are discrete adaptations to the supplied hole grid; the
saved proposal and simulated policy are never rewritten to claim performance.
"""
from __future__ import annotations

import math

from .. import assemblies as A
from ..errors import TachyonError
from .builder import RecipeBuilder
from .source_pack import DISPLAY, native_pose

T = A.RigidTransform
X, Y, Z = (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)


def compile_chassis_and_drive(proposal, pack):
    """Compile the actual two-motor, gear-linked four-wheel platform.

    Returned authoring state is extended with the scoring/acquisition hardware
    by the robot compiler. This platform is never classified as a complete robot.
    """
    intents = {s["id"]: s for s in proposal["subsystems"]}
    if (proposal["alternative"] != "A" or intents["drive"]["mechanismIntent"] != "linked_geared_four_wheel_tank"
            or intents["drive"]["layoutIntent"]["wheelCount"] != 4):
        raise TachyonError("UNSUPPORTED_ROBOT_RECIPE", "This builder realizes the saved four-bar/roller alternative A")
    required = {"channel", "bearing", "shaft_long", "gear84", "motor", "omni", "shaft_insert", "collar", "bolt", "nut"}
    if required - pack.parts.keys():
        raise TachyonError("ROBOT_PARTS_MISSING", "The measured part pack lacks drivetrain or structural components")
    b = RecipeBuilder("override-a-geared-four-bar-v1", "A", pack.builder_parts())
    roles, stages, supports = {}, [], []
    # Source channel 276-6009-001 has a 12.7 mm staggered hole grid, with
    # web centres at native z=-0.1 mm and outer flange z=13.9684 mm.
    web = lambda name, x: pack.port("channel", name, (x, 0., -.1), Y, X)
    top = lambda name, x: pack.port("channel", name, (x, -12.7, 13.9684), Z, X)
    front_world = native_pose((0., 64.8684, 89.))
    root = b.root_part("front-crossmember", "channel", "chassis", front_world)
    for side, sign in (("right", 1), ("left", -1)):
        # All four long members attach through actual web/flange holes.
        # The second crossmember closes the rectangular structure at four mates.
        axes = ((0., 0., sign), (sign, 0., 0.), Y)
        for track, x in (("outer", 127.), ("inner", 88.9)):
            name = f"{side}-{track}-rail"
            parent_port = web(f"cross-{side}-{track}", sign*(x-12.7))
            child_port = top(f"front-{side}-{track}", sign*88.9)
            world = native_pose((sign*x, 50.9, 0.), *axes)
            b.attach_at(name, "channel", "chassis", root, parent_port, child_port, world, angular_tolerance=math.pi)
    rear_world = native_pose((0., 64.8684, -88.8))
    child = web("rear-cross-right", 114.3)
    parent = top("rear-right-outer", -88.9)
    b.attach_at("rear-crossmember", "channel", "chassis", "right-outer-rail", parent, child, rear_world, angular_tolerance=math.pi)
    for side, sign in (("right", 1), ("left", -1)):
        for track, x in (("outer", 127.), ("inner", 88.9)):
            if side == "right" and track == "outer":
                continue
            parent = top(f"rear-{side}-{track}", -sign*88.9)
            child = web(f"rear-cross-{side}-{track}", sign*(x-12.7))
            # Measured world frames can have different roll; the fixed mate
            # records that rotation and AssemblyService checks full closure.
            mate = b.port(f"{side}-{track}-rail", parent).inverse().compose(rear_world.compose(pack.parts["channel"].ports[child].frame))
            b.constraint(f"rear-tie-{side}-{track}", f"{side}-{track}-rail", parent, "rear-crossmember", child, mate=mate)
    # Purchased bearing flats: native X is the shaft axis; the two screw holes
    # lie ±12.7 mm along native Y. The rear mounting face is x=-6.35 mm.
    pack.port("bearing", "mount", (-6.35, 0., 0.), X, Y)
    pack.port("bearing", "axis", (0., 0., 0.), X, Y, kind="bearing")
    pack.port("shaft_long", "axis", (0., 0., 0.), Z, Y, kind="shaft", basis="shaft_station")
    pack.port("gear84", "shaft", (0., 0., 0.), Z, Y, kind="shaft", basis="bore_station")
    pack.port("omni", "shaft", (0., 0., 0.), Y, Z, kind="shaft", basis="purchased_interface")
    pack.port("motor", "mount", (0., 0., 44.2), Z, X)
    pack.port("motor", "output", (12.7, 0., 34.), Z, X, kind="shaft")
    wheelbase = 177.8  # two 84-tooth meshes at 88.9 mm pitch centre distance
    # Axle locations use the actual rail grid; endpoints rotate in the same
    # direction after two external gear meshes. No four-motor direct-drive fallback.
    for side, sign in (("right", 1), ("left", -1)):
        side_outputs, side_stages = [], []
        for station, z in (("rear", -wheelbase/2), ("middle", 0.), ("front", wheelbase/2)):
            rail = f"{side}-outer-rail"
            parent_port = pack.port("channel", f"axle-{side}-{station}", (sign*z, 1.1684, -.1), Y, Z, kind="bearing")
            outer = f"{side}-{station}-outer-bearing"
            bearing_rotation = ((sign, 0., 0.), (0., 0., sign), (0., -1., 0.))
            outer_world = native_pose((sign*(128.1684+6.35), 50.8, z), *bearing_rotation)
            b.attach_at(outer, "bearing", "drive", rail, parent_port, "mount", outer_world, angular_tolerance=math.pi)
            shaft = f"{side}-{station}-shaft"
            shaft_rotation = ((0., 0., -sign), Y, (sign, 0., 0.))
            # The 99.822 mm shaft spans both supports and the wheel hub.
            shaft_centre = 118.65 if station == "middle" else 125.0
            offset = shaft_centre-(128.1684+6.35)
            station_port = pack.port("shaft_long", f"outer-{side}-{station}", (0., 0., -offset), Z, Y, kind="shaft", basis="shaft_station")
            shaft_world = native_pose((sign*shaft_centre, 50.8, z), *shaft_rotation)
            b.attached(shaft, "shaft_long", "drive", outer, "axis", station_port,
                       kind="revolute", axis=(0., 0., 1.), limits=(-math.pi*100, math.pi*100), lower=0., raised=0.)
            # Place a second bearing through the actual inner-rail web.
            inner = f"{side}-{station}-inner-bearing"
            inner_rail = f"{side}-inner-rail"
            inner_port = pack.port("channel", f"inner-axle-{side}-{station}", (sign*z, 0., -.1), Y, Z, kind="bearing")
            inner_rotation = ((-sign, 0., 0.), (0., 0., -sign), (0., -1., 0.))
            inner_world = native_pose((sign*(88.9-6.35), 50.8, z), *inner_rotation)
            b.attach_at(inner, "bearing", "drive", inner_rail, inner_port, "mount", inner_world, angular_tolerance=math.pi)
            # Meshes live between the two rails; actual shafts pass through them.
            gear = f"{side}-{station}-gear"
            gear_world = native_pose((sign*108., 50.8, z), *shaft_rotation)
            if station == "middle":
                gear_world = gear_world.compose(DISPLAY).compose(T.rotation(Z, math.pi/84)).compose(DISPLAY.inverse())
            gear_station = pack.port("shaft_long", f"gear-{side}-{station}", (0., 0., 108.-shaft_centre), Z, Y, kind="shaft", basis="shaft_station")
            b.attach_at(gear, "gear84", "drive", shaft, gear_station, "shaft", gear_world, angular_tolerance=math.pi)
            if station != "middle":
                wheel = f"{side}-{station}-wheel"
                wheel_rotation = ((0., 0., sign), (sign, 0., 0.), Y)
                wheel_world = native_pose((sign*152.6652, 50.8, z), *wheel_rotation)
                wheel_station = pack.port("shaft_long", f"wheel-{side}-{station}", (0., 0., 152.6652-shaft_centre), Z, Y, kind="shaft", basis="shaft_station")
                b.attach_at(wheel, "omni", "drive", shaft, wheel_station, "shaft", wheel_world, angular_tolerance=math.pi)
                side_outputs.append(wheel)
            supports.append({"shaft": shaft, "innerBearing": inner, "outerBearing": outer})
        # Output socket is recessed relative to the two authentic mounting posts.
        # Native motor +X follows the rail and native +Z is its output axis.
        motor = f"{side}-drive-motor"
        motor_rotation = ((0., 0., sign), (0., -1., 0.), (sign, 0., 0.))
        motor_world = native_pose((sign*(88.9-44.2), 50.8, -sign*12.7), *motor_rotation)
        port = pack.port("channel", f"motor-{side}", (-12.7, 0., -.1), Y, X)
        b.attach_at(motor, "motor", "drive", f"{side}-inner-rail", port, "mount", motor_world, angular_tolerance=math.pi)
        stages.append({"side": side, "motor": motor, "wheels": side_outputs,
                       "gears": [f"{side}-{p}-gear" for p in ("rear", "middle", "front")],
                       "shaftSupports": supports[-3:]})
        roles[side] = {"motor": motor, "wheels": side_outputs}
    return b, {"driveSides": roles, "transmissions": stages, "shaftSupports": supports,
               "realizationChoices": {"wheelbaseM": wheelbase/1000, "gearTeeth": 84,
                    "gearPitchDiameterM": .0889, "wheelDiameterM": .1016,
                    "drivetrainMotors": 2,
                    "sizingNote": "Hole-grid adaptation of the saved sizing intent; loaded speed/traction remain unverified"}}


def add_four_bar(b, pack):
    """Paired real-hole parallelograms, with an explicitly closed tool bridge.

    The selected source angle's actual pivot span is 292.1 mm. Choosing source
    upright pivots at 254/330.2 mm and -0.65/+0.40 rad endpoint angles produces
    approximately 292 mm travel, consistent with the strategy-derived intent.
    The source solids are neither resized nor cut to fit a desired link length.
    """
    if {"angle", "short_channel"} - pack.parts.keys():
        raise TachyonError("ROBOT_PARTS_MISSING", "Four-bar needs measured angle links and tool-carrier channels")
    for key in ("angle", "short_channel"):
        b.parts[key] = pack.parts[key].part()
    # A real bearing flat, washer and 3.175 mm spacer separate each moving
    # link from its ground/carrier plate. This leaves the source flange clear.
    low, high, spacer = -.65, .40, .00635 + .000762 + .003175
    controls, carriers, ground_ids, link_ids = [], [], [], []
    source_back = pack.port("angle", "link-back", (-146.05, 0., 0.), (0., 0., -1.), X, kind="revolute")
    source_front = pack.port("angle", "link-front", (146.05, 0., 0.), (0., 0., -1.), X, kind="revolute")
    for side, sign in (("right", 1), ("left", -1)):
        ground = f"{side}-lift-upright"
        ground_world = native_pose((sign*76.2, 203.2, -107.95), Y, (0., 0., sign), (sign, 0., 0.))
        rail = f"{side}-inner-rail"
        rail_port = pack.port("channel", f"upright-{side}", (-sign*101.6, 0., -.1), Y, Z)
        foot = pack.port("angle", f"foot-{side}", (-152.4, sign*6.35, 1.1684), Z, X)
        # Two source hole pairs accept the real long through-bolt/standoff
        # mounting group. Its axial separation is explicit, not a floating mesh.
        b.attach_at(ground, "angle", "scorer", rail, rail_port, foot, ground_world,
                    axial_stack_m=-.0115316, angular_tolerance=math.pi)
        second_rail = pack.port("channel", f"upright-second-{side}", (-sign*114.3, 0., -.1), Y, Z)
        second_foot = pack.port("angle", f"foot-second-{side}", (-152.4, -sign*6.35, 1.1684), Z, X)
        mate = b.port(rail, second_rail).inverse().compose(ground_world.compose(pack.parts["angle"].ports[second_foot].frame))
        b.constraint(f"{side}-upright-second-bolt", rail, second_rail, ground, second_foot, mate=mate)
        branch = []
        for level, source_x in (("lower", 50.8), ("upper", 127.)):
            pivot = pack.port("angle", f"ground-{side}-{level}", (source_x, sign*6.35, 1.1684), Z, Y, kind="revolute")
            link = f"{side}-{level}-four-bar-link"
            joint = f"{side}-{level}-ground-pivot"
            roll = T.rotation(Z, math.pi if sign < 0 else 0.)
            b.attached(link, "angle", "scorer", ground, pivot, source_back,
                mate=T.translation(0., 0., spacer).compose(roll), kind="revolute",
                axis=(0., 0., -sign), limits=(-.75, .5), lower=low, raised=high, joint_id=joint)
            controls.append((joint, 1.)); branch.append(link); link_ids.append(link)
        carrier = f"{side}-tool-carrier"
        lower_port = pack.port("short_channel", f"carrier-{side}-lower", (-38.1, 1.1684, sign*6.35), Y, X, kind="revolute")
        upper_port = pack.port("short_channel", f"carrier-{side}-upper", (38.1, 1.1684, sign*6.35), Y, X, kind="revolute")
        mate = T.translation(0., 0., -spacer).compose(T.rotation(Z, -sign*math.pi/2))
        joint = f"{side}-lower-carrier-pivot"
        b.attached(carrier, "short_channel", "scorer", branch[0], source_front, lower_port,
            mate=mate, kind="revolute", axis=(0., 0., -sign), limits=(-.5, .75),
            lower=-low, raised=-high, joint_id=joint)
        controls.append((joint, -1.))
        closing = f"{side}-upper-carrier-pivot"
        b.constraint(closing, branch[1], source_front, carrier, upper_port, mate=mate,
            kind="revolute", axis=(0., 0., -sign), limits=(-.5, .75), lower=-low, raised=-high)
        controls.append((closing, -1.)); carriers.append(carrier); ground_ids.append(ground)
    # A real source channel spans the carriers. One tree mate places it; the
    # second is an independently checked loop-closure constraint.
    bridge = "tool-crossmember"
    right_face = pack.port("short_channel", "bridge-mount-right", (0., -6.35, -12.7), (0., 0., -1.), X)
    right_hole = pack.port("short_channel", "bridge-right-hole", (69.85, 0., 0.), Y, (0., 0., -1.))
    b.attached(bridge, "short_channel", "scorer", carriers[0], right_face, right_hole)
    left_face = pack.port("short_channel", "bridge-mount-left", (0., -6.35, 12.7), Z, X)
    left_hole = pack.port("short_channel", "bridge-left-hole", (-69.85, 0., 0.), Y, (0., 0., -1.))
    # Rolling the left port about its axis maintains the physical source-face
    # orientation. The full matrix is checked by the existing graph service.
    mate = b.port(carriers[1], left_face).inverse().compose(b.port(bridge, left_hole))
    b.constraint("tool-crossmember-left-mount", carriers[1], left_face, bridge, left_hole, mate=mate)
    return {"grounds": ground_ids, "links": link_ids, "carriers": carriers,
            "bridge": bridge, "controls": controls, "lowerAngleRad": low, "raisedAngleRad": high,
            "sourcePivotSpanM": .2921, "basePivotHeightM": .254,
            "sourceSpacingM": .0762,
            "realizationNote": "Source hole-grid linkage; task performance, swept clearance and load capacity unverified"}


def add_purchased_gripper(b, pack, four_bar):
    """Mount the real, internally detailed Claw Kit v2 as a purchased tool.

    The whole Clawbot is never placed. The selected tool has its own retained
    source hierarchy and integrated motor/gears; internal jaw animation is not
    asserted by importing its factory pose.
    """
    if "gripper" not in pack.parts:
        raise TachyonError("ROBOT_PARTS_MISSING", "A qualified source Claw Kit v2 tool is required")
    b.parts["gripper"] = pack.parts["gripper"].part()
    bridge = four_bar["bridge"]
    flange = pack.port("short_channel", "tool-platform-top", (0., -6.35, -12.7), (0., 0., -1.), X)
    underside = pack.port("short_channel", "tool-platform-under", (0., 0., 6.35), Y, X)
    platform = "gripper-mount-platform"
    b.attached(platform, "short_channel", "scorer", bridge, flange, underside)
    top = pack.port("short_channel", "gripper-mount", (0., 1.1684, 6.35), Y, X)
    mount = pack.port("gripper", "rear-plate-mount", (0., -15.2625, -44.45), Y, X, basis="purchased_interface")
    identity = "pin-retaining-gripper"
    b.attached(identity, "gripper", "scorer", platform, top, mount)
    # The source jaw working region is an annotation, not certified Pin fit.
    point = DISPLAY.point((0., 0., .065))
    lower = b.nominal_world[identity][1].point(point)
    low, high = four_bar["lowerAngleRad"], four_bar["raisedAngleRad"]
    length = four_bar["sourcePivotSpanM"]
    raised = (lower[0], lower[1]+length*(math.sin(high)-math.sin(low)), lower[2]+length*(math.cos(high)-math.cos(low)))
    reaches = {key: {"actionId": "place_alliance", "anchorId": "pin-grip-working-reference", "worldPointM": list(value),
                     "evidence": "Source jaw working datum transformed through the generated four-bar; physical Pin contact/scoring support unverified"}
               for key, value in (("lower", lower), ("raised", raised))}
    return {"instanceId": identity, "platformId": platform,
            "anchor": {"id": "pin-grip-working-reference", "instanceId": identity, "localPointM": list(point)},
            "reach": reaches,
            "interfaceStatus": "purchased source tool; internal pose retained, Pin/Cup fit and physical operation unverified"}


def compile_architecture_a(proposal, pack):
    """Compile the implemented A subsystems into the production recipe format.

    This is a partial robot recipe until the explicit hardware/task gaps pass.
    No existing Clawbot placement tree is copied, and no source geometry is
    created, changed, approved or loaded by this metadata compiler.
    """
    from .electronics import add_electronics
    from .hardware import add_drive_hardware, add_structural_fasteners
    from .scoring_drive import add_scoring_drive
    from .handling import add_pin_intake

    b,drive=compile_chassis_and_drive(proposal,pack)
    four_bar=add_four_bar(b,pack)
    gripper=add_purchased_gripper(b,pack,four_bar)
    electronics=add_electronics(b,pack)
    drive_hardware=add_drive_hardware(b,pack,drive)
    lift_hardware=add_scoring_drive(b,pack,four_bar)
    intake=add_pin_intake(b,pack)
    structure=add_structural_fasteners(b,pack,four_bar,electronics)
    # The source omni roller envelope is larger than the nominal 4-inch tyre.
    # Move the complete graph to its measured floor; never scale source meshes.
    wheel_bottom=pack.parts["omni"].measurements["boundsMm"][0][2]
    floor_shift=max(0.,(-wheel_bottom-50.8)/1000)
    if floor_shift:
        shift=T.translation(0.,floor_shift,0.)
        b.root_world=shift.compose(b.root_world)
        b.nominal_world={key:(part,shift.compose(world)) for key,(part,world) in b.nominal_world.items()}
        for reach in gripper["reach"].values():
            reach["worldPointM"][1]+=floor_shift
    # Bind only actual populated mechanisms. Unimplemented Cup/transfer roles
    # remain explicit gaps; a Pin mechanism never masquerades as a Cup handler.
    members={r: [n["id"] for n in b.instances if n["subsystemId"]==r] for r in {n["subsystemId"] for n in b.instances}}
    seen=set()
    for intent in proposal["bindingIntent"]["actions"]:
        action=intent.get("action",intent.get("sourceValue"))
        if not isinstance(action,str) or action in seen:
            continue
        role=("scorer" if action in {"place_alliance","place_yellow"} else
              "pin_intake" if action in {"acquire_alliance","acquire_yellow"} else
              "drive" if action.startswith("move_to_") or action=="park_and_wait" else None)
        if role not in members or role not in intent["subsystemIDs"]:
            continue
        joints=[r["id"] for r in b.relationships if r["kind"]!="fixed" and r["childInstanceId"] in members[role]]
        b.bind(action,role,members[role],joints,[gripper["anchor"]] if role=="scorer" else ())
        seen.add(action)
    by_component={p.component_id:p for p in pack.parts.values()}
    # The qualification service evaluates completeness from declarations tied
    # to current receipts; this BOM cannot assert a caller-supplied success flag.
    robot=dict(bom=[dict(instanceId=n["id"],componentId=n["componentId"],
        catalogFingerprint=by_component[n["componentId"]].catalog_fingerprint,purpose=b.purposes[n["id"]],
        evidence="Generated measured-source part placement; supporting hardware and task qualifications are evaluated separately") for n in b.instances])
    return b,dict(reach=gripper["reach"],gripper=gripper,fourBar=four_bar,drive=drive,
        electronics=electronics,driveHardware=drive_hardware,liftHardware=lift_hardware,
        intake=intake,structure=structure,robot=robot,floorShiftM=floor_shift,
        completeRobot=False,physicalPerformanceVerified=False,
        missing=[dict(role=r,code="REQUIRED_ROLE_UNREALIZED") for r in ("pin_transfer","cup_cradle","stack_interface")],
        limitations=["This generated recipe is partial, not a complete competition robot",
            "Actual CAD rendering, task interfaces, source tool mounting and swept clearances require verification",
            "Transmission and mount qualification declarations are not complete; BOM presence alone is insufficient"])
