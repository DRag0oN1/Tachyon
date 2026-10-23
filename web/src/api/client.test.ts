import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, captureSession, SESSION_KEY } from './client';
import { componentFixture, workspaceFixture } from '../test/contracts';
import { sha256Hex } from './sha256';

beforeEach(() => {
  history.replaceState(null, '', '/#session='); captureSession(); sessionStorage.clear();
});
afterEach(() => { vi.restoreAllMocks(); });
function launch() { history.replaceState(null, '', '/?workspace=local#session=unit-test-owner&view=focus'); captureSession(); }

describe('owner-session API boundary', () => {
  it('removes the token from the URL, retains other navigation, and keeps it in tab storage', () => {
    launch();
    expect(location.hash).toBe('#view=focus');
    expect(location.search).toBe('?workspace=local');
    expect(sessionStorage.getItem(SESSION_KEY)).toBe('unit-test-owner');
    expect(localStorage.getItem(SESSION_KEY)).toBeNull();
  });
  it('uses the owner header on protected reads and JSON patches, never the URL', async () => {
    launch();
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(workspaceFixture))));
    vi.stubGlobal('fetch', fetcher);
    await api.workspace();
    await api.patchWorkspace({ preferences: { theme: 'shift' } });
    expect(fetcher).toHaveBeenCalledTimes(2);
    for (const [url, init] of fetcher.mock.calls) {
      expect(url).toBe('/api/workspace');
      expect((init.headers as Headers).get('X-Tachyon-Session')).toBe('unit-test-owner');
      expect(init.redirect).toBe('error');
    }
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ preferences: { theme: 'shift' } });
  });
  it('allows redacted health without a session and refuses a protected request before fetch', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok', version: '0.1.0', cadProfile: 'user_provided_local', providerConfigured: false })));
    vi.stubGlobal('fetch', fetcher);
    await expect(api.health()).resolves.toMatchObject({ providerConfigured: false });
    await expect(api.workspace()).rejects.toThrow('authorized launch URL');
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][1].headers.has('X-Tachyon-Session')).toBe(false);
  });
  it('keeps authorization errors actionable without echoing server secrets', async () => {
    launch(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private error content', { status: 403 })));
    await expect(api.workspace()).rejects.toThrow('new authorized launch URL');
  });
  it('authenticates GLB bytes and rejects a hash mismatch', async () => {
    launch();
    const bytes = new TextEncoder().encode('Tachyon authored non-VEX converter test only').buffer;
    const digest = await sha256Hex(bytes);
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(bytes)));
    vi.stubGlobal('fetch', fetcher);
    const c = { ...componentFixture, meshSha256: digest, meshUrl: `/api/assets/${digest}.glb` };
    await expect(api.asset(c)).resolves.toBeInstanceOf(Blob);
    expect(fetcher.mock.calls[0][1].headers.get('X-Tachyon-Session')).toBe('unit-test-owner');
    await expect(api.asset(componentFixture)).rejects.toThrow('integrity check failed');
  });
  it('refuses non-content-addressed mesh URLs before sending any credential', async () => {
    launch(); const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
    await expect(api.asset({ ...componentFixture, meshUrl: 'https://example.com/component.glb' })).rejects.toThrow('mesh identity is invalid');
    expect(fetcher).not.toHaveBeenCalled();
  });
});
