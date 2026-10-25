import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Box3, BoxGeometry, Group, Mesh, MeshBasicMaterial, Texture, Vector3 } from 'three';
import { applyDesignPose, boundInstances, designGeometryResolution, designInstances, designRevisionId, DesignSceneLoadError, disposeDesignScene, instanceAt, instanceBounds, loadDesignScene, type DesignSceneSession } from './designSceneGraph';
import { loadComponent } from './loadComponent';
import { highlightSelection } from './inspection';
import { componentFixture } from '../test/contracts';

vi.mock('./loadComponent', async importOriginal => ({ ...await importOriginal<typeof import('./loadComponent')>(), loadComponent: vi.fn() }));
beforeEach(() => { vi.mocked(loadComponent).mockReset(); });

// Numerical transform oracle only. These test boxes are never product CAD.
const matrix = (x: number,y: number,z: number) => [1,0,0,0,0,1,0,0,0,0,1,0,x,y,z,1];
function setup() {
  const scene = new Group();
  const support = new Group(), carrier = new Group();
  support.userData.designInstanceId='support'; carrier.userData.designInstanceId='carrier';
  support.add(new Mesh(new BoxGeometry(.02,.02,.02),new MeshBasicMaterial()));
  carrier.add(new Mesh(new BoxGeometry(.01,.01,.01),new MeshBasicMaterial()));
  scene.add(support,carrier);
  const instances = new Map([['support',support],['carrier',carrier]]);
  const nodes = [
    { id:'support',componentId:'source-support',subsystemId:'chassis' },
    { id:'carrier',componentId:'source-carrier',subsystemId:'scorer' },
  ];
  const session: DesignSceneSession = {
    designId:'test-design', revisionId:'accepted-1', accepted:{id:'accepted-1',assembly:{instances:nodes}},candidate:null,
    bindings:{revisionId:'accepted-1',actions:[{actionId:'place_alliance',instanceIds:['carrier']}]},candidateBindings:null,
    components:[],worldTransforms:{support:matrix(.1,0,0),carrier:matrix(.1,.2,0)},candidateWorldTransforms:{},
  };
  return { session,graph:{scene,instances,meshCount:2},support,carrier };
}

describe('actual assembly pose presentation',() => {
  it('uses world matrices once, preserving geometry size and stable identity',() => {
    const {session,graph,carrier}=setup();
    applyDesignPose(graph,session);
    expect(carrier.getWorldPosition(new Vector3()).toArray()).toEqual([.1,.2,0]);
    const size=instanceBounds(graph,['carrier'])!.getSize(new Vector3());
    expect(size.x).toBeCloseTo(.01); expect(size.y).toBeCloseTo(.01);
    expect(instanceAt(carrier.children[0])).toBe('carrier');
    expect(designInstances(session).map(i=>i.id)).toEqual(['support','carrier']);
  });
  it('presents preview, discard and undo from exact server revisions',() => {
    const {session,graph,carrier}=setup();
    const preview={...session,candidate:{id:'candidate-2',assembly:(session.accepted as {assembly:unknown}).assembly},
      candidateBindings:{revisionId:'candidate-2',actions:[{actionId:'place_alliance',instanceIds:['carrier']}]},
      candidateWorldTransforms:{support:matrix(.1,0,0),carrier:matrix(.1,.4,0)}};
    applyDesignPose(graph,preview);
    expect(carrier.getWorldPosition(new Vector3()).y).toBe(.4);
    expect(designRevisionId(preview)).toBe('candidate-2');
    expect(boundInstances(preview,'place_alliance')).toEqual(['carrier']);
    applyDesignPose(graph,session);
    expect(carrier.getWorldPosition(new Vector3()).y).toBe(.2);
    expect(boundInstances(session,'place_alliance')).toEqual(['carrier']);
  });
  it('refuses stale strategy links and missing, resized or nonfinite transforms',() => {
    const {session,graph}=setup();
    expect(()=>boundInstances({...session,bindings:{revisionId:'stale',actions:[]}},'place_alliance')).toThrow('displayed revision');
    expect(()=>applyDesignPose(graph,{...session,worldTransforms:{}})).toThrow('incomplete');
    const resized=matrix(0,0,0); resized[0]=2;
    expect(()=>applyDesignPose(graph,{...session,worldTransforms:{...session.worldTransforms,carrier:resized}})).toThrow('rigid');
    const invalid=matrix(0,0,0); invalid[12]=NaN;
    expect(()=>applyDesignPose(graph,{...session,worldTransforms:{...session.worldTransforms,carrier:invalid}})).toThrow('invalid');
  });
  it('validates the whole pose before changing any placement or accepting other instance identities', () => {
    const { session, graph, support } = setup();
    applyDesignPose(graph, session);
    const original = support.matrix.clone();
    const invalid = matrix(0, 0, 0); invalid[0] = 2;
    expect(() => applyDesignPose(graph, { ...session, worldTransforms: { support: matrix(9, 0, 0), carrier: invalid } })).toThrow('rigid');
    expect(support.matrix.equals(original)).toBe(true);
    const wrong = { ...session, accepted: { id: 'other', assembly: { instances: [{ id: 'different', componentId: 'x', subsystemId: 'scorer' }, { id: 'carrier', componentId: 'y', subsystemId: 'scorer' }] } } };
    expect(() => applyDesignPose(graph, wrong)).toThrow('incomplete');
    expect(support.matrix.equals(original)).toBe(true);
  });
});

// Original development-CAD metadata and numerical Three meshes only. These are
// not manufacturer geometry, a physical robot, or authentic-CAD acceptance.
function manyPlacements(count = 449, definitions = 26): DesignSceneSession {
  const components = Array.from({ length: definitions }, (_, index) => ({ ...componentFixture, id: `development-${index}` }));
  const roles = ['chassis', 'drive', 'scorer', 'pin_intake', 'pin_transfer', 'cup_cradle', 'stack_interface'];
  const nodes = Array.from({ length: count }, (_, index) => ({ id: `placement-${index}`, componentId: components[index % definitions].id, subsystemId: roles[index % roles.length] }));
  return { designId: 'development-assembly', revisionId: 'development-r1', accepted: { id: 'development-r1', assembly: { instances: nodes } }, candidate: null,
    bindings: null, candidateBindings: null, components,
    worldTransforms: Object.fromEntries(nodes.map((node, index) => [node.id, matrix(index * .003, index * .002, 0)])), candidateWorldTransforms: null };
}
function sourceTemplate() {
  const scene = new Group(), native = new Group();
  native.userData.tachyonNativeNodeId = 'node-1';
  native.userData.tachyonNativeNodeName = 'Original development part';
  const geometry = new BoxGeometry(.01, .02, .03), material = new MeshBasicMaterial();
  native.add(new Mesh(geometry, material), new Mesh(geometry, material)); scene.add(native);
  return { scene, meshCount: 2, bounds: new Box3().setFromObject(scene), geometry, material };
}
function firstMesh(group: Group): Mesh {
  let first: Mesh | undefined;
  group.traverse(node => { if (!first && node instanceof Mesh) first = node; });
  return first!;
}
describe('complete generated scene resolution', () => {
  it.each([449, 474])('loads all %i placements from 26 templates without truncation or per-placement resource copies', async count => {
    const session = manyPlacements(count);
    const templates = new Map<string, ReturnType<typeof sourceTemplate>>();
    vi.mocked(loadComponent).mockImplementation(async component => {
      const template = sourceTemplate(); templates.set(component.id, template); return template;
    });
    const graph = await loadDesignScene(session, new AbortController().signal);
    expect(loadComponent).toHaveBeenCalledTimes(26);
    expect(graph.instances.size).toBe(count); expect(graph.scene.children).toHaveLength(count);
    expect(new Set(designInstances(session).map(node => node.subsystemId)).size).toBe(7);
    expect(graph.meshCount).toBe(count * 2);
    expect(graph.resolution).toEqual({ revisionId: 'development-r1', requestedInstanceCount: count, resolvedInstanceCount: count,
      requestedComponentCount: 26, resolvedComponentCount: 26, loadedInstanceCount: count, loadedComponentCount: 26,
      missingInstanceIds: [], missingComponentIds: [] });
    const first = firstMesh(graph.instances.get('placement-0')!), repeated = firstMesh(graph.instances.get('placement-26')!);
    expect(first.geometry).toBe(repeated.geometry); expect(first.material).toBe(repeated.material);
    expect(first.geometry).toBe(templates.get('development-0')!.geometry);
    expect(instanceAt(first)).toBe('placement-0'); expect(instanceAt(repeated)).toBe('placement-26');
    expect(repeated.parent!.userData.tachyonNativeNodeName).toBe('Original development part');
    expect(graph.instances.get(`placement-${count - 1}`)!.getWorldPosition(new Vector3()).toArray()).toEqual([(count - 1) * .003, (count - 1) * .002, 0]);
    const changed = structuredClone(session.accepted) as { id: string; assembly: { instances: { componentId: string }[] } };
    changed.assembly.instances[0].componentId = 'development-1';
    expect(() => applyDesignPose(graph, { ...session, accepted: changed })).toThrow('component identities');
    disposeDesignScene(graph);
  });
  it('reports all missing placement identities before fetching any source assets', async () => {
    const session = manyPlacements();
    session.components = session.components.filter(c => !['development-3', 'development-11'].includes(c.id));
    const missing = designInstances(session).filter(n => ['development-3', 'development-11'].includes(n.componentId)).map(n => n.id);
    const resolution = designGeometryResolution(session);
    expect(resolution.missingInstanceIds).toEqual(missing);
    expect(resolution.resolvedInstanceCount).toBe(449 - missing.length);
    try { await loadDesignScene(session, new AbortController().signal); throw new Error('expected missing geometry'); }
    catch (error) { expect(error).toBeInstanceOf(DesignSceneLoadError); expect((error as DesignSceneLoadError).resolution.missingInstanceIds).toEqual(missing); }
    expect(loadComponent).not.toHaveBeenCalled();
  });
  it.each(['reference', 'unqualified', 'placeholder'])('refuses %s geometry while accepting independently authored development CAD', async reason => {
    const session = manyPlacements(1, 1);
    expect(designGeometryResolution(session).resolvedInstanceCount).toBe(1);
    if (reason === 'reference') session.components[0].referenceOnly = true;
    if (reason === 'unqualified') session.components[0].rightsStatus = 'unverified';
    if (reason === 'placeholder') session.components[0].geometryClass = 'placeholder';
    await expect(loadDesignScene(session, new AbortController().signal)).rejects.toBeInstanceOf(DesignSceneLoadError);
    expect(designGeometryResolution(session).missingInstanceIds).toEqual(['placement-0']);
    expect(loadComponent).not.toHaveBeenCalled();
  });
  it('does not silently choose a duplicate definition or accept empty geometry', async () => {
    const session = manyPlacements(1, 1);
    session.components.push(session.components[0]);
    await expect(loadDesignScene(session, new AbortController().signal)).rejects.toThrow('Duplicate');
    session.components.pop();
    vi.mocked(loadComponent).mockResolvedValue({ scene: new Group(), meshCount: 1, bounds: new Box3() });
    await expect(loadDesignScene(session, new AbortController().signal)).rejects.toThrow('no renderable geometry');
  });
  it('reports the affected instances on a failed component fetch and releases preceding templates', async () => {
    const session = manyPlacements(), template = sourceTemplate();
    const geometryDispose = vi.spyOn(template.geometry, 'dispose'), materialDispose = vi.spyOn(template.material, 'dispose');
    vi.mocked(loadComponent).mockResolvedValueOnce(template).mockRejectedValueOnce(new Error('Protected asset unavailable'));
    try { await loadDesignScene(session, new AbortController().signal); throw new Error('expected load failure'); }
    catch (error) {
      expect(error).toBeInstanceOf(DesignSceneLoadError);
      const resolution = (error as DesignSceneLoadError).resolution;
      expect(resolution.loadedInstanceCount).toBe(0);
      expect(resolution.missingComponentIds).toEqual(['development-1']);
      expect(resolution.missingInstanceIds).toEqual(designInstances(session).filter(n => n.componentId === 'development-1').map(n => n.id));
    }
    expect(geometryDispose).toHaveBeenCalledOnce(); expect(materialDispose).toHaveBeenCalledOnce();
  });
  it('releases shared textures/materials once and restores per-instance highlighting before disposal', async () => {
    const template = sourceTemplate(), texture = new Texture(), secondMaterial = new MeshBasicMaterial({ map: texture });
    template.material.map = texture;
    (template.scene.children[0].children[1] as Mesh).material = secondMaterial;
    const geometryDispose = vi.spyOn(template.geometry, 'dispose'), materialDispose = vi.spyOn(template.material, 'dispose');
    const secondDispose = vi.spyOn(secondMaterial, 'dispose'), textureDispose = vi.spyOn(texture, 'dispose');
    vi.mocked(loadComponent).mockResolvedValue(template);
    const graph = await loadDesignScene(manyPlacements(449, 1), new AbortController().signal);
    const first = graph.instances.get('placement-0')!, other = graph.instances.get('placement-1')!;
    highlightSelection(first, first, '#ffff00');
    expect(firstMesh(first).material).not.toBe(firstMesh(other).material);
    expect(firstMesh(other).material).toBe(template.material);
    disposeDesignScene(graph); disposeDesignScene(graph);
    expect(geometryDispose).toHaveBeenCalledOnce(); expect(materialDispose).toHaveBeenCalledOnce();
    expect(secondDispose).toHaveBeenCalledOnce(); expect(textureDispose).toHaveBeenCalledOnce();
  });
  it('cleans up an aborted load without publishing a partial scene', async () => {
    const template = sourceTemplate(), abort = new AbortController(), dispose = vi.spyOn(template.geometry, 'dispose');
    vi.mocked(loadComponent).mockImplementation(async () => { abort.abort(); return template; });
    await expect(loadDesignScene(manyPlacements(), abort.signal)).rejects.toMatchObject({ name: 'AbortError' });
    expect(loadComponent).toHaveBeenCalledOnce(); expect(dispose).toHaveBeenCalledOnce();
  });
});
