import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../api/client';
import type { SourceRegister } from '../api/sources';
import { parseSourceRegister } from '../api/sources';
import { SourceRegisterPanel } from './SourceRegisterPanel';

vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<object>(), api: { sources: vi.fn() } }));
const register: SourceRegister = { schemaVersion: 1, geometryIncluded: false, blockers: [], sources: [{
  sourceSha256: 'a'.repeat(64), name: 'V5 Clawbot', sku: '276-6009', sourceUrl: 'https://www.vexrobotics.com/v5-system-bundle.html', sourceState: 'present',
  permissions: { conversion: { status: 'unverified', code: 'RIGHTS_UNVERIFIED' }, loopback_display: { status: 'unverified', code: 'RIGHTS_UNVERIFIED' }, public_hosting: { status: 'unverified', code: 'RIGHTS_UNVERIFIED' } },
}] };
beforeEach(() => vi.clearAllMocks());
it('distinguishes discovered originals from prepared geometry without offering an import bypass', async () => {
  vi.mocked(api.sources).mockResolvedValue(register);
  render(<SourceRegisterPanel mode="simple" />);
  expect(await screen.findByRole('heading', { name: 'V5 Clawbot' })).toBeVisible();
  expect(screen.getAllByText('Unverified — blocked')).toHaveLength(2);
  expect(screen.getByText(/not an AI-generated design/)).toBeVisible();
  expect(screen.queryByText('Public hosting')).not.toBeInTheDocument();
  expect(screen.getAllByRole('button')).toHaveLength(1);
});
it('refreshes stale metadata and exposes operation scopes in Advanced mode', async () => {
  vi.mocked(api.sources).mockResolvedValueOnce(register).mockResolvedValueOnce({ ...register, sources: [{ ...register.sources[0], sourceState: 'changed' }] });
  render(<SourceRegisterPanel mode="advanced" />);
  expect(await screen.findByText('Public hosting')).toBeVisible();
  expect(screen.getByText(`SHA-256 · ${'a'.repeat(64)}`)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh sources' }));
  expect(await screen.findByText(/276-6009 · changed/)).toBeVisible();
  expect(api.sources).toHaveBeenCalledTimes(2);
});
it('reports a failed metadata request and allows a real retry', async () => {
  vi.mocked(api.sources).mockRejectedValueOnce(new Error('Session expired')).mockResolvedValueOnce({ ...register, sources: [] });
  render(<SourceRegisterPanel mode="simple" />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Session expired');
  fireEvent.click(screen.getByRole('button', { name: 'Refresh sources' }));
  expect(await screen.findByText(/No STEP originals have been recorded/)).toBeVisible();
});
it('rejects incompatible or geometry-bearing source status responses', () => {
  expect(parseSourceRegister(register)).toEqual(register);
  expect(() => parseSourceRegister({ ...register, geometryIncluded: true })).toThrow();
  expect(() => parseSourceRegister({ ...register, sources: [{ ...register.sources[0], sourceState: 'prepared' }] })).toThrow();
  expect(() => parseSourceRegister({ ...register, sources: [{ ...register.sources[0], permissions: { conversion: { status: 'approved' } } }] })).toThrow();
});
