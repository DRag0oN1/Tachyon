import savedSpec from '../../../research/strategy_rl/results/strategy-design-bridge-v1/strategy-spec-v2.json';
import savedArchitectures from '../../../research/strategy_rl/results/strategy-design-bridge-v1/design/architecture-proposals.json';
import { parseStrategySession, type DesignSession, type StrategySession } from '../api/strategy';
import { componentFixture } from './contracts';

/** Recorded research artifacts exercise presentation/contracts only, never live-inference evidence. */
export function strategyFixture(): StrategySession {
  const spec = structuredClone(savedSpec);
  const trace = spec.representativeSequences[0];
  const frequencies: Record<string, number> = {};
  trace.events.forEach(e => { frequencies[e.action] = (frequencies[e.action] ?? 0) + 1 / trace.events.length; });
  return parseStrategySession({
    id: spec.id, competition: spec.competition, strategyFamily: spec.strategyFamily,
    source: 'trained_ppo', performanceDomain: 'abstract_simulation_only',
    spec, architectures: structuredClone(savedArchitectures), limitations: spec.limitations,
    rollout: { events: trace.events, score: trace.modeledScore, pointsByObjective: { alliance_pin_halves: trace.modeledScore },
      capabilities: spec.capabilityRequirements.referenceCapabilities, actionFrequencies: frequencies,
      policyParameterHash: spec.policy.checkpoint.parameterHash, simulationOnly: true, evidence: { episodeSeed: trace.episodeSeed } },
  });
}
export function blockedDesignFixture(): DesignSession {
  const strategy = strategyFixture();
  return {
    designId: 'unit-design', architectureId: strategy.architectures[0].id, strategyId: strategy.spec.id,
    status: 'blocked', canEdit: false, revisionId: null, accepted: null, candidate: null,
    bindings: null, candidateBindings: null, worldTransforms: {}, candidateWorldTransforms: {}, components: [],
    missing: [{ role: 'scorer', code: 'REQUIRED_ROLE_UNREALIZED', message: 'No qualified scoring mechanism recipe or assembly placement is available.' }],
    qualification: { completeRobot: false }, plan: {},
  };
}
/** Original non-VEX fixture data: verifies revision requests, not physical/CAD acceptance. */
export function editableDesignFixture(): DesignSession {
  const session = blockedDesignFixture();
  const matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  return {
    ...session, status: 'partial', canEdit: true, revisionId: 'unit-accepted',
    accepted: { id: 'unit-accepted', parentRevisionId: null, engineeringHash: 'a'.repeat(64), assembly: {
      designId: session.designId, configurationId: 'lower', units: 'm', upAxis: 'Y', matrixLayout: 'column-major',
      instances: [{ id: 'unit-scorer', componentId: componentFixture.id, subsystemId: 'scorer', parentId: null, transform: { matrix } }],
      subsystems: [{ id: 'scorer', name: 'Original software test fixture' }],
    } },
    bindings: { designId: session.designId, strategyId: session.strategyId, revisionId: 'unit-accepted', engineeringHash: 'a'.repeat(64), bindingsHash: 'b'.repeat(64),
      actions: [{ actionId: 'place_alliance', subsystemId: 'scorer', instanceIds: ['unit-scorer'], componentIds: [componentFixture.id], jointIds: [], anchors: [], capabilityStatus: 'unsupported', capabilityReason: 'Software fixture only' }] },
    worldTransforms: { 'unit-scorer': matrix }, components: [componentFixture], previous: null, qualification: { completeRobot: false, testFixtureOnly: true },
  };
}
