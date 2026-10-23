import { sha256 } from '@noble/hashes/sha2.js';

// Web Crypto is unavailable on an ordinary HTTP LAN origin on phones.
// Both branches verify identical bytes; no insecure-context bypass.
export async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  const digest = globalThis.crypto?.subtle
    ? new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes))
    : sha256(new Uint8Array(bytes));
  return Array.from(digest, byte => byte.toString(16).padStart(2, '0')).join('');
}
