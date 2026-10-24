import { readable, type DesignSession } from '../api/strategy';

/** Coordinate/connection illustration from the displayed assembly revision. */
export function AssemblySketch({ session, actionId }: { session: DesignSession; actionId: string | null }) {
  if (!actionId) return null;
  const revision=session.candidate??session.accepted;
  const bindings=session.candidate?session.candidateBindings:session.bindings;
  const transforms=session.candidate?session.candidateWorldTransforms:session.worldTransforms;
  if (!revision || !bindings || bindings.revisionId!==revision.id) return null;
  const action=bindings.actions.find(a=>a.actionId===actionId);
  if (!action) return <p className="strategy-caption">This action has no component binding in the displayed assembly.</p>;
  const members=new Set(action.instanceIds);
  const nodes=new Map(revision.assembly.instances.map(n=>[n.id,n]));
  for (const id of [...members]) {
    let parent=nodes.get(id)?.parentId;
    while (parent) { members.add(parent); parent=nodes.get(parent)?.parentId; }
  }
  const rows=[...members].flatMap(id=> {
    const matrix=transforms[id]; const node=nodes.get(id);
    return matrix?.length===16&&node?[{id,node,point:[matrix[12],matrix[13],matrix[14]]}]:[];
  });
  const points=[...rows.map(r=>r.point),...action.anchors.map(a=>a.worldPointM)];
  if (!points.length) return null;
  const span=(axis:number)=>Math.max(...points.map(p=>p[axis]))-Math.min(...points.map(p=>p[axis]));
  const horizontal=span(0)>=span(2)?0:2;
  const minX=Math.min(...points.map(p=>p[horizontal])),minY=Math.min(...points.map(p=>p[1]));
  const size=Math.max(span(horizontal),span(1),.04);
  const project=(p:number[])=>[60+(p[horizontal]-minX)/size*180,235-(p[1]-minY)/size*180];
  return <figure className="strategy-figure assembly-coordinate-sketch" data-revision-id={revision.id}>
    <svg viewBox="0 0 360 280" role="img" aria-label="Assembly joint and tool anchor sketch from the displayed revision">
      {rows.map(row=> {
        const parent=rows.find(p=>p.id===row.node.parentId);
        if (!parent) return null;
        const a=project(parent.point),b=project(row.point);
        return <path key={'link-'+row.id} d={`M${a.join(' ')}L${b.join(' ')}`} fill="none" stroke="currentColor" strokeWidth="2"/>;
      })}
      {rows.map(row=> {
        const p=project(row.point);
        return <g key={row.id}><title>{readable(row.node.subsystemId)} · {row.id}</title><circle cx={p[0]} cy={p[1]} r="6" fill="none" stroke="currentColor" strokeWidth="2"/></g>;
      })}
      {action.anchors.map(anchor=> {
        const p=project(anchor.worldPointM);
        return <g key={anchor.id}><title>Tool anchor · {(anchor.worldPointM[1]*1000).toFixed(0)} mm high</title><path d={`M${p[0]-8} ${p[1]}H${p[0]+8}M${p[0]} ${p[1]-8}V${p[1]+8}`} stroke="var(--accent, #2671a9)" strokeWidth="2"/></g>;
      })}
    </svg>
    <figcaption><strong>Circles: component origins. Cross: tool anchor.</strong>{action.anchors.map(anchor=><span key={anchor.id} className="assembly-anchor-height">Tool anchor · {(anchor.worldPointM[1]*1000).toFixed(0)} mm high</span>)} Joint-tree connections from this exact {session.candidate?'preview':'accepted'} pose. This coordinate sketch is not part geometry or verified scoring capability.</figcaption>
  </figure>;
}
