"""Read-only integration audit using original in-memory mechanical metadata.

No user CAD, rights, imported solids or trained artifacts are used. A closed
parallelogram here proves graph mathematics only, never authentic VEX acceptance.
Regression cases cover independently reproduced integration audit findings.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess

import pytest

from tachyon import assemblies as A, bindings as B, realization as R
from tachyon.errors import TachyonError
from tachyon.models import Model, PreparedComponent
from tachyon.robot_qualification import RobotContract


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = "Original audit metadata; no authentic CAD or physical acceptance"


def case():
    def definition(identity, points):
        return A.ComponentDefinition(id=identity,name="Original non-VEX audit "+identity,source_url="urn:audit:"+identity,
            source_sha256="1"*64,mesh_sha256="2"*64,mesh_url="urn:no-asset",catalog_fingerprint=A.content_hash(identity),
            origin_kind="tachyon_authored",geometry_class="test_fixture",declared_use="assembly_placement",
            qualified_operations=("assembly_placement",),geometry_validation=A.GeometryValidation(status="valid",native_brep_valid=True,qualified_for_robot_generation=True),
            ports=tuple(A.AttachmentPort(id=k,kind="mount" if k.startswith("mount") else "revolute",
                frame=A.RigidTransform.translation(*p),evidence=EVIDENCE) for k,p in points.items()))
    definitions = [definition("base",{"front":(0.,0.,0.),"rear":(0.,.0762,0.)}),
        definition("link",{"pivot":(0.,0.,0.),"tip":(.2921,0.,0.)}),
        definition("carrier",{"front":(0.,0.,0.),"rear":(0.,.0762,0.),"mount-tool":(0.,.025,0.),"mount-cup":(.04,0.,0.),"mount-stack":(-.04,0.,0.)}),
        definition("tool",{"mount":(0.,0.,0.)}),definition("cup",{"mount":(0.,0.,0.)}),
        definition("stack",{"mount":(0.,0.,0.)})]
    instances = [dict(id=i,componentId=c,subsystemId=s,parentId=p) for i,c,s,p in (
        ("base","base","chassis",None),("link-a","link","scorer","base"),("link-b","link","scorer","base"),
        ("carrier","carrier","scorer","link-a"),("tool","tool","scorer","carrier"),
        ("cup","cup","cup_cradle","carrier"),("stack","stack","stack_interface","carrier"))]
    relationships = []
    for identity,parent,pp,child,cp,moving in (
        ("front-input","base","front","link-a","pivot",("link-a","carrier","tool","cup","stack")),
        ("rear-input","base","rear","link-b","pivot",("link-b",)),
        ("front-carrier","link-a","tip","carrier","front",("carrier","tool","cup","stack")),
        ("rear-closure","link-b","tip","carrier","rear",("carrier","tool","cup","stack"))):
        relationships.append(A.Relationship(id=identity,parent_instance_id=parent,parent_port_id=pp,child_instance_id=child,
            child_port_id=cp,kind="revolute",axis=(0.,0.,1.),limits=(-1.5,1.5),moving_member_ids=moving).json_data())
    for child in ("tool","cup","stack"):
        relationships.append(A.Relationship(id=child+"-mount",parent_instance_id="carrier",parent_port_id="mount-"+child,
            child_instance_id=child,child_port_id="mount").json_data())
    configs = {}
    for name,theta in (("lower",-.2),("raised",.85)):
        configs[name] = dict(jointPositions={"front-input":theta,"rear-input":theta,"front-carrier":-theta,"rear-closure":-theta},
            reach=dict(actionId="place_alliance",anchorId="tool",worldPointM=[.2921*math.cos(theta),.1397+.2921*math.sin(theta)+.025,0.],evidence=EVIDENCE))
    roles = {role:sorted({n["componentId"] for n in instances if n["subsystemId"]==role}) for role in {n["subsystemId"] for n in instances}}
    raw = dict(id="audit-parallelogram",alternative="A",roleComponentIds=roles,
        portFrames={d.id:dict(sourceSha256=d.source_sha256,ports=[p.json_data() for p in d.ports]) for d in definitions},
        template=dict(rootInstanceId="base",rootTransform=A.RigidTransform.translation(0.,.1397,0.).json_data(),instances=instances,
            subsystems=[dict(id=r,name=r) for r in sorted(roles)],relationships=relationships),
        actions=[dict(actionId="place_alliance",subsystemId="scorer",instanceIds=["link-a","link-b","carrier","tool"],
            jointIds=["front-input","rear-input","front-carrier","rear-closure"],anchors=[dict(id="tool",instanceId="tool")])],
        configurations=configs,editGroup=dict(id="scoring-assembly",driverJointId="front-input",
            members=["link-a","link-b","carrier","tool","cup","stack"],
            coupling=[dict(jointId=i,ratio=ratio) for i,ratio in (("front-input",1.),("rear-input",1.),("front-carrier",-1.),("rear-closure",-1.))]))
    context = R.ArchitectureContext(proposal=dict(id="audit-architecture-A",alternative="A",subsystems=[dict(id=r) for r in roles],
        requirements=[],attachmentAndJointIntents=[],qualificationRequired=[],bindingIntent=dict(actions=[dict(action="place_alliance",subsystemIDs=["scorer"])])),
        spec=dict(id="audit-strategy",competition=dict(id="audit-competition"),behavior=dict(inference=dict(actionNames=["place_alliance"])),
            capabilityRequirements=dict(targets=dict(reachM=.352))))
    return A.AssemblyService(definitions),context,raw


def reply_case(raw=None):
    service,context,original = case()
    recipe = R.Recipe.model_validate(raw or original)
    design_id = "audit-design"
    lower = R.build_pose(service,recipe,design_id,"lower")
    upper = R.build_pose(service,recipe,design_id,"raised",lower.id)
    data = dict(designId=design_id,accepted=lower.json_data(),bindings=R._links(context,recipe,lower).json_data(),
        candidate=upper.json_data(),candidateBindings=R._links(context,recipe,upper).json_data(),undo=[])
    return service,context,recipe,data


def minimal_robot(raw):
    return dict(bom=[dict(instanceId=n["id"],componentId=n["componentId"],catalogFingerprint=A.content_hash(n["componentId"]),
        purpose="gripper" if n["id"]=="tool" else "structure",evidence=EVIDENCE) for n in raw["template"]["instances"]])


def test_legacy_recipe_json_and_hash_are_identical_without_new_optional_fields():
    _,_,raw = case(); raw.pop("editGroup")
    class OldPorts(Model):
        source_sha256: str
        ports: tuple[A.AttachmentPort,...]
    class OldRecipe(Model):
        id: str
        alternative: str
        role_component_ids: dict[str,tuple[str,...]]
        port_frames: dict[str,OldPorts]
        template: R.AssemblyTemplate
        actions: tuple[B.ActionBinding,...] = ()
        configurations: dict[str,R.Pose]
    legacy = OldRecipe.model_validate(raw).json_data()
    for explicit_none in (False,True):
        candidate = deepcopy(raw)
        if explicit_none:
            candidate.update(robot=None,editGroup=None)
            for frames in candidate["portFrames"].values(): frames["catalogFingerprint"] = None
        current = R.Recipe.model_validate(candidate)
        assert current.json_data() == legacy
        assert A.content_hash(current.json_data()) == A.content_hash(legacy)
        assert json.loads(current.model_dump_json(by_alias=True)) == legacy


def test_closed_parallelogram_group_carries_cup_and_stack_through_both_poses():
    service,context,raw = case(); recipe = R.Recipe.model_validate(raw)
    assert R.edit_qualification(service,context,recipe,"audit-design") == (True,[])
    lower,upper = [R.build_pose(service,recipe,"audit-design",pose) for pose in ("lower","raised")]
    worlds = [A.world_transforms(r.assembly) for r in (lower,upper)]
    moved = {i for i in worlds[0] if worlds[0][i] != worlds[1][i]}
    assert moved == set(recipe.edit_group.members)
    assert {n.subsystem_id for n in lower.assembly.instances if n.id in moved} == {"scorer","cup_cradle","stack_interface"}
    assert all(service.validate(r).graph_valid for r in (lower,upper))


@pytest.mark.parametrize("fault",["no-group","missing-cup","extra-root","bad-coupling","drive-joint"])
def test_coupled_edit_cannot_hide_missing_members_bad_coupling_or_drive_changes(fault):
    service,context,raw = case()
    if fault == "no-group": raw.pop("editGroup")
    elif fault == "missing-cup": raw["editGroup"]["members"].remove("cup")
    elif fault == "extra-root": raw["editGroup"]["members"].append("base")
    elif fault == "bad-coupling": raw["editGroup"]["coupling"][1]["ratio"] = 2.
    else:
        raw["roleComponentIds"]["drive"] = ["base"]
        raw["template"]["subsystems"].append(dict(id="drive",name="Independent drive audit"))
        raw["template"]["instances"].append(dict(id="wheel",componentId="base",subsystemId="drive",parentId="base"))
        raw["template"]["relationships"].append(A.Relationship(id="wheel-spin",parent_instance_id="base",parent_port_id="front",
            child_instance_id="wheel",child_port_id="front",kind="revolute",axis=(0.,0.,1.),limits=(-1.,1.),moving_member_ids=("wheel",)).json_data())
        for key in raw["configurations"]: raw["configurations"][key]["jointPositions"]["wheel-spin"] = -.2 if key=="lower" else .85
    ok,gaps = R.edit_qualification(service,context,R.Recipe.model_validate(raw),"audit-design")
    assert not ok
    assert gaps[0]["code"] == ("INVALID_JOINT_COUPLING" if fault=="bad-coupling" else "EDIT_SCOPE_VIOLATION")


def selected_receipt():
    _,_,raw = case()
    ports = raw["portFrames"]["base"]["ports"]
    data = dict(id="base",name="Original selected audit receipt",sku=None,originKind="tachyon_authored",geometryClass="test_fixture",
        sourceUrl="urn:audit:base",sourceSha256="1"*64,meshSha256="2"*64,meshUrl="urn:no-asset",catalogFingerprint=A.content_hash("base"),
        boundsM=dict(min=[0.,0.,0.],max=[1.,1.,1.]),sourceBoundsMm=dict(min=[0.,0.,0.],max=[1000.,1000.,1000.]),
        solidCount=1,nativeHierarchy=[],ports=[dict(id=p["id"],kind=p["kind"],positionM=p["frame"]["matrix"][12:15],axis=[0.,0.,1.],evidence=EVIDENCE) for p in ports],
        rightsStatus="qualified_for_declared_use",declaredUse="audit",conversion=dict(tool="CadQuery",version="audit",linearDeflectionMm=.05,
            angularDeflectionRad=.1,frame="Original metadata",maxBoundsErrorM=0.,displayMeshOnly=True),attribution=EVIDENCE,completeRobot=False,
        sourceSelection=dict(definitionLabel="0:1:1:2",expectedDefinitionName="original-audit-part"))
    return PreparedComponent.model_validate(data),raw["portFrames"]["base"]


def test_same_source_selected_ports_need_the_exact_catalog_fingerprint():
    receipt,raw = selected_receipt()
    with pytest.raises(TachyonError,match="fingerprint"):
        R._measured_definition(receipt,R.MeasuredPorts.model_validate(raw))
    raw["catalogFingerprint"] = receipt.catalog_fingerprint
    assert R._measured_definition(receipt,R.MeasuredPorts.model_validate(raw)).catalog_fingerprint == receipt.catalog_fingerprint
    # Same source bytes, same port origins/axes, different selected definition.
    other = receipt.model_copy(update={"catalog_fingerprint":"f"*64})
    with pytest.raises(TachyonError) as caught:
        R._measured_definition(other,R.MeasuredPorts.model_validate(raw))
    assert caught.value.code == "STALE_PORT_FRAMES"


def test_endpoint_height_and_both_qualification_reports_use_exact_revisions():
    _,_,raw = case(); raw["robot"] = minimal_robot(raw)
    service,context,recipe,data = reply_case(raw)
    result = object.__new__(R.RealizationService)._reply(data,context,recipe,service,[])
    q = result["qualification"]
    assert q["reach"]["heightM"] < .352 < q["availableEndpointHeightM"]
    assert "MODELED_REACH_TARGET_UNMET" not in {m["code"] for m in result["missing"]}
    for key,revision_key in (("robotReport","accepted"),("candidateRobotReport","candidate")):
        assert q[key]["revisionId"] == data[revision_key]["id"]
        assert q[key]["engineeringHash"] == data[revision_key]["engineeringHash"]
        assert not q[key]["completeRobot"]
    assert result["status"] == "partial" and not q["completeRobot"]
    assert "TEST_FIXTURE_ONLY" in {m["code"] for m in result["missing"]}


def test_invalid_optional_raised_pose_preserves_the_accepted_inspectable_revision():
    _,_,raw = case(); raw["robot"] = minimal_robot(raw)
    service,context,recipe,data = reply_case(raw)
    raw["configurations"]["raised"]["jointPositions"]["rear-input"] += .05
    recipe = R.Recipe.model_validate(raw)
    data.update(candidate=None,candidateBindings=None)
    assert not R.edit_qualification(service,context,recipe,"audit-design")[0]
    result = object.__new__(R.RealizationService)._reply(data,context,recipe,service,[])
    assert result["accepted"]["id"] == data["accepted"]["id"] and result["status"] == "partial"


@pytest.fixture(scope="module")
def frontend_probe():
    """Bundle current TS into memory. No frontend files or generated files written."""
    script = r'''
import {build} from './web/node_modules/esbuild/lib/main.js';
const result=await build({entryPoints:['web/src/api/strategy.ts'],bundle:true,platform:'node',format:'esm',write:false,logLevel:'silent'});
const {parseDesignSession}=await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));
const matrix=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
const revision=(id,hash)=>({id,parentRevisionId:null,engineeringHash:hash,assembly:{designId:'audit',configurationId:'lower',units:'m',upAxis:'Y',matrixLayout:'column-major',instances:[{id:'part',componentId:'part',subsystemId:'scorer',parentId:null,transform:{matrix}}],subsystems:[{id:'scorer',name:'Audit metadata'}]}});
const base={designId:'audit',architectureId:'audit-A',strategyId:'audit-strategy',status:'ready',missing:[],canEdit:false,revisionId:'accepted',accepted:revision('accepted','a'.repeat(64)),candidate:revision('candidate','b'.repeat(64)),bindings:null,candidateBindings:null,worldTransforms:{part:matrix},candidateWorldTransforms:{part:matrix},components:[{id:'part',name:'Audit metadata only',sku:'276-0000',originKind:'manufacturer_cad',geometryClass:'verified_imported_component',sourceUrl:'https://www.vexrobotics.com/unit-test',sourceSha256:'c'.repeat(64),meshSha256:'d'.repeat(64),meshUrl:'/api/assets/'+ 'd'.repeat(64)+'.glb',boundsM:{min:[0,0,0],max:[1,1,1]},solidCount:1,rightsStatus:'qualified_for_declared_use',ports:[]}],qualification:{completeRobot:true,hardwareQualified:true,physicalPerformanceVerified:false,robotReport:{revisionId:'accepted',engineeringHash:'a'.repeat(64),completeRobot:true},candidateRobotReport:{revisionId:'candidate',engineeringHash:'b'.repeat(64),completeRobot:true}},plan:{}};
const cases={valid:base,staleAccepted:structuredClone(base),staleCandidate:structuredClone(base),fixture:structuredClone(base)};
cases.staleAccepted.qualification.robotReport.revisionId='stale';
cases.staleCandidate.qualification.candidateRobotReport.revisionId='stale';
cases.fixture.components[0].geometryClass='test_fixture';cases.fixture.components[0].originKind='tachyon_authored';cases.fixture.qualification.testFixtureOnly=true;
const output={};for(const [name,value] of Object.entries(cases)){try{parseDesignSession(value);output[name]=true;}catch{output[name]=false;}}
process.stdout.write(JSON.stringify(output));
'''
    completed = subprocess.run(["node","--input-type=module","-e",script],cwd=ROOT,text=True,capture_output=True,check=True,timeout=30)
    return json.loads(completed.stdout)


def test_frontend_ready_guard_accepts_metadata_and_rejects_stale_accepted_report(frontend_probe):
    assert frontend_probe["valid"] and not frontend_probe["staleAccepted"]


def test_frontend_rejects_stale_candidate_qualification(frontend_probe):
    assert not frontend_probe["staleCandidate"]


def test_frontend_rejects_ready_fixture_claims(frontend_probe):
    assert not frontend_probe["fixture"]
