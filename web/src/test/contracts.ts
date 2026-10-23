import type { Catalog, Capabilities, ComponentDefinition, Workspace } from '../api/contracts';

// Metadata only, deliberately synthetic and non-VEX. No test robot geometry.
export const componentFixture: ComponentDefinition = {
  id: 'tachyon-authored-calibration', name: 'Tachyon-authored non-VEX calibration fixture', sku: null,
  originKind: 'tachyon_authored', geometryClass: 'test_fixture', sourceUrl: '',
  sourceSha256: 'a'.repeat(64), meshSha256: 'b'.repeat(64), meshUrl: `/api/assets/${'b'.repeat(64)}.glb`,
  boundsM: { min: [0, 0, 0], max: [0.12, 0.04, 0.06] }, solidCount: 3,
  rightsStatus: 'qualified_for_declared_use', ports: [], completeRobot: false,
};
export const catalogFixture: Catalog = { profile: 'user_provided_local', components: [componentFixture], blockers: [] };
export const capabilitiesFixture: Capabilities = { canInspect: true, canGenerateStrategy: false, canGenerateRobot: false, canEdit: false, reasons: ['Generation is unavailable.'] };
export const workspaceFixture: Workspace = { preferences: { theme: 'snap', mode: 'simple' }, activeComponentId: null };
