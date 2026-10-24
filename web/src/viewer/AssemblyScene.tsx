import { Component, useCallback, useEffect, useLayoutEffect, useRef, useState, type ComponentRef, type ReactNode } from 'react';
import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { PerspectiveCamera, PMREMGenerator, Vector3 } from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import type { ComponentDefinition, Selection, Theme } from '../api/contracts';
import { errorMessage } from '../api/client';
import { disposeScene, loadComponent, type LoadedComponent } from './loadComponent';
import { applyInspection, frameCamera, framingAction, highlightSelection, selectionFromObject, selectionTarget, subtreeBounds, type FrameRequest, type Inspection } from './inspection';

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
  inspection?: Inspection;
  upAxis?: 'X' | 'Y' | 'Z';
}
class SceneBoundary extends Component<{ children: ReactNode; onError: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onError(); }
  render() { return this.state.failed ? null : this.props.children; }
}
function NativeScene({ model, ...props }: Props & { model: LoadedComponent }) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const { camera, invalidate, size, gl, scene: renderScene } = useThree();
  useEffect(() => {
    // Procedural studio lighting, generated locally; no remote environment assets.
    const generator = new PMREMGenerator(gl);
    const room = new RoomEnvironment();
    const environment = generator.fromScene(room, 0.04);
    const previous = renderScene.environment;
    renderScene.environment = environment.texture;
    invalidate();
    return () => { renderScene.environment = previous; environment.dispose(); room.dispose(); generator.dispose(); };
  }, [gl, renderScene, invalidate]);
  const frameRequest = useRef<FrameRequest | null>(null);
  const observeCamera = useCallback(() => {
    // Passive observation of the real controls: no React updates or render loop.
    gl.domElement.dataset.cameraPosition = JSON.stringify(camera.position.toArray());
    gl.domElement.dataset.cameraQuaternion = JSON.stringify(camera.quaternion.toArray());
    gl.domElement.dataset.cameraUp = JSON.stringify(camera.up.toArray());
    gl.domElement.dataset.controlsTarget = JSON.stringify(controls.current?.target.toArray() ?? []);
  }, [camera, gl]);
  useLayoutEffect(() => {
    const restore = applyInspection(model.scene, props.inspection);
    invalidate();
    return () => { restore(); invalidate(); };
  }, [model, props.inspection, invalidate]);
  useLayoutEffect(() => {
    const restore = highlightSelection(model.scene, selectionTarget(model.scene, props.component, props.selection), props.theme === 'snap' ? '#2069b5' : '#6ec8fa');
    invalidate();
    return () => { restore(); invalidate(); };
  }, [model, props.component, props.selection, props.theme, invalidate]);
  useEffect(() => {
    const upAxis = props.upAxis ?? 'Z';
    const next = { model, resetKey: props.resetKey, focusKey: props.focusKey, upAxis };
    const action = framingAction(frameRequest.current, next);
    frameRequest.current = next;
    if (!action) return;
    if (!(camera instanceof PerspectiveCamera)) return;
    camera.up.copy(upAxis === 'Y' ? new Vector3(0, 0, -1) : upAxis === 'X' ? new Vector3(1, 0, 0) : new Vector3(0, 1, 0));
    const target = action === 'focus' && props.selection ? selectionTarget(model.scene, props.component, props.selection) : model.scene;
    // A stale or hidden selection never silently focuses the whole assembly.
    const bounds = action === 'reset' ? model.bounds : target && subtreeBounds(target);
    if (!bounds) return;
    const defaultDirection = upAxis === 'Y' ? new Vector3(1, 1, -.65) : upAxis === 'X' ? new Vector3(.65, 1, 1) : new Vector3(1, .65, 1);
    const direction = action === 'focus' && controls.current ? camera.position.clone().sub(controls.current.target) : defaultDirection;
    const fit = frameCamera(camera, bounds, size, direction, model.bounds);
    if (controls.current) {
      controls.current.target.copy(fit.center);
      controls.current.minDistance = fit.minDistance;
      controls.current.maxDistance = fit.maxDistance;
      controls.current.update();
    }
    observeCamera();
    invalidate();
  }, [model, camera, invalidate, observeCamera, props.component, props.selection, props.resetKey, props.focusKey, props.upAxis, size.width, size.height]);
  useEffect(() => {
    if (!(camera instanceof PerspectiveCamera)) return;
    if (props.panelOpen && size.width <= 760) {
      camera.setViewOffset(size.width, size.height, size.height <= 510 ? size.width * 0.25 : 0, size.height > 510 ? size.height * 0.23 : 0, size.width, size.height);
    } else camera.clearViewOffset();
    camera.updateProjectionMatrix(); invalidate();
  }, [camera, invalidate, props.panelOpen, size.width, size.height]);
  const select = (event: ThreeEvent<MouseEvent>) => {
    // R3F's delta distinguishes taps from orbit drags.
    if (event.delta > 5) return;
    event.stopPropagation();
    props.onSelect(selectionFromObject(model.scene, props.component, event.object));
  };
  return <>
    <ambientLight intensity={1.4} />
    <hemisphereLight args={['#ffffff', '#87909a', 2.1]} />
    <directionalLight position={[3, 5, 4]} intensity={3} />
    <directionalLight position={[-3, 1, -2]} intensity={1} />
    <primitive object={model.scene} onClick={select} dispose={null} />
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
