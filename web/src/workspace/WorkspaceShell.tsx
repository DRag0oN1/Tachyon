import { lazy, Suspense, useCallback, useEffect, useReducer, useRef, useState, type CSSProperties } from 'react';
import { api, errorMessage } from '../api/client';
import { geometryLabel, isInspectable, type Capabilities, type Catalog, type ComponentDefinition, type Health, type Preferences, type Selection, type WorkspacePatch } from '../api/contracts';
import { parseDesignSession, readable, type DesignSession, type RealizationState, type StrategySession, type StrategyStatus } from '../api/strategy';
import { AiCore, type CommandResult } from '../assistant/AiCore';
import { Icon } from '../components/Icon';
import { ComponentsPanel } from '../panels/ComponentsPanel';
import { AssemblyInspector } from '../panels/AssemblyInspector';
import { PanelHost } from '../panels/PanelHost';
import { PreferencesPanel } from '../panels/PreferencesPanel';
import { StrategyPanel } from '../panels/StrategyPanel';
import { ArchitecturesPanel } from '../panels/ArchitecturesPanel';
import { Home } from '../screens/Home';
import type { SceneStatus } from '../viewer/AssemblyScene';
import { ViewControls } from '../viewer/ViewControls';
import { initialState, workspaceReducer, type Panel } from './reducer';
import '../styles/strategy.css';

const AssemblyScene = lazy(() => import('../viewer/AssemblyScene').then(module => ({ default: module.AssemblyScene })));
const DesignAssemblyScene = lazy(() => import('../viewer/DesignAssemblyScene').then(module => ({ default: module.DesignAssemblyScene })));
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
  const [upAxis, setUpAxis] = useState<'X' | 'Y' | 'Z'>('Z');
  const [saveState, setSaveState] = useState<SaveState>('saved');
  const [strategyStatus, setStrategyStatus] = useState<StrategyStatus | null>(null);
  const [strategyChecking, setStrategyChecking] = useState(true);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [strategySession, setStrategySession] = useState<StrategySession | null>(null);
  const [generating, setGenerating] = useState(false);
  const generationBusy = useRef(false);
  const generationAbort = useRef<AbortController | null>(null);
  const designBusy = useRef(false);
  const [designWorking, setDesignWorking] = useState(false);
  const [realization, setRealization] = useState<RealizationState>({ state: 'idle' });
  const [designSession, setDesignSession] = useState<DesignSession | null>(null);
  const [selectedDesignInstanceId, setSelectedDesignInstanceId] = useState<string | null>(null);
  const [canvasMode, setCanvasMode] = useState<'reference' | 'design'>('reference');
  const [panelWidth, setPanelWidth] = useState(480);
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

  useEffect(() => {
    const abort = new AbortController();
    setStrategyChecking(true);
    Promise.resolve().then(() => api.strategyStatus(abort.signal)).then(status => {
      if (!abort.signal.aborted) { setStrategyStatus(status); setStrategyError(null); }
    }).catch(reason => { if (!abort.signal.aborted) { setStrategyStatus(null); setStrategyError(errorMessage(reason)); } })
      .finally(() => { if (!abort.signal.aborted) setStrategyChecking(false); });
    return () => abort.abort();
  }, [reload]);
  useEffect(() => () => generationAbort.current?.abort(), []);

  const component = catalog?.components.find(c => c.id === state.activeComponentId);
  const renderable = component && connected && capabilities?.canInspect && isInspectable(component) ? component : undefined;
  const onSceneStatus = useCallback((s: SceneStatus) => setScene(s), []);
  const showDesign = canvasMode === 'design' && !!designSession?.accepted && !!designSession.components.length;
  const sourceRenderable = !showDesign ? renderable : undefined;
  const displayedRevision = designSession?.candidate ?? designSession?.accepted;
  const displayedBindings = designSession?.candidate ? designSession.candidateBindings : designSession?.bindings;
  const designInstance = displayedRevision?.assembly.instances.find(i => i.id === selectedDesignInstanceId);
  const reverseActions = displayedBindings?.revisionId === displayedRevision?.id && selectedDesignInstanceId
    ? displayedBindings?.actions.filter(a => a.instanceIds.includes(selectedDesignInstanceId)) ?? [] : [];

  async function generate(target: 'strategy' | 'architectures') {
    panel(target);
    if (generationBusy.current || designBusy.current || !strategyStatus?.available) return;
    if (designSession?.candidate) { setStrategyError('Apply or discard the pending design preview before generating a replacement session.'); return; }
    generationBusy.current = true; setGenerating(true); setStrategyError(null);
    const abort = new AbortController(); generationAbort.current = abort;
    try {
      const next = await api.generateStrategy(abort.signal);
      if (abort.signal.aborted) return;
      setStrategySession(next); dispatch({ type: 'strategy-generated' });
      setRealization({ state: 'idle' }); setDesignSession(null); setSelectedDesignInstanceId(null); setCanvasMode('reference');
      if (target === 'architectures' && next.architectures[0]) dispatch({ type: 'architecture', architectureId: next.architectures[0].id });
    } catch (reason) { if (!abort.signal.aborted) setStrategyError(errorMessage(reason)); }
    finally { generationBusy.current = false; if (!abort.signal.aborted) setGenerating(false); }
  }
  function openFlow(target: 'strategy' | 'architectures') {
    if (strategySession) {
      panel(target);
      if (target === 'architectures' && !state.selectedArchitectureId && strategySession.architectures[0]) dispatch({ type: 'architecture', architectureId: strategySession.architectures[0].id });
    } else void generate(target);
  }
  function selectAction(actionId: string) {
    dispatch({ type: 'strategy-action', action: actionId }); setSelectedDesignInstanceId(null); setFocusKey(n => n + 1);
  }
  function acceptDesignResponse(next: DesignSession) {
    setDesignSession(next); setRealization({ state: 'loaded', architectureId: next.architectureId, result: next });
    setSelectedDesignInstanceId(null); setFocusKey(n => n + 1);
    if (next.accepted && next.components.length) {
      setCanvasMode('design');
      if (!showDesign || (next.candidate ?? next.accepted).id !== displayedRevision?.id) setScene({ state: 'loading' });
    }
  }
  async function realizeArchitecture(architectureId: string) {
    if (!strategySession || designBusy.current || generationBusy.current) return;
    dispatch({ type: 'architecture', architectureId });
    if (designSession?.candidate) { setRealization({ state: 'failed', architectureId, message: 'Apply or discard the pending preview before realizing another architecture.' }); return; }
    designBusy.current = true; setDesignWorking(true); setRealization({ state: 'loading', architectureId });
    try {
      const result = parseDesignSession(await api.post('/api/designs/realize', { architecture_id: architectureId }));
      if (result.architectureId !== architectureId || result.strategyId !== strategySession.spec.id) throw new Error('The CAD response belongs to a different architecture or strategy.');
      acceptDesignResponse(result);
    } catch (reason) { setRealization({ state: 'failed', architectureId, message: errorMessage(reason) }); }
    finally { designBusy.current = false; setDesignWorking(false); }
  }
  const editReason = !designSession?.canEdit
    ? `Editing requires a qualified mechanism recipe, components, and assembly placement. ${designSession?.missing.map(m => m.message).join(' ') || 'Realize an architecture to inspect the missing qualifications.'}`
    : !showDesign ? 'Source inspection references cannot be edited. Return to the assembly revision to preview or apply a supported mechanism change.'
    : designSession.candidate ? 'Previewing a candidate revision. Apply accepts this exact candidate; Discard preserves the accepted revision.' : 'Supported edits: lower or raised scoring configuration. Preview before Apply.';
  async function edit(action: 'preview' | 'apply' | 'discard' | 'undo', configuration?: 'lower' | 'raised'): Promise<CommandResult> {
    const current = designSession;
    const canRestore = action === 'undo' && !!current?.previous && current.status !== 'blocked';
    if ((!current?.canEdit && !canRestore) || !current?.revisionId) return { message: editReason };
    if (!showDesign && action !== 'discard') return { message: editReason };
    if (designBusy.current) return { message: 'A design request is already running. Wait for its result.' };
    if ((action === 'apply' || action === 'discard') && !current.candidate) return { message: 'There is no candidate preview to apply or discard.' };
    if ((action === 'preview' || action === 'undo') && current.candidate) return { message: 'Apply or discard the current preview first.' };
    designBusy.current = true; setDesignWorking(true);
    try {
      const path = `/api/designs/${encodeURIComponent(current.designId)}/${action === 'preview' ? 'preview' : 'decision'}`;
      const body = action === 'preview' ? { base_revision_id: current.revisionId, configuration_id: configuration } : {
        base_revision_id: current.revisionId, action, ...(current.candidate ? { candidate_revision_id: current.candidate.id } : {}),
      };
      const next = parseDesignSession(await api.post(path, body));
      if (next.designId !== current.designId || next.architectureId !== current.architectureId || next.strategyId !== current.strategyId) throw new Error('The revision response belongs to a different design.');
      if (next.status === 'blocked') {
        acceptDesignResponse(next);
        return { message: `Design qualification is now blocked. No successful revision change was confirmed. ${next.missing.map(m => m.message).join(' ')}` };
      }
      if (action === 'preview' && (!next.candidate || next.revisionId !== current.revisionId)) throw new Error('The server did not return a candidate against the accepted revision.');
      if (action === 'apply' && (next.revisionId !== current.candidate?.id || next.candidate)) throw new Error('The requested candidate was not confirmed as accepted. Refresh the design before continuing.');
      if (action === 'discard' && (next.revisionId !== current.revisionId || next.candidate)) throw new Error('The server did not confirm the preview was discarded.');
      if (action === 'undo' && (next.revisionId === current.revisionId || next.candidate)) throw new Error('The server did not confirm an undo revision.');
      acceptDesignResponse(next);
      return { message: action === 'preview' ? `Preview returned for the ${configuration} configuration. The accepted revision is unchanged; review before Apply.` : action === 'apply' ? 'The server accepted the exact previewed revision.' : action === 'discard' ? 'Preview discarded. The accepted revision is unchanged.' : 'Undo confirmed by the server as a new accepted revision.' };
    } finally { designBusy.current = false; setDesignWorking(false); }
  }
  async function command(text: string): Promise<CommandResult> {
    if (/\b(show|open|view)\s+(the\s+)?strateg(y|ies)\b/i.test(text)) { openFlow('strategy'); return { message: strategySession ? 'Strategy opened.' : `Strategy panel opened. ${strategyStatus?.available ? 'Running the frozen seeded policy.' : strategyStatus?.reason ?? strategyError ?? 'The trained strategy service is unavailable.'}` }; }
    if (/\b(show|open|view|compare)\s+(the\s+)?(architectures?|alternatives?|concepts?)\b/i.test(text)) { openFlow('architectures'); return { message: 'Architecture comparison opened. These are engineering alternatives for one learned family.' }; }
    if (/\b(raise|raised|higher|taller|lower|lowered|shorter|increase|decrease)\b/i.test(text) && !/\b(explain|what|how|why|describe)\b/i.test(text)) {
      if (/\b(do not|don't|cancel|no changes)\b/i.test(text)) return {message:'No height preview was created.'};
      if (/\d\s*(mm|cm|m|inches|inch|feet)\b/i.test(text)) return {message:'Only registered lower and raised configurations are supported. An arbitrary requested dimension cannot be applied; use Preview raised or Preview lower to inspect the actual endpoint.'};
      const explicitHeight = /\b(scor(e|er|ing)|lift|reach|height)\b/i.test(text);
      const registeredPose = /^(?:preview\s+)?(?:raised|lower)(?:\s+configuration)?[.!]?$/i.test(text.trim());
      const selectedScorer = designInstance?.subsystemId === 'scorer' && /^(?:please\s+)?(?:(?:raise|lower)\s+(?:it|this|the selection)|make\s+(?:it|this)\s+(?:taller|shorter|higher|lower))[.!]?$/i.test(text.trim());
      if (/\b(camera|view|drive|drivetrain|speed|acceleration|reliability|wheels?|intake|cup|cradle|transfer|chassis)\b/i.test(text) || (!explicitHeight && !registeredPose && !selectedScorer)) return {message:'The supported height configuration affects the scoring mechanism. This request does not identify a supported scoring-height edit.'};
      return edit('preview', /\b(lower|lowered|shorter|decrease)\b/i.test(text) ? 'lower' : 'raised');
    }
    if (/\b(explain|what|how|why|describe)\b/i.test(text)) {
      if (showDesign && designInstance) return { message: `${readable(designInstance.subsystemId)} instance ${designInstance.id} is in displayed revision ${displayedRevision?.id}. ${reverseActions.length ? `Linked actions: ${reverseActions.map(a => readable(a.actionId)).join(', ')}. Component links do not establish physical task capability.` : 'No action binding was returned for this instance.'}` };
      if (!showDesign && state.selection && component) return { message: `${component.name}${state.selection.meshName ? ` · ${state.selection.meshName}` : ''} is a source inspection selection. ${component.referenceOnly ? 'Reference only; it is not a generated architecture.' : geometryLabel(component)}. ${editReason}` };
      if (state.selectedStrategyAction && strategySession) {
        const support = strategySession.spec.mechanicalRequirements.filter(m => m.supports.includes(state.selectedStrategyAction!));
        return { message: `${readable(state.selectedStrategyAction)}: ${support.length ? support.map(m => `${readable(m.id)} requires ${m.requirements.map(readable).join(', ')}`).join('; ') : 'No mechanism requirement declared for this action'}. Abstract simulation only; physical task capability remains unverified.` };
      }
      if (strategySession) return { message: `${readable(strategySession.strategyFamily)} prioritizes ${strategySession.spec.scoringPriorities.map(o => readable(o.objective)).join(', ')}. Two saved engineering alternatives implement the same learned requirements. Abstract simulation only; no physical performance is established.` };
      return { message: `Select a source component or generate the default Override strategy to get a contextual explanation. ${editReason}` };
    }
    return { message: `This request is unsupported. I can explain your selection, show strategy or architectures, and preview a lower or raised configuration when qualified. ${editReason}` };
  }
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
    setCanvasMode('reference'); setSelectedDesignInstanceId(null);
    if (state.activeComponentId === c.id) return;
    dispatch({ type: 'component', componentId: c.id }); setScene({ state: 'loading' }); save({ activeComponentId: c.id });
  }
  function selectComponent(c: ComponentDefinition) {
    if (state.activeComponentId !== c.id) openComponent(c);
    dispatch({ type: 'select', selection: { componentId: c.id, catalogMeshSha256: c.meshSha256 } });
  }
  function select(selection: Selection | null) { if (selection) setCanvasMode('reference'); dispatch({ type: 'select', selection }); }
  function panel(next: Panel) { dispatch({ type: 'panel', panel: next }); }
  const panelTitle = state.panel === 'home' ? 'Welcome to Tachyon' : state.panel === 'components' ? 'Components' : state.panel === 'strategy' ? 'Strategy' : state.panel === 'architectures' ? 'Architectures' : 'Preferences';
  const strategyPanelOpen = state.panel === 'strategy' || state.panel === 'architectures';
  const ready = (!!sourceRenderable || showDesign) && scene.state === 'ready';
  const contextLabel = showDesign ? designInstance ? `${readable(designInstance.subsystemId)} · ${designInstance.id}` : `Assembly ${designSession?.designId} · ${designSession?.candidate ? 'candidate preview' : 'accepted revision'}` : state.selection && component ? `${component.name}${state.selection.meshName ? ` · ${state.selection.meshName}` : ''} · source inspection` : state.selectedStrategyAction ? readable(state.selectedStrategyAction) : strategySession ? readable(strategySession.strategyFamily) : 'No selection · default Override';

  return <main className="workspace strategy-workspace" data-theme={state.preferences.theme} data-mode={state.preferences.mode} data-panel={state.panel ?? 'none'} style={{ '--strategy-panel-width': `${panelWidth}px` } as CSSProperties}
    onKeyDown={e => { if (e.key === 'Escape') { if (state.assistantSize !== 'compact') dispatch({ type: 'assistant', size: 'compact' }); else panel(null); } }}>
    <div className="drafting-grid" aria-hidden="true" />
    {sourceRenderable && <Suspense fallback={<span className="sr-only">Loading CAD renderer</span>}><AssemblyScene key={`${sourceRenderable.id}-${sourceRenderable.meshSha256}-${assetAttempt}`} component={sourceRenderable} theme={state.preferences.theme} selection={state.selection} onSelect={select} onStatus={onSceneStatus} resetKey={resetKey} focusKey={focusKey} panelOpen={state.panel !== null} upAxis={upAxis} /></Suspense>}
    {showDesign && designSession && <Suspense fallback={<span className="sr-only">Loading design renderer</span>}><DesignAssemblyScene key={`${designSession.designId}-${assetAttempt}`} session={designSession} theme={state.preferences.theme} activeActionId={state.selectedStrategyAction} selectedInstanceId={selectedDesignInstanceId} onSelectInstance={setSelectedDesignInstanceId} onStatus={onSceneStatus} resetKey={resetKey} focusKey={focusKey} panelOpen={state.panel !== null} /></Suspense>}
    <div className="workspace-topline"><div className="workspace-context"><span className="context-mark" /><span>{showDesign ? `Design ${designSession?.designId}` : component ? component.name : strategySession ? readable(strategySession.strategyFamily) : 'Untitled workspace'}</span><span className="context-divider" /><span className="context-type">{showDesign ? designSession?.candidate ? 'Candidate preview' : 'Assembly revision' : component?.referenceOnly ? 'Imported reference' : component ? 'Source component' : 'Focus'}</span></div><span className="wordmark">TACHYON<span className="wordmark-symbol">↗</span></span></div>
    <AiCore size={state.assistantSize} onSize={size => dispatch({ type: 'assistant', size })} draft={state.commandDraft} onDraft={text => dispatch({ type: 'draft', text })} component={component} selection={showDesign ? null : state.selection} contextLabel={contextLabel} loading={loading || generating || designWorking} onComponents={() => panel('components')} command={command} onIntent={intent => { if (intent === 'showstrategy') openFlow('strategy'); else if (intent === 'showarchitectures') openFlow('architectures'); else { dispatch({ type: 'draft', text: 'Explain this selection' }); } }} controls={{
      canPreview: showDesign && !!designSession?.canEdit && !designSession.candidate,
      canApply: showDesign && !!designSession?.canEdit && !!designSession.candidate,
      canDiscard: !!designSession?.canEdit && !!designSession.candidate,
      canUndo: showDesign && designSession?.status !== 'blocked' && !designSession?.candidate && !!designSession?.previous,
      busy: designWorking, reason: editReason,
      candidateLabel: designSession?.candidate ? `Candidate ${designSession.candidate.id} · preview only; accepted ${designSession.revisionId}` : undefined,
      preview: configuration => edit('preview', configuration), apply: () => edit('apply'), discard: () => edit('discard'), undo: () => edit('undo'),
    }} />
    {!loading && error && <div className="connection-banner" role="alert"><Icon name="info" /><span>{error}</span><button onClick={() => setReload(n => n + 1)}>Retry connection</button></div>}
    {!sourceRenderable && !showDesign && <div className="canvas-empty" data-testid="cad-unavailable"><div className="empty-reticle" aria-hidden="true"><span /><Icon name="parts" size={40} /><span /></div><span className="eyebrow">{loading ? 'CONNECTING WORKSPACE' : 'SOURCE COMPONENT INSPECTION'}</span><h2>{loading ? 'Opening your workspace…' : component ? 'This component is unavailable' : 'Make room for the real thing.'}</h2><p>{loading ? 'Reading the local catalog and workspace capabilities.' : error ? 'Connect this tab to inspect your local source catalog.' : component ? 'The source part is missing permission, valid geometry, or inspection capability.' : 'Qualified local CAD appears here. Your workspace stays empty until real source geometry is available.'}</p>{!loading && <button className="secondary-button" onClick={() => panel('components')}>Open Components <Icon name="arrow" size={16} /></button>}
      {!loading && !!catalog?.blockers.length && <p className="empty-blocker">{catalog.blockers[0].message}</p>}
    </div>}
    {(sourceRenderable || showDesign) && scene.state !== 'ready' && <div className="scene-message" role={scene.state === 'failed' ? 'alert' : 'status'}><Icon name={scene.state === 'failed' ? 'info' : 'parts'} size={26} /><h2>{scene.state === 'failed' ? 'Source geometry could not be displayed' : 'Loading source geometry'}</h2><p>{scene.message ?? 'Fetching the protected GLB and checking its identity.'}</p>{scene.state === 'failed' && <button className="secondary-button" onClick={() => setAssetAttempt(n => n + 1)}>Retry geometry</button>}</div>}
    {sourceRenderable && <div className={`source-status ${sourceRenderable.geometryClass === 'test_fixture' ? 'is-fixture' : ''}`} role="status" data-testid="scene-status" data-state={scene.state} data-component-id={sourceRenderable.id} data-mesh-sha256={sourceRenderable.meshSha256} data-mesh-count={scene.meshCount ?? 0} data-render-bounds={scene.boundsM ? JSON.stringify(scene.boundsM) : undefined}>
      <span className="status-dot" /><span>{geometryLabel(sourceRenderable)}</span><strong>{sourceRenderable.geometryClass === 'test_fixture' ? 'CONVERTER PROOF ONLY · NOT AUTHENTIC VEX' : sourceRenderable.referenceOnly || strategySession ? 'IMPORTED REFERENCE · NOT A GENERATED ROBOT' : 'SOURCE PART · NO ROBOT ASSEMBLY'}</strong>
    </div>}
    {showDesign && <div className={`source-status design-status ${designSession?.qualification.testFixtureOnly ? 'is-fixture' : ''}`} role="status" data-testid="design-status" data-state={scene.state} data-mesh-count={scene.meshCount ?? 0} data-render-bounds={scene.boundsM ? JSON.stringify(scene.boundsM) : undefined}><span className="status-dot" /><strong>{designSession?.qualification.testFixtureOnly ? 'Tachyon-authored non-VEX mechanism · NOT AUTHENTIC VEX / NOT COMPLETE ROBOT' : 'Partial assembly · physical capabilities unverified'}</strong><span>{designSession?.candidate ? 'CANDIDATE PREVIEW · NOT APPLIED' : 'ACCEPTED ASSEMBLY REVISION'}{state.preferences.mode === 'advanced' ? ` · ${displayedRevision?.id}` : ''}</span>{canvasMode === 'design' && renderable && <button className="text-action" onClick={() => setCanvasMode('reference')}>Inspect source reference</button>}</div>}
    {!showDesign && state.selection && <div className="selection-chip" data-component-id={state.selection.componentId} data-native-node-id={state.selection.nativeNodeId}><Icon name="parts" size={16} /><span><strong>{component?.name}</strong><small>{state.selection.meshName ?? component?.sku} · selected</small></span><button className="icon-button" aria-label="Inspect selection" onClick={() => panel('components')}><Icon name="info" size={16} /></button><button className="icon-button" aria-label="Clear selection" onClick={() => select(null)}><Icon name="close" size={16} /></button></div>}
    {showDesign && designInstance && <div className="selection-chip design-selection-chip"><Icon name="parts" size={16} /><span><strong>{readable(designInstance.subsystemId)}</strong><small>{designInstance.id} · displayed revision</small>{reverseActions.map(a => <button key={a.actionId} className="text-action" onClick={() => { selectAction(a.actionId); panel('strategy'); }}>{readable(a.actionId)}</button>)}</span><button className="icon-button" aria-label="Clear design selection" onClick={() => setSelectedDesignInstanceId(null)}><Icon name="close" size={16} /></button></div>}
    {state.panel && <PanelHost key={state.panel} title={panelTitle} subtitle={state.panel === 'home' ? 'COMPLICATEDLY SIMPLE' : state.panel === 'components' ? 'INSPECT / SOURCE / IDENTITY' : state.panel === 'strategy' ? 'RULES INTO ACTION' : state.panel === 'architectures' ? 'ONE STRATEGY, TWO APPROACHES' : 'MAKE IT YOURS'} onClose={() => panel(null)}>
      {strategyPanelOpen && <div className="strategy-panel-tools"><div className="strategy-panel-tabs"><button aria-pressed={state.panel === 'strategy'} onClick={() => openFlow('strategy')}>Strategy</button><button aria-pressed={state.panel === 'architectures'} onClick={() => openFlow('architectures')}>Architectures</button></div><label className="strategy-width-control">Panel width<input type="range" min="360" max="760" step="20" value={panelWidth} onChange={e => setPanelWidth(Number(e.target.value))} /></label>{designSession?.accepted && !showDesign && <button className="text-action" onClick={() => { setCanvasMode('design'); setScene({ state: 'loading' }); }}>Return to assembly revision</button>}</div>}
      {state.panel === 'home' && <Home catalog={catalog} capabilities={capabilities} onInspect={() => panel('components')} strategyStatus={strategyStatus} strategyLoading={strategyChecking} generating={generating} onGenerateStrategy={() => openFlow('strategy')} onCreateRobot={() => openFlow('architectures')} strategyError={strategyError} onRetryStrategy={() => setReload(n => n + 1)} />}
      {state.panel === 'strategy' && <StrategyPanel session={strategySession} loading={generating} error={strategyError ?? (!strategyStatus?.available ? strategyStatus?.reason : null)} mode={state.preferences.mode} selectedActionId={state.selectedStrategyAction} onSelectAction={selectAction} onGenerate={() => void generate('strategy')} onArchitectures={() => openFlow('architectures')} available={!!strategyStatus?.available} assembly={showDesign?designSession:null} />}
      {state.panel === 'architectures' && <ArchitecturesPanel session={strategySession} loading={generating} error={strategyError ?? (!strategyStatus?.available ? strategyStatus?.reason : null)} mode={state.preferences.mode} selectedArchitectureId={state.selectedArchitectureId} selectedActionId={state.selectedStrategyAction} realization={realization} onSelectArchitecture={architectureId => dispatch({ type: 'architecture', architectureId })} onRealizeArchitecture={realizeArchitecture} onInspectReference={() => { setCanvasMode('reference'); panel('components'); }} onStrategy={() => panel('strategy')} onGenerate={() => void generate('architectures')} available={!!strategyStatus?.available} />}
      {state.panel === 'components' && (showDesign && designSession ? <AssemblyInspector session={designSession} selectedId={selectedDesignInstanceId} onSelect={id=>{setSelectedDesignInstanceId(id);setFocusKey(n=>n+1);}} onSource={id=>{const source=catalog?.components.find(c=>c.id===id);if(source)openComponent(source);}}/> : <>{strategySession && <p className="strategy-notice">Source inspection reference only. This is not the selected architecture’s generated CAD.</p>}<ComponentsPanel catalog={catalog} activeId={state.activeComponentId} mode={state.preferences.mode} canInspect={connected && !!capabilities?.canInspect} onOpen={openComponent} onSelect={selectComponent} onSelectNode={(c, nativeNodeId, meshName) => select({ componentId: c.id, catalogMeshSha256: c.meshSha256, nativeNodeId, meshName })} /></>)}
      {state.panel === 'preferences' && <PreferencesPanel preferences={state.preferences} onChange={preferences} disabled={!connected} />}
    </PanelHost>}
    <div className="workspace-bottomline"><span className="gesture-hint"><Icon name="orbit" size={14} /> <span className="desktop-hint">Drag to orbit · Scroll to zoom · Right-drag to pan</span><span className="mobile-hint">Drag to orbit · Pinch to zoom · Two fingers to pan</span></span><span className="workspace-version">{health ? `LOCAL / ${health.version}` : 'LOCAL WORKSPACE'}<span className="unit-label">m</span></span></div>
    <div className="workspace-dock"><nav aria-label="Workspace tools">{([{ id: 'home', icon: 'home', title: 'Home' }, { id: 'strategy', icon: 'orbit', title: 'Strategy' }, { id: 'architectures', icon: 'parts', title: 'Architectures' }, { id: 'components', icon: 'parts', title: 'Components' }, { id: 'preferences', icon: 'settings', title: 'Preferences' }] as const).map(item => <button key={item.id} aria-pressed={state.panel === item.id} onClick={() => state.panel === item.id ? panel(null) : item.id === 'strategy' || item.id === 'architectures' ? openFlow(item.id) : panel(item.id)}><Icon name={item.icon} /><span>{item.title}</span></button>)}</nav><span className="dock-divider" /><ViewControls disabled={!ready} onFocus={() => setFocusKey(n => n + 1)} onReset={() => setResetKey(n => n + 1)} upAxis={showDesign ? 'Y' : upAxis} onUpAxis={showDesign ? undefined : () => setUpAxis(value => value === 'Z' ? 'X' : value === 'X' ? 'Y' : 'Z')} /></div>
    <div className={`save-state save-${saveState}`} role="status">{saveState === 'saving' ? 'Saving preferences…' : saveState === 'unsaved' ? <>Unsaved preferences <button onClick={() => save(pendingPatch.current)}>Retry save</button></> : connected ? 'Local workspace' : 'Not connected'}</div>
  </main>;
}
