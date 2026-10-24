import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../api/client';
import { capabilitiesFixture, catalogFixture, componentFixture, workspaceFixture } from '../test/contracts';
import { blockedDesignFixture, editableDesignFixture, strategyFixture } from '../test/strategy';
import { WorkspaceShell } from './WorkspaceShell';
import type { DesignSession } from '../api/strategy';

vi.mock('../api/client', async original => ({ ...await original<object>(), api: {
  health: vi.fn(), catalog: vi.fn(), capabilities: vi.fn(), workspace: vi.fn(), patchWorkspace: vi.fn(),
  strategyStatus: vi.fn(), generateStrategy: vi.fn(), post: vi.fn(),
} }));
// Contract stubs deliberately provide no browser or authentic geometry evidence.
vi.mock('../viewer/AssemblyScene', () => ({ AssemblyScene: () => <div data-testid="unit-reference-scene" /> }));
vi.mock('../viewer/DesignAssemblyScene', () => ({ DesignAssemblyScene: ({ session, activeActionId, focusKey, onSelectInstance }: {
  session: DesignSession; activeActionId: string | null; focusKey: number; onSelectInstance: (id: string) => void;
}) => <div data-testid="unit-design-scene" data-revision={session.candidate?.id ?? session.revisionId} data-action={activeActionId} data-focus={focusKey}><button onClick={() => onSelectInstance('unit-scorer')}>Select original software fixture</button></div> }));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.health).mockResolvedValue({ status: 'ok', version: '0.1.0', cadProfile: 'user_provided_local', providerConfigured: false });
  vi.mocked(api.catalog).mockResolvedValue(catalogFixture);
  vi.mocked(api.capabilities).mockResolvedValue({ ...capabilitiesFixture, canGenerateStrategy: true });
  vi.mocked(api.workspace).mockResolvedValue({ ...workspaceFixture, activeComponentId: componentFixture.id });
  vi.mocked(api.patchWorkspace).mockResolvedValue(workspaceFixture);
  vi.mocked(api.strategyStatus).mockResolvedValue({ available: true, competitionId: 'v5-override-v2.1', environmentId: 'override_abstract_strategy_v2_cups' });
  vi.mocked(api.generateStrategy).mockResolvedValue(strategyFixture());
});
async function home() { render(<WorkspaceShell />); await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Strategy' })).toBeEnabled()); }

it.each(['Generate Strategy', 'Create Robot'])('enters through %s without requiring the other screen or any CAD request', async name => {
  await home(); fireEvent.click(screen.getByRole('button', { name }));
  expect(await screen.findByRole('heading', { name: name === 'Create Robot' ? 'Two ways to support the same strategy' : 'Low quadrant scoring cycles' })).toBeVisible();
  expect(api.generateStrategy).toHaveBeenCalledOnce();
  expect(api.post).not.toHaveBeenCalled();
  expect(screen.getByTestId('unit-reference-scene')).toBeInTheDocument();
  expect(screen.getAllByRole('dialog')).toHaveLength(1);
});
it('keeps the reference intact on a blocked architecture, reports missing parts, and refuses edits', async () => {
  vi.mocked(api.post).mockResolvedValue(blockedDesignFixture());
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Check parts and realize concept' }));
  expect(await screen.findByText('CAD blocked — missing qualified parts or mechanisms')).toBeVisible();
  expect(api.post).toHaveBeenCalledWith('/api/designs/realize', { architecture_id: strategyFixture().architectures[0].id });
  expect(screen.getByTestId('unit-reference-scene')).toBeInTheDocument();
  expect(screen.queryByTestId('unit-design-scene')).toBeNull();
  fireEvent.change(screen.getByLabelText('Design request'), { target: { value: 'raise scorer' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  expect(await screen.findByText(/Editing requires a qualified mechanism recipe, components, and assembly placement/)).toBeVisible();
  expect(api.post).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Inspect reference' }));
  expect(screen.getByRole('dialog', { name: 'Components' })).toBeVisible();
  expect(screen.getByText(/Source inspection reference only/)).toBeVisible();
});
it('retains the previous strategy and source if a fresh generation fails; switching panels reuses it', async () => {
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Generate Strategy' }));
  await screen.findByRole('heading', { name: 'Low quadrant scoring cycles' });
  vi.mocked(api.generateStrategy).mockRejectedValueOnce(new Error('Frozen inference failed'));
  fireEvent.click(screen.getByRole('button', { name: 'Rerun the seeded policy' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Frozen inference failed');
  expect(screen.getByRole('heading', { name: 'Low quadrant scoring cycles' })).toBeVisible();
  fireEvent.click(within(screen.getByRole('navigation', { name: 'Workspace tools' })).getByRole('button', { name: 'Architectures' }));
  expect(screen.getByRole('heading', { name: 'Two ways to support the same strategy' })).toBeVisible();
  expect(api.generateStrategy).toHaveBeenCalledTimes(2);
  expect(screen.getByTestId('unit-reference-scene')).toBeInTheDocument();
});
it('reflects status loading/unavailability and retries without relying on the legacy CAD capability', async () => {
  vi.mocked(api.strategyStatus).mockRejectedValueOnce(new Error('Checkpoint service unavailable'));
  render(<WorkspaceShell />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Checkpoint service unavailable');
  expect(screen.getByRole('button', { name: 'Generate Strategy' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Retry strategy connection' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Strategy' })).toBeEnabled());
});
it('previews the selected design, applies exactly that candidate, and passes action/focus and reverse bindings', async () => {
  const accepted = editableDesignFixture();
  const candidate = structuredClone(accepted);
  candidate.candidate = { ...structuredClone(accepted.accepted!), id: 'unit-candidate', parentRevisionId: accepted.revisionId, engineeringHash: 'c'.repeat(64) };
  candidate.candidateBindings = { ...structuredClone(accepted.bindings!), revisionId: 'unit-candidate', engineeringHash: 'c'.repeat(64) };
  candidate.candidateWorldTransforms = structuredClone(accepted.worldTransforms);
  const applied = { ...structuredClone(candidate), accepted: candidate.candidate, bindings: candidate.candidateBindings, revisionId: 'unit-candidate', candidate: null, candidateBindings: null, candidateWorldTransforms: {}, previous: accepted.accepted };
  const undone = { ...structuredClone(accepted), revisionId: 'unit-undone', accepted: { ...structuredClone(accepted.accepted!), id: 'unit-undone', parentRevisionId: 'unit-candidate' }, bindings: { ...structuredClone(accepted.bindings!), revisionId: 'unit-undone' } };
  vi.mocked(api.post).mockResolvedValueOnce(accepted).mockResolvedValueOnce(candidate).mockResolvedValueOnce(applied).mockResolvedValueOnce(undone);
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Check parts and realize concept' }));
  await screen.findByTestId('unit-design-scene');
  expect(screen.getByTestId('design-status')).toHaveTextContent('NOT AUTHENTIC VEX / NOT COMPLETE ROBOT');
  fireEvent.click(screen.getByRole('button', { name: 'Select original software fixture' }));
  fireEvent.click(screen.getByRole('button', { name: 'Place an alliance Pin' }));
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-action', 'place_alliance');
  const before = Number(screen.getByTestId('unit-design-scene').dataset.focus);
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  fireEvent.click(screen.getByRole('button', { name: 'Preview raised' }));
  await waitFor(() => expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-revision', 'unit-candidate'));
  expect(api.post).toHaveBeenNthCalledWith(2, '/api/designs/unit-design/preview', { base_revision_id: 'unit-accepted', configuration_id: 'raised' });
  expect(Number(screen.getByTestId('unit-design-scene').dataset.focus)).toBeGreaterThan(before);
  fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
  expect(await screen.findByText('The server accepted the exact previewed revision.')).toBeVisible();
  expect(api.post).toHaveBeenNthCalledWith(3, '/api/designs/unit-design/decision', { base_revision_id: 'unit-accepted', candidate_revision_id: 'unit-candidate', action: 'apply' });
  expect(screen.getByRole('button', { name: 'Undo' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Undo' }));
  expect(await screen.findByText('Undo confirmed by the server as a new accepted revision.')).toBeVisible();
  expect(api.post).toHaveBeenNthCalledWith(4, '/api/designs/unit-design/decision', { base_revision_id: 'unit-candidate', action: 'undo' });
  expect(screen.getByRole('button', { name: 'Undo' })).toBeDisabled();
});
it('ignores duplicate generation submits until the active request finishes', async () => {
  let finish!: (s: ReturnType<typeof strategyFixture>) => void;
  vi.mocked(api.generateStrategy).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  expect(screen.getByRole('heading', { name: 'Preparing engineering alternatives…' })).toBeVisible();
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: 'Strategy' }));
  expect(api.generateStrategy).toHaveBeenCalledOnce();
  await act(async () => finish(strategyFixture()));
  expect(await screen.findByRole('heading', { name: 'Low quadrant scoring cycles' })).toBeVisible();
});

it('replaces edit controls with actual missing qualifications if a preview request becomes blocked', async () => {
  vi.mocked(api.post).mockResolvedValueOnce(editableDesignFixture()).mockResolvedValueOnce(blockedDesignFixture());
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Check parts and realize concept' }));
  await screen.findByTestId('unit-design-scene');
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  fireEvent.click(screen.getByRole('button', { name: 'Preview raised' }));
  expect(await screen.findByText(/Design qualification is now blocked/)).toHaveTextContent('No qualified scoring mechanism recipe');
  expect(screen.getByRole('button', { name: 'Preview raised' })).toBeDisabled();
  expect(screen.queryByTestId('unit-design-scene')).toBeNull();
  expect(screen.getByTestId('unit-reference-scene')).toBeInTheDocument();
});

it.each(['Do not raise the scorer', 'Raise scoring height by 20 cm', 'Raise the drivetrain', 'Raise the cup cradle', 'Increase drive speed', 'Increase reliability'])('refuses an unsupported or negated engineering command: %s', async text => {
  vi.mocked(api.post).mockResolvedValueOnce(editableDesignFixture());
  await home(); fireEvent.click(screen.getByRole('button', {name:'Create Robot'}));
  fireEvent.click(await screen.findByRole('button', {name:'Check parts and realize concept'}));
  await screen.findByTestId('unit-design-scene');
  fireEvent.change(screen.getByLabelText('Design request'), {target:{value:text}});
  fireEvent.click(screen.getByRole('button', {name:'Send request'}));
  await waitFor(() => expect(screen.getByLabelText('Design request')).toHaveValue(''));
  expect(api.post).toHaveBeenCalledTimes(1); // Only the existing realization.
});

it('retains Undo when the bounded accepted-edit history prevents another preview', async () => {
  const limited=editableDesignFixture(); limited.canEdit=false;
  limited.previous=structuredClone(limited.accepted);
  const restored=structuredClone(limited);
  restored.canEdit=true; restored.previous=null; restored.revisionId='unit-history-restored';
  restored.accepted={...restored.accepted!,id:restored.revisionId,parentRevisionId:limited.revisionId};
  restored.bindings={...restored.bindings!,revisionId:restored.revisionId};
  vi.mocked(api.post).mockResolvedValueOnce(limited).mockResolvedValueOnce(restored);
  await home(); fireEvent.click(screen.getByRole('button',{name:'Create Robot'}));
  fireEvent.click(await screen.findByRole('button',{name:'Check parts and realize concept'}));
  await screen.findByTestId('unit-design-scene');
  fireEvent.click(screen.getByRole('button',{name:'Expand assistant'}));
  expect(screen.getByRole('button',{name:'Preview raised'})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Undo'})).toBeEnabled();
  fireEvent.click(screen.getByRole('button',{name:'Undo'}));
  expect(await screen.findByText('Undo confirmed by the server as a new accepted revision.')).toBeVisible();
});
