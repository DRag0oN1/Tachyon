import { useEffect,useLayoutEffect,useState } from 'react';
import { useThree } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import { Box3,Group,Matrix4,PerspectiveCamera,Vector3 } from 'three';
import { disposeScene,loadComponent } from './loadComponent';
import { applyDesignPose,type DesignSceneGraph,type DesignSceneSession } from './designSceneGraph';
import { frameCamera } from './inspection';
import { operationPose,type OperationPlayback } from './operationKinematics';

export function OperationScene({graph,session,playback}:{graph:DesignSceneGraph;session:DesignSceneSession;playback:OperationPlayback}){
  const {invalidate,gl,camera,size}=useThree();
  const controls=useThree(s=>s.controls) as unknown as {target:Vector3;update:()=>void;minDistance:number;maxDistance:number}|null;
  const [objects,setObjects]=useState<Group|null>(null),[error,setError]=useState<string|null>(null);
  const model=playback.model;
  useEffect(()=>{
    let group:Group|null=null;const abort=new AbortController();setError(null);
    (async()=>{
      group=new Group();group.name='modeled-operation-objects';
      for(const c of model.objectComponents){
        const loaded=await loadComponent(c,abort.signal);
        if(abort.signal.aborted){disposeScene(loaded.scene);return;}
        loaded.scene.name=c.id;group.add(loaded.scene);
      }
      setObjects(group);invalidate();
    })().catch(e=>{if(!abort.signal.aborted)setError(e instanceof Error?e.message:'Operation geometry failed to load');});
    return()=>{abort.abort();if(group)disposeScene(group);setObjects(null);applyDesignPose(graph,session);for(const key of ['operationStage','operationObjectState','operationObjectMatrix','operationLeftJawMatrix','operationTime','operationObjectCount','operationError'])delete gl.domElement.dataset[key];invalidate();};
    // Source object geometry is immutable across playback frames.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[model,graph]);
  useLayoutEffect(()=>{
    if(!objects)return;
    try{
      const revision=session.accepted as {id?:string;engineeringHash?:string}|null;
      if(session.candidate||session.designId!==model.designId||session.revisionId!==model.revisionId||revision?.id!==model.revisionId||revision.engineeringHash!==model.engineeringHash)
        throw new Error('The operation belongs to an earlier design revision. Restore the design pose and prepare it again.');
      const pose=operationPose(model,playback.timeS);
      applyDesignPose(graph,{...session,candidate:null,worldTransforms:pose.worldTransforms});
      for(const object of model.staticObjects){
        const node=objects.getObjectByName(object.componentId);if(!node)throw new Error('Operation field geometry is missing.');
        node.matrixAutoUpdate=false;node.matrix.fromArray(object.transform.matrix);
      }
      const cup=objects.getObjectByName(model.object.componentId);if(!cup)throw new Error('Modeled Cup geometry is missing.');
      cup.matrixAutoUpdate=false;cup.matrix.fromArray(pose.objectTransform);objects.updateMatrixWorld(true);
      gl.domElement.dataset.operationStage=pose.stage;gl.domElement.dataset.operationObjectState=pose.state;
      gl.domElement.dataset.operationObjectMatrix=JSON.stringify(cup.matrixWorld.toArray());
      gl.domElement.dataset.operationLeftJawMatrix=JSON.stringify(graph.instances.get('cup-left-jaw')!.matrixWorld.toArray());
      gl.domElement.dataset.operationTime=String(pose.timeS);gl.domElement.dataset.operationObjectCount='3';
      invalidate();
    }catch(e){setError(e instanceof Error?e.message:'Operation pose failed');}
  },[objects,model,playback.timeS,graph,session,gl,invalidate]);
  useEffect(()=>{
    if(!objects||!(camera instanceof PerspectiveCamera))return;
    const bounds=new Box3().setFromObject(graph.scene,true).union(new Box3().setFromObject(objects,true));
    const definitions=new Map(session.components.map(c=>[c.id,c]));
    // Frame the whole prescribed path, not merely its lowered first pose.
    for(const frame of model.keyframes)for(const node of model.kinematicGraph.instances){
      const c=definitions.get(node.componentId),transform=frame.worldTransforms[node.id];
      if(c&&transform)bounds.union(new Box3(new Vector3(...c.boundsM.min),new Vector3(...c.boundsM.max)).applyMatrix4(new Matrix4().fromArray(transform)));
    }
    const fit=frameCamera(camera,bounds,size,new Vector3(1,.7,1),bounds);
    if(controls){controls.target.copy(fit.center);controls.minDistance=fit.minDistance;controls.maxDistance=fit.maxDistance;controls.update();}
    invalidate();
    // Fit once when actual object assets have loaded; preserve manual orbit during playback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[objects]);
  useEffect(()=>{if(error)gl.domElement.dataset.operationError=error;else delete gl.domElement.dataset.operationError;},[error,gl]);
  return <>{objects&&!error&&<primitive object={objects} dispose={null}/>}{error&&<Html center><p className="strategy-notice" role="alert">Modeled operation unavailable: {error}. Restore the design pose to continue inspecting.</p></Html>}</>;
}
