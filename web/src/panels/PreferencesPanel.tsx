import type { Preferences } from '../api/contracts';
import { Icon } from '../components/Icon';

export function PreferencesPanel({ preferences, onChange, disabled }: { preferences: Preferences; onChange: (p: Partial<Preferences>) => void; disabled: boolean }) {
  return <div className="preferences-content">
    <fieldset disabled={disabled}><legend>Workspace character</legend><p>One workspace. Two ways to think.</p><div className="theme-choices">{(['snap', 'shift'] as const).map(theme => <button key={theme} className={`theme-card theme-preview-${theme}`} aria-pressed={preferences.theme === theme} onClick={() => onChange({ theme })}><span className="theme-swatch"><i /><i /><i /></span><strong>{theme.toUpperCase()} {preferences.theme === theme && <Icon name="check" size={16} />}</strong><small>{theme === 'snap' ? 'Warm. Modular. Precise.' : 'Technical. Fluid. Focused.'}</small></button>)}</div></fieldset>
    <fieldset disabled={disabled}><legend>Level of detail</legend><p>Expose the details you need. Geometry and validation stay the same.</p><div className="mode-choices">{(['simple', 'advanced'] as const).map(mode => <button key={mode} aria-pressed={preferences.mode === mode} onClick={() => onChange({ mode })}><strong>{mode === 'simple' ? 'Simple' : 'Advanced'}</strong><span>{mode === 'simple' ? 'Identity, dimensions, source' : 'Hashes, provenance, interfaces'}</span>{preferences.mode === mode && <Icon name="check" size={16} />}</button>)}</div></fieldset>
    <div className="preference-note"><Icon name="info" /><p>Focus layout keeps the canvas open. Close any panel to return to inspection. On a phone, drag the sheet handle to resize.</p></div>
    <p className="availability-note">Motion follows your device’s reduced-motion preference.</p>
  </div>;
}
