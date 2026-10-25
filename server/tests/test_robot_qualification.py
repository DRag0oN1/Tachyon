"""Original metadata mathematics only; synthetic receipts are not VEX acceptance.

The positive case stubs already-reviewed manufacturer receipt metadata. No CAD,
rights files, private inventory, training or other application state is opened.
"""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from tachyon import assemblies as A
from tachyon.models import PreparedComponent
from tachyon.robot_qualification import RobotContract, qualify_robot


EVIDENCE = "Original synthetic receipt/measurement for validator unit tests only"


def make_case():
    parts, relationships, supports, transmissions, mechanisms = {}, [], [], [], []

    def add(identity, purpose, role, position=(0., 0., 0.), ports=None):
        frames = {"mount": (0., 0., 0.), "axis": (0., 0., 0.), **(ports or {})}
        parts[identity] = dict(purpose=purpose, role=role, position=position, ports=frames)
        return identity

    def ref(identity, port="axis"):
        return {"instanceId": identity, "portId": port}

    def connect(parent, child, *, kind="fixed", pp="mount", cp="mount"):
        if kind != "fixed":
            pp = "axis" if pp == "mount" else pp
            cp = "axis" if cp == "mount" else cp
        p, c = parts[parent], parts[child]
        wp = A.RigidTransform.translation(*p["position"]).compose(A.RigidTransform.translation(*p["ports"][pp]))
        wc = A.RigidTransform.translation(*c["position"]).compose(A.RigidTransform.translation(*c["ports"][cp]))
        identity = "connection-" + str(len(relationships))
        arguments = dict(id=identity, parent_instance_id=parent, parent_port_id=pp,
                         child_instance_id=child, child_port_id=cp, kind=kind,
                         mate_transform=wp.inverse().compose(wc))
        if kind != "fixed":
            arguments.update(axis=(0., 0., 1.), limits=(-1., 1.), moving_member_ids=(child,))
        relationships.append(A.Relationship(**arguments))
        return identity

    def shaft(identity, role, position):
        add(identity, "shaft", role, position, {"start": (0.,0.,-.05), "end": (0.,0.,.05)})
        bearings = []
        rels = []
        for suffix, z in (("a", -.03), ("b", .03)):
            bearing = add(identity+"-bearing-"+suffix, "bearing", role, (position[0], position[1], position[2]+z))
            bearings.append(ref(bearing)); rels.append(connect(identity,bearing))
        collar = add(identity+"-collar", "retainer", role, position)
        rels.append(connect(identity,collar))
        supports.append(dict(id=identity+"-support", shaftId=identity, startPortId="start", endPortId="end",
                             bearings=bearings, retainerIds=[collar], relationshipIds=rels, evidence=EVIDENCE))
        return identity

    def stage(stages, a, b, *, gear=False):
        s = dict(id="stage-"+str(len(stages)), kind="gear_mesh" if gear else "shaft", driver=ref(a),
                 driven=ref(b), speedRatio=-1. if gear else 1., evidence=EVIDENCE)
        if gear:
            s.update(driverTeeth=40, drivenTeeth=40, moduleM=.001)
        else:
            s.update(engagementM=.01)
        stages.append(s)

    def transmission(identity, motor, outputs, stages):
        transmissions.append(dict(id=identity, actuator=ref(motor), outputs=[ref(i) for i in outputs], stages=stages, evidence=EVIDENCE))
        return identity

    add("frame", "structure", "chassis", ports={"front": (0.,.2,0.), "rear": (.05,.2,0.)})
    for i in range(3):
        add("cross-"+str(i), "structure", "chassis", (.1*i,0.,0.))
    add("brain", "control", "chassis"); add("battery", "power", "chassis")
    add("screw", "fastener", "chassis")
    sides = []
    for side, y in (("left", -.2), ("right", .2)):
        positions = [(-.2+i*.04,y,0.) for i in range(3)]
        motor = add(side+"-motor", "motor", "drive", positions[0])
        shafts = [shaft(side+"-shaft-"+str(i), "drive", pos) for i,pos in enumerate(positions)]
        gears = [add(side+"-gear-"+str(i), "gear", "drive", pos) for i,pos in enumerate(positions)]
        wheels = [add(side+"-wheel-"+str(i), "wheel", "drive", positions[j]) for i,j in enumerate((0,2))]
        stages = []
        stage(stages,motor,shafts[0]); stage(stages,shafts[0],gears[0]); stage(stages,shafts[0],wheels[0])
        stage(stages,gears[0],gears[1],gear=True); stage(stages,gears[1],shafts[1])
        stage(stages,gears[1],gears[2],gear=True); stage(stages,gears[2],shafts[2]); stage(stages,shafts[2],wheels[1])
        for wheel in wheels:
            connect("frame",wheel,kind="revolute",cp="axis")
        tid = transmission(side+"-drive",motor,wheels,stages)
        sides.append(dict(id=side,wheelInstanceIds=wheels,transmissionId=tid))

    positions = [(.3,.1,0.), (.34,.1,0.)]
    motor = add("intake-motor","motor","pin_intake",positions[0])
    shafts = [shaft("intake-shaft-"+str(i),"pin_intake",p) for i,p in enumerate(positions)]
    gears = [add("intake-gear-"+str(i),"gear","pin_intake",p) for i,p in enumerate(positions)]
    rollers = [add("roller-"+str(i),"roller","pin_intake",p) for i,p in enumerate(positions)]
    add("intake-guide","guide","pin_intake")
    stages = []; stage(stages,motor,shafts[0]); stage(stages,shafts[0],gears[0]); stage(stages,shafts[0],rollers[0])
    stage(stages,gears[0],gears[1],gear=True); stage(stages,gears[1],shafts[1]); stage(stages,shafts[1],rollers[1])
    tid = transmission("intake-drive",motor,rollers,stages)
    joints = [connect("frame",r,kind="revolute",cp="axis") for r in rollers]
    mechanisms.append(dict(role="pin_intake",kind="opposed_rollers",jointIds=joints,transmissionIds=[tid],evidence=EVIDENCE))

    add("link-a","structure","scorer",(0.,.2,0.), {"pivot": (0.,0.,0.), "tip": (0.,.2,0.)})
    add("link-b","structure","scorer",(.05,.2,0.), {"pivot": (0.,0.,0.), "tip": (0.,.2,0.)})
    add("carrier","structure","scorer",(0.,.4,0.), {"front": (0.,0.,0.), "rear": (.05,0.,0.)})
    add("gripper","gripper","scorer",(0.,.45,0.))
    bar_joints = [connect("frame","link-a",kind="revolute",pp="front",cp="pivot"),
                  connect("frame","link-b",kind="revolute",pp="rear",cp="pivot"),
                  connect("link-a","carrier",kind="revolute",pp="tip",cp="front"),
                  connect("link-b","carrier",kind="revolute",pp="tip",cp="rear")]
    connect("carrier","gripper")
    motor = add("lift-motor","motor","scorer",(0.,.2,0.)); axle = shaft("lift-shaft","scorer",(0.,.2,0.))
    stages = []; stage(stages,motor,axle); stage(stages,axle,"link-a")
    tid = transmission("lift-drive",motor,["link-a"],stages)
    grip_motor = add("grip-motor","motor","scorer",(0.,.45,0.)); grip_axle = shaft("grip-shaft","scorer",(0.,.45,0.))
    stages = []; stage(stages,grip_motor,grip_axle); stage(stages,grip_axle,"gripper")
    grip_tid = transmission("grip-drive",grip_motor,["gripper"],stages)
    grip_joint = connect("carrier","gripper",kind="revolute",cp="axis")
    mechanisms.append(dict(role="scorer",kind="four_bar_gripper",jointIds=[*bar_joints,grip_joint],transmissionIds=[tid,grip_tid],evidence=EVIDENCE,
                           fourBar=dict(groundId="frame",linkIds=["link-a","link-b"],carrierId="carrier",gripperId="gripper",jointIds=bar_joints)))

    for role,kind,position,outputs in (
        ("pin_transfer","gated_handoff",(.4,.2,0.),[("gate","gate")]),
        ("cup_cradle","independent_cup",(.2,.4,0.),[("cup","cradle"),("cup-latch","latch")])):
        motor = add(role+"-motor","motor",role,position); axle = shaft(role+"-shaft",role,position)
        stages = []; stage(stages,motor,axle)
        joints = []
        for identity,purpose in outputs:
            add(identity,purpose,role,position); stage(stages,axle,identity)
            joints.append(connect("frame",identity,kind="revolute",cp="axis"))
        if role == "pin_transfer":
            add("handoff-guide","guide",role)
        tid = transmission(role+"-drive",motor,[i for i,_ in outputs],stages)
        mechanisms.append(dict(role=role,kind=kind,jointIds=joints,transmissionIds=[tid],evidence=EVIDENCE))
    add("stack-guide","guide","stack_interface",(0.,.5,0.)); connect("carrier","stack-guide")
    mechanisms.append(dict(role="stack_interface",kind="stack_alignment",evidence=EVIDENCE))
    for mechanism in mechanisms:
        mechanism["memberIds"] = [i for i,p in parts.items() if p["role"] == mechanism["role"]]
        if mechanism["role"] == "scorer":
            mechanism["memberIds"].append("frame")
    for identity in parts:
        if identity != "frame":
            connect("frame",identity)
    definitions = []
    instances = []
    bom = []
    for identity,p in parts.items():
        fingerprint = A.content_hash([identity,p])
        ports = tuple(A.AttachmentPort(id=k,kind="mount" if k=="mount" else "shaft", frame=A.RigidTransform.translation(*v),evidence=EVIDENCE) for k,v in p["ports"].items())
        definition = A.ComponentDefinition(id=identity,name="Synthetic reviewed receipt: "+identity,sku="276-0000",
            source_url="https://www.vexrobotics.com/unit-test-metadata",source_sha256="1"*64,mesh_sha256="2"*64,
            mesh_url="urn:unit-test:no-mesh",catalog_fingerprint=fingerprint,origin_kind="manufacturer_cad",
            geometry_class="verified_imported_component",declared_use="unit-test-metadata",qualified_operations=("assembly_placement",),ports=ports,
            geometry_validation=A.GeometryValidation(status="valid",native_brep_valid=True,qualified_for_robot_generation=True))
        definitions.append(definition)
        instances.append(A.ComponentInstance(id=identity,component_id=identity,subsystem_id=p["role"],parent_id=None if identity=="frame" else "frame",transform=A.RigidTransform.translation(*p["position"])))
        bom.append(dict(instanceId=identity,componentId=identity,catalogFingerprint=fingerprint,purpose=p["purpose"],evidence=EVIDENCE))
    revision = A.AssemblyService(definitions).build(design_id="qualification-unit-test",recipe_id="synthetic-receipts",
        configuration_id="lower",root_instance_id="frame",instances=instances,subsystems=[A.Subsystem(id=r,name=r) for r in sorted({p["role"] for p in parts.values()})],relationships=relationships)
    contract = dict(bom=bom,mounts=[dict(id="original-metadata-mount",memberIds=list(parts),supportIds=["frame"],
        fastenerIds=["screw"],relationshipIds=[r.id for r in relationships],evidence=EVIDENCE)],shaftSupports=supports,
        transmissions=transmissions,driveSides=sides,mechanisms=mechanisms,
        objects=[dict(kind="pin",diameterM=.04,heightM=.165,sourceUrl="https://www.vexrobotics.com/declared-test-reference",uncertainty="Learner-declared dimensions; official source review remains separate"),
                 dict(kind="cup",sourceUrl="https://www.vexrobotics.com/declared-test-reference",uncertainty="Official dimensions unspecified")])
    return revision, contract


@pytest.fixture
def case():
    return make_case()


def codes(report):
    return {m.code for m in report.missing}


def test_complete_metadata_contract_computes_true_without_task_or_physical_claims(case):
    revision, raw = case
    report = qualify_robot(revision,RobotContract.model_validate(raw))
    assert report.missing == (), report.json_data()["missing"]
    assert report.complete_robot and report.hardware_qualified and report.status == "ready"
    assert report.counts["wheel"] == 4 and report.counts["motor"] == 7
    assert len(report.role_counts) == 7 and all(report.role_counts.values())
    assert report.task_capability_status == "unverified" and report.physical_performance_verified is False
    assert any("cup: official dimensions are unspecified" in text for text in report.uncertainties)
    assert report.revision_id == revision.id and report.engineering_hash == revision.engineering_hash
    assert all(p.matches_bom for p in report.provenance)
    assert qualify_robot(revision,RobotContract.model_validate(raw)) == report


@pytest.mark.parametrize("fault,expected", [
    ("missing-bom", "BOM_COVERAGE"), ("fingerprint", "STALE_BOM_FINGERPRINT"),
    ("disconnected", "DISCONNECTED_TRANSMISSION"), ("ratio", "TRANSMISSION_RATIO"),
    ("pitch", "GEAR_PITCH_ALIGNMENT"), ("missing-mount", "MOUNT_COVERAGE"),
    ("bearing", "TWO_SEPARATED_BEARINGS_REQUIRED"), ("support", "SHAFT_SUPPORT_MISSING"),
    ("role", "MECHANISM_REQUIRED"), ("fourbar", "FOUR_BAR_LOOP"),
    ("drive-side", "INDEPENDENT_DRIVE_MOTORS"), ("engagement", "SHAFT_ENGAGEMENT"),
])
def test_faults_cannot_be_hidden_by_connected_scene_graph(case,fault,expected):
    revision,raw = case
    if fault == "missing-bom": raw["bom"] = [b for b in raw["bom"] if b["instanceId"] != "screw"]
    elif fault == "fingerprint": raw["bom"][0]["catalogFingerprint"] = "f"*64
    elif fault == "disconnected": raw["transmissions"][0]["stages"].pop(0)
    elif fault == "ratio": raw["transmissions"][0]["stages"][3]["speedRatio"] = -.5
    elif fault == "pitch": raw["transmissions"][0]["stages"][3]["moduleM"] = .002
    elif fault == "missing-mount": raw["mounts"] = []
    elif fault == "bearing": raw["shaftSupports"][0]["bearings"][1] = deepcopy(raw["shaftSupports"][0]["bearings"][0])
    elif fault == "support": raw["shaftSupports"].pop(0)
    elif fault == "role": raw["mechanisms"] = [m for m in raw["mechanisms"] if m["role"] != "pin_transfer"]
    elif fault == "fourbar":
        bar = next(m["fourBar"] for m in raw["mechanisms"] if m["role"] == "scorer")
        bar["jointIds"][0] = bar["jointIds"][1]
    elif fault == "drive-side": raw["driveSides"][1]["transmissionId"] = raw["driveSides"][0]["transmissionId"]
    elif fault == "engagement": raw["transmissions"][0]["stages"][0]["engagementM"] = .2
    report = qualify_robot(revision,RobotContract.model_validate(raw))
    assert not report.complete_robot and expected in codes(report), report.json_data()["missing"]


@pytest.mark.parametrize("claim",["completeRobot","hardwareQualified","physicalPerformanceVerified","taskCapabilityStatus"])
def test_caller_cannot_inject_success_or_physical_claims(case,claim):
    _,raw = case
    raw[claim] = True
    with pytest.raises(ValidationError): RobotContract.model_validate(raw)


def test_non_vex_fixtures_never_pass_authenticity(case):
    revision,raw = case
    data = revision.assembly.json_data()
    data["components"][0].update(originKind="tachyon_authored",geometryClass="test_fixture")
    fixture = A._revision(A.AssemblySnapshot.model_validate(data))
    report = qualify_robot(fixture,RobotContract.model_validate(raw))
    assert "NON_AUTHENTIC_VEX_COMPONENT" in codes(report) and not report.complete_robot


def test_exact_revision_hash_and_contract_order_are_respected(case):
    revision,raw = case
    before = qualify_robot(revision,RobotContract.model_validate(raw))
    raw["bom"].reverse(); raw["mounts"][0]["memberIds"].reverse()
    assert qualify_robot(revision,RobotContract.model_validate(raw)) == before
    changed = A._revision(revision.assembly,revision.id)
    after = qualify_robot(changed,RobotContract.model_validate(raw))
    assert after.complete_robot and after.engineering_hash == before.engineering_hash
    assert after.revision_id != before.revision_id and after.report_hash != before.report_hash
    tampered = revision.model_copy(update={"engineering_hash": "f"*64})
    assert "REVISION_HASH_MISMATCH" in codes(qualify_robot(tampered,RobotContract.model_validate(raw)))


def test_missing_contract_is_truthful_and_does_not_mutate_revision(case):
    revision,_ = case
    original = revision.model_dump_json()
    report = qualify_robot(revision,None)
    assert report.graph_valid and not report.complete_robot
    assert "ROBOT_CONTRACT_MISSING" in codes(report)
    assert revision.model_dump_json() == original


def test_gear_mesh_cannot_be_faked_as_fixed_contact(case):
    revision,raw = case
    data = revision.assembly.json_data()
    data["relationships"].append(A.Relationship(id="fake-fixed-gear-contact",parent_instance_id="left-gear-0",
        parent_port_id="mount",child_instance_id="left-gear-1",child_port_id="mount",
        mate_transform=A.RigidTransform.translation(.04,0.,0.)).json_data())
    changed = A._revision(A.AssemblySnapshot.model_validate(data))
    report = qualify_robot(changed,RobotContract.model_validate(raw))
    assert not report.complete_robot and "FAKE_FIXED_GEAR_CONTACT" in codes(report)


def test_world_axis_misalignment_is_not_just_graph_connectivity(case):
    revision,raw = case
    data = revision.assembly.json_data()
    gear = next(c for c in data["components"] if c["id"] == "left-gear-1")
    next(p for p in gear["ports"] if p["id"] == "axis")["frame"] = A.RigidTransform.rotation((1.,0.,0.),.2).json_data()
    changed = A._revision(A.AssemblySnapshot.model_validate(data))
    report = qualify_robot(changed,RobotContract.model_validate(raw))
    assert not report.complete_robot and "SHAFT_AXIS_ALIGNMENT" in codes(report)


def test_gate_joint_must_be_actuated_not_just_near_a_motor(case):
    revision,raw = case
    handoff = next(t for t in raw["transmissions"] if t["id"] == "pin_transfer-drive")
    handoff["outputs"] = [{"instanceId":"pin_transfer-shaft","portId":"axis"}]
    report = qualify_robot(revision,RobotContract.model_validate(raw))
    assert not report.complete_robot and "JOINT_UNPOWERED" in codes(report)


def test_attached_gripper_without_a_driven_retention_joint_is_incomplete(case):
    revision,raw = case
    scorer = next(m for m in raw["mechanisms"] if m["role"] == "scorer")
    scorer["jointIds"] = list(scorer["fourBar"]["jointIds"])
    report = qualify_robot(revision,RobotContract.model_validate(raw))
    assert not report.complete_robot and "GRIPPER_ACTUATION" in codes(report)


@pytest.mark.parametrize("value",[True,"1.0",float("nan"),float("inf")])
def test_stage_ratios_reject_coercion_and_nonfinite_values(case,value):
    _,raw = case
    raw["transmissions"][0]["stages"][0]["speedRatio"] = value
    with pytest.raises(ValidationError): RobotContract.model_validate(raw)


def independent_intake(case):
    revision, raw = case
    data = revision.assembly.json_data()
    original = next(i for i in data["instances"] if i["id"] == "intake-motor")
    new = deepcopy(original)
    new["id"] = "intake-motor-b"
    new["transform"] = next(i["transform"] for i in data["instances"] if i["id"] == "roller-1")
    data["instances"].append(new); data["requiredInstanceIds"].append(new["id"])
    rel = A.Relationship(id="mount-independent-intake",parent_instance_id="frame",parent_port_id="mount",
        child_instance_id=new["id"],child_port_id="mount",mate_transform=A.RigidTransform.model_validate(new["transform"]))
    data["relationships"].append(rel.json_data())
    raw["mounts"][0]["memberIds"].append(new["id"])
    raw["mounts"][0]["relationshipIds"].append(rel.id)
    item = deepcopy(next(b for b in raw["bom"] if b["instanceId"] == "intake-motor"))
    item["instanceId"] = new["id"]; raw["bom"].append(item)
    intake = next(t for t in raw["transmissions"] if t["id"] == "intake-drive")
    left = deepcopy(intake)
    left["outputs"] = [intake["outputs"][0]]; left["stages"] = intake["stages"][:3]
    intake.update(left)
    right = dict(id="intake-independent-b",actuator={"instanceId":new["id"],"portId":"axis"},
        outputs=[{"instanceId":"roller-1","portId":"axis"}],evidence=EVIDENCE,
        stages=[dict(id="motor-shaft",kind="shaft",driver={"instanceId":new["id"],"portId":"axis"},
            driven={"instanceId":"intake-shaft-1","portId":"axis"},speedRatio=1.,engagementM=.01,evidence=EVIDENCE),
            dict(id="shaft-gear",kind="shaft",driver={"instanceId":"intake-shaft-1","portId":"axis"},
            driven={"instanceId":"intake-gear-1","portId":"axis"},speedRatio=1.,engagementM=.01,evidence=EVIDENCE),
            dict(id="shaft-roller",kind="shaft",driver={"instanceId":"intake-shaft-1","portId":"axis"},
            driven={"instanceId":"roller-1","portId":"axis"},speedRatio=1.,engagementM=.01,evidence=EVIDENCE)])
    raw["transmissions"].append(right)
    mechanism = next(m for m in raw["mechanisms"] if m["role"] == "pin_intake")
    mechanism["memberIds"].append(new["id"])
    mechanism["transmissionIds"].append(right["id"])
    mechanism["motorSpeedsRpm"] = {"intake-motor":200.,new["id"]:-200.}
    return A._revision(A.AssemblySnapshot.model_validate(data)),raw


@pytest.mark.parametrize("fault",[None,"same-direction","missing-command","zero-command"])
def test_independent_intake_requires_opposing_declared_motor_commands(case,fault):
    revision,raw = independent_intake(case)
    speeds = next(m for m in raw["mechanisms"] if m["role"] == "pin_intake")["motorSpeedsRpm"]
    if fault == "same-direction": speeds["intake-motor-b"] = 200.
    elif fault == "missing-command": speeds.pop("intake-motor-b")
    elif fault == "zero-command": speeds["intake-motor-b"] = 0.
    report = qualify_robot(revision,RobotContract.model_validate(raw))
    if fault is None:
        assert report.complete_robot, report.json_data()["missing"]
    else:
        assert not report.complete_robot and codes(report).intersection(("ROLLER_DIRECTION","ROLLER_MOTOR_COMMANDS"))


@pytest.mark.parametrize("fault",[None,"missing-retainer","wrong-release"])
def test_cup_can_use_fixed_retention_and_one_powered_tilt_joint(case,fault):
    revision,raw = case
    data = revision.assembly.json_data()
    cup = next(m for m in raw["mechanisms"] if m["role"] == "cup_cradle")
    latch_joint = cup["jointIds"].pop()
    # Static retaining hardware replaces the separately actuated latch. Existing
    # root mount relationships still attach every member in this metadata case.
    data["relationships"] = [r for r in data["relationships"] if r["id"] != latch_joint]
    for group in raw["mounts"]:
        group["relationshipIds"] = [i for i in group["relationshipIds"] if i != latch_joint]
    cup["memberIds"].append("frame")
    cup["retentionMemberIds"] = ["cup-latch"]
    cup["releaseJointId"] = cup["jointIds"][0]
    drive = next(t for t in raw["transmissions"] if t["id"] == "cup_cradle-drive")
    drive["outputs"] = [drive["outputs"][0]]; drive["stages"].pop()
    if fault == "missing-retainer": cup["retentionMemberIds"] = ["nonexistent"]
    elif fault == "wrong-release": cup["releaseJointId"] = next(m for m in raw["mechanisms"] if m["role"] == "pin_transfer")["jointIds"][0]
    report = qualify_robot(A._revision(A.AssemblySnapshot.model_validate(data)),RobotContract.model_validate(raw))
    if fault is None:
        assert report.complete_robot, report.json_data()["missing"]
        assert report.task_capability_status == "unverified"
    else:
        assert not report.complete_robot and codes(report).intersection(("CUP_RETENTION_HARDWARE","CUP_RELEASE_JOINT"))


@pytest.mark.parametrize("fault",[None,"wrong-pitch","unpowered-rear"])
def test_center_input_84_tooth_side_train_uses_actual_pitch_and_both_branches(case,fault):
    revision,raw = case
    data = revision.assembly.json_data()
    for side in ("left","right"):
        for instance in data["instances"]:
            identity = instance["id"]
            offset = 0.
            if identity == side+"-motor": offset = .0889
            for index in range(3):
                if identity == f"{side}-gear-{index}" or identity.startswith(f"{side}-shaft-{index}"):
                    offset = index*(.0889-.04)
            if identity == side+"-wheel-1": offset = 2*(.0889-.04)
            instance["transform"]["matrix"][12] += offset
        stages = []
        def edge(driver,driven,gear=False):
            item = dict(id="center-stage-"+str(len(stages)),kind="gear_mesh" if gear else "shaft",
                driver={"instanceId":side+"-"+driver,"portId":"axis"},
                driven={"instanceId":side+"-"+driven,"portId":"axis"},speedRatio=-1. if gear else 1.,evidence=EVIDENCE)
            if gear: item.update(driverTeeth=84,drivenTeeth=84,moduleM=.0889/84)
            else: item["engagementM"] = .01
            stages.append(item)
        edge("motor","shaft-1"); edge("shaft-1","gear-1")
        for index,wheel in ((0,0),(2,1)):
            edge("gear-1",f"gear-{index}",True); edge(f"gear-{index}",f"shaft-{index}"); edge(f"shaft-{index}",f"wheel-{wheel}")
        next(t for t in raw["transmissions"] if t["id"] == side+"-drive")["stages"] = stages
    snapshot = A.AssemblySnapshot.model_validate(data)
    worlds = A.world_transforms(snapshot)
    definitions = {d.id:d for d in snapshot.components}
    nodes = {n.id:n for n in snapshot.instances}
    for rel in data["relationships"]:
        def frame(instance,port_id):
            port = next(p for p in definitions[nodes[instance].component_id].ports if p.id == port_id)
            return worlds[instance].compose(port.frame)
        rel["mateTransform"] = frame(rel["parentInstanceId"],rel["parentPortId"]).inverse().compose(frame(rel["childInstanceId"],rel["childPortId"])).json_data()
    if fault == "wrong-pitch": raw["transmissions"][0]["stages"][2]["moduleM"] = .001
    elif fault == "unpowered-rear": raw["transmissions"][0]["stages"].pop()
    report = qualify_robot(A._revision(A.AssemblySnapshot.model_validate(data)),RobotContract.model_validate(raw))
    if fault is None:
        assert report.complete_robot, report.json_data()["missing"]
        assert report.transmission_ratios["left-drive"] == {"left-wheel-0/axis":-1.,"left-wheel-1/axis":-1.}
    else:
        assert not report.complete_robot and codes(report).intersection(("GEAR_PITCH_ALIGNMENT","UNPOWERED_OUTPUT"))


def test_gripper_may_mount_through_explicit_source_adapter_members(case):
    revision,raw = case
    data = revision.assembly.json_data()
    scorer = next(m for m in raw["mechanisms"] if m["role"] == "scorer")
    scorer["memberIds"].append("cross-0")
    for rel in data["relationships"]:
        if rel["childInstanceId"] == "gripper":
            rel["parentInstanceId"] = "cross-0"
            rel["parentPortId"] = "mount" if rel["kind"] == "fixed" else "axis"
            rel["mateTransform"] = A.RigidTransform.translation(0.,.45,0.).json_data()
    report = qualify_robot(A._revision(A.AssemblySnapshot.model_validate(data)),RobotContract.model_validate(raw))
    assert report.complete_robot, report.json_data()["missing"]


def integrated_gripper(case):
    """Collapse synthetic explicit tool hardware into a synthetic OEM receipt.

    This tests the metadata trust boundary only. It is not an imported VEX solid,
    current rights evidence, or proof of authentic/physical robot acceptance.
    """
    revision,raw = case
    data = revision.assembly.json_data()
    removed = {i["id"] for i in data["instances"] if i["id"].startswith("grip-")}
    data["instances"] = [i for i in data["instances"] if i["id"] not in removed]
    data["requiredInstanceIds"] = [i for i in data["requiredInstanceIds"] if i not in removed]
    data["components"] = [c for c in data["components"] if c["id"] not in removed]
    data["relationships"] = [r for r in data["relationships"] if not {r["parentInstanceId"],r["childInstanceId"]} & removed
                            and not (r["childInstanceId"] == "gripper" and r["kind"] != "fixed")]
    rel_ids = {r["id"] for r in data["relationships"]}
    for group in raw["mounts"]:
        group["memberIds"] = [i for i in group["memberIds"] if i not in removed]
        group["relationshipIds"] = [i for i in group["relationshipIds"] if i in rel_ids]
    raw["bom"] = [b for b in raw["bom"] if b["instanceId"] not in removed]
    raw["shaftSupports"] = [s for s in raw["shaftSupports"] if s["shaftId"] not in removed]
    raw["transmissions"] = [t for t in raw["transmissions"] if t["id"] != "grip-drive"]
    scorer = next(m for m in raw["mechanisms"] if m["role"] == "scorer")
    scorer["memberIds"] = [i for i in scorer["memberIds"] if i not in removed]
    scorer["jointIds"] = list(scorer["fourBar"]["jointIds"])
    scorer["transmissionIds"].remove("grip-drive")
    component = next(c for c in data["components"] if c["id"] == "gripper")
    component.update(sku="276-6010",name="Synthetic selected OEM receipt",catalogFingerprint=A.content_hash("synthetic-selected-claw-kit"))
    next(b for b in raw["bom"] if b["instanceId"] == "gripper")["catalogFingerprint"] = component["catalogFingerprint"]
    children = [dict(definitionLabel=label,definitionName=name,purpose=purpose,quantity=count,**({"teeth":teeth} if teeth else {}))
                for label,name,purpose,count,teeth in (
                    ("0:1:1:6","276-4840-000 Rev1_1","motor",1,None),
                    ("0:1:1:52","276-6010-011 Rev2_Spur01","gear",1,12),
                    ("0:1:1:47","276-6010-003 Rev6_35 Tooth","gear",2,35),
                    ("0:1:1:49","276-6010-002 Rev5","jaw",2,None),
                    ("0:1:1:28","276-4996-001 Rev1_No Threads","fastener",2,None))]
    hierarchy = [dict(id="unit-root",name="276-6010-100 Rev12_276-6010",parentId=None,matrix=list(A.RigidTransform().matrix),hasMesh=False)]
    for child in children:
        for i in range(child["quantity"]):
            hierarchy.append(dict(id="native-"+str(len(hierarchy)),name=child["definitionName"],parentId="unit-root",
                                  matrix=list(A.RigidTransform().matrix),hasMesh=True))
    common = ("id","name","sku","originKind","geometryClass","sourceUrl","sourceSha256","meshSha256","meshUrl","catalogFingerprint","geometryValidation")
    receipt = {k:component[k] for k in common}
    receipt.update(sourceSelection=dict(definitionLabel="0:1:1:45",expectedDefinitionName="276-6010-100 Rev12_276-6010"),
        boundsM=dict(min=[-.05,-.05,-.05],max=[.05,.05,.05]),sourceBoundsMm=dict(min=[-50.,-50.,-50.],max=[50.,50.,50.]),
        solidCount=8,nativeHierarchy=hierarchy,ports=[dict(id=p["id"],kind=p["kind"],positionM=p["frame"]["matrix"][12:15],
        axis=p["frame"]["matrix"][8:11],evidence=EVIDENCE) for p in component["ports"]],rightsStatus="qualified_for_declared_use",
        declaredUse="unit-test-metadata",conversion=dict(tool="CadQuery",version="unit-test",linearDeflectionMm=.05,
        angularDeflectionRad=.1,frame="Original metadata",maxBoundsErrorM=0.,displayMeshOnly=True),
        attribution=EVIDENCE,completeRobot=False,referenceOnly=False)
    prepared = PreparedComponent.model_validate(receipt)
    raw["integratedUnits"] = [dict(instanceId="gripper",componentId="gripper",catalogFingerprint=component["catalogFingerprint"],
        sourceSha256=component["sourceSha256"],definitionLabel="0:1:1:45",definitionName="276-6010-100 Rev12_276-6010",
        nativeHierarchySha256=A.content_hash([n.json_data() for n in prepared.native_hierarchy]),children=children,evidence=EVIDENCE)]
    return A._revision(A.AssemblySnapshot.model_validate(data)),raw,prepared


def test_source_bound_oem_gripper_needs_no_internal_joint_simulation(case):
    revision,raw,receipt = integrated_gripper(case)
    report = qualify_robot(revision,RobotContract.model_validate(raw),prepared_components=[receipt])
    assert report.complete_robot, report.json_data()["missing"]
    assert report.integrated_unit_counts == {"motor":1,"gear":3,"jaw":2,"fastener":2}
    assert report.integrated_units[0].instance_id == "gripper"
    assert report.task_capability_status == "unverified" and not report.physical_performance_verified
    assert not any(r.id.startswith("grip") for r in revision.assembly.relationships)
    assert qualify_robot(revision,RobotContract.model_validate(raw),prepared_components=[receipt]) == report


@pytest.mark.parametrize("fault,expected",[
    ("receipt-missing","OEM_RECEIPT_MISSING"),("fingerprint","OEM_IDENTITY_MISMATCH"),
    ("root-label","OEM_SELECTION_MISMATCH"),("whole-robot","OEM_SELECTION_MISMATCH"),
    ("hierarchy","OEM_HIERARCHY_MISMATCH"),("motor","OEM_INTERNAL_HARDWARE_MISSING"),
    ("gears","OEM_INTERNAL_HARDWARE_MISSING"),("jaws","OEM_INTERNAL_HARDWARE_MISSING"),
    ("mount","OEM_CARRIER_MOUNT_REQUIRED"),("fixture","OEM_GEOMETRY_NOT_QUALIFIED"),
    ("drive","DRIVE_TRANSMISSION_MISSING"),("fourbar","FOUR_BAR_LOOP"),
])
def test_oem_evidence_does_not_relax_identity_hardware_or_major_robot_checks(case,fault,expected):
    revision,raw,receipt = integrated_gripper(case)
    unit = raw["integratedUnits"][0]
    receipts = [receipt]
    if fault == "receipt-missing": receipts = []
    elif fault == "fingerprint": unit["catalogFingerprint"] = "f"*64
    elif fault == "root-label": unit["definitionLabel"] = "0:1:1:1"
    elif fault == "whole-robot": unit["definitionName"] = "Whole Clawbot"
    elif fault == "hierarchy": unit["nativeHierarchySha256"] = "f"*64
    elif fault == "motor": unit["children"][0]["definitionName"] = "not-a-VEX-motor"
    elif fault == "gears": unit["children"][2]["teeth"] = 34
    elif fault == "jaws": unit["children"][3]["quantity"] = 1
    elif fault == "mount":
        data = revision.assembly.json_data()
        data["relationships"] = [r for r in data["relationships"] if not (r["parentInstanceId"] == "carrier" and r["childInstanceId"] == "gripper")]
        retained = {r["id"] for r in data["relationships"]}
        raw["mounts"][0]["relationshipIds"] = [i for i in raw["mounts"][0]["relationshipIds"] if i in retained]
        revision = A._revision(A.AssemblySnapshot.model_validate(data))
    elif fault == "fixture":
        data = revision.assembly.json_data()
        next(c for c in data["components"] if c["id"] == "gripper").update(originKind="tachyon_authored",geometryClass="test_fixture")
        revision = A._revision(A.AssemblySnapshot.model_validate(data))
        receipts = [receipt.model_copy(update={"origin_kind":"tachyon_authored","geometry_class":"test_fixture"})]
    elif fault == "drive": raw["driveSides"][0]["transmissionId"] = "nonexistent"
    elif fault == "fourbar":
        bar = next(m["fourBar"] for m in raw["mechanisms"] if m["role"] == "scorer")
        bar["jointIds"][0] = bar["jointIds"][1]
    report = qualify_robot(revision,RobotContract.model_validate(raw),prepared_components=receipts)
    assert not report.complete_robot and expected in codes(report), report.json_data()["missing"]


def test_oem_record_rejects_a_boolean_shortcut_and_does_not_trust_display_rights(case):
    revision,raw,receipt = integrated_gripper(case)
    raw["integratedUnits"][0]["qualified"] = True
    with pytest.raises(ValidationError): RobotContract.model_validate(raw)
    raw["integratedUnits"][0].pop("qualified")
    public = receipt.json_data(); public["qualifiedOperations"] = ["loopback_display"]
    report = qualify_robot(revision,RobotContract.model_validate(raw),prepared_components=[public])
    assert report.complete_robot  # assembly operations still come from the revision definition
    raw["bom"].reverse()
    raw["integratedUnits"][0]["children"].reverse()
    assert qualify_robot(revision,RobotContract.model_validate(raw),prepared_components=[public]) == report
