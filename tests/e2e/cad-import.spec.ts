import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '../../web/e2e-support';
import { isInspectable, parseCatalog, parseCapabilities, parseWorkspace, type ComponentDefinition } from '../../web/src/api/contracts';

// These tests use a running backend. There are no mocked successful CAD routes.
// Credentials are supplied only at runtime. Reports/recordings never include them.
function ownerSession(): string | null {
  const content = process.env.TACHYON_E2E_SESSION_FILE
    ? readFileSync(process.env.TACHYON_E2E_SESSION_FILE, 'utf8').trim()
    : process.env.TACHYON_E2E_SESSION?.trim();
  if (!content) return null;
  return content.startsWith('http') ? new URLSearchParams(new URL(content).hash.slice(1)).get('session') : content;
}
async function connect(page: Page, token: string) {
  await page.addInitScript(owner => { sessionStorage.setItem('tachyon.owner-session', owner); }, token);
  await page.goto('/');
  await expect(page.getByText('Local workspace', { exact: true })).toBeVisible();
}
async function openSource(page: Page, component: ComponentDefinition) {
  await page.getByRole('button', { name: 'Components', exact: true }).click();
  await page.locator('.component-row').filter({ hasText: component.name }).click();
  await expect(page.getByTestId('scene-status')).toHaveAttribute('data-state', 'ready', { timeout: 20_000 });
}
test.beforeEach(async ({ request }) => {
  const health = await request.get('/api/health', { timeout: 5000 }).catch(() => null);
  test.skip(!health?.ok(), 'Blocked: start the real local backend on port 8000.');
});

test('@cad-import missing owner session stays unavailable without replacement geometry', async ({ page, request }) => {
  expect((await request.get('/api/catalog')).status()).toBe(401);
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('authorized launch URL');
  await expect(page.getByTestId('cad-canvas')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Generate Strategy' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Create Robot' })).toBeDisabled();
  await page.getByRole('button', { name: 'Close Welcome to Tachyon' }).click();
  await page.screenshot({ path: test.info().outputPath(`${test.info().project.name}-missing-session-no-cad.png`) });
});

test('@cad-import authenticated empty catalog explains missing source inputs', async ({ page, request, baseURL }) => {
  const token = ownerSession();
  test.skip(!token, 'Blocked: supply the serving process owner session through TACHYON_E2E_SESSION_FILE.');
  const headers = { 'X-Tachyon-Session': token!, Origin: baseURL! };
  const response = await request.get('/api/catalog', { headers });
  expect(response.ok(), 'The runtime owner session must authorize the real backend.').toBe(true);
  const catalog = parseCatalog(await response.json());
  test.skip(catalog.components.some(isInspectable), 'This server has geometry; use the real-GLB test for this catalog.');
  await connect(page, token!);
  await page.getByRole('button', { name: 'Components', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your catalog is empty' })).toBeVisible();
  await expect(page.getByTestId('cad-canvas')).toHaveCount(0);
  for (const blocker of catalog.blockers) await expect(page.getByRole('dialog', { name: 'Components' })).toContainText(blocker.message);
});

test('@cad-import real authenticated GLB keeps identity, bounds, selection and workspace context', async ({ page, request, baseURL }) => {
  const token = ownerSession();
  test.skip(!token, 'Blocked: supply a runtime owner session; no catalog or rendering evidence is fabricated.');
  const headers = { 'X-Tachyon-Session': token!, Origin: baseURL! };
  const catalogResponse = await request.get('/api/catalog', { headers });
  expect(catalogResponse.ok()).toBe(true);
  const catalog = parseCatalog(await catalogResponse.json());
  const caps = parseCapabilities(await (await request.get('/api/capabilities', { headers })).json());
  const source = catalog.components.find(isInspectable);
  test.skip(!source || !caps.canInspect, 'Blocked: register and prepare a rights-qualified local source or separately labeled Tachyon-authored converter fixture.');
  const component = source!;
  const initial = parseWorkspace(await (await request.get('/api/workspace', { headers })).json());
  test.info().annotations.push({ type: 'geometry-purpose', description: component.geometryClass === 'test_fixture' ? 'Tachyon-authored non-VEX converter/render proof only; authentic-VEX acceptance remains blocked.' : 'Qualified source component inspection; not a complete robot.' });
  const pageErrors: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  let meshRequests = 0;
  let unauthenticatedMeshRequest = false;
  page.on('request', req => {
    if (new URL(req.url()).pathname === component.meshUrl) {
      meshRequests++;
      if (req.headers()['x-tachyon-session'] !== token) unauthenticatedMeshRequest = true;
    }
  });
  try {
    if (test.info().project.name === 'mobile-webkit') await page.addInitScript(() => {
      Object.defineProperty(window, 'crypto', { configurable: true, value: { subtle: undefined } });
    });
    await connect(page, token!);
    await openSource(page, component);
    const status = page.getByTestId('scene-status');
    await expect(status).toHaveAttribute('data-component-id', component.id);
    await expect(status).toHaveAttribute('data-mesh-sha256', component.meshSha256);
    expect(Number(await status.getAttribute('data-mesh-count'))).toBeGreaterThan(0);
    const observed = JSON.parse((await status.getAttribute('data-render-bounds'))!);
    for (const side of ['min', 'max'] as const) component.boundsM[side].forEach((v, i) => expect(observed[side][i]).toBeCloseTo(v, 4));
    const expectedDimensions = component.boundsM.max.map((v, i) => ((v - component.boundsM.min[i]) * 1000).toFixed(2)).join(' × ');
    await expect(page.getByTestId('component-dimensions')).toHaveText(expectedDimensions);
    await expect(page.getByRole('dialog', { name: 'Components' })).toContainText('Source part only');
    if (component.geometryClass === 'test_fixture') await expect(status).toContainText('NOT AUTHENTIC VEX');
    await page.getByRole('button', { name: 'Select in scene' }).click();
    await page.getByRole('button', { name: 'Close Components' }).click();
    await expect(page.locator('.selection-chip')).toHaveAttribute('data-component-id', component.id);
    await page.getByRole('button', { name: 'Clear selection' }).click();
    const canvas = page.locator('canvas');
    const bounds = (await canvas.boundingBox())!;
    const initialPosition = await canvas.getAttribute('data-camera-position');
    const initialTarget = await canvas.getAttribute('data-controls-target');
    const cx = bounds.x + bounds.width * .5;
    const cy = bounds.y + bounds.height * .5;
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx + 55, cy + 20, { steps: 8 });
    await page.mouse.up();
    await expect(canvas).not.toHaveAttribute('data-camera-position', initialPosition!);
    // Orbit drags never become picks.
    await expect(page.locator('.selection-chip')).toHaveCount(0);
    const orbitPosition = await canvas.getAttribute('data-camera-position');
    if (test.info().project.name === 'mobile-webkit') {
      // This driver cannot send mouse.wheel in a mobile context. Exercise the
      // real wheel handler; this is not evidence of a physical pinch gesture.
      test.info().annotations.push({ type: 'input-limit', description: 'Mobile WebKit zoom handler uses a dispatched WheelEvent; physical phone pinch/pan remain unverified.' });
      await canvas.dispatchEvent('wheel', { deltaY: -160, deltaMode: 0, bubbles: true, cancelable: true, clientX: cx, clientY: cy });
    } else await page.mouse.wheel(0, -160);
    await expect(canvas).not.toHaveAttribute('data-camera-position', orbitPosition!);
    await page.mouse.move(cx, cy);
    await page.mouse.down({ button: 'right' });
    await page.mouse.move(cx + 35, cy + 15, { steps: 6 });
    await page.mouse.up({ button: 'right' });
    await expect(canvas).not.toHaveAttribute('data-controls-target', initialTarget!);
    await page.getByRole('button', { name: 'Reset view' }).click();
    await expect(canvas).toHaveAttribute('data-camera-position', initialPosition!);
    await expect(canvas).toHaveAttribute('data-controls-target', initialTarget!);
    // Pick the real imported surfaces, including off-centre nested source parts.
    for (const [x, y] of [[.5, .5], [.42, .5], [.58, .5], [.5, .42], [.5, .58], [.35, .45], [.65, .55]]) {
      if (await page.locator('.selection-chip').count()) break;
      const position = { x: bounds.width * x, y: bounds.height * y };
      if (test.info().project.name === 'mobile-webkit') await canvas.tap({ position });
      else await canvas.click({ position });
    }
    await expect(page.locator('.selection-chip')).toHaveAttribute('data-component-id', component.id);
    await expect(page.locator('.selection-chip')).toHaveAttribute('data-native-node-id', /^node-\d+$/);
    const requestCount = meshRequests;
    const retainedCamera = await canvas.getAttribute('data-camera-position');
    await page.getByRole('button', { name: 'Preferences', exact: true }).click();
    await page.getByRole('button', { name: /SHIFT/ }).click();
    await page.getByRole('button', { name: /Advanced/ }).click();
    await page.getByRole('button', { name: 'Close Preferences' }).click();
    await expect(page.locator('main')).toHaveAttribute('data-theme', 'shift');
    await expect(page.locator('.selection-chip')).toHaveAttribute('data-component-id', component.id);
    await expect(canvas).toHaveAttribute('data-camera-position', retainedCamera!);
    await page.getByRole('button', { name: 'Components', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Components' })).toContainText(component.sourceSha256);
    const node = component.nativeHierarchy?.find(n => n.hasMesh);
    if (node) {
      await page.locator('.native-hierarchy button').filter({ hasText: node.id }).click();
      await expect(page.locator('.selection-chip')).toHaveAttribute('data-native-node-id', node.id);
    }
    await page.getByRole('button', { name: 'Close Components' }).click();
    await page.getByRole('button', { name: 'Reset view' }).click();
    if (component.geometryClass === 'test_fixture') await page.screenshot({ path: test.info().outputPath(`${test.info().project.name}-shift-tachyon-authored-non-vex-converter-fixture.png`) });
    await page.getByRole('button', { name: 'Expand assistant', exact: true }).click();
    await page.getByLabel('Design request').fill('Keep this draft; editing is unavailable.');
    await page.getByRole('button', { name: 'Full-screen assistant' }).click();
    await expect(page.getByRole('dialog', { name: 'Tachyon assistant' })).toHaveAttribute('aria-modal', 'true');
    await expect(page.getByRole('button', { name: 'Send request' })).toBeDisabled();
    await page.getByRole('button', { name: 'Close assistant' }).click();
    await page.getByRole('button', { name: 'Expand assistant', exact: true }).click();
    await expect(page.getByLabel('Design request')).toHaveValue('Keep this draft; editing is unavailable.');
    await page.getByRole('button', { name: 'Close assistant' }).click();
    await expect(canvas).toHaveAttribute('data-camera-position', retainedCamera!);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.getByRole('button', { name: 'Expand assistant', exact: true }).click();
    await expect(page.locator('.core-module').first()).toHaveCSS('transform', 'none');
    await expect(page.locator('.core-center')).toHaveCSS('animation-name', 'none');
    await page.getByRole('button', { name: 'Close assistant' }).click();
    await page.getByRole('button', { name: 'Preferences', exact: true }).click();
    await page.getByRole('button', { name: /SNAP/ }).click();
    await page.getByRole('button', { name: 'Close Preferences' }).click();
    await expect(page.getByTestId('scene-status')).toHaveAttribute('data-state', 'ready');
    expect(meshRequests).toBe(requestCount);
    expect(unauthenticatedMeshRequest).toBe(false);
    expect(pageErrors).toEqual([]);
    if (component.geometryClass === 'test_fixture') await page.screenshot({ path: test.info().outputPath(`${test.info().project.name}-snap-tachyon-authored-non-vex-converter-fixture.png`) });
    // Wait for actual preference persistence before restoring the initial state.
    await expect(page.getByText('Local workspace', { exact: true })).toBeVisible();
  } catch (error) {
    await test.info().attach('renderer-diagnostics', { body: JSON.stringify({ pageErrors, canvasCount: await page.locator('canvas').count(), state: await page.getByTestId('scene-status').getAttribute('data-state') }), contentType: 'application/json' });
    if (component.geometryClass === 'test_fixture') await page.screenshot({ path: test.info().outputPath(`${test.info().project.name}-failed-tachyon-authored-non-vex-converter-fixture.png`) });
    throw error;
  } finally { await request.patch('/api/workspace', { headers, data: initial }); }
});

test('@cad-import HTTP-phone SHA-256 fallback works with crypto.subtle unavailable in a real browser', async ({ page }) => {
  await page.goto('/');
  const actual = await page.evaluate(async () => {
    const oldCrypto = window.crypto;
    Object.defineProperty(window, 'crypto', { configurable: true, value: { subtle: undefined } });
    try {
      const modulePath = '/src/api/sha256.ts';
      const { sha256Hex } = await import(modulePath);
      return await sha256Hex(new TextEncoder().encode('abc').buffer);
    } finally { Object.defineProperty(window, 'crypto', { configurable: true, value: oldCrypto }); }
  });
  expect(actual).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});
