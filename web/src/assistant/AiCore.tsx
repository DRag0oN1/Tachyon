import { useRef } from 'react';
import type { ComponentDefinition, Selection } from '../api/contracts';
import { Icon } from '../components/Icon';
import type { AssistantSize } from '../workspace/reducer';
import { useDialogFocus } from '../workspace/useDialogFocus';

interface Props {
  size: AssistantSize;
  onSize: (size: AssistantSize) => void;
  draft: string;
  onDraft: (text: string) => void;
  component?: ComponentDefinition;
  selection: Selection | null;
  loading: boolean;
  onComponents: () => void;
}
function CoreGlyph({ loading }: { loading: boolean }) {
  return <svg className={`core-glyph ${loading ? 'is-connecting' : ''}`} viewBox="0 0 64 64" fill="none" aria-hidden="true">
    <path className="core-orbit" d="M32 3 58 18v28L32 61 6 46V18Z" />
    <g className="core-module module-a"><path d="m30 14-14 8v9l14-8Z" /><path d="m16 24 8 5v10l-8-5Z" /></g>
    <g className="core-module module-b"><path d="m34 14 14 8v9l-14-8Z" /><path d="m48 24-8 5v10l8-5Z" /></g>
    <g className="core-module module-c"><path d="m16 38 14 8v9l-14-8Z" /></g>
    <g className="core-module module-d"><path d="m48 38-14 8v9l14-8Z" /></g>
    <path className="core-center" d="m32 26 7 4v8l-7 4-7-4v-8Z" />
  </svg>;
}
export function AiCore(props: Props) {
  const ref = useRef<HTMLElement>(null);
  const expanded = props.size !== 'compact';
  useDialogFocus(ref, expanded, props.size === 'fullscreen');
  return <aside ref={ref} className={`ai-core ai-${props.size}`} data-testid="ai-core" data-state={props.size}
    role={expanded ? 'dialog' : undefined} aria-modal={props.size === 'fullscreen' || undefined}
    aria-label="Tachyon assistant" tabIndex={-1}
    onKeyDown={e => { if (e.key === 'Escape' && expanded) { e.stopPropagation(); props.onSize('compact'); } }}>
    <div className="ai-header">
      <button className="core-launch" aria-label={expanded ? 'Collapse assistant' : 'Expand assistant'} onClick={() => props.onSize(expanded ? 'compact' : 'expanded')} aria-expanded={expanded}>
        <CoreGlyph loading={props.loading} />
        <span className="core-caption"><strong>Tachyon</strong><span>{props.loading ? 'Connecting workspace' : 'Design intelligence'}</span></span>
      </button>
      <div className="assistant-controls">
        <button className="icon-button" aria-label={props.size === 'fullscreen' ? 'Restore assistant panel' : 'Full-screen assistant'} onClick={() => props.onSize(props.size === 'fullscreen' ? 'expanded' : 'fullscreen')}><Icon name={props.size === 'fullscreen' ? 'collapse' : 'expand'} size={16} /></button>
        {expanded && <button className="icon-button" aria-label="Close assistant" onClick={() => props.onSize('compact')}><Icon name="close" size={16} /></button>}
      </div>
    </div>
    {expanded && <div className="assistant-body">
      <span className="eyebrow">YOUR WORKSPACE, IN CONTEXT</span>
      <h2>Start with what’s real.</h2>
      <p>Inspect your source components and their provenance. Design generation and engineering changes are currently unavailable.</p>
      <div className="context-card"><span className="status-dot" /><div><strong>{props.selection ? 'Selected source component' : 'Inspection context'}</strong><p>{props.component?.name ?? 'No source component loaded'}{props.selection?.meshName ? ` · ${props.selection.meshName}` : ''}</p></div></div>
      <button className="text-action" onClick={props.onComponents}>Inspect component catalog <Icon name="arrow" /></button>
      <div className="assistant-composer">
        <label htmlFor="assistant-command">Design request</label>
        <textarea id="assistant-command" rows={3} value={props.draft} onChange={e => props.onDraft(e.target.value)} placeholder="Keep a request here for when editing is available…" />
        <div className="composer-footer"><span>Draft retained in this tab</span><button className="primary-button" disabled>Send request <Icon name="arrow" size={15} /></button></div>
      </div>
      <p className="availability-note" role="status">Editing unavailable. No command has been submitted and no design has changed.</p>
    </div>}
  </aside>;
}
