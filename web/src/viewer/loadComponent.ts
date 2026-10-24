import { Box3, LoadingManager, Mesh, type Group, type Material, type Object3D, type Texture } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { api } from '../api/client';
import type { ComponentDefinition } from '../api/contracts';
import { clearSelectionHighlight } from './inspection';
import { batchSourcePrimitives } from './batchSourcePrimitives';

export interface LoadedComponent { scene: Group; meshCount: number; bounds: Box3 }
export function actualSourceBounds(scene: Group): Box3 { return new Box3().setFromObject(scene, true); }

export function annotateNativeNodes(scene: Group, component: ComponentDefinition, associations: ReadonlyMap<Object3D | Material | Texture, { nodes?: number }>, nodes: readonly { name?: string }[]): void {
  const names = new Map(component.nativeHierarchy?.map(node => [node.id, node.name]));
  scene.traverse(object => {
    object.userData.tachyonComponentId = component.id;
    object.userData.tachyonMeshSha256 = component.meshSha256;
    const index = associations.get(object)?.nodes;
    // Face primitives often have a mesh association but no native node. Picking
    // must climb to their associated parent, not invent a primitive identity.
    delete object.userData.tachyonNativeNodeId;
    delete object.userData.tachyonNativeNodeName;
    if (index !== undefined) {
      const id = `node-${index}`;
      object.userData.tachyonNativeNodeId = id;
      // GLTFLoader sanitizes/deduplicates Object3D.name. Keep the source name.
      object.userData.tachyonNativeNodeName = nodes[index]?.name ?? names.get(id) ?? `Body ${index}`;
    }
  });
}

// GLBs must be self-contained. Never let a loader bypass authenticated fetching
// through an external buffer, image, decoder, or network URL.
export async function validateGlb(blob: Blob): Promise<void> {
  const bytes = await blob.arrayBuffer();
  const view = new DataView(bytes);
  if (bytes.byteLength < 20 || view.getUint32(0, true) !== 0x46546c67 ||
    view.getUint32(4, true) !== 2 || view.getUint32(8, true) !== bytes.byteLength ||
    view.getUint32(16, true) !== 0x4e4f534a) throw new Error('This asset is not a valid binary glTF 2 component.');
  const length = view.getUint32(12, true);
  if (20 + length > bytes.byteLength) throw new Error('The GLB JSON chunk is incomplete.');
  const document = JSON.parse(new TextDecoder().decode(new Uint8Array(bytes, 20, length)));
  const resources = [...(document.buffers ?? []), ...(document.images ?? [])] as { uri?: string }[];
  if (resources.some(r => r.uri !== undefined && !r.uri.startsWith('data:'))) throw new Error('The component has external resources. Prepare a self-contained local GLB.');
  if (document.extensionsRequired?.some((extension: string) => /draco|basisu|meshopt/i.test(extension))) throw new Error('This component requires an unavailable mesh decoder. Prepare an uncompressed GLB.');
}
export function disposeScene(scene: Group): void {
  clearSelectionHighlight(scene);
  const geometries = new Set<Mesh['geometry']>();
  const materials = new Set<Material>();
  scene.traverse(object => {
    if (object instanceof Mesh) {
      geometries.add(object.geometry);
      (Array.isArray(object.material) ? object.material : [object.material]).forEach(m => materials.add(m));
    }
  });
  geometries.forEach(g => g.dispose());
  materials.forEach(m => {
    for (const value of Object.values(m)) if (value && typeof value === 'object' && value.isTexture) value.dispose();
    m.dispose();
  });
}
export async function loadComponent(component: ComponentDefinition, signal: AbortSignal): Promise<LoadedComponent> {
  const blob = await api.asset(component, signal);
  await validateGlb(blob);
  signal.throwIfAborted();
  const url = URL.createObjectURL(blob);
  let scene: Group | undefined;
  try {
    const manager = new LoadingManager();
    manager.setURLModifier(resource => {
      if (resource === url || resource.startsWith('data:') || resource.startsWith('blob:')) return resource;
      throw new Error('External component resources are unavailable.');
    });
    const gltf = await new GLTFLoader(manager).loadAsync(url);
    scene = gltf.scene;
    signal.throwIfAborted();
    let meshCount = 0;
    annotateNativeNodes(scene, component, gltf.parser.associations, gltf.parser.json.nodes ?? []);
    batchSourcePrimitives(scene);
    scene.traverse(object => { if (object instanceof Mesh) meshCount++; });
    if (!meshCount) throw new Error('The imported GLB contains no renderable source meshes.');
    // Rotated curved/sparse parts have conservative transformed local AABBs.
    // Check actual world vertices, matching the native conversion receipt.
    const bounds = actualSourceBounds(scene);
    const values = [...bounds.min.toArray(), ...bounds.max.toArray()];
    const declared = [...component.boundsM.min, ...component.boundsM.max];
    if (bounds.isEmpty() || values.some((n, i) => !Number.isFinite(n) || Math.abs(n - declared[i]) > Math.max(0.0002, Math.abs(declared[i]) * 0.01))) throw new Error('Rendered mesh bounds do not match the catalog in metres. Refresh or re-prepare this component.');
    return { scene, meshCount, bounds };
  } catch (error) {
    if (scene) disposeScene(scene);
    throw error;
  } finally { URL.revokeObjectURL(url); }
}
