import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { AiCore, type AiCoreProps } from './AiCore';

function props(): AiCoreProps {
  return { size: 'compact', onSize: vi.fn(), draft: 'Explain the selected Pin intake', onDraft: vi.fn(), selection: null, loading: false,
    contextLabel: 'Pin intake · source reference', onComponents: vi.fn(), command: vi.fn().mockResolvedValue({ message: 'Selected Pin intake is reference geometry only.' }) };
}
it('submits from the compact input, exposes the result and delegates internal sizing', async () => {
  const p = props(); render(<AiCore {...p} />);
  expect(screen.getByRole('textbox', { name: 'Design request' })).toHaveValue(p.draft);
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  expect(await screen.findByRole('status')).toHaveTextContent('reference geometry only');
  expect(p.command).toHaveBeenCalledWith(p.draft);
  expect(p.onDraft).toHaveBeenCalledWith('');
  fireEvent.click(screen.getByRole('button', { name: 'Full-screen assistant' }));
  expect(p.onSize).toHaveBeenCalledWith('fullscreen');
});
it('retains a newer draft while a previous request completes and shows errors truthfully', async () => {
  const p = props(); let finish!: (r: { message: string }) => void;
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
