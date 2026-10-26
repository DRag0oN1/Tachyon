import { useState } from 'react';
import type { Mode } from '../api/contracts';
import type { DesignCatalog } from '../api/designCatalog';
import { capabilityValue,readable,type ArchitectureProposal,type DesignSession,type RealizationState,type StrategySession } from '../api/strategy';
import { ArchitectureDrawing,architectureName } from '../studio/ArchitectureDrawing';
import { DockFrame } from '../studio/Mechanical';
import { Icon } from '../components/Icon';

export interface ArchitecturesPanelProps {
  session:StrategySession|null;loading:boolean;error?:string|null;mode?:Mode;
  selectedArchitectureId:string|null;selectedActionId?:string|null;realization?:RealizationState;
  onSelectArchitecture:(id:string)=>void;onRealizeArchitecture?:(id:string)=>void|Promise<void>;
  onInspectReference?:()=>void;onStrategy:()=>void;onGenerate:()=>void;available?:boolean;
  designCatalog?:DesignCatalog|null;designSessions?:Record<string,DesignSession>;onInspectAssembly?:(id:string)=>void;
}
export function designStatus(a:ArchitectureProposal,session?:DesignSession,catalog?:DesignCatalog|null){
  if(session?.accepted)return session.qualification.completeRobot?'Realized assembly':'Partial assembly';
  if(catalog?.architectures.find(row=>row.architectureId===a.id)?.recipeAvailable)return 'Authored recipe available';
  return 'Architecture only';
}
function Tradeoffs({architecture}:{architecture:ArchitectureProposal}){
  const lift=architecture.subsystems.find(s=>s.id==='scorer')?.mechanismIntent??'';
  const intake=architecture.subsystems.find(s=>s.id==='pin_intake')?.mechanismIntent??'';
  return <dl className="design-tradeoffs"><div><dt>Lift</dt><dd>{lift.includes('four_bar')?'Linked motion, with a curved tool path to qualify.':'Guided vertical motion, with carriage alignment to qualify.'}</dd></div><div><dt>Acquire</dt><dd>{intake.includes('roller')?'Roller feed needs controlled contact and a timed handoff.':'Jaw pickup needs alignment and coordinated grip timing.'}</dd></div><div><dt>Verify</dt><dd>Clearance, retention and loaded performance remain unverified.</dd></div></dl>;
}
export function ArchitecturesPanel({session,loading,error,mode='simple',selectedArchitectureId,selectedActionId,realization={state:'idle'},onSelectArchitecture,onRealizeArchitecture,onStrategy,onGenerate,available=true,designCatalog,designSessions={},onInspectAssembly}:ArchitecturesPanelProps){
  const [showRequirements,setShowRequirements]=useState(false);
  if(!session)return <div className="design-explorer"><span className="eyebrow">MECHANICAL DESIGN / 01—02</span><h2>{loading?'Preparing the design bench…':'Start with a strategy.'}</h2><p>{loading?'Running the saved policy and loading its two mechanical proposals.':'Create Robot runs the learned strategy as context. No separate strategy visit is needed.'}</p>{error&&<p role="alert" className="strategy-notice">{error}</p>}<button className="primary-button" disabled={loading||!available} onClick={onGenerate}>{loading?'Preparing designs…':'Create Robot'}<Icon name="arrow"/></button></div>;
  const selected=session.architectures.find(a=>a.id===selectedArchitectureId);
  const current=selected?designSessions[selected.id]:undefined;
  const availability=designCatalog?.architectures.find(a=>a.architectureId===selected?.id);
  const loaded=realization.state==='loaded'&&realization.architectureId===selected?.id?realization.result:undefined;
  const working=realization.state==='loading'&&realization.architectureId===selected?.id;
  const canBuild=availability?.recipeAvailable??true;
  return <div className="design-explorer">
    <header className="design-heading"><span className="eyebrow">ONE LEARNED PLAN / TWO MECHANICAL APPROACHES</span><h2>Choose your machine.</h2><p>Different mechanisms. The same learned strategy.</p></header>
    {error&&<p role="alert" className="strategy-notice">{error}</p>}
    <div className="architecture-options design-choices" aria-label="Engineering alternatives">{session.architectures.map((a,index)=><button className="design-choice" key={a.id} aria-pressed={a.id===selectedArchitectureId} onClick={()=>{setShowRequirements(false);onSelectArchitecture(a.id);}}><span className="design-choice-id">DESIGN {String(index+1).padStart(2,'0')}<span>{a.id===selectedArchitectureId?'IN VIEW':'SELECT'}</span></span><ArchitectureDrawing architecture={a} compact/><strong>{architectureName(a)}</strong><span className="design-choice-state"><i/>{designStatus(a,designSessions[a.id],designCatalog)}</span></button>)}</div>
    {selected&&<>
      <DockFrame className="design-detail" label={`DESIGN ${String(session.architectures.indexOf(selected)+1).padStart(2,'0')}`} code="MECHANISM INTENT">
        <div className="design-title-row"><h3>{architectureName(selected)}</h3><span className="design-state">{designStatus(selected,current??loaded,designCatalog)}</span></div>
        <ArchitectureDrawing architecture={selected} activeActionId={selectedActionId}/>
        <p className="drawing-caption">Conceptual arrangement from this proposal. Not CAD or a verified mechanical layout.</p>
        <div className="design-primary-actions">{current?.accepted?<button className="primary-button" onClick={()=>onInspectAssembly?.(selected.id)}>Inspect assembly<Icon name="arrow"/></button>:canBuild?<button className="primary-button" disabled={!onRealizeArchitecture||working} onClick={()=>onRealizeArchitecture?.(selected.id)}>{working?'Assembling registered parts…':'Assemble local recipe'}<Icon name="parts"/></button>:<button className="primary-button" onClick={()=>setShowRequirements(v=>!v)}>{showRequirements?'Hide build requirements':'Review build requirements'}<Icon name="parts"/></button>}<button className="text-action" onClick={onStrategy}>Open strategy<Icon name="arrow"/></button></div>
        {working&&<p role="status" className="design-progress">Checking source geometry, placements and registered connections.</p>}
        {realization.state==='failed'&&realization.architectureId===selected.id&&<p role="alert" className="strategy-notice">{realization.message}</p>}
        <p className="design-provenance">{current?.accepted?'Constructed from a preauthored component recipe. Source provenance and clearance warnings remain in the CAD workspace.':!availability?'Recipe availability is unknown. The local engine will check the recipe and return construction results or missing requirements.':canBuild?'Builds a registered, authored assembly recipe using local component geometry. This is not an unrestricted robot generator.':'This design is a proposal. No assembled CAD recipe is available for it in this catalog.'}</p>
      </DockFrame>
      <section className="design-mechanisms"><h3>Inside this machine</h3><ol>{selected.subsystems.map((s,i)=><li key={s.id}><span className="mechanism-pin">{String(i+1).padStart(2,'0')}</span><div><strong>{readable(s.id)}</strong><span>{readable(s.mechanismIntent)}</span></div></li>)}</ol></section>
      <section className="design-support"><h3>Strategy goals</h3><p>{session.spec.scoringPriorities.slice(0,2).map(p=>readable(p.objective)).join(' · ')}</p><Tradeoffs architecture={selected}/></section>
      {(showRequirements||loaded?.status==='blocked')&&<section className="strategy-notice" role="status"><h3>Assembly still required</h3><p>The schematic remains available while these engineering requirements are unresolved.</p><ul>{(loaded?.missing??[]).map((m,i)=><li key={i}>{readable(m.role)}: {m.message}</li>)}{selected.qualificationRequired.slice(0,5).map(q=><li key={q}>{q}</li>)}</ul></section>}
      <details className="strategy-evidence" open={mode==='advanced'}><summary>Advanced design analysis</summary><h4>Capability requirements</h4><dl className="strategy-metrics">{Object.entries(selected.capabilityConstraints.targets).map(([k,v])=><div key={k}><dt>{readable(k)}</dt><dd>{capabilityValue(k,v)}</dd></div>)}</dl><p>Targets are abstract engineering inputs, not measured robot capabilities.</p><h4>Subsystem sizing and actuation intents</h4>{selected.subsystems.map(s=><section key={s.id}><h4>{readable(s.id)}</h4><dl>{Object.entries({...s.layoutIntent,...s.actuationIntent}).filter(([,v])=>['number','boolean','string'].includes(typeof v)).map(([k,v])=><div key={k}><dt>{readable(k)}</dt><dd>{String(v)}</dd></div>)}</dl></section>)}<h4>Connection intents</h4><ul>{selected.attachmentAndJointIntents.map((j,i)=><li key={i}>{readable(j.parentSubsystemID)} → {readable(j.childSubsystemID)}: {j.jointIntent} · {j.mountZoneIntent}</li>)}</ul><h4>Qualification requirements</h4><ul>{selected.qualificationRequired.map(q=><li key={q}>{q}</li>)}</ul><h4>Engineering assumptions</h4><ul>{selected.engineeringAssumptions.map(q=><li key={q}>{q}</li>)}</ul><p>These are the two saved bridge proposals. Additional architecture generation is not supported by the current contract.</p></details>
    </>}
  </div>;
}
