import { lazy, Suspense, useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { api, errorMessage } from '../api/client';
import { geometryLabel, isInspectable, type Capabilities, type Catalog, type ComponentDefinition, type Health, type Preferences, type Selection, type WorkspacePatch } from '../api/contracts';
import { AiCore } from '../assistant/AiCore';
import { Icon } from '../components/Icon';
import { ComponentsPanel } from '../panels/ComponentsPanel';
import { PanelHost } from '../panels/PanelHost';
import { PreferencesPanel } from '../panels/PreferencesPanel';
import { Home } from '../screens/Home';
import type { SceneStatus } from '../viewer/AssemblyScene';
import { ViewControls } from '../viewer/ViewControls';
import { initialState, workspaceReducer, type Panel } from './reducer';

const AssemblyScene = lazy(() => import('../viewer/AssemblyScene').then(module => ({ default: module.AssemblyScene })));
type SaveState = 'saved' | 'saving' | 'unsaved';
export function WorkspaceShell() {
  const [state, dispatch] = useReducer(workspaceReducer, initialState);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [assetAttempt, setAssetAttempt] = useState(0);
  const [scene, setScene] = useState<SceneStatus>({ state: 'idle' });
  const [resetKey, setResetKey] = useState(0);
  const [focusKey, setFocusKey] = useState(0);
  const [saveState, setSaveState] = useState<SaveState>('saved');
  const saveQueue = useRef(Promise.resolve());
  const saveSequence = useRef(0);
  const pendingPatch = useRef<WorkspacePatch>({});
  const initialized = useRef(false);

  useEffect(() => {
    const abort = new AbortController();
    setLoading(true); setError(null);
    api.health(abort.signal).then(setHealth).catch(() => { if (!abort.signal.aborted) setHealth(null); });
    Promise.all([api.catalog(abort.signal), api.capabilities(abort.signal), api.workspace(abort.signal)]).then(([nextCatalog, nextCapabilities, workspace]) => {
      if (abort.signal.aborted) return;
      setCatalog(nextCatalog); setCapabilities(nextCapabilities); setConnected(true);
      // A refresh never overwrites an unsaved in-tab preference or command draft.
      if (!initialized.current) {
        dispatch({ type: 'restore', workspace }); initialized.current = true;
      }
    }).catch(reason => { if (!abort.signal.aborted) { setError(errorMessage(reason)); setConnected(false); } })
      .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [reload]);

  const component = catalog?.components.find(c => c.id === state.activeComponentId);
  const renderable = component && connected && capabilities?.canInspect && isInspectable(component) ? component : undefined;
  const onSceneStatus = useCallback((s: SceneStatus) => setScene(s), []);
  function save(patch: WorkspacePatch) {
    pendingPatch.current = {
      ...pendingPatch.current, ...patch,
      ...(patch.preferences ? { preferences: { ...pendingPatch.current.preferences, ...patch.preferences } } : {}),
    };
    const payload = structuredClone(pendingPatch.current);
    const sequence = ++saveSequence.current;
    setSaveState('saving');
    saveQueue.current = saveQueue.current.then(async () => {
      try {
        await api.patchWorkspace(payload);
        if (sequence === saveSequence.current) { pendingPatch.current = {}; setSaveState('saved'); }
      } catch {
        if (sequence === saveSequence.current) setSaveState('unsaved');
      }
    });
  }
  function preferences(p: Partial<Preferences>) { dispatch({ type: 'preferences', preferences: p }); save({ preferences: p }); }
  function openComponent(c: ComponentDefinition) {
    if (!isInspectable(c) || !capabilities?.canInspect) return;
    if (state.activeComponentId === c.id) return;
    dispatch({ type: 'component', componentId: c.id }); setScene({ state: 'loading' }); save({ activeComponentId: c.id });
  }
  function selectComponent(c: ComponentDefinition) {
    if (state.activeComponentId !== c.id) openComponent(c);
    dispatch({ type: 'select', selection: { componentId: c.id, catalogMeshSha256: c.meshSha256 } });
  }
  function select(selection: Selection | null) { dispatch({ type: 'select', selection }); }
  function panel(next: Panel) { dispatch({ type: 'panel', panel: next }); }
  const panelTitle = state.panel === 'home' ? 'Welcome to Tachyon' : state.panel === 'components' ? 'Components' : 'Preferences';
  const ready = !!renderable && scene.state === 'ready';

  return <main className="workspace" data-theme={state.preferences.theme} data-mode={state.preferences.mode}
    onKeyDown={e => { if (e.key === 'Escape') { if (state.assistantSize !== 'compact') dispatch({ type: 'assistant', size: 'compact' }); else panel(null); } }}>
    <div className="drafting-grid" aria-hidden="true" />
    {renderable && <Suspense fallback={<span className="sr-only">Loading CAD renderer</span>}><AssemblyScene key={`${renderable.id}-${renderable.meshSha256}-${assetAttempt}`} component={renderable} theme={state.preferences.theme} selection={state.selection} onSelect={select} onStatus={onSceneStatus} resetKey={resetKey} focusKey={focusKey} panelOpen={state.panel !== null} /></Suspense>}
    <div className="workspace-topline"><div className="workspace-context"><span className="context-mark" /><span>{component ? component.name : 'Untitled workspace'}</span><span className="context-divider" /><span className="context-type">{component ? 'Source component' : 'Focus'}</span></div><span className="wordmark">TACHYON<span className="wordmark-symbol">↗</span></span></div>
    <AiCore size={state.assistantSize} onSize={size => dispatch({ type: 'assistant', size })} draft={state.commandDraft} onDraft={text => dispatch({ type: 'draft', text })} component={component} selection={state.selection} loading={loading} onComponents={() => panel('components')} />
    {!loading && error && <div className="connection-banner" role="alert"><Icon name="info" /><span>{error}</span><button onClick={() => setReload(n => n + 1)}>Retry connection</button></div>}
    {!renderable && <div className="canvas-empty" data-testid="cad-unavailable"><div className="empty-reticle" aria-hidden="true"><span /><Icon name="parts" size={40} /><span /></div><span className="eyebrow">{loading ? 'CONNECTING WORKSPACE' : 'SOURCE COMPONENT INSPECTION'}</span><h2>{loading ? 'Opening your workspace…' : component ? 'This component is unavailable' : 'Make room for the real thing.'}</h2><p>{loading ? 'Reading the local catalog and workspace capabilities.' : error ? 'Connect this tab to inspect your local source catalog.' : component ? 'The source part is missing permission, valid geometry, or inspection capability.' : 'Qualified local CAD appears here. Your workspace stays empty until real source geometry is available.'}</p>{!loading && <button className="secondary-button" onClick={() => panel('components')}>Open Components <Icon name="arrow" size={16} /></button>}
      {!loading && !!catalog?.blockers.length && <p className="empty-blocker">{catalog.blockers[0].message}</p>}
    </div>}
    {renderable && scene.state !== 'ready' && <div className="scene-message" role={scene.state === 'failed' ? 'alert' : 'status'}><Icon name={scene.state === 'failed' ? 'info' : 'parts'} size={26} /><h2>{scene.state === 'failed' ? 'Source geometry could not be displayed' : 'Loading source geometry'}</h2><p>{scene.message ?? 'Fetching the protected GLB and checking its identity.'}</p>{scene.state === 'failed' && <button className="secondary-button" onClick={() => setAssetAttempt(n => n + 1)}>Retry geometry</button>}</div>}
    {renderable && <div className={`source-status ${renderable.geometryClass === 'test_fixture' ? 'is-fixture' : ''}`} role="status" data-testid="scene-status" data-state={scene.state} data-component-id={renderable.id} data-mesh-sha256={renderable.meshSha256} data-mesh-count={scene.meshCount ?? 0} data-render-bounds={scene.boundsM ? JSON.stringify(scene.boundsM) : undefined}>
      <span className="status-dot" /><span>{geometryLabel(renderable)}{ready ? ` · ${scene.meshCount} mesh${scene.meshCount === 1 ? '' : 'es'}` : ''}</span><strong>{renderable.geometryClass === 'test_fixture' ? 'CONVERTER PROOF ONLY · NOT AUTHENTIC VEX' : 'SOURCE PART · NO ROBOT ASSEMBLY'}</strong>
    </div>}
    {state.selection && <div className="selection-chip" data-component-id={state.selection.componentId} data-native-node-id={state.selection.nativeNodeId}><Icon name="parts" size={16} /><span><strong>{component?.name}</strong><small>{state.selection.meshName ?? component?.sku} · selected</small></span><button className="icon-button" aria-label="Inspect selection" onClick={() => panel('components')}><Icon name="info" size={16} /></button><button className="icon-button" aria-label="Clear selection" onClick={() => select(null)}><Icon name="close" size={16} /></button></div>}
    {state.panel && <PanelHost key={state.panel} title={panelTitle} subtitle={state.panel === 'home' ? 'COMPLICATEDLY SIMPLE' : state.panel === 'components' ? 'INSPECT / SOURCE / IDENTITY' : 'MAKE IT YOURS'} onClose={() => panel(null)}>
      {state.panel === 'home' && <Home catalog={catalog} capabilities={capabilities} onInspect={() => panel('components')} />}
      {state.panel === 'components' && <ComponentsPanel catalog={catalog} activeId={state.activeComponentId} mode={state.preferences.mode} canInspect={connected && !!capabilities?.canInspect} onOpen={openComponent} onSelect={selectComponent} onSelectNode={(c, nativeNodeId, meshName) => select({ componentId: c.id, catalogMeshSha256: c.meshSha256, nativeNodeId, meshName })} />}
      {state.panel === 'preferences' && <PreferencesPanel preferences={state.preferences} onChange={preferences} disabled={!connected} />}
    </PanelHost>}
    <div className="workspace-bottomline"><span className="gesture-hint"><Icon name="orbit" size={14} /> <span className="desktop-hint">Drag to orbit · Scroll to zoom · Right-drag to pan</span><span className="mobile-hint">Drag to orbit · Pinch to zoom · Two fingers to pan</span></span><span className="workspace-version">{health ? `LOCAL / ${health.version}` : 'LOCAL WORKSPACE'}<span className="unit-label">m</span></span></div>
    <div className="workspace-dock"><nav aria-label="Workspace tools">{([{ id: 'home', icon: 'home', title: 'Home' }, { id: 'components', icon: 'parts', title: 'Components' }, { id: 'preferences', icon: 'settings', title: 'Preferences' }] as const).map(item => <button key={item.id} aria-pressed={state.panel === item.id} onClick={() => panel(state.panel === item.id ? null : item.id)}><Icon name={item.icon} /><span>{item.title}</span></button>)}</nav><span className="dock-divider" /><ViewControls disabled={!ready} onFocus={() => setFocusKey(n => n + 1)} onReset={() => setResetKey(n => n + 1)} /></div>
    <div className={`save-state save-${saveState}`} role="status">{saveState === 'saving' ? 'Saving preferences…' : saveState === 'unsaved' ? <>Unsaved preferences <button onClick={() => save(pendingPatch.current)}>Retry save</button></> : connected ? 'Local workspace' : 'Not connected'}</div>
  </main>;
}
