import { beforeEach,expect,it,vi } from 'vitest';
import { api } from './client';
import { loadDesignCatalog,parseDesignCatalog,type DesignCatalog } from './designCatalog';

vi.mock('./client',()=>({api:{get:vi.fn()}}));
beforeEach(()=>{vi.mocked(api.get).mockReset();});

// Navigation/availability metadata only; never CAD or permission evidence.
function fixture():DesignCatalog {
  return {schemaVersion:1,kind:'tachyon.design_catalog',canGenerateAdditionalArchitectures:false,
    architectures:[{architectureId:'fixed-A',alternative:'A',recipeAvailable:true,recipeKind:'authored_component_recipe',
      requestedPlacements:474,roleIds:['scorer','cup_cradle'],qualification:'not_checked'},
    {architectureId:'fixed-B',alternative:'B',recipeAvailable:false,recipeKind:'none',
      requestedPlacements:0,roleIds:[],qualification:'not_checked'}],
    saved:[{designId:'saved-design',architectureId:'fixed-A',strategyId:'fixed-strategy',revisionId:'accepted-revision',hasCandidate:true},
      {designId:'blocked-observation',architectureId:'fixed-B',strategyId:'fixed-strategy',revisionId:null,hasCandidate:false}]};
}

it('loads only the read-only design catalog route and forwards cancellation',async()=>{
  const value=fixture(),controller=new AbortController();
  vi.mocked(api.get).mockResolvedValue(value);
  await expect(loadDesignCatalog(controller.signal)).resolves.toEqual(value);
  expect(api.get).toHaveBeenCalledExactlyOnceWith('/api/designs/catalog',controller.signal);
  expect(value.architectures[0].qualification).toBe('not_checked');
  expect(value.canGenerateAdditionalArchitectures).toBe(false);
});

it('accepts an empty index without inventing recipes, saved builds or readiness',()=>{
  const value={...fixture(),architectures:[],saved:[]};
  expect(parseDesignCatalog(value)).toEqual(value);
});

it.each([
  ['wrong version',(value:Record<string,unknown>)=>{value.schemaVersion=2;}],
  ['wrong kind',(value:Record<string,unknown>)=>{value.kind='raw-private-recipe';}],
  ['unsupported generator',(value:Record<string,unknown>)=>{value.canGenerateAdditionalArchitectures=true;}],
  ['invalid architectures',(value:Record<string,unknown>)=>{value.architectures={};}],
  ['invalid saved builds',(value:Record<string,unknown>)=>{value.saved=null;}],
] as const)('rejects an incompatible root: %s',(_,damage)=>{
  const value=fixture() as unknown as Record<string,unknown>;damage(value);
  expect(()=>parseDesignCatalog(value)).toThrow('catalog is unavailable');
});

it.each([
  ['readiness promoted from metadata',{qualification:'ready'}],
  ['negative placement count',{requestedPlacements:-1}],
  ['fractional placement count',{requestedPlacements:1.5}],
  ['coerced placement count',{requestedPlacements:'474'}],
  ['coerced recipe availability',{recipeAvailable:'true'}],
  ['unknown recipe kind',{recipeKind:'generated_and_qualified'}],
  ['non-string roles',{roleIds:[true]}],
] as const)('rejects an invalid availability record: %s',(_,damage)=>{
  const value=fixture();Object.assign(value.architectures[0],damage);
  expect(()=>parseDesignCatalog(value)).toThrow('availability record is invalid');
});

it('rejects duplicate architecture identities instead of ambiguously resolving design availability',()=>{
  const value=fixture();value.architectures[1].architectureId=value.architectures[0].architectureId;
  expect(()=>parseDesignCatalog(value)).toThrow('availability record is invalid');
});

it.each([
  {strategyId:null},{revisionId:false},{hasCandidate:'yes'},{designId:undefined},
])('rejects malformed saved navigation metadata %j',damage=>{
  const value=fixture();Object.assign(value.saved[0],damage);
  expect(()=>parseDesignCatalog(value)).toThrow('saved-design record is invalid');
});

it('propagates index failures so the workspace can use its optional-index fallback',async()=>{
  vi.mocked(api.get).mockRejectedValue(new Error('Read-only index offline'));
  await expect(loadDesignCatalog()).rejects.toThrow('Read-only index offline');
});
