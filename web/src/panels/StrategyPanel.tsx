import { useState } from 'react';
import type { Mode } from '../api/contracts';
import { OVERRIDE_MANUAL_URL, capabilityValue, formatNumber, readable, type StrategyEvent, type StrategySession, type DesignSession } from '../api/strategy';
import { AssemblySketch } from './AssemblySketch';

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
}

function Playbook({ events, selectedActionId }: { events: StrategyEvent[]; selectedActionId: string | null }) {
  const points = events.flatMap(e => [e.from_xy, e.to_xy]);
  if (!points.length) return <p>No path was returned for this sequence.</p>;
  const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  const minX = Math.min(...xs), minY = Math.min(...ys);
  const scale = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY, .5);
  const project = (p: [number, number]) => [40 + (p[0] - minX) / scale * 260, 290 - (p[1] - minY) / scale * 250];
  const sites = new Map<string, { point: number[]; label: string }>();
  for (const e of events) if (e.action.startsWith('move_to_') && e.success) sites.set(e.to_xy.join(','), { point: project(e.to_xy), label: readable(e.action).replace(/^(Travel to|Approach) /, '') });
  return <figure className="strategy-figure"><svg role="img" aria-label="Annotated abstract playbook from the selected simulation sequence" viewBox="0 0 340 340">
    <rect className="playbook-field" x="12" y="12" width="316" height="316" rx="8" />
    <path className="playbook-grid" d="M12 118H328M12 222H328M118 12V328M222 12V328" />
    {events.filter(e => e.from_xy.some((n, i) => n !== e.to_xy[i])).map((e, i) => {
      const a = project(e.from_xy), b = project(e.to_xy);
      return <path key={i} className={e.action === selectedActionId ? 'playbook-path is-selected' : 'playbook-path'} d={`M${a.join(' ')} L${b.join(' ')}`}><title>{readable(e.action)} · {formatNumber(e.start_s)} s</title></path>;
    })}
    {Array.from(sites.entries()).map(([key, s], i) => <g key={key}><circle cx={s.point[0]} cy={s.point[1]} r="11" /><text className="playbook-number" x={s.point[0]} y={s.point[1] + 4}>{i + 1}</text><text x={Math.min(230, s.point[0] + 15)} y={Math.max(30, s.point[1] - 16)}>{s.label}</text></g>)}
    {selectedActionId && events.filter(e => e.action === selectedActionId).slice(0, 1).map(e => <circle key={e.action} className="playbook-focus" cx={project(e.to_xy)[0]} cy={project(e.to_xy)[1]} r="18" />)}
  </svg><figcaption>Schematic abstract coordinates from the rollout. This is not an official field plan, physical trajectory, or CAD.</figcaption></figure>;
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

export function StrategyPanel({ session, loading, error, mode = 'simple', selectedActionId, onSelectAction, onGenerate, onArchitectures, available = true, assembly }: StrategyPanelProps) {
  const [sequence, setSequence] = useState('live');
  if (!session) return <div className="strategy-content"><span className="eyebrow">DEFAULT OVERRIDE · V2.1</span><h2>{loading ? 'Running the trained policy…' : 'Explore a learned strategy'}</h2><p role="status">{loading ? 'Loading the full strategy specification, saved engineering alternatives, and a newly executed seeded simulation rollout.' : 'Generate a strategy without creating a CAD assembly.'}</p>{error && <p className="strategy-notice" role="alert">{error}</p>}<button className="primary-button" disabled={loading || !available} onClick={onGenerate}>{error ? 'Retry generation' : 'Generate Strategy'}</button></div>;
  const { spec, rollout } = session;
  const trace = sequence === 'live' ? null : spec.representativeSequences[Number(sequence)];
  const events = trace?.events ?? rollout.events;
  const score = trace?.modeledScore ?? rollout.score;
  const contexts = [...spec.behavior.conditionalPreferences].sort((a, b) => b.observedDecisions - a.observedDecisions);
  const requirements = spec.mechanicalRequirements.filter(m => !selectedActionId || m.supports.includes(selectedActionId));
  const limitations = [...new Set([...session.limitations, ...spec.limitations])];
  return <div className="strategy-content">
    <div className="strategy-heading"><span className="eyebrow">TRAINED PPO · ONE LEARNED FAMILY</span><h2>{readable(session.strategyFamily)}</h2><p className="strategy-domain">Abstract simulation only · default Override v2.1</p><a className="source-link" href={OVERRIDE_MANUAL_URL} target="_blank" rel="noreferrer">Official V5 Override manual · pinned v2.1</a><p>These decisions depend on state, time, and modeled capabilities. A sequence illustrates the policy; it does not replace the neural decision rule or certify robot performance.</p></div>
    {loading && <p role="status">Generating another session. Your current result remains available.</p>}
    {error && <div className="strategy-notice" role="alert"><p>{error}</p><button className="secondary-button" disabled={loading} onClick={onGenerate}>Retry generation</button></div>}
    <section><h3>Objectives and priorities</h3><ol className="strategy-objectives">{spec.scoringPriorities.map(o => <li key={o.objective}><strong>{readable(o.objective)}</strong><span>{formatNumber(o.meanModeledPoints)} mean modeled points</span></li>)}</ol><p className="strategy-caption">Observed evaluation contributions, not guaranteed points or official scoring validation.</p></section>
    <section><div className="strategy-section-head"><h3>Action sequence</h3><span className="strategy-score">{formatNumber(score)} modeled points</span></div>
      <label className="strategy-sequence-select">Sequence source<select value={sequence} onChange={e => setSequence(e.target.value)}><option value="live">Newly executed seeded rollout</option>{spec.representativeSequences.map((_, i) => <option key={i} value={i}>Saved representative sequence {i + 1}</option>)}</select></label>
      <p className="strategy-caption">{trace?.selection ?? 'Frozen-policy inference executed for this request with a fixed episode seed. Reruns reproduce the same modeled episode, not a new learned family or physical robot run.'}</p>
      <Playbook events={events} selectedActionId={selectedActionId} />
      <ol className="strategy-timeline" aria-label="Simulated action sequence">{events.map((event, i) => <li key={i}><button onClick={() => onSelectAction(event.action)} aria-pressed={selectedActionId === event.action}><span className="strategy-step-number">{i + 1}</span><span><strong>{readable(event.action)}</strong><small>{formatNumber(event.start_s)}–{formatNumber(event.end_s)} s · {event.success ? 'Succeeded in simulation' : 'Failed / incomplete in simulation'} · {formatNumber(event.score_after - event.score_before)} point change</small></span></button></li>)}</ol>
    </section>
    <section><h3>Mechanisms behind {selectedActionId ? readable(selectedActionId).toLowerCase() : 'the strategy'}</h3><p className="strategy-caption">Semantic requirements only. CAD highlights require actual revision bindings.</p>{requirements.length ? <ul className="strategy-requirements">{requirements.map(m => <li key={m.id}><strong>{readable(m.id)}</strong><p>{m.requirements.map(readable).join(' · ')}</p><small>Supports: {m.supports.map(readable).join(', ')}</small></li>)}</ul> : <p>No mechanism requirement was declared for this action.</p>}
      {assembly && <AssemblySketch session={assembly} actionId={selectedActionId}/>}
      <button className="primary-button" onClick={onArchitectures}>Compare engineering alternatives</button>
    </section>
    <section><h3>How context changes the choice</h3><p className="strategy-caption">Observed context summaries approximate a conditional policy. They are not an exhaustive rule table.</p><div className="strategy-contexts">{contexts.slice(0, mode === 'advanced' ? contexts.length : 5).map((c, i) => {
      const best = Object.entries(c.meanNeuralActionProbabilities).sort((a, b) => b[1] - a[1])[0];
      return <article key={i}><p>{contextText(c.when)}</p>{best && <button className="text-action" onClick={() => onSelectAction(best[0])}>{readable(best[0])} · {formatNumber(best[1] * 100)}% mean policy probability</button>}<small>{formatNumber(c.observedDecisions)} observed decisions</small></article>;
    })}</div>{mode === 'simple' && contexts.length > 5 && <p className="strategy-caption">Advanced mode shows all {contexts.length} observed contexts.</p>}</section>
    <section><h3>Capability targets</h3><p>{spec.capabilityRequirements.basis}</p><dl className="strategy-metrics">{Object.entries(spec.capabilityRequirements.targets).map(([k, v]) => <div key={k}><dt>{readable(k)}</dt><dd>{capabilityValue(k, v)}</dd></div>)}</dl><p className="strategy-caption">Targets are engineering inputs. Acceleration and physical feasibility are not established.</p></section>
    <details open={mode === 'advanced'} className="strategy-evidence"><summary>Policy and simulation evidence</summary><dl><div><dt>Experiment</dt><dd>{spec.policy.experimentId}</dd></div><div><dt>Source revision</dt><dd>{spec.policy.sourceCommit}</dd></div><div><dt>Environment</dt><dd>{session.competition.environmentId}</dd></div>{rollout.evidence?.episodeSeed !== undefined && <div><dt>Episode seed</dt><dd>{rollout.evidence.episodeSeed}</dd></div>}<div><dt>Policy parameter hash</dt><dd className="strategy-hash">{rollout.policyParameterHash}</dd></div></dl><h4>Executed rollout contributions</h4><ul>{Object.entries(rollout.pointsByObjective).map(([k, v]) => <li key={k}>{readable(k)}: {formatNumber(v)} modeled points</li>)}</ul><h4>Executed rollout action frequencies</h4><ul>{Object.entries(rollout.actionFrequencies).map(([k, v]) => <li key={k}>{readable(k)}: {formatNumber(v * 100)}% of decisions</li>)}</ul></details>
    <details className="strategy-evidence"><summary>Limitations and required validation</summary><ul>{limitations.map((l, i) => <li key={i}>{l}</li>)}</ul></details>
    <p className="strategy-caption">Generated session is retained in this tab while you switch panels. Server restoration is not enabled.</p>
    <button className="secondary-button" disabled={loading || !available} onClick={onGenerate}>Rerun the seeded policy</button>
  </div>;
}
