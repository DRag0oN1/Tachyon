import { webcrypto } from 'node:crypto';
import { expect, it, vi } from 'vitest';
import { sha256Hex } from './sha256';

it('verifies the SHA-256 standard abc vector with Web Crypto and with subtle unavailable', async () => {
  const bytes = new TextEncoder().encode('abc').buffer;
  const expected = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad';
  vi.stubGlobal('crypto', webcrypto);
  expect(await sha256Hex(bytes)).toBe(expected);
  vi.stubGlobal('crypto', { subtle: undefined });
  expect(await sha256Hex(bytes)).toBe(expected);
});
