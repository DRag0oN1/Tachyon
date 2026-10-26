import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Quaternion, Vector3 } from 'three';

const SVG_NS = 'http://www.w3.org/2000/svg';
const AXES = [
  { label: 'X', direction: new Vector3(1, 0, 0), color: 'var(--mechanical-red, #c25950)' },
  { label: 'Y', direction: new Vector3(0, 1, 0), color: '#42977b' },
  { label: 'Z', direction: new Vector3(0, 0, 1), color: 'var(--blue, #317cb8)' },
];

/** World-axis directions in the actual camera basis, without camera tweening.
 * Updates only when the demand-rendered viewport draws, including with reduced
 * motion enabled. It displays direction, never fabricated robot coordinates.
 */
export function OrientationMarker() {
  const { camera, gl, invalidate } = useThree();
  const inverse = useRef(new Quaternion());
  const projected = useRef(new Vector3());
  const elements = useRef<{ line: SVGLineElement; text: SVGTextElement }[]>([]);

  useEffect(() => {
    const host = gl.domElement.parentElement;
    if (!host) return;
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.classList.add('orientation-marker');
    svg.setAttribute('viewBox', '0 0 76 76');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'World axes projected from the current camera');
    Object.assign(svg.style, {
      position: 'absolute', left: '16px', bottom: '144px', width: '76px', height: '76px',
      pointerEvents: 'none', color: 'var(--muted)', fontFamily: 'var(--font-mono, monospace)',
    });
    const title = document.createElementNS(SVG_NS, 'title');
    title.textContent = 'Camera orientation · world X, Y and Z axes';
    svg.appendChild(title);
    const caption = document.createElementNS(SVG_NS, 'text');
    caption.setAttribute('x', '38'); caption.setAttribute('y', '73');
    caption.setAttribute('text-anchor', 'middle'); caption.setAttribute('font-size', '7');
    caption.setAttribute('fill', 'currentColor'); caption.textContent = 'WORLD';
    svg.appendChild(caption);
    elements.current = AXES.map(axis => {
      const line = document.createElementNS(SVG_NS, 'line');
      line.setAttribute('x1', '38'); line.setAttribute('y1', '34');
      line.setAttribute('stroke', axis.color); line.setAttribute('stroke-width', '2');
      line.setAttribute('stroke-linecap', 'round');
      const text = document.createElementNS(SVG_NS, 'text');
      text.textContent = axis.label;
      text.setAttribute('fill', axis.color); text.setAttribute('font-size', '10');
      text.setAttribute('font-weight', '700'); text.setAttribute('text-anchor', 'middle');
      text.setAttribute('dominant-baseline', 'central');
      text.style.paintOrder = 'stroke'; text.style.stroke = 'var(--background)'; text.style.strokeWidth = '3px';
      svg.append(line, text);
      return { line, text };
    });
    host.appendChild(svg);
    invalidate();
    return () => { elements.current = []; svg.remove(); };
  }, [gl, invalidate]);

  useFrame(() => {
    camera.getWorldQuaternion(inverse.current).invert();
    AXES.forEach((axis, index) => {
      const element = elements.current[index];
      if (!element) return;
      const direction = projected.current.copy(axis.direction).applyQuaternion(inverse.current);
      element.line.setAttribute('x2', String(38 + direction.x * 22));
      element.line.setAttribute('y2', String(34 - direction.y * 22));
      element.text.setAttribute('x', String(38 + direction.x * 30));
      element.text.setAttribute('y', String(34 - direction.y * 30));
      element.line.setAttribute('opacity', direction.z < 0 ? '0.5' : '1');
    });
  });
  return null;
}
