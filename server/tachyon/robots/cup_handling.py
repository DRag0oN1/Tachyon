"""Original development-CAD Cup clamp and connected guide/alignment hardware.

These are newly authored fabrication concepts, not VEX manufacturer geometry.
The parallel clamp has an ideal opposed-lead screw coupling. Thread geometry,
grip force, friction, contact dynamics and independent Cup tilt are unverified.
"""
from __future__ import annotations

import math

from .. import assemblies as A
from .source_pack import DISPLAY,native_pose
from .hardware import fastener,shaft_adapters

T=A.RigidTransform
X,Y,Z=(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)
CUP_DIAMETER_MM=80.
CUP_HEIGHT_MM=164.5
SCREW_LEAD_M=.008
INPUT_PHASE_RAD=math.pi/12
INPUT_JOINTS=('cup-input-shaft-spin','cup-input-left-support','cup-input-right-support')


def development_parts():
    import cadquery as cq
    def box(dx,dy,dz,center):
        return cq.Workplane().box(dx,dy,dz).translate(center)
    def cylinder(radius,length,point,axis):
        return cq.Workplane(obj=cq.Solid.makeCylinder(radius,length,cq.Vector(*point),cq.Vector(*axis)))
    def assembly(name,solid,color):
        a=cq.Assembly(name='original_'+name);a.add(solid,name=name+'_fabrication',color=cq.Color(*color));return a
    bridge=box(146.05,3.175,88.9,(79.375,1.5875,-38.1))
    bridge=bridge.union(box(31.75,3.175,25.4,(-9.525,1.5875,-6.35)))
    bridge=bridge.union(box(18.375,3.175,38.1,(-2.8375,1.5875,-63.5)))
    # Clearance in the horizontal foot only; retain the motor mount face.
    bridge=bridge.cut(cylinder(4.6,4.7,(-13.55,0.,-63.5),X))
    # Rear motor plate and two actual input-bearing supports share the base.
    # The motor plate ends below the left bearing, leaving its rear face free.
    bridge=bridge.union(box(3.175,25.4,31.75,(-7.2625,-6.35,-63.5)))
    for x in (14.2875,131.7625):
        bridge=bridge.union(box(3.175,19.05,38.1,(x,12.7,-63.5)))
        for z in (-76.2,-63.5,-50.8):
            bridge=bridge.cut(cylinder(2.6 if z==-63.5 else 2.4,12.,(x-6.,12.7,z),X))
    for x,z in ((-19.05,0.),(-19.05,-12.7),(6.35,0.),(139.7,0.),(63.5,-6.35),(88.9,-6.35)):
        bridge=bridge.cut(cylinder(2.4,10,(x,-3,z),Y))
    for y in (0.,-12.7):bridge=bridge.cut(cylinder(2.4,10,(-12.05,y,-63.5),X))
    rail=cq.Assembly(name='original_cup_linear_guide')
    for z in (-6.35,-19.05):rail.add(cylinder(3.,146.05,(0.,12.7,z),X),name='linear_rail_'+str(abs(z)),color=cq.Color(.58,.64,.68))
    for x in (6.35,139.7):
        block=box(12.7,15.875,38.1,(x,14.2875,-12.7))
        for z,r in ((-6.35,3.1),(-19.05,3.1),(-12.7,2.6)):
            block=block.cut(cylinder(r,20,(x-10.,12.7,z),X))
        block=block.cut(cylinder(2.4,25,(x,3.,0.),Y))
        rail.add(block,name='guide_support_'+str(x),color=cq.Color(.27,.32,.36))
    result={'cup_bridge':assembly('cup_cantilever_bridge',bridge,(.26,.34,.41)),'cup_rail':rail}
    for side,sign in (('left',1),('right',-1)):
        jaw=box(10.,20.,30.,(0.,0.,0.))
        for z,r in ((-6.35,3.1),(6.35,3.1),(0.,2.6)):
            jaw=jaw.cut(cylinder(r,14,(-7.,0.,z),X))
        jaw=jaw.union(box(4.,18.,74.,(sign*2.,0.,43.35)))
        # Inner pad is exactly tangent to the modeled 80 mm development Cup.
        result['cup_jaw_'+side]=assembly('cup_'+side+'_jaw',jaw,(.12,.44,.57))
    # Round screw to the right guide exit, then an integral 3.175 mm square
    # extension through the 84T adapters. No round shaft overlaps the inserts.
    screw=cylinder(2.5,155.575,(0.,0.,-82.55),Z)
    screw=screw.union(box(3.175,3.175,9.525,(0.,0.,-77.7875)))
    screw=screw.union(box(3.175,3.175,38.125,(0.,0.,88.9125)))
    screw=screw.union(cq.Workplane('XY').polygon(6,7.).extrude(4.).translate((0.,0.,103.975)))
    result['cup_screw']=assembly('opposed_lead_screw_unthreaded',screw,(.63,.66,.7))
    result['cup_input_shaft']=assembly('cup_square_input_shaft_209_55mm',box(3.175,3.175,209.55,(0.,0.,-9.525)),(.63,.66,.7))
    collar=cylinder(6.,6.,(0.,0.,-3.),Z).cut(cylinder(2.6,8.,(0.,0.,-4.),Z))
    collar=collar.cut(cylinder(1.5,10.,(0.,-7.,0.),Y))
    retainer=assembly('cup_shaft_retainer',collar,(.34,.38,.42))
    retainer.add(cylinder(1.45,4.5,(0.,-6.1,0.),Y),name='original_nominal_set_screw_unthreaded',color=cq.Color(.55,.58,.6))
    result['cup_collar']=retainer
    # Original static funnel: no powered Pin gate or Pin scoring claim.
    guide=box(38.1,3.,12.7,(0.,1.5,0.))
    for x in (-12.7,12.7):guide=guide.cut(cylinder(2.4,8.,(x,-2.,0.),Y))
    for sign in (-1,1):
        guide=guide.union(box(3.,40.,21.,(sign*22.,-17.,-27.5)))
        guide=guide.union(box(8.,3.,21.,(sign*17.5,-35.5,-27.5)))
        guide=guide.union(box(8.,3.,22.,(sign*21.,1.5,-11.)))
    result['pin_handoff']=assembly('static_pin_handoff_guides',guide,(.7,.47,.12))
    stop=box(25.4,19.,3.,(76.2,12.7,22.))
    for x in (63.5,88.9):
        stop=stop.union(box(3.,3.,31.75,(x,4.5,6.125)))
        stop=stop.union(box(12.7,3.,12.7,(x,1.5,-6.35)))
        stop=stop.cut(cylinder(2.4,8,(x,-2.,-6.35),Y))
    result['cup_alignment']=assembly('cup_rear_alignment_stop',stop,(.79,.47,.15))
    # Official nominal envelope (Appendix B C-1). Wall thickness and centre
    # seating stop are explicit development assumptions, not manufacturer CAD.
    cup=cq.Assembly(name='original_modeled_cup')
    lower=cylinder(40.,82.25,(0.,0.,0.),Y).cut(cylinder(38.,84.25,(0.,-1.,0.),Y))
    upper=cylinder(40.,82.25,(0.,82.25,0.),Y).cut(cylinder(38.,84.25,(0.,81.25,0.),Y))
    cup.add(lower,name='assumed_clear_lower_half',color=cq.Color(.15,.62,.84,.45))
    cup.add(upper,name='assumed_opaque_upper_half',color=cq.Color(.23,.27,.31))
    cup.add(cylinder(38.,2.,(0.,81.25,0.),Y),name='assumed_internal_seating_stop',color=cq.Color(.35,.4,.44))
    result['operation_cup']=cup
    pin=cq.Assembly(name='original_modeled_pin')
    pin.add(cylinder(20.,82.5,(0.,0.,0.),Y),name='nominal_pin_lower_half',color=cq.Color(.8,.2,.15))
    pin.add(cylinder(20.,82.5,(0.,82.5,0.),Y),name='nominal_pin_upper_half',color=cq.Color(.9,.7,.12))
    result['operation_pin']=pin
    fixture=box(120.,6.,120.,(0.,3.,0.)).union(box(30.,108.,30.,(0.,60.,0.)))
    fixture=fixture.union(box(80.,6.,80.,(0.,117.,0.)))
    result['operation_target']=assembly('modeled_pin_support_fixture_not_official_goal',fixture,(.21,.29,.35))
    return result


def add_cup_handling(b,pack,facts):
    for alias in development_parts_aliases():b.parts[alias]=pack.parts[alias].part()
    root='cup-grip-frame'
    pp=pack.port('short_channel','cup-module-mount',(88.9,1.1684,6.35),Y,X)
    cp=pack.port('cup_bridge','platform-interface',(-19.05,0.,0.),Y,X,basis='purchased_interface')
    # Use the same native XYZ orientation as the existing horizontal platform.
    parent=facts['gripper']['platformId']
    parent_world=b.nominal_world[parent][1]
    desired=parent_world.compose(DISPLAY).compose(T.translation(.10795,.0043434,.00635)).compose(DISPLAY.inverse())
    b.attach_at(root,'cup_bridge','cup_cradle',parent,pp,cp,desired,axial_stack_m=.003175,angular_tolerance=math.pi)
    # A second actual grid hole prevents the fabricated module rotating on one screw.
    pp2=pack.port('short_channel','cup-module-second',(88.9,1.1684,-6.35),Y,X)
    cp2=pack.port('cup_bridge','platform-second',(-19.05,0.,-12.7),Y,X,basis='purchased_interface')
    b.constraint('cup-platform-second-fixing',parent,pp2,root,cp2,mate=T.translation(0.,0.,.003175))
    for i,port in enumerate((pp,pp2)):
        seat=pack.port('spacer','cup-platform-seat',(0.,-1.5875,0.),Y,X,kind='shaft',basis='bore_station')
        b.attached('cup-platform-spacer-'+str(i),'spacer','cup_cradle',parent,port,seat)
        fastener(b,pack,'cup-platform-bolt-'+str(i),parent,port,bolt='bolt_mid',offset_m=-.0011684,nut_distances_m=(.0090678,),role='cup_cradle')
    rail='cup-linear-guide'
    for label,x in (('left',6.35),('right',139.7)):
        rp=pack.port('cup_rail',label+'-foot',(x,6.35,0.),Y,X,basis='purchased_interface')
        bp=pack.port('cup_bridge',label+'-guide-bolt',(x,3.175,0.),Y,X,basis='purchased_interface')
        if label=='left':b.attached(rail,'cup_rail','cup_cradle',root,bp,rp,mate=T.translation(0.,0.,.003175))
        else:b.constraint('cup-guide-right-foot',root,bp,rail,rp,mate=b.port(root,bp).inverse().compose(b.port(rail,rp)))
        sp=pack.port('spacer',label+'-guide-spacer',(0.,-1.5875,0.),Y,X,basis='bore_station')
        b.attached('cup-guide-'+label+'-spacer','spacer','cup_cradle',root,bp,sp)
        fastener(b,pack,'cup-guide-'+label+'-bolt',root,bp,bolt='bolt_long',offset_m=-.003175,nut_distances_m=(.0237744,))
    mp=pack.port('cup_bridge','motor-face',(-8.85,0.,-63.5),X,Y,basis='purchased_interface')
    # Existing original actuator model; its mount posts face the fabricated plate.
    world=b.nominal_world[root][1].compose(DISPLAY).compose(native_pose((-53.05,0.,-63.5),Y,Z,X))
    b.attach_at('cup-grip-motor','motor','cup_cradle',root,mp,'mount',world,angular_tolerance=math.pi)
    for i,y in enumerate((0.,-12.7)):
        p=pack.port('cup_bridge','motor-bolt-'+str(i),(-8.85,y,-63.5),X,Y,basis='purchased_interface')
        fastener(b,pack,'cup-motor-bolt-'+str(i),root,p,offset_m=.003175,reverse=True,nut_distances_m=())
    # The screw is supported by its real guide bores; the rear motor drives it
    # through a separate 12T:84T input shaft, not a displaced direct socket.
    source=pack.port('cup_screw','left-tree-support',(0.,0.,6.35-73.025),Z,X,kind='shaft',basis='shaft_station')
    bearing=pack.port('cup_rail','left-tree-screw-bearing',(6.35,12.7,-12.7),X,Y,kind='bearing',basis='purchased_interface')
    b.attached('cup-opposed-screw','cup_screw','cup_cradle',rail,bearing,source,
        kind='revolute',axis=Z,limits=(-40.,40.),lower=0.,raised=0.,joint_id='cup-grip-screw-spin')
    # Both independently checked support constraints share the guide parent.
    # Explicitly select the placement edge, as required by build_pose.
    next(n for n in b.instances if n['id']=='cup-opposed-screw')['placementRelationshipId']='cup-grip-screw-spin'
    for label,x in (('left',6.35),('right',139.7)):
        pp=pack.port('cup_rail',label+'-screw-bearing',(x,12.7,-12.7),X,Y,kind='bearing',basis='purchased_interface')
        cp=pack.port('cup_screw',label+'-support',(0.,0.,x-73.025),Z,X,kind='shaft',basis='shaft_station')
        b.constraint('cup-screw-'+label+'-support',rail,pp,'cup-opposed-screw',cp,kind='revolute',axis=Z,
            limits=(-40.,40.),lower=0.,raised=0.)
    input_shaft='cup-transmission-input-shaft'
    cp=pack.port('cup_input_shaft','motor-key',(0.,0.,-104.775),Z,X,kind='shaft',basis='shaft_station')
    b.attached(input_shaft,'cup_input_shaft','cup_cradle','cup-grip-motor','output',cp,kind='revolute',
        axis=Z,limits=(-100.,100.),lower=INPUT_PHASE_RAD,raised=INPUT_PHASE_RAD,joint_id=INPUT_JOINTS[0])
    b.purposes[input_shaft]='shaft'
    input_bearings=[]
    for label,x,direction,face in (('left',6.35,-1.,12.7),('right',139.7,1.,133.35)):
        name='cup-input-'+label+'-bearing'
        axis=tuple(direction*v for v in X)
        pp=pack.port('cup_bridge',name+'-seat',(face,12.7,-63.5),axis,Z,basis='hole')
        cp=pack.port('bearing','cup-mount',(-6.35,0.,0.),X,Y)
        b.attached(name,'bearing','cup_cradle',root,pp,cp)
        for index,z in enumerate((-76.2,-50.8)):
            pp=pack.port('cup_bridge',name+'-bolt-'+str(index),(face,12.7,z),axis,Z,basis='hole')
            cp=pack.port('bearing','cup-bolt-'+str(index),(-6.35,(-12.7,12.7)[index],0.),X,Y)
            b.constraint(name+'-bolt-mate-'+str(index),root,pp,name,cp)
            fastener(b,pack,name+'-bolt-'+str(index),root,pp,bolt='bolt_mid',offset_m=.00635,
                reverse=True,nut_distances_m=(.0110744,),role='cup_cradle')
        pp=pack.port('bearing','cup-input-'+label+'-axis',(0.,0.,0.),axis,(0.,0.,-direction),kind='bearing',basis='bore_station')
        cp=pack.port('cup_input_shaft',label+'-support',(0.,0.,x-85.725),Z,X,kind='shaft',basis='shaft_station')
        b.constraint('cup-input-'+label+'-support',name,pp,input_shaft,cp,kind='revolute',axis=Z,
            limits=(-100.,100.),lower=INPUT_PHASE_RAD,raised=INPUT_PHASE_RAD)
        input_bearings.append(name)
    gears=[]
    for alias,shaft,centre in (('gear12',input_shaft,85.725),('gear84','cup-opposed-screw',73.025)):
        shaft_alias=b.nominal_world[shaft][0]
        pp=pack.port(shaft_alias,'cup-transfer-gear',(0.,0.,158.75-centre),Z,X,kind='shaft',basis='shaft_station')
        cp=pack.port(alias,'cup-transfer-shaft',(0.,0.,0.),Z,X,kind='shaft',basis='bore_station')
        name='cup-transfer-'+alias
        b.attached(name,alias,'cup_cradle',shaft,pp,cp)
        gears.append(name)
        if alias=='gear84':shaft_adapters(b,pack,name,alias,'cup_cradle')
    cp=pack.port('cup_collar','shaft',(0.,0.,0.),Z,X,kind='shaft',basis='bore_station')
    retainers=[]
    for shaft,alias,centre,prefix in ((input_shaft,'cup_input_shaft',85.725,'cup-input'),
                                     ('cup-opposed-screw','cup_screw',73.025,'cup-screw')):
        for label,x in (('thrust',149.225),('output',168.275)):
            pp=pack.port(alias,label+'-retention',(0.,0.,x-centre),Z,X,kind='shaft',basis='shaft_station')
            name=prefix+'-'+label+'-collar'
            b.attached(name,'cup_collar','cup_cradle',shaft,pp,cp)
            retainers.append(name)
    jaw_joints=[]
    for side,sign in (('left',-1.),('right',1.)):
        pp=pack.port('cup_rail',side+'-carriage',(76.2+sign*44.,12.7,-12.7),X,Y,kind='prismatic',basis='purchased_interface')
        cp=pack.port('cup_jaw_'+side,'carriage',(0.,0.,0.),X,Y,kind='prismatic',basis='bore_station')
        joint='cup-'+side+'-jaw-slide'
        b.attached('cup-'+side+'-jaw','cup_jaw_'+side,'cup_cradle',rail,pp,cp,
            kind='prismatic',axis=Z,limits=(-.01,.000001) if side=='left' else (-.000001,.01),lower=0.,raised=0.,joint_id=joint)
        jaw_joints.append(joint)
    # Static Pin funnel remains explicitly unsupported as an actuated handoff.
    pp=pack.port('channel','handoff-guide',(0.,1.1684,-.1),Y,X)
    cp=pack.port('pin_handoff','mount',(0.,0.,0.),Y,X,basis='purchased_interface')
    b.attached('pin-handoff-guides','pin_handoff','pin_transfer','upper-intake-crossbeam',pp,cp)
    pp=pack.port('cup_bridge','alignment-mount',(63.5,3.175,-6.35),Y,X,basis='purchased_interface')
    cp=pack.port('cup_alignment','mount',(63.5,0.,-6.35),Y,X,basis='purchased_interface')
    b.attached('cup-alignment-stop','cup_alignment','stack_interface',root,pp,cp)
    for x in (63.5,88.9):
        pp=pack.port('cup_bridge','alignment-bolt-'+str(x),(x,3.175,-6.35),Y,X,basis='purchased_interface')
        fastener(b,pack,'cup-alignment-bolt-'+str(int(x)),root,pp,offset_m=-.003175,nut_distances_m=(.0077244,),role='stack_interface')
    point=DISPLAY.point((.0762,.0127,.0635))
    anchor=dict(id='cup-clamp-center',instanceId=root,localPointM=list(point))
    members=[n['id'] for n in b.instances if n['subsystemId']=='cup_cradle']
    for action in ('acquire_cup','place_cup'):b.bind(action,'cup_cradle',members,jaw_joints,[anchor])
    return dict(kind='original_parallel_cup_clamp',instanceId=root,anchor=anchor,
        jawJoints=jaw_joints,screwJoints=['cup-grip-screw-spin','cup-screw-left-support','cup-screw-right-support'],
        inputJoints=list(INPUT_JOINTS),modeledObjectDiameterM=.08,modeledObjectHeightM=.1645,screwLeadM=SCREW_LEAD_M,
        transmission=dict(kind='original_12_84_spur_transfer',inputShaftId=input_shaft,inputBearingIds=input_bearings,
            inputGearId=gears[0],outputGearId=gears[1],retainerIds=retainers,inputRatio=-7.,inputOffsetRad=INPUT_PHASE_RAD,
            inputTeeth=12,outputTeeth=84,centerDistanceM=.0508,gearPlaneOwnXM=.15875,
            inputShaftLengthM=.20955,shaftClearanceStatus='known_nonmating_four_bar_intersection',
            provenance='Newly authored development shaft, keyed screw and supports; original development gear/bearing/adapter definitions, no manufacturer geometry'),
        independentTiltSupported=False,physicalRetentionVerified=False,
        clearanceStatus='partial_known_body_intersections',
        limitations=['Nominal Cup dimensions follow official Appendix B C-1; simplified walls, central stop and equal half-lengths are assumptions',
            'Known motor/foot intersections with four-bar and intake bodies remain; the extended input shaft also intersects the upper four-bar in raised/carry/place poses. This partial layout is not clearance-qualified',
            'Ideal 8 mm/revolution opposed-thread screw and 7:1 spur coupling; thread/gear contact, force and friction are not simulated',
            'Pin handoff and stack pieces are static guides; powered Pin gate/Pin release remain unsupported'])


def development_parts_aliases():
    return ('cup_bridge','cup_rail','cup_jaw_left','cup_jaw_right','cup_screw','cup_input_shaft','cup_collar','pin_handoff','cup_alignment')
