import { useRef, useState, type ReactNode } from 'react';
import { Icon } from '../components/Icon';
import { useDialogFocus } from '../workspace/useDialogFocus';

export function PanelHost({ title, subtitle, children, onClose }: { title: string; subtitle: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLElement>(null);
  const drag = useRef<{ y: number; height: number } | null>(null);
  const [height, setHeight] = useState(56);
  useDialogFocus(ref, true);
  const clamp = (h: number) => Math.min(75, Math.max(32, h));
  return <section ref={ref} role="dialog" aria-label={title} tabIndex={-1} className="workspace-panel" style={{ '--sheet-height': `${height}dvh` } as React.CSSProperties}
    onKeyDown={e => { if (e.key === 'Escape') { e.stopPropagation(); onClose(); } }}>
    <div className="sheet-resizer" role="separator" aria-label="Resize panel" aria-orientation="horizontal" aria-valuemin={32} aria-valuemax={75} aria-valuenow={Math.round(height)} tabIndex={0}
      onKeyDown={e => { if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); setHeight(h => clamp(h + (e.key === 'ArrowUp' ? 5 : -5))); } }}
      onPointerDown={e => { drag.current = { y: e.clientY, height }; e.currentTarget.setPointerCapture(e.pointerId); }}
      onPointerMove={e => { if (drag.current) setHeight(clamp(drag.current.height + (drag.current.y - e.clientY) / window.innerHeight * 100)); }}
      onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}><span /></div>
    <header className="panel-header"><div><span className="eyebrow">{subtitle}</span><h1>{title}</h1></div><button className="icon-button" aria-label={`Close ${title}`} onClick={onClose}><Icon name="close" /></button></header>
    <div className="panel-scroll">{children}</div>
  </section>;
}
