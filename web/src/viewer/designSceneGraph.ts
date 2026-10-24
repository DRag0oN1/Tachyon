import { Box3, Group, Matrix4, Object3D } from 'three';
import type { ComponentDefinition } from '../api/contracts';
import { disposeScene, loadComponent } from './loadComponent';

export interface DesignSceneSession {
  designId: string; revisionId: string | null;
  accepted: unknown; candidate: unknown;
  bindings: unknown; candidateBindings: unknown;
  components: ComponentDefinition[];
  worldTransforms: Record<string, number[]>;
  candidateWorldTransforms: Record<string, number[]> | null;
}
export interface DesignInstance { id: string; componentId: string; subsystemId: string }
export interface DesignSceneGraph { scene: Group; instances: Map<string, Group>; meshCount: number }
const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
export function designInstances(session: DesignSceneSession): DesignInstance[] {
  const revision = session.candidate ?? session.accepted;
  if (!object(revision) || !object(revision.assembly) || !Array.isArray(revision.assembly.instances)) throw new Error('The assembly revision has no inspectable instances.');
  const ids = new Set<string>();
  return revision.assembly.instances.map(node => {
    if (!object(node) || typeof node.id !== 'string' || ids.has(node.id) || typeof node.componentId !== 'string' || typeof node.subsystemId !== 'string') throw new Error('Invalid assembly instance identity.');
    ids.add(node.id);
    return { id: node.id, componentId: node.componentId, subsystemId: node.subsystemId };
  });
}
export function designRevisionId(session: DesignSceneSession): string {
  const revision = session.candidate ?? session.accepted;
  if (!object(revision) || typeof revision.id !== 'string') throw new Error('The assembly has no revision identity.');
  return revision.id;
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
  if (!transforms || Object.keys(transforms).length !== graph.instances.size) throw new Error('The assembly pose is incomplete.');
  for (const [id, group] of graph.instances) {
    const values = transforms[id];
    if (!Array.isArray(values) || values.length !== 16 || values.some(v => !Number.isFinite(v))) throw new Error('An assembly transform is invalid.');
    const matrix = new Matrix4().fromArray(values);
    const axes = [0, 1, 2].map(c => [values[4*c], values[4*c+1], values[4*c+2]]);
    const rigid = axes.every((a, i) => axes.every((b, j) => Math.abs(a.reduce((sum, v, k) => sum+v*b[k], 0)-(i===j ? 1 : 0)) < 1e-7));
    if (!rigid || Math.abs(matrix.determinant()-1) > 1e-7 || [3,7,11].some(i => Math.abs(values[i])>1e-9) || Math.abs(values[15]-1)>1e-9) throw new Error('Assembly placement must be rigid and preserve scale.');
    // API matrices are already world transforms. Flat placement groups avoid
    // applying the source's assembly parent transform twice.
    group.matrixAutoUpdate = false;
    group.matrix.copy(matrix);
  }
  graph.scene.updateMatrixWorld(true);
}
export async function loadDesignScene(session: DesignSceneSession, signal: AbortSignal): Promise<DesignSceneGraph> {
  const instances = designInstances(session);
  const definitions = new Map(session.components.map(c => [c.id, c]));
  const templates = new Map<string, Awaited<ReturnType<typeof loadComponent>>>();
  const scene = new Group();
  try {
    for (const key of new Set(instances.map(node => node.componentId))) {
      const component = definitions.get(key);
      if (!component || component.referenceOnly) throw new Error('A design component is missing or restricted to reference inspection.');
      templates.set(key, await loadComponent(component, signal));
      signal.throwIfAborted();
    }
    const groups = new Map<string, Group>();
    let meshCount = 0;
    for (const node of instances) {
      const template = templates.get(node.componentId)!;
      const placed = new Group(); placed.name = node.id;
      placed.userData.designInstanceId = node.id;
      placed.userData.subsystemId = node.subsystemId;
      placed.add(template.scene.clone(true));
      scene.add(placed); groups.set(node.id, placed); meshCount += template.meshCount;
    }
    const graph = { scene, instances: groups, meshCount };
    applyDesignPose(graph, session);
    return graph;
  } catch (error) {
    // Each component template owns its resources. Clones only share them.
    for (const template of templates.values()) disposeScene(template.scene);
    throw error;
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
