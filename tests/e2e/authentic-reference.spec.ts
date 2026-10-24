import { readFileSync } from 'node:fs';
import { test, expect } from '../../web/e2e-support';
import { parseCatalog, parseWorkspace } from '../../web/src/api/contracts';

test('@authentic-reference actual manufacturer assembly renders and selects separate parts in SNAP and SHIFT', async ({ page, request, baseURL }) => {
  test.setTimeout(180_000);
  const sessionFile = process.env.TACHYON_E2E_SESSION_FILE;
  const id = process.env.TACHYON_E2E_REFERENCE_ID;
  test.skip(!sessionFile || !id, 'Opt-in: requires the owner-selected private manufacturer reference workspace.');
  expect(['127.0.0.1', 'localhost']).toContain(new URL(baseURL!).hostname);
  const token = readFileSync(sessionFile!, 'utf8').trim();
  const headers = { 'X-Tachyon-Session': token, Origin: baseURL! };
  const response = await request.get('/api/catalog', { headers });
  expect(response.status()).toBe(200);
  const catalog = parseCatalog(await response.json());
  const source = catalog.components.find(c => c.id === id);
  expect(source, 'The exact requested genuine reference must be prepared; absence is a failure, not substituted evidence.').toBeTruthy();
  const component = source!;
  expect(component.originKind).toBe('manufacturer_cad');
  expect(component.geometryClass).toBe('verified_imported_component');
  expect(component.referenceOnly).toBe(true);
  expect(component.completeRobot).toBe(false);
  const known = id === 'v5_clawbot_reference' ? 'd291e70cf6ccd5260983193ab07d9f824b965b1c5f7e2ef298e961e7e7768fb7' : '3399374de417a5b403619e9e475d616e0cc1c3196324b4ba15d4fd0049ab9cec';
  expect(component.sourceSha256).toBe(known);
  const parts = component.nativeHierarchy!.filter(n => n.hasMesh);
  expect(parts.length).toBeGreaterThan(1);
  const initial = parseWorkspace(await (await request.get('/api/workspace', { headers })).json());
  const errors: string[] = [], remote: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (/^https?:/.test(r.url()) && new URL(r.url()).origin !== baseURL) remote.push(new URL(r.url()).origin); });
  try {
    // Avoid loading a different potentially very large source before the
    // owner-selected reference. The original workspace is restored below.
    await request.patch('/api/workspace', { headers, data: { activeComponentId: component.id } });
    await page.addInitScript(owner => sessionStorage.setItem('tachyon.owner-session', owner), token);
    await page.goto('/');
    await expect(page.getByText('Local workspace', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Preferences', exact: true }).click();
    await page.getByRole('button', { name: /Advanced/ }).click();
    await page.getByRole('button', { name: 'Components', exact: true }).click();
    await page.locator('.component-row').filter({ hasText: component.name }).click();
    const status = page.getByTestId('scene-status');
    await expect(status).toHaveAttribute('data-state', /ready|failed/, { timeout: 100_000 });
    await expect(status).toHaveAttribute('data-state', 'ready');
    expect(Number(await status.getAttribute('data-mesh-count'))).toBeGreaterThan(1);
    await expect(status).toContainText('IMPORTED REFERENCE');
    const observed = JSON.parse((await status.getAttribute('data-render-bounds'))!);
    for (const side of ['min', 'max'] as const) component.boundsM[side].forEach((v, i) => expect(observed[side][i]).toBeCloseTo(v, 4));
    if (id === 'v5_clawbot_reference') {
      // This manufacturer reference uses native Y as its upright axis. Only the
      // viewing camera changes; receipt coordinates and engineering data do not.
      await page.getByRole('button', { name: /^Change native up axis/ }).click();
      await page.getByRole('button', { name: /^Change native up axis/ }).click();
      await expect(page.locator('canvas')).toHaveAttribute('data-camera-up', '[0,0,-1]');
    }
    // Select two different native occurrences through the real hierarchy UI.
    for (const part of parts.slice(0, 2)) {
      await page.getByPlaceholder('Source name or node ID').fill(part.id);
      await page.locator(`.native-hierarchy button[data-native-node-id="${part.id}"]`).click();
      await expect(page.locator('.selection-chip')).toHaveAttribute('data-native-node-id', part.id);
    }
    await page.getByRole('button', { name: 'Close Components' }).click();
    const canvas = page.locator('canvas');
    const wholeCamera = await canvas.getAttribute('data-camera-position');
    await page.getByRole('button', { name: 'Focus', exact: true }).click();
    await expect(canvas).not.toHaveAttribute('data-camera-position', wholeCamera!);
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(null)))));
    await page.screenshot({ path: test.info().outputPath(`${test.info().project.name}-${id}-selected-native-part-private.png`) });
    await page.getByRole('button', { name: 'Reset view', exact: true }).click();
    await page.getByRole('button', { name: 'Clear selection' }).click();
    for (const theme of ['SNAP', 'SHIFT']) {
      await page.getByRole('button', { name: 'Preferences', exact: true }).click();
      await page.getByRole('button', { name: new RegExp(theme) }).click();
      await page.getByRole('button', { name: 'Close Preferences' }).click();
      await expect(page.locator('main')).toHaveAttribute('data-theme', theme.toLowerCase());
      await expect(status).toHaveAttribute('data-state', 'ready');
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(null)))));
      await page.screenshot({ path: test.info().outputPath(`${test.info().project.name}-${theme.toLowerCase()}-${id}-private.png`) });
    }
    expect(remote).toEqual([]);
    expect(errors).toEqual([]);
    test.info().annotations.push({ type: 'purpose', description: 'Private manufacturer reference inspection only. Actual source geometry, not a newly generated robot. Screenshots are local; public depiction permission is not inferred.' });
  } finally { await request.patch('/api/workspace', { headers, data: initial }).catch(() => {}); }
});
