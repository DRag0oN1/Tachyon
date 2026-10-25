"""Source-component actuation and shaft support for the paired four-bars.

This authors ports and an assembly graph only. The existing pose solver checks
both endpoints. Neither these declared joints nor their gear ratios establish
collision-free motion, load capacity, object contact or achieved cycle time.
"""
from __future__ import annotations

import math

from .. import assemblies as A
from .source_pack import native_pose
from .hardware import bearing_fasteners, fastener, shaft_adapters, shaft_retention

T = A.RigidTransform
X, Y, Z = (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)


def _spinning_constraint(b, identity, parent, pp, shaft, cp, low, high):
    motion = T.rotation(Z, low)
    mate = motion.inverse().compose(b.port(parent, pp).inverse().compose(b.port(shaft, cp)))
    b.constraint(identity, parent, pp, shaft, cp, mate=mate, kind="revolute", axis=Z,
                 limits=(-200., 200.), lower=low, raised=high)


def add_scoring_drive(b, pack, four_bar):
    """Two geared lift motors; eight supported pivots and two input shafts.

    An off-axis through-bolt and real standoff connect each output gear to its
    angle link: a square shaft in a round sheet-metal hole is not a torque path.
    All source parts retain their original dimensions.
    """
    for alias in ("shaft_medium", "gear12", "standoff_short", "bolt_long"):
        b.parts[alias] = pack.parts[alias].part()
    for alias in ("shaft_medium",):
        for label, z in (("axis", 0.), ("start", -37.211), ("end", 37.211)):
            pack.port(alias, label, (0., 0., z), Z, X, kind="shaft", basis="shaft_station")
    pack.port("gear12", "shaft", (0., 0., 0.), Z, X, kind="shaft", basis="bore_station")
    pack.port("gear84", "lift-shaft", (0., 0., 0.), Z, X, kind="shaft", basis="bore_station")
    mounts, supports, transmissions = [], [], []
    gear_x = 106.7054  # 12.7 mm source standoff between link and near gear face
    low, high = four_bar["lowerAngleRad"], four_bar["raisedAngleRad"]

    def support_pair(side, sign, station, parent, alias, point, shaft, shaft_centre, q0, q1, ratio, outer_collar=93.9164):
        bearings, rels, screws = [], [], []
        # Each support is independently mounted to a real plate face. Native
        # bearing +Y follows vertical world +Y, keeping the bolt holes off-axis.
        for face, x, direction, source_face in (("outer",83.7184,sign,1.1684),("inner",69.85,-sign,0.)):
            node = f"{side}-{station}-{face}-bearing"
            source_point = (point[0], source_face, point[1]) if alias == "short_channel" else (point[0], point[1], source_face)
            axis = Y if alias == "short_channel" else Z
            roll = X
            port = pack.port(alias, node+"-plate", source_point, axis, roll, kind="bearing")
            center = b.port(parent, port).point()
            world = native_pose((sign*x, center[1]*1000, center[2]*1000), (direction,0.,0.), Y, (0.,0.,direction))
            b.attach_at(node,"bearing","scorer",parent,port,"mount",world,angular_tolerance=math.pi)
            # Source plate holes separated by 25.4 mm support each bearing.
            points = [(point[0]+d,source_face,point[1]) if alias=="short_channel" else (point[0]+d,point[1],source_face) for d in (-12.7,12.7)]
            info = bearing_fasteners(b,pack,node,parent,points,support_part=alias,support_axis=axis,support_roll=X)
            mounts.append(info); screws.extend(info["fastenerIds"])
            # A non-tree revolute constraint explicitly checks each shaft bore.
            station_mm = x-shaft_centre
            cp = pack.port("shaft_medium", node+"-station",(0.,0.,station_mm),Z,X,kind="shaft",basis="shaft_station")
            joint = node+"-rotation"
            # Reversing a support axis also reverses its signed coordinate.
            factor = direction/sign
            _spinning_constraint(b,joint,node,"axis",shaft,cp,q0*factor,q1*factor)
            four_bar["controls"].append((joint,ratio*factor))
            bearings.append(dict(instanceId=node,portId="axis")); rels.append(joint)
        retainers = shaft_retention(b,pack,shaft,"scorer",stations_mm=(63.0244-shaft_centre,outer_collar-shaft_centre),reversed_indices=(1,))
        supports.append(dict(shaftId=shaft,startPortId="start",endPortId="end",bearings=bearings,retainerIds=retainers,relationshipIds=rels))
        return bearings

    for side,sign in (("right",1),("left",-1)):
        ground,carrier = f"{side}-lift-upright",f"{side}-tool-carrier"
        output = None
        for level,gx,cx in (("lower",50.8,-38.1),("upper",127.,38.1)):
            link = f"{side}-{level}-four-bar-link"
            for end,point,parent,alias,plate_point in (("back",-146.05,ground,"angle",(gx,sign*6.35)),("front",146.05,carrier,"short_channel",(cx,sign*6.35))):
                shaft = f"{side}-{level}-{end}-pivot-shaft"
                # The pivot shaft rotates with its link, rather than drifting
                # independently as a nearby decorative cylinder.
                cp = pack.port("shaft_medium","link-plane",(0.,0.,87.6554-95.25),Z,X,kind="shaft",basis="shaft_station")
                lp = pack.port("angle","link-shaft-"+end,(point,0.,0.),(0.,0.,-1.),X,kind="shaft")
                b.attached(shaft,"shaft_medium","scorer",link,lp,cp)
                support_pair(side,sign,level+"-"+end,parent,alias,plate_point,shaft,95.25,-sign*low,-sign*high,-sign,
                             outer_collar=119.3164 if level=="lower" and end=="back" else 93.9164)
                # Source 3.175 mm spacer and 0.762 mm washer between bearing
                # and moving link. Their bores are kept on the actual shaft.
                for a,center in (("spacer",85.3059),("washer",87.2744)):
                    ap = pack.port(a,"lift-seat",(0.,0.,0.),Y if a=="spacer" else Z,X,kind="shaft",basis="bore_station")
                    sp = pack.port("shaft_medium",f"{a}-lift-plane",(0.,0.,center-95.25),Z,X,kind="shaft",basis="shaft_station")
                    b.attached(shaft+"-"+a,a,"scorer",shaft,sp,ap)
                if level=="lower" and end=="back":
                    output = shaft
        motor = f"{side}-lift-motor"
        mp = pack.port("angle",f"{side}-lift-motor-mount",(-12.7,sign*6.35,0.),Z,X)
        world = native_pose((sign*32.,190.5,-101.6),Y,(0.,0.,sign),(sign,0.,0.))
        b.attach_at(motor,"motor","scorer",ground,mp,"mount",world,angular_tolerance=math.pi)
        for index,x in enumerate((-12.7,-25.4)):
            p = pack.port("angle",f"{side}-lift-thread-{index}",(x,sign*6.35,0.),Z,X)
            mounts.append(dict(fastenerIds=fastener(b,pack,motor+f"-bolt-{index}",ground,p,offset_m=.0011684,reverse=True,nut_distances_m=())))
        shaft = f"{side}-lift-input-shaft"
        cp = pack.port("shaft_medium","motor-socket",(0.,0.,66.-94.),Z,X,kind="shaft",basis="shaft_station")
        phase = math.pi/12
        joint = shaft+"-spin"
        b.attached(shaft,"shaft_medium","scorer",motor,"output",cp,kind="revolute",axis=Z,
                   limits=(-200.,200.),lower=7*sign*low+phase,raised=7*sign*high+phase,joint_id=joint)
        four_bar["controls"].append((joint,7*sign))
        support_pair(side,sign,"lift-input",ground,"angle",(0.,sign*6.35),shaft,94.,7*sign*low+phase,7*sign*high+phase,7*sign,outer_collar=119.3164)
        gears=[]
        for gear_alias,axis_shaft,centre in (("gear12",shaft,94.),("gear84",output,95.25)):
            sp = pack.port("shaft_medium",gear_alias+"-plane",(0.,0.,gear_x-centre),Z,X,kind="shaft",basis="shaft_station")
            gear = f"{side}-lift-{gear_alias}"
            b.attached(gear,gear_alias,"scorer",axis_shaft,sp,"shaft" if gear_alias=="gear12" else "lift-shaft")
            gears.append(gear)
            if gear_alias=="gear84":
                shaft_adapters(b,pack,gear,gear_alias,"scorer")
        # Actual source off-axis hole, standoff and through-bolt join output
        # gear to moving sheet link; the full matrix closure is checked twice.
        lp = pack.port("angle","lift-torque-hole",(-107.95,0.,0.),(0.,0.,-1.),X)
        seat = pack.port("standoff_short","lift-bottom",(0.,-6.35,0.),Y,X,basis="bore_station")
        tip = pack.port("standoff_short","lift-top",(0.,6.35,0.),Y,X,basis="bore_station")
        stand = f"{side}-lift-torque-standoff"
        link = f"{side}-lower-four-bar-link"
        b.attached(stand,"standoff_short","scorer",link,lp,seat)
        gp = pack.port("gear84","lift-near-torque-hole",(38.1,0.,-6.35),Z,X)
        mate = b.port(stand,tip).inverse().compose(b.port(gears[1],gp))
        b.constraint(stand+"-gear-tie",stand,tip,gears[1],gp,mate=mate)
        far = pack.port("gear84","lift-far-torque-hole",(38.1,0.,6.35),Z,X)
        fastener(b,pack,f"{side}-lift-torque-bolt",gears[1],far,bolt="bolt_long",offset_m=0.,reverse=True,nut_distances_m=(.0281178,))
        transmissions.append(dict(side=side,motor=motor,inputShaft=shaft,outputShaft=output,inputGear=gears[0],outputGear=gears[1],reduction=7.,gearPlaneM=gear_x/1000))
    return dict(mounts=mounts,shaftSupports=supports,transmissions=transmissions,
                validationScope="Two declared endpoints; actuator load, swept clearance and physical performance unverified")
