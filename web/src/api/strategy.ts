import { parseCatalog, type ComponentDefinition, type Vector3M } from './contracts';
/** The saved v2 handoff is kept intact; the UI reads only documented fields. */
export const OVERRIDE_COMPETITION_ID = 'v5-override-v2.1' as const;
export const OVERRIDE_MANUAL_URL = 'https://manuals.vex.com/v5/override/v2.1/game/?view=core';
export interface StrategyStatus {
  available: boolean;
  competitionId: typeof OVERRIDE_COMPETITION_ID;
  environmentId: string;
  reason?: string;
  policyParameterHash?: string;
}
export interface StrategyEvent {
  action: string;
  start_s: number;
  end_s: number;
  from_xy: [number, number];
  to_xy: [number, number];
  success: boolean;
  score_before: number;
  score_after: number;
  [key: string]: unknown;
}
export interface CapabilityRequirements {
  hardMinimums: Record<string, number>;
  targets: Record<string, number>;
  basis?: string;
  minimumScope?: string;
  [key: string]: unknown;
}
export interface StrategySpec {
  schemaVersion: 2;
  kind: 'tachyon.strategy_spec';
  id: string;
  competition: { id: string; environmentId: string };
  strategyFamily: string;
  performanceDomain: 'abstract_simulation_only';
  objectives: { objective: string; meanModeledPoints: number }[];
  scoringPriorities: { objective: string; meanModeledPoints: number }[];
  behavior: {
    conditionalPreferences: {
      when: Record<string, string | number | boolean>;
      observedDecisions: number;
      meanNeuralActionProbabilities: Record<string, number>;
      selectedActionCounts: Record<string, number>;
    }[];
    [key: string]: unknown;
  };
  representativeSequences: { events: StrategyEvent[]; modeledScore: number; selection: string; [key: string]: unknown }[];
  mechanicalRequirements: { id: string; supports: string[]; requirements: string[]; [key: string]: unknown }[];
  capabilityRequirements: CapabilityRequirements;
  policy: { experimentId: string; sourceCommit: string; checkpoint: { parameterHash: string; sha256: string; path: string }; [key: string]: unknown };
  limitations: string[];
  [key: string]: unknown;
}
export interface ArchitectureProposal {
  id: string;
  alternative: string;
  strategyId: string;
  strategyFamily: string;
  performanceDomain: 'abstract_simulation_only';
  subsystems: {
    id: string;
    mechanismIntent: string;
    layoutIntent: Record<string, unknown>;
    actuationIntent: Record<string, unknown>;
    qualificationStatus: string;
  }[];
  capabilityConstraints: CapabilityRequirements;
  qualificationRequired: string[];
  engineeringAssumptions: string[];
  bindingIntent: { actions: { action?: string; sourceValue?: unknown; subsystemIDs: string[]; status: string; [key: string]: unknown }[]; [key: string]: unknown };
  attachmentAndJointIntents: { parentSubsystemID: string; childSubsystemID: string; jointIntent: string; mountZoneIntent: string }[];
  completeRobot: false;
  cadGenerated: false;
  physicalPerformanceVerified: false;
  [key: string]: unknown;
}
export interface StrategySession {
  id: string;
  competition: { id: typeof OVERRIDE_COMPETITION_ID; environmentId: string; [key: string]: unknown };
  strategyFamily: string;
  source: 'trained_ppo';
  performanceDomain: 'abstract_simulation_only';
  spec: StrategySpec;
  architectures: ArchitectureProposal[];
  rollout: {
    events: StrategyEvent[];
    score: number;
    pointsByObjective: Record<string, number>;
    capabilities: Record<string, unknown>;
    actionFrequencies: Record<string, number>;
    policyParameterHash: string;
    simulationOnly: true;
    evidence?: { episodeSeed?: number; [key: string]: unknown };
    [key: string]: unknown;
  };
  limitations: string[];
}
/** CAD payloads remain opaque to the strategy view; only the renderer interprets instances/bindings. */
export interface AssemblyRevisionJSON {
  id: string;
  parentRevisionId: string | null;
  engineeringHash: string;
  assembly: {
    designId: string;
    configurationId: string;
    units: 'm';
    upAxis: 'Y';
    matrixLayout: 'column-major';
    instances: { id: string; componentId: string; subsystemId: string; parentId: string | null; transform: { matrix: number[] } }[];
    subsystems: { id: string; name: string }[];
    [key: string]: unknown;
  };
  [key: string]: unknown;
}
export interface BindingSnapshot {
  designId: string;
  strategyId: string;
  revisionId: string;
  engineeringHash: string;
  bindingsHash: string;
  actions: {
    actionId: string;
    subsystemId: string;
    instanceIds: string[];
    componentIds: string[];
    jointIds: string[];
    anchors: { id: string; instanceId: string; componentId: string; worldPointM: Vector3M; [key: string]: unknown }[];
    capabilityStatus: string;
    capabilityReason: string;
  }[];
  [key: string]: unknown;
}
export interface DesignSession {
  designId: string;
  architectureId: string;
  strategyId: string;
  status: 'blocked' | 'partial' | 'ready';
  missing: { role: string; code: string; message: string }[];
  canEdit: boolean;
  revisionId: string | null;
  accepted: AssemblyRevisionJSON | null;
  candidate: AssemblyRevisionJSON | null;
  bindings: BindingSnapshot | null;
  candidateBindings: BindingSnapshot | null;
  worldTransforms: Record<string, number[]>;
  candidateWorldTransforms: Record<string, number[]>;
  components: ComponentDefinition[];
  qualification: { completeRobot: boolean; [key: string]: unknown };
  plan: Record<string, unknown>;
  [key: string]: unknown;
}
export type DesignRealization = DesignSession;
export type RealizationState =
  | { state: 'idle' }
  | { state: 'loading'; architectureId: string }
  | { state: 'failed'; architectureId: string; message: string }
  | { state: 'loaded'; architectureId: string; result: DesignRealization };

const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const str = (v: unknown): v is string => typeof v === 'string' && v.length > 0;
const number = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(str);
const numbers = (v: unknown): v is Record<string, number> => object(v) && Object.values(v).every(number);
const hash = (v: unknown) => str(v) && /^[a-f0-9]{64}$/i.test(v);
const xy = (v: unknown) => Array.isArray(v) && v.length === 2 && v.every(number);
function invalid(): never { throw new Error('The server returned an incompatible strategy or architecture response. Retry after checking the server version.'); }
function requirements(v: unknown): v is CapabilityRequirements {
  return object(v) && numbers(v.hardMinimums) && numbers(v.targets);
}
function events(v: unknown): v is StrategyEvent[] {
  return Array.isArray(v) && v.every(e => object(e) && str(e.action) && number(e.start_s) && number(e.end_s) &&
    e.end_s >= e.start_s && xy(e.from_xy) && xy(e.to_xy) && typeof e.success === 'boolean' && number(e.score_before) && number(e.score_after));
}
export function parseStrategyStatus(v: unknown): StrategyStatus {
  if (!object(v) || typeof v.available !== 'boolean' || v.competitionId !== OVERRIDE_COMPETITION_ID || !str(v.environmentId) ||
    (v.reason !== undefined && !str(v.reason)) || (v.policyParameterHash !== undefined && !hash(v.policyParameterHash))) return invalid();
  return v as unknown as StrategyStatus;
}
export function parseStrategySession(v: unknown): StrategySession {
  if (!object(v) || !str(v.id) || !object(v.competition) || v.competition.id !== OVERRIDE_COMPETITION_ID || !str(v.competition.environmentId) ||
    v.source !== 'trained_ppo' || v.performanceDomain !== 'abstract_simulation_only' || !str(v.strategyFamily) || !strings(v.limitations)) return invalid();
  const s = v.spec;
  if (!object(s) || s.schemaVersion !== 2 || s.kind !== 'tachyon.strategy_spec' || !str(s.id) || s.id !== v.id || s.strategyFamily !== v.strategyFamily ||
    s.performanceDomain !== v.performanceDomain || !object(s.competition) || s.competition.id !== v.competition.id ||
    s.competition.environmentId !== v.competition.environmentId || !requirements(s.capabilityRequirements) || !strings(s.limitations)) return invalid();
  for (const rows of [s.objectives, s.scoringPriorities]) if (!Array.isArray(rows) || rows.some(r => !object(r) || !str(r.objective) || !number(r.meanModeledPoints))) return invalid();
  if (!object(s.behavior) || !Array.isArray(s.behavior.conditionalPreferences) || s.behavior.conditionalPreferences.some(c => !object(c) ||
    !object(c.when) || !Object.values(c.when).every(x => typeof x === 'boolean' || str(x) || number(x)) || !number(c.observedDecisions) ||
    !numbers(c.meanNeuralActionProbabilities) || !numbers(c.selectedActionCounts))) return invalid();
  if (!Array.isArray(s.representativeSequences) || s.representativeSequences.some(t => !object(t) || !events(t.events) || !number(t.modeledScore) || !str(t.selection)) ||
    !Array.isArray(s.mechanicalRequirements) || s.mechanicalRequirements.some(m => !object(m) || !str(m.id) || !strings(m.supports) || !strings(m.requirements)) ||
    !object(s.policy) || !str(s.policy.experimentId) || !str(s.policy.sourceCommit) || !object(s.policy.checkpoint) || !hash(s.policy.checkpoint.parameterHash)) return invalid();
  if (!Array.isArray(v.architectures)) return invalid();
  const ids = new Set<string>();
  for (const a of v.architectures) {
    if (!object(a) || !str(a.id) || ids.has(a.id) || !str(a.alternative) || a.strategyId !== s.id || a.strategyFamily !== v.strategyFamily ||
      a.performanceDomain !== v.performanceDomain || a.completeRobot !== false || a.cadGenerated !== false || a.physicalPerformanceVerified !== false ||
      !strings(a.qualificationRequired) || !strings(a.engineeringAssumptions) || !requirements(a.capabilityConstraints) ||
      !Array.isArray(a.subsystems) || !a.subsystems.length || a.subsystems.some(x => !object(x) || !str(x.id) || !str(x.mechanismIntent) || !object(x.layoutIntent) || !object(x.actuationIntent) || !str(x.qualificationStatus)) ||
      !object(a.bindingIntent) || !Array.isArray(a.bindingIntent.actions) || a.bindingIntent.actions.some(b => !object(b) || (b.action !== undefined && !str(b.action)) || !strings(b.subsystemIDs) || !str(b.status)) ||
      !Array.isArray(a.attachmentAndJointIntents) || a.attachmentAndJointIntents.some(j => !object(j) || !str(j.parentSubsystemID) || !str(j.childSubsystemID) || !str(j.jointIntent) || !str(j.mountZoneIntent))) return invalid();
    ids.add(a.id);
  }
  const r = v.rollout;
  if (!object(r) || r.simulationOnly !== true || !events(r.events) || !number(r.score) || !numbers(r.pointsByObjective) || !object(r.capabilities) ||
    !numbers(r.actionFrequencies) || Object.values(r.actionFrequencies).some(f => f < 0 || f > 1) ||
    (r.evidence !== undefined && (!object(r.evidence) || (r.evidence.episodeSeed !== undefined && !number(r.evidence.episodeSeed)))) ||
    !hash(r.policyParameterHash) || r.policyParameterHash !== s.policy.checkpoint.parameterHash) return invalid();
  return v as unknown as StrategySession;
}
export function parseDesignRealization(v: unknown): DesignRealization {
  if (!object(v) || !str(v.designId) || !str(v.architectureId) || !str(v.strategyId) || !['blocked', 'partial', 'ready'].includes(String(v.status)) ||
    typeof v.canEdit !== 'boolean' || !(v.revisionId === null || str(v.revisionId)) || !Array.isArray(v.missing) ||
    v.missing.some(m => !object(m) || !str(m.role) || !str(m.code) || !str(m.message)) || !object(v.qualification) || typeof v.qualification.completeRobot !== 'boolean' || !object(v.plan)) throw new Error('The server returned an incompatible CAD realization response.');
  const matrix = (m: unknown) => Array.isArray(m) && m.length === 16 && m.every(number);
  for (const key of ['worldTransforms', 'candidateWorldTransforms']) if (!object(v[key]) || !Object.values(v[key]).every(matrix)) return invalid();
  for (const key of ['accepted', 'candidate']) {
    const r = v[key];
    if (r === null) continue;
    if (!object(r) || !str(r.id) || !hash(r.engineeringHash) || !object(r.assembly) || r.assembly.designId !== v.designId ||
      r.assembly.units !== 'm' || r.assembly.upAxis !== 'Y' || r.assembly.matrixLayout !== 'column-major' ||
      !Array.isArray(r.assembly.instances) || r.assembly.instances.some(i => !object(i) || !str(i.id) || !str(i.componentId) || !str(i.subsystemId) || !object(i.transform) || !matrix(i.transform.matrix)) ||
      !Array.isArray(r.assembly.subsystems) || r.assembly.subsystems.some(s => !object(s) || !str(s.id) || !str(s.name))) return invalid();
  }
  if (object(v.accepted) && v.accepted.id !== v.revisionId || v.accepted === null && v.revisionId !== null) return invalid();
  for (const [key, revision] of [['bindings', 'accepted'], ['candidateBindings', 'candidate']]) {
    const b = v[key], r = v[revision];
    if (b === null) continue;
    if (!object(b) || !object(r) || b.designId !== v.designId || b.strategyId !== v.strategyId || b.revisionId !== r.id || b.engineeringHash !== r.engineeringHash ||
      !Array.isArray(b.actions) || b.actions.some(a => !object(a) || !str(a.actionId) || !strings(a.instanceIds) || !str(a.subsystemId) || !Array.isArray(a.anchors))) return invalid();
  }
  parseCatalog({ profile: 'user_provided_local', components: v.components, blockers: [] });
  if (v.qualification.completeRobot && (v.status !== 'ready' || !object(v.accepted) ||
    v.qualification.hardwareQualified !== true || v.qualification.physicalPerformanceVerified !== false ||
    v.qualification.testFixtureOnly === true ||
    (v.components as { geometryClass?: string }[]).some(c => c.geometryClass === 'test_fixture') ||
    !object(v.qualification.robotReport) || v.qualification.robotReport.revisionId !== v.accepted.id ||
    v.qualification.robotReport.engineeringHash !== v.accepted.engineeringHash ||
    v.qualification.robotReport.completeRobot !== true ||
    (v.candidate !== null && (!object(v.candidate) || !object(v.qualification.candidateRobotReport) ||
      v.qualification.candidateRobotReport.revisionId !== v.candidate.id ||
      v.qualification.candidateRobotReport.engineeringHash !== v.candidate.engineeringHash ||
      v.qualification.candidateRobotReport.completeRobot !== true)))) return invalid();
  if (v.status === 'ready' && !v.qualification.completeRobot) return invalid();
  if (v.canEdit && (v.status === 'blocked' || v.accepted === null || !str(v.revisionId))) return invalid();
  return v as unknown as DesignRealization;
}
export const parseDesignSession = parseDesignRealization;

const labels: Record<string, string> = {
  low_quadrant_cycles: 'Low quadrant scoring cycles', alliance_pin_halves: 'Alliance Pin scoring halves', terminal_midfield: 'Finish at midfield',
  owned_yellow_pin_halves: 'Owned yellow Pin scoring halves', move_to_supply0: 'Travel to supply 1', move_to_supply1: 'Travel to supply 2',
  move_to_goal0: 'Approach low goal', move_to_goal1: 'Approach elevated goal', move_to_midfield: 'Travel to midfield',
  acquire_alliance: 'Acquire an alliance Pin', acquire_yellow: 'Acquire a yellow Pin', acquire_cup: 'Acquire a Cup independently',
  place_alliance: 'Place an alliance Pin', place_yellow: 'Place a yellow Pin', place_cup: 'Prepare the stack with a Cup',
  park_and_wait: 'Park and wait', wait: 'Wait', toggle: 'Operate toggle', pin_intake: 'Pin intake', pin_transfer: 'Pin transfer',
  cup_cradle: 'Independent Cup cradle', stack_interface: 'Stack alignment', scorer: 'Scoring mechanism',
  driveSpeedMps: 'Drive speed', turnSeconds: 'Turning time', reachM: 'Tool reach', acquisitionSeconds: 'Acquisition time',
  placementSeconds: 'Placement time', acquisitionSuccessProbability: 'Acquisition success', placementSuccessProbability: 'Placement success',
  cycleSeconds: 'Cycle time', pinCapacity: 'Pin capacity', cupCapacity: 'Independent Cup capacity',
};
export function readable(value: string): string {
  return labels[value] ?? value.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
}
export function formatNumber(value: number): string { return new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(value); }
export function capabilityValue(key: string, value: number): string {
  if (/Probability$/.test(key)) return `${formatNumber(value * 100)}%`;
  const unit = /Mps$/.test(key) ? ' m/s' : /Seconds$/.test(key) ? ' s' : /M$/.test(key) ? ' m' : '';
  return `${new Intl.NumberFormat('en', { maximumFractionDigits: 3 }).format(value)}${unit}`;
}
