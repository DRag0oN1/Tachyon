import { Icon } from '../components/Icon';
export function ViewControls({ disabled, onFocus, onReset }: { disabled: boolean; onFocus: () => void; onReset: () => void }) {
  return <div className="view-controls" role="toolbar" aria-label="CAD view controls"><button disabled={disabled} onClick={onFocus}><Icon name="focus" /><span>Focus</span></button><button disabled={disabled} onClick={onReset}><Icon name="reset" /><span>Reset view</span></button></div>;
}
