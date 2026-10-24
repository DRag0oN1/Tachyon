import { Box3, Color, InstancedMesh, Mesh, PerspectiveCamera, SkinnedMesh, Vector3, type Material, type Object3D } from 'three';
import type { ComponentDefinition, Selection } from '../api/contracts';

export function selectionFromObject(scene: Object3D, component: ComponentDefinition, object: Object3D): Selection | null {
  let native: Object3D | null = null;
  let current: Object3D | null = object;
  while (current) {
    if (!native && typeof current.userData.tachyonNativeNodeId === 'string') native = current;
    if (current === scene) return {
      componentId: component.id, catalogMeshSha256: component.meshSha256,
      ...(native ? { nativeNodeId: native.userData.tachyonNativeNodeId, meshName: native.userData.tachyonNativeNodeName } : {}),
    };
    current = current.parent;
  }
  return null;
}

function nativeNodeTarget(scene: Object3D, id: string): Object3D | null {
  let target: Object3D | null = null;
  scene.traverse(object => { if (object.userData.tachyonNativeNodeId === id) target = object; });
  return target;
}
export function selectionTarget(scene: Object3D, component: ComponentDefinition, selection: Selection | null): Object3D | null {
  if (!selection || selection.componentId !== component.id || selection.catalogMeshSha256 !== component.meshSha256) return null;
  return selection.nativeNodeId === undefined ? scene : nativeNodeTarget(scene, selection.nativeNodeId);
}

const highlights = new WeakMap<Object3D, () => void>();
export function clearSelectionHighlight(scene: Object3D): void { highlights.get(scene)?.(); }

// Materials alone are borrowed for display. Restore the exact original material
// references (including arrays), and dispose only the clones, never their textures.
export function highlightSelection(scene: Object3D, target: Object3D | null, color: string): () => void {
  clearSelectionHighlight(scene);
  if (!target) return () => {};
  const originals = new Map<Mesh, Mesh['material']>();
  const clones = new Map<Material, Material>();
  const accent = new Color(color);
  const clone = (material: Material): Material => {
    const existing = clones.get(material);
    if (existing) return existing;
    const highlighted = material.clone();
    if ('color' in highlighted && highlighted.color instanceof Color) highlighted.color.lerp(accent, 0.45);
    if ('emissive' in highlighted && highlighted.emissive instanceof Color) {
      highlighted.emissive.lerp(accent, 0.65);
      if ('emissiveIntensity' in highlighted && typeof highlighted.emissiveIntensity === 'number') highlighted.emissiveIntensity = Math.max(highlighted.emissiveIntensity, 0.45);
    }
    clones.set(material, highlighted);
    return highlighted;
  };
  target.traverse(object => {
    if (!(object instanceof Mesh)) return;
    originals.set(object, object.material);
    object.material = Array.isArray(object.material) ? object.material.map(clone) : clone(object.material);
  });
  let restored = false;
  const restore = () => {
    if (restored) return;
    restored = true;
    originals.forEach((material, mesh) => { mesh.material = material; });
    clones.forEach(material => material.dispose());
    if (highlights.get(scene) === restore) highlights.delete(scene);
  };
  highlights.set(scene, restore);
  return restore;
}

export interface Inspection { hiddenNodeIds: string[]; isolatedNodeId: string | null }
export function applyInspection(scene: Object3D, inspection?: Inspection): () => void {
  if (!inspection) return () => {};
  const hidden = new Set(inspection.hiddenNodeIds);
  const isolated = inspection.isolatedNodeId === null ? null : nativeNodeTarget(scene, inspection.isolatedNodeId);
  const path = new Set<Object3D>();
  let ancestor: Object3D | null = isolated;
  while (ancestor) { path.add(ancestor); ancestor = ancestor.parent; }
  const original = new Map<Object3D, { visible: boolean; layers: number }>();
  const visit = (object: Object3D, inside: boolean) => {
    original.set(object, { visible: object.visible, layers: object.layers.mask });
    const inSubtree = inside || object === isolated;
    object.visible = object.visible && !hidden.has(object.userData.tachyonNativeNodeId) && (!isolated || inSubtree || path.has(object));
    // A native mesh can itself parent other parts. Keep the ancestor path
    // traversable without drawing or picking that ancestor's own geometry.
    if (isolated && !inSubtree && object instanceof Mesh) object.layers.mask = 0;
    object.children.forEach(child => visit(child, inSubtree));
  };
  visit(scene, false);
  return () => original.forEach((state, object) => { object.visible = state.visible; object.layers.mask = state.layers; });
}

export function subtreeBounds(target: Object3D): Box3 | null {
  let ancestor: Object3D | null = target;
  while (ancestor) { if (!ancestor.visible) return null; ancestor = ancestor.parent; }
  target.updateWorldMatrix(true, true);
  const bounds = new Box3();
  target.traverseVisible(object => {
    if (!(object instanceof Mesh) || object.layers.mask === 0) return;
    if (object instanceof InstancedMesh || object instanceof SkinnedMesh) {
      object.computeBoundingBox();
      if (object.boundingBox) bounds.union(object.boundingBox.clone().applyMatrix4(object.matrixWorld));
    } else {
      if (!object.geometry.boundingBox) object.geometry.computeBoundingBox();
      if (object.geometry.boundingBox) bounds.union(object.geometry.boundingBox.clone().applyMatrix4(object.matrixWorld));
    }
  });
  return bounds.isEmpty() || [...bounds.min.toArray(), ...bounds.max.toArray()].some(n => !Number.isFinite(n)) ? null : bounds;
}

export interface FrameRequest { model: object; resetKey: number; focusKey: number; upAxis?: 'X' | 'Y' | 'Z' }
export function framingAction(previous: FrameRequest | null, next: FrameRequest): 'reset' | 'focus' | null {
  if (!previous || previous.model !== next.model || previous.resetKey !== next.resetKey || previous.upAxis !== next.upAxis) return 'reset';
  return previous.focusKey !== next.focusKey ? 'focus' : null;
}

export function frameCamera(camera: PerspectiveCamera, bounds: Box3, viewport: { width: number; height: number }, direction: Vector3, sceneBounds = bounds) {
  const radius = Math.max(bounds.getSize(new Vector3()).length() / 2, 0.00001);
  const halfFov = camera.getEffectiveFOV() * Math.PI / 360;
  const aspect = Math.max(viewport.width, 1) / Math.max(viewport.height, 1);
  const fit = Math.max(radius / Math.sin(halfFov), radius / Math.sin(Math.atan(Math.tan(halfFov) * aspect))) * 1.3;
  const center = bounds.getCenter(new Vector3());
  const heading = direction.lengthSq() > 0 ? direction.clone().normalize() : new Vector3(1, 0.65, 1).normalize();
  camera.near = Math.max(radius / 1000, 0.000001);
  camera.position.copy(center).addScaledVector(heading, fit);
  camera.far = Math.max(fit * 100, camera.position.distanceTo(sceneBounds.getCenter(new Vector3())) + sceneBounds.getSize(new Vector3()).length(), 10);
  camera.lookAt(center); camera.updateProjectionMatrix();
  return { center, minDistance: Math.max(radius * 0.15, 0.00001), maxDistance: Math.max(fit * 15, sceneBounds.getSize(new Vector3()).length() * 2, 1) };
}
