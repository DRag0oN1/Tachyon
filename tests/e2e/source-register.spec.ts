import { readFileSync } from 'node:fs';
import { test, expect } from '../../web/e2e-support';
import { parseSourceRegister } from '../../web/src/api/sources';
import { parseWorkspace } from '../../web/src/api/contracts';

// Real metadata-only requests. Never substitute this for authentic CAD rendering.
test('@source-register external originals remain blocked without qualified conversion and display rights', async ({ page, request, baseURL }) => {
  const sessionFile = process.env.TACHYON_E2E_SESSION_FILE;
  const expected = process.env.TACHYON_E2E_SOURCE_HASHES?.split(',').filter(Boolean) ?? [];
  test.skip(!sessionFile || expected.length < 2, 'Requires an explicitly selected external-source workspace and runtime owner session.');
  const token = readFileSync(sessionFile!, 'utf8').trim();
  const headers = { 'X-Tachyon-Session': token, Origin: baseURL! };
  const response = await request.get('/api/sources', { headers });
  expect(response.status()).toBe(200);
  const status = parseSourceRegister(await response.json());
  expect(status.geometryIncluded).toBe(false);
  expect(status.sources.map(s => s.sourceSha256)).toEqual(expect.arrayContaining(expected));
  for (const source of status.sources.filter(s => expected.includes(s.sourceSha256))) {
    expect(source.sourceState).toBe('present');
    expect(source.permissions.conversion.status).toBe('unverified');
    expect(source.permissions.loopback_display.status).toBe('unverified');
  }
  const body = JSON.stringify(status);
  expect(body).not.toContain('/Users/');
  expect(body).not.toContain('evidencePath');
  const catalog = await (await request.get('/api/catalog', { headers })).json();
  expect(catalog.components).toHaveLength(0);
  const initial = parseWorkspace(await (await request.get('/api/workspace', { headers })).json());
  const errors: string[] = [];
  let assetRequests = 0;
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', req => { if (new URL(req.url()).pathname.startsWith('/api/assets/')) assetRequests++; });
  try {
    await page.addInitScript(owner => sessionStorage.setItem('tachyon.owner-session', owner), token);
    await page.goto('/');
    await expect(page.getByText('LOCAL / CONNECTED', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Preferences', exact: true }).click();
    const theme = test.info().project.name === 'mobile-webkit' ? 'SHIFT' : 'SNAP';
    await page.getByRole('button', { name: new RegExp(theme) }).click();
    await page.getByRole('button', { name: /Advanced/ }).click();
    await page.getByRole('button', { name: 'Components', exact: true }).click();
    await page.getByRole('button', { name: 'Review source register' }).click();
    const register = page.getByRole('region', { name: 'Local source register' });
    await expect(register.getByRole('heading', { name: 'V5 Clawbot', exact: true })).toBeVisible();
    await expect(register.getByRole('heading', { name: 'V5 Smart Motor (11W)', exact: true })).toBeAttached();
    expect(await register.getByText('Unverified — blocked', { exact: true }).count()).toBeGreaterThanOrEqual(6);
    await expect(page.getByTestId('cad-canvas')).toHaveCount(0);
    await page.getByRole('button', { name: 'Refresh sources' }).click();
    await expect(register.getByRole('heading', { name: 'V5 Clawbot', exact: true })).toBeVisible();
    await register.scrollIntoViewIfNeeded();
    await page.screenshot({ path: test.info().outputPath(`${test.info().project.name}-${theme.toLowerCase()}-external-register-blocked.png`) });
    await page.getByRole('button', { name: 'Hide source register' }).click();
    await expect(page.getByRole('region', { name: 'Local source register' })).toHaveCount(0);
    expect(assetRequests).toBe(0);
    expect(errors).toEqual([]);
    test.info().annotations.push({ type: 'evidence-limits', description: 'Actual external source metadata and blocked-state UI only; no VEX conversion, rendering, dimensions, transforms or part picking proved.' });
  } finally {
    await request.patch('/api/workspace', { headers, data: initial });
  }
});
