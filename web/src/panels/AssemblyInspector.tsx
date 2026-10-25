import { readable, type DesignSession } from '../api/strategy';
import { geometryLabel } from '../api/contracts';
import { SUBSYSTEM_COLORS } from '../viewer/subsystemPalette';

export function AssemblyInspector({session,selectedId,onSelect,onSource,colorSubsystems=false,onColorSubsystems}:{session:DesignSession;selectedId:string|null;onSelect:(id:string)=>void;onSource:(componentId:string)=>void;colorSubsystems?:boolean;onColorSubsystems?:()=>void}) {
  const revision=session.candidate??session.accepted;
  if (!revision) return null;
  const nodes=revision.assembly.instances;
  const definitions=new Map(session.components.map(c=>[c.id,c]));
  const node=nodes.find(n=>n.id===selectedId);
  const part=node?definitions.get(node.componentId):null;
  const bindings=session.candidate?session.candidateBindings:session.bindings;
  const actions=bindings?.revisionId===revision.id?bindings.actions.filter(a=>a.instanceIds.includes(selectedId??'')):[];
  const branch=(parent:string|null):React.ReactNode=> <ul>{nodes.filter(n=>n.parentId===parent).map(n=> {
    const definition=definitions.get(n.componentId);
    return <li key={n.id}><button className="assembly-tree-row" onClick={()=>onSelect(n.id)} aria-pressed={selectedId===n.id} data-instance-id={n.id}>
      <strong>{definition?.name??'Missing source component'}</strong><small>{readable(n.subsystemId)} · {n.id}</small>
    </button>{nodes.some(child=>child.parentId===n.id)&&branch(n.id)}</li>;
  })}</ul>;
  return <div className="assembly-inspector">
    <span className="eyebrow">{session.candidate?'CANDIDATE POSE':'ACCEPTED POSE'}</span>
    <h2>Assembly components</h2>
    <p>{nodes.length} placed components · {revision.assembly.configurationId} configuration. The assembly remains partial; physical task capability is unverified.</p>
    {onColorSubsystems&&<section><button className="secondary-button" aria-pressed={colorSubsystems} onClick={onColorSubsystems}>Color subsystems</button><ul className="subsystem-legend">{revision.assembly.subsystems.map(s=><li key={s.id}><span style={{display:'inline-block',width:10,height:10,marginRight:8,background:SUBSYSTEM_COLORS[s.id]??'#8b9dad'}}/>{readable(s.id)} · {nodes.filter(n=>n.subsystemId===s.id).length}</li>)}</ul></section>}
    <nav className="assembly-tree" aria-label="Assembly component hierarchy">{branch(null)}</nav>
    {node&&part&&<section className="assembly-part-details"><h3>{part.name}</h3><p>{geometryLabel(part)}</p>
      <dl><dt>Subsystem</dt><dd>{readable(node.subsystemId)}</dd><dt>Part identity</dt><dd>{part.sku??part.id}</dd><dt>Imported solids</dt><dd>{part.solidCount}</dd></dl>
      <p>{actions.length?`Linked actions: ${actions.map(a=>readable(a.actionId)).join(', ')}.`:'No strategy action is bound to this component.'}</p>
      <p className="strategy-caption">Links identify geometry in this revision; they do not verify scoring support, actuation, or physical fit.</p>
      <button className="secondary-button" onClick={()=>onSource(part.id)}>Inspect original component source</button>
    </section>}
    <details className="strategy-evidence"><summary>Remaining qualifications</summary><ul>{session.missing.map((gap,index)=><li key={index}>{readable(gap.role)}: {gap.message}</li>)}</ul></details>
  </div>;
}
