/** Record actual owner-authorized UI behavior to ignored local artifacts.
 * No API mocking, synthetic CAD, credentials in frames, or public upload.
 */
import {webkit} from '../../web/node_modules/playwright/index.mjs';
import {expect} from '../../web/node_modules/@playwright/test/index.mjs';
import {readFileSync,writeFileSync,mkdirSync,renameSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
const folder=process.env.TACHYON_DEMO_OUTPUT??'.local/final-demo/recording';mkdirSync(folder,{recursive:true});
const launch=JSON.parse(readFileSync(process.env.TACHYON_DEMO_LAUNCH_FILE??'.local/runtime/owner-launch-8019.json','utf8'));
const origin=process.env.TACHYON_DEMO_ORIGIN??launch.origin;
if(origin!==launch.origin||!['127.0.0.1','localhost','[::1]'].includes(new URL(origin).hostname))throw Error('Use the exact running loopback studio.');
let browser,context,page,video,step='start',failure;const waits=[],events=[];let baseline;let start=0;const errors=[];
const now=()=>Number(((performance.now()-start)/1000).toFixed(3));
const mark=name=>{step=name;events.push({timeS:now(),step:name});console.log('Recorded:',name);};
const shot=async name=>page.screenshot({path:folder+'/'+name+'.png',animations:'disabled',timeout:120_000});
const hold=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const ready=()=>expect(page.getByTestId('design-status')).toHaveAttribute('data-state','ready',{timeout:120_000});
async function action(name,button,suffix,action){
  mark(name);const began=now();
  const response=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith(suffix)&&r.request().method()==='POST'&&(!action||r.request().postDataJSON()?.action===action),{timeout:120_000});
  await button.click();const reply=await(await response).json();await ready();waits.push({startS:began,endS:now(),reason:name});return reply;
}
try{
 browser=await webkit.launch();context=await browser.newContext({viewport:{width:1440,height:900},recordVideo:{dir:folder,size:{width:1440,height:900}}});page=await context.newPage();video=page.video();start=performance.now();page.setDefaultTimeout(20_000);page.on('pageerror',e=>errors.push(e.message));
 mark('private launch screen');await page.goto(origin);await expect(page.getByRole('heading',{name:'Connect to your studio.',exact:true})).toBeVisible();await hold(1500);
 mark('authorized home');await page.goto(origin+'/#session='+launch.session);await expect(page.getByRole('button',{name:'Generate Strategy',exact:true})).toBeEnabled({timeout:45_000});
 // Presentation preferences only; every engineering revision below is real.
 await page.getByRole('button',{name:'Preferences',exact:true}).click();await page.getByRole('button',{name:/^SNAP/}).click();await page.getByRole('button',{name:/^Simple/}).click();await page.getByRole('button',{name:'Close Preferences',exact:true}).click();
 if(await page.getByRole('button',{name:'Generate Strategy',exact:true}).count()===0)await page.getByRole('button',{name:'Home',exact:true}).click();
 await expect(page.getByTestId('ai-core').getByRole('textbox')).toHaveCount(0);await shot('home');await hold(2500);
 mark('PPO-derived six-phase playbook');await page.getByRole('button',{name:'Generate Strategy',exact:true}).click();await expect(page.locator('.playbook-phase-rail button')).toHaveCount(6,{timeout:60_000});await shot('playbook');await hold(4500);
 mark('two architecture alternatives');await page.getByRole('button',{name:'Design',exact:true}).click();await expect(page.locator('.design-choice')).toHaveCount(2);await shot('two-designs');await hold(2000);
 await page.locator('.design-choice').nth(1).click();await expect(page.getByRole('button',{name:'Review build requirements',exact:true})).toBeVisible();await shot('design-02-concept');await hold(2500);
 await page.locator('.design-choice').nth(0).click();await shot('design-01');
 mark('open actual partial development assembly');const began=now();
 const read=page.waitForResponse(r=>{const p=new URL(r.url()).pathname;return (r.request().method()==='GET'&&p.startsWith('/api/designs/')&&!p.endsWith('/catalog'))||(r.request().method()==='POST'&&p.endsWith('/api/designs/realize'));},{timeout:120_000});
 const open=page.getByRole('button',{name:'Open development CAD',exact:true});if(await open.count())await open.click();else await page.getByRole('button',{name:'Assemble local recipe',exact:true}).click();baseline=await(await read).json();await ready();waits.push({startS:began,endS:now(),reason:'local geometry and recipe qualification'});
 await expect(page.getByRole('dialog',{name:'Design',exact:true})).toHaveCount(0);const count=baseline.accepted.assembly.instances.length;
 await expect(page.getByTestId('design-status')).toHaveAttribute('data-loaded-instance-count',String(count));
 await page.getByTestId('design-status').locator('summary').click();await expect(page.getByTestId('design-status')).toContainText('NOT AUTHENTIC VEX');await hold(2500);await page.getByTestId('design-status').locator('summary').click();
 await shot('snap-actual-assembly');const canvas=page.locator('canvas'),bounds=await canvas.boundingBox();
 await page.mouse.move(bounds.width*.62,bounds.height*.5);await page.mouse.down();await page.mouse.move(bounds.width*.49,bounds.height*.51,{steps:10});await page.mouse.up();await hold(2000);
 mark('actual strategy-to-CAD link');await page.getByRole('button',{name:'Strategy',exact:true}).click();await page.locator('.playbook-phase-rail button[data-action-id="place_alliance"]').first().click();await page.locator('.playbook-phase-actions button[data-action-id="place_cup"]').click();await expect(canvas).toHaveAttribute('data-bound-instance-ids',/cup-grip-frame/);
 await page.locator('.panel-scroll').evaluate(el=>{const h=el.querySelector('.playbook-phase-heading');if(h)el.scrollTop+=h.getBoundingClientRect().top-el.getBoundingClientRect().top;});await shot('strategy-highlight');await hold(3500);await page.getByRole('button',{name:'Close Strategy',exact:true}).click();await page.getByRole('button',{name:'Reset view',exact:true}).click();
 mark('SHIFT full-screen CAD');await page.getByRole('button',{name:'Preferences',exact:true}).click();await page.getByRole('button',{name:/^SHIFT/}).click();await page.getByRole('button',{name:'Close Preferences',exact:true}).click();await shot('shift-actual-assembly');await hold(2500);
 mark('contextual mechanical AI core');await page.getByRole('button',{name:'Expand assistant',exact:true}).click();
 const target=baseline.accepted.assembly.configurationId==='raised'?'lower':'raised';const originalFrame=await canvas.getAttribute('data-scoring-frame-matrix');
 await page.getByLabel('Design request',{exact:true}).fill(target==='raised'?'Raise scoring height':'Lower scoring height');
 const preview=await action('preview actual scoring configuration',page.getByRole('button',{name:'Send request',exact:true}),'/preview');
 await expect(canvas).toHaveAttribute('data-revision-id',preview.candidate.id);expect(await canvas.getAttribute('data-scoring-frame-matrix')).not.toBe(originalFrame);await shot('edit-preview');await hold(2000);
 const applied=await action('apply exact candidate',page.getByRole('button',{name:'Apply',exact:true}),'/decision','apply');expect(applied.revisionId).toBe(preview.candidate.id);await shot('edit-applied');await hold(1500);
 const undone=await action('undo accepted revision',page.getByRole('button',{name:'Undo',exact:true}),'/decision','undo');expect(undone.accepted.engineeringHash).toBe(baseline.accepted.engineeringHash);await expect(canvas).toHaveAttribute('data-scoring-frame-matrix',originalFrame);await shot('edit-undone');await hold(1500);
 await action('second real preview',page.getByRole('button',{name:'Preview '+target,exact:true}),'/preview');
 const discarded=await action('discard preview',page.getByRole('button',{name:'Discard',exact:true}),'/decision','discard');expect(discarded.candidate).toBeNull();expect(discarded.accepted.engineeringHash).toBe(baseline.accepted.engineeringHash);await shot('edit-discarded');await page.getByRole('button',{name:'Close assistant',exact:true}).click();await expect(page.getByTestId('ai-core').getByRole('textbox')).toHaveCount(0);
 mark('mobile SHIFT CAD');await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Reset view',exact:true}).click();await shot('mobile-shift-cad');await hold(2500);
 mark('mobile SNAP playbook');await page.getByRole('button',{name:'Preferences',exact:true}).click();await page.getByRole('button',{name:/^SNAP/}).click();await page.getByRole('button',{name:'Close Preferences',exact:true}).click();await page.getByRole('button',{name:'Strategy',exact:true}).click();await page.locator('.panel-scroll').evaluate(el=>el.scrollTop=0);await shot('mobile-snap-playbook');await hold(2500);
 await page.getByRole('button',{name:'Close Strategy',exact:true}).click();await page.setViewportSize({width:1440,height:900});await page.getByRole('button',{name:'Reset view',exact:true}).click();await hold(2000);
 expect(errors).toEqual([]);mark('verified end');
 writeFileSync(folder+'/evidence.json',JSON.stringify({durationWallS:now(),events,waits,placementCount:count,relationships:baseline.accepted.assembly.relationships.length,geometry:'original Tachyon development CAD, NOT authentic VEX',completeRobot:false,physicalPerformanceVerified:false,secondDesign:'unrealized architectural proposal',policy:'existing frozen PPO; abstract simulation',edits:{preview:true,apply:true,undo:true,discard:true},browserErrors:errors},null,2));
}catch(error){failure=error;const safe=String(error).replaceAll(launch.session,'[REDACTED LOCAL SESSION]');writeFileSync(folder+'/failure.txt','Stage: '+step+'\n'+safe);console.error('Recording failed at:',step);}
finally{if(context)await context.close();if(video){const path=await video.path();renameSync(path,folder+'/raw-demo.webm');}if(browser)await browser.close();}
if(failure)process.exitCode=1;else console.log('Private recording and verification evidence saved.');
