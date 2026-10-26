import { fireEvent, render, screen, within } from '@testing-library/react';
import { useState } from 'react';
import { expect, it, vi } from 'vitest';
import { blockedDesignFixture, editableDesignFixture, strategyFixture } from '../test/strategy';
import { StrategyPanel } from './StrategyPanel';
import { buildStrategyPhases } from './strategyPlaybook';

function openAnalysis() { fireEvent.click(screen.getByText('Advanced Analysis')); }

// SVG and complete evidence visibility checks are CPU-heavy in jsdom,
// especially alongside real software-WebGL verification. Assertions stay intact.
vi.setConfig({testTimeout:15_000});

it('renders actual policy objectives, context, mechanisms and annotated paths without JSON dumps', () => {
  const session = strategyFixture(), onSelectAction = vi.fn();
  const { container } = render(<StrategyPanel session={session} loading={false} selectedActionId="place_alliance" onSelectAction={onSelectAction} onGenerate={vi.fn()} onArchitectures={vi.fn()} />);
  expect(screen.getByRole('heading', { name: 'Low quadrant scoring cycles' })).toBeVisible();
  expect(within(container.querySelector('.playbook-heading')!).getByText('Alliance Pin scoring halves', { exact: true })).toBeVisible();
  expect(screen.getByRole('img', { name: /Annotated abstract playbook/ })).toBeVisible();
  expect(screen.getByText(/Abstract simulation only · default Override/)).toBeVisible();
  expect(screen.queryByRole('list', { name: 'Simulated action sequence' })).toBeNull();
  openAnalysis();
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
  expect(within(screen.getByRole('img', { name: /Annotated abstract playbook/ })).queryByText('low goal')).toBeNull();
  openAnalysis();
  expect(screen.getByText(/fixed episode seed/)).toBeVisible();
  expect(screen.getByText('5000000001', { selector: 'dd' })).toBeInTheDocument();
  session.rollout.events[0].success = true;
  view.rerender(<StrategyPanel {...props} />);
  expect(within(screen.getByRole('img', { name: /Annotated abstract playbook/ })).getByText('low goal')).toBeVisible();
});

it('shows a concise phase rail whose actual action IDs drive selection, retaining full evidence in one collapsible', () => {
  const session = strategyFixture(), onSelectAction = vi.fn(), onArchitectures = vi.fn();
  const phases = buildStrategyPhases(session.rollout.events);
  const view = render(<StrategyPanel session={session} loading={false} selectedActionId={null} onSelectAction={onSelectAction} onGenerate={vi.fn()} onArchitectures={onArchitectures} />);
  const rail = screen.getByRole('list', { name: 'Strategy phases' });
  const buttons = within(rail).getAllByRole('button');
  expect(buttons).toHaveLength(6);
  expect(view.container.querySelectorAll('details')).toHaveLength(1);
  expect(screen.getByText('Executed episode points')).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Policy and simulation evidence' })).toBeNull();
  buttons.forEach((button, i) => {
    fireEvent.click(button);
    expect(onSelectAction).toHaveBeenLastCalledWith(phases[i].primaryActionId);
    expect(button).toHaveAttribute('aria-pressed', 'true');
    expect(within(screen.getByLabelText('Selected strategy phase')).getByRole('heading', { name: phases[i].title })).toBeVisible();
  });
  fireEvent.click(screen.getByRole('button', { name: 'Compare engineering alternatives' }));
  expect(onArchitectures).toHaveBeenCalledOnce();
  openAnalysis();
  expect(within(screen.getByRole('list', { name: 'Simulated action sequence' })).getAllByRole('button')).toHaveLength(session.rollout.events.length);
  expect(screen.getByText(session.rollout.policyParameterHash, { exact: true, selector: '.strategy-hash' })).toBeVisible();
  expect(screen.getByText(session.spec.policy.checkpoint.sha256, { exact: true })).toBeVisible();
  session.limitations.forEach(limit => expect(screen.getByText(limit, { exact: true })).toBeVisible());
  expect(screen.getByRole('heading', { name: 'Hard minimums' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Held-out confirmation comparison' })).toBeVisible();
  fireEvent.change(screen.getByLabelText('Sequence source'), { target: { value: '1' } });
  expect(screen.getByText('Representative episode points')).toBeVisible();
  expect(screen.getByText(/Saved evaluation mean contributions/)).toBeVisible();
  expect(screen.getByText(/mean modeled point difference, strategy-aware/)).toBeVisible();
  openAnalysis();
  expect(screen.queryByRole('list', { name: 'Simulated action sequence' })).toBeNull();
  // This exercises six SVG-rich phases plus the complete evidence DOM. Keep
  // every assertion; allow CPU contention during actual software-WebGL checks.
}, 15_000);

it('opens Advanced Analysis in Advanced mode and retains a usable rerun control in Simple mode', () => {
  const props = { session: strategyFixture(), loading: false, selectedActionId: null, onSelectAction: vi.fn(), onGenerate: vi.fn(), onArchitectures: vi.fn() };
  const view = render(<StrategyPanel {...props} mode="advanced" />);
  expect(screen.getByRole('list', { name: 'Simulated action sequence' })).toBeVisible();
  view.rerender(<StrategyPanel {...props} mode="simple" />);
  expect(screen.queryByRole('list', { name: 'Simulated action sequence' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Rerun the seeded policy' }));
  expect(props.onGenerate).toHaveBeenCalledOnce();
  view.rerender(<StrategyPanel {...props} available={false} />);
  expect(screen.getByRole('button', { name: 'Rerun the seeded policy' })).toBeDisabled();
});

it('distinguishes proposed requirements from exact revision-linked fixture coordinates and unverified task capability', () => {
  const props = { session: strategyFixture(), loading: false, selectedActionId: 'place_alliance', onSelectAction: vi.fn(), onGenerate: vi.fn(), onArchitectures: vi.fn() };
  const view = render(<StrategyPanel {...props} assembly={blockedDesignFixture()} />);
  expect(screen.getByText('Proposed requirements')).toBeVisible();
  expect(screen.getByText(/Proposed needs, not realized components/)).toBeVisible();
  expect(screen.queryByRole('img', { name: /Assembly joint and tool anchor/ })).toBeNull();
  const assembly = editableDesignFixture();
  view.rerender(<StrategyPanel {...props} assembly={assembly} />);
  expect(screen.getByRole('img', { name: /Assembly joint and tool anchor/ })).toBeVisible();
  expect(view.container.querySelector('.assembly-coordinate-sketch')).toHaveAttribute('data-revision-id', assembly.revisionId);
  expect(screen.getByText(/Software fixture only/)).toBeVisible();
  expect(screen.getByText(/Revision-linked assembly; task capability unverified/)).toBeVisible();
  assembly.bindings!.engineeringHash = 'c'.repeat(64);
  view.rerender(<StrategyPanel {...props} assembly={assembly} />);
  expect(screen.queryByRole('img', { name: /Assembly joint and tool anchor/ })).toBeNull();
  expect(screen.getByText('Proposed requirements')).toBeVisible();
});

it('selects the containing phase for an external CAD action and reports empty rollouts honestly', () => {
  const session = strategyFixture();
  const props = { session, loading: false, selectedActionId: 'acquire_cup', onSelectAction: vi.fn(), onGenerate: vi.fn(), onArchitectures: vi.fn() };
  const view = render(<StrategyPanel {...props} />);
  expect(within(screen.getByRole('list', { name: 'Strategy phases' })).getByRole('button', { pressed: true })).toHaveTextContent('Acquire a Pin and Cup');
  session.rollout.events = [];
  view.rerender(<StrategyPanel {...props} />);
  expect(screen.queryByRole('list', { name: 'Strategy phases' })).toBeNull();
  expect(screen.getByText(/No actions were returned for this sequence/)).toBeVisible();
  expect(screen.queryByRole('img', { name: /Annotated abstract playbook/ })).toBeNull();
});

it('offers concept inspection when no exact binding exists, without invoking realized-mechanism callbacks', () => {
  const onArchitectures = vi.fn(), onInspectMechanism = vi.fn(), onAskMechanism = vi.fn();
  render(<StrategyPanel session={strategyFixture()} assembly={blockedDesignFixture()} loading={false} selectedActionId="place_alliance" onSelectAction={vi.fn()} onGenerate={vi.fn()} {...{ onArchitectures, onInspectMechanism, onAskMechanism }} />);
  expect(screen.getByText(/Architecture concept · assembly not linked/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Inspect Design' }));
  expect(onArchitectures).toHaveBeenCalledOnce();
  expect(screen.queryByRole('button', { name: 'Inspect mechanism' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Ask about mechanism' })).toBeNull();
  expect(onInspectMechanism).not.toHaveBeenCalled();
  expect(onAskMechanism).not.toHaveBeenCalled();
});

it('commits the selected phase action before asking the parent to inspect its actual binding', () => {
  const session = strategyFixture(), assembly = editableDesignFixture();
  assembly.bindings!.actions.push({ ...structuredClone(assembly.bindings!.actions[0]), actionId: session.rollout.events[0].action });
  const onInspect = vi.fn(), onAsk = vi.fn();
  function Harness() {
    const [action, setAction] = useState<string | null>(null);
    return <StrategyPanel session={session} assembly={assembly} loading={false} selectedActionId={action} onSelectAction={setAction} onGenerate={vi.fn()} onArchitectures={vi.fn()} onInspectMechanism={() => onInspect(action)} onAskMechanism={() => onAsk(action)} />;
  }
  render(<Harness />);
  fireEvent.click(screen.getByRole('button', { name: 'Inspect mechanism' }));
  expect(onInspect).toHaveBeenCalledExactlyOnceWith(session.rollout.events[0].action);
  fireEvent.click(screen.getByRole('button', { name: 'Ask about mechanism' }));
  expect(onAsk).toHaveBeenCalledExactlyOnceWith(session.rollout.events[0].action);
  expect(screen.queryByRole('button', { name: 'Inspect Design' })).toBeNull();
});

it('shows a retryable generation failure without claiming an available CAD design', () => {
  const onGenerate = vi.fn();
  render(<StrategyPanel session={null} loading={false} error="Frozen checkpoint could not be read" selectedActionId={null} onSelectAction={vi.fn()} onGenerate={onGenerate} onArchitectures={vi.fn()} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Frozen checkpoint');
  fireEvent.click(screen.getByRole('button', { name: 'Retry generation' }));
  expect(onGenerate).toHaveBeenCalledOnce();
});
