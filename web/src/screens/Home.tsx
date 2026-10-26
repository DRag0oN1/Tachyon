import { useState } from 'react';
import type { Capabilities,Catalog } from '../api/contracts';
import type { DesignCatalog } from '../api/designCatalog';
import { Icon } from '../components/Icon';
import { OVERRIDE_MANUAL_URL,type StrategyStatus } from '../api/strategy';
import { BeamGraphic } from '../studio/Mechanical';

export function Home({catalog,capabilities,strategyStatus,strategyLoading=false,generating=false,onGenerateStrategy,onCreateRobot,strategyError,onRetryStrategy,designCatalog,onOpenSavedDesign}:{
  catalog:Catalog|null;capabilities:Capabilities|null;onInspect:()=>void;
  strategyStatus?:StrategyStatus|null;strategyLoading?:boolean;generating?:boolean;
  onGenerateStrategy?:()=>void;onCreateRobot?:()=>void;strategyError?:string|null;onRetryStrategy?:()=>void;
  designCatalog?:DesignCatalog|null;onOpenSavedDesign?:(id:string)=>void;
}){
  const [competitionOpen,setCompetitionOpen]=useState(false);
  const available=strategyStatus?.available===true;
  const reason=strategyLoading?'Connecting to the saved strategy policy…':strategyStatus?.reason??'Connect the local strategy service to begin.';
  return <div className="home-studio">
    <div className="home-station-line"><span className="eyebrow">TACHYON / ROBOTICS CREATION STUDIO</span><span className="station-state"><i/>{catalog?.components.length?'LOCAL COMPONENTS CONNECTED':'LOCAL WORKSPACE'}</span></div>
    <div className="home-studio-grid">
      <section className="home-intro">
        <div className="competition-switcher"><button className="competition-trigger" aria-expanded={competitionOpen} onClick={()=>setCompetitionOpen(v=>!v)}><span className="competition-marker">V5</span><span><small>COMPETITION</small><strong>Override <span>2026—27</span></strong></span><Icon name="arrow" size={15}/></button>{competitionOpen&&<div className="competition-info"><strong>Override · pinned manual v2.1</strong><p>The current learned policy supports this bounded Override scenario. Other rulebook workflows are not available yet.</p><a href={OVERRIDE_MANUAL_URL} target="_blank" rel="noreferrer">Inspect the official manual ↗</a></div>}</div>
        <h2>Make your<br/><em>next move.</em></h2>
        <p className="studio-intro">Understand the game.<br/>Find the mechanism. Build the machine.</p>
        <div className="home-process" aria-label="Studio workflow"><span>STRATEGY</span><i/><span>DESIGN</span><i/><span>ASSEMBLY</span></div>
        <p className="home-domain">Learned in abstract simulation.<br/>Engineered and verified separately.</p>
      </section>
      <div className="studio-entry-modules">
        <button className="entry-module entry-strategy" aria-label="Generate Strategy" disabled={!available||generating||!onGenerateStrategy} onClick={onGenerateStrategy}><div className="entry-module-copy"><span className="entry-module-index">01 / PLAYBOOK</span><h3>Generate<br/>Strategy</h3><p>Turn learned game decisions into a visual plan.</p><span className="module-action">OPEN THE PLAYBOOK <Icon name="arrow"/></span></div><BeamGraphic kind="strategy"/></button>
        <button className="entry-module entry-robot" aria-label="Create Robot" disabled={!available||generating||!onCreateRobot} onClick={onCreateRobot}><div className="entry-module-copy"><span className="entry-module-index">02 / DESIGN BENCH</span><h3>Create<br/>Robot</h3><p>Explore two mechanical approaches. Inspect the available assembly.</p><span className="module-action">ENTER THE STUDIO <Icon name="arrow"/></span></div><BeamGraphic kind="robot"/></button>
        {(generating||!available)&&<p className="studio-connection" role="status">{generating?'Preparing your studio from the saved policy…':reason}</p>}
      </div>
    </div>
    {strategyError&&<div role="alert" className="strategy-notice"><p>{strategyError}</p>{onRetryStrategy&&<button className="secondary-button" onClick={onRetryStrategy}>Retry strategy connection</button>}</div>}
    <section className="saved-builds"><div className="saved-builds-heading"><span className="eyebrow">SAVED LOCAL BUILDS</span><span>{catalog?.components.length??0} catalog definitions</span></div>{designCatalog?.saved.length?<div className="saved-builds-rail">{designCatalog.saved.filter(s=>s.revisionId).slice(0,3).map(s=><button key={s.designId} onClick={()=>onOpenSavedDesign?.(s.designId)} disabled={!onOpenSavedDesign||generating}><Icon name="parts"/><span><strong>Design {designCatalog.architectures.find(a=>a.architectureId===s.architectureId)?.alternative==='B'?'02':'01'}</strong><small>Saved assembly{ s.hasCandidate?' · pending preview':''} · recheck on open</small></span><Icon name="arrow"/></button>)}</div>:<p className="empty-saved">Your saved assemblies will appear here after local construction.</p>}</section>
    <details className="home-system-notes"><summary>Workspace availability</summary><p>Strategy runs the existing trained PPO policy. Design construction uses registered component recipes; it does not synthesize unrestricted new robot geometry.</p><p>{capabilities?.reasons.join(' ')||'Imported geometry and source permissions are checked by the local CAD pipeline.'}</p></details>
  </div>;
}
