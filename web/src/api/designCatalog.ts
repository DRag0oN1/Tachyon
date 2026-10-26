import { api } from './client';
export interface DesignCatalog {
  schemaVersion:1;kind:'tachyon.design_catalog';
  architectures:{architectureId:string;alternative:string;recipeAvailable:boolean;recipeKind:'authored_component_recipe'|'none';requestedPlacements:number;roleIds:string[];qualification:'not_checked'}[];
  saved:{designId:string;architectureId:string;strategyId:string;revisionId:string|null;hasCandidate:boolean}[];
  canGenerateAdditionalArchitectures:false;
}
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
export function parseDesignCatalog(value:unknown):DesignCatalog {
  if(!object(value)||value.schemaVersion!==1||value.kind!=='tachyon.design_catalog'||value.canGenerateAdditionalArchitectures!==false||!Array.isArray(value.architectures)||!Array.isArray(value.saved))throw new Error('The saved-design catalog is unavailable.');
  const ids=new Set<string>();
  for(const row of value.architectures){
    if(!object(row)||typeof row.architectureId!=='string'||ids.has(row.architectureId)||typeof row.alternative!=='string'||typeof row.recipeAvailable!=='boolean'||!['authored_component_recipe','none'].includes(String(row.recipeKind))||typeof row.requestedPlacements!=='number'||!Number.isInteger(row.requestedPlacements)||row.requestedPlacements<0||!Array.isArray(row.roleIds)||!row.roleIds.every(x=>typeof x==='string')||row.qualification!=='not_checked')throw new Error('A design availability record is invalid.');
    ids.add(row.architectureId);
  }
  for(const row of value.saved)if(!object(row)||typeof row.designId!=='string'||typeof row.architectureId!=='string'||typeof row.strategyId!=='string'||!(row.revisionId===null||typeof row.revisionId==='string')||typeof row.hasCandidate!=='boolean')throw new Error('A saved-design record is invalid.');
  return value as unknown as DesignCatalog;
}
export const loadDesignCatalog=(signal?:AbortSignal)=>api.get('/api/designs/catalog',signal).then(parseDesignCatalog);
