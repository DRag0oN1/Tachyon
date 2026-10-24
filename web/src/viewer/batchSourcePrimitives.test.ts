import { expect, it } from 'vitest';
import { Box3, BoxGeometry, Group, Mesh, MeshStandardMaterial } from 'three';
import { batchSourcePrimitives } from './batchSourcePrimitives';
import { disposeScene } from './loadComponent';

it('batches exact source surfaces by native part/material while retaining vertices, normals and transforms', () => {
  const scene = new Group(), part = new Group();
  part.userData.tachyonNativeNodeId = 'node-1';
  part.position.set(.01, .02, .03); part.rotation.z = .4; scene.add(part);
  const material = new MeshStandardMaterial();
  const geometries = [new BoxGeometry(1, 2, 3), new BoxGeometry(2, 3, 4)];
  geometries.forEach(geometry => part.add(new Mesh(geometry, material)));
  const vertices = geometries.reduce((n, geometry) => n + geometry.getAttribute('position').count, 0);
  const expected = new Box3().setFromObject(scene, true);
  const pose = part.position.clone(), orientation = part.quaternion.clone();
  batchSourcePrimitives(scene);
  expect(part.children).toHaveLength(1);
  const mesh = part.children[0] as Mesh;
  expect(mesh.geometry.getAttribute('position').count).toBe(vertices);
  expect(mesh.geometry.getAttribute('normal').count).toBe(vertices);
  expect(mesh.material).toBe(material);
  expect(part.position.equals(pose)).toBe(true); expect(part.quaternion.equals(orientation)).toBe(true);
  expect(part.userData.tachyonNativeNodeId).toBe('node-1');
  expect(new Box3().setFromObject(scene, true).equals(expected)).toBe(true);
  disposeScene(scene);
});

it('keeps separate native identities, materials and locally transformed primitives', () => {
  const scene = new Group(), part = new Group();
  part.userData.tachyonNativeNodeId = 'node-1'; scene.add(part);
  const material = new MeshStandardMaterial(), other = new MeshStandardMaterial();
  const first = new Mesh(new BoxGeometry(), material), second = new Mesh(new BoxGeometry(), other);
  const native = new Mesh(new BoxGeometry(), material); native.userData.tachyonNativeNodeId = 'node-2';
  const translated = new Mesh(new BoxGeometry(), material); translated.position.x = .1;
  part.add(first, second, native, translated);
  batchSourcePrimitives(scene);
  expect(part.children).toEqual([first, second, native, translated]);
  disposeScene(scene);
});
