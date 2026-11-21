/* Uses installed Playwright/Chromium, a loopback HTTP server, and real key events.
 * Usage: node verify_browser.cjs [chromium executable] [HTML filename]
 */
const fs=require('node:fs'), http=require('node:http'), path=require('node:path'), assert=require('node:assert/strict');
const {chromium}=require('playwright');
async function run(){
 const root=__dirname;
 const server=http.createServer((req,res)=>{
  const p=path.resolve(root,'.'+decodeURIComponent(req.url.split('?')[0]));
  if(!p.startsWith(root+'/')||!fs.existsSync(p)||!fs.statSync(p).isFile()){res.writeHead(404).end();return}
  res.setHeader('content-type',{'.html':'text/html;charset=UTF-8','.js':'application/javascript','.png':'image/png'}[path.extname(p)]??'application/octet-stream');fs.createReadStream(p).pipe(res);
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 let browser;
 try{
 browser=await chromium.launch({executablePath:process.argv[2]??'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1200,height:900},deviceScaleFactor:1}); const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:'+server.address().port+'/'+(process.argv[3]??'preview.html'));
 await page.waitForFunction(()=>window.LARK_PREVIEW_DEBUG?.snapshot().ready);
 const snapshot=()=>page.evaluate(()=>window.LARK_PREVIEW_DEBUG.snapshot());
 const eventually=(key,val)=>page.waitForFunction(([k,v])=>LARK_PREVIEW_DEBUG.snapshot()[k]===v,[key,val]);
 const focus=()=>page.evaluate(()=>document.activeElement.blur());
 const initial=await snapshot(); assert.equal(initial.name,'idle'); assert.deepEqual(initial.anchor,[24,40]); assert.equal(initial.zoom,2);
 const tallies={browser:browser.version(), viewport:[1200,900], preview:process.argv[3]??'preview.html', initial};
 for(const [dir,...pressed] of [[0,'s'],[1,'s','a'],[2,'a'],[3,'w','a'],[4,'w'],[5,'w','d'],[6,'d'],[7,'s','d']]){
  const prev=await snapshot();
  for(const k of pressed)await page.keyboard.down(k);
  await eventually('direction',dir); await eventually('name','walk'); await page.waitForTimeout(55);
  const walk=await snapshot(); assert.ok(walk.steps>prev.steps);
  for(const k of pressed)await page.keyboard.up(k);
  await eventually('name','idle'); assert.equal((await snapshot()).direction,dir);
 }
 const velocities=[];
 for(const speed of [0.6,1,1.6]){
  await page.selectOption('#speed',String(speed).replace(/^0\./,'.')); await page.locator('#center').click(); await focus();
  const start=await snapshot(), t0=Date.now(), frames=new Set();
  await page.keyboard.down('d');
  for(let i=0;i<20;i++){await page.waitForTimeout(15);let s=await snapshot();if(s.name==='walk')frames.add(s.i)}
  await page.keyboard.up('d'); await eventually('name','idle');
  const end=await snapshot(); assert.ok(end.x>start.x); assert.ok(Math.abs(end.y)<1e-7);
  velocities.push({speed,distance:end.x-start.x,rateApprox:(end.x-start.x)*1000/(Date.now()-t0),frames:[...frames].sort()});
 }
 assert.ok(velocities[0].rateApprox<velocities[1].rateApprox&&velocities[1].rateApprox<velocities[2].rateApprox);
 tallies.speed=velocities;
 await page.locator('#center').click();await focus();await page.keyboard.down('w');await page.waitForTimeout(110);await page.keyboard.up('w');await eventually('name','idle');
 const idle=await snapshot(); assert.equal(idle.direction,4);
 const attacks=[];
 await page.selectOption('#tempo','.5');
 for(const version of ['old','new']){
  await page.locator('#'+version).click();
  assert.equal((await snapshot()).version,version);assert.equal((await snapshot()).x,idle.x);assert.equal((await snapshot()).y,idle.y);
  for(const timing of ['authored','equal']){
   await page.selectOption('#timing',timing);await page.locator('#attack').click();await eventually('name','attack');
   const onset=await snapshot();assert.deepEqual(onset.anchor,[32,48]);assert.equal(onset.x,idle.x);assert.equal(onset.y,idle.y);
   const observedFrames=new Set([onset.i]);
   await page.keyboard.down('d');
   while(true){
    const s=await snapshot();
    if(s.name!=='attack')break;
    assert.equal(s.direction,4);assert.equal(s.x,idle.x);assert.equal(s.y,idle.y);
    observedFrames.add(s.i);await page.waitForTimeout(14);
   }
   await page.keyboard.up('d');await eventually('name','idle');
   const n=await page.evaluate(v=>LARK_ASSETS[v].attack.columns,version);
   assert.equal(observedFrames.size,n);
   attacks.push({version,timing,nominalBaseMs:onset.attackDuration,firstAttackDrawMs:onset.firstAttackDrawMs,frames:[...observedFrames]});
  }
 }
 tallies.attacks=attacks;
 await page.locator('#center').click();await page.selectOption('#zoom','1');await eventually('zoom',1);
 assert.deepEqual(await page.locator('#field').evaluate(c=>[c.clientWidth,c.clientHeight]),[320,208]);
 await page.selectOption('#zoom','2');await eventually('zoom',2);
 assert.deepEqual(await page.locator('#field').evaluate(c=>[c.clientWidth,c.clientHeight]),[640,416]);
 await page.selectOption('#tempo','1');await page.selectOption('#timing','authored');await page.selectOption('#speed','1');
 await page.locator('#anchor').check();await focus();await page.keyboard.down('a');await page.waitForTimeout(220);await page.keyboard.up('a');await eventually('name','idle');
 await page.keyboard.press('j');await eventually('name','attack');
 await page.waitForFunction(()=>LARK_PREVIEW_DEBUG.snapshot().i>=2);
 const css=await page.locator('#field').evaluate(c=>[getComputedStyle(c).imageRendering,c.getContext('2d').imageSmoothingEnabled]);
 assert.deepEqual(css,['pixelated',false]);
 fs.mkdirSync(path.join(root,'qa'),{recursive:true});
 await page.screenshot({path:path.join(root,'qa','chromium-preview.png')});
 await page.setViewportSize({width:390,height:844});await eventually('zoom',1);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
 assert.deepEqual(errors,[]);
 tallies.screen={origCell:48,attackCell:64,anchorPreserved:true,integerZoom:true,mobileWidth390NoOverflow:true};
 tallies.pageErrors=errors;
 fs.writeFileSync(path.join(root,'qa','chromium-results.json'),JSON.stringify(tallies,null,2)+'\n');
 console.log(JSON.stringify(tallies,null,2));
 } finally {
  if(browser)await browser.close();
  await new Promise(r=>server.close(r));
 }
}
run().catch(e=>{console.error(e);process.exitCode=1});
