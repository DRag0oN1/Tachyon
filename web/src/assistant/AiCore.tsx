import { useRef, useState, type FormEvent } from 'react';
import type { ComponentDefinition, Selection } from '../api/contracts';
import { Icon } from '../components/Icon';
import { MechanicalCore } from '../studio/Mechanical';
import type { AssistantSize } from '../workspace/reducer';
import { useDialogFocus } from '../workspace/useDialogFocus';
import '../styles/ai-core.css';

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
export function AiCore(props: AiCoreProps) {
  const ref = useRef<HTMLElement>(null);
  const submitting = useRef(false);
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
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
  const activity = disabled ? 'busy' : props.loading ? 'loading' : failed && reply ? 'attention'
    : props.controls?.candidateLabel || props.controls?.canApply ? 'preview' : reply ? 'reply' : props.draft.trim() ? 'draft' : 'idle';
  const compactStatus = { busy: 'Working…', loading: 'Loading…', attention: 'Needs attention',
    preview: 'Preview available', reply: 'Response ready', draft: 'Draft saved', idle: 'Open console' }[activity];
  const reason = props.controls?.reason ?? props.unavailableReason ?? 'Editing requires a qualified assembly and a supported mechanism.';
  const context = props.contextLabel ?? `${props.component?.name ?? 'No source component loaded'}${props.selection?.meshName ? ` · ${props.selection.meshName}` : ''}`;
  const composer = <form className="ac-composer ac-composer-open" onSubmit={submit}>
    <label htmlFor="assistant-command" className="ac-field-label">Design request</label>
    <div className="ac-command-rail">
      <textarea id="assistant-command" rows={2} value={props.draft} onChange={e => props.onDraft(e.target.value)} placeholder="Explain this selection or request a supported edit…" />
      <button className="ac-send" disabled={disabled || !props.command || !props.draft.trim()} type="submit" aria-label="Send request" title="Send request"><Icon name="arrow" size={18} /><span className="sr-only">Send request</span></button>
    </div>
    <span className="ac-input-note">Selection included · draft kept in this tab</span>
  </form>;
  const response = (disabled || reply) && <div className={`ac-response assistant-reply ${failed ? 'ac-response-error' : ''}`} role={failed ? 'alert' : 'status'}>
    <span className="ac-field-label">{disabled ? 'Request in progress' : failed ? 'Request failed' : 'Request result'}</span>
    <p>{disabled ? 'Working on your request…' : reply}</p>
  </div>;
  return <aside ref={ref} className={`ai-core mechanical-assistant ai-${props.size}`} data-testid="ai-core" data-state={props.size} data-activity={activity}
    role={expanded ? 'dialog' : undefined} aria-modal={props.size === 'fullscreen' || undefined}
    aria-label="Tachyon assistant" aria-busy={disabled} tabIndex={-1}
    onKeyDown={e => { if (e.key === 'Escape' && expanded) { e.stopPropagation(); props.onSize('compact'); } }}>
    <header className="ac-housing">
      <button className="ac-core-control" aria-label={expanded ? 'Collapse assistant' : 'Expand assistant'} onClick={() => props.onSize(expanded ? 'compact' : 'expanded')} aria-expanded={expanded} title={expanded ? 'Collapse assistant' : 'Expand assistant'}>
        <span className="ac-core-object" aria-hidden="true"><MechanicalCore expanded={expanded} /></span>
        <span className="ac-identity">{expanded ? <><span className="ac-kicker">Tachyon / AI core</span><strong>Design console</strong></> : <><strong>Tachyon</strong><span className="ac-compact-status" aria-live="polite">{compactStatus}</span></>}</span>
        {!expanded && <span className="ac-expand-cue" aria-hidden="true"><Icon name="chevron" size={14} /></span>}
      </button>
      {expanded && <div className="ac-mode-controls">
        <button className="ac-icon-button" aria-label={props.size === 'fullscreen' ? 'Restore assistant panel' : 'Full-screen assistant'} title={props.size === 'fullscreen' ? 'Restore assistant panel' : 'Full-screen assistant'} onClick={() => props.onSize(props.size === 'fullscreen' ? 'expanded' : 'fullscreen')}><Icon name={props.size === 'fullscreen' ? 'collapse' : 'expand'} size={17} /></button>
        <button className="ac-icon-button" aria-label="Close assistant" title="Close assistant" onClick={() => props.onSize('compact')}><Icon name="close" size={17} /></button>
      </div>}
    </header>
    {expanded && <div className="ac-deck">
      <section className="ac-context" aria-label="Current design context">
        <div className="ac-section-heading"><h2>{props.selection ? 'Selection' : 'Current context'}</h2><span className="ac-context-kind">{props.loading ? 'Connecting workspace' : 'Workspace'}</span></div>
        <p>{context}</p>
      </section>
      {composer}
      {response}
      <section className="ac-revisions" aria-label="Supported design edits">
        <div className="ac-section-heading"><h3>Revision controls</h3><span className="ac-step-mark" aria-hidden="true">Preview / Decide</span></div>
        {props.controls?.candidateLabel && <p className="ac-candidate"><span>Preview</span>{props.controls.candidateLabel}</p>}
        <div className="ac-preview-actions" aria-label="Preview configuration">
          <button className="ac-action" disabled={disabled || !props.controls?.canPreview} onClick={() => void run(() => props.controls!.preview('raised'))} aria-describedby="assistant-availability">Preview raised <Icon name="arrow" size={15} /></button>
          <button className="ac-action" disabled={disabled || !props.controls?.canPreview} onClick={() => void run(() => props.controls!.preview('lower'))} aria-describedby="assistant-availability">Preview lower <Icon name="arrow" size={15} /></button>
        </div>
        <div className="ac-decision-actions" aria-label="Revision decisions">
          <button className="ac-action ac-action-primary" disabled={disabled || !props.controls?.canApply} onClick={() => void run(() => props.controls!.apply())}><Icon name="check" size={16} />Apply</button>
          <button className="ac-action" disabled={disabled || !props.controls?.canDiscard} onClick={() => void run(() => props.controls!.discard())}>Discard</button>
          <button className="ac-action" disabled={disabled || !props.controls?.canUndo} onClick={() => void run(() => props.controls!.undo())}><Icon name="reset" size={15} />Undo</button>
        </div>
        <p className="ac-availability" id="assistant-availability">{reason}</p>
      </section>
      <nav className="ac-workspace-actions" aria-label="Workspace actions">
        {props.onIntent && <>
          <button className="ac-tool" onClick={() => props.onIntent?.('showstrategy')}><Icon name="orbit" size={16} />Show strategy</button>
          <button className="ac-tool" onClick={() => props.onIntent?.('showarchitectures')}><Icon name="parts" size={16} />Show architectures</button>
          <button className="ac-tool" disabled={disabled} onClick={() => props.command ? void run(() => props.command!('Explain this selection')) : props.onIntent?.('explain')}><Icon name="info" size={16} />Explain selection</button>
        </>}
        <button className="ac-tool" onClick={props.onComponents}><Icon name="parts" size={16} />Inspect component catalog</button>
      </nav>
      <div className="ac-details">
        <button className="ac-disclosure" aria-expanded={showDetails} aria-controls="assistant-edit-details" onClick={() => setShowDetails(value => !value)}>How design changes work <Icon name="chevron" size={14} /></button>
        {showDetails && <p id="assistant-edit-details">Preview returns a proposed revision. Apply accepts it; Discard closes the preview. Undo restores the preceding accepted design. Availability follows the current design and supported commands.</p>}
      </div>
    </div>}
  </aside>;
}
