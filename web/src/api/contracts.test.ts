import { describe, expect, it } from 'vitest';
import { geometryLabel, isInspectable, parseCapabilities, parseCatalog } from './contracts';
import { capabilitiesFixture, catalogFixture, componentFixture } from '../test/contracts';

describe('catalog contract and honest geometry classification', () => {
  it('accepts null SKU and preserves component identity, units, source hash and metadata', () => {
    expect(parseCatalog(catalogFixture).components[0]).toMatchObject(componentFixture);
    expect(geometryLabel(componentFixture)).toBe('Tachyon-authored · non-VEX test fixture');
    expect(isInspectable(componentFixture)).toBe(true);
  });
  it.each([
    { meshUrl: 'https://example.com/mesh.glb' }, { boundsM: { min: [0, 0, 0], max: [1, Infinity, 1] } },
    { boundsM: { min: [2, 0, 0], max: [1, 1, 1] } }, { sourceSha256: 'unknown' }, { completeRobot: true },
  ])('rejects unsafe or incompatible geometry metadata: %j', change => {
    expect(() => parseCatalog({ ...catalogFixture, components: [{ ...componentFixture, ...change }] })).toThrow('incompatible');
  });
  it('keeps unqualified, conceptual and placeholder geometry unavailable', () => {
    expect(isInspectable({ ...componentFixture, rightsStatus: 'unverified' })).toBe(false);
    expect(isInspectable({ ...componentFixture, geometryClass: 'placeholder' })).toBe(false);
    expect(isInspectable({ ...componentFixture, geometryClass: 'conceptual' })).toBe(false);
  });
  it('never interprets provider configuration as implemented generation support', () => {
    expect(parseCapabilities(capabilitiesFixture).canGenerateRobot).toBe(false);
    expect(() => parseCapabilities({ ...capabilitiesFixture, canEdit: true })).toThrow('incompatible');
  });
});
