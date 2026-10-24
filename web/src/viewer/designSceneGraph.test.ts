import { describe, expect, it } from 'vitest';
import { BoxGeometry, Group, Mesh, MeshBasicMaterial, Vector3 } from 'three';
import { applyDesignPose, boundInstances, designInstances, designRevisionId, instanceAt, instanceBounds, type DesignSceneSession } from './designSceneGraph';

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
});
