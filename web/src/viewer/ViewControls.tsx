import { Icon } from '../components/Icon';
export function ViewControls({ disabled, onFocus, onReset, upAxis = 'Z', onUpAxis }: { disabled: boolean; onFocus: () => void; onReset: () => void; upAxis?: 'X' | 'Y' | 'Z'; onUpAxis?: () => void }) {
  return <div className="view-controls" role="toolbar" aria-label="CAD view controls"><button disabled={disabled} onClick={onFocus}><Icon name="focus" /><span>Focus</span></button><button disabled={disabled} onClick={onReset}><Icon name="reset" /><span>Reset view</span></button>{onUpAxis && <button disabled={disabled} onClick={onUpAxis} aria-label={`Change native up axis, current ${upAxis}`} title="Change viewing orientation; source geometry stays unchanged"><Icon name="orbit" /><span>Up: {upAxis}</span></button>}</div>;
}
