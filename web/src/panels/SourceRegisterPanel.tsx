import { useEffect, useState } from 'react';
import { api, errorMessage } from '../api/client';
import type { SourceRegister } from '../api/sources';
import type { Mode } from '../api/contracts';

const labels: Record<string, string> = {
  acquisition_storage: 'Original storage', conversion: 'Mesh conversion',
  assembly_placement: 'Assembly placement', loopback_display: 'Local display',
  lan_display: 'LAN display', public_depiction: 'Public imagery',
  original_redistribution: 'Original redistribution', mesh_redistribution: 'Mesh redistribution',
  public_hosting: 'Public hosting', part_modification: 'Part modification',
};
export function SourceRegisterPanel({ mode }: { mode: Mode }) {
  const [data, setData] = useState<SourceRegister | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null); setData(null);
    api.sources(controller.signal).then(next => { if (!controller.signal.aborted) setData(next); })
      .catch(reason => { if (!controller.signal.aborted) setError(errorMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);
  return <section className="source-register" aria-label="Local source register">
    <div className="subsection-title"><h2>Source register</h2><button className="text-action" disabled={loading} onClick={() => setAttempt(n => n + 1)}>Refresh sources</button></div>
    <p className="availability-note">Discovered originals are separate from prepared components. This list contains metadata only; it does not import or convert geometry.</p>
    {loading && <p role="status">Checking local source records…</p>}
    {error && <p role="alert">{error}</p>}
    {data && !data.sources.length && <p>No STEP originals have been recorded. Add your STEP files to the external catalog, then run local discovery.</p>}
    {!!data?.sources.length && <ul className="source-records">{data.sources.map(s => <li key={s.sourceSha256}>
      <h3>{s.name}</h3><small>{s.sku ?? 'Identity needs review'} · {s.sourceState}</small>
      <dl>{Object.entries(s.permissions).filter(([op]) => mode === 'advanced' || ['conversion', 'loopback_display', 'assembly_placement'].includes(op)).map(([op, permission]) => <div key={op}><dt>{labels[op] ?? op.replaceAll('_', ' ')}</dt><dd>{permission.status === 'qualified' ? 'Evidence checked' : permission.status === 'disallowed' ? 'Disallowed' : 'Unverified — blocked'}</dd></div>)}</dl>
      {mode === 'advanced' && <p className="source-hash">SHA-256 · {s.sourceSha256}</p>}
      {s.sourceUrl && /^https:\/\//i.test(s.sourceUrl) && <a className="source-link" href={s.sourceUrl} target="_blank" rel="noopener noreferrer">Manufacturer/source reference</a>}
    </li>)}</ul>}
    {!!data?.blockers.length && <ul className="source-record-blockers">{data.blockers.map((b, i) => <li key={`${b.code}-${i}`}>{b.message}</li>)}</ul>}
    <p className="availability-note">An available download is not a license. Unverified operations remain blocked. An imported Clawbot is an import test fixture, not an AI-generated design.</p>
  </section>;
}
