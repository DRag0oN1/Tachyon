import { parseCapabilities, parseCatalog, parseHealth, parseWorkspace, type ComponentDefinition, type WorkspacePatch } from './contracts';
import { sha256Hex } from './sha256';
import { parseSourceRegister } from './sources';
import { OVERRIDE_COMPETITION_ID, parseStrategySession, parseStrategyStatus } from './strategy';

export const SESSION_KEY = 'tachyon.owner-session';
let memorySession: string | null = null;

export function captureSession(): void {
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  if (!fragment.has('session')) return;
  memorySession = fragment.get('session') || null;
  fragment.delete('session');
  const rest = fragment.toString();
  window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search + (rest ? `#${rest}` : ''));
  try {
    if (memorySession) sessionStorage.setItem(SESSION_KEY, memorySession);
    else sessionStorage.removeItem(SESSION_KEY);
  } catch { /* The session remains in this tab's memory if storage is disabled. */ }
}
function session(): string | null {
  try { return memorySession ?? sessionStorage.getItem(SESSION_KEY); } catch { return memorySession; }
}
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = 'ApiError'; }
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The workspace could not be reached. Try again.';
}
async function request(path: string, init: RequestInit = {}, publicHealth = false): Promise<Response> {
  if (!path.startsWith('/api/') || path.includes('..') || path.includes('#') || path.includes('?')) throw new Error('Unsupported API resource.');
  const headers = new Headers(init.headers);
  if (!publicHealth) {
    const token = session();
    if (!token) throw new ApiError(401, 'Open the authorized launch URL from the running Tachyon server to connect this tab.');
    headers.set('X-Tachyon-Session', token);
  }
  let response: Response;
  try { response = await fetch(path, { ...init, headers, credentials: 'omit', cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer' }); }
  catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'Tachyon server is unavailable. Start the local server, then retry.');
  }
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) throw new ApiError(response.status, 'This session is missing, expired, or unauthorized. Open a new authorized launch URL from the running server.');
    if (response.status === 404) throw new ApiError(404, 'The requested component or resource is unavailable. Refresh the local catalog.');
    throw new ApiError(response.status, `The server could not complete this request (${response.status}). Retry when it is available.`);
  }
  return response;
}
async function json(path: string, init?: RequestInit, publicHealth = false): Promise<unknown> {
  const response = await request(path, init, publicHealth);
  try { return await response.json(); }
  catch { throw new Error('The server returned an unreadable response.'); }
}
export const api = {
  // Uses the same owner session, response checks and no-store policy as source inspection.
  get: (path: string, signal?: AbortSignal) => json(path, { signal }),
  post: (path: string, body: unknown, signal?: AbortSignal) => json(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal,
  }),
  strategyStatus: (signal?: AbortSignal) => json('/api/strategy/status', { signal }).then(parseStrategyStatus),
  generateStrategy: (signal?: AbortSignal) => json('/api/strategy/generate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ competition_id: OVERRIDE_COMPETITION_ID }), signal,
  }).then(parseStrategySession),
  health: (signal?: AbortSignal) => json('/api/health', { signal }, true).then(parseHealth),
  catalog: (signal?: AbortSignal) => json('/api/catalog', { signal }).then(parseCatalog),
  sources: (signal?: AbortSignal) => json('/api/sources', { signal }).then(parseSourceRegister),
  capabilities: (signal?: AbortSignal) => json('/api/capabilities', { signal }).then(parseCapabilities),
  workspace: (signal?: AbortSignal) => json('/api/workspace', { signal }).then(parseWorkspace),
  patchWorkspace: (patch: WorkspacePatch) => json('/api/workspace', {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch),
  }).then(parseWorkspace),
  async asset(component: ComponentDefinition, signal?: AbortSignal): Promise<Blob> {
    if (!/^[a-f0-9]{64}$/i.test(component.meshSha256) || component.meshUrl !== `/api/assets/${component.meshSha256}.glb`) throw new Error('The catalog mesh identity is invalid.');
    const response = await request(component.meshUrl, { signal });
    const bytes = await response.arrayBuffer();
    const actual = await sha256Hex(bytes);
    if (actual !== component.meshSha256.toLowerCase()) throw new Error('Mesh integrity check failed. Refresh the qualified local catalog.');
    return new Blob([bytes], { type: 'model/gltf-binary' });
  },
};
