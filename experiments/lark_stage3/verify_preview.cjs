#!/usr/bin/env node
/* Deterministic browser API mock with real PNG decoding and Canvas rasterisation.
 * Not a browser; this validates atlas extraction, world/animation clock, and layout calculations,
 * but not DOM event routing, real device timing, or typographic rendering.
 * Usage: npm install --no-save @napi-rs/canvas; node verify_preview.cjs
 */
'use strict';
const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm'), assert=require('node:assert/strict');
const {createCanvas,loadImage}=require('@napi-rs/canvas');
const root=__dirname, qa=path.join(root,'qa');
const html=fs.readFileSync(path.join(root,'preview.html'),'utf8');
const script=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].at(-1)[1];
const embedded=fs.readFileSync(path.join(root,'preview_assets.js'),'utf8');
class Elem {
 constructor(id){this.id=id;this.events={};this.attrs={};this.style={};this.clientWidth=730;this.hidden=true;this.dataset={};}
 addEventListener(e,f){this.events[e]=f}
 emit(e,data={}){this.events[e]?.(data)}
 setAttribute(k,v){this.attrs[k]=String(v)}
 setPointerCapture(){}
 closest(){return null}
 getContext(...args){return this.canvas.getContext(...args)}
}
async function main(){
 const events={}, queue=[], nodes={};
 const get=id=>nodes[id]??=(new Elem(id));
 const field=get('field'), native=get('native');
 for(const [el,w,h] of [[field,320,208],[native,64,64]]){el.width=w;el.height=h;el.canvas=createCanvas(w,h);}
 for(const [id,val] of Object.entries({zoom:'2',speed:'1',tempo:'1',timing:'authored'}))get(id).value=val;
 get('sync').checked=true;
 const directionButtons=Array.from({length:8},(_,i)=>{const e=new Elem(i);e.dataset.dir=i;return e});
 const document={getElementById:get,querySelectorAll:()=>directionButtons,addEventListener(){}};
 let time=0;
 class Source {
  set src(v){loadImage(v).then(img=>{this.canvas=img;this.onload()}).catch(e=>this.onerror(e));}
 }
 // Only adapt the image object used by the fixture. Canvas's drawImage is the installed native implementation.
 for(const e of [field,native]){
  const c=e.getContext('2d'), draw=c.drawImage.bind(c);
  c.drawImage=(img,...args)=>draw(img.canvas??img,...args);
 }
 const window={addEventListener:(name,f)=>events[name]=f};
 const context=vm.createContext({window,document,Image:Source,performance:{now:()=>time},requestAnimationFrame:f=>queue.push(f),ResizeObserver:class{observe(){}},console});
 vm.runInContext(embedded,context);
 vm.runInContext(script,context);
 const snapshot=()=>JSON.parse(JSON.stringify(window.LARK_PREVIEW_DEBUG.snapshot()));
 for(let i=0;!snapshot().ready&&i<200;i++)await new Promise(r=>setTimeout(r,5));
 assert.equal(snapshot().ready,true,get('error').textContent);
 const tick=(dt=8)=>{time+=dt;const f=queue.shift();assert.ok(f);f(time);};
 const key=(phase,k)=>events[phase]({key:k,target:get('body'),preventDefault(){},repeat:false});
 const near=(a,b,tol=1e-7)=>assert.ok(Math.abs(a-b)<tol,a+' != '+b);
 const sources=window.LARK_ASSETS;
 const dirs=Array.from(sources.directions);
 const result={kind:'Node + @napi-rs/canvas; canvas drawing and input callbacks exercised, not a browser',assets:{},velocities:[],movementRows:[],attacks:[]};
 tick(0);
 assert.equal(snapshot().name,'idle');assert.equal(field.style.width,'640px');
 fs.mkdirSync(qa,{recursive:true});
 const sheet=createCanvas(1000,820), sc=sheet.getContext('2d');sc.fillStyle='#142122';sc.fillRect(0,0,1000,820);sc.font='bold 19px sans-serif';sc.fillStyle='#e1ecdb';sc.fillText('LARK / PNG RUNTIME RASTER TEST',22,27);sc.font='14px sans-serif';
 const [kx,ky]=snapshot().screenScale;
 let line=0;
 const mark=label=>{sc.fillStyle='#c7ddcb';sc.fillText(label,22,61+line*244);};
 const grab=(col)=>{sc.imageSmoothingEnabled=false;sc.drawImage(field.canvas,22+col*324,72+line*244);};
 const size=(a)=>[a.img.canvas.width,a.img.canvas.height];
 const anchorPix=(snap)=>[snap.screenX,snap.screenY];
 const actualFrame=(ver,snap)=>{
   const c=sources[ver][snap.name], [w,h]=c.cell;
   const expected=createCanvas(64,64), ctx=expected.getContext('2d');ctx.imageSmoothingEnabled=false;
   ctx.drawImage(c.img.canvas,snap.i*w,snap.row*h,w,h,32-c.anchor[0],48-c.anchor[1],w,h);
   const a=Buffer.from(native.getContext('2d').getImageData(0,0,64,64).data);
   const b=Buffer.from(ctx.getImageData(0,0,64,64).data);
   assert.ok(a.equals(b),ver+' '+snap.name+' native atlas tile mismatch');
 };
 for(const ver of ['old','new']){
  get(ver).onclick();tick(0);
  assert.equal(get(ver).attrs['aria-pressed'],'true');
  result.assets[ver]={};
  for(const clip of ['idle','walk','attack']){
   const c=sources[ver][clip]; result.assets[ver][clip]=size(c);
   assert.deepEqual(size(c),[c.columns*c.cell[0],(clip==='idle'?1:8)*c.cell[1]]);
  }
  for(const [i,...pressed] of [[0,'s'],[1,'s','a'],[2,'a'],[3,'w','a'],[4,'w'],[5,'w','d'],[6,'d'],[7,'s','d']]){
   get('center').onclick();tick(0);const start=snapshot();
   for(const k of pressed)key('keydown',k);
   for(let j=0;j<12;j++)tick(17);
   const s=snapshot();assert.equal(s.name,'walk');assert.equal(s.direction,i);assert.equal(s.row,i);
   const angle=i*Math.PI/4, stride=sources[ver].walk.suggested_forward_per_frame_model_units??1.9, fps=sources[ver].walk.fps??9;
   const distance=.204*fps*stride;
   near(s.x-start.x,-Math.sin(angle)*distance);near(s.y-start.y,Math.cos(angle)*distance);near(s.walkPhase, .204*fps);
   assert.equal(s.screenX,Math.round(160+s.x*kx));assert.equal(s.screenY,Math.round(104+s.y*ky));
   actualFrame(ver,s);
   for(const k of pressed)key('keyup',k);tick(0);const idle=snapshot();
   assert.equal(idle.name,'idle');assert.equal(idle.direction,i);assert.deepEqual(anchorPix(s),anchorPix(idle));actualFrame(ver,idle);
   result.movementRows.push({ver,dir:dirs[i],row:s.row,walkFrame:s.i,anchorPreserved:true});
  }
  for(const speed of [.6,1,1.6]){
   get('center').onclick();tick(0);get('speed').value=String(speed);
   key('keydown','d');for(let j=0;j<40;j++)tick(25);
   const s=snapshot(), w=sources[ver].walk, stride=w.suggested_forward_per_frame_model_units??1.9, frameRate=w.fps*speed;
   near(s.x, stride*frameRate);near(s.walkPhase,frameRate%w.columns);assert.equal(s.direction,6);
   result.velocities.push({ver,speed,distance_units:s.x,screen_travel_px:s.x*kx,projected_vertical_px:s.x*ky,frameRate,stride});
   actualFrame(ver,s);key('keyup','d');
  }
  get('speed').value='1';get('sync').checked=false;get('tempo').value='.5';get('center').onclick();key('keydown','d');
  for(let j=0;j<20;j++)tick(25);
  near(snapshot().walkPhase,sources[ver].walk.fps*.25);near(snapshot().x,(sources[ver].walk.suggested_forward_per_frame_model_units??1.9)*sources[ver].walk.fps*.5);
  key('keyup','d');get('sync').checked=true;get('tempo').value='1';
  // Face north without walking, then swing in both timing modes.
  directionButtons[4].emit('click',{detail:0});tick(0);const idle=snapshot();
  for(const timing of ['authored','equal']){
   get('timing').value=timing;get('attack').onclick();tick(0);
   const atk=snapshot();assert.deepEqual(atk.anchor,[32,48]);assert.deepEqual(anchorPix(atk),anchorPix(idle));assert.equal(atk.direction,4);
   const a=sources[ver].attack, frames=new Set(), hitTiming=[];
   key('keydown','d');
   while(snapshot().attackTime!==null){
    const s=snapshot();
    if(!frames.has(s.i)){hitTiming.push(s.attackTime);frames.add(s.i);actualFrame(ver,s)}
    near(s.x,idle.x);near(s.y,idle.y);assert.equal(s.direction,4);tick(5);
   }
   const resumed=snapshot();assert.equal(resumed.name,'idle');assert.deepEqual(anchorPix(resumed),anchorPix(idle));
   key('keyup','d');tick(0);
   assert.equal(frames.size,a.columns);
   const durations=a.durations_ms??Array(a.columns).fill(1000/a.fps), total=durations.reduce((s,v)=>s+v,0);
   const wanted=timing==='authored'?durations:Array(a.columns).fill(total/a.columns);
   for(let i=0;i<wanted.length;i++)assert.ok(Math.abs(hitTiming[i]-wanted.slice(0,i).reduce((a,b)=>a+b,0))<=5);
   result.attacks.push({ver,timing,frames:[...frames],sampledStartsMs:hitTiming,totalMs:total});
  }
 }
 get('timing').value='authored';get('speed').value='1';get('center').onclick();tick(0);
 mark('Floor travel / 0.6x - 1.0x - 1.6x (1 second, east)');let col=0;
 for(const speed of [.6,1,1.6]){
  get('center').onclick();get('speed').value=speed;key('keydown','d');for(let j=0;j<40;j++)tick(25);grab(col++);key('keyup','d');tick(0);
 }
 line++; mark('North strike / old poses before, during, after');
 get('old').onclick();get('center').onclick();directionButtons[4].emit('click',{detail:0});get('attack').onclick();tick(0);
 for(col=0;col<3;col++){for(let j=0;j<10;j++)tick(24);grab(col)}
 line++; mark('North strike / improved poses before, during, after');
 get('new').onclick();get('center').onclick();directionButtons[4].emit('click',{detail:0});get('attack').onclick();tick(0);
 for(col=0;col<3;col++){for(let j=0;j<10;j++)tick(24);grab(col)}
 get('zoom').value='3';get('zoom').onchange();assert.equal(field.style.width,'640px');
 get('scene').clientWidth=330;get('zoom').onchange();assert.equal(field.style.width,'320px');
 assert.equal(field.getContext('2d').imageSmoothingEnabled,false);
 assert.equal(get('error').hidden,true);
 fs.writeFileSync(path.join(qa,'preview-raster-test.png'),sheet.toBuffer('image/png'));
 fs.writeFileSync(path.join(qa,'preview-mock-results.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({assets:result.assets,movementRows:result.movementRows.length,velocities:result.velocities,attacks:result.attacks},null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1});
