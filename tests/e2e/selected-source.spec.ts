import { readFileSync } from 'node:fs';
import { test, expect } from '../../web/e2e-support';
import { parseCatalog } from '../../web/src/api/contracts';

test('@selected-source purchased native unit renders actual geometry and retains separate selectable parts', async ({ page, request, baseURL }) => {
  test.setTimeout(180_000);
  const sessionFile=process.env.TACHYON_E2E_SESSION_FILE;
  const id=process.env.TACHYON_E2E_SELECTED_SOURCE_ID;
  test.skip(!sessionFile || !id,'Requires the separate private source-selected catalog.');
  expect(['127.0.0.1','localhost']).toContain(new URL(baseURL!).hostname);
  const token=readFileSync(sessionFile!,'utf8').trim();
  const headers={'X-Tachyon-Session':token,Origin:baseURL!};
  const response=await request.get('/api/catalog',{headers});
  expect(response.status()).toBe(200);
  const raw=await response.json();
  const component=parseCatalog(raw).components.find(c=>c.id===id)!;
  expect(component,'Exact selected source unit must be available; no fixture substitution').toBeTruthy();
  expect(component.originKind).toBe('manufacturer_cad');
  expect(component.geometryClass).toBe('verified_imported_component');
  expect(component.completeRobot).toBe(false);
  const receipt=raw.components.find((c:{id:string})=>c.id===id);
  expect(receipt.sourceSelection.definitionLabel).toBe('0:1:1:45');
  expect(receipt.sourceSelection.expectedDefinitionName).toBe('276-6010-100 Rev12_276-6010');
  expect(receipt.sourceSha256).toBe('d291e70cf6ccd5260983193ab07d9f824b965b1c5f7e2ef298e961e7e7768fb7');
  expect(receipt.geometryValidation.nativeBrepValid).toBe(true);
  expect(receipt.conversion.meshingMode).toBe('relative');
  expect(receipt.conversion.maxBoundsErrorM).toBeLessThanOrEqual(.0001);
  const parts=component.nativeHierarchy!.filter(n=>n.hasMesh);
  expect(parts.length).toBeGreaterThan(2);
  const initial=await (await request.get('/api/workspace',{headers})).json();
  const errors:string[]=[],remote:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()) && new URL(r.url()).origin!==baseURL)remote.push(new URL(r.url()).origin);});
  const theme=test.info().project.name.includes('mobile')?'shift':'snap';
  try {
    await request.patch('/api/workspace',{headers,data:{activeComponentId:id,preferences:{theme,mode:'advanced'}}});
    await page.addInitScript(owner=>sessionStorage.setItem('tachyon.owner-session',owner),token);
    await page.goto('/');
    const status=page.getByTestId('scene-status');
    await expect(status).toHaveAttribute('data-state',/ready|failed/,{timeout:100_000});
    await expect(status).toHaveAttribute('data-state','ready');
    expect(Number(await status.getAttribute('data-mesh-count'))).toBeGreaterThan(2);
    const observed=JSON.parse((await status.getAttribute('data-render-bounds'))!);
    for(const side of ['min','max'] as const)component.boundsM[side].forEach((v,i)=>expect(observed[side][i]).toBeCloseTo(v,4));
    await expect(page.getByTestId('design-canvas')).toHaveCount(0);
    await page.getByRole('button',{name:'Components',exact:true}).click();
    for(const part of parts.slice(0,2)) {
      await page.getByPlaceholder('Source name or node ID').fill(part.id);
      await page.locator(`.native-hierarchy button[data-native-node-id="${part.id}"]`).click();
      await expect(page.locator('.selection-chip')).toHaveAttribute('data-native-node-id',part.id);
    }
    await page.getByRole('button',{name:'Close Components',exact:true}).click();
    await page.getByRole('button',{name:'Clear selection',exact:true}).click();
    for(let i=0;i<3 && await page.locator('canvas').getAttribute('data-camera-up')!=='[0,0,-1]';i++)
      await page.getByRole('button',{name:/^Change native up axis/}).click();
    await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-${theme}-source-selected-gripper-private.png`)});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    expect(errors).toEqual([]);expect(remote).toEqual([]);
    test.info().annotations.push({type:'boundary',description:'Factory Claw Kit v2 source inspection only. This is one purchased tool, not a generated robot or proof of jaw actuation/Pin fit.'});
  } finally { await request.patch('/api/workspace',{headers,data:initial}).catch(()=>{}); }
});
