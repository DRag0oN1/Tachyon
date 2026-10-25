import { useEffect,useRef,useState } from 'react';
import { api,errorMessage } from '../api/client';
import { parseCatalog } from '../api/contracts';
import type { DesignSession } from '../api/strategy';
import type { OperationModel,OperationPlayback } from '../viewer/operationKinematics';

export function useOperationPlayback(){
  const [playback,onChange]=useState<OperationPlayback|null>(null);
  useEffect(()=>{
    if(!playback?.playing)return;
    let frame=0;const initial=performance.now(),start=playback.timeS;
    function tick(now:number){
      const next=Math.min(playback!.model.durationS,start+(now-initial)/1000);
      onChange({model:playback!.model,timeS:next,playing:next<playback!.model.durationS});
      if(next<playback!.model.durationS)frame=requestAnimationFrame(tick);
    }
    frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);
    // Restart only on Play/Pause; each animation frame preserves its own clock.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[playback?.playing,playback?.model]);
  return [playback,onChange] as const;
}

export function OperationPanel({session,playback,onChange}:{session:DesignSession;playback:OperationPlayback|null;onChange:(p:OperationPlayback|null)=>void}){
  const [busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null);
  const key=JSON.stringify([session.designId,session.revisionId,session.accepted?.engineeringHash??null,session.candidate?.id??null]);
  const currentKey=useRef(key);currentKey.current=key;
  const pending=useRef<AbortController|null>(null);
  useEffect(()=>{
    setBusy(false);setError(null);
    return()=>{pending.current?.abort();pending.current=null;};
  },[key]);
  async function prepare(){
    if(session.candidate)return;
    pending.current?.abort();
    const controller=new AbortController(),requestKey=key;
    pending.current=controller;
    const fresh=()=>pending.current===controller&&!controller.signal.aborted&&currentKey.current===requestKey;
    setBusy(true);setError(null);
    try{
      const raw=await api.post(`/api/designs/${session.designId}/operation`,{base_revision_id:session.revisionId},controller.signal) as OperationModel;
      if(!fresh())return;
      if(raw.kind!=='development_cup_kinematics'||raw.designId!==session.designId||raw.revisionId!==session.revisionId||raw.engineeringHash!==session.accepted?.engineeringHash||!raw.validation?.graphValid||!raw.validation.capturePredicatePassed||raw.validation.physicalPerformanceVerified!==false)throw new Error('The operation does not match this accepted assembly.');
      const catalog=raw.objectComponents?parseCatalog({profile:'user_provided_local',components:raw.objectComponents,blockers:[]}):await api.catalog(controller.signal);
      if(!fresh())return;
      raw.objectComponents=catalog.components.filter(c=>[raw.object.componentId,...raw.staticObjects.map(o=>o.componentId)].includes(c.id));
      if(raw.objectComponents.length!==3)throw new Error('A required modeled object is missing.');
      onChange({model:raw,timeS:0,playing:false});
    }catch(reason){if(fresh())setError(errorMessage(reason));}finally{if(fresh()){pending.current=null;setBusy(false);}}
  }
  const stage=playback?.model.keyframes.find(f=>f.timeS>=playback.timeS)?.stageId??'start';
  const stageLabel:Record<string,string>={approach:'Approach',grip:'Grasp',lift:'Lift',translate:'Transfer',alignment:'Align',place:'Place',open:'Release',retract:'Retract'};
  return <section className="strategy-notice operation-panel" data-testid="operation-panel">
    <h3>Modeled Cup operation</h3>
    <p>Actual assembly joints · 120 mm development fixture · no contact dynamics or competition-performance claim.</p>
    <p>Assembly clearance is unqualified. Known structural intersections prevent a successful physical-operation or complete-robot claim.</p>
    {!playback?<button className="secondary-button" disabled={busy||!!session.candidate} onClick={()=>void prepare()}>{busy?'Checking modeled sequence…':'Prepare Cup operation'}</button>:<>
      <p role="status">{stage.replaceAll('_',' ')} · {playback.timeS.toFixed(1)} / {playback.model.durationS} s</p>
      <label>Operation time<input aria-label="Operation time" type="range" min="0" max={playback.model.durationS} step=".05" value={playback.timeS} onChange={e=>onChange({...playback,timeS:Number(e.target.value),playing:false})}/></label>
      <nav aria-label="Operation stages" className="operation-stages">{playback.model.keyframes.slice(1).map(frame=><button key={frame.stageId} className="text-action" aria-label={'Operation: '+(stageLabel[frame.stageId]??frame.stageId)} onClick={()=>onChange({...playback,timeS:frame.timeS,playing:false})}>{stageLabel[frame.stageId]??frame.stageId}</button>)}</nav>
      <div className="operation-buttons"><button className="secondary-button" onClick={()=>onChange({...playback,timeS:playback.timeS>=playback.model.durationS?0:playback.timeS,playing:!playback.playing})}>{playback.playing?'Pause operation':'Play operation'}</button><button className="secondary-button" onClick={()=>onChange(null)}>Restore design pose</button></div>
      <p>Grasp → lift → align over the preplaced Pin → nest → release → retract. Held-object motion is prescribed; force, friction and stability are unverified.</p>
      <details><summary>Model limitations</summary><ul>{playback.model.limitations.map((text,i)=><li key={i}>{text}</li>)}</ul></details>
    </>}
    {error&&<p role="alert">{error}</p>}
  </section>;
}
