import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../api/client';
import { capabilitiesFixture, workspaceFixture } from '../test/contracts';
import { WorkspaceShell } from './WorkspaceShell';

vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<object>(), api: { health: vi.fn(), catalog: vi.fn(), capabilities: vi.fn(), workspace: vi.fn(), patchWorkspace: vi.fn(), get: vi.fn(), strategyStatus: vi.fn() } }));
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.health).mockResolvedValue({ status: 'ok', version: '0.1.0', cadProfile: 'user_provided_local', providerConfigured: true });
  vi.mocked(api.catalog).mockResolvedValue({ profile: 'user_provided_local', components: [], blockers: [{ code: 'MISSING_LOCAL_CAD', message: 'No rights-qualified local source parts are registered.' }] });
  vi.mocked(api.capabilities).mockResolvedValue({ ...capabilitiesFixture, canInspect: false });
  vi.mocked(api.workspace).mockResolvedValue(structuredClone(workspaceFixture));
  vi.mocked(api.patchWorkspace).mockResolvedValue(structuredClone(workspaceFixture));
  vi.mocked(api.strategyStatus).mockResolvedValue({available:false,competitionId:'v5-override-v2.1',environmentId:'override_abstract_strategy_v2_cups',reason:'The frozen policy is unavailable.'});
  vi.mocked(api.get).mockImplementation(async path=>{
    if(path==='/api/designs/catalog')return {schemaVersion:1,kind:'tachyon.design_catalog',architectures:[],saved:[],canGenerateAdditionalArchitectures:false};
    throw new Error(`Unexpected test GET: ${path}`);
  });
});

it('keeps CAD absent and generation disabled even when a provider is configured', async () => {
  render(<WorkspaceShell />);
  expect(await screen.findByText('LOCAL / CONNECTED')).toBeVisible();
  expect(screen.queryByTestId('cad-canvas')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Generate Strategy' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Create Robot' })).toBeDisabled();
  expect(screen.getByRole('dialog',{name:'Studio'})).toBeVisible();
  expect(screen.getByRole('heading',{name:'Make your next move.'})).toBeVisible();
  expect(screen.getByText('The frozen policy is unavailable.')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Components' }));
  expect(screen.getByRole('heading', { name: 'Your catalog is empty' })).toBeVisible();
  expect(screen.getByText('MISSING LOCAL CAD', { exact: false })).toBeVisible();
});
it('preserves a command draft across all assistant sizes and panel switches', async () => {
  render(<WorkspaceShell />); await screen.findByText('LOCAL / CONNECTED');
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  expect(screen.queryByRole('dialog', { name: 'Studio' })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Design request'), { target: { value: 'Raise the scoring height' } });
  expect(screen.getByRole('button', { name: 'Send request' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Full-screen assistant' }));
  expect(screen.getByRole('dialog', { name: 'Tachyon assistant' })).toHaveAttribute('aria-modal', 'true');
  fireEvent.click(screen.getByRole('button', { name: 'Close assistant' }));
  fireEvent.click(screen.getByRole('button', { name: 'Preferences' }));
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  expect(screen.getByLabelText('Design request')).toHaveValue('Raise the scoring height');
  expect(screen.getAllByRole('dialog')).toHaveLength(1);
  expect(api.patchWorkspace).not.toHaveBeenCalled();
});
it('reports unsaved preferences, preserves local choice, and retries the real patch', async () => {
  vi.mocked(api.patchWorkspace).mockRejectedValueOnce(new Error('save unavailable'));
  const { container } = render(<WorkspaceShell />); await screen.findByText('LOCAL / CONNECTED');
  fireEvent.click(screen.getByRole('button', { name: 'Preferences' }));
  fireEvent.click(screen.getByRole('button', { name: /SHIFT/ }));
  expect(container.querySelector('main')).toHaveAttribute('data-theme', 'shift');
  expect(await screen.findByRole('button', { name: 'Retry save' })).toBeVisible();
  expect(api.patchWorkspace).toHaveBeenCalledWith({ preferences: { theme: 'shift' } });
  fireEvent.click(screen.getByRole('button', { name: 'Retry save' }));
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Retry save' })).not.toBeInTheDocument());
  expect(container.querySelector('main')).toHaveAttribute('data-theme', 'shift');
});
it('serializes rapid preference updates and merges the latest values', async () => {
  let resolve!: (value: typeof workspaceFixture) => void;
  vi.mocked(api.patchWorkspace).mockImplementationOnce(() => new Promise(r => { resolve = r; }));
  render(<WorkspaceShell />); await screen.findByText('LOCAL / CONNECTED');
  fireEvent.click(screen.getByRole('button', { name: 'Preferences' }));
  fireEvent.click(screen.getByRole('button', { name: /SHIFT/ }));
  fireEvent.click(screen.getByRole('button', { name: /Advanced/ }));
  await waitFor(() => expect(api.patchWorkspace).toHaveBeenCalledTimes(1));
  await act(async () => resolve(workspaceFixture));
  await waitFor(() => expect(api.patchWorkspace).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.patchWorkspace).mock.calls[1][0]).toEqual({ preferences: { theme: 'shift', mode: 'advanced' } });
});
