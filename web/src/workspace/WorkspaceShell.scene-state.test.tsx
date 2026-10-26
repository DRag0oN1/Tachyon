import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { api } from '../api/client';
import { capabilitiesFixture, catalogFixture, componentFixture, workspaceFixture } from '../test/contracts';
import { WorkspaceShell } from './WorkspaceShell';

vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<object>(), api: { health: vi.fn(), catalog: vi.fn(), capabilities: vi.fn(), workspace: vi.fn(), patchWorkspace: vi.fn() } }));
vi.mock('../viewer/AssemblyScene', async () => {
  const { useEffect } = await import('react');
  return { AssemblyScene: function RendererContractStub({ onStatus }: { onStatus: (status: { state: 'ready'; meshCount: number }) => void }) {
    // State contract only; this stub never supplies CAD or rendering evidence.
    useEffect(() => { onStatus({ state: 'ready', meshCount: 1 }); }, [onStatus]);
    return <div aria-label="Unit-test renderer contract stub" />;
  } };
});

it('reopening the already loaded source never resets readiness or submits another workspace mutation', async () => {
  vi.mocked(api.health).mockResolvedValue({ status: 'ok', version: '0.1.0', cadProfile: 'user_provided_local', providerConfigured: false });
  vi.mocked(api.catalog).mockResolvedValue(catalogFixture);
  vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture);
  vi.mocked(api.workspace).mockResolvedValue({ ...workspaceFixture, activeComponentId: componentFixture.id });
  render(<WorkspaceShell />);
  await screen.findByText('LOCAL / CONNECTED');
  expect(screen.queryByLabelText('Unit-test renderer contract stub')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Components' }));
  await screen.findByLabelText('Unit-test renderer contract stub');
  await waitFor(() => expect(screen.getByTestId('scene-status')).toHaveAttribute('data-state', 'ready'));
  fireEvent.click(screen.getByRole('button', { name: 'Close Components' }));
  fireEvent.click(screen.getByRole('button', { name: 'Components' }));
  fireEvent.click(screen.getByRole('button', { name: /Tachyon-authored non-VEX calibration fixture/ }));
  expect(screen.getByTestId('scene-status')).toHaveAttribute('data-state', 'ready');
  expect(api.patchWorkspace).not.toHaveBeenCalled();
});
