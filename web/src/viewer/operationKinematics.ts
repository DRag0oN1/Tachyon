import { Matrix4,Quaternion,Vector3 } from 'three';
import type { ComponentDefinition } from '../api/contracts';

type Transform={matrix:number[]};
interface Edge {id:string;parentInstanceId:string;childInstanceId:string;kind:'fixed'|'revolute'|'prismatic';axis:number[]|null;limits:number[]|null;parentPortFrame:Transform;postMatrix:number[];fixedLocalMatrix?:number[]}
export interface OperationModel {
  schemaVersion:1;kind:'development_cup_kinematics';designId:string;revisionId:string;engineeringHash:string;durationS:number;
  keyframes:{timeS:number;stageId:string;jointPositions:Record<string,number>;rootTransform:Transform;worldTransforms:Record<string,number[]>;objectTransform:Transform}[];
  kinematicGraph:{rootInstanceId:string;instances:{id:string;componentId:string;parentId:string|null;placementRelationshipId:string|null}[];treeRelationships:Edge[]};
  object:{componentId:string;instanceId:string;anchor:{instanceId:string;localPointM:number[]};initialTransform:Transform;targetTransform:Transform;heldRelativeTransform:Transform};
  staticObjects:{componentId:string;instanceId:string;transform:Transform}[];
  objectComponents:ComponentDefinition[];
  events:{type:string;timeS:number}[];
  validation:{graphValid:boolean;sampleCount:number;capturePredicatePassed:boolean;scoringVerified:false;physicalPerformanceVerified:false;approachClearanceOverPinTopM:number};
  limitations:string[];
}
export interface OperationPlayback {model:OperationModel;timeS:number;playing:boolean}
const matrix=(values:number[])=>{
  if(values.length!==16||!values.every(Number.isFinite))throw new Error('Operation matrix is invalid.');
  const result=new Matrix4().fromArray(values);
  if(Math.abs(result.determinant()-1)>1e-6)throw new Error('Operation must preserve rigid geometry and scale.');
  return result;
};
export function operationPose(model:OperationModel,time:number) {
  const t=Math.max(0,Math.min(model.durationS,time));
  const endIndex=Math.max(1,model.keyframes.findIndex(f=>f.timeS>=t));
  const end=model.keyframes[endIndex],start=model.keyframes[endIndex-1];
  const amount=(t-start.timeS)/(end.timeS-start.timeS);
  const positions=Object.fromEntries(Object.entries(start.jointPositions).map(([id,value])=>[id,value+(end.jointPositions[id]-value)*amount]));
  const a=matrix(start.rootTransform.matrix),b=matrix(end.rootTransform.matrix);
  const pa=new Vector3(),pb=new Vector3(),qa=new Quaternion(),qb=new Quaternion(),sa=new Vector3(),sb=new Vector3();
  a.decompose(pa,qa,sa);b.decompose(pb,qb,sb);
  const root=new Matrix4().compose(pa.lerp(pb,amount),qa.slerp(qb,amount),new Vector3(1,1,1));
  const world=new Map<string,Matrix4>(),pending=new Map(model.kinematicGraph.instances.map(n=>[n.id,n]));
  const edges=new Map(model.kinematicGraph.treeRelationships.map(e=>[e.id,e]));
  while(pending.size){
    let progress=false;
    for(const [id,node] of pending){
      if(node.parentId===null){
        if(id!==model.kinematicGraph.rootInstanceId)throw new Error('Operation has an unexpected root.');
        world.set(id,root.clone());
      }else{
        const parent=world.get(node.parentId);if(!parent)continue;
        const edge=edges.get(node.placementRelationshipId??'');
        if(!edge||edge.childInstanceId!==id||edge.parentInstanceId!==node.parentId)throw new Error('Operation placement link is missing.');
        let local:Matrix4;
        if(edge.kind==='fixed')local=matrix(edge.fixedLocalMatrix!);
        else{
          const q=positions[edge.id],axis=new Vector3(...edge.axis as [number,number,number]);
          if(!Number.isFinite(q)||!edge.limits||q<edge.limits[0]-1e-8||q>edge.limits[1]+1e-8||Math.abs(axis.length()-1)>1e-8)throw new Error('Operation joint exceeds its declared limits.');
          const motion=edge.kind==='revolute'?new Matrix4().makeRotationAxis(axis,q):new Matrix4().makeTranslation(axis.x*q,axis.y*q,axis.z*q);
          local=matrix(edge.parentPortFrame.matrix).multiply(motion).multiply(matrix(edge.postMatrix));
        }
        world.set(id,parent.clone().multiply(local));
      }
      pending.delete(id);progress=true;
    }
    if(!progress)throw new Error('Operation placement hierarchy is disconnected.');
  }
  const capture=model.events.find(e=>e.type==='capture')!.timeS,release=model.events.find(e=>e.type==='release')!.timeS;
  let objectTransform:Matrix4,state:string;
  if(t<capture){objectTransform=matrix(model.object.initialTransform.matrix);state='free';}
  else if(t<release){
    const anchor=world.get(model.object.anchor.instanceId);
    if(!anchor)throw new Error('Operation grasp anchor is missing.');
    objectTransform=anchor.clone().multiply(new Matrix4().makeTranslation(...model.object.anchor.localPointM as [number,number,number])).multiply(matrix(model.object.heldRelativeTransform.matrix));state='held';
  }else{objectTransform=matrix(model.object.targetTransform.matrix);state='placed';}
  return {worldTransforms:Object.fromEntries([...world].map(([id,m])=>[id,m.toArray()])),objectTransform:objectTransform.toArray(),state,stage:t===0?'start':end.stageId,jointPositions:positions,timeS:t};
}
