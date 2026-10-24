import { Box3, BoxGeometry, Group, InstancedMesh, Matrix4, Mesh, MeshBasicMaterial, MeshStandardMaterial, PerspectiveCamera, Texture, Vector3, type Object3D } from 'three';
import { expect, it, vi } from 'vitest';
import { componentFixture } from '../test/contracts';
import { annotateNativeNodes, disposeScene } from './loadComponent';
import { applyInspection, frameCamera, framingAction, highlightSelection, selectionFromObject, selectionTarget, subtreeBounds } from './inspection';

// Synthetic Three geometry exercises display math and lifetime contracts only.
function assembly() {
  const scene = new Group(), source = new Group(), part = new Group();
  const material = new MeshStandardMaterial({ color: '#b42a18', metalness: 0.6, roughness: 0.2, opacity: 0.8, transparent: true, map: new Texture() });
  const face: Mesh = new Mesh(new BoxGeometry(0.02, 0.04, 0.06), material);
  const sibling = new Mesh(face.geometry, material);
  scene.position.set(0.1, 0.2, -0.3); source.scale.setScalar(0.001);
  part.position.set(50, 25, -10); sibling.position.set(-120, 0, 0);
  scene.add(source); source.add(part, sibling); part.add(face);
  annotateNativeNodes(scene, componentFixture, new Map<Object3D, { nodes: number }>([[source, { nodes: 0 }], [part, { nodes: 1 }], [sibling, { nodes: 2 }]]), [{ name: 'Source group' }, { name: 'Source part [1]' }, { name: 'Other part' }]);
  return { scene, source, part, face, sibling, material };
}

it('resolves exact subtree identity and rejects wrong assets, foreign objects, and unknown nodes', () => {
  const { scene, source, part, face } = assembly();
  const selected = selectionFromObject(scene, componentFixture, face)!;
  expect(selectionTarget(scene, componentFixture, selected)).toBe(part);
  expect(selectionTarget(scene, componentFixture, { ...selected, nativeNodeId: 'node-0' })).toBe(source);
  expect(selectionTarget(scene, componentFixture, { ...selected, nativeNodeId: undefined })).toBe(scene);
  expect(selectionTarget(scene, componentFixture, { ...selected, catalogMeshSha256: 'c'.repeat(64) })).toBeNull();
  expect(selectionTarget(scene, componentFixture, { ...selected, componentId: 'another-part' })).toBeNull();
  expect(selectionTarget(scene, componentFixture, { ...selected, nativeNodeId: 'node-missing' })).toBeNull();
  expect(selectionTarget(scene, componentFixture, null)).toBeNull();
  expect(selectionFromObject(scene, componentFixture, new Group())).toBeNull();
  disposeScene(scene);
});

it('highlights the actual subtree while preserving shared originals, geometry, transforms, and textures on clear', () => {
  const { scene, source, part, face, sibling, material } = assembly();
  const additional = new MeshBasicMaterial({ color: '#00dd00', vertexColors: true });
  const originalArray = [material, additional, material];
  face.material = originalArray;
  const before = material.toJSON(), basicBefore = additional.toJSON();
  const geometry = face.geometry, position = part.position.clone(), scale = source.scale.clone();
  const textureDispose = vi.spyOn(material.map!, 'dispose');
  const materialDispose = vi.spyOn(material, 'dispose');
  const restore = highlightSelection(scene, part, '#2069b5');
  const highlighted = face.material as unknown as typeof originalArray;
  expect(highlighted).not.toBe(originalArray);
  expect(highlighted[0]).not.toBe(material); expect(highlighted[0]).toBe(highlighted[2]);
  expect((highlighted[0] as MeshStandardMaterial).color.equals(material.color)).toBe(false);
  expect((highlighted[0] as MeshStandardMaterial).map).toBe(material.map);
  expect((highlighted[0] as MeshStandardMaterial).metalness).toBe(material.metalness);
  expect((highlighted[0] as MeshStandardMaterial).opacity).toBe(material.opacity);
  expect(sibling.material).toBe(material);
  const disposals = highlighted.slice(0, 2).map(clone => vi.spyOn(clone, 'dispose'));
  restore(); restore();
  expect(face.material).toBe(originalArray);
  expect(face.geometry).toBe(geometry);
  expect(part.position.equals(position)).toBe(true); expect(source.scale.equals(scale)).toBe(true);
  expect(material.toJSON()).toEqual(before); expect(additional.toJSON()).toEqual(basicBefore);
  disposals.forEach(dispose => expect(dispose).toHaveBeenCalledTimes(1));
  expect(textureDispose).not.toHaveBeenCalled(); expect(materialDispose).not.toHaveBeenCalled();
  disposeScene(scene);
});

it('replaces highlights without accumulating clones or allowing old cleanup to clear a newer highlight', () => {
  const { scene, part, face, sibling, material } = assembly();
  const firstCleanup = highlightSelection(scene, part, '#2069b5');
  const firstDispose = vi.spyOn(face.material as MeshStandardMaterial, 'dispose');
  const secondCleanup = highlightSelection(scene, sibling, '#6ec8fa');
  const second = sibling.material;
  expect(firstDispose).toHaveBeenCalledTimes(1); expect(face.material).toBe(material);
  firstCleanup(); expect(sibling.material).toBe(second);
  secondCleanup(); expect(sibling.material).toBe(material);
  highlightSelection(scene, part, '#2069b5');
  highlightSelection(scene, null, '#2069b5'); expect(face.material).toBe(material);
  disposeScene(scene);
});

it('computes selected world bounds through native parent transforms without including siblings', () => {
  const { scene, source, part, face, sibling } = assembly();
  source.rotation.z = Math.PI / 4;
  const bounds = subtreeBounds(part)!;
  const expected = new Box3().setFromObject(face);
  expect(bounds.min.distanceTo(expected.min)).toBeLessThan(1e-10);
  expect(bounds.max.distanceTo(expected.max)).toBeLessThan(1e-10);
  expect(bounds.getCenter(new Vector3()).distanceTo(part.getWorldPosition(new Vector3()))).toBeLessThan(1e-10);
  expect(bounds.containsPoint(sibling.getWorldPosition(new Vector3()))).toBe(false);
  expect(subtreeBounds(new Group())).toBeNull();
  source.visible = false; expect(subtreeBounds(part)).toBeNull();
  disposeScene(scene);
});

it('focuses a subtree more closely than reset in desktop and phone aspect ratios, preserving the chosen heading', () => {
  const { scene, part } = assembly();
  const whole = subtreeBounds(scene)!, selected = subtreeBounds(part)!;
  const heading = new Vector3(-1, 0.4, 0.8).normalize();
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const camera = new PerspectiveCamera(40, viewport.width / viewport.height);
    const focus = frameCamera(camera, selected, viewport, heading, whole);
    const focusedDistance = camera.position.distanceTo(focus.center);
    expect(focus.center.distanceTo(selected.getCenter(new Vector3()))).toBeLessThan(1e-10);
    expect(camera.position.clone().sub(focus.center).normalize().distanceTo(heading)).toBeLessThan(1e-8);
    for (const x of [selected.min.x, selected.max.x]) for (const y of [selected.min.y, selected.max.y]) for (const z of [selected.min.z, selected.max.z]) {
      camera.updateMatrixWorld();
      const projected = new Vector3(x, y, z).project(camera);
      expect(Math.abs(projected.x)).toBeLessThan(1); expect(Math.abs(projected.y)).toBeLessThan(1);
      expect(projected.z).toBeGreaterThan(-1); expect(projected.z).toBeLessThan(1);
    }
    const reset = frameCamera(camera, whole, viewport, new Vector3(1, 0.65, 1));
    expect(camera.position.distanceTo(reset.center)).toBeGreaterThan(focusedDistance);
  }
  disposeScene(scene);
});

it('only requests camera movement for a new model or an explicit focus/reset action', () => {
  const model = new Group();
  const previous = { model, resetKey: 3, focusKey: 7 };
  expect(framingAction(null, previous)).toBe('reset');
  // Selection, theme, panel and viewport changes keep these keys/model intact.
  expect(framingAction(previous, { ...previous })).toBeNull();
  expect(framingAction(previous, { ...previous, focusKey: 8 })).toBe('focus');
  expect(framingAction(previous, { ...previous, resetKey: 4 })).toBe('reset');
  expect(framingAction(previous, { ...previous, model: new Group() })).toBe('reset');
});

it('hides and isolates native subtrees as reversible inspection state, respecting preexisting visibility', () => {
  const { scene, source, part, face, sibling } = assembly();
  scene.updateWorldMatrix(true, true);
  const transform = source.matrix.clone();
  const restore = applyInspection(scene, { hiddenNodeIds: [], isolatedNodeId: 'node-1' });
  expect(part.visible).toBe(true); expect(source.visible).toBe(true); expect(sibling.visible).toBe(false);
  expect(subtreeBounds(scene)!.equals(subtreeBounds(part)!)).toBe(true);
  restore(); expect(sibling.visible).toBe(true);
  const unhide = applyInspection(scene, { hiddenNodeIds: ['node-1'], isolatedNodeId: null });
  expect(part.visible).toBe(false); expect(subtreeBounds(face)).toBeNull();
  unhide(); expect(part.visible).toBe(true);
  sibling.visible = false;
  const showAll = applyInspection(scene, { hiddenNodeIds: [], isolatedNodeId: null });
  expect(sibling.visible).toBe(false); showAll();
  expect(source.matrix.equals(transform)).toBe(true);
  disposeScene(scene);
});

it('isolates a descendant of a mesh without drawing that ancestor mesh and includes instance bounds', () => {
  const scene = new Group();
  const parent = new Mesh(new BoxGeometry(1, 1, 1), new MeshStandardMaterial());
  const child = new InstancedMesh(new BoxGeometry(0.01, 0.02, 0.03), parent.material, 2);
  child.setMatrixAt(1, new Matrix4().makeTranslation(0.1, 0, 0));
  child.userData.tachyonNativeNodeId = 'node-child'; scene.add(parent); parent.add(child);
  const originalMask = parent.layers.mask;
  const restore = applyInspection(scene, { hiddenNodeIds: [], isolatedNodeId: 'node-child' });
  expect(parent.visible).toBe(true); expect(parent.layers.mask).toBe(0);
  expect(subtreeBounds(scene)!.equals(subtreeBounds(child)!)).toBe(true);
  expect(subtreeBounds(child)!.getSize(new Vector3()).x).toBeCloseTo(0.11);
  restore(); expect(parent.layers.mask).toBe(originalMask);
  disposeScene(scene);
});
