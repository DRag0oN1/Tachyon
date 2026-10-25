import { readFileSync,writeFileSync } from 'node:fs';
import { test,expect } from '../../web/e2e-support';

test('@generated-development actual architecture recipe renders all geometry and strategy mechanisms',async({page,request,baseURL})=>{
  // Hundreds of original STEP-derived instances and repeated private-catalog
  // requalification make this a slow end-to-end fixture, especially under
  // software WebGL. This is a functional check, not a latency benchmark.
  test.setTimeout(900_000);
  const file=process.env.TACHYON_E2E_SESSION_FILE;
  test.skip(!file || !process.env.TACHYON_E2E_GENERATED_DEVELOPMENT,'Opt-in independently authored generated robot workspace');
  const token=readFileSync(file!,'utf8').trim(),headers={'X-Tachyon-Session':token,Origin:baseURL!};
  const catalog=await(await request.get('/api/catalog',{headers})).json();
  expect(catalog.components.length).toBeGreaterThan(30);
  expect(catalog.components.every((c:{originKind:string;geometryClass:string})=>c.originKind==='tachyon_authored'&&c.geometryClass==='test_fixture')).toBe(true);
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  const mobile=test.info().project.name.includes('mobile');
  await request.patch('/api/workspace',{headers,data:{preferences:{theme:mobile?'shift':'snap',mode:'simple'}}});
  await page.addInitScript(owner=>sessionStorage.setItem('tachyon.owner-session',owner),token);
  await page.goto('/');
  await page.getByRole('button',{name:'Create Robot',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Two ways to support the same strategy',exact:true})).toBeVisible({timeout:40_000});
  await page.locator('.architecture-options button').first().click();
  const realizationReply=page.waitForResponse(r=>r.url().endsWith('/api/designs/realize')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Check parts and realize concept',exact:true}).click();
  const realization=await(await realizationReply).json();
  const status=page.getByTestId('design-status');
  await expect(status).toHaveAttribute('data-state',/ready|failed/,{timeout:100_000});
  await expect(status).toHaveAttribute('data-state','ready');
  const count=Number(await status.getAttribute('data-requested-instance-count'));
  expect(count).toBeGreaterThanOrEqual(474);
  await expect(status).toHaveAttribute('data-resolved-instance-count',String(count));
  await expect(status).toHaveAttribute('data-loaded-instance-count',String(count));
  await expect(status).toHaveAttribute('data-missing-instance-ids','[]');
  await expect(status).toContainText('NOT AUTHENTIC VEX');
  await expect(page.getByTestId('design-canvas')).toBeVisible();
  await page.getByRole('button',{name:'Close Architectures',exact:true}).click();
  await page.locator('canvas').hover();
  if(mobile){
    await page.locator('canvas').dispatchEvent('wheel',{deltaY:-180,deltaMode:0,bubbles:true,cancelable:true});
    test.info().annotations.push({type:'input-limit',description:'Mobile WebKit zoom uses the real dispatched WheelEvent handler; physical phone pinch/pan remain unverified.'});
  }else await page.mouse.wheel(0,-180);
  await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-generated-robot-overview.png`)});
  const canvas=page.locator('canvas');const rect=(await canvas.boundingBox())!;
  const originalScoringFrame=JSON.parse((await canvas.getAttribute('data-scoring-frame-matrix'))!);
  await page.mouse.move(rect.x+rect.width*.7,rect.y+rect.height*.45);
  await page.mouse.down();await page.mouse.move(rect.x+rect.width*.45,rect.y+rect.height*.5,{steps:3});await page.mouse.up();
  await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-generated-robot-reverse.png`)});
  await page.getByRole('button',{name:'Components',exact:true}).click();
  await page.getByRole('button',{name:'Color subsystems',exact:true}).click();
  await expect(page.locator('.subsystem-legend li')).toHaveCount(7);
  await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-generated-robot-subsystems.png`)});
  await page.getByRole('button',{name:'Close Components',exact:true}).click();
  await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-generated-robot-subsystems-overview.png`)});
  await page.getByRole('button',{name:'Components',exact:true}).click();
  await page.getByRole('button',{name:'Color subsystems',exact:true}).click();
  await page.getByRole('button',{name:'Close Components',exact:true}).click();
  await page.getByRole('button',{name:'Strategy',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Low quadrant scoring cycles',exact:true})).toBeVisible();
  const cup=page.locator('.strategy-timeline button').filter({hasText:'Prepare the stack with a Cup'}).first();
  await cup.click();
  await expect(canvas).toHaveAttribute('data-bound-instance-ids',/cup-grip-frame/);
  await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-generated-cup-strategy-highlight.png`)});
  const operationReply=page.waitForResponse(r=>r.url().endsWith('/operation')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Prepare Cup operation',exact:true}).click();
  const reply=await operationReply;expect(reply.status()).toBe(200);
  const operation=await reply.json();
  writeFileSync(test.info().outputPath('operation-model.json'),JSON.stringify(operation));
  expect(operation.validation.graphValid).toBe(true);expect(operation.validation.physicalPerformanceVerified).toBe(false);
  expect(operation.validation.sampleCount).toBe(33);
  await expect(canvas).toHaveAttribute('data-operation-object-count','3',{timeout:30_000});
  // Run the whole sequence against the live scene, including while its panel
  // is dismissed. Stage jumps below separately compare actual drawn matrices.
  await page.getByRole('button',{name:'Play operation',exact:true}).click();
  await page.getByRole('button',{name:'Close Strategy',exact:true}).click();
  await expect(canvas).toHaveAttribute('data-operation-stage','retract',{timeout:35_000});
  await expect(canvas).toHaveAttribute('data-operation-time',String(operation.durationS));
  await expect(canvas).toHaveAttribute('data-operation-object-state','placed');
  await page.getByRole('button',{name:'Strategy',exact:true}).click();
  async function stage(label:string,id:string){
    await page.getByRole('button',{name:'Operation: '+label,exact:true}).click();
    await expect(canvas).toHaveAttribute('data-operation-stage',id);
    const frame=operation.keyframes.find((f:{stageId:string})=>f.stageId===id);
    const observed=JSON.parse((await canvas.getAttribute('data-operation-object-matrix'))!);
    observed.forEach((n:number,i:number)=>expect(n).toBeCloseTo(frame.objectTransform.matrix[i],7));
    const jaw=JSON.parse((await canvas.getAttribute('data-operation-left-jaw-matrix'))!);
    jaw.forEach((n:number,i:number)=>expect(n).toBeCloseTo(frame.worldTransforms['cup-left-jaw'][i],7));
  }
  await stage('Grasp','grip');await expect(canvas).toHaveAttribute('data-operation-object-state','held');
  await stage('Lift','lift');await stage('Transfer','translate');await stage('Place','place');
  await expect(canvas).toHaveAttribute('data-operation-object-state','placed');
  const placed=await canvas.getAttribute('data-operation-object-matrix');
  await page.getByRole('button',{name:'Close Strategy',exact:true}).click();
  await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-generated-cup-placement.png`)});
  await page.getByRole('button',{name:'Strategy',exact:true}).click();
  await stage('Release','open');await stage('Retract','retract');
  await expect(canvas).toHaveAttribute('data-operation-object-matrix',placed!);
  await expect(canvas).not.toHaveAttribute('data-operation-error',/./);
  await page.screenshot({path:test.info().outputPath(`${test.info().project.name}-generated-cup-retained-placement.png`)});
  await page.getByRole('button',{name:'Restore design pose',exact:true}).click();
  await expect(canvas).not.toHaveAttribute('data-operation-object-count','3');
  await page.getByRole('button',{name:'Close Strategy',exact:true}).click();
  await page.getByRole('button',{name:'Expand assistant',exact:true}).click();
  const targetConfiguration=realization.accepted.assembly.configurationId==='raised'?'lower':'raised';
  await page.getByLabel('Design request',{exact:true}).fill(targetConfiguration==='raised'?'Raise scoring height':'Lower scoring height');
  const previewReply=page.waitForResponse(r=>r.url().endsWith('/preview')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Send request',exact:true}).click();
  const preview=await(await previewReply).json();
  expect(preview.revisionId).toBe(realization.revisionId);
  expect(preview.candidate.engineeringHash).not.toBe(preview.accepted.engineeringHash);
  await expect(page.getByRole('button',{name:'Apply',exact:true})).toBeEnabled({timeout:60_000});
  await expect(canvas).toHaveAttribute('data-revision-id',preview.candidate.id);
  const previewScoringFrame=JSON.parse((await canvas.getAttribute('data-scoring-frame-matrix'))!);
  expect(previewScoringFrame).not.toEqual(originalScoringFrame);
  previewScoringFrame.forEach((n:number,i:number)=>expect(n).toBeCloseTo(preview.candidateWorldTransforms['cup-grip-frame'][i],7));
  const discardReply=page.waitForResponse(r=>r.url().endsWith('/decision')&&r.request().postDataJSON()?.action==='discard');
  await page.getByRole('button',{name:'Discard',exact:true}).click();
  const discarded=await(await discardReply).json();
  expect(discarded.revisionId).toBe(realization.revisionId);
  await expect(page.getByRole('button',{name:'Preview '+targetConfiguration,exact:true})).toBeEnabled({timeout:60_000});
  await expect(canvas).toHaveAttribute('data-scoring-frame-matrix',JSON.stringify(originalScoringFrame));
  const secondPreviewReply=page.waitForResponse(r=>r.url().endsWith('/preview')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Preview '+targetConfiguration,exact:true}).click();
  const secondPreview=await(await secondPreviewReply).json();
  await expect(page.getByRole('button',{name:'Apply',exact:true})).toBeEnabled({timeout:60_000});
  const applyReply=page.waitForResponse(r=>r.url().endsWith('/decision')&&r.request().postDataJSON()?.action==='apply');
  await page.getByRole('button',{name:'Apply',exact:true}).click();
  const applied=await(await applyReply).json();
  expect(applied.revisionId).toBe(secondPreview.candidate.id);
  expect(applied.bindings.revisionId).toBe(applied.revisionId);
  await expect(page.getByRole('button',{name:'Undo',exact:true})).toBeEnabled({timeout:60_000});
  await expect(canvas).toHaveAttribute('data-revision-id',applied.revisionId);
  const undoReply=page.waitForResponse(r=>r.url().endsWith('/decision')&&r.request().postDataJSON()?.action==='undo');
  await page.getByRole('button',{name:'Undo',exact:true}).click();
  const undone=await(await undoReply).json();
  expect(undone.accepted.engineeringHash).toBe(realization.accepted.engineeringHash);
  expect(undone.bindings.revisionId).toBe(undone.revisionId);
  await expect(canvas).toHaveAttribute('data-revision-id',undone.revisionId,{timeout:60_000});
  await expect(canvas).toHaveAttribute('data-scoring-frame-matrix',JSON.stringify(originalScoringFrame));
  // The layout effect applies the restored matrix before the next drawn-frame
  // status update. Wait for that confirmation rather than recording a transient
  // zero loaded count while the accepted revision's ready callback is pending.
  await expect(status).toHaveAttribute('data-state','ready',{timeout:30_000});
  await expect(status).toHaveAttribute('data-loaded-instance-count',String(count));
  expect(errors).toEqual([]);
  writeFileSync(test.info().outputPath('generated-scene-evidence.json'),JSON.stringify({
    project:test.info().project.name,designId:realization.designId,requestedPlacements:count,
    resolvedPlacements:Number(await status.getAttribute('data-resolved-instance-count')),
    loadedPlacements:Number(await status.getAttribute('data-loaded-instance-count')),
    uniqueGeometryAssets:Number(await status.getAttribute('data-geometry-asset-count')),
    drawnMeshCount:Number(await status.getAttribute('data-mesh-count')),
    relationships:realization.accepted.assembly.relationships.length,
    strategyBindings:realization.bindings.actions.length,modeledSamples:operation.validation.sampleCount,
    fullPlaybackPassed:true,previewDiscardApplyUndoPassed:true,physicalPerformanceVerified:false,
    authenticVex:false,completeRobot:false,geometry:'independently_authored_development_CAD',browserErrors:errors,
  },null,2));
  test.info().annotations.push({type:'geometry',description:`Actual generated architecture A: ${count} resolved/rendered placements, all independently authored development CAD. No manufacturer source or physical simulation claim.`});
});
