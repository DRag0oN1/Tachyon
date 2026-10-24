import { useRef, useState, type FormEvent } from 'react';
import type { ComponentDefinition, Selection } from '../api/contracts';
import { Icon } from '../components/Icon';
import type { AssistantSize } from '../workspace/reducer';
import { useDialogFocus } from '../workspace/useDialogFocus';

export interface CommandResult { message: string }
export interface AiCoreEditControls {
  canPreview: boolean;
  canApply: boolean;
  canDiscard: boolean;
  canUndo: boolean;
  busy?: boolean;
  reason?: string;
  candidateLabel?: string;
  preview: (configuration: 'lower' | 'raised') => Promise<CommandResult>;
  apply: () => Promise<CommandResult>;
  discard: () => Promise<CommandResult>;
  undo: () => Promise<CommandResult>;
}
export interface AiCoreProps {
  size: AssistantSize;
  onSize: (size: AssistantSize) => void;
  draft: string;
  onDraft: (text: string) => void;
  component?: ComponentDefinition;
  selection: Selection | null;
  loading: boolean;
  onComponents: () => void;
  contextLabel?: string;
  command?: (text: string) => Promise<CommandResult>;
  controls?: AiCoreEditControls;
  onIntent?: (intent: 'showstrategy' | 'showarchitectures' | 'explain') => void;
  unavailableReason?: string;
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
export function AiCore(props: AiCoreProps) {
  const ref = useRef<HTMLElement>(null);
  const submitting = useRef(false);
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const expanded = props.size !== 'compact';
  useDialogFocus(ref, expanded, props.size === 'fullscreen');
  async function run(action: () => Promise<CommandResult>, clearDraft = false) {
    if (submitting.current || props.controls?.busy) return;
    submitting.current = true; setBusy(true); setFailed(false);
    const submitted = props.draft;
    try {
      const result = await action(); setReply(result.message);
      if (clearDraft && draftRef.current === submitted) props.onDraft('');
    } catch (error) { setReply(error instanceof Error ? error.message : 'The request failed. No successful change was confirmed.'); setFailed(true); }
    finally { submitting.current = false; setBusy(false); }
  }
  const draftRef = useRef(props.draft); draftRef.current = props.draft;
  function submit(e: FormEvent) {
    e.preventDefault();
    if (props.command && props.draft.trim()) void run(() => props.command!(props.draft.trim()), true);
  }
  const disabled = busy || !!props.controls?.busy;
  const reason = props.controls?.reason ?? props.unavailableReason ?? 'Editing requires a qualified assembly and a supported mechanism.';
  const composer = <form className={expanded ? 'assistant-composer' : 'assistant-compact-composer'} onSubmit={submit}>
    <label htmlFor="assistant-command" className={expanded ? undefined : 'sr-only'}>Design request</label>
    {expanded ? <textarea id="assistant-command" rows={3} value={props.draft} onChange={e => props.onDraft(e.target.value)} placeholder="Explain this selection, show strategy, or request a supported edit…" /> : <input id="assistant-command" value={props.draft} onChange={e => props.onDraft(e.target.value)} placeholder="Ask about this selection…" autoComplete="off" />}
    <div className="composer-footer">{expanded && <span>Selection context included · draft kept in this tab</span>}<button className={expanded ? 'primary-button' : 'icon-button'} disabled={disabled || !props.command || !props.draft.trim()} type="submit" aria-label="Send request">{expanded && (disabled ? 'Working…' : 'Send request')}<Icon name="arrow" size={16} /></button></div>
  </form>;
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
    {!expanded && <>{composer}{reply && <p className="assistant-compact-reply" role={failed ? 'alert' : 'status'}>{reply}</p>}</>}
    {expanded && <div className="assistant-body">
      <span className="eyebrow">YOUR WORKSPACE, IN CONTEXT</span>
      <h2>Work from this context.</h2>
      <p>Explain a strategy or selection, compare engineering alternatives, and preview supported mechanism changes when qualified.</p>
      <div className="context-card"><span className="status-dot" /><div><strong>{props.selection ? 'Selected source component' : 'Workspace context'}</strong><p>{props.contextLabel ?? `${props.component?.name ?? 'No source component loaded'}${props.selection?.meshName ? ` · ${props.selection.meshName}` : ''}`}</p></div></div>
      {props.onIntent && <div className="assistant-intents"><button className="text-action" onClick={() => props.onIntent?.('showstrategy')}>Show strategy</button><button className="text-action" onClick={() => props.onIntent?.('showarchitectures')}>Show architectures</button><button className="text-action" disabled={disabled} onClick={() => props.command ? void run(() => props.command!('Explain this selection')) : props.onIntent?.('explain')}>Explain selection</button></div>}
      <button className="text-action" onClick={props.onComponents}>Inspect component catalog <Icon name="arrow" /></button>
      {composer}
      {(disabled || reply) && <p className="assistant-reply" role={failed ? 'alert' : 'status'}>{disabled ? 'Working on your request…' : reply}</p>}
      <section className="assistant-revisions" aria-label="Supported design edits"><h3>Revision controls</h3>{props.controls?.candidateLabel && <p className="strategy-notice">{props.controls.candidateLabel}</p>}<div className="assistant-revision-actions">
        <button className="secondary-button" disabled={disabled || !props.controls?.canPreview} onClick={() => void run(() => props.controls!.preview('raised'))}>Preview raised</button>
        <button className="secondary-button" disabled={disabled || !props.controls?.canPreview} onClick={() => void run(() => props.controls!.preview('lower'))}>Preview lower</button>
        <button className="primary-button" disabled={disabled || !props.controls?.canApply} onClick={() => void run(() => props.controls!.apply())}>Apply</button>
        <button className="secondary-button" disabled={disabled || !props.controls?.canDiscard} onClick={() => void run(() => props.controls!.discard())}>Discard</button>
        <button className="secondary-button" disabled={disabled || !props.controls?.canUndo} onClick={() => void run(() => props.controls!.undo())}>Undo</button>
      </div><p className="availability-note">{reason}</p></section>
    </div>}
  </aside>;
}
