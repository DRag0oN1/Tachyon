"""Measured source roller acquisition module, not a task-capability claim.

The module uses purchased traction wheels as conceptual compliant rollers. Real
Pin contact, floor pickup, a powered handoff gate and independent Cup retention
still require qualification; a roller module alone cannot pass robot acceptance.
"""
from __future__ import annotations

import math

from .. import assemblies as A
from .hardware import fastener, bearing_fasteners, shaft_retention
from .source_pack import native_pose

T = A.RigidTransform
X, Y, Z = (1.,0.,0.), (0.,1.,0.), (0.,0.,1.)


def add_pin_intake(b, pack):
    """Two independently driven vertical rollers on a bolted cantilever frame.

    Every structural port is checked against the supplied source hole centres.
    Two separated bearing flats support each shaft. The source wheel/hub/shaft
    inserts remain one purchased native subassembly with its eccentric origin.
    """
    for alias in ("traction",):
        b.parts[alias] = pack.parts[alias].part()
    mounts, rollers, shafts, motors = [], [], [], []
    beam_y = {"upper":166.4684,"lower":102.9684}
    arm_z, roller_z = 147.4184,261.7184
    for side,sign in (("right",1),("left",-1)):
        tower = side+"-intake-tower"
        pp = pack.port("channel",tower+"-base",(sign*69.85,-6.35,13.9684),Z,X)
        cp = pack.port("short_channel",tower+"-foot",(-76.2,0.,sign*6.35),Y,X)
        world = native_pose((sign*63.5,134.7184,102.9684),Y,Z,X)
        b.attach_at(tower,"short_channel","pin_intake","front-crossmember",pp,cp,world,angular_tolerance=math.pi)
        for i,x in enumerate((-76.2,-88.9)):
            pp = pack.port("channel",tower+f"-fix-{i}",(sign*69.85,-6.35-i*12.7,13.9684),Z,X)
            cp = pack.port("short_channel",tower+f"-fix-{i}",(x,0.,sign*6.35),Y,X)
            b.constraint(tower+f"-fix-{i}","front-crossmember",pp,tower,cp,
                         mate=b.port("front-crossmember",pp).inverse().compose(b.port(tower,cp)))
            mounts.extend(fastener(b,pack,tower+f"-bolt-{i}","front-crossmember",pp,offset_m=-.0011684,nut_distances_m=(.0038862,),role="pin_intake"))
        for level,y in beam_y.items():
            arm = f"{side}-{level}-intake-arm"
            center_y = y-12.7
            # Both folded angle flanges face upwards; native X reverses on
            # the left to preserve a right-handed placement without mirroring.
            tx = center_y+6.35-134.7184
            pp = pack.port("short_channel",arm+"-tower",(tx,-6.35,sign*12.7),Z,X)
            cp = pack.port("angle",arm+"-foot",(-sign*50.8,-6.35,0.),Z,X)
            world = native_pose((sign*76.2,center_y,arm_z),(0.,0.,sign),(0.,-1.,0.),(sign,0.,0.))
            b.attach_at(arm,"angle","pin_intake",tower,pp,cp,world,angular_tolerance=math.pi)
            for i in range(2):
                pp = pack.port("short_channel",arm+f"-tower-{i}",(tx-i*12.7,-6.35,sign*12.7),Z,X)
                cp = pack.port("angle",arm+f"-fix-{i}",(-sign*50.8,-6.35+i*12.7,0.),Z,X)
                b.constraint(arm+f"-fix-{i}",tower,pp,arm,cp,mate=b.port(tower,pp).inverse().compose(b.port(arm,cp)))
                mounts.extend(fastener(b,pack,arm+f"-bolt-{i}",tower,pp,offset_m=-sign*.0011684,reverse=sign<0,nut_distances_m=(.0038862,),role="pin_intake"))
    beams=[]
    for level,y in beam_y.items():
        beam = level+"-intake-crossbeam"
        for side,sign in (("right",1),("left",-1)):
            arm = f"{side}-{level}-intake-arm"
            # The source angle has a 0.0016 mm bend datum offset. The full
            # measured mate retains it, rather than rescaling either component.
            pp = pack.port("angle",beam+"-"+side,(sign*101.6,-12.7,-6.3516),Y,X)
            cp = pack.port("channel",beam+"-"+side,(sign*69.85,0.,-6.45),Y,X)
            world = native_pose((0.,y,255.4684))
            if side=="right":
                # Hole centre discrepancy is 1.6 micrometres, well within
                # source port tolerance; placement still uses measured frames.
                b.attach_at(beam,"channel","pin_intake",arm,pp,cp,world,angular_tolerance=math.pi)
            else:
                b.constraint(beam+"-left-tie",arm,pp,beam,cp,mate=b.port(arm,pp).inverse().compose(b.port(beam,cp)))
            mounts.extend(fastener(b,pack,beam+"-"+side+"-bolt",beam,cp,offset_m=.0011684,reverse=True,nut_distances_m=(.0038862,)))
        beams.append(beam)
    supports=[]
    for side,sign in (("right",1),("left",-1)):
        motor = side+"-intake-motor"
        mx = sign*69.85-12.7
        pp = pack.port("channel",motor+"-seat",(mx,1.1684,6.25),Y,X)
        world = native_pose((mx,211.8368,roller_z),X,Z,(0.,-1.,0.))
        b.attach_at(motor,"motor","pin_intake",beams[0],pp,"mount",world,angular_tolerance=math.pi)
        motors.append(motor)
        for i,x in enumerate((mx,mx-12.7)):
            pp = pack.port("channel",motor+f"-screw-{i}",(x,1.1684,6.25),Y,X)
            mounts.extend(fastener(b,pack,motor+f"-bolt-{i}",beams[0],pp,offset_m=-.0011684,nut_distances_m=()))
        shaft=side+"-intake-shaft"
        cp=pack.port("shaft_long","intake-motor-seat",(0.,0.,136.-177.8368),Z,X,kind="shaft",basis="shaft_station")
        b.attached(shaft,"shaft_long","pin_intake",motor,"output",cp,kind="revolute",axis=Z,limits=(-1000.,1000.),lower=0.,raised=0.)
        # The shaft origin is 136 mm above ground; the roller's working
        # plane is 130 mm. Eccentric native source coordinates remain intact.
        sp=pack.port("shaft_long","intake-roller-plane",(0.,0.,6.),Z,X,kind="shaft",basis="shaft_station")
        wheel_port=pack.port("traction","roller-shaft",(29.3129364268,56.9311020238,68.3968973123),Z,X,kind="shaft",basis="purchased_interface")
        roller=side+"-pin-roller"
        b.attached(roller,"traction","pin_intake",shaft,sp,wheel_port)
        b.purposes[roller]="roller"; rollers.append(roller); shafts.append(shaft)
        bearings=[]
        for level,cy,direction,face in (("upper",160.1184,-1.,0.),("lower",110.4868,1.,1.1684)):
            support=level+"-intake-crossbeam"
            pp=pack.port("channel",side+level+"-bearing-mount",(sign*69.85,face,6.25),Y,X,kind="bearing")
            bearing=side+"-"+level+"-intake-bearing"
            world=native_pose((sign*69.85,cy,roller_z),(0.,direction,0.),X,(0.,0.,-direction))
            b.attach_at(bearing,"bearing","pin_intake",support,pp,"mount",world,angular_tolerance=math.pi)
            points=[(sign*69.85+dx,face,6.25) for dx in (-12.7,12.7)]
            info=bearing_fasteners(b,pack,bearing,support,points,support_roll=X)
            mounts.extend(info["fastenerIds"])
            cp=pack.port("shaft_long",bearing+"-station",(0.,0.,136.-cy),Z,X,kind="shaft",basis="shaft_station")
            b.constraint(bearing+"-rotation",bearing,"axis",shaft,cp,kind="revolute",axis=Z,limits=(-1000.,1000.),lower=0.,raised=0.,
                         mate=b.port(bearing,"axis").inverse().compose(b.port(shaft,cp)))
            bearings.append(dict(instanceId=bearing,portId="axis"))
        retainers=shaft_retention(b,pack,shaft,"pin_intake",stations_mm=(136.-153.1716,136.-96.7074),reversed_indices=(0,))
        supports.append(dict(shaft=shaft,bearings=bearings,retainers=retainers))
    return dict(rollers=rollers,shafts=shafts,motors=motors,shaftSupports=supports,fasteners=mounts,
                motorCommandsRpm={motors[0]:100.,motors[1]:-100.},nominalGapM=.0381,
                limitations=["Traction-wheel compliance and Pin contact are unverified", "Powered gated transfer and independent Cup handling are not supplied by this module"])
