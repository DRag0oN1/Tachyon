import { Blob as NodeBlob } from 'node:buffer';
import { expect, it, vi } from 'vitest';
import { Box3, BoxGeometry, BufferGeometry, Float32BufferAttribute, Group, Mesh, MeshStandardMaterial, type Object3D } from 'three';
import { componentFixture } from '../test/contracts';
import { actualSourceBounds, annotateNativeNodes, disposeScene, validateGlb } from './loadComponent';
import { highlightSelection, selectionFromObject } from './inspection';

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
it('checks world vertices rather than conservative rotated local boxes', () => {
  const scene = new Group();
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new Float32BufferAttribute([0, 0, 0, 1, 0, 0, 0, 1, 0], 3));
  const part = new Mesh(geometry, new MeshStandardMaterial());
  part.rotation.z = Math.PI / 4; scene.add(part);
  const approximate = new Box3().setFromObject(scene);
  const precise = actualSourceBounds(scene);
  expect(precise.max.y).toBeCloseTo(Math.SQRT1_2, 6);
  expect(approximate.max.y).toBeCloseTo(Math.SQRT2, 6);
  expect(precise.max.y).toBeLessThan(approximate.max.y);
  disposeScene(scene);
});
it('rejects external GLB dependencies so loaders cannot bypass the authenticated API', async () => {
  await expect(validateGlb(envelope({ buffers: [{ uri: 'https://example.com/private.bin' }] }))).rejects.toThrow('external resources');
  await expect(validateGlb(envelope({ images: [{ uri: '../texture.png' }] }))).rejects.toThrow('external resources');
  await expect(validateGlb(envelope({ buffers: [{ byteLength: 32 }] }))).resolves.toBeUndefined();
});
it('rejects broken GLB headers and unsupported external decoders', async () => {
  await expect(validateGlb(new NodeBlob(['not geometry']) as unknown as Blob)).rejects.toThrow('valid binary glTF');
  await expect(validateGlb(envelope({ extensionsRequired: ['KHR_draco_mesh_compression'] }))).rejects.toThrow('unavailable mesh decoder');
});

it('keeps raw source names and resolves unassociated face primitives to their nearest native parent', () => {
  // Authored Three objects test identity plumbing only, never authentic CAD.
  const scene = new Group();
  const root = new Group();
  const part = new Group();
  const face = new Mesh(new BoxGeometry(), new MeshStandardMaterial({ color: '#d02f12' }));
  root.name = 'Source_assembly'; part.name = 'Motor_housing_1'; face.name = 'primitive_7';
  part.userData.sourceExtra = 'preserved';
  face.userData.tachyonNativeNodeId = 'untrusted-extra';
  part.position.set(0.01, 0.02, 0.03);
  scene.add(root); root.add(part); part.add(face);
  const geometry = face.geometry, material = face.material, transform = part.position.clone();
  const associations = new Map<Object3D, { nodes?: number; meshes?: number }>([[root, { nodes: 0 }], [part, { nodes: 1 }], [face, { meshes: 0 }]]);
  annotateNativeNodes(scene, componentFixture, associations, [{ name: 'Source assembly' }, { name: 'Motor housing [left].1' }]);
  expect(selectionFromObject(scene, componentFixture, face)).toEqual({ componentId: componentFixture.id, catalogMeshSha256: componentFixture.meshSha256, nativeNodeId: 'node-1', meshName: 'Motor housing [left].1' });
  expect(face.userData.tachyonNativeNodeId).toBeUndefined();
  expect(part.name).toBe('Motor_housing_1');
  expect(part.userData.sourceExtra).toBe('preserved');
  expect(part.position.equals(transform)).toBe(true);
  expect(face.geometry).toBe(geometry); expect(face.material).toBe(material);
  disposeScene(scene);
});

it('keeps repeated source names stable with distinct node identities and catalog fallbacks', () => {
  const scene = new Group();
  const first = new Group(), second = new Group(), unnamed = new Group();
  first.name = 'Duplicated'; second.name = 'Duplicated_1'; scene.add(first, second, unnamed);
  annotateNativeNodes(scene, { ...componentFixture, nativeHierarchy: [{ id: 'node-2', name: 'Catalog source name', parentId: null, matrix: [], hasMesh: false }] }, new Map([[first, { nodes: 0 }], [second, { nodes: 1 }], [unnamed, { nodes: 2 }]]), [{ name: 'Repeated source part' }, { name: 'Repeated source part' }]);
  expect(selectionFromObject(scene, componentFixture, first)?.meshName).toBe('Repeated source part');
  expect(selectionFromObject(scene, componentFixture, second)).toMatchObject({ nativeNodeId: 'node-1', meshName: 'Repeated source part' });
  expect(selectionFromObject(scene, componentFixture, unnamed)?.meshName).toBe('Catalog source name');
});

it('restores highlighted originals before scene disposal so both material lifetimes end once', () => {
  const scene = new Group();
  const original = new MeshStandardMaterial();
  const geometry = new BoxGeometry();
  const mesh = new Mesh(geometry, original); scene.add(mesh);
  const originalDispose = vi.spyOn(original, 'dispose'), geometryDispose = vi.spyOn(geometry, 'dispose');
  const restore = highlightSelection(scene, mesh, '#2069b5');
  const cloneDispose = vi.spyOn(mesh.material, 'dispose');
  disposeScene(scene); restore();
  expect(mesh.material).toBe(original);
  expect(cloneDispose).toHaveBeenCalledTimes(1);
  expect(originalDispose).toHaveBeenCalledTimes(1);
  expect(geometryDispose).toHaveBeenCalledTimes(1);
});
