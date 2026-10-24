import type { Mode } from '../api/contracts';
import { capabilityValue, readable, type ArchitectureProposal, type RealizationState, type StrategySession } from '../api/strategy';

export interface ArchitecturesPanelProps {
  session: StrategySession | null;
  loading: boolean;
  error?: string | null;
  mode?: Mode;
  selectedArchitectureId: string | null;
  selectedActionId?: string | null;
  realization?: RealizationState;
  onSelectArchitecture: (architectureId: string) => void;
  onRealizeArchitecture?: (architectureId: string) => void | Promise<void>;
  onInspectReference?: () => void;
  onStrategy: () => void;
  onGenerate: () => void;
  available?: boolean;
}

function mechanism(a: ArchitectureProposal, id: string) { return a.subsystems.find(s => s.id === id); }
function title(a: ArchitectureProposal) {
  return [mechanism(a, 'scorer'), mechanism(a, 'pin_intake')].filter(s => !!s).map(s => readable(s!.mechanismIntent)).join(' + ');
}

/** An authored schematic of supplied mechanism intents, never authentic component geometry. */
function ConceptSketch({ architecture, activeActionId }: { architecture: ArchitectureProposal; activeActionId?: string | null }) {
  const scorer = mechanism(architecture, 'scorer');
  const fourBar = scorer?.mechanismIntent.includes('four_bar');
  const elevator = scorer?.mechanismIntent.includes('elevator');
  const highlighted = new Set(architecture.bindingIntent.actions.filter(a => (a.action ?? a.sourceValue) === activeActionId).flatMap(a => a.subsystemIDs));
  return <figure className="strategy-figure concept-sketch"><svg viewBox="0 0 440 300" role="img" aria-label={`Schematic mechanical concept for alternative ${architecture.alternative}; not CAD`}>
    <path className="concept-ground" d="M20 245H420" />
    <g className={highlighted.has('drive') ? 'is-selected' : ''}><rect x="100" y="209" width="220" height="23" rx="3" /><circle cx="130" cy="234" r="15" /><circle cx="290" cy="234" r="15" />{mechanism(architecture, 'drive')?.layoutIntent.wheelCount === 6 && <circle cx="210" cy="236" r="15" />}<path d="M220 250V272H340" /><text x="230" y="287">{String(mechanism(architecture, 'drive')?.layoutIntent.wheelCount ?? '?')} wheel drive intent</text></g>
    <g className={highlighted.has('scorer') ? 'is-selected' : ''}>
      {fourBar ? <><path d="M175 205 245 113 284 113 214 205ZM175 185 245 93 284 93 214 185Z" /><circle cx="175" cy="205" r="4" /><circle cx="245" cy="113" r="4" /><path d="M280 98H350V66H395" /></> : elevator ? <><path d="M234 208V80H266V208M242 200V90M258 200V90" /><rect x="229" y="106" width="44" height="27" /><path d="M273 119H320M266 80H350V66H395" /></> : <><rect x="220" y="100" width="50" height="100" /><path d="M270 100H350V66H395" /></>}
      <text x="270" y="52">{fourBar ? 'Four-bar scoring intent' : elevator ? 'Guided elevator intent' : 'Scoring mechanism intent'}</text>
    </g>
    <g className={highlighted.has('pin_intake') || highlighted.has('pin_transfer') ? 'is-selected' : ''}><path d="M100 213 65 197H35M100 199 65 183H35M65 183V159H22" /><text x="22" y="146">Pin pickup → handoff</text></g>
    <g className={highlighted.has('cup_cradle') ? 'is-selected' : ''}><path d="M285 159 292 186H316L323 159M304 186V208M323 172H397" /><text x="316" y="151">Cup bay</text></g>
    <text x="22" y="28">CONCEPT ONLY · NOT CAD · NOT TO SCALE</text>
  </svg><figcaption>Original schematic of the supplied subsystem intents. Lines are not real parts, mounts, verified joints, or achieved travel. Dimensions below are sizing intent in metres.</figcaption></figure>;
}

function Tradeoffs({ architecture }: { architecture: ArchitectureProposal }) {
  const drive = mechanism(architecture, 'drive');
  const scorer = mechanism(architecture, 'scorer');
  const intake = mechanism(architecture, 'pin_intake');
  return <div className="architecture-tradeoffs"><h4>Engineering tradeoffs to qualify</h4><ul>
    {drive && <li>{String(drive.layoutIntent.wheelCount)} wheels and {String(drive.actuationIntent.motorCountIntent)} drive motors intended; qualify transmission losses, traction, loaded speed, and turning.</li>}
    {scorer?.mechanismIntent.includes('four_bar') && <li>Four-bar links introduce a curved tool path and pivot alignment requirements. Check reach, retention, and clearance throughout the stroke.</li>}
    {scorer?.mechanismIntent.includes('elevator') && <li>A guided elevator adds rails, carriage alignment, and lift transmission requirements. Check binding, loaded holding, and stability.</li>}
    {intake?.mechanismIntent.includes('rollers') && <li>Roller pickup needs contact force, orientation guides, and a timed handoff that prevents a second Pin entering.</li>}
    {intake?.mechanismIntent.includes('jaw') && <li>Jaw pickup needs alignment, opening clearance, and coordinated grip/shuttle timing while preserving Pin orientation.</li>}
  </ul><p className="strategy-caption">Engineering considerations inferred from the supplied mechanisms. Neither concept has measured performance or a proven advantage.</p></div>;
}

export function ArchitecturesPanel({ session, loading, error, mode = 'simple', selectedArchitectureId, selectedActionId, realization = { state: 'idle' }, onSelectArchitecture, onRealizeArchitecture, onInspectReference, onStrategy, onGenerate, available = true }: ArchitecturesPanelProps) {
  if (!session) return <div className="strategy-content"><span className="eyebrow">START WITH THE MACHINE</span><h2>{loading ? 'Preparing engineering alternatives…' : 'Create a robot concept'}</h2><p role="status">{loading ? 'Loading saved proposals driven by the frozen PPO strategy. CAD qualification is a separate step.' : 'Start directly here. The strategy runs as context for two mechanical alternatives; no prior Strategy visit is required.'}</p>{error && <p role="alert" className="strategy-notice">{error}</p>}<button disabled={loading || !available} className="primary-button" onClick={onGenerate}>{error ? 'Retry generation' : 'Create Robot'}</button></div>;
  const selected = session.architectures.find(a => a.id === selectedArchitectureId);
  const roles = [...new Set(session.architectures.flatMap(a => a.subsystems.map(s => s.id)))];
  const currentRealization = realization.state !== 'idle' && realization.architectureId === selectedArchitectureId ? realization : null;
  return <div className="strategy-content architectures-content">
    <span className="eyebrow">ONE LEARNED FAMILY · ENGINEERING ALTERNATIVES</span><h2>Two ways to support the same strategy</h2><p>Both alternatives consume {readable(session.strategyFamily).toLowerCase()} requirements. They are mechanically different proposals, not two learned strategies or complete generated robots.</p><p className="strategy-domain">Abstract simulation only · default Override v2.1</p>
    {error && <p role="alert" className="strategy-notice">{error}</p>}
    <div className="architecture-options" aria-label="Engineering alternatives">{session.architectures.map(a => <button key={a.id} className="architecture-option" aria-pressed={selectedArchitectureId === a.id} onClick={() => onSelectArchitecture(a.id)}><span className="eyebrow">ALTERNATIVE {a.alternative}</span><strong>{title(a)}</strong><small>Same learned family · engineering intent</small></button>)}</div>
    {!session.architectures.length && <p>No saved architecture proposals were returned. No robot has been created.</p>}
    <section><h3>Compare actual subsystem choices</h3><div className="architecture-table-scroll" tabIndex={0} role="region" aria-label="Architecture subsystem comparison"><table className="architecture-table"><thead><tr><th scope="col">Subsystem</th>{session.architectures.map(a => <th scope="col" key={a.id}>Alternative {a.alternative}</th>)}</tr></thead><tbody>{roles.map(role => <tr key={role}><th scope="row">{readable(role)}</th>{session.architectures.map(a => <td key={a.id}>{mechanism(a, role) ? readable(mechanism(a, role)!.mechanismIntent) : 'Not declared'}</td>)}</tr>)}</tbody></table></div></section>
    {selected ? <>
      <section><h3>Alternative {selected.alternative} · mechanical concept</h3><ConceptSketch architecture={selected} activeActionId={selectedActionId} /><Tradeoffs architecture={selected} />
        <dl className="strategy-metrics">{Object.entries(selected.capabilityConstraints.targets).map(([k, v]) => <div key={k}><dt>{readable(k)} target</dt><dd>{capabilityValue(k, v)}</dd></div>)}</dl><p className="strategy-caption">Shared abstract capability targets, not predictions for either mechanism. No topology performance comparison is established.</p>
      </section>
      <section className="architecture-realization"><h3>CAD qualification</h3><p>Authentic components, mounts, actuation, and validation are required before this concept can become a connected assembly.</p>
        <button className="primary-button" disabled={!onRealizeArchitecture || realization.state === 'loading'} onClick={() => onRealizeArchitecture?.(selected.id)}>{currentRealization?.state === 'loading' ? 'Checking qualified components…' : currentRealization?.state === 'failed' ? 'Retry CAD qualification' : 'Check parts and realize concept'}</button>
        {!onRealizeArchitecture && <p className="strategy-caption">CAD realization is unavailable in this workspace.</p>}
        {currentRealization?.state === 'loading' && <p role="status">Requesting a real assembly. The schematic remains a concept.</p>}
        {currentRealization?.state === 'failed' && <p role="alert" className="strategy-notice">{currentRealization.message}</p>}
        {currentRealization?.state === 'loaded' && <div className="strategy-notice" role="status"><strong>{currentRealization.result.status === 'blocked' ? 'CAD blocked — missing qualified parts or mechanisms' : currentRealization.result.status === 'partial' ? 'Partial assembly — qualifications remain' : 'Assembly response ready — review qualifications'}</strong><p>{currentRealization.result.accepted ? 'Only the returned assembly revision may be displayed as design geometry.' : 'No architecture CAD is available. Any source geometry on the canvas is an inspection reference.'}</p><ul>{currentRealization.result.missing.map((m, i) => <li key={i}><strong>{readable(m.role)}</strong>: {m.message}<small>{readable(m.code)}</small></li>)}</ul>{onInspectReference && <button className="secondary-button" onClick={onInspectReference}>Inspect reference</button>}</div>}
      </section>
      <details open={mode === 'advanced'} className="strategy-evidence"><summary>Required qualifications</summary><ul>{selected.qualificationRequired.map((q, i) => <li key={i}>{q}</li>)}</ul></details>
      <details className="strategy-evidence" open={mode === 'advanced'}><summary>Subsystem sizing, actuation, and connection intents</summary>{selected.subsystems.map(s => <article key={s.id}><h4>{readable(s.id)} · {readable(s.mechanismIntent)}</h4><dl className="strategy-metrics">{Object.entries({ ...s.layoutIntent, ...s.actuationIntent }).filter(([, v]) => ['string', 'number', 'boolean'].includes(typeof v)).map(([k, v]) => <div key={k}><dt>{readable(k)}</dt><dd>{typeof v === 'number' ? capabilityValue(k, v) : typeof v === 'boolean' ? v ? 'Yes' : 'No' : String(v)}</dd></div>)}</dl></article>)}<h4>Attachment and joint intents</h4><ul>{selected.attachmentAndJointIntents.map((j, i) => <li key={i}>{readable(j.parentSubsystemID)} → {readable(j.childSubsystemID)}: {j.jointIntent} · {j.mountZoneIntent}</li>)}</ul></details>
      <details className="strategy-evidence"><summary>Engineering assumptions</summary><ul>{selected.engineeringAssumptions.map((s, i) => <li key={i}>{s}</li>)}</ul></details>
      <p className="strategy-caption">Minimum modeled reach: {capabilityValue('reachM', selected.capabilityConstraints.hardMinimums.reachM ?? 0)}. Authentic part selection and physical performance remain unverified.</p>
    </> : <p className="strategy-notice">Select an alternative to inspect its schematic, capability targets, qualifications, and CAD availability.</p>}
    <button className="secondary-button" onClick={onStrategy}>View the strategy behind these concepts</button>
  </div>;
}
