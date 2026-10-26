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
import { OperationPanel,useOperationPlayback } from '../panels/OperationPanel';
import { Home } from '../screens/Home';
import type { SceneStatus } from '../viewer/AssemblyScene';
import type { DesignSceneStatus } from '../viewer/DesignAssemblyScene';
import { ViewControls } from '../viewer/ViewControls';
import { loadDesignCatalog,type DesignCatalog } from '../api/designCatalog';
import { ArchitectureDrawing,architectureName } from '../studio/ArchitectureDrawing';
import { TachyonWordmark } from '../studio/Mechanical';
import { initialState, workspaceReducer, type Panel } from './reducer';
import '../styles/strategy.css';
import '../styles/studio.css';
import '../styles/demo.css';

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
  const [scene, setScene] = useState<DesignSceneStatus>({ state: 'idle' });
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
  const [designSessions,setDesignSessions]=useState<Record<string,DesignSession>>({});
  const [designCatalog,setDesignCatalog]=useState<DesignCatalog|null>(null);
  const [operation,setOperation]=useOperationPlayback();
  const [colorSubsystems,setColorSubsystems]=useState(false);
  const [selectedDesignInstanceId, setSelectedDesignInstanceId] = useState<string | null>(null);
  const [canvasMode, setCanvasMode] = useState<'reference' | 'design' | 'concept'>('reference');
  const [panelWidth, setPanelWidth] = useState(480);
  const [studioLayout,setStudioLayout]=useState<'focus'|'split'|'studio'|'custom'>(()=>{try{const v=localStorage.getItem('tachyon.studio-layout');return v==='split'||v==='studio'||v==='custom'?v:'focus';}catch{return 'focus';}});
  const [toolsCollapsed,setToolsCollapsed]=useState(false);
  const saveQueue = useRef(Promise.resolve());
  const saveSequence = useRef(0);
  const pendingPatch = useRef<WorkspacePatch>({});
  const initialized = useRef(false);
  const preferencesReturn=useRef<Panel>(null),assistantReturn=useRef<Panel>(null);

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
  useEffect(()=>{const abort=new AbortController();Promise.resolve().then(()=>loadDesignCatalog(abort.signal)).then(setDesignCatalog).catch(()=>{if(!abort.signal.aborted)setDesignCatalog(null);});return()=>abort.abort();},[reload]);
  useEffect(()=>{try{localStorage.setItem('tachyon.studio-layout',studioLayout);}catch{/* Layout remains usable in this tab. */}},[studioLayout]);

  const component = catalog?.components.find(c => c.id === state.activeComponentId);
  const renderable = component && connected && capabilities?.canInspect && isInspectable(component) ? component : undefined;
  const onSceneStatus = useCallback((s: SceneStatus) => setScene(s), []);
  const showDesign = canvasMode === 'design' && !!designSession?.accepted && !!designSession.components.length;
  const selectedArchitecture=strategySession?.architectures.find(a=>a.id===state.selectedArchitectureId);
  const showConcept=canvasMode==='concept'&&!!selectedArchitecture;
  useEffect(()=>{if(!showDesign)setOperation(null);},[showDesign,setOperation]);
  const sourceRenderable = canvasMode==='reference'&&state.panel!=='home'&&!showDesign ? renderable : undefined;
  const displayedRevision = designSession?.candidate ?? designSession?.accepted;
  const displayedBindings = designSession?.candidate ? designSession.candidateBindings : designSession?.bindings;
  // Report every requested placement, including hardware; no presentation quota.
  const displayedInstances = displayedRevision?.assembly.instances ?? [];
  const displayedComponents = new Map(designSession?.components.map(c => [c.id, c]));
  const unresolvedGeometryIds = displayedInstances.filter(node => {
    const source = displayedComponents.get(node.componentId);
    return !source || source.referenceOnly || !isInspectable(source);
  }).map(node => node.id);
  const geometryAssetCount = new Set(displayedInstances.map(node => node.componentId)).size;
  const sceneResolution = scene.geometryResolution?.revisionId === displayedRevision?.id ? scene.geometryResolution : undefined;
  const missingGeometryIds = sceneResolution?.missingInstanceIds ?? unresolvedGeometryIds;
  const requestedPlacements = sceneResolution?.requestedInstanceCount ?? displayedInstances.length;
  const resolvedPlacements = sceneResolution?.resolvedInstanceCount ?? displayedInstances.length - missingGeometryIds.length;
  const loadedPlacements = sceneResolution?.loadedInstanceCount ?? (scene.state === 'ready' ? resolvedPlacements : 0);
  const developmentCad = displayedInstances.some(node => {
    const source = displayedComponents.get(node.componentId);
    return source?.originKind === 'tachyon_authored' && source.geometryClass === 'test_fixture';
  });
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
      setRealization({ state: 'idle' }); setDesignSession(null); setSelectedDesignInstanceId(null); setCanvasMode('concept');
      setDesignSessions(previous=>Object.fromEntries(Object.entries(previous).filter(([,d])=>d.strategyId===next.spec.id)));
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
    if(!['acquire_cup','place_cup'].includes(actionId))setOperation(null);
    dispatch({ type: 'strategy-action', action: actionId }); setSelectedDesignInstanceId(null); setFocusKey(n => n + 1);
  }
  function selectArchitecture(architectureId:string){
    if(designSession?.candidate&&designSession.architectureId!==architectureId){setStrategyError('Apply or discard the current preview before switching designs.');return;}
    if(designBusy.current)return;
    setOperation(null);setStrategyError(null);setSelectedDesignInstanceId(null);
    dispatch({type:'architecture',architectureId});dispatch({type:'strategy-action',action:null});
    const cached=designSessions[architectureId];
    if(cached?.accepted){setDesignSession(cached);setCanvasMode('design');if(!showDesign||designSession?.architectureId!==architectureId)setScene({state:'loading'});}
    else {setDesignSession(cached??null);setCanvasMode('concept');}
  }
  function acceptDesignResponse(next: DesignSession) {
    setOperation(null);
    setDesignSessions(previous=>({...previous,[next.architectureId]:next}));
    setDesignSession(next); setRealization({ state: 'loaded', architectureId: next.architectureId, result: next });
    setSelectedDesignInstanceId(null); setFocusKey(n => n + 1);
    if (next.accepted && next.components.length) {
      setCanvasMode('design');
      if (!showDesign || (next.candidate ?? next.accepted).id !== displayedRevision?.id) setScene({ state: 'loading' });
    }else setCanvasMode('concept');
  }
  async function openSavedDesign(id:string){
    if(designBusy.current||generationBusy.current)return;
    if(designSession?.candidate){setStrategyError('Apply or discard the current preview before opening another saved build.');return;}
    designBusy.current=true;setDesignWorking(true);setStrategyError(null);
    try{
      const strategy=strategySession??await api.generateStrategy();
      const next=parseDesignSession(await api.get(`/api/designs/${encodeURIComponent(id)}`));
      if(next.strategyId!==strategy.spec.id)throw new Error('The saved assembly belongs to a different strategy context.');
      setStrategySession(strategy);dispatch({type:'architecture',architectureId:next.architectureId});acceptDesignResponse(next);panel(null);
    }catch(reason){setStrategyError(errorMessage(reason));}finally{designBusy.current=false;setDesignWorking(false);}
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
      if(result.accepted&&result.components.length)panel(null);
      void loadDesignCatalog().then(setDesignCatalog).catch(()=>{});
    } catch (reason) { setRealization({ state: 'failed', architectureId, message: errorMessage(reason) }); }
    finally { designBusy.current = false; setDesignWorking(false); }
  }
  const editReason = !designSession?.canEdit
    ? `Editing requires a qualified mechanism recipe, components, and assembly placement. ${designSession?.missing.map(m => m.message).join(' ') || 'Realize an architecture to inspect the missing qualifications.'}`
    : !showDesign ? showConcept?'This is an architecture schematic. Open its actual assembly before previewing a design revision.':'Source inspection references cannot be edited. Return to the assembly revision to preview or apply a supported mechanism change.'
    : designSession.candidate ? 'Previewing a candidate revision. Apply accepts this exact candidate; Discard preserves the accepted revision.' : 'Supported edits: lower or raised scoring configuration. Preview before Apply.';
  async function edit(action: 'preview' | 'apply' | 'discard' | 'undo', configuration?: 'lower' | 'raised'): Promise<CommandResult> {
    setOperation(null);
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
      if(showConcept&&selectedArchitecture)return {message:`Design ${selectedArchitecture.alternative}: ${architectureName(selectedArchitecture)}. ${selectedArchitecture.subsystems.slice(0,4).map(s=>`${readable(s.id)}: ${readable(s.mechanismIntent)}`).join('; ')}. This is proposed mechanism intent, not realized or physically validated CAD.`};
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
  function panel(next: Panel) { if(next==='preferences'&&state.panel!=='preferences')preferencesReturn.current=state.panel;dispatch({ type: 'panel', panel: next }); }
  function closePanel(){panel(state.panel==='preferences'?preferencesReturn.current:null);}
  function assistant(size:'compact'|'expanded'|'fullscreen'){
    if(state.assistantSize==='compact'&&size!=='compact')assistantReturn.current=state.panel;
    dispatch({type:'assistant',size});
    if(size==='compact'&&assistantReturn.current)panel(assistantReturn.current);
  }
  const panelTitle = state.panel === 'home' ? 'Studio' : state.panel === 'components' ? 'Components' : state.panel === 'strategy' ? 'Strategy' : state.panel === 'architectures' ? 'Design' : 'Preferences';
  const strategyPanelOpen = state.panel === 'strategy' || state.panel === 'architectures';
  const ready = (!!sourceRenderable || showDesign) && scene.state === 'ready';
  const contextLabel = showConcept&&selectedArchitecture?`Design ${selectedArchitecture.alternative} · ${architectureName(selectedArchitecture)} · architecture schematic`:showDesign ? designInstance ? `${readable(designInstance.subsystemId)} · ${designInstance.id}` : `${selectedArchitecture?architectureName(selectedArchitecture):'Robot assembly'} · ${designSession?.candidate ? 'candidate preview' : 'accepted assembly'}` : state.selection && component ? `${component.name}${state.selection.meshName ? ` · ${state.selection.meshName}` : ''} · source inspection` : state.selectedStrategyAction ? readable(state.selectedStrategyAction) : strategySession ? readable(strategySession.strategyFamily) : 'No selection · default Override';

  function inspectMechanism(ask=false){
    const binding=displayedBindings?.actions.find(a=>a.actionId===state.selectedStrategyAction);
    if(binding){setSelectedDesignInstanceId(binding.instanceIds.find(id=>!/(bolt|nut|washer|spacer|collar|bearing)/.test(id))??binding.instanceIds[0]??null);setFocusKey(n=>n+1);}
    if(ask)assistant('expanded');else panel('components');
  }
  const selectedDesignNumber=selectedArchitecture?String((strategySession?.architectures.indexOf(selectedArchitecture)??0)+1).padStart(2,'0'):null;
  const applyLayout=(layout:typeof studioLayout)=>{setStudioLayout(layout);if(layout==='focus')panel(null);else if(layout==='split'||layout==='studio')panel('strategy');};
  return <main className="workspace strategy-workspace studio-workspace" data-theme={state.preferences.theme} data-mode={state.preferences.mode} data-panel={state.panel??'none'} data-layout={studioLayout} data-tools={toolsCollapsed?'hidden':'visible'} data-canvas={showDesign?'assembly':showConcept?'concept':sourceRenderable?'source':'empty'} style={{'--strategy-panel-width':`${panelWidth}px`,'--studio-panel-width':`${panelWidth}px`} as CSSProperties}
    onKeyDown={e=>{if(e.key==='Escape'){if(toolsCollapsed)setToolsCollapsed(false);else if(state.assistantSize!=='compact')assistant('compact');else closePanel();}}}>
    <div className="drafting-grid" aria-hidden="true"/>
    {sourceRenderable&&<Suspense fallback={<span className="sr-only">Loading CAD renderer</span>}><AssemblyScene key={`${sourceRenderable.id}-${sourceRenderable.meshSha256}-${assetAttempt}`} component={sourceRenderable} theme={state.preferences.theme} selection={state.selection} onSelect={select} onStatus={onSceneStatus} resetKey={resetKey} focusKey={focusKey} panelOpen={state.panel!==null} upAxis={upAxis}/></Suspense>}
    {showDesign&&designSession&&<Suspense fallback={<span className="sr-only">Loading design renderer</span>}><DesignAssemblyScene key={`${designSession.designId}-${assetAttempt}`} session={designSession} theme={state.preferences.theme} activeActionId={state.selectedStrategyAction} selectedInstanceId={selectedDesignInstanceId} onSelectInstance={setSelectedDesignInstanceId} onStatus={onSceneStatus} resetKey={resetKey} focusKey={focusKey} panelOpen={state.panel!==null} operation={operation} colorSubsystems={colorSubsystems}/></Suspense>}
    {showConcept&&selectedArchitecture&&<section className="concept-canvas" data-testid="concept-canvas" data-architecture-id={selectedArchitecture.id} aria-label={`Design ${selectedDesignNumber} architecture preview`}><div className="concept-sheet"><span className="eyebrow">DESIGN {selectedDesignNumber} / ARCHITECTURE PREVIEW</span><h2>{architectureName(selectedArchitecture)}</h2><ArchitectureDrawing architecture={selectedArchitecture} activeActionId={state.selectedStrategyAction}/><div className="concept-stamp"><strong>CONCEPTUAL SCHEMATIC</strong><span>Not CAD · not to scale · assembly not realized in this view</span></div></div></section>}
    <header className="workspace-topline"><div className="workspace-context"><span className="context-mark"/><span>OVERRIDE / {state.panel==='home'?'STUDIO':selectedDesignNumber?`DESIGN ${selectedDesignNumber}`:sourceRenderable?'SOURCE INSPECTION':'STUDIO'}</span><span className="context-divider"/><span className="context-type">{state.panel==='home'?'STRATEGY INTO MACHINERY':showDesign?designSession?.candidate?'REVISION PREVIEW':'COMPONENT ASSEMBLY':showConcept?'SCHEMATIC':'STRATEGY INTO MACHINERY'}</span></div><span className="wordmark"><TachyonWordmark/></span></header>
    {strategySession&&state.panel!=='home'&&<nav className="design-switcher" aria-label="Switch robot design">{strategySession.architectures.map((a,index)=><button key={a.id} aria-label={`Select Design ${String(index+1).padStart(2,'0')}`} aria-pressed={a.id===state.selectedArchitectureId} onClick={()=>selectArchitecture(a.id)}><span>{String(index+1).padStart(2,'0')}</span><strong>{architectureName(a)}</strong><small>{designSessions[a.id]?.accepted?'PARTIAL CAD':'CONCEPT'}</small></button>)}</nav>}
    <AiCore size={state.assistantSize} onSize={assistant} draft={state.commandDraft} onDraft={text=>dispatch({type:'draft',text})} component={showConcept?undefined:component} selection={showDesign||showConcept?null:state.selection} contextLabel={contextLabel} loading={loading||generating||designWorking} onComponents={()=>panel('components')} command={command} onIntent={intent=>{if(intent==='showstrategy')openFlow('strategy');else if(intent==='showarchitectures')openFlow('architectures');else dispatch({type:'draft',text:'Explain this selection'});}} controls={{
      canPreview:showDesign&&!!designSession?.canEdit&&!designSession.candidate,canApply:showDesign&&!!designSession?.canEdit&&!!designSession.candidate,canDiscard:showDesign&&!!designSession?.canEdit&&!!designSession.candidate,canUndo:showDesign&&designSession?.status!=='blocked'&&!designSession?.candidate&&!!designSession?.previous,busy:designWorking,reason:editReason,
      candidateLabel:designSession?.candidate?'Candidate preview · not applied':undefined,preview:configuration=>edit('preview',configuration),apply:()=>edit('apply'),discard:()=>edit('discard'),undo:()=>edit('undo'),
    }}/>
    {strategyError&&strategySession&&state.panel===null&&<div className="design-transition-note" role="alert"><Icon name="info"/><p>{strategyError}</p><button className="text-action" onClick={()=>assistant('expanded')}>Review preview</button><button className="icon-button" aria-label="Dismiss design message" onClick={()=>setStrategyError(null)}><Icon name="close"/></button></div>}
    {!loading&&error&&<div className="connection-banner" role="alert"><Icon name="info"/><span>{error}</span><button onClick={()=>setReload(n=>n+1)}>Retry connection</button></div>}
    {!sourceRenderable&&!showDesign&&!showConcept&&state.panel!=='home'&&state.panel!=='strategy'&&<div className="canvas-empty" data-testid="cad-unavailable"><div className="empty-reticle" aria-hidden="true"><span/><Icon name="parts" size={40}/><span/></div><span className="eyebrow">{loading?'CONNECTING STUDIO':'READY FOR YOUR NEXT MACHINE'}</span><h2>{loading?'Opening your workspace…':'Your design bench.'}</h2><p>{error?'Connect this tab to inspect your local catalog.':'Choose a mechanical approach, construct an available recipe, or inspect your own source CAD.'}</p><button className="secondary-button" onClick={()=>strategySession?openFlow('architectures'):panel('home')}>{strategySession?'Choose a design':'Open studio'}<Icon name="arrow"/></button></div>}
    {(sourceRenderable||showDesign)&&scene.state!=='ready'&&<div className="scene-message" role={scene.state==='failed'?'alert':'status'}><Icon name={scene.state==='failed'?'info':'parts'} size={26}/><h2>{scene.state==='failed'?'Geometry could not be displayed':'Assembling the view…'}</h2><p>{scene.message??'Loading checked component geometry and placements.'}</p>{scene.state==='failed'&&<button className="secondary-button" onClick={()=>setAssetAttempt(n=>n+1)}>Retry geometry</button>}</div>}
    {sourceRenderable&&<details className={`source-status source-receipt ${sourceRenderable.geometryClass==='test_fixture'?'is-fixture':''}`} data-testid="scene-status" data-state={scene.state} data-component-id={sourceRenderable.id} data-mesh-sha256={sourceRenderable.meshSha256} data-mesh-count={scene.meshCount??0} data-render-bounds={scene.boundsM?JSON.stringify(scene.boundsM):undefined}><summary><span className="status-dot"/>{sourceRenderable.referenceOnly?'Imported reference':'Source component'}<Icon name="info" size={14}/></summary><p>{geometryLabel(sourceRenderable)}</p><strong>{sourceRenderable.geometryClass==='test_fixture'?'ORIGINAL DEVELOPMENT CAD · NOT AUTHENTIC VEX':sourceRenderable.referenceOnly||strategySession?'IMPORTED REFERENCE · NOT A GENERATED ROBOT':'SOURCE PART · NO ROBOT ASSEMBLY'}</strong></details>}
    {showDesign&&<details className={`source-status design-status ${developmentCad?'is-fixture':''}`} data-testid="design-status" data-state={scene.state} data-mesh-count={scene.meshCount??0} data-requested-instance-count={requestedPlacements} data-resolved-instance-count={resolvedPlacements} data-loaded-instance-count={loadedPlacements} data-geometry-asset-count={geometryAssetCount} data-missing-instance-ids={JSON.stringify(missingGeometryIds)} data-render-bounds={scene.boundsM?JSON.stringify(scene.boundsM):undefined}><summary><span className="status-dot"/><strong>{designSession?.candidate?'PREVIEW · NOT APPLIED':designSession?.qualification.completeRobot?'COMPONENT ASSEMBLY':'PARTIAL ASSEMBLY'}</strong><span>{developmentCad?'Independent CAD · clearance conflicts':'Source CAD · physical fit unverified'}</span><Icon name="info" size={14}/></summary><div className="receipt-content"><p>{developmentCad?'Tachyon-authored development CAD · NOT AUTHENTIC VEX / NOT COMPLETE ROBOT. The current development recipe has known frame and shaft intersections.':'Source identities are preserved. Geometry and connections alone do not establish physical robot performance.'}</p><p>{resolvedPlacements}/{requestedPlacements} placements resolve · {loadedPlacements} loaded · {geometryAssetCount} geometry assets{missingGeometryIds.length?` · Missing: ${missingGeometryIds.join(', ')}`:''}</p><p>Constructed from an authored assembly recipe; not an unrestricted new-robot generator.</p>{state.preferences.mode==='advanced'&&<code>{displayedRevision?.id}</code>}</div></details>}
    {showDesign&&displayedRevision&&<nav className="subsystem-controls" aria-label="Robot subsystems">{displayedRevision.assembly.subsystems.filter(s=>displayedBindings?.actions.some(a=>a.subsystemId===s.id)).map(s=><button key={s.id} aria-pressed={displayedBindings?.actions.find(a=>a.actionId===state.selectedStrategyAction)?.subsystemId===s.id} onClick={()=>{const action=displayedBindings?.actions.find(a=>a.subsystemId===s.id);if(action)selectAction(action.actionId);}}><i/><span>{readable(s.id)}</span></button>)}</nav>}
    {!showDesign&&!showConcept&&state.selection&&<div className="selection-chip" data-component-id={state.selection.componentId} data-native-node-id={state.selection.nativeNodeId}><Icon name="parts" size={16}/><span><strong>{component?.name}</strong><small>{state.selection.meshName??component?.sku} · selected</small></span><button className="icon-button" aria-label="Inspect selection" onClick={()=>panel('components')}><Icon name="info" size={16}/></button><button className="icon-button" aria-label="Clear selection" onClick={()=>select(null)}><Icon name="close" size={16}/></button></div>}
    {showDesign&&designInstance&&<div className="selection-chip design-selection-chip"><Icon name="parts" size={16}/><span><strong>{readable(designInstance.subsystemId)}</strong><small>{designInstance.id}</small>{reverseActions.map(a=><button key={a.actionId} className="text-action" onClick={()=>{selectAction(a.actionId);panel('strategy');}}>{readable(a.actionId)}</button>)}</span><button className="icon-button" aria-label="Clear design selection" onClick={()=>setSelectedDesignInstanceId(null)}><Icon name="close" size={16}/></button></div>}
    {studioLayout==='studio'&&showDesign&&displayedRevision&&<aside className="studio-assembly-rail" aria-label="Studio assembly tree"><span className="eyebrow">ASSEMBLY / {displayedRevision.assembly.instances.length}</span>{displayedRevision.assembly.subsystems.map(sub=><details key={sub.id}><summary>{readable(sub.id)}</summary>{displayedRevision.assembly.instances.filter(n=>n.subsystemId===sub.id).map(n=><button key={n.id} aria-pressed={n.id===selectedDesignInstanceId} onClick={()=>{setSelectedDesignInstanceId(n.id);setFocusKey(v=>v+1);}}>{n.id}</button>)}</details>)}</aside>}
    {state.panel&&<PanelHost key={state.panel} defaultHeight={state.panel==='strategy'?68:56} title={panelTitle} subtitle={state.panel==='home'?'COMPLICATEDLY SIMPLE':state.panel==='components'?'PARTS / CONNECTIONS / SOURCES':state.panel==='strategy'?'VISUAL PLAYBOOK':state.panel==='architectures'?'MECHANICAL DESIGN BENCH':'CONFIGURE YOUR STUDIO'} onClose={closePanel}>
      {strategyPanelOpen&&state.preferences.mode==='advanced'&&<label className="strategy-width-control">Panel width<input type="range" min="360" max="760" step="20" value={panelWidth} onChange={e=>setPanelWidth(Number(e.target.value))}/></label>}
      {state.panel==='home'&&<Home catalog={catalog} capabilities={capabilities} onInspect={()=>panel('components')} strategyStatus={strategyStatus} strategyLoading={strategyChecking} generating={generating||designWorking} onGenerateStrategy={()=>openFlow('strategy')} onCreateRobot={()=>openFlow('architectures')} strategyError={error?null:strategyError} onRetryStrategy={()=>setReload(n=>n+1)} designCatalog={designCatalog} onOpenSavedDesign={id=>void openSavedDesign(id)}/>}
      {state.panel==='strategy'&&<><StrategyPanel architectureId={state.selectedArchitectureId} session={strategySession} loading={generating} error={strategyError??(!strategyStatus?.available?strategyStatus?.reason:null)} mode={state.preferences.mode} selectedActionId={state.selectedStrategyAction} onSelectAction={selectAction} onGenerate={()=>void generate('strategy')} onArchitectures={()=>openFlow('architectures')} available={!!strategyStatus?.available} assembly={showDesign?designSession:null} onInspectMechanism={()=>inspectMechanism()} onAskMechanism={()=>inspectMechanism(true)}/>{showDesign&&designSession?.components.some(c=>c.id==='dev_cup_bridge')&&<details className="operation-drawer" open={['acquire_cup','place_cup'].includes(state.selectedStrategyAction??'')}><summary>Cup joint preview <span>DEVELOPMENT MECHANISM</span></summary><OperationPanel session={designSession} playback={operation} onChange={setOperation}/></details>}</>}
      {state.panel==='architectures'&&<ArchitecturesPanel session={strategySession} loading={generating} error={strategyError??(!strategyStatus?.available?strategyStatus?.reason:null)} mode={state.preferences.mode} selectedArchitectureId={state.selectedArchitectureId} selectedActionId={state.selectedStrategyAction} realization={realization} onSelectArchitecture={selectArchitecture} onRealizeArchitecture={realizeArchitecture} onInspectReference={()=>{setCanvasMode('reference');panel('components');}} onStrategy={()=>panel('strategy')} onGenerate={()=>void generate('architectures')} available={!!strategyStatus?.available} designCatalog={designCatalog} designSessions={designSessions} onOpenSavedDesign={id=>void openSavedDesign(id)} onInspectAssembly={id=>{selectArchitecture(id);panel(null);}}/>}
      {state.panel==='components'&&(showDesign&&designSession?<AssemblyInspector session={designSession} selectedId={selectedDesignInstanceId} onSelect={id=>{setSelectedDesignInstanceId(id);setFocusKey(n=>n+1);}} colorSubsystems={colorSubsystems} onColorSubsystems={()=>setColorSubsystems(v=>!v)} onSource={id=>{const source=catalog?.components.find(c=>c.id===id);if(source)openComponent(source);}}/>:<>{showConcept&&<p className="strategy-notice">This design is a schematic. These are separate local source components, not its realized assembly.</p>}<ComponentsPanel catalog={catalog} activeId={state.activeComponentId} mode={state.preferences.mode} canInspect={connected&&!!capabilities?.canInspect} onOpen={openComponent} onSelect={selectComponent} onSelectNode={(c,nativeNodeId,meshName)=>select({componentId:c.id,catalogMeshSha256:c.meshSha256,nativeNodeId,meshName})}/></>)}
      {state.panel==='preferences'&&<PreferencesPanel preferences={state.preferences} onChange={preferences} disabled={!connected} layout={studioLayout} onLayout={applyLayout}/>}
    </PanelHost>}
    <div className="workspace-bottomline"><span className="gesture-hint"><Icon name="orbit" size={14}/><span className="desktop-hint">ORBIT / DRAG · ZOOM / SCROLL · PAN / RIGHT DRAG</span><span className="mobile-hint">ORBIT / DRAG · ZOOM / PINCH</span></span><span className="workspace-version">{health?'LOCAL STUDIO':'OFFLINE'}<span className="unit-label">m</span></span></div>
    <div className="workspace-dock"><button className="dock-home" aria-label="Home" aria-pressed={state.panel==='home'} onClick={()=>panel('home')}><Icon name="home"/></button><span className="dock-divider"/><nav aria-label="Workspace tools">{([{id:'architectures',icon:'design',title:'Design'},{id:'strategy',icon:'strategy',title:'Strategy'},{id:'components',icon:'components',title:'Components'}] as const).map(item=><button key={item.id} aria-pressed={state.panel===item.id} onClick={()=>{setToolsCollapsed(false);if(state.panel===item.id)panel(null);else if(item.id==='strategy'||item.id==='architectures')openFlow(item.id);else panel(item.id);}}><Icon name={item.icon}/><span>{item.title}</span></button>)}</nav><span className="dock-divider"/><button aria-label="Preferences" aria-pressed={state.panel==='preferences'} onClick={()=>panel('preferences')}><Icon name="settings"/></button></div>
    <div className="cad-utility-rail"><ViewControls disabled={!ready} onFocus={()=>setFocusKey(n=>n+1)} onReset={()=>setResetKey(n=>n+1)} upAxis={showDesign?'Y':upAxis} onUpAxis={showDesign||showConcept?undefined:()=>setUpAxis(v=>v==='Z'?'X':v==='X'?'Y':'Z')}/><button className="icon-button" aria-label={toolsCollapsed?'Show workspace tools':'Hide workspace tools'} onClick={()=>{if(!toolsCollapsed)panel(null);setToolsCollapsed(v=>!v);}}><Icon name={toolsCollapsed?'expand':'collapse'}/></button></div>
    <div className={`save-state save-${saveState}`} role="status">{saveState==='saving'?'Saving preferences…':saveState==='unsaved'?<>Unsaved preferences <button onClick={()=>save(pendingPatch.current)}>Retry save</button></>:connected?'LOCAL / CONNECTED':'CONNECTING'}</div>
  </main>;
}
