import { useId, useMemo, useState } from 'react';
import type { ComponentDefinition, Mode } from '../api/contracts';
import { Icon } from '../components/Icon';
import { buildNativeHierarchy, filterNativeHierarchy, type HierarchyItem } from './hierarchyTree';

interface RowsProps {
  items: HierarchyItem[];
  expanded: Set<string>;
  filtering: boolean;
  disabled: boolean;
  mode: Mode;
  toggle: (id: string) => void;
  select: (id: string, name: string) => void;
}
function HierarchyRows({ items, ...props }: RowsProps) {
  const [limit, setLimit] = useState(40);
  return <ul>{items.slice(0, limit).map(item => {
    const { node } = item;
    const isOpen = props.filtering || props.expanded.has(node.id);
    return <li key={node.id}>
      <div className="native-node-row">
        {item.children.length > 0 ? <button className="native-node-toggle" aria-label={`${isOpen ? 'Collapse' : 'Expand'} ${node.name || node.id}`} aria-expanded={isOpen} disabled={props.filtering} onClick={() => props.toggle(node.id)}><Icon name="chevron" size={14} /></button> : <span className="native-node-spacer" />}
        <button className="native-node-select" data-native-node-id={node.id} disabled={props.disabled} title={`${node.name || node.id} · ${node.id}`} onClick={() => props.select(node.id, node.name)}>
          <Icon name="parts" size={14} /><span>{node.name || node.id}<small>{props.mode === 'advanced' ? `${node.id} · ` : ''}{node.hasMesh ? 'Source part' : 'Source group'}{item.descendantCount > 0 ? ` · ${item.descendantCount} nested nodes` : ''}</small></span><Icon name="focus" size={14} />
        </button>
      </div>
      {isOpen && item.children.length > 0 && <HierarchyRows {...props} items={item.children} />}
    </li>;
  })}{items.length > limit && <li><button className="text-action native-node-more" onClick={() => setLimit(value => value + 40)}>Show {Math.min(40, items.length - limit)} more source nodes · {items.length - limit} remaining</button></li>}</ul>;
}

export function NativeHierarchy({ component, mode, disabled, onSelect }: { component: ComponentDefinition; mode: Mode; disabled: boolean; onSelect: (nodeId: string, name: string) => void }) {
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const searchId = useId();
  const tree = useMemo(() => buildNativeHierarchy(component.nativeHierarchy ?? []), [component.nativeHierarchy]);
  const filtered = useMemo(() => filterNativeHierarchy(tree, query), [tree, query]);
  return <details className="native-hierarchy" open>
    <summary>Native source hierarchy · {component.nativeHierarchy?.length ?? 0} nodes</summary>
    <p className="availability-note">Select a source part or group, then use Focus. Source groups can help inspect subsystems; they do not establish a verified mechanism.</p>
    <label className="search-field" htmlFor={searchId}><span>Find source parts</span><input id={searchId} type="search" placeholder="Source name or node ID" value={query} onChange={event => setQuery(event.target.value)} /></label>
    <div className="native-tree">
      {filtered.length ? <HierarchyRows items={filtered} expanded={expanded} filtering={!!query.trim()} disabled={disabled} mode={mode} select={onSelect} toggle={id => setExpanded(previous => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; })} /> : <p className="availability-note" role="status">No matching source parts.</p>}
    </div>
  </details>;
}
