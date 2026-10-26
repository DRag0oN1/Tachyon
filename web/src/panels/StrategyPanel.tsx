import { useEffect, useId, useState } from 'react';
import type { Mode } from '../api/contracts';
import { OVERRIDE_MANUAL_URL, capabilityValue, formatNumber, readable, type StrategyEvent, type StrategySession, type DesignSession } from '../api/strategy';
import { AssemblySketch } from './AssemblySketch';
import { DockFrame } from '../studio/Mechanical';
import { ArchitectureDrawing, architectureName } from '../studio/ArchitectureDrawing';
import { buildPlaybookDrawing, buildStrategyPhases, phaseAssemblyLink, phaseRequirements, type PlaybookPhase } from './strategyPlaybook';
import '../styles/playbook.css';

export interface StrategyPanelProps {
  session: StrategySession | null;
  loading: boolean;
  error?: string | null;
  mode?: Mode;
  selectedActionId: string | null;
  onSelectAction: (actionId: string) => void;
  onGenerate: () => void;
  onArchitectures: () => void;
  available?: boolean;
  assembly?: DesignSession | null;
  onInspectMechanism?: () => void;
  onAskMechanism?: () => void;
  architectureId?: string | null;
}

function Playbook({ events, phase, actionId }: { events: StrategyEvent[]; phase: PlaybookPhase; actionId: string }) {
  const arrowId = useId().replaceAll(':', '') + '-travel';
  const drawing = buildPlaybookDrawing(events);
  const active = new Set(phase.eventIndices);
  const focus = phase.events.find(e => e.action === actionId);
  return <figure className="playbook-map">
    <svg role="img" aria-label="Annotated abstract playbook from the selected simulation sequence" viewBox="0 0 340 300">
      <defs><marker id={arrowId} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M1 1 7 4 1 7" fill="none" stroke="var(--blue)" strokeWidth="1.5" /></marker></defs>
      <rect className="phase-map-plane" x="12" y="12" width="316" height="272" rx="5" />
      <path className="phase-map-grid" d="M44 40V254H302M44 110H302M44 182H302M126 40V254M210 40V254M294 40V254" />
      <text className="phase-map-caption" x="24" y="30">OBSERVED SIMULATION PATH</text>
      {drawing.routes.map(route => <path key={route.index} className={`phase-map-route${active.has(route.index) ? ' is-active' : ''}${route.success ? '' : ' is-incomplete'}`}
        markerEnd={active.has(route.index) ? `url(#${arrowId})` : undefined} d={`M${route.from.join(' ')}L${route.to.join(' ')}`}><title>{readable(route.actionId)} · {route.success ? 'arrived' : 'incomplete travel attempt'}</title></path>)}
      {drawing.sites.map((site, i) => <g key={site.key} className="phase-map-site">
        <circle cx={site.point[0]} cy={site.point[1]} r="5" />
        <text x={site.point[0] > 230 ? site.point[0] - 9 : site.point[0] + 9} y={site.point[1] - 10} textAnchor={site.point[0] > 230 ? 'end' : 'start'}>{site.label}</text>
        <title>Observed arrival {i + 1}</title>
      </g>)}
      {focus && <circle className="phase-map-focus" cx={drawing.project(focus.to_xy)[0]} cy={drawing.project(focus.to_xy)[1]} r="13" />}
      <text className="phase-map-caption" x="226" y="274">ABSTRACT X / Y</text>
    </svg>
    <figcaption>Rollout coordinates · solid travel arrived; dashed travel was incomplete. Schematic only, not an official field plan, physical trajectory or CAD.</figcaption>
  </figure>;
}

function ProposedMechanisms({ session, phase, actionId, architectureId }: { session: StrategySession; phase: PlaybookPhase; actionId: string; architectureId?: string | null }) {
  const requirements = phaseRequirements(session.spec, phase).filter(r => r.supports.includes(actionId));
  const architecture = session.architectures.find(a => a.id === architectureId) ?? session.architectures[0];
  return <div className="phase-mechanisms">
    <div className="phase-mechanism-heading"><span className="playbook-tag">Proposed requirements</span><h4>Mechanisms behind this action</h4></div>
    {architecture && <figure className="phase-architecture-figure"><ArchitectureDrawing architecture={architecture} activeActionId={actionId} compact/><figcaption>{architectureName(architecture)} · proposal schematic. Highlight follows its declared strategy links; not CAD or verified geometry.</figcaption></figure>}
    {requirements.length ? <figure className="phase-requirement-figure"><svg viewBox={`0 0 340 ${74 + requirements.length * 47}`} role="img" aria-label="Proposed mechanism requirements from the StrategySpec">
      <circle className="phase-requirement-hub" cx="22" cy="26" r="5" />
      <text x="38" y="30" className="phase-requirement-action">{readable(actionId)}</text>
      {requirements.map((requirement, i) => <g key={requirement.id}>
        <path className="phase-requirement-line" d={`M22 32V${70 + i * 47}H56`} />
        <rect className="phase-requirement-node" x="56" y={53 + i * 47} width="267" height="33" rx="4" />
        <text x="68" y={74 + i * 47}>{readable(requirement.id)}</text>
      </g>)}
    </svg><figcaption>Semantic action-to-requirement links from the specification. Proposed needs, not realized components or physical connections.</figcaption></figure> : <p>No mechanism requirement was declared for this action.</p>}
  </div>;
}

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
function EvidenceValues({ value }: { value: unknown }) {
  if (Array.isArray(value)) return <ul className="playbook-data-list">{value.map((item, i) => <li key={i}><EvidenceValues value={item} /></li>)}</ul>;
  if (record(value)) return <dl className="playbook-data-values">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{readable(key)}</dt><dd><EvidenceValues value={item} /></dd></div>)}</dl>;
  return <span>{value === null || value === undefined ? 'Not supplied' : String(value)}</span>;
}

function contextText(when: Record<string, string | number | boolean>): string {
  const parts: string[] = [];
  if (typeof when.timeBand === 'string') parts.push(`${readable(when.timeBand)} match`);
  if (typeof when.site === 'number') parts.push(({ '-1': 'between sites', '0': 'at supply 1', '1': 'at supply 2', '2': 'at the low goal', '3': 'at the elevated goal', '6': 'at midfield' } as Record<string, string>)[String(when.site)] ?? `at abstract site ${when.site}`);
  for (const [key, yes, no] of [['pinCarried', 'holding a Pin', 'no Pin held'], ['cupCarried', 'holding a Cup', 'no Cup held'], ['lowCupReady', 'Cup interface ready', 'Cup interface not ready'], ['lowReachable', 'low goal reachable', 'low goal out of reach']]) {
    if (typeof when[key] === 'boolean') parts.push(when[key] ? yes : no);
  }
  return parts.join(' · ');
}

export function StrategyPanel(props: StrategyPanelProps) {
  const { session, loading, error, onGenerate, available = true } = props;
  if (!session) return <div className="strategy-content strategy-playbook"><span className="eyebrow">DEFAULT OVERRIDE · V2.1</span><h2>{loading ? 'Running the trained policy…' : 'Explore a learned strategy'}</h2><p role="status">{loading ? 'Loading the strategy and a newly executed seeded simulation rollout.' : 'Generate a strategy without creating a CAD assembly.'}</p>{error && <p className="strategy-notice" role="alert">{error}</p>}<button className="primary-button" disabled={loading || !available} onClick={onGenerate}>{error ? 'Retry generation' : 'Generate Strategy'}</button></div>;
  return <LoadedStrategyPanel key={session.id} {...props} session={session} />;
}

function LoadedStrategyPanel({ session, loading, error, mode = 'simple', selectedActionId, onSelectAction, onGenerate, onArchitectures, available = true, assembly, onInspectMechanism, onAskMechanism, architectureId }: StrategyPanelProps & { session: StrategySession }) {
  const [sequence, setSequence] = useState('live');
  const [activePhase, setActivePhase] = useState(0);
  const [analysisOpen, setAnalysisOpen] = useState(mode === 'advanced');
  const [mechanismRequest, setMechanismRequest] = useState<{ actionId: string; intent: 'inspect' | 'ask' } | null>(null);
  const { spec, rollout } = session;
  const trace = sequence === 'live' ? null : spec.representativeSequences[Number(sequence)];
  const events = trace?.events ?? rollout.events;
  const score = trace?.modeledScore ?? rollout.score;
  const phases = buildStrategyPhases(events);
  const phase = phases[Math.min(activePhase, Math.max(0, phases.length - 1))];
  const actionId = phase?.actionIds.includes(selectedActionId ?? '') ? selectedActionId! : phase?.primaryActionId;
  const linked = actionId ? phaseAssemblyLink(assembly, spec.id, actionId) : null;
  const contexts = [...spec.behavior.conditionalPreferences].sort((a, b) => b.observedDecisions - a.observedDecisions);
  const limitations = [...new Set([...session.limitations, ...spec.limitations])];
  const evidence = record(spec.evidence) ? spec.evidence : {};
  const comparison = record(evidence.strategyAwareVsBlind) ? evidence.strategyAwareVsBlind : {};
  const confirmation = record(comparison.confirmationDifference) ? comparison.confirmationDifference : null;
  useEffect(() => { setAnalysisOpen(mode === 'advanced'); }, [mode]);
  useEffect(() => {
    if (!selectedActionId) return;
    setActivePhase(current => phases[current]?.actionIds.includes(selectedActionId) ? current : Math.max(0, phases.findIndex(p => p.actionIds.includes(selectedActionId))));
    // Phase membership follows the actual selected sequence and external CAD action.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedActionId, sequence]);
  useEffect(() => {
    if (!mechanismRequest) return;
    if (!linked || actionId !== mechanismRequest.actionId) { setMechanismRequest(null); return; }
    if (selectedActionId !== mechanismRequest.actionId) return;
    // Let the parent commit the actual action before its callback reads the binding.
    setMechanismRequest(null);
    if (mechanismRequest.intent === 'inspect') onInspectMechanism?.();
    else onAskMechanism?.();
  }, [mechanismRequest, selectedActionId, actionId, linked, onInspectMechanism, onAskMechanism]);
  function selectPhase(index: number) {
    setMechanismRequest(null);
    setActivePhase(index);
    onSelectAction(phases[index].primaryActionId);
  }
  function requestMechanism(intent: 'inspect' | 'ask') {
    if (!linked || !actionId) return;
    setMechanismRequest({ actionId, intent });
    onSelectAction(actionId);
  }
  return <div className="strategy-content strategy-playbook">
    <header className="playbook-heading"><span className="eyebrow">STRATEGY PLAYBOOK / FROZEN PPO</span><h2>{readable(session.strategyFamily)}</h2>
      <p className="playbook-overview">{phases.some(p => p.kind === 'repeat') ? 'Collect objects, return to the scoring location, and repeat the observed cycle.' : 'Follow the decisions observed in this policy rollout.'} Select a phase to connect the plan to its mechanisms.</p>
      <p className="strategy-domain playbook-model-status">Abstract simulation only · default Override v2.1 · one learned family · {linked ? 'Revision-linked assembly; task capability unverified' : 'Proposed mechanisms; no verified CAD link for this action'}</p>
      <div className="playbook-priorities"><span>Prioritize</span>{spec.scoringPriorities.filter(o => o.meanModeledPoints > 0).map(o => <strong key={o.objective}>{readable(o.objective)}</strong>)}</div>
    </header>
    {loading && <p role="status">Generating another session. Your current result remains available.</p>}
    {error && <div className="strategy-notice" role="alert"><p>{error}</p><button className="secondary-button" disabled={loading} onClick={onGenerate}>Retry generation</button></div>}
    <DockFrame className="playbook-sequence" aria-label="Visual strategy playbook" label="Observed rollout" code="SIM / XY">
      <div className="playbook-sequence-heading"><h3>Action sequence</h3><p><strong>{formatNumber(score)}</strong><span>{trace ? 'Representative episode points' : 'Executed episode points'}</span></p></div>
      <p className="playbook-score-basis">One modeled episode, not an evaluation average.</p>
      {phase && actionId ? <div className="playbook-sequence-layout">
        <ol className="playbook-phase-rail" aria-label="Strategy phases">{phases.map((item, index) => <li key={item.id}>
          <button className={item.id === phase.id ? 'is-active' : ''} data-phase-id={item.id} data-action-id={item.primaryActionId} aria-pressed={item.id === phase.id} aria-controls="selected-strategy-phase" onClick={() => selectPhase(index)}>
            <span className="playbook-phase-number">{String(index + 1).padStart(2, '0')}</span><span><strong>{item.title}</strong><small>{formatNumber(item.startS)}–{formatNumber(item.endS)} s</small></span>
          </button>
        </li>)}</ol>
        <div id="selected-strategy-phase" className="playbook-selected-phase" data-phase-id={phase.id} aria-label="Selected strategy phase">
          <div className="playbook-phase-heading"><span className="eyebrow">PHASE {phases.indexOf(phase) + 1} / {phases.length}</span><h3>{phase.title}</h3><p>{phase.events.length} observed decisions · {phase.failures} failed attempts · {formatNumber(phase.scoreChange)} episode point change</p></div>
          {phase.events.some(e => /^(acquire|place)_/.test(e.action)) && <div className="phase-object-key" aria-label="Objects involved in this phase">
            {phase.events.some(e => /^(acquire|place)_(alliance|yellow)$/.test(e.action)) && <span><svg viewBox="0 0 48 30" role="img" aria-label="Pin illustration"><path d="M7 9H34V21H7ZM34 6H40V24H34M7 12H2V18H7" fill="none" stroke="currentColor" strokeWidth="1.5"/><path d="M12 13H30M12 17H30" stroke="currentColor"/></svg>Pin</span>}
            {phase.events.some(e => /^(acquire|place)_cup$/.test(e.action)) && <span><svg viewBox="0 0 36 30" role="img" aria-label="Cup illustration"><path d="M4 4H32L27 26H9ZM7 8H29M12 11V22M24 11V22" fill="none" stroke="currentColor" strokeWidth="1.5"/></svg>Cup</span>}
            <small>Object illustrations · not to scale</small>
          </div>}
          <div className={`playbook-drawings${linked?' has-cad-link':''}`}><Playbook events={events} phase={phase} actionId={actionId} />
            {linked && assembly ? <div className="phase-mechanisms"><div className="phase-mechanism-heading"><span className="playbook-tag">Revision-linked geometry</span><h4>Mechanism in the displayed assembly</h4></div><AssemblySketch session={assembly} actionId={actionId} /><p className="playbook-binding-basis">{linked.action.instanceIds.length} linked instances · {linked.candidate ? 'candidate preview' : 'accepted revision'} · {linked.action.capabilityStatus === 'unsupported' ? linked.action.capabilityReason : 'Physical task capability remains unverified.'}</p></div>
              : <ProposedMechanisms session={session} phase={phase} actionId={actionId} architectureId={architectureId} />}
          </div>
          <div className="playbook-mechanism-actions">
            {linked ? <>{onInspectMechanism && <button className="secondary-button" onClick={() => requestMechanism('inspect')}>Inspect mechanism</button>}{onAskMechanism && <button className="text-action" onClick={() => requestMechanism('ask')}>Ask about mechanism</button>}</>
              : <><button className="secondary-button" onClick={onArchitectures}>Inspect Design</button><span>Architecture concept · assembly not linked for this action</span></>}
          </div>
          <div className="playbook-phase-actions" aria-label="Inspect actions in this phase">{phase.actionIds.map(id => <button key={id} data-action-id={id} className="text-action" aria-pressed={selectedActionId === id} onClick={() => onSelectAction(id)}>{readable(id)}<span aria-hidden="true">↗</span></button>)}</div>
        </div>
      </div> : <p>No actions were returned for this sequence. No phases or path are invented.</p>}
      <div className="playbook-footer-actions"><button className="primary-button" onClick={onArchitectures}>Compare engineering alternatives</button><button className="secondary-button" disabled={loading || !available} onClick={onGenerate}>Rerun the seeded policy</button></div>
    </DockFrame>
    <details className="playbook-analysis" open={analysisOpen}>
      <summary onClick={event => { event.preventDefault(); setAnalysisOpen(open => !open); }}><span>Advanced Analysis</span><small>Full trace · capability targets · policy evidence</small></summary>
      <div className="playbook-analysis-content" hidden={!analysisOpen}>
      <section><h3>Sequence and full trace</h3><label className="strategy-sequence-select">Sequence source<select value={sequence} onChange={e => { setSequence(e.target.value); setActivePhase(0); }}><option value="live">Newly executed seeded rollout</option>{spec.representativeSequences.map((_, i) => <option key={i} value={i}>Saved representative sequence {i + 1}</option>)}</select></label>
      <p className="strategy-caption">{trace?.selection ?? 'Frozen-policy inference executed for this request with a fixed episode seed. Reruns reproduce the same modeled episode, not a new learned family or physical robot run.'}</p>
      <p>{trace ? 'Saved representative episode score' : 'Newly executed episode score'}: {formatNumber(score)} modeled points. Episode scores are separate from saved evaluation means and held-out confirmation comparisons.</p>
      <ol className="strategy-timeline" aria-label="Simulated action sequence">{events.map((event, i) => <li key={i}><button onClick={() => onSelectAction(event.action)} aria-pressed={selectedActionId === event.action}><span className="strategy-step-number">{i + 1}</span><span><strong>{readable(event.action)}</strong><small>{formatNumber(event.start_s)}–{formatNumber(event.end_s)} s · {event.success ? 'Succeeded in simulation' : 'Failed / incomplete in simulation'} · {formatNumber(event.score_after - event.score_before)} point change</small></span></button></li>)}</ol></section>
      <section><h3>Objectives and priorities</h3><dl className="strategy-metrics">{spec.scoringPriorities.map(o => <div key={o.objective}><dt>{readable(o.objective)}</dt><dd>{formatNumber(o.meanModeledPoints)} mean modeled points</dd></div>)}</dl><p className="strategy-caption">Saved evaluation mean contributions, not this episode's score, guaranteed points or official scoring validation.</p></section>
      <section><h3>Mechanism requirements</h3><ul className="strategy-requirements">{spec.mechanicalRequirements.map(m => <li key={m.id}><strong>{readable(m.id)}</strong><p>{m.requirements.map(readable).join(' · ')}</p><small>Supports: {m.supports.map(readable).join(', ')}</small></li>)}</ul></section>
      <section><h3>How context changes the choice</h3><p className="strategy-caption">Observed context summaries approximate a conditional policy. They are not an exhaustive rule table.</p><div className="strategy-contexts">{contexts.map((c, i) => {
      const best = Object.entries(c.meanNeuralActionProbabilities).sort((a, b) => b[1] - a[1])[0];
      return <article key={i}><p>{contextText(c.when)}</p>{best && <button className="text-action" onClick={() => onSelectAction(best[0])}>{readable(best[0])} · {formatNumber(best[1] * 100)}% mean policy probability</button>}<small>{formatNumber(c.observedDecisions)} observed decisions</small></article>;
    })}</div></section>
      <section><h3>Capability targets</h3><p>{spec.capabilityRequirements.basis}</p><dl className="strategy-metrics">{Object.entries(spec.capabilityRequirements.targets).map(([k, v]) => <div key={k}><dt>{readable(k)}</dt><dd>{capabilityValue(k, v)}</dd></div>)}</dl><h4>Hard minimums</h4><dl className="strategy-metrics">{Object.entries(spec.capabilityRequirements.hardMinimums).map(([k, v]) => <div key={k}><dt>{readable(k)}</dt><dd>{capabilityValue(k, v)}</dd></div>)}</dl><h4>Executed rollout capability profile</h4><EvidenceValues value={rollout.capabilities} /><p className="strategy-caption">Targets are engineering inputs. Acceleration and physical feasibility are not established.</p></section>
      <section className="strategy-evidence"><h3>Policy and simulation evidence</h3><dl><div><dt>Experiment</dt><dd>{spec.policy.experimentId}</dd></div><div><dt>Source revision</dt><dd>{spec.policy.sourceCommit}</dd></div><div><dt>Environment</dt><dd>{session.competition.environmentId}</dd></div>{rollout.evidence?.episodeSeed !== undefined && <div><dt>Episode seed</dt><dd>{rollout.evidence.episodeSeed}</dd></div>}<div><dt>Policy parameter hash</dt><dd className="strategy-hash">{rollout.policyParameterHash}</dd></div><div><dt>Checkpoint SHA-256</dt><dd className="strategy-hash">{spec.policy.checkpoint.sha256}</dd></div><div><dt>Checkpoint path</dt><dd>{spec.policy.checkpoint.path}</dd></div></dl>
      <h4>Executed rollout contributions</h4><ul>{Object.entries(rollout.pointsByObjective).map(([k, v]) => <li key={k}>{readable(k)}: {formatNumber(v)} modeled points</li>)}</ul><h4>Executed rollout action frequencies</h4><ul>{Object.entries(rollout.actionFrequencies).map(([k, v]) => <li key={k}>{readable(k)}: {formatNumber(v * 100)}% of decisions</li>)}</ul>
      {confirmation && <div className="playbook-statistic-note"><h4>Held-out confirmation comparison</h4><p>{String(confirmation.meanScoreDifference)} mean modeled point difference, strategy-aware versus balanced abstract profile. This is an evaluation comparison, not the selected episode's score or a mechanical topology advantage.</p></div>}
      <h4>Saved evidence and uncertainty</h4><EvidenceValues value={evidence} /><h4>Executed inference evidence</h4><EvidenceValues value={rollout.evidence} /></section>
      <section><h3>Limitations and required validation</h3><ul>{limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>{assembly && <><h4>Assembly qualification</h4><EvidenceValues value={assembly.qualification} /><ul>{assembly.missing.map((m, i) => <li key={i}>{readable(m.role)}: {m.message}</li>)}</ul></>}<a className="source-link" href={OVERRIDE_MANUAL_URL} target="_blank" rel="noreferrer">Official V5 Override manual · pinned v2.1</a><p className="strategy-caption">Generated session is retained in this tab while you switch panels. Server restoration is not enabled.</p></section>
      </div>
    </details>
  </div>;
}
