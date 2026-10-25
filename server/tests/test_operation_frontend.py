"""Cross-check browser FK against the existing backend on original metadata.

No source CAD or physical claims: this compares the two runtime representations
used for the visible operation, including placement parents and held objects.
"""
import json
from pathlib import Path
import subprocess

from tachyon.operation import build_operation
from test_operation import operation_case


def test_browser_joint_interpolation_matches_authoritative_keyframe_poses():
    model=build_operation(*operation_case())
    script=r'''
import {build} from './web/node_modules/esbuild/lib/main.js';
let input='';for await(const chunk of process.stdin)input+=chunk;
const model=JSON.parse(input);
const result=await build({entryPoints:['web/src/viewer/operationKinematics.ts'],bundle:true,platform:'node',format:'esm',write:false,logLevel:'silent'});
const {operationPose}=await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));
let maximum=0;for(const frame of model.keyframes){
 const observed=operationPose(model,frame.timeS);
 for(const [id,expected] of Object.entries(frame.worldTransforms))expected.forEach((x,i)=>{maximum=Math.max(maximum,Math.abs(x-observed.worldTransforms[id][i]));});
 frame.objectTransform.matrix.forEach((x,i)=>{maximum=Math.max(maximum,Math.abs(x-observed.objectTransform[i]));});
}
let sampledObjectError=0;for(const sample of model.validation.samples){
 const observed=operationPose(model,sample.timeS);
 sample.objectTransform.matrix.forEach((x,i)=>{sampledObjectError=Math.max(sampledObjectError,Math.abs(x-observed.objectTransform[i]));});
}
const invalid=structuredClone(model);invalid.kinematicGraph.treeRelationships.pop();let rejected=false;try{operationPose(invalid,4);}catch{rejected=true;}
process.stdout.write(JSON.stringify({maximum,sampledObjectError,rejected}));
'''
    result=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(model),text=True,
        cwd=Path(__file__).resolve().parents[2],capture_output=True,check=True,timeout=30)
    report=json.loads(result.stdout)
    assert report['maximum']<1e-9
    assert report['sampledObjectError']<1e-9
    assert report['rejected']
