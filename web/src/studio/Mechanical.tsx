import { useId, type ComponentPropsWithoutRef, type ReactNode } from 'react';
import '../styles/mechanical.css';

export interface DockFrameProps extends ComponentPropsWithoutRef<'section'> {
  children: ReactNode;
  label?: string;
  code?: string;
}

/** A dockable housing. Content and focus outlines stay outside the notched skin. */
export function DockFrame({ children, className = '', label, code, ...props }: DockFrameProps) {
  const labelId = useId();
  return (
    <section {...props} className={`dock-frame ${className}`.trim()}
      aria-labelledby={props['aria-labelledby'] ?? (label && !props['aria-label'] ? labelId : undefined)}>
      <div className="dock-frame__hardware" aria-hidden="true">
        <span className="dock-frame__rail">{[0, 1, 2, 3, 4].map(slot => <i key={slot} />)}</span>
        {['tl', 'tr', 'bl', 'br'].map(corner => <i key={corner} className={`dock-frame__fastener dock-frame__fastener--${corner}`} />)}
      </div>
      {(label || code) && <header className="dock-frame__header">
        {label && <span id={labelId} className="dock-frame__label">{label}</span>}
        {code && <span className="dock-frame__code">{code}</span>}
      </header>}
      <div className="dock-frame__body">{children}</div>
    </section>
  );
}

function gearPath(cx: number, cy: number, outer: number, root: number, teeth: number) {
  return Array.from({ length: teeth * 4 }, (_, index) => {
    const angle = index * Math.PI / (teeth * 2) - Math.PI / 2;
    const radius = index % 4 === 1 || index % 4 === 2 ? outer : root;
    return `${index ? 'L' : 'M'}${(cx + Math.cos(angle) * radius).toFixed(2)},${(cy + Math.sin(angle) * radius).toFixed(2)}`;
  }).join(' ') + 'Z';
}

function Fastener({ x, y, radius = 3 }: { x: number; y: number; radius?: number }) {
  return <g className="mechanical-fastener" transform={`translate(${x} ${y})`}>
    <circle r={radius} /><path d={`M${-radius * .55},${radius * .55}L${radius * .55},${-radius * .55}`} />
  </g>;
}

export interface MechanicalCoreProps { expanded?: boolean; className?: string }

/** Original interface emblem; expansion separates the four shell modules. */
export function MechanicalCore({ expanded = false, className = '' }: MechanicalCoreProps) {
  return <svg className={`mechanical-core ${className}`.trim()} viewBox="0 0 128 128"
    data-expanded={expanded ? 'true' : 'false'} aria-hidden="true" focusable="false">
    <path className="mechanical-core__chassis" d="M25 12H103L116 25V103L103 116H25L12 103V25Z" />
    <g className="mechanical-core__datum" fill="none">
      <path d="M64 5V21M64 107V123M5 64H21M107 64H123" />
      <circle cx="64" cy="64" r="43" strokeDasharray="2 5" />
      <path d="M23 23L41 41M87 41L105 23M23 105L41 87M87 87L105 105" />
    </g>
    <g className="core-module module-a mechanical-core__module">
      <path className="mechanical-core__plate" d="M28 18H56V34L43 43H18V28Z" />
      <path className="mechanical-core__latch" d="M24 38H39L48 31H56V37L45 47H24Z" />
      <path className="mechanical-core__vent" d="M34 23V30M40 23V30M46 23V28" /><Fastener x={25} y={27} />
    </g>
    <g className="core-module module-b mechanical-core__module">
      <path className="mechanical-core__plate" d="M72 18H100L110 28V43H85L72 34Z" />
      <path className="mechanical-core__latch" d="M72 31H80L89 38H104V47H83L72 37Z" />
      <path className="mechanical-core__vent" d="M82 23V28M88 23V30M94 23V30" /><Fastener x={103} y={27} />
    </g>
    <g className="core-module module-c mechanical-core__module">
      <path className="mechanical-core__plate" d="M18 85H43L56 94V110H28L18 100Z" />
      <path className="mechanical-core__latch" d="M24 81H45L56 91V97H48L39 90H24Z" />
      <path className="mechanical-core__vent" d="M34 98V105M40 98V105M46 100V105" /><Fastener x={25} y={101} />
    </g>
    <g className="core-module module-d mechanical-core__module">
      <path className="mechanical-core__plate" d="M85 85H110V100L100 110H72V94Z" />
      <path className="mechanical-core__latch" d="M83 81H104V90H89L80 97H72V91Z" />
      <path className="mechanical-core__vent" d="M82 100V105M88 98V105M94 98V105" /><Fastener x={103} y={101} />
    </g>
    <g className="mechanical-core__gear">
      <path className="mechanical-core__gear-ring" d={gearPath(64, 64, 27, 23, 20)} />
      <circle className="core-center mechanical-core__hub" cx="64" cy="64" r="16" />
      <path className="mechanical-core__hub-detail" d="M64 49V58M51 71L59 67M77 71L69 67" />
      <circle className="mechanical-core__bearing" cx="64" cy="64" r="6" />
      <circle className="mechanical-core__signal" cx="64" cy="64" r="2.5" />
    </g>
    <path className="mechanical-core__index" d="M9 49V57M119 71V79" />
  </svg>;
}

function PerforatedBeam({ x, y, length, angle = 0, className = '' }: {
  x: number; y: number; length: number; angle?: number; className?: string;
}) {
  // x/y and length describe the pin datums; material extends beyond each pin.
  const holes = Math.max(2, Math.floor(length / 14) + 1);
  return <g className={`beam-graphic__beam ${className}`} transform={`translate(${x} ${y}) rotate(${angle})`}>
    <path className="beam-graphic__plate" d={`M-8 -4L-5 -7H${length + 5}L${length + 8} -4V4L${length + 5} 7H-5L-8 4Z`} />
    <path className="beam-graphic__fold" d={`M-4 -4H${length + 4}`} />
    {Array.from({ length: holes }, (_, i) => <circle className="beam-graphic__hole" key={i}
      cx={i * length / (holes - 1)} cy="0" r="2.4" />)}
  </g>;
}

function SchematicWheel({ x, y }: { x: number; y: number }) {
  return <g className="beam-graphic__wheel" transform={`translate(${x} ${y})`}>
    <path className="beam-graphic__tread" d={gearPath(0, 0, 27, 25, 28)} />
    <circle className="beam-graphic__rim" r="18" />
    {[0, 60, 120].map(angle => <path key={angle} d="M-15 0H15" transform={`rotate(${angle})`} />)}
    <Fastener x={0} y={0} radius={4} />
  </g>;
}

function StrategySchematic() {
  return <>
    <g className="beam-graphic__construction"><path d="M24 109H376M64 30V190M195 30V190M337 30V190" /></g>
    <PerforatedBeam x={39} y={48} length={311} /><PerforatedBeam x={39} y={172} length={311} />
    <path className="beam-graphic__route" d="M64 109H170M220 109H250L278 73H337M250 109L278 145H337" />
    <g className="beam-graphic__terminal"><path d="M51 96H77V122H51Z" /><circle cx="64" cy="109" r="5" /></g>
    <path className="beam-graphic__decision" d={gearPath(195, 109, 27, 23, 16)} />
    <path className="beam-graphic__choice" d="M195 97L207 109L195 121L183 109Z" />
    {[73, 145].map(y => <g className="beam-graphic__terminal" key={y}>
      <path d={`M326 ${y - 11}H344L350 ${y - 5}V${y + 5}L344 ${y + 11}H326Z`} />
      <Fastener x={337} y={y} radius={4} />
    </g>)}
    <g className="beam-graphic__annotations"><text x="45" y="145">01 / INTENT</text><text x="165" y="155">02 / CHOOSE</text>
      <text x="315" y="53">A</text><text x="315" y="129">B</text></g>
    <Fastener x={39} y={48} /><Fastener x={350} y={48} /><Fastener x={39} y={172} /><Fastener x={350} y={172} />
  </>;
}

function RobotSchematic() {
  const linkLength = Math.hypot(115, 32);
  const linkAngle = Math.atan2(-32, 115) * 180 / Math.PI;
  return <>
    <g className="beam-graphic__construction"><path d="M24 196H376M124 26V194M239 26V156M42 168H354" />
      <path d="M239 60A119.4 119.4 0 0 0 193 1" strokeDasharray="3 5" /></g>
    <path className="beam-graphic__chassis" d="M64 135H305L325 155V169H54V145Z" />
    <PerforatedBeam x={62} y={148} length={254} />
    <PerforatedBeam x={124} y={92} length={66} angle={90} />
    <PerforatedBeam x={124} y={92} length={linkLength} angle={linkAngle} className="beam-graphic__link" />
    <PerforatedBeam x={124} y={125} length={linkLength} angle={linkAngle} className="beam-graphic__link" />
    <PerforatedBeam x={239} y={60} length={33} angle={90} />
    <path className="beam-graphic__tool" d="M246 67H265L281 54H303V62H286L273 77V82L286 97H303V105H281L265 92H246Z" />
    <path className="beam-graphic__tool-detail" d="M291 54V62M297 54V62M291 97V105M297 97V105" />
    {[[124, 92], [124, 125], [239, 60], [239, 93]].map(([x, y]) => <Fastener key={`${x}-${y}`} x={x} y={y} radius={4} />)}
    <SchematicWheel x={102} y={168} /><SchematicWheel x={286} y={168} />
    <g className="beam-graphic__annotations"><text x="147" y="60">LINK / JOINT</text><text x="282" y="36">TOOL</text>
      <path d="M291 40V48M169 64L174 75" /></g>
  </>;
}

export interface BeamGraphicProps { kind: 'strategy' | 'robot'; className?: string }

/** An editorial mechanism illustration, never a preview of generated CAD. */
export function BeamGraphic({ kind, className = '' }: BeamGraphicProps) {
  const titleId = useId();
  return <figure className={`beam-graphic beam-graphic--${kind} ${className}`.trim()}>
    <svg viewBox="0 0 400 220" role="img" aria-labelledby={titleId} focusable="false">
      <title id={titleId}>{kind === 'strategy' ? 'Planning schematic: one intent branches into two choices' : 'Mechanism schematic: wheeled chassis, parallel links, and a jointed tool'}</title>
      {kind === 'strategy' ? <StrategySchematic /> : <RobotSchematic />}
    </svg>
    <figcaption><span>{kind === 'strategy' ? 'Planning schematic' : 'Mechanism schematic'}</span><span>ILLUSTRATION</span></figcaption>
  </figure>;
}

export interface StatusBadgeProps extends ComponentPropsWithoutRef<'span'> {
  children: ReactNode;
  tone?: 'neutral' | 'active' | 'warning' | 'danger';
}

export function StatusBadge({ children, tone = 'neutral', className = '', ...props }: StatusBadgeProps) {
  return <span {...props} className={`mechanical-status ${className}`.trim()} data-tone={tone}>
    <span className="mechanical-status__lamp" aria-hidden="true" />{children}
  </span>;
}

/** Original line-drawn product lettering; no font or third-party artwork. */
export function TachyonWordmark({ className = '' }: { className?: string }) {
  const titleId = useId();
  return <svg className={`tachyon-wordmark ${className}`.trim()} viewBox="0 0 320 52" role="img" aria-labelledby={titleId}>
    <title id={titleId}>Tachyon</title>
    <path className="tachyon-wordmark__letters" d="M5 10H39M22 10V42M48 42V18L56 10H71V42M48 29H71M110 10H92L84 18V34L92 42H110M124 10V42M124 26H147M147 10V42M161 10L173 26L185 10M173 26V42M209 10H224L232 18V34L224 42H209L201 34V18ZM248 42V10L275 42V10M290 42H314" />
    <path className="tachyon-wordmark__cuts" d="M18 10H26M56 29H63M209 10H216M209 42H216M257 22L263 29" />
  </svg>;
}
