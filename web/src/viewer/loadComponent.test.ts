import { Blob as NodeBlob } from 'node:buffer';
import { expect, it } from 'vitest';
import { validateGlb } from './loadComponent';

// Authored JSON envelope only: this is not VEX geometry or render evidence.
function envelope(document: object): Blob {
  const text = JSON.stringify(document);
  const body = new TextEncoder().encode(text + ' '.repeat((4 - text.length % 4) % 4));
  const bytes = new ArrayBuffer(20 + body.length);
  const view = new DataView(bytes);
  [0x46546c67, 2, bytes.byteLength, body.length, 0x4e4f534a].forEach((n, i) => view.setUint32(i * 4, n, true));
  new Uint8Array(bytes, 20).set(body);
  return new NodeBlob([bytes]) as unknown as Blob;
}
it('rejects external GLB dependencies so loaders cannot bypass the authenticated API', async () => {
  await expect(validateGlb(envelope({ buffers: [{ uri: 'https://example.com/private.bin' }] }))).rejects.toThrow('external resources');
  await expect(validateGlb(envelope({ images: [{ uri: '../texture.png' }] }))).rejects.toThrow('external resources');
  await expect(validateGlb(envelope({ buffers: [{ byteLength: 32 }] }))).resolves.toBeUndefined();
});
it('rejects broken GLB headers and unsupported external decoders', async () => {
  await expect(validateGlb(new NodeBlob(['not geometry']) as unknown as Blob)).rejects.toThrow('valid binary glTF');
  await expect(validateGlb(envelope({ extensionsRequired: ['KHR_draco_mesh_compression'] }))).rejects.toThrow('unavailable mesh decoder');
});
