import {readFileSync} from 'node:fs';
import {test,expect} from '../../web/e2e-support';

test('@demo-launch clean authorization, recovery, refresh and reopening preserve the private boundary',async({page,context,baseURL})=>{
  test.setTimeout(120_000);
  const path=process.env.TACHYON_E2E_LAUNCH_FILE;
  test.skip(!path,'Requires the running server’s private filesystem launch handoff.');
  const launch=JSON.parse(readFileSync(path!,'utf8'));
  // Secrets are used only for the real launch navigation, never assertion text,
  // snapshots, request URLs, browser console output or a mocked API success.
  const ownerUrl=baseURL+'/#session='+launch.session;
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  let protectedReads=0,assetReads=0;
  page.on('request',r=>{const path=new URL(r.url()).pathname;if(path.startsWith('/api/')&&path!=='/api/health')protectedReads++;if(path.startsWith('/api/assets/'))assetReads++;});
  await page.goto('/');await expect(page.getByRole('heading',{name:'Connect to your studio.',exact:true})).toBeVisible();
  await expect(page.getByLabel('Authorized launch URL')).not.toBeVisible();expect(protectedReads).toBe(0);expect(assetReads).toBe(0);
  await expect(page.getByRole('button',{name:'Generate Strategy',exact:true})).toHaveCount(0);
  await page.screenshot({path:test.info().outputPath('clean-connection-screen.png')});
  await page.goto('/#session=expired-local-session');await expect(page.getByRole('alert')).toHaveCount(1);
  await expect(page.getByRole('heading',{name:'Connect to your studio.',exact:true})).toBeVisible();expect(new URL(page.url()).hash).toBe('');
  await page.getByText('Connect with an authorized launch URL',{exact:true}).click();
  await page.getByLabel('Authorized launch URL').fill(ownerUrl);await page.getByRole('button',{name:'Connect to studio',exact:true}).click();
  await expect(page.getByRole('button',{name:'Generate Strategy',exact:true})).toBeEnabled({timeout:45_000});await expect(page.getByRole('alert')).toHaveCount(0);
  expect(new URL(page.url()).hash).toBe('');await page.reload();await expect(page.getByRole('button',{name:'Create Robot',exact:true})).toBeEnabled({timeout:45_000});
  await page.getByRole('button',{name:'Generate Strategy',exact:true}).click();await expect(page.locator('.playbook-phase-rail button')).toHaveCount(6,{timeout:60_000});
  await expect(page.getByRole('alert')).toHaveCount(0);await expect(page.getByTestId('ai-core')).toHaveAttribute('data-state','compact');
  await expect(page.getByTestId('ai-core').getByRole('textbox')).toHaveCount(0);
  await page.screenshot({path:test.info().outputPath('authorized-six-phase-playbook.png'),animations:'disabled'});
  // A new independent page has no tab-scoped credential; launch it explicitly.
  const reopened=await context.newPage();await reopened.goto(baseURL!);await expect(reopened.getByRole('heading',{name:'Connect to your studio.',exact:true})).toBeVisible();
  await reopened.goto(ownerUrl);await expect(reopened.getByRole('button',{name:'Generate Strategy',exact:true})).toBeEnabled({timeout:45_000});
  expect(new URL(reopened.url()).hash).toBe('');expect(errors).toEqual([]);await reopened.close();
});
