import { Box3, Group, Matrix4, Mesh, Object3D, Texture, type Material } from 'three';
import type { ComponentDefinition } from '../api/contracts';
import { loadComponent } from './loadComponent';
import { clearSelectionHighlight } from './inspection';

export interface DesignSceneSession {
  designId: string; revisionId: string | null;
  accepted: unknown; candidate: unknown;
  bindings: unknown; candidateBindings: unknown;
  components: ComponentDefinition[];
  worldTransforms: Record<string, number[]>;
  candidateWorldTransforms: Record<string, number[]> | null;
}
export interface DesignInstance { id: string; componentId: string; subsystemId: string }
export interface DesignGeometryResolution {
  revisionId: string;
  requestedInstanceCount: number;
  resolvedInstanceCount: number;
  requestedComponentCount: number;
  resolvedComponentCount: number;
  loadedInstanceCount: number;
  loadedComponentCount: number;
  missingInstanceIds: string[];
  missingComponentIds: string[];
}
export interface DesignSceneGraph { scene: Group; instances: Map<string, Group>; meshCount: number; resolution?: DesignGeometryResolution }
export class DesignSceneLoadError extends Error {
  constructor(message: string, public readonly resolution: DesignGeometryResolution, options?: ErrorOptions) {
    super(message, options); this.name = 'DesignSceneLoadError';
  }
}
const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
export function designInstances(session: DesignSceneSession): DesignInstance[] {
  const revision = session.candidate ?? session.accepted;
  if (!object(revision) || !object(revision.assembly) || !Array.isArray(revision.assembly.instances)) throw new Error('The assembly revision has no inspectable instances.');
  const ids = new Set<string>();
  return revision.assembly.instances.map(node => {
    if (!object(node) || typeof node.id !== 'string' || !node.id || ids.has(node.id) || typeof node.componentId !== 'string' || !node.componentId || typeof node.subsystemId !== 'string' || !node.subsystemId) throw new Error('Invalid assembly instance identity.');
    ids.add(node.id);
    return { id: node.id, componentId: node.componentId, subsystemId: node.subsystemId };
  });
}
export function designRevisionId(session: DesignSceneSession): string {
  const revision = session.candidate ?? session.accepted;
  if (!object(revision) || typeof revision.id !== 'string') throw new Error('The assembly has no revision identity.');
  return revision.id;
}
function definitionsFor(session: DesignSceneSession): Map<string, ComponentDefinition> {
  const definitions = new Map<string, ComponentDefinition>();
  for (const component of session.components) {
    if (definitions.has(component.id)) throw new Error('Duplicate assembly component definition identity.');
    definitions.set(component.id, component);
  }
  return definitions;
}
function usable(component: ComponentDefinition | undefined): boolean {
  return !!component && !component.referenceOnly && component.rightsStatus === 'qualified_for_declared_use' && (
    (component.geometryClass === 'test_fixture' && component.originKind === 'tachyon_authored') ||
    (component.geometryClass === 'verified_imported_component' && ['manufacturer_cad', 'community_component_model'].includes(component.originKind)));
}
/** Catalog resolution is distinct from loaded/drawn geometry. No placement cap. */
export function designGeometryResolution(session: DesignSceneSession): DesignGeometryResolution {
  const instances = designInstances(session), definitions = definitionsFor(session);
  const requested = new Set(instances.map(node => node.componentId));
  const missingComponentIds = [...requested].filter(id => !usable(definitions.get(id)));
  const missing = new Set(missingComponentIds);
  const missingInstanceIds = instances.filter(node => missing.has(node.componentId)).map(node => node.id);
  return { revisionId: designRevisionId(session), requestedInstanceCount: instances.length,
    resolvedInstanceCount: instances.length - missingInstanceIds.length,
    requestedComponentCount: requested.size, resolvedComponentCount: requested.size - missing.size,
    loadedInstanceCount: 0, loadedComponentCount: 0, missingInstanceIds, missingComponentIds };
}
export function boundInstances(session: DesignSceneSession, actionId: string | null): string[] {
  const bindings = session.candidate ? session.candidateBindings : session.bindings;
  if (!actionId || !object(bindings) || !Array.isArray(bindings.actions)) return [];
  if (bindings.revisionId !== designRevisionId(session)) throw new Error('Strategy bindings do not match the displayed revision.');
  const action = bindings.actions.find(a => object(a) && a.actionId === actionId);
  return object(action) && Array.isArray(action.instanceIds) && action.instanceIds.every(x => typeof x === 'string') ? action.instanceIds as string[] : [];
}
export function applyDesignPose(graph: DesignSceneGraph, session: DesignSceneSession): void {
  const transforms = session.candidate ? session.candidateWorldTransforms : session.worldTransforms;
  const instances = designInstances(session);
  if (!transforms || Object.keys(transforms).length !== graph.instances.size || instances.length !== graph.instances.size ||
    instances.some(node => !graph.instances.has(node.id))) throw new Error('The assembly pose is incomplete.');
  if (instances.some(node => {
    const loaded = graph.instances.get(node.id)!.userData.componentId;
    return loaded !== undefined && loaded !== node.componentId;
  })) throw new Error('The assembly geometry does not match its requested component identities.');
  const matrices = new Map<string, Matrix4>();
  for (const id of graph.instances.keys()) {
    const values = transforms[id];
    if (!Array.isArray(values) || values.length !== 16 || values.some(v => !Number.isFinite(v))) throw new Error('An assembly transform is invalid.');
    const matrix = new Matrix4().fromArray(values);
    const axes = [0, 1, 2].map(c => [values[4*c], values[4*c+1], values[4*c+2]]);
    const rigid = axes.every((a, i) => axes.every((b, j) => Math.abs(a.reduce((sum, v, k) => sum+v*b[k], 0)-(i===j ? 1 : 0)) < 1e-7));
    if (!rigid || Math.abs(matrix.determinant()-1) > 1e-7 || [3,7,11].some(i => Math.abs(values[i])>1e-9) || Math.abs(values[15]-1)>1e-9) throw new Error('Assembly placement must be rigid and preserve scale.');
    matrices.set(id, matrix);
  }
  // Validate the entire pose before updating any live placement. Failed previews
  // retain the last accepted scene instead of leaving a partially applied pose.
  for (const [id, group] of graph.instances) {
    // API matrices are already world transforms. Flat placement groups avoid
    // applying the source's assembly parent transform twice.
    group.matrixAutoUpdate = false;
    group.matrix.copy(matrices.get(id)!);
  }
  graph.scene.updateMatrixWorld(true);
  if (graph.resolution) graph.resolution.revisionId = designRevisionId(session);
}
function releaseResources(scenes: Iterable<Group>): void {
  const geometries = new Set<Mesh['geometry']>(), materials = new Set<Material>(), textures = new Set<Texture>();
  for (const scene of scenes) {
    scene.traverse(object => {
      clearSelectionHighlight(object);
      if (object instanceof Mesh) {
        geometries.add(object.geometry);
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material);
      }
    });
  }
  for (const material of materials) for (const value of Object.values(material)) if (value instanceof Texture) textures.add(value);
  geometries.forEach(geometry => geometry.dispose()); textures.forEach(texture => texture.dispose()); materials.forEach(material => material.dispose());
}
const disposed = new WeakSet<Group>();
/** Dispose a loaded assembly once, including shared source resources/highlights. */
export function disposeDesignScene(graph: DesignSceneGraph): void {
  if (disposed.has(graph.scene)) return;
  disposed.add(graph.scene); releaseResources([graph.scene]);
}
export async function loadDesignScene(session: DesignSceneSession, signal: AbortSignal): Promise<DesignSceneGraph> {
  signal.throwIfAborted();
  const instances = designInstances(session);
  const definitions = definitionsFor(session);
  const resolution = designGeometryResolution(session);
  if (!instances.length) throw new DesignSceneLoadError('The assembly has no geometry placements.', resolution);
  if (resolution.missingInstanceIds.length) throw new DesignSceneLoadError(
    `${resolution.resolvedInstanceCount}/${resolution.requestedInstanceCount} placements resolve to usable geometry. Missing or unavailable: ${resolution.missingInstanceIds.join(', ')}.`, resolution);
  const templates = new Map<string, Awaited<ReturnType<typeof loadComponent>>>();
  const scene = new Group();
  let loadingComponent: string | null = null;
  try {
    for (const key of new Set(instances.map(node => node.componentId))) {
      loadingComponent = key;
      const template = await loadComponent(definitions.get(key)!, signal);
      templates.set(key, template);
      signal.throwIfAborted();
      let meshes = 0;
      template.scene.traverse(object => { if (object instanceof Mesh) meshes++; });
      if (!meshes) throw new Error('The component contains no renderable geometry.');
      template.meshCount = meshes;
      resolution.loadedComponentCount = templates.size;
    }
    loadingComponent = null;
    const groups = new Map<string, Group>();
    let meshCount = 0;
    for (const node of instances) {
      const template = templates.get(node.componentId)!;
      const placed = new Group(); placed.name = node.id;
      placed.userData.designInstanceId = node.id;
      placed.userData.componentId = node.componentId;
      placed.userData.subsystemId = node.subsystemId;
      placed.add(template.scene.clone(true));
      scene.add(placed); groups.set(node.id, placed); meshCount += template.meshCount;
    }
    const graph = { scene, instances: groups, meshCount, resolution };
    applyDesignPose(graph, session);
    resolution.loadedInstanceCount = groups.size;
    scene.userData.geometryResolution = resolution;
    return graph;
  } catch (error) {
    // Clones borrow GPU resources; release the union, once, on every failed load.
    releaseResources([scene, ...[...templates.values()].map(template => template.scene)]);
    if (signal.aborted) throw error;
    if (loadingComponent) {
      resolution.missingComponentIds = [loadingComponent];
      resolution.missingInstanceIds = instances.filter(node => node.componentId === loadingComponent).map(node => node.id);
      resolution.resolvedComponentCount--; resolution.resolvedInstanceCount -= resolution.missingInstanceIds.length;
    }
    const message = error instanceof Error ? error.message : 'Assembly geometry could not be loaded.';
    throw new DesignSceneLoadError(loadingComponent ? `${loadingComponent}: ${message} (${resolution.missingInstanceIds.length} placements unavailable).` : message, resolution, { cause: error });
  }
}
export function instanceAt(object: Object3D): string | null {
  let target: Object3D | null = object;
  while (target) {
    if (typeof target.userData.designInstanceId === 'string') return target.userData.designInstanceId;
    target = target.parent;
  }
  return null;
}
export function instanceBounds(graph: DesignSceneGraph, ids: readonly string[]): Box3 | null {
  const bounds = new Box3();
  for (const id of ids) {
    const target = graph.instances.get(id);
    if (target) bounds.union(new Box3().setFromObject(target, true));
  }
  return bounds.isEmpty() ? null : bounds;
}
