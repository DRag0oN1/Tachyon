"""Original Tachyon development hardware, in millimetres and native part frames.

These are newly authored conceptual mechanical BReps, not manufacturer models,
VEX components, replicas, or evidence of physical/competition performance.
Only engineering interface coordinates from Tachyon's recipe code are reused.
No CAD inputs, private inventories, network resources, or external projects are
read. There is no license grant in this file. The seeder owns self-authorship
records, permitted local use, catalog registration, and any publication decision.

``create_parts()`` returns independent named assemblies and writes nothing.
``measure_cached()`` optionally caches measurements of an authored STEP in a
caller-selected private directory; it writes no CAD, catalogs or rights records.
Mounting holes, shaft/bore axes and seating faces are actual geometry, so the
normal native metrology/SourcePack path can measure them. Thread helices,
electrical function, rubber compliance and mechanical actuation are not verified.
"""
from __future__ import annotations

from functools import lru_cache
import math

import cadquery as cq


PITCH_MM = 12.7
SHEET_MM = 1.1684
TRACTION_DATUM_MM = (29.3129364268, 56.9311020238, 68.3968973123)
PROVENANCE = {
    "originKind": "tachyon_authored",
    "developmentPart": True,
    "authorship": "Original Tachyon development generator; recipe interface facts only",
    "identity": "Project-authored, non-VEX conceptual mechanical hardware",
    "units": "mm",
    "usage": "Self-authored private-local usage is recorded by the seeder",
    "publication": "User-controlled; no publication or license grant implied",
    "physicalPerformanceVerified": False,
}
METAL = cq.Color(0.64, 0.70, 0.75)
STEEL = cq.Color(0.32, 0.38, 0.43)
POLYMER = cq.Color(0.12, 0.22, 0.28)
RUBBER = cq.Color(0.19, 0.20, 0.22)
COPPER = cq.Color(0.69, 0.36, 0.15)
ACCENT = cq.Color(0.15, 0.48, 0.58)


def _assembly(alias, **facts):
    return cq.Assembly(name="tachyon-development-" + alias.replace("_", "-"),
                       metadata={**PROVENANCE, "alias": alias, **facts})


def _add(assembly, shape, name, color=METAL, *, location=None):
    if isinstance(shape, cq.Workplane):
        shape = shape.val()
    assembly.add(shape, name="authored-" + name, color=color,
                 loc=location or cq.Location(), metadata=dict(PROVENANCE))


def _box(x, y, z, center=(0., 0., 0.)):
    return cq.Workplane("XY").box(x, y, z).val().translate(center)


def _cylinder(radius, length, start, axis=(0., 0., 1.)):
    return cq.Solid.makeCylinder(radius, length, cq.Vector(*start), cq.Vector(*axis))


def _cut(shape, cutters):
    if not cutters:
        return shape
    return shape.cut(cq.Compound.makeCompound(cutters)).clean()


def _orient_z(shape, axis):
    if axis == (0., 1., 0.):
        return shape.rotate((0, 0, 0), (1, 0, 0), -90)
    if axis == (1., 0., 0.):
        return shape.rotate((0, 0, 0), (0, 1, 0), 90)
    if axis != (0., 0., 1.):
        raise ValueError("An authored principal-axis orientation is required")
    return shape


def _folded_channel(length, half_width, depth, *, middle=-.1, center_row_even=True):
    # A single folded profile avoids overlapping separate sheet solids.
    t, w = SHEET_MM, half_width
    profile = [(t, -w), (t, w), (-depth, w), (-depth, w-t),
               (0., w-t), (0., -w+t), (-depth, -w+t), (-depth, -w)]
    stock = cq.Workplane("YZ", origin=(-length/2, 0, 0)).polyline(profile).close().extrude(length).val()
    cutters = []
    n = int((length/2 - 5.) / PITCH_MM)
    # Alternating three-row round perforations are independently authored;
    # only their centres/planes implement the recipe's attachment interfaces.
    for index in range(-2*n-1, 2*n+2):
        x = index * PITCH_MM/2
        if abs(x) > length/2-5.:
            continue
        center_row = (index % 2 == 0) == center_row_even
        zs = (middle,) if center_row else (middle-6.35, middle+6.35)
        for z in zs:
            cutters.append(_cylinder(2.2, t+2., (x, -1., z), (0., 1., 0.)))
        ys = ((-12.7,) if index % 2 == 0 else (-6.35, -19.05)) if depth > 20 else (-6.35,)
        for y in ys:
            cutters.append(_cylinder(2.2, 2*w+2., (x, y, -w-1.)))
    return _cut(stock, cutters)


def _folded_link():
    # Wide web and two narrow return flanges: an original folded link section.
    t, half_width, length = SHEET_MM, 12.7, 317.5
    profile = [(-half_width, t), (half_width, t), (half_width, -12.7016),
               (half_width-t, -12.7016), (half_width-t, 0.),
               (-half_width+t, 0.), (-half_width+t, -12.7016), (-half_width, -12.7016)]
    stock = cq.Workplane("YZ", origin=(-length/2, 0, 0)).polyline(profile).close().extrude(length).val()
    cutters = []
    for index in range(-24, 25):
        x = index*6.35
        for y in ((-6.35, 6.35) if index % 2 == 0 else (0.,)):
            cutters.append(_cylinder(2.2, t+2., (x, y, -1.)))
        if index % 2 == 0:
            cutters.append(_cylinder(2.2, 27.4, (x, -13.7, -6.3516), (0., 1., 0.)))
    return _cut(stock, cutters)


def _shaft(length):
    shaft = cq.Workplane("XY").box(3.175, 3.175, length).edges("|Z").fillet(.25)
    return shaft.faces(">Z").edges().chamfer(.15).faces("<Z").edges().chamfer(.15).val()


@lru_cache(maxsize=8)
def _spur_gear(teeth, module=25.4/24, width=12.7):
    """20-degree involute spur gear with sampled B-spline tooth flanks.

    Both flanks follow the involute equation; tip/root lands are circular arcs.
    The radial root transition is a development approximation, not a hobbed
    undercut/fillet or a manufacturing/contact-stress qualification.
    """
    phi = math.radians(20)
    pitch = teeth*module/2
    base, tip = pitch*math.cos(phi), pitch+module
    root = pitch-1.25*module
    start = max(base, root)
    pitch_involute = math.tan(phi)-phi

    def half_angle(radius):
        angle = math.acos(min(1., base/radius))
        return math.pi/(2*teeth)+pitch_involute-(math.tan(angle)-angle)

    def point(radius, angle):
        return cq.Vector(radius*math.cos(angle), radius*math.sin(angle), 0.)

    edges = []
    half_root, half_tip = half_angle(start), half_angle(tip)
    for index in range(teeth):
        center = 2*math.pi*index/teeth
        if root < start:
            edges.append(cq.Edge.makeLine(point(root, center-half_root), point(start, center-half_root)))
        radii = [start+(tip-start)*i/12 for i in range(13)]
        edges.append(cq.Edge.makeSpline([point(r, center-half_angle(r)) for r in radii]))
        edges.append(cq.Edge.makeThreePointArc(point(tip, center-half_tip), point(tip, center), point(tip, center+half_tip)))
        edges.append(cq.Edge.makeSpline([point(r, center+half_angle(r)) for r in reversed(radii)]))
        if root < start:
            edges.append(cq.Edge.makeLine(point(start, center+half_root), point(root, center+half_root)))
        end, following = center+half_root, center+2*math.pi/teeth-half_root
        edges.append(cq.Edge.makeThreePointArc(point(root, end), point(root, (end+following)/2), point(root, following)))
    wire = cq.Wire.assembleEdges(edges)
    gear = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, width)).translate((0, 0, -width/2))
    cutters = [_box(6.4, 6.4, width+2.)]
    if teeth >= 60:
        # Union the hub, thin web and toothed rim with positive overlap. This
        # avoids coincident annular pocket tools splitting the gear into bodies.
        rim = gear.cut(_cylinder(32., width+2., (0, 0, -width/2-1.)))
        web = _cylinder(32.5, 4.572, (0, 0, -2.286))
        hub = _cylinder(10., width, (0, 0, -width/2))
        gear = rim.fuse(web, hub).clean()
        for radius in (12.7, 25.4, 38.1):
            for theta in (0., math.pi/2, math.pi, 3*math.pi/2):
                cutters.append(_cylinder(2.2, width+2., (radius*math.cos(theta), radius*math.sin(theta), -width/2-1.)))
        for theta in (math.pi/4, 3*math.pi/4, 5*math.pi/4, 7*math.pi/4):
            cutters.append(_cylinder(4.5, width+2., (19.05*math.cos(theta), 19.05*math.sin(theta), -width/2-1.)))
    return _cut(gear, cutters)


def _bearing():
    body = cq.Workplane("YZ", origin=(-6.35, 0, 0)).rect(35.56, 10.16).extrude(6.35).edges("|X").fillet(2.).val()
    cuts = [_cylinder(2.35 if y == 0 else 2.2, 8.35, (-7.35, y, 0), (1., 0., 0.)) for y in (-12.7, 0., 12.7)]
    # Two shallow oil/weight pockets distinguish the machined bearing block.
    cuts += [_box(1.4, 4., 5., (-.5, y, 0)) for y in (-6.35, 6.35)]
    return _cut(body, cuts)


def _insert():
    flange = _cylinder(5.0165, 1.27, (0, 0, 0), (0., 1., 0.))
    boss = _box(6.34, 3.81, 6.34, (0, 3.175, 0))
    return _cut(flange.fuse(boss), [_box(3.4, 7.08, 3.4, (0, 2.54, 0))])


def _sleeve(length, radius=4.7625, *, axis=(0., 1., 0.), hexagon=False):
    if hexagon:
        shape = cq.Workplane("XY").polygon(6, 2*radius).extrude(length).translate((0, 0, -length/2)).val()
        shape = _orient_z(shape, axis)
    else:
        shape = _cylinder(radius, length, tuple(-v*length/2 for v in axis), axis)
    return _cut(shape, [_cylinder(2.15, length+2., tuple(-v*(length/2+1.) for v in axis), axis)])


def _bolt(length):
    head = cq.Workplane("XY").circle(3.8).extrude(2.2).faces(">Z").edges().chamfer(.35).val()
    shank = cq.Workplane("XY").circle(2.).extrude(length).translate((0, 0, -length)).faces("<Z").edges().chamfer(.3).val()
    socket = cq.Workplane("XY").polygon(6, 2.8).extrude(1.8).translate((0, 0, .7)).val()
    return _orient_z(_cut(head.fuse(shank), [socket]), (0., 1., 0.))


def _collar():
    unit = _assembly("collar", boreAxis="Z", threadGeometry="Nominal drilled set-screw bores; helices omitted")
    body = _cylinder(4.75, 12.4, (0, 0, -6.2))
    body = _cut(body, [_cylinder(2.35, 14.4, (0, 0, -7.2))] +
                [_cylinder(1.25, 5., (1.5, 0, z), (1., 0., 0.)) for z in (-3., 3.)])
    _add(unit, body, "split-drive-collar", STEEL)
    for index, z in enumerate((-3., 3.)):
        screw = _cylinder(1.15, 2.6, (2.1, 0, z), (1., 0., 0.))
        _add(unit, screw, f"radial-clamp-screw-{index}", METAL)
    return unit


def _wheel_disc(radius, thickness, *, bore=6.4, holes=6):
    disc = _cylinder(radius, thickness, (0, 0, -thickness/2))
    cuts = [_box(bore, bore, thickness+2.)]
    for index in range(holes):
        theta = 2*math.pi*index/holes
        cuts.append(_cylinder(radius*.14, thickness+2.,
                              (radius*.62*math.cos(theta), radius*.62*math.sin(theta), -thickness/2-1.)))
    return _cut(disc, cuts)


def _traction():
    unit = _assembly("traction", axis="Z", interfaceDatumMm=list(TRACTION_DATUM_MM))
    center = cq.Location(cq.Vector(*TRACTION_DATUM_MM))
    hub = _cut(_cylinder(10., 16., (0, 0, -8.)), [_box(6.4, 6.4, 18.)])
    _add(unit, hub, "keyed-hub", STEEL, location=center)
    disc = _wheel_disc(38., 2.4)
    for index, z in enumerate((-7., 7.)):
        _add(unit, disc.translate((0, 0, z)), f"six-window-rim-{index}", ACCENT, location=center)
    tyre = _cylinder(50.8, 22., (0, 0, -11.)).cut(_cylinder(36., 24., (0, 0, -12.)))
    grooves = [_box(3.4, 2.2, 24., (50.2, 0, 0)).rotate((0, 0, 0), (0, 0, 1), i*15) for i in range(24)]
    _add(unit, _cut(tyre, grooves), "grooved-compliant-development-tyre", RUBBER, location=center)
    for index, (z, angle) in enumerate(((-7., 90), (7., -90))):
        insert = _insert().rotate((0, 0, 0), (1, 0, 0), angle).translate((0, 0, z))
        _add(unit, insert, f"keyed-drive-insert-{index}", POLYMER, location=center)
    return unit


def _omni():
    unit = _assembly("omni", axis="Y", interfaceDatumMm=[0., 0., 0.],
                     rollerCount=20, rollerMotion="Passive tangent axles; motion unverified")
    hub = _cylinder(11., 14., (0, -7., 0), (0., 1., 0.))
    hub = _cut(hub, [_box(6.4, 16., 6.4)])
    _add(unit, hub, "axial-keyed-hub", STEEL)
    disc = _orient_z(_wheel_disc(34., 2., holes=5), (0., 1., 0.))
    # A turned barrel with a real axle bore; local passive axis is Z.
    roller = (cq.Workplane("XZ").moveTo(0, -7).lineTo(4.6, -7)
              .threePointArc((6.6, -4), (7., 0)).threePointArc((6.6, 4), (4.6, 7))
              .lineTo(0, 7).close().revolve(360, (0, -7), (0, 7)).val())
    roller = _cut(roller, [_cylinder(1.15, 16., (0, 0, -8.))])
    fork = _cut(_box(17., 4., 19., (36.5, 0, 0)), [_box(13., 6., 15., (40., 0, 0)),
                _cylinder(1.15, 21., (43.3, 0, -10.5))])
    for row, y in enumerate((-6.35, 6.35)):
        _add(unit, disc.translate((0, y, 0)), f"windowed-carrier-{row}", ACCENT)
        for index in range(10):
            angle = index*36 + row*18
            # Passive roller Z goes to wheel tangent Z, followed by wheel Y rotation.
            barrel = roller.translate((43.3, y, 0)).rotate((0, 0, 0), (0, 1, 0), angle)
            axle = _cylinder(1., 19., (43.3, y, -9.5)).rotate((0, 0, 0), (0, 1, 0), angle)
            holder = fork.translate((0, y, 0)).rotate((0, 0, 0), (0, 1, 0), angle)
            _add(unit, barrel, f"passive-barrel-{row}-{index}", RUBBER)
            _add(unit, axle, f"roller-axle-{row}-{index}", STEEL)
            _add(unit, holder, f"roller-fork-{row}-{index}", METAL)
    for index, angle in enumerate((0, 180)):
        _add(unit, _insert().rotate((0, 0, 0), (0, 0, 1), angle).translate((0, -6.92 if index == 0 else 6.92, 0)),
             f"shaft-insert-{index}", POLYMER)
    return unit


def _motor():
    unit = _assembly("motor", outputDatumMm=[12.7, 0., 34.], outputAxis="Z",
                     mountingDatumMm=[[0., 0., 44.2], [-12.7, 0., 44.2]],
                     housingEnvelopeMm=[[-25., -12.5, -27.4], [25., 12.5, 16.]])
    # Withdraw the broad housing from the channel-flange region. Only real
    # mounting bosses and the narrow output neck extend beyond the z=16 lid.
    case = cq.Workplane("XY").box(50., 25., 40.4).edges("|Z").fillet(3.).val().translate((0, 0, -7.2))
    case = _cut(case, [_box(45., 20., 39., (0, 0, -4.)),
                       _box(16., 9., 6., (0, 0, -26.4))])
    _add(unit, case, "vented-gear-motor-case", ACCENT)
    lid = _box(50., 25., 3., (0, 0, 14.5))
    bosses = [_cylinder(4.5, 28.2, (x, 0, 16.)) for x in (0., -12.7)]
    lid = lid.fuse(*bosses).clean()
    cuts = [_cylinder(3.55, 5., (12.7, 0, 12.))]
    cuts += [_cylinder(2.1, 31.2, (x, 0, 14.)) for x in (0., -12.7)]
    _add(unit, _cut(lid, cuts), "dual-post-gearbox-cover", METAL)
    stator = _cylinder(10., 28., (0, 0, -22.)).cut(_cylinder(7.1, 30., (0, 0, -23.)))
    _add(unit, stator, "annular-winding", COPPER)
    _add(unit, _cylinder(6.5, 24., (0, 0, -20.)), "motor-rotor", STEEL)
    _add(unit, _cylinder(1.5, 35., (0, 0, -23.)), "rotor-shaft", STEEL)
    for index, x in enumerate((0., 12.7)):
        gear = _spur_gear(12, width=4.).rotate((0, 0, 0), (0, 0, 1), 15. if index else 0.).translate((x, 0, 10.))
        _add(unit, gear, f"original-reduction-gear-{index}", POLYMER)
    neck = _cylinder(4.2, 18., (12.7, 0, 16.))
    spindle = _cylinder(3.4, 4., (12.7, 0, 12.))
    # The annular face at z=34 has >30 mm² area after the 3.3 mm square
    # socket is cut, so normal native metrology retains its opening centre.
    socket = _cut(neck.fuse(spindle), [_box(3.3, 3.3, 24., (12.7, 0, 24.))])
    _add(unit, socket, "keyed-output-socket", STEEL)
    connector = _cut(_box(16., 9., 4., (0, 0, -25.4)), [_box(12., 6., 3., (0, 0, -26.4))])
    _add(unit, connector, "recessed-connector", POLYMER)
    return unit


def _controller():
    bottom, height = -15.12608151, 30.
    unit = _assembly("brain", identity="Project-authored generic controller; no branded electronics")
    outer = cq.Workplane("XY").box(134., height, 92.).edges("|Y").fillet(5.).val().translate((0, bottom+height/2, 0))
    case = _cut(outer, [_box(129., height, 87., (0, bottom+height/2+3., 0))])
    holes = [_cylinder(2.2, 6., (x, bottom-1., z), (0., 1., 0.)) for x in (-38.1, 38.1) for z in (-19.05, 19.05)]
    _add(unit, _cut(case, holes), "four-mount-controller-chassis", POLYMER)
    board = _box(115., 1.6, 73., (0, bottom+7., 0))
    board = _cut(board, [_cylinder(2.2, 4., (x, bottom+5., z), (0., 1., 0.)) for x in (-38.1, 38.1) for z in (-19.05, 19.05)])
    _add(unit, board, "controller-pcb", ACCENT)
    lid = _cut(_box(128., 2.2, 86., (0, bottom+height-1.1, 0)), [_box(65., 4.2, 39., (0, bottom+height-1.1, 0))])
    _add(unit, lid, "display-bezel", METAL)
    _add(unit, _box(64., 1.2, 38., (0, bottom+height-1.2, 0)), "display-module", cq.Color(.08, .16, .19))
    for index in range(8):
        x = -49.+14.*index
        jack = _cut(_box(10., 9., 12., (x, bottom+14., 35.)), [_box(7., 5., 9., (x, bottom+14., 38.))])
        _add(unit, jack, f"open-interface-jack-{index}", POLYMER)
    return unit


def _battery():
    unit = _assembly("battery", seatingPlaneMm=-7.75, identity="Project-authored generic four-cell battery enclosure")
    case = cq.Workplane("XY").box(156., 27.75, 46.).edges("|Y").fillet(4.).val().translate((0, 6.125, 0))
    case = _cut(case, [_box(151., 26., 41., (0, 8.75, 0))])
    _add(unit, case, "power-enclosure-base", POLYMER)
    _add(unit, _box(150., 1.8, 40., (0, 19.1, 0)), "removable-power-cover", ACCENT)
    for row, z in enumerate((-9., 9.)):
        for column, x in enumerate((-65., 2.)):
            _add(unit, _cylinder(8.3, 63., (x, 5., z), (1., 0., 0.)), f"development-cell-{row}-{column}", METAL)
    connector = _cut(_box(7., 12., 16., (79., 7., 0)), [_box(6., 6., 10., (81., 7., 0))])
    _add(unit, connector, "polarized-power-receptacle", POLYMER)
    return unit


def _battery_clip():
    foot = _box(54., 3., 14., (0, -7.5, 0))
    ledge = _box(38., 6., 10., (0, -3., 0))
    body = foot.fuse(ledge, _box(3., 19., 14., (-25.5, .5, 0)), _box(3., 19., 14., (25.5, .5, 0)))
    return _cut(body, [_cylinder(2.2, 4., (x, -10., 0), (0., 1., 0.)) for x in (-6.35, 6.35)])


def _gripper():
    unit = _assembly("gripper", mountDatumMm=[0., -15.2625, -44.45], mountAxis="Y",
                     mechanism="Fabricated parallel jaws, guide rods and counter-travel rack concept",
                     jawGapMm=40., motion="Authored static pose; contact and actuation unverified")
    back = _box(90., 4., 66., (0, -13.2625, -24.))
    back = _cut(back, [_cylinder(2.2, 6., (x, -16.2625, -44.45), (0., 1., 0.)) for x in (-19.05, 0., 19.05)])
    _add(unit, back, "fabricated-mounting-plate", METAL)
    for z in (10., 28.):
        _add(unit, _cylinder(2.5, 82., (-41., 2., z), (1., 0., 0.)), f"cross-slide-guide-{int(z)}", STEEL)
    for side, sign in (("left", -1), ("right", 1)):
        carriage = _box(13., 16., 29., (sign*27., 2., 19.))
        carriage = _cut(carriage, [_cylinder(2.6, 15., (sign*27.-7.5, 2., z), (1., 0., 0.)) for z in (10., 28.)])
        _add(unit, carriage, side+"-bored-slide-carriage", POLYMER)
        jaw = _box(6., 14., 65., (sign*25., 2., 57.5))
        jaw = _cut(jaw, [_cylinder(1.7, 8., (sign*25.-4., 2., z), (1., 0., 0.)) for z in (37., 78.)])
        _add(unit, jaw, side+"-drilled-jaw", METAL)
        _add(unit, _box(2., 13., 40., (sign*21., 2., 67.)), side+"-replaceable-jaw-pad", RUBBER)
    # Original rack teeth, not an imported claw/tool. Both rack solids expose
    # a mechanical drive concept without claiming an animated working gripper.
    for row, z in enumerate((6.65, 21.35)):
        bar = _box(61., 5., 3., (0, 2., z))
        teeth = [_box(1.7, 5., 1.3, (-27.+i*math.pi*(25.4/24), 2., z+(2. if row == 0 else -2.))) for i in range(17)]
        _add(unit, bar.fuse(*teeth).clean(), f"development-rack-{row}", STEEL)
    _add(unit, _orient_z(_spur_gear(12, width=5.), (0., 1., 0.)).translate((0, 2., 14.)), "rack-drive-pinion", POLYMER)
    motor = _box(23., 18., 25., (0, -2., -12.))
    motor = _cut(motor, [_cylinder(1.6, 20., (x, -12., -12.), (0., 1., 0.)) for x in (-7., 7.)])
    _add(unit, motor, "generic-jaw-actuator-case", ACCENT)
    _add(unit, _cylinder(1.5, 24., (0, -10., 14.), (0., 1., 0.)), "jaw-drive-spindle", STEEL)
    return unit


def create_parts() -> dict[str, cq.Assembly]:
    """Build every current architecture/hardware alias without file or network I/O.

    Aliases identify development interfaces, never supplier SKUs. The caller
    must retain this provenance and classify them as project-authored conceptual
    hardware, separately from manufacturer CAD and complete-robot qualification.
    """
    parts = {}

    def single(alias, shape, color=METAL, **facts):
        result = _assembly(alias, **facts)
        _add(result, shape, alias.replace("_", "-"), color)
        parts[alias] = result

    single("channel", _folded_channel(254., 13.9684, 24.2316), gridPitchMm=PITCH_MM)
    single("short_channel", _folded_channel(190.5, 12.7, 12.7, middle=0., center_row_even=False), gridPitchMm=PITCH_MM)
    single("angle", _folded_link(), gridPitchMm=PITCH_MM)
    single("bearing", _bearing(), POLYMER, boreAxis="X")
    for alias, length in (("shaft_long", 99.822), ("shaft_medium", 74.422), ("shaft_short", 49.022)):
        single(alias, _shaft(length), STEEL, shaftAxis="Z", shaftLengthMm=length)
    for alias, teeth in (("gear84", 84), ("gear12", 12)):
        single(alias, _spur_gear(teeth), POLYMER, teeth=teeth, moduleMm=25.4/24,
               pressureAngleDeg=20., toothProfile="Sampled involute B-spline flanks; circular root/tip lands")
    for alias, length in (("bolt_short", 9.525), ("bolt_mid", 12.7), ("bolt_long", 38.1), ("bolt25", 25.4), ("bolt", 38.1)):
        single(alias, _bolt(length), STEEL, shankAxis="-Y", shankLengthMm=length,
               threadGeometry="Nominal unthreaded shank; thread helix not represented")
    single("nut", _sleeve(3.0988, radius=4.92, hexagon=True), STEEL)
    single("washer", _sleeve(.762, radius=4., axis=(0., 0., 1.)), STEEL)
    single("spacer", _sleeve(3.175), METAL)
    single("brace", _sleeve(3.175), METAL)
    single("standoff", _sleeve(22.225, hexagon=True), METAL)
    single("standoff_short", _sleeve(12.7, hexagon=True), METAL)
    single("shaft_insert", _insert(), POLYMER, boreAxis="Y")
    single("battery_clip", _battery_clip(), POLYMER, seatingPlaneMm=0.)
    parts.update(collar=_collar(), motor=_motor(), omni=_omni(), traction=_traction(),
                 brain=_controller(), battery=_battery(), gripper=_gripper())
    for alias, assembly in parts.items():
        shape = assembly.toCompound()
        if not shape.Solids() or not shape.isValid():
            raise ValueError(f"Original development part is not a valid solid assembly: {alias}")
    return parts


def measure_cached(source_path, cache_dir) -> dict:
    """Measure an exported development part, reusing exact-source-byte results.

    The seeder may reuse/copy unchanged authored STEP originals into a fresh
    workspace and call this instead of repeating native import/metrology. A
    changed STEP, importer/metrology implementation or kernel version requires
    new measurements. Pass an ignored private cache directory. Nothing here
    grants usage rights or qualifies manufacturer geometry.
    """
    import hashlib
    from importlib.metadata import version
    import json
    from pathlib import Path

    from tachyon.cad import native, metrology
    from tachyon.cad.catalog import write_json
    from tachyon.cad.rights import sha256_file

    source = Path(source_path)
    source_hash = sha256_file(source)
    implementation = hashlib.sha256()
    for module in (native, metrology):
        implementation.update(Path(module.__file__).read_bytes())
    identity = {"schemaVersion": 1, "sourceSha256": source_hash,
                "measurementImplementation": implementation.hexdigest(),
                "cadquery": cq.__version__, "ocp": version("cadquery-ocp")}

    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()

    cache = Path(cache_dir) / (digest(identity) + ".json")
    if cache.is_file():
        try:
            saved = json.loads(cache.read_text())
            data = saved["measurements"]
            if (saved["identity"] == identity and saved["measurementSha256"] == digest(data)
                    and data["name"].startswith("tachyon-development-")
                    and saved["nativeBrepValid"] is True
                    and sha256_file(source) == source_hash):
                return data
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass  # Damaged cache metadata cannot substitute for fresh metrology.
    assembly = native.import_source(source)
    if not assembly.metadata.get("definitionName", "").startswith("tachyon-development-"):
        raise ValueError("Measurement cache accepts only this generator's named development STEP exports")
    shape = assembly.toCompound()
    if not shape.Solids() or not shape.isValid():
        raise ValueError("Development STEP must contain valid solid geometry")
    data = metrology.measure_definition(assembly)
    if sha256_file(source) != source_hash:
        raise ValueError("Authored STEP changed during native measurement")
    write_json(cache, {"identity": identity, "nativeBrepValid": True,
                       "measurementSha256": digest(data), "measurements": data})
    return data
