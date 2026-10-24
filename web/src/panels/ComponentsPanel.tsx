import { useState } from 'react';
import { geometryLabel, isInspectable, type Catalog, type ComponentDefinition, type Mode } from '../api/contracts';
import { Icon } from '../components/Icon';
import { SourceRegisterPanel } from './SourceRegisterPanel';
import { NativeHierarchy } from '../viewer/NativeHierarchy';

export function SourceDetails({ component: c, mode }: { component: ComponentDefinition; mode: Mode }) {
  const sourceUrl = /^https?:\/\//i.test(c.sourceUrl) ? c.sourceUrl : null;
  // These are optional prepared-source metadata, supplied by the parent API.
  const validation = c.geometryValidation && typeof c.geometryValidation === 'object' ? c.geometryValidation as { status?: string; nativeBrepValid?: boolean; invalidComponentInstances?: unknown[]; invalidDefinitionCount?: number | null; limitations?: string[] } : null;
  const sourceDefects = validation?.status === 'source_defects' || validation?.nativeBrepValid === false;
  const invalidInstances = validation?.invalidComponentInstances?.length ?? 0;
  const invalidDefinitions = validation?.invalidDefinitionCount;
  return <div className="source-details">
    {c.referenceOnly === true && <span className="source-tag reference-tag">Reference assembly · not generated robot</span>}
    <span className={`source-tag ${c.geometryClass === 'test_fixture' ? 'fixture-tag' : ''}`}>{geometryLabel(c)}</span>
    {sourceDefects && <div className="source-defect-warning" role="status"><strong>Imported reference fails aggregate BRep check</strong><p>Inspection reference only. The cause may be in the original source or aggregate import. Not qualified for robot generation or verified engineering.</p>{invalidInstances > 0 && <p>{invalidInstances} invalid source component instances identified.</p>}{typeof invalidDefinitions === 'number' && invalidDefinitions > 0 && <p>{invalidDefinitions} invalid definitions identified.</p>}{!!validation?.limitations?.length && <ul>{validation.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul>}</div>}
    <dl><div><dt>Part identity</dt><dd>{c.sku || c.id}</dd></div><div><dt>Dimensions · mm</dt><dd data-testid="component-dimensions">{c.boundsM.max.map((n, i) => ((n - c.boundsM.min[i]) * 1000).toFixed(2)).join(' × ')}</dd></div><div><dt>Source solids</dt><dd>{c.solidCount}</dd></div><div><dt>Display</dt><dd>Source-derived triangle mesh · metres</dd></div><div><dt>Rights scope</dt><dd>{c.rightsStatus === 'qualified_for_declared_use' ? 'Qualified for declared local use' : c.rightsStatus.replaceAll('_', ' ')}</dd></div></dl>
    {sourceUrl && <a className="source-link" href={sourceUrl} target="_blank" rel="noopener noreferrer">Inspect source reference <Icon name="arrow" size={14} /></a>}
    {c.attribution && <p className="availability-note">Attribution: {c.attribution}</p>}
    {mode === 'advanced' && <div className="advanced-details"><span className="eyebrow">SOURCE IDENTITY</span><dl><div><dt>Component ID</dt><dd>{c.id}</dd></div><div><dt>Source SHA-256</dt><dd className="hash">{c.sourceSha256}</dd></div><div><dt>Mesh SHA-256</dt><dd className="hash">{c.meshSha256}</dd></div><div><dt>Declared ports</dt><dd>{c.ports.length}</dd></div><div><dt>Origin</dt><dd>{c.originKind.replaceAll('_', ' ')}</dd></div>{c.conversion && Object.entries(c.conversion).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd></div>)}</dl></div>}
    <p className="availability-note">{c.referenceOnly === true ? 'Imported reference geometry for inspection. This is not a generated robot, an editable solid, or evidence of physical validation.' : 'Source part only. This is not a connected robot assembly, an editable solid, or evidence of physical validation.'}</p>
  </div>;
}
export function ComponentsPanel({ catalog, activeId, mode, canInspect, onOpen, onSelect, onSelectNode }: { catalog: Catalog | null; activeId: string | null; mode: Mode; canInspect: boolean; onOpen: (c: ComponentDefinition) => void; onSelect: (c: ComponentDefinition) => void; onSelectNode: (c: ComponentDefinition, nodeId: string, name: string) => void }) {
  const [query, setQuery] = useState('');
  const [showSources, setShowSources] = useState(false);
  const active = catalog?.components.find(c => c.id === activeId);
  const components = catalog?.components.filter(c => `${c.name} ${c.sku} ${c.id}`.toLowerCase().includes(query.toLowerCase())) ?? [];
  return <>
    <label className="search-field"><span>Filter components</span><input type="search" placeholder="Name or part number" value={query} onChange={e => setQuery(e.target.value)} /></label>
    <div className="catalog-heading"><span>LOCAL SOURCE PARTS</span><span>{catalog?.components.length ?? 0}</span></div>
    <button className="text-action" aria-expanded={showSources} onClick={() => setShowSources(value => !value)}>{showSources ? 'Hide source register' : 'Review source register'}</button>
    {showSources && <SourceRegisterPanel mode={mode} />}
    {components.length ? <ul className="component-list">{components.map(c => <li key={c.id}>
      <button className={`component-row ${activeId === c.id ? 'is-active' : ''}`} aria-pressed={activeId === c.id} onClick={() => onOpen(c)} disabled={!canInspect || !isInspectable(c)}><span className="part-symbol"><Icon name="parts" size={22} /></span><span><strong>{c.name}</strong><small>{c.sku || c.id}</small><small>{geometryLabel(c)}</small></span><Icon name={activeId === c.id ? 'check' : 'chevron'} size={16} /></button>
    </li>)}</ul> : <div className="panel-empty"><Icon name="parts" size={32} /><h2>{query ? 'No matching components' : 'Your catalog is empty'}</h2><p>{query ? 'Try another name or part number.' : 'Register and prepare rights-qualified local STEP files with the Tachyon CLI, then refresh the workspace.'}</p></div>}
    {active && <section className="component-inspector"><div className="subsection-title"><h2>{active.name}</h2><button className="text-action" onClick={() => onSelect(active)} disabled={!canInspect || !isInspectable(active)}>Select in scene <Icon name="focus" size={15} /></button></div><SourceDetails component={active} mode={mode} />{!!active.nativeHierarchy?.length && <NativeHierarchy key={`${active.id}-${active.meshSha256}`} component={active} mode={mode} disabled={!canInspect || !isInspectable(active)} onSelect={(id, name) => onSelectNode(active, id, name)} />}</section>}
    {!!catalog?.blockers.length && <section className="blockers"><h2>What’s needed</h2><ul>{catalog.blockers.map((b, i) => <li key={`${b.code}-${i}`}><strong>{b.code.replaceAll('_', ' ')}</strong><p>{b.message}</p>{b.componentId && <small>Component: {b.componentId}</small>}</li>)}</ul></section>}
  </>;
}
