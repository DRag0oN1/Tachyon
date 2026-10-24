export type PermissionState = 'qualified' | 'unverified' | 'disallowed';
export interface SourceRecord {
  sourceSha256: string;
  name: string;
  sku: string | null;
  sourceUrl: string | null;
  sourceState: 'present' | 'missing' | 'changed' | 'unreadable';
  permissions: Record<string, { status: PermissionState; code: string | null }>;
}
export interface SourceRegister {
  schemaVersion: 1;
  sources: SourceRecord[];
  blockers: { code: string; message: string }[];
  geometryIncluded: false;
}
export function parseSourceRegister(value: unknown): SourceRegister {
  const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
  const fail = (): never => { throw new Error('The server returned an incompatible source register.'); };
  if (!object(value) || value.schemaVersion !== 1 || value.geometryIncluded !== false || !Array.isArray(value.sources) || !Array.isArray(value.blockers)) return fail();
  for (const s of value.sources) {
    if (!object(s) || typeof s.sourceSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(s.sourceSha256) || typeof s.name !== 'string' ||
      !(s.sku === null || typeof s.sku === 'string') || !(s.sourceUrl === null || typeof s.sourceUrl === 'string') ||
      !['present', 'missing', 'changed', 'unreadable'].includes(String(s.sourceState)) || !object(s.permissions)) return fail();
    for (const p of Object.values(s.permissions)) {
      if (!object(p) || !['qualified', 'unverified', 'disallowed'].includes(String(p.status)) || !(p.code === null || typeof p.code === 'string')) return fail();
    }
  }
  if (value.blockers.some(b => !object(b) || typeof b.code !== 'string' || typeof b.message !== 'string')) return fail();
  return value as unknown as SourceRegister;
}
