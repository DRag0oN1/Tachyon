import { act,fireEvent,render,screen,waitFor } from '@testing-library/react';
import { beforeEach,expect,it,vi } from 'vitest';
import { api } from '../api/client';
import type { Catalog } from '../api/contracts';
import type { DesignSession } from '../api/strategy';
import { componentFixture } from '../test/contracts';
import type { OperationModel } from '../viewer/operationKinematics';
import { OperationPanel } from './OperationPanel';

vi.mock('../api/client',()=>({api:{post:vi.fn(),catalog:vi.fn()},errorMessage:(value:unknown)=>value instanceof Error?value.message:'Request failed'}));
beforeEach(()=>{vi.mocked(api.post).mockReset();vi.mocked(api.catalog).mockReset();});

// Independently authored UI metadata only: no CAD, physical-operation evidence,
// manufacturer identity or authentic robot acceptance is exercised by this file.
const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
const objects=['cup','pin','target'].map(id=>({...componentFixture,id}));
const catalog:Catalog={profile:'user_provided_local',components:objects,blockers:[]};
function session():DesignSession {
  return {designId:'audit-design',architectureId:'audit-A',strategyId:'audit-strategy',status:'partial',missing:[],canEdit:false,
    revisionId:'accepted-old',accepted:{id:'accepted-old',parentRevisionId:null,engineeringHash:'a'.repeat(64),assembly:{
      designId:'audit-design',configurationId:'lower',units:'m',upAxis:'Y',matrixLayout:'column-major',
      instances:[{id:'source-part',componentId:componentFixture.id,subsystemId:'cup_cradle',parentId:null,transform:{matrix:identity}}],
      subsystems:[{id:'cup_cradle',name:'Original UI metadata fixture'}]}},candidate:null,bindings:null,candidateBindings:null,
    worldTransforms:{'source-part':identity},candidateWorldTransforms:{},components:[componentFixture],qualification:{completeRobot:false,testFixtureOnly:true},plan:{}};
}
function changed(source:DesignSession,field:string):DesignSession {
  const next=structuredClone(source);
  if(field==='design'){next.designId='another-design';next.accepted!.assembly.designId=next.designId;}
  if(field==='revision'){next.revisionId='accepted-new';next.accepted!.id=next.revisionId;}
  if(field==='engineeringHash')next.accepted!.engineeringHash='b'.repeat(64);
  if(field==='candidate')next.candidate={...structuredClone(next.accepted!),id:'candidate-preview',parentRevisionId:next.revisionId};
  return next;
}
function response(source:DesignSession):OperationModel {
  return {schemaVersion:1,kind:'development_cup_kinematics',designId:source.designId,revisionId:source.revisionId!,engineeringHash:source.accepted!.engineeringHash,
    durationS:14,keyframes:[],kinematicGraph:{rootInstanceId:'source-part',instances:[],treeRelationships:[]},
    object:{componentId:'cup',instanceId:'operation-cup',anchor:{instanceId:'source-part',localPointM:[0,0,0]},
      initialTransform:{matrix:identity},targetTransform:{matrix:identity},heldRelativeTransform:{matrix:identity}},
    staticObjects:[{componentId:'pin',instanceId:'operation-pin',transform:{matrix:identity}},{componentId:'target',instanceId:'operation-target',transform:{matrix:identity}}],
    objectComponents:objects,events:[],validation:{graphValid:true,sampleCount:33,capturePredicatePassed:true,scoringVerified:false,physicalPerformanceVerified:false,approachClearanceOverPinTopM:0},
    limitations:['Synthetic UI response fixture only; no operation or CAD acceptance']};
}
function deferred<T>() {
  let resolve!:(value:T)=>void,reject!:(reason:Error)=>void;
  const promise=new Promise<T>((done,fail)=>{resolve=done;reject=fail;});
  return {promise,resolve,reject};
}
function clickPrepare(){fireEvent.click(screen.getByRole('button',{name:'Prepare Cup operation'}));}
function requestSignal(index=0){return vi.mocked(api.post).mock.calls[index][2]!;}

it('commits a current validated response and passes an AbortSignal to the operation request',async()=>{
  const source=session(),pending=deferred<OperationModel>(),onChange=vi.fn();
  vi.mocked(api.post).mockReturnValueOnce(pending.promise);
  render(<OperationPanel session={source} playback={null} onChange={onChange}/>);clickPrepare();
  expect(requestSignal()).toBeInstanceOf(AbortSignal);
  expect(requestSignal().aborted).toBe(false);
  const model=response(source);await act(async()=>pending.resolve(model));
  expect(onChange).toHaveBeenCalledExactlyOnceWith({model,timeS:0,playing:false});
  expect(api.catalog).not.toHaveBeenCalled();
  expect(screen.getByRole('button',{name:'Prepare Cup operation'})).toBeEnabled();
});

it.each(['design','revision','engineeringHash','candidate'])('aborts a pending operation on %s change and ignores its eventual response',async field=>{
  const source=session(),pending=deferred<OperationModel>(),onChange=vi.fn();
  vi.mocked(api.post).mockReturnValueOnce(pending.promise);
  const view=render(<OperationPanel session={source} playback={null} onChange={onChange}/>);clickPrepare();
  const signal=requestSignal();
  view.rerender(<OperationPanel session={changed(source,field)} playback={null} onChange={onChange}/>);
  expect(signal.aborted).toBe(true);
  await act(async()=>pending.resolve(response(source)));
  expect(onChange).not.toHaveBeenCalled();expect(api.catalog).not.toHaveBeenCalled();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it.each(['resolve','reject'])('ignores stale %s/catch/finally while a newer operation request remains busy',async outcome=>{
  const source=session(),next=changed(source,'revision'),oldRequest=deferred<OperationModel>(),newRequest=deferred<OperationModel>(),onChange=vi.fn();
  vi.mocked(api.post).mockReturnValueOnce(oldRequest.promise).mockReturnValueOnce(newRequest.promise);
  const view=render(<OperationPanel session={source} playback={null} onChange={onChange}/>);clickPrepare();
  view.rerender(<OperationPanel session={next} playback={null} onChange={onChange}/>);clickPrepare();
  const active=requestSignal(1);
  await act(async()=>{if(outcome==='resolve')oldRequest.resolve(response(source));else oldRequest.reject(new Error('Stale failure must stay invisible'));});
  expect(active.aborted).toBe(false);
  expect(screen.getByRole('button',{name:'Checking modeled sequence…'})).toBeDisabled();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();expect(onChange).not.toHaveBeenCalled();
  await act(async()=>newRequest.resolve(response(next)));
  expect(onChange).toHaveBeenCalledOnce();expect(onChange.mock.calls[0][0].model.revisionId).toBe(next.revisionId);
});

it.each(['revision','candidate'])('rechecks freshness after catalog resolution when the %s changes',async field=>{
  const source=session(),pending=deferred<Catalog>(),onChange=vi.fn();
  const {objectComponents:_,...withoutObjects}=response(source);void _;
  vi.mocked(api.post).mockResolvedValueOnce(withoutObjects);
  vi.mocked(api.catalog).mockReturnValueOnce(pending.promise);
  const view=render(<OperationPanel session={source} playback={null} onChange={onChange}/>);clickPrepare();
  await waitFor(()=>expect(api.catalog).toHaveBeenCalledOnce());
  expect(vi.mocked(api.catalog).mock.calls[0][0]).toBe(requestSignal());
  view.rerender(<OperationPanel session={changed(source,field)} playback={null} onChange={onChange}/>);
  expect(requestSignal().aborted).toBe(true);
  await act(async()=>pending.resolve(catalog));
  expect(onChange).not.toHaveBeenCalled();expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it.each(['post','catalog'])('aborts on unmount during %s and never commits its late result',async phase=>{
  const source=session(),post=deferred<OperationModel>(),lookup=deferred<Catalog>(),onChange=vi.fn();
  if(phase==='post')vi.mocked(api.post).mockReturnValueOnce(post.promise);
  else{
    const {objectComponents:_,...withoutObjects}=response(source);void _;
    vi.mocked(api.post).mockResolvedValueOnce(withoutObjects);vi.mocked(api.catalog).mockReturnValueOnce(lookup.promise);
  }
  const view=render(<OperationPanel session={source} playback={null} onChange={onChange}/>);clickPrepare();
  if(phase==='catalog')await waitFor(()=>expect(api.catalog).toHaveBeenCalledOnce());
  const signal=requestSignal();view.unmount();expect(signal.aborted).toBe(true);
  await act(async()=>{if(phase==='post')post.resolve(response(source));else lookup.resolve(catalog);});
  expect(onChange).not.toHaveBeenCalled();
});

it('keeps a current request across unrelated rerenders and reports current failures for retry',async()=>{
  const source=session(),pending=deferred<OperationModel>(),onChange=vi.fn();
  vi.mocked(api.post).mockReturnValueOnce(pending.promise);
  const view=render(<OperationPanel session={source} playback={null} onChange={onChange}/>);clickPrepare();
  view.rerender(<OperationPanel session={{...source,missing:[{role:'fixture',code:'INFO',message:'Metadata only'}]}} playback={null} onChange={onChange}/>);
  expect(requestSignal().aborted).toBe(false);
  await act(async()=>pending.reject(new Error('Current request failed')));
  expect(screen.getByRole('alert')).toHaveTextContent('Current request failed');
  expect(screen.getByRole('button',{name:'Prepare Cup operation'})).toBeEnabled();
  expect(onChange).not.toHaveBeenCalled();
});
