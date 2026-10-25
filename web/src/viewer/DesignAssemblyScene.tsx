import { Component, useEffect, useLayoutEffect, useRef, useState, type ComponentRef, type ReactNode } from 'react';
import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Box3, PerspectiveCamera, PMREMGenerator, Vector3 } from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import type { Theme } from '../api/contracts';
import { errorMessage } from '../api/client';
import type { SceneStatus } from './AssemblyScene';
import { frameCamera, highlightSelection } from './inspection';
import { OperationScene } from './OperationScene';
import type { OperationPlayback } from './operationKinematics';
import { SUBSYSTEM_COLORS } from './subsystemPalette';
import { applyDesignPose, boundInstances, designGeometryResolution, designInstances, designRevisionId, DesignSceneLoadError, disposeDesignScene, instanceAt, instanceBounds, loadDesignScene, type DesignGeometryResolution, type DesignSceneGraph, type DesignSceneSession } from './designSceneGraph';

export type DesignSceneStatus = SceneStatus & { geometryResolution?: DesignGeometryResolution };

interface Props {
  session: DesignSceneSession; theme: Theme; activeActionId: string | null;
  selectedInstanceId: string | null; onSelectInstance: (id: string | null) => void;
  onStatus: (status: DesignSceneStatus) => void;
  resetKey: number; focusKey: number; panelOpen: boolean;
  operation?:OperationPlayback|null; colorSubsystems?:boolean;
}
export function DesignAssemblyScene(props: Props) {
  return <DesignBoundary session={props.session} onStatus={props.onStatus}><LoadedDesign {...props}/></DesignBoundary>;
}
class DesignBoundary extends Component<{ session:DesignSceneSession; onStatus:Props['onStatus']; children:ReactNode },{failed:boolean}> {
  state={failed:false};
  static getDerivedStateFromError() { return {failed:true}; }
  componentDidCatch() { this.props.onStatus({state:'failed',message:'The assembly renderer failed. Strategy and accepted design data are retained; retry the geometry.'}); }
  componentDidUpdate(previous:Readonly<{session:DesignSceneSession}>) {
    if (this.state.failed && previous.session!==this.props.session) this.setState({failed:false});
  }
  render() { return this.state.failed ? null : this.props.children; }
}
function LoadedDesign(props: Props) {
  const [graph, setGraph] = useState<DesignSceneGraph | null>(null);
  const [failed, setFailed] = useState(false);
  const status = useRef(props.onStatus); status.current = props.onStatus;
  const instances = designInstances(props.session);
  const geometryKey = JSON.stringify([instances, props.session.components.map(c => [c.id,c.meshSha256,c.referenceOnly,c.rightsStatus,c.originKind,c.geometryClass])]);
  useEffect(() => {
    const abort = new AbortController(); let loaded: DesignSceneGraph | null = null;
    setGraph(null); setFailed(false); status.current({ state: 'loading', geometryResolution: designGeometryResolution(props.session) });
    loadDesignScene(props.session, abort.signal).then(result => {
      if (abort.signal.aborted) { disposeDesignScene(result); return; }
      loaded = result; setGraph(result);
    }).catch(error => { if (!abort.signal.aborted) { setFailed(true); status.current({ state: 'failed', message: errorMessage(error),
      ...(error instanceof DesignSceneLoadError ? { geometryResolution: error.resolution } : {}) }); } });
    return () => { abort.abort(); if (loaded) disposeDesignScene(loaded); };
    // Transform-only revisions preserve source meshes and the current camera.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geometryKey]);
  return <div className="canvas-host" data-testid="design-canvas" aria-label="Generated assembly inspection"
    data-design-id={props.session.designId} data-revision-id={designRevisionId(props.session)}>
    {!failed && <Canvas frameloop="demand" dpr={[1, 1.75]} camera={{ fov: 40 }} gl={{ antialias: true, alpha: true }}
      onCreated={({ gl }) => gl.domElement.setAttribute('aria-label','Orbit, zoom, pan and select assembly components')}
      onPointerMissed={event => { if (event.type === 'click') props.onSelectInstance(null); }}
      fallback={<Unavailable onStatus={props.onStatus} />}>
      {graph && <Presented {...props} graph={graph} />}
    </Canvas>}
  </div>;
}
function Unavailable({ onStatus }: Pick<Props,'onStatus'>) {
  useEffect(() => { onStatus({ state:'failed',message:'WebGL is unavailable. The assembly and strategy information remain inspectable.' }); },[onStatus]);
  return null;
}
function Presented(props: Props & { graph: DesignSceneGraph }) {
  const { camera, gl, scene, size, invalidate } = useThree();
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const previous = useRef({ graph: props.graph, reset: -1, focus: -1 });
  const poseValid = useRef(false);
  const selected = props.selectedInstanceId ? [props.selectedInstanceId] : boundInstances(props.session, props.activeActionId);
  const selectionKey = JSON.stringify(selected);
  const revision = designRevisionId(props.session);
  function observe() {
    gl.domElement.dataset.cameraPosition = JSON.stringify(camera.position.toArray());
    gl.domElement.dataset.controlsTarget = JSON.stringify(controls.current?.target.toArray() ?? []);
    gl.domElement.dataset.boundInstanceIds = selectionKey;
    gl.domElement.dataset.revisionId = props.graph.resolution?.revisionId ?? revision;
    if (props.graph.resolution) {
      const resolution = props.graph.resolution;
      gl.domElement.dataset.requestedInstanceCount = String(resolution.requestedInstanceCount);
      gl.domElement.dataset.resolvedInstanceCount = String(resolution.resolvedInstanceCount);
      gl.domElement.dataset.loadedInstanceCount = String(resolution.loadedInstanceCount);
      gl.domElement.dataset.loadedComponentCount = String(resolution.loadedComponentCount);
      gl.domElement.dataset.missingInstanceIds = JSON.stringify(resolution.missingInstanceIds);
    }
  }
  useEffect(() => {
    const generator = new PMREMGenerator(gl), room = new RoomEnvironment();
    const map = generator.fromScene(room,.04); const before = scene.environment;
    scene.environment = map.texture; invalidate();
    return () => { scene.environment = before; map.dispose(); room.dispose(); generator.dispose(); };
  },[gl,scene,invalidate]);
  useLayoutEffect(() => {
    poseValid.current = false;
    try {
      applyDesignPose(props.graph, props.session); poseValid.current = true;
      const scorer=props.graph.instances.get('cup-grip-frame');
      if(scorer)gl.domElement.dataset.scoringFrameMatrix=JSON.stringify(scorer.matrixWorld.toArray());
      else delete gl.domElement.dataset.scoringFrameMatrix;
      invalidate();
    }
    catch (error) { props.onStatus({state:'failed',message:errorMessage(error),geometryResolution:props.graph.resolution}); }
  },[props.graph,props.session,invalidate,props.onStatus,gl]);
  useLayoutEffect(() => {
    const restores = [...props.graph.instances].map(([id, target]) => highlightSelection(target, selected.includes(id)||props.colorSubsystems ? target : null, selected.includes(id) ? props.theme==='snap' ? '#2069b5' : '#6ec8fa' : SUBSYSTEM_COLORS[target.userData.subsystemId]??'#8b9dad'));
    invalidate(); return () => { restores.forEach(restore => restore()); invalidate(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[props.graph,selectionKey,props.theme,props.colorSubsystems,invalidate]);
  useEffect(() => {
    if (!(camera instanceof PerspectiveCamera)) return;
    const old = previous.current;
    const reset = old.graph!==props.graph || old.reset!==props.resetKey;
    const focus = old.focus!==props.focusKey;
    previous.current = {graph:props.graph,reset:props.resetKey,focus:props.focusKey};
    if (!reset && !focus) { observe(); return; }
    const whole = new Box3().setFromObject(props.graph.scene,true);
    const bounds = reset ? whole : instanceBounds(props.graph,selected);
    if (!bounds) return;
    camera.up.set(0,1,0);
    const fit = frameCamera(camera,bounds,size,new Vector3(1,.7,1),whole);
    if (controls.current) {
      controls.current.target.copy(fit.center); controls.current.minDistance=fit.minDistance;
      controls.current.maxDistance=fit.maxDistance; controls.current.update();
    }
    observe(); invalidate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[props.graph,props.resetKey,props.focusKey,size.width,size.height,camera,invalidate,selectionKey,revision]);
  useEffect(() => {
    if (!(camera instanceof PerspectiveCamera)) return;
    if (props.panelOpen && size.width <=760) camera.setViewOffset(size.width,size.height,0,size.height*.23,size.width,size.height);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix(); invalidate();
  },[props.panelOpen,camera,size.width,size.height,invalidate]);
  useEffect(() => {
    let second=0;
    const request=requestAnimationFrame(() => { invalidate(); second=requestAnimationFrame(() => {
      if (!poseValid.current) return;
      if (gl.getContext().isContextLost() || gl.info.render.calls===0) props.onStatus({state:'failed',message:'No actual assembly geometry was drawn.',geometryResolution:props.graph.resolution});
      else {
        const bounds=new Box3().setFromObject(props.graph.scene,true);
        props.onStatus({state:'ready',meshCount:props.graph.meshCount,geometryResolution:props.graph.resolution,boundsM:{min:bounds.min.toArray(),max:bounds.max.toArray()}});
      }
    }); });
    return () => { cancelAnimationFrame(request); cancelAnimationFrame(second); };
  },[props.graph,revision,gl,invalidate,props.onStatus]);
  const pick=(event:ThreeEvent<MouseEvent>) => {
    if (event.delta>5) return;
    event.stopPropagation(); props.onSelectInstance(instanceAt(event.object));
  };
  return <>
    <ambientLight intensity={1.4}/><hemisphereLight args={['#fff','#87909a',2.1]}/>
    <directionalLight position={[3,5,4]} intensity={3}/><directionalLight position={[-3,1,-2]} intensity={1}/>
    <primitive object={props.graph.scene} dispose={null} onClick={pick}/>
    {props.operation&&<OperationScene graph={props.graph} session={props.session} playback={props.operation}/>}
    <OrbitControls ref={controls} makeDefault enableDamping={false} screenSpacePanning rotateSpeed={.7} zoomSpeed={.8} onChange={observe}/>
  </>;
}
