import type { Capabilities, Catalog } from '../api/contracts';
import { Icon } from '../components/Icon';

export function Home({ catalog, capabilities, onInspect }: { catalog: Catalog | null; capabilities: Capabilities | null; onInspect: () => void }) {
  return <div className="home-content">
    <div className="competition-card"><span className="eyebrow">COMPETITION CONTEXT</span><strong>Override</strong><span>Rulebook and source snapshot unavailable</span></div>
    <span className="eyebrow section-eyebrow">FROM RULES TO ROBOTICS</span>
    <h2>Your next idea.<br />Grounded in real parts.</h2>
    <p className="lead">A focused space to connect strategy, mechanisms, and the robot you build.</p>
    <div className="entry-actions">
      <div className="entry-card"><span className="entry-number">01</span><h3>Find an approach</h3><p>Turn competition rules into a grounded strategy.</p><button disabled>Generate Strategy <Icon name="arrow" /></button><span className="unavailable-label">Strategy generation unavailable</span></div>
      <div className="entry-card"><span className="entry-number">02</span><h3>Shape the machine</h3><p>Explore connected, component-based designs.</p><button disabled>Create Robot <Icon name="arrow" /></button><span className="unavailable-label">Robot generation unavailable</span></div>
    </div>
    <div className="home-inspect"><Icon name="parts" size={26} /><div><strong>Start with your components</strong><p>{catalog?.components.length ? `${catalog.components.length} local catalog ${catalog.components.length === 1 ? 'entry' : 'entries'}. Inspect identity, geometry, and sources.` : 'No qualified local geometry is available yet.'}</p></div><button className="icon-button" aria-label="Inspect components" onClick={onInspect}><Icon name="arrow" /></button></div>
    {capabilities?.reasons.length ? <details className="capability-details"><summary>Workspace availability</summary><ul>{capabilities.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul></details> : <p className="availability-note">Generation and editing are unavailable in this workspace.</p>}
  </div>;
}
