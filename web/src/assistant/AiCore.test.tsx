import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { AiCore, type AiCoreProps } from './AiCore';

function props(): AiCoreProps {
  return { size: 'compact', onSize: vi.fn(), draft: 'Explain the selected Pin intake', onDraft: vi.fn(), selection: null, loading: false,
    contextLabel: 'Pin intake · source reference', onComponents: vi.fn(), command: vi.fn().mockResolvedValue({ message: 'Selected Pin intake is reference geometry only.' }) };
}
it('opens command entry from the compact object, submits and delegates internal sizing', async () => {
  const p = props(); const view = render(<AiCore {...p} />);
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Send request' })).not.toBeInTheDocument();
  expect(screen.getAllByRole('button')).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  expect(p.onSize).toHaveBeenCalledWith('expanded');
  view.rerender(<AiCore {...p} size="expanded" />);
  expect(screen.getByRole('textbox', { name: 'Design request' })).toHaveValue(p.draft);
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  expect(await screen.findByRole('status')).toHaveTextContent('reference geometry only');
  expect(p.command).toHaveBeenCalledWith(p.draft);
  expect(p.onDraft).toHaveBeenCalledWith('');
  fireEvent.click(screen.getByRole('button', { name: 'Full-screen assistant' }));
  expect(p.onSize).toHaveBeenCalledWith('fullscreen');
});
it('retains a newer draft while a previous request completes and shows errors truthfully', async () => {
  const p = props(); p.size = 'expanded'; let finish!: (r: { message: string }) => void;
  p.command = vi.fn().mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const view = render(<AiCore {...p} />);
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  expect(screen.getByRole('button', { name: 'Send request' })).toBeDisabled();
  view.rerender(<AiCore {...p} draft="A newer request" />);
  await act(async () => finish({ message: 'Explanation returned' }));
  expect(p.onDraft).not.toHaveBeenCalled();
  view.rerender(<AiCore {...p} command={vi.fn().mockRejectedValue(new Error('Stale revision; refresh before applying'))} />);
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Stale revision');
});
it('delegates preview and decision controls and disables unsupported actions with a reason', async () => {
  const preview = vi.fn().mockResolvedValue({ message: 'Server returned candidate test-revision' });
  const p = props();
  const controls = { canPreview: true, canApply: false, canDiscard: false, canUndo: false,
    preview, apply: vi.fn(), discard: vi.fn(), undo: vi.fn(), reason: 'Raised and lower configurations only; physical performance unverified.' };
  render(<AiCore {...p} size="expanded" controls={controls} />);
  fireEvent.click(screen.getByRole('button', { name: 'Preview raised' }));
  expect(await screen.findByRole('status')).toHaveTextContent('candidate test-revision');
  expect(preview).toHaveBeenCalledWith('raised');
  expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Undo' })).toBeDisabled();
  expect(screen.getByText(/Raised and lower configurations only/)).toBeVisible();
});

it('keeps every size control inside the assistant and preserves the request across sizes', () => {
  const p = props(); const view = render(<AiCore {...p} />);
  const core = screen.getByTestId('ai-core');
  expect(core).toHaveClass('mechanical-assistant');
  fireEvent.click(within(core).getByRole('button', { name: 'Expand assistant' }));
  expect(p.onSize).toHaveBeenLastCalledWith('expanded');
  view.rerender(<AiCore {...p} size="expanded" />);
  fireEvent.click(within(core).getByRole('button', { name: 'Full-screen assistant' }));
  expect(p.onSize).toHaveBeenLastCalledWith('fullscreen');
  view.rerender(<AiCore {...p} size="fullscreen" />);
  expect(core).toHaveAttribute('aria-modal', 'true');
  expect(screen.getByRole('textbox', { name: 'Design request' })).toHaveValue(p.draft);
  fireEvent.click(within(core).getByRole('button', { name: 'Restore assistant panel' }));
  expect(p.onSize).toHaveBeenLastCalledWith('expanded');
  fireEvent.click(within(core).getByRole('button', { name: 'Collapse assistant' }));
  expect(p.onSize).toHaveBeenLastCalledWith('compact');
  fireEvent.click(within(core).getByRole('button', { name: 'Close assistant' }));
  expect(p.onSize).toHaveBeenLastCalledWith('compact');
  expect(p.onDraft).not.toHaveBeenCalled();
});

it.each(['Apply', 'Discard', 'Undo', 'Preview lower'] as const)('delegates %s without inventing a revision result', async label => {
  const p = props();
  const controls = {
    canPreview: true, canApply: true, canDiscard: true, canUndo: true,
    preview: vi.fn().mockResolvedValue({ message: 'Server preview response' }),
    apply: vi.fn().mockResolvedValue({ message: 'Server apply response' }),
    discard: vi.fn().mockResolvedValue({ message: 'Server discard response' }),
    undo: vi.fn().mockResolvedValue({ message: 'Server undo response' }),
    candidateLabel: 'Candidate revision from the current design',
  };
  render(<AiCore {...p} size="expanded" controls={controls} />);
  expect(screen.getByText(controls.candidateLabel)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: label }));
  expect(await screen.findByRole('status')).toHaveTextContent(/Server .* response/);
  const called = label === 'Preview lower' ? controls.preview : controls[label.toLowerCase() as 'apply' | 'discard' | 'undo'];
  expect(called).toHaveBeenCalledTimes(1);
  if (label === 'Preview lower') expect(called).toHaveBeenCalledWith('lower');
  expect(p.onDraft).not.toHaveBeenCalled();
});

it('prevents a second command or revision action while a decision is pending', async () => {
  const p = props(); let finish!: (r: { message: string }) => void;
  const apply = vi.fn().mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const controls = {
    canPreview: true, canApply: true, canDiscard: true, canUndo: true,
    preview: vi.fn(), apply, discard: vi.fn(), undo: vi.fn(),
  };
  render(<AiCore {...p} size="expanded" controls={controls} />);
  fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
  expect(screen.getByRole('dialog')).toHaveAttribute('aria-busy', 'true');
  for (const name of ['Preview raised', 'Preview lower', 'Apply', 'Discard', 'Undo', 'Send request']) {
    expect(screen.getByRole('button', { name })).toBeDisabled();
  }
  fireEvent.submit(screen.getByRole('textbox', { name: 'Design request' }).closest('form')!);
  expect(p.command).not.toHaveBeenCalled();
  expect(controls.preview).not.toHaveBeenCalled();
  await act(async () => finish({ message: 'Accepted exact server revision' }));
  expect(screen.getByRole('status')).toHaveTextContent('Accepted exact server revision');
  expect(screen.getByRole('dialog')).toHaveAttribute('aria-busy', 'false');
});

it('hides errors on collapse and restores the response, context and draft on expansion', async () => {
  const p = props(); p.command = vi.fn().mockRejectedValue(new Error('Current source is unavailable'));
  const view = render(<AiCore {...p} size="expanded" />);
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Current source is unavailable');
  fireEvent.click(screen.getByRole('button', { name: 'Close assistant' }));
  expect(p.onSize).toHaveBeenCalledWith('compact');
  view.rerender(<AiCore {...p} />);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.queryByText('Current source is unavailable')).not.toBeInTheDocument();
  expect(screen.getByText('Needs attention')).toBeVisible();
  expect(screen.getAllByRole('button')).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  view.rerender(<AiCore {...p} size="expanded" />);
  expect(screen.getByRole('alert')).toHaveTextContent('Current source is unavailable');
  expect(screen.getByText(p.contextLabel!)).toBeVisible();
  view.rerender(<AiCore {...p} size="fullscreen" />);
  expect(screen.getByRole('alert')).toHaveTextContent('Current source is unavailable');
  expect(screen.getByRole('textbox', { name: 'Design request' })).toHaveValue(p.draft);
  expect(p.onDraft).not.toHaveBeenCalled();
});

it('finishes a request while collapsed without opening a response panel or clearing a newer draft', async () => {
  const p = props(); let finish!: (r: { message: string }) => void;
  p.command = vi.fn().mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const view = render(<AiCore {...p} size="expanded" />);
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  view.rerender(<AiCore {...p} draft="Keep this newer request" />);
  expect(screen.getByTestId('ai-core')).toHaveAttribute('aria-busy', 'true');
  expect(screen.getByText('Working…')).toBeVisible();
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  await act(async () => finish({ message: 'The current server response' }));
  expect(screen.getByText('Response ready')).toBeVisible();
  expect(screen.queryByText('The current server response')).not.toBeInTheDocument();
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  expect(p.onSize).not.toHaveBeenCalled();
  view.rerender(<AiCore {...p} size="expanded" draft="Keep this newer request" />);
  expect(screen.getByRole('status')).toHaveTextContent('The current server response');
  expect(screen.getByRole('textbox', { name: 'Design request' })).toHaveValue('Keep this newer request');
  expect(p.onDraft).not.toHaveBeenCalled();
});

it('keeps a pending preview behind a compact notification until opened', () => {
  const p = props();
  const controls = { canPreview: false, canApply: true, canDiscard: true, canUndo: false,
    preview: vi.fn(), apply: vi.fn(), discard: vi.fn(), undo: vi.fn(), candidateLabel: 'Exact candidate revision abc123' };
  const view = render(<AiCore {...p} controls={controls} />);
  expect(screen.getByText('Preview available')).toBeVisible();
  expect(screen.queryByText(controls.candidateLabel)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument();
  view.rerender(<AiCore {...p} size="expanded" controls={controls} />);
  expect(screen.getByText(controls.candidateLabel)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
  expect(controls.apply).not.toHaveBeenCalled();
});

it.each(['snap', 'shift'])('uses the shared mechanical SVG in %s with an object-only compact state', theme => {
  const p = props(); p.draft = '';
  const view = render(<main className="workspace" data-theme={theme}><AiCore {...p} /></main>);
  const core = screen.getByTestId('ai-core');
  expect(core.querySelector('.mechanical-core')).toHaveAttribute('data-expanded', 'false');
  expect(within(core).getByText('Tachyon')).toBeVisible();
  expect(within(core).getByText('Open console')).toBeVisible();
  expect(core.querySelector('form')).toBeNull();
  expect(core.querySelector('.ac-response')).toBeNull();
  view.rerender(<main className="workspace" data-theme={theme}><AiCore {...p} size="expanded" /></main>);
  expect(core.querySelector('.mechanical-core')).toHaveAttribute('data-expanded', 'true');
  fireEvent.change(screen.getByRole('textbox', { name: 'Design request' }), { target: { value: 'Explain this design' } });
  expect(p.onDraft).toHaveBeenCalledWith('Explain this design');
});

it('delegates workspace actions and explains through the actual command callback', async () => {
  const p = props(); p.onIntent = vi.fn();
  render(<AiCore {...p} size="expanded" />);
  fireEvent.click(screen.getByRole('button', { name: 'Show strategy' }));
  fireEvent.click(screen.getByRole('button', { name: 'Show architectures' }));
  fireEvent.click(screen.getByRole('button', { name: 'Inspect component catalog' }));
  expect(p.onIntent).toHaveBeenCalledWith('showstrategy');
  expect(p.onIntent).toHaveBeenCalledWith('showarchitectures');
  expect(p.onComponents).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Explain selection' }));
  expect(await screen.findByRole('status')).toHaveTextContent('reference geometry only');
  expect(p.command).toHaveBeenCalledWith('Explain this selection');
  expect(p.onDraft).not.toHaveBeenCalled();
});

it('keeps unavailable controls honest while allowing the provided explanation intent', () => {
  const p = props(); p.command = undefined; p.onIntent = vi.fn();
  render(<AiCore {...p} size="expanded" unavailableReason="No editable assembly is loaded" />);
  for (const name of ['Preview raised', 'Preview lower', 'Apply', 'Discard', 'Undo', 'Send request']) {
    expect(screen.getByRole('button', { name })).toBeDisabled();
  }
  expect(screen.getByText('No editable assembly is loaded')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Explain selection' }));
  expect(p.onIntent).toHaveBeenCalledWith('explain');
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('progressively reveals editing help and traps focus only in full-screen mode', () => {
  const p = props(); const bubbled = vi.fn();
  render(<div onKeyDown={bubbled}><AiCore {...p} size="fullscreen" /></div>);
  const disclosure = screen.getByRole('button', { name: 'How design changes work' });
  expect(disclosure).toHaveAttribute('aria-expanded', 'false');
  expect(screen.queryByText(/Preview returns a proposed revision/)).not.toBeInTheDocument();
  fireEvent.click(disclosure);
  expect(disclosure).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByText(/Preview returns a proposed revision/)).toBeVisible();
  const first = screen.getByRole('button', { name: 'Collapse assistant' });
  disclosure.focus(); fireEvent.keyDown(disclosure, { key: 'Tab' });
  expect(first).toHaveFocus();
  fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
  expect(disclosure).toHaveFocus();
  bubbled.mockClear();
  fireEvent.keyDown(disclosure, { key: 'Escape' });
  expect(p.onSize).toHaveBeenCalledWith('compact');
  expect(bubbled).not.toHaveBeenCalled();
});
