import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { strategyFixture } from '../test/strategy';
import { StrategyPanel } from './StrategyPanel';

it('renders actual policy objectives, context, mechanisms and annotated paths without JSON dumps', () => {
  const session = strategyFixture(), onSelectAction = vi.fn();
  const { container } = render(<StrategyPanel session={session} loading={false} selectedActionId="place_alliance" onSelectAction={onSelectAction} onGenerate={vi.fn()} onArchitectures={vi.fn()} />);
  expect(screen.getByRole('heading', { name: 'Low quadrant scoring cycles' })).toBeVisible();
  expect(screen.getByText('Alliance Pin scoring halves', { exact: true })).toBeVisible();
  expect(screen.getByRole('img', { name: /Annotated abstract playbook/ })).toBeVisible();
  expect(screen.getByText(/Abstract simulation only · default Override/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Official V5 Override manual · pinned v2.1' })).toHaveAttribute('href', 'https://manuals.vex.com/v5/override/v2.1/game/?view=core');
  expect(screen.getAllByText(/Cup interface ready/)[0]).toBeVisible();
  const timeline = screen.getByRole('list', { name: 'Simulated action sequence' });
  fireEvent.click(within(timeline).getAllByRole('button', { name: /Place an alliance Pin/ })[0]);
  expect(onSelectAction).toHaveBeenCalledWith('place_alliance');
  fireEvent.change(screen.getByLabelText('Sequence source'), { target: { value: '0' } });
  expect(screen.getByText('Near calibration mean, not an action script')).toBeVisible();
  expect(container.querySelector('pre')).toBeNull();
  expect(container.textContent).not.toContain('"schemaVersion"');
  expect(screen.getAllByText(/% of decisions/).length).toBeGreaterThan(0);
});

it('marks only successful arrivals as named sites and identifies the fixed-seed execution', () => {
  const session = strategyFixture();
  session.rollout.events = [{ ...session.rollout.events[0], action: 'move_to_goal0', success: false, to_xy: [.6, .8] }];
  const props = { session, loading: false, selectedActionId: null, onSelectAction: vi.fn(), onGenerate: vi.fn(), onArchitectures: vi.fn() };
  const view = render(<StrategyPanel {...props} />);
  expect(within(screen.getByRole('img')).queryByText('low goal')).toBeNull();
  expect(screen.getByText(/fixed episode seed/)).toBeVisible();
  expect(screen.getByText('5000000001')).toBeInTheDocument();
  session.rollout.events[0].success = true;
  view.rerender(<StrategyPanel {...props} />);
  expect(within(screen.getByRole('img')).getByText('low goal')).toBeVisible();
});

it('shows a retryable generation failure without claiming an available CAD design', () => {
  const onGenerate = vi.fn();
  render(<StrategyPanel session={null} loading={false} error="Frozen checkpoint could not be read" selectedActionId={null} onSelectAction={vi.fn()} onGenerate={onGenerate} onArchitectures={vi.fn()} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Frozen checkpoint');
  fireEvent.click(screen.getByRole('button', { name: 'Retry generation' }));
  expect(onGenerate).toHaveBeenCalledOnce();
});
