export type Theme = 'snap' | 'shift';
export type { ArchitectureProposal, AssemblyRevisionJSON, BindingSnapshot, DesignRealization, DesignSession, StrategySession, StrategySpec, StrategyStatus } from './strategy';
export type Mode = 'simple' | 'advanced';
export interface Preferences { theme: Theme; mode: Mode }
export interface Workspace { preferences: Preferences; activeComponentId: string | null }
export type WorkspacePatch = { preferences?: Partial<Preferences>; activeComponentId?: string | null };
export type Vector3M = [number, number, number];
export interface NativeNode { id: string; name: string; parentId: string | null; matrix: number[]; hasMesh: boolean }
export interface ComponentDefinition {
  id: string;
  name: string;
  sku: string | null;
  originKind: 'manufacturer_cad' | 'community_component_model' | 'tachyon_authored';
  geometryClass: 'verified_imported_component' | 'conceptual' | 'placeholder' | 'test_fixture';
  sourceUrl: string;
  sourceSha256: string;
  meshSha256: string;
  meshUrl: string;
  boundsM: { min: Vector3M; max: Vector3M };
  solidCount: number;
  rightsStatus: 'qualified_for_declared_use' | 'unverified' | 'disallowed';
  ports: unknown[];
  nativeHierarchy?: NativeNode[];
  conversion?: Record<string, unknown>;
  attribution?: string;
  completeRobot?: false;
  referenceOnly?: boolean;
  geometryValidation?: { status: 'valid' | 'source_defects'; nativeBrepValid: boolean; invalidDefinitionCount: number | null; invalidComponentInstances: { path: string; name: string; definitionName: string }[]; qualifiedForRobotGeneration: boolean; limitations: string[] };
  [metadata: string]: unknown;
}
export interface CatalogBlocker { code: string; message: string; componentId?: string }
export interface Catalog {
  components: ComponentDefinition[];
  blockers: CatalogBlocker[];
  profile: 'user_provided_local';
}
export interface Capabilities {
  canInspect: boolean;
  canGenerateStrategy: boolean;
  canGenerateRobot: false;
  canEdit: false;
  reasons: string[];
}
export interface Health {
  status: 'ok'; version: '0.1.0'; cadProfile: 'user_provided_local'; providerConfigured: boolean;
}
export interface Selection {
  // A source mesh is catalog-scoped, not an accepted robot revision.
  catalogMeshSha256: string;
  componentId: string;
  meshName?: string;
  nativeNodeId?: string;
}

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const string = (v: unknown): v is string => typeof v === 'string';
const hash = (v: unknown): v is string => string(v) && /^[a-f0-9]{64}$/i.test(v);
const vec = (v: unknown): v is Vector3M =>
  Array.isArray(v) && v.length === 3 && v.every(n => typeof n === 'number' && Number.isFinite(n));
const oneOf = (v: unknown, choices: string[]) => string(v) && choices.includes(v);
function invalid(): never { throw new Error('The server returned an incompatible workspace contract.'); }

export function parseWorkspace(v: unknown): Workspace {
  if (!record(v) || !record(v.preferences) ||
    !oneOf(v.preferences.theme, ['snap', 'shift']) || !oneOf(v.preferences.mode, ['simple', 'advanced']) ||
    !(v.activeComponentId === null || string(v.activeComponentId))) return invalid();
  return v as unknown as Workspace;
}
export function parseHealth(v: unknown): Health {
  if (!record(v) || v.status !== 'ok' || v.version !== '0.1.0' ||
    v.cadProfile !== 'user_provided_local' || typeof v.providerConfigured !== 'boolean') return invalid();
  return v as unknown as Health;
}
export function parseCapabilities(v: unknown): Capabilities {
  if (!record(v) || typeof v.canInspect !== 'boolean' || typeof v.canGenerateStrategy !== 'boolean' ||
    v.canGenerateRobot !== false || v.canEdit !== false || !Array.isArray(v.reasons) || !v.reasons.every(string)) return invalid();
  return v as unknown as Capabilities;
}
export function parseCatalog(v: unknown): Catalog {
  if (!record(v) || v.profile !== 'user_provided_local' || !Array.isArray(v.components) || !Array.isArray(v.blockers)) return invalid();
  const ids = new Set<string>();
  for (const c of v.components) {
    if (!record(c) || !string(c.id) || !c.id || ids.has(c.id) || !string(c.name) || !(c.sku === null || string(c.sku)) ||
      !oneOf(c.originKind, ['manufacturer_cad', 'community_component_model', 'tachyon_authored']) ||
      !oneOf(c.geometryClass, ['verified_imported_component', 'conceptual', 'placeholder', 'test_fixture']) ||
      !oneOf(c.rightsStatus, ['qualified_for_declared_use', 'unverified', 'disallowed']) ||
      !string(c.sourceUrl) || !hash(c.sourceSha256) || !hash(c.meshSha256) ||
      c.meshUrl !== `/api/assets/${c.meshSha256}.glb` || !record(c.boundsM) ||
      !vec(c.boundsM.min) || !vec(c.boundsM.max) ||
      !c.boundsM.min.every((n, i) => n <= (c.boundsM as { max: Vector3M }).max[i]) ||
      !Number.isInteger(c.solidCount) || (c.solidCount as number) < 1 || !Array.isArray(c.ports)) return invalid();
    ids.add(c.id);
    if (c.completeRobot !== undefined && c.completeRobot !== false) return invalid();
    if (c.nativeHierarchy !== undefined && (!Array.isArray(c.nativeHierarchy) || c.nativeHierarchy.some(n =>
      !record(n) || !string(n.id) || !string(n.name) || !(n.parentId === null || string(n.parentId)) ||
      typeof n.hasMesh !== 'boolean' || !Array.isArray(n.matrix) || n.matrix.length !== 16 ||
      !n.matrix.every(x => typeof x === 'number' && Number.isFinite(x))))) return invalid();
  }
  for (const b of v.blockers) {
    if (!record(b) || !string(b.code) || !string(b.message) ||
      !(b.componentId === undefined || string(b.componentId))) return invalid();
  }
  return v as unknown as Catalog;
}
export function isInspectable(c: ComponentDefinition): boolean {
  return c.rightsStatus === 'qualified_for_declared_use' &&
    (c.geometryClass === 'verified_imported_component' ||
      (c.geometryClass === 'test_fixture' && c.originKind === 'tachyon_authored'));
}
export function geometryLabel(c: ComponentDefinition): string {
  if (c.geometryClass === 'test_fixture') return 'Tachyon-authored · non-VEX test fixture';
  if (c.geometryClass !== 'verified_imported_component') return `${c.geometryClass} · unavailable for CAD inspection`;
  return c.originKind === 'manufacturer_cad' ? 'Manufacturer source component' :
    c.originKind === 'community_component_model' ? 'Community source component' : 'Tachyon-authored source component';
}
