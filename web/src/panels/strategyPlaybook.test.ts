import { describe, expect, it } from 'vitest';
import type { StrategyEvent } from '../api/strategy';
import { editableDesignFixture, strategyFixture } from '../test/strategy';
import { buildPlaybookDrawing, buildStrategyPhases, phaseAssemblyLink, phaseRequirements } from './strategyPlaybook';

function trace(actions: string[]): StrategyEvent[] {
  return actions.map((action, i) => ({ action, start_s: i * 2, end_s: i * 2 + 2, from_xy: [i, 0], to_xy: [i + 1, 0], success: true, score_before: i, score_after: i + 1 }));
}

describe('observed strategy phases', () => {
  it('reduces each actual saved trace to a chronological playbook without losing or inventing decisions', () => {
    for (const sequence of strategyFixture().spec.representativeSequences) {
      const phases = buildStrategyPhases(sequence.events);
      expect(phases.length).toBeGreaterThanOrEqual(4);
      expect(phases.length).toBeLessThanOrEqual(6);
      expect(phases.flatMap(p => p.events)).toEqual(sequence.events);
      expect(phases.flatMap(p => p.eventIndices)).toEqual(sequence.events.map((_, i) => i));
      expect(phases.reduce((sum, p) => sum + p.scoreChange, 0)).toBe(sequence.events.at(-1)!.score_after - sequence.events[0].score_before);
      for (const phase of phases) {
        expect(phase.actionIds).toContain(phase.primaryActionId);
        expect(phase.events.some(e => e.action === phase.primaryActionId)).toBe(true);
      }
    }
  });

  it('retains unsuccessful attempts and labels repeat cycles only after observed acquisition and placement', () => {
    const events = trace(['move_to_supply0', 'acquire_alliance', 'acquire_cup', 'move_to_goal0', 'place_alliance', 'place_cup', 'move_to_supply0', 'acquire_alliance', 'move_to_goal0', 'place_alliance']);
    events[1].success = false;
    events[1].score_after = events[1].score_before;
    const phases = buildStrategyPhases(events);
    expect(phases.map(p => p.kind)).toEqual(['travel', 'acquire', 'travel', 'place', 'repeat']);
    expect(phases[1].failures).toBe(1);
    expect(phases[1].actionIds).toEqual(['acquire_alliance', 'acquire_cup']);
    expect(phases[4].primaryActionId).toBe('place_alliance');
    const retries = buildStrategyPhases(trace(['toggle', 'move_to_supply0', 'wait', 'move_to_goal0', 'acquire_alliance', 'place_alliance', 'place_alliance']));
    expect(retries.some(p => p.kind === 'repeat')).toBe(false);
  });

  it('creates a terminal phase only for actual terminal actions and never fills sparse traces with invented phases', () => {
    expect(buildStrategyPhases([])).toEqual([]);
    expect(buildStrategyPhases(trace(['acquire_cup']))).toHaveLength(1);
    expect(buildStrategyPhases(trace(['acquire_cup', 'wait'])).some(p => p.kind === 'finish')).toBe(false);
    const phases = buildStrategyPhases(trace(['acquire_cup', 'move_to_midfield', 'park_and_wait']));
    expect(phases.at(-1)?.actionIds).toEqual(['move_to_midfield', 'park_and_wait']);
    expect(phases.at(-1)?.title).toBe('Move to midfield and wait');
    expect(buildStrategyPhases(trace(['acquire_unknown']))[0].title).not.toContain('Pin');
  });

  it('looks up mechanism needs using actual phase action IDs only', () => {
    const spec = strategyFixture().spec;
    const phase = buildStrategyPhases(trace(['acquire_cup']))[0];
    expect(phaseRequirements(spec, phase)).toEqual(spec.mechanicalRequirements.filter(r => r.supports.includes('acquire_cup')));
    expect(phaseRequirements(spec, buildStrategyPhases(trace(['unknown_action']))[0])).toEqual([]);
  });
});

describe('coordinate playbook', () => {
  it('names only successful actual arrivals and retains incomplete travel without fabricating a field', () => {
    const events = trace(['move_to_goal0', 'acquire_alliance']);
    events[0].success = false;
    events[1].from_xy = events[1].to_xy;
    let drawing = buildPlaybookDrawing(events);
    expect(drawing.sites).toEqual([]);
    expect(drawing.routes).toHaveLength(1);
    expect(drawing.routes[0]).toMatchObject({ index: 0, actionId: 'move_to_goal0', success: false });
    events[0].success = true;
    drawing = buildPlaybookDrawing(events);
    expect(drawing.sites).toEqual([{ key: '1,0', point: drawing.project([1, 0]), label: 'low goal' }]);
    expect(buildPlaybookDrawing([]).routes).toEqual([]);
  });

  it('preserves equal scale on both coordinate axes', () => {
    const events = trace(['move_to_supply0']);
    events[0].to_xy = [1, 1];
    const drawing = buildPlaybookDrawing(events);
    const a = drawing.project([0, 0]), b = drawing.project([1, 1]);
    expect(b[0] - a[0]).toBe(a[1] - b[1]);
  });
});

describe('proposed versus revision-linked geometry', () => {
  it('links only actual instances in the displayed accepted or candidate revision', () => {
    const assembly = editableDesignFixture();
    const id = assembly.strategyId;
    expect(phaseAssemblyLink(assembly, id, 'place_alliance')).toMatchObject({ candidate: false, revision: { id: assembly.revisionId } });
    assembly.candidate = { ...structuredClone(assembly.accepted!), id: 'preview', parentRevisionId: assembly.revisionId, engineeringHash: 'c'.repeat(64) };
    // An accepted binding must never stand in for a missing preview binding.
    expect(phaseAssemblyLink(assembly, id, 'place_alliance')).toBeNull();
    assembly.candidateBindings = { ...structuredClone(assembly.bindings!), revisionId: 'preview', engineeringHash: 'c'.repeat(64) };
    assembly.candidateWorldTransforms = structuredClone(assembly.worldTransforms);
    expect(phaseAssemblyLink(assembly, id, 'place_alliance')).toMatchObject({ candidate: true, revision: { id: 'preview' } });
    assembly.candidate.parentRevisionId = 'stale-base';
    expect(phaseAssemblyLink(assembly, id, 'place_alliance')).toBeNull();
  });

  it.each(['strategy', 'revision', 'hash', 'instance', 'anchor', 'world', 'reference', 'rights'] as const)('refuses %s mismatches rather than promoting a proposal or source reference', fault => {
    const assembly = structuredClone(editableDesignFixture()), id = assembly.strategyId;
    if (fault === 'strategy') assembly.bindings!.strategyId = 'other-strategy';
    if (fault === 'revision') assembly.bindings!.revisionId = 'stale-revision';
    if (fault === 'hash') assembly.bindings!.engineeringHash = 'f'.repeat(64);
    if (fault === 'instance') assembly.bindings!.actions[0].instanceIds = ['missing-instance'];
    if (fault === 'anchor') assembly.bindings!.actions[0].anchors = [{ id: 'stale-anchor', instanceId: 'missing-instance', componentId: assembly.components[0].id, worldPointM: [0, 0, 0] }];
    if (fault === 'world') assembly.worldTransforms = {};
    if (fault === 'reference') assembly.components[0].referenceOnly = true;
    if (fault === 'rights') assembly.components[0].rightsStatus = 'unverified';
    expect(phaseAssemblyLink(assembly, id, 'place_alliance')).toBeNull();
    expect(phaseAssemblyLink(assembly, 'unrelated-strategy', 'place_alliance')).toBeNull();
    expect(phaseAssemblyLink(assembly, id, 'unknown_action')).toBeNull();
  });
});
