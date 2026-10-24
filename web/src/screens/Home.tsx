import type { Capabilities, Catalog } from '../api/contracts';
import { Icon } from '../components/Icon';
import { OVERRIDE_MANUAL_URL, type StrategyStatus } from '../api/strategy';

export function Home({ catalog, capabilities, onInspect, strategyStatus, strategyLoading = false, generating = false, onGenerateStrategy, onCreateRobot, strategyError, onRetryStrategy }: {
  catalog: Catalog | null; capabilities: Capabilities | null; onInspect: () => void;
  strategyStatus?: StrategyStatus | null; strategyLoading?: boolean; generating?: boolean;
  onGenerateStrategy?: () => void; onCreateRobot?: () => void; strategyError?: string | null; onRetryStrategy?: () => void;
}) {
  const available = strategyStatus?.available === true;
  const reason = strategyLoading ? 'Checking trained strategy availability…' : strategyStatus?.reason ?? 'Trained strategy service unavailable. Connect the local server to check availability.';
  return <div className="home-content">
    <div className="competition-card"><span className="eyebrow">COMPETITION CONTEXT</span><strong>Override · v2.1</strong><span>Default Override only · abstract simulation</span><a className="source-link" href={OVERRIDE_MANUAL_URL} target="_blank" rel="noreferrer">Official V5 Override manual · pinned v2.1</a><small>Other competitions and rulebook upload are unavailable in this strategy flow.</small></div>
    <span className="eyebrow section-eyebrow">FROM RULES TO ROBOTICS</span>
    <h2>Your next idea.<br />Grounded in real parts.</h2>
    <p className="lead">A focused space to connect strategy, mechanisms, and the robot you build.</p>
    <div className="entry-actions">
      <div className="entry-card"><span className="entry-number">01</span><h3>Find an approach</h3><p>Explore the trained PPO policy, objectives, and simulated actions.</p><button disabled={!available || generating || !onGenerateStrategy} onClick={onGenerateStrategy}>Generate Strategy <Icon name="arrow" /></button><span className="unavailable-label">{generating ? 'Running the frozen policy…' : available ? 'Strategy first · no robot required' : reason}</span></div>
      <div className="entry-card"><span className="entry-number">02</span><h3>Shape the machine</h3><p>Compare two engineering concepts for the same learned family.</p><button disabled={!available || generating || !onCreateRobot} onClick={onCreateRobot}>Create Robot <Icon name="arrow" /></button><span className="unavailable-label">{available ? 'Start directly with architecture concepts; CAD qualification follows.' : reason}</span></div>
    </div>
    {strategyError && <div className="strategy-notice" role="alert"><p>{strategyError}</p>{onRetryStrategy && <button className="secondary-button" onClick={onRetryStrategy}>Retry strategy connection</button>}</div>}
    <div className="home-inspect"><Icon name="parts" size={26} /><div><strong>Start with your components</strong><p>{catalog?.components.length ? `${catalog.components.length} local catalog ${catalog.components.length === 1 ? 'entry' : 'entries'}. Inspect identity, geometry, and sources.` : 'No qualified local geometry is available yet.'}</p></div><button className="icon-button" aria-label="Inspect components" onClick={onInspect}><Icon name="arrow" /></button></div>
    {capabilities?.reasons.length ? <details className="capability-details"><summary>CAD workspace availability</summary><ul>{capabilities.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul></details> : <p className="availability-note">CAD availability is qualified separately from strategy availability.</p>}
  </div>;
}
