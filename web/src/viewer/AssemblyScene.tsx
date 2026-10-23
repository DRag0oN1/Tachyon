import { Component, useCallback, useEffect, useRef, useState, type ComponentRef, type ReactNode } from 'react';
import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { BoxHelper, PerspectiveCamera, Vector3 } from 'three';
import type { ComponentDefinition, Selection, Theme } from '../api/contracts';
import { errorMessage } from '../api/client';
import { disposeScene, loadComponent, type LoadedComponent } from './loadComponent';

export type SceneStatus = { state: 'idle' | 'loading' | 'ready' | 'failed'; meshCount?: number; message?: string; boundsM?: { min: number[]; max: number[] } };
interface Props {
  component: ComponentDefinition;
  selection: Selection | null;
  theme: Theme;
  resetKey: number;
  focusKey: number;
  panelOpen: boolean;
  onSelect: (selection: Selection | null) => void;
  onStatus: (status: SceneStatus) => void;
}
class SceneBoundary extends Component<{ children: ReactNode; onError: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onError(); }
  render() { return this.state.failed ? null : this.props.children; }
}
function NativeScene({ model, ...props }: Props & { model: LoadedComponent }) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const { camera, invalidate, size, gl } = useThree();
  const box = useRef<BoxHelper>(null);
  const observeCamera = useCallback(() => {
    // Passive observation of the real controls: no React updates or render loop.
    gl.domElement.dataset.cameraPosition = JSON.stringify(camera.position.toArray());
    gl.domElement.dataset.cameraQuaternion = JSON.stringify(camera.quaternion.toArray());
    gl.domElement.dataset.controlsTarget = JSON.stringify(controls.current?.target.toArray() ?? []);
  }, [camera, gl]);
  useEffect(() => {
    const center = model.bounds.getCenter(new Vector3());
    const radius = model.bounds.getSize(new Vector3()).length() / 2;
    if (!(camera instanceof PerspectiveCamera)) return;
    const fov = camera.fov * Math.PI / 180;
    const fit = Math.max(radius / Math.sin(fov / 2), radius / Math.sin(Math.atan(Math.tan(fov / 2) * size.width / size.height))) * 1.3;
    camera.near = Math.max(radius / 1000, 0.00001);
    camera.far = Math.max(fit * 100, 10);
    camera.position.copy(center).add(new Vector3(1, 0.65, 1).normalize().multiplyScalar(fit));
    camera.lookAt(center); camera.updateProjectionMatrix();
    if (controls.current) {
      controls.current.target.copy(center);
      controls.current.minDistance = Math.max(radius * 0.15, 0.0001);
      controls.current.maxDistance = Math.max(fit * 15, 1);
      controls.current.update();
    }
    observeCamera();
    invalidate();
  }, [model, camera, invalidate, observeCamera, props.resetKey, props.focusKey]);
  useEffect(() => {
    if (!(camera instanceof PerspectiveCamera)) return;
    if (props.panelOpen && size.width <= 760) {
      camera.setViewOffset(size.width, size.height, size.height <= 510 ? size.width * 0.25 : 0, size.height > 510 ? size.height * 0.23 : 0, size.width, size.height);
    } else camera.clearViewOffset();
    camera.updateProjectionMatrix(); invalidate();
  }, [camera, invalidate, props.panelOpen, size.width, size.height]);
  useEffect(() => {
    if (box.current) {
      let target = model.scene;
      if (props.selection?.nativeNodeId) model.scene.traverse(object => {
        if (object.userData.tachyonNativeNodeId === props.selection?.nativeNodeId) target = object as typeof target;
      });
      box.current.setFromObject(target); invalidate();
    }
  }, [model, props.selection, invalidate]);
  const select = (event: ThreeEvent<MouseEvent>) => {
    // R3F's delta distinguishes taps from orbit drags.
    if (event.delta > 5) return;
    event.stopPropagation();
    let node = event.object;
    while (!node.userData.tachyonNativeNodeId && node.parent) node = node.parent;
    props.onSelect({ componentId: props.component.id, catalogMeshSha256: props.component.meshSha256, meshName: event.object.name || undefined, nativeNodeId: node.userData.tachyonNativeNodeId });
  };
  return <>
    <ambientLight intensity={1.4} />
    <hemisphereLight args={['#ffffff', '#87909a', 2.1]} />
    <directionalLight position={[3, 5, 4]} intensity={3} />
    <directionalLight position={[-3, 1, -2]} intensity={1} />
    <primitive object={model.scene} onClick={select} dispose={null} />
    {props.selection?.componentId === props.component.id && <boxHelper ref={box} args={[model.scene, props.theme === 'snap' ? '#2069b5' : '#6ec8fa']} />}
    <OrbitControls ref={controls} makeDefault enableDamping={false} screenSpacePanning rotateSpeed={0.7} zoomSpeed={0.8} onChange={observeCamera} />
  </>;
}
export function AssemblyScene(props: Props) {
  const [model, setModel] = useState<LoadedComponent | null>(null);
  const onStatus = useRef(props.onStatus);
  onStatus.current = props.onStatus;
  useEffect(() => {
    const abort = new AbortController();
    let loaded: LoadedComponent | null = null;
    setModel(null); onStatus.current({ state: 'loading' });
    loadComponent(props.component, abort.signal).then(result => {
      if (abort.signal.aborted) { disposeScene(result.scene); return; }
      loaded = result; setModel(result);
    }).catch(error => { if (!abort.signal.aborted) onStatus.current({ state: 'failed', message: errorMessage(error) }); });
    return () => { abort.abort(); if (loaded) disposeScene(loaded.scene); };
  }, [props.component]);
  return <div className="canvas-host" data-testid="cad-canvas" aria-label="Source component 3D viewer">
    <SceneBoundary onError={() => onStatus.current({ state: 'failed', message: 'The 3D renderer is unavailable. Check WebGL support, then retry. Source information remains available.' })}>
      <Canvas frameloop="demand" dpr={[1, 1.75]} camera={{ fov: 40 }} gl={{ antialias: true, alpha: true }}
        onCreated={({ gl }) => { gl.domElement.setAttribute('aria-label', 'Orbit, zoom, pan and select source component'); }}
        onPointerMissed={event => { if (event.type === 'click') props.onSelect(null); }}
        fallback={<RendererUnavailable onStatus={props.onStatus} />}>
        {model && <PresentedScene {...props} model={model} />}
      </Canvas>
    </SceneBoundary>
  </div>;
}
function PresentedScene(props: Props & { model: LoadedComponent }) {
  const { gl, invalidate } = useThree();
  useEffect(() => {
    // Report real scene submission, not merely a successful HTTP response.
    const notify = () => {
      if (!gl.getContext().isContextLost() && gl.info.render.calls > 0) props.onStatus({ state: 'ready', meshCount: props.model.meshCount, boundsM: { min: props.model.bounds.min.toArray(), max: props.model.bounds.max.toArray() } });
      else props.onStatus({ state: 'failed', message: 'No source geometry was drawn. Retry the 3D renderer.' });
    };
    const lost = (e: Event) => { e.preventDefault(); props.onStatus({ state: 'failed', message: 'The graphics context was lost. Retry to reload the source component.' }); };
    gl.domElement.addEventListener('webglcontextlost', lost);
    let second = 0;
    const id = requestAnimationFrame(() => { invalidate(); second = requestAnimationFrame(notify); });
    return () => { cancelAnimationFrame(id); cancelAnimationFrame(second); gl.domElement.removeEventListener('webglcontextlost', lost); };
  }, [props.model, gl, invalidate, props.onStatus]);
  return <NativeScene {...props} />;
}
function RendererUnavailable({ onStatus }: { onStatus: (s: SceneStatus) => void }) {
  useEffect(() => { onStatus({ state: 'failed', message: 'WebGL is unavailable in this browser. Source details remain inspectable.' }); }, [onStatus]);
  return null;
}
