import { readable, type DesignSession, type StrategyEvent, type StrategySpec } from '../api/strategy';

export type PhaseKind = 'travel' | 'acquire' | 'place' | 'control' | 'wait' | 'action' | 'repeat' | 'finish';
export interface PlaybookPhase {
  id: string;
  kind: PhaseKind;
  title: string;
  events: StrategyEvent[];
  eventIndices: number[];
  actionIds: string[];
  primaryActionId: string;
  startS: number;
  endS: number;
  scoreChange: number;
  failures: number;
}

function kindOf(action: string): PhaseKind {
  if (action.startsWith('move_to_')) return 'travel';
  if (action.startsWith('acquire_')) return 'acquire';
  if (action.startsWith('place_')) return 'place';
  if (action === 'toggle') return 'control';
  if (action === 'wait' || action === 'park_and_wait') return 'wait';
  return 'action';
}

function titleFor(kind: PhaseKind, events: StrategyEvent[]): string {
  const ids = new Set(events.map(e => e.action));
  if (kind === 'finish') return ids.has('move_to_midfield') ? (ids.has('park_and_wait') ? 'Move to midfield and wait' : 'Move to midfield') : 'Park and wait';
  if (kind === 'repeat') return 'Repeat the supply–goal cycle';
  if (kind === 'acquire') return ids.has('acquire_cup') && (ids.has('acquire_alliance') || ids.has('acquire_yellow'))
    ? 'Acquire a Pin and Cup' : ids.has('acquire_cup') ? 'Acquire a Cup' : (ids.has('acquire_alliance') || ids.has('acquire_yellow')) ? 'Acquire a Pin' : readable(events[0].action);
  if (kind === 'place') return ids.has('place_cup') && (ids.has('place_alliance') || ids.has('place_yellow'))
    ? 'Place the Pin, prepare the Cup' : ids.has('place_cup') ? readable('place_cup') : (ids.has('place_alliance') || ids.has('place_yellow')) ? 'Place the Pin' : readable(events[0].action);
  if (kind === 'travel') {
    if (events.every(e => e.action.startsWith('move_to_supply'))) return 'Travel to supply';
    if (events.every(e => e.action.startsWith('move_to_goal'))) return 'Approach the goal';
  }
  return readable(events[0].action);
}

/** Group actual contiguous events, without adding actions, timings or outcomes.
 * A normal cycle rollout yields 4–6 phases; sparse traces stay sparse.
 */
export function buildStrategyPhases(events: readonly StrategyEvent[]): PlaybookPhase[] {
  if (!events.length) return [];
  let tail = events.length;
  while (tail > 0 && ['move_to_midfield', 'park_and_wait', 'wait'].includes(events[tail - 1].action)) tail--;
  // Waiting alone never invents an endgame. Require an observed terminal action.
  if (!events.slice(tail).some(e => e.action === 'move_to_midfield' || e.action === 'park_and_wait')) tail = events.length;
  const runs: { kind: PhaseKind; indices: number[] }[] = [];
  for (let index = 0; index < tail; index++) {
    const kind = kindOf(events[index].action);
    if (runs.at(-1)?.kind === kind) runs.at(-1)!.indices.push(index);
    else runs.push({ kind, indices: [index] });
  }
  const groups = runs.slice(0, 4);
  const rest = runs.slice(4).flatMap(run => run.indices);
  if (rest.length) {
    const actions = rest.map(i => events[i].action);
    const firstPlacement = events.findIndex(e => e.action.startsWith('place_'));
    const nextAcquisition = events.findIndex((e, i) => i > firstPlacement && e.action.startsWith('acquire_'));
    const repeat = firstPlacement >= 0 && nextAcquisition > firstPlacement &&
      events.some((e, i) => i > nextAcquisition && e.action.startsWith('place_')) &&
      actions.some(a => a.startsWith('move_to_supply')) && actions.some(a => a.startsWith('move_to_goal'));
    groups.push({ kind: repeat ? 'repeat' : 'action', indices: rest });
  }
  if (tail < events.length) groups.push({ kind: 'finish', indices: Array.from({ length: events.length - tail }, (_, i) => tail + i) });
  return groups.map(({ kind, indices }) => {
    const members = indices.map(i => events[i]);
    const actionIds = [...new Set(members.map(e => e.action))];
    const primary = kind === 'repeat' ? members.find(e => e.action.startsWith('place_'))?.action : undefined;
    return {
      id: `phase-${indices[0]}-${indices.at(-1)}`, kind, title: titleFor(kind, members),
      events: members, eventIndices: indices, actionIds, primaryActionId: primary ?? members[0].action,
      startS: members[0].start_s, endS: members.at(-1)!.end_s,
      scoreChange: members.reduce((sum, e) => sum + e.score_after - e.score_before, 0),
      failures: members.filter(e => !e.success).length,
    };
  });
}

export interface PlaybookDrawing {
  routes: { index: number; actionId: string; from: [number, number]; to: [number, number]; success: boolean }[];
  sites: { key: string; point: [number, number]; label: string }[];
  project: (point: [number, number]) => [number, number];
}

export function buildPlaybookDrawing(events: readonly StrategyEvent[]): PlaybookDrawing {
  const points = events.flatMap(e => [e.from_xy, e.to_xy]);
  const minX = points.length ? Math.min(...points.map(p => p[0])) : 0;
  const minY = points.length ? Math.min(...points.map(p => p[1])) : 0;
  const span = Math.max(.5, ...points.map(p => p[0] - minX), ...points.map(p => p[1] - minY));
  const project = (p: [number, number]): [number, number] => [44 + (p[0] - minX) / span * 214, 254 - (p[1] - minY) / span * 214];
  const sites = new Map<string, PlaybookDrawing['sites'][number]>();
  events.forEach(e => {
    if (e.action.startsWith('move_to_') && e.success) sites.set(e.to_xy.join(','), {
      key: e.to_xy.join(','), point: project(e.to_xy), label: readable(e.action).replace(/^(Travel to|Approach) /, ''),
    });
  });
  return { project, sites: [...sites.values()], routes: events.flatMap((e, index) =>
    e.from_xy.some((v, i) => v !== e.to_xy[i]) ? [{ index, actionId: e.action, from: project(e.from_xy), to: project(e.to_xy), success: e.success }] : []) };
}

export function phaseRequirements(spec: StrategySpec, phase: PlaybookPhase) {
  return spec.mechanicalRequirements.filter(r => r.supports.some(id => phase.actionIds.includes(id)));
}

/** A proposal is promoted to a link only for the exact displayed revision. */
export function phaseAssemblyLink(assembly: DesignSession | null | undefined, strategyId: string, actionId: string) {
  const revision = assembly?.candidate ?? assembly?.accepted;
  const bindings = assembly?.candidate ? assembly.candidateBindings : assembly?.bindings;
  if (!assembly || assembly.status === 'blocked' || !revision || !bindings || assembly.strategyId !== strategyId ||
      revision.assembly.designId !== assembly.designId || bindings.designId !== assembly.designId ||
      bindings.strategyId !== strategyId || bindings.revisionId !== revision.id || bindings.engineeringHash !== revision.engineeringHash) return null;
  if (assembly.candidate ? revision.parentRevisionId !== assembly.revisionId : revision.id !== assembly.revisionId) return null;
  const action = bindings.actions.find(a => a.actionId === actionId);
  const transforms = assembly.candidate ? assembly.candidateWorldTransforms : assembly.worldTransforms;
  if (!action?.instanceIds.length || !action.instanceIds.every(id => {
    const instance = revision.assembly.instances.find(i => i.id === id);
    const component = assembly.components.find(c => c.id === instance?.componentId);
    return instance && component && component.referenceOnly !== true && component.rightsStatus === 'qualified_for_declared_use' &&
      transforms[id]?.length === 16 && transforms[id].every(Number.isFinite);
  }) || !action.anchors.every(anchor => action.instanceIds.includes(anchor.instanceId) &&
      revision.assembly.instances.some(i => i.id === anchor.instanceId && i.componentId === anchor.componentId))) return null;
  return { action, revision, candidate: !!assembly.candidate };
}
