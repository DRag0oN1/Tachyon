import { useId } from 'react';
import type { ArchitectureProposal } from '../api/strategy';

export function architectureName(architecture:ArchitectureProposal){
  const scorer=architecture.subsystems.find(s=>s.id==='scorer')?.mechanismIntent??'';
  return scorer.includes('four_bar')?'Linked four-bar':scorer.includes('elevator')?'Guided elevator':'Mechanical concept';
}
/** An original diagram of declared subsystem intents. Never source CAD or a fit check. */
export function ArchitectureDrawing({architecture,activeActionId,compact=false}:{architecture:ArchitectureProposal;activeActionId?:string|null;compact?:boolean}){
  const id=useId().replaceAll(':','');
  const subsystem=(name:string)=>architecture.subsystems.find(s=>s.id===name);
  const scorer=subsystem('scorer')?.mechanismIntent??'';
  const fourBar=scorer.includes('four_bar'),elevator=scorer.includes('elevator');
  const rollers=subsystem('pin_intake')?.mechanismIntent.includes('roller');
  const wheelCount=Number(subsystem('drive')?.layoutIntent.wheelCount);
  const active=new Set(architecture.bindingIntent.actions.filter(a=>(a.action??a.sourceValue)===activeActionId).flatMap(a=>a.subsystemIDs));
  const beam=(x:number,y:number,width:number,rotation=0)=><g transform={`translate(${x} ${y}) rotate(${rotation})`}><path d={`M0 -7H${width}V7H0Z`} fill="url(#${id}-steel)"/>{Array.from({length:Math.floor(width/16)},(_,n)=><circle key={n} cx={8+n*16} cy="0" r="2.3"/>)}</g>;
  return <svg viewBox="0 0 560 340" role="img" className={`architecture-drawing ${compact?'is-compact':''}`} aria-label={`${architectureName(architecture)} architecture ${architecture.alternative}: conceptual mechanical schematic, not CAD`} data-architecture-id={architecture.id}>
    <defs><pattern id={`${id}-grid`} width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="currentColor" opacity=".09" strokeWidth=".5"/></pattern><pattern id={`${id}-steel`} width="12" height="12" patternUnits="userSpaceOnUse"><path d="M0 12 12 0" stroke="currentColor" opacity=".1" strokeWidth="1"/></pattern><marker id={`${id}-arrow`} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="m0 0 6 3-6 3" fill="none" stroke="currentColor"/></marker></defs>
    <rect x="0" y="0" width="560" height="340" fill={`url(#${id}-grid)`} stroke="none"/>
    <path className="drawing-datum" d="M28 277H530M34 267V287M526 267V287"/>
    <g className={`drawing-drive ${active.has('drive')?'is-selected':''}`} data-subsystem="drive">
      {beam(128,244,284)}{beam(143,222,250)}
      {(wheelCount===6?[154,264,382]:[154,382]).map(x=><g key={x}><circle cx={x} cy="260" r="21"/><circle cx={x} cy="260" r="11"/><path d={`M${x-21} 260H${x+21}M${x} 239V281`}/></g>)}
      <path d="M154 260H382" strokeDasharray="4 4"/>
    </g>
    <g className={`drawing-scorer ${active.has('scorer')?'is-selected':''}`} data-subsystem="scorer">
      {fourBar?<>{beam(292,223,146,-51)}{beam(292,195,146,-51)}{beam(380,81,70,90)}{beam(286,156,76,90)}<path d="M378 79h82v-18h34M396 119h63v16h35"/>{[[292,223],[292,195],[384,109],[384,81]].map(([x,y])=><g key={`${x}-${y}`}><circle cx={x} cy={y} r="7"/><circle cx={x} cy={y} r="2"/></g>)}<path className="drawing-motion" d="M334 184q-2-53 45-84" markerEnd={`url(#${id}-arrow)`}/></>:elevator?<>{beam(324,74,155,90)}{beam(365,74,155,90)}<path d="M324 76h41M324 230h41M335 84v138m18-138v138"/><path className="drawing-carriage" d="M313 108h64v34h-64zM377 113h83v-25h34M377 138h83v16h34"/><path className="drawing-motion" d="M300 195V95" markerEnd={`url(#${id}-arrow)`}/></>:<path d="M324 223V90h40v133"/>}
    </g>
    <g className={`drawing-intake ${active.has('pin_intake')?'is-selected':''}`} data-subsystem="pin_intake">
      <path d="M149 225 101 206H64M149 240l-48-18H64"/>
      {rollers?<><circle cx="77" cy="216" r="14"/><circle cx="118" cy="230" r="14"/><path d="m71 210 12 12m29 2 12 12"/></>:<><path d="M68 201H45v18h24M88 224H45v18h43M45 219H25"/><circle cx="78" cy="213" r="5"/></>}
      <path className="drawing-motion" d="M23 248q27 3 53-5" markerEnd={`url(#${id}-arrow)`}/>
    </g>
    <g className={`drawing-transfer ${active.has('pin_transfer')?'is-selected':''}`} data-subsystem="pin_transfer"><path d="M151 207h122l28-41" strokeDasharray="5 4" markerEnd={`url(#${id}-arrow)`}/><path d="M208 197v20m10-20v20"/></g>
    <g className={`drawing-cup ${active.has('cup_cradle')?'is-selected':''}`} data-subsystem="cup_cradle"><path d="m414 206 7 30h28l7-30M420 210h30M435 236v9"/><path d="M412 200v-7h46v7"/></g>
    {!compact&&<g className="drawing-annotations"><path d="M90 205V129H26"/><text x="26" y="118">01 / {rollers?'ROLLER ACQUISITION':'JAW ACQUISITION'}</text><path d="M228 207V164h-75"/><text x="153" y="154">02 / HANDOFF INTENT</text><path d="M366 74V35h155"/><text x="344" y="25">03 / {fourBar?'LINKED LIFT':elevator?'GUIDED LIFT':'SCORER'}</text><path d="M449 223h72"/><text x="466" y="211">CUP BAY</text><text x="32" y="312">{Number.isFinite(wheelCount)?`${wheelCount} WHEEL DRIVE`:'DRIVE INTENT'} / SOURCE: ARCHITECTURE {architecture.alternative}</text><text x="32" y="328">CONCEPTUAL SCHEMATIC · NOT CAD · NOT TO SCALE</text></g>}
  </svg>;
}
