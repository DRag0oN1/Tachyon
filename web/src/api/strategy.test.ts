import { describe, expect, it } from 'vitest';
import { blockedDesignFixture, editableDesignFixture, strategyFixture } from '../test/strategy';
import { parseDesignSession, parseStrategySession, parseStrategyStatus } from './strategy';

describe('production handoff boundary', () => {
  it('preserves actual full saved v2 spec, source identity and both engineering alternatives', () => {
    const session = strategyFixture();
    expect(parseStrategySession(session)).toBe(session);
    expect(session.spec.behavior.conditionalPreferences.length).toBeGreaterThan(5);
    expect(session.architectures).toHaveLength(2);
    expect(session.architectures[0].subsystems.find(s => s.id === 'scorer')?.mechanismIntent).toBe('four_bar_gripper');
    expect(session.architectures[1].subsystems.find(s => s.id === 'scorer')?.mechanismIntent).toBe('linear_elevator_parallel_gripper');
  });
  it.each(['competition', 'domain', 'policy', 'architecture', 'events', 'simulation'])('rejects mismatched %s instead of presenting fabricated success', key => {
    const session = strategyFixture();
    const payload: Record<string, unknown> = { ...structuredClone(session) };
    if (key === 'competition') payload.competition = { ...session.competition, id: 'uploaded-unknown' };
    if (key === 'domain') payload.performanceDomain = 'physically_verified';
    if (key === 'policy') payload.rollout = { ...session.rollout, policyParameterHash: '0'.repeat(64) };
    if (key === 'architecture') payload.architectures = [{ ...session.architectures[0], strategyId: 'wrong' }, session.architectures[1]];
    if (key === 'events') payload.rollout = { ...session.rollout, events: [{ ...session.rollout.events[0], to_xy: [Infinity, 0] }] };
    if (key === 'simulation') payload.rollout = { ...session.rollout, simulationOnly: false };
    expect(() => parseStrategySession(payload)).toThrow('incompatible');
  });
  it('keeps unavailable strategy status distinct from a malformed status', () => {
    expect(parseStrategyStatus({ available: false, competitionId: 'v5-override-v2.1', environmentId: 'override_abstract_strategy_v2_cups', reason: 'Checkpoint unavailable' }).available).toBe(false);
    expect(() => parseStrategyStatus({ available: true, competitionId: 'unknown' })).toThrow('incompatible');
  });
  it('accepts honest blocked replies and rejects editing without an accepted revision', () => {
    expect(parseDesignSession(blockedDesignFixture()).accepted).toBeNull();
    expect(() => parseDesignSession({ ...blockedDesignFixture(), canEdit: true })).toThrow('incompatible');
  });
  it('rejects stale revision bindings and transformed geometry with incomplete identity', () => {
    const session = editableDesignFixture();
    expect(parseDesignSession(session)).toBe(session);
    expect(() => parseDesignSession({ ...session, bindings: { ...session.bindings, revisionId: 'stale' } })).toThrow('incompatible');
    expect(() => parseDesignSession({ ...session, components: [{ ...session.components[0], meshUrl: 'https://example.com/mesh.glb' }] })).toThrow('incompatible');
  });
});
