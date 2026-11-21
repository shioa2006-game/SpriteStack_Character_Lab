// Mock Canvas and RAF only; this is logic QA, not browser visual QA.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync(require('node:path').join(__dirname,'preview.html'),'utf8').match(/<script>([\s\S]+)<\/script>/)[1];
async function verify(sheets, attackW, attackH) {
  const calls=[], raf=[];
  const mk=()=>({style:{},dataset:{},checked:false,disabled:false,children:[],listeners:{},
    append(b){this.children.push(b)},setAttribute(k,v){this[k]=v},
    addEventListener(k,fn){this.listeners[k]=fn},trigger(k){this.listeners[k]?.({target:this})}});
  const el={};
  const document={getElementById:id=>el[id]??(el[id]=mk()),createElement:mk};
  const c=document.getElementById('sprite');
  c.parentElement={clientWidth:307,clientHeight:272};
  const ctx={clearRect(){},drawImage(image,...r){calls.push([image.src,...r])}};
  c.getContext=()=>ctx;
  document.getElementById('fps').value='8';
  class Image {set src(path){this._src=path;const sz=sheets[path];if(!sz){this.onerror();return;}
      [this.naturalWidth,this.naturalHeight]=sz;this.onload()}
    get src(){return this._src}}
  vm.runInNewContext(script,{document,Image,window:{addEventListener(){}},requestAnimationFrame(fn){raf.push(fn)}});
  await new Promise(resolve=>setImmediate(resolve));
  const dx=(attackW-48)/2,dy=(attackH-48)/2;
  assert.equal(c.width,attackW);assert.equal(c.height,attackH);
  const dir=el.directions.children;
  const [idle,walk,attack]=el.modes.children;
  for(const [i,name] of ['S','SW','W','NW','N','NE','E','SE'].entries()) {
    dir[i].trigger('click');
    assert.deepEqual(calls.at(-1),['output/idle.png',48*i,0,48,48,dx,dy,48,48]);
    assert.equal(c.dataset.direction,name);
  }
  walk.trigger('click');
  assert.deepEqual(calls.at(-1),['output/walk.png',0,7*48,48,48,dx,dy,48,48]);
  for(let i=1;i<=6;i++) {
    el.step.trigger('click'); assert.equal(c.dataset.frame,String(i%6));
    assert.deepEqual(calls.at(-1),['output/walk.png',(i%6)*48,7*48,48,48,dx,dy,48,48]);
  }
  attack.trigger('click');dir[5].trigger('click');
  const sample=(ms)=>{assert.ok(raf.length);raf.shift()(ms)};
  for(let time=0;time<=1000;time+=25)sample(time);
  assert.equal(c.dataset.frame,'5');
  assert.equal(el.toggle.textContent,'もう一度');
  assert.deepEqual(calls.at(-1),['output/attack.png',5*attackW,5*attackH,attackW,attackH,0,0,attackW,attackH]);
  el.toggle.trigger('click');assert.equal(c.dataset.frame,'0');
  el.fps.value='10';el.fps.trigger('input');
  sample(1000);sample(1090);assert.equal(c.dataset.frame,'0');
  sample(1100);assert.equal(c.dataset.frame,'1');
  el.repeat.checked=true;
  for(let time=1125;time<=1600;time+=25)sample(time);
  assert.equal(c.dataset.frame,'0');assert.equal(el.toggle.textContent,'一時停止');
  el.native.checked=true;el.native.trigger('change');
  assert.equal(c.style.width,attackW+'px');
  assert.equal(c.style.height,attackH+'px');
  assert.equal(ctx.imageSmoothingEnabled,false);
  idle.trigger('click'); assert.equal(el.toggle.disabled,true);
}
const sizes={'output/idle.png':[384,48],'output/walk.png':[288,384],'output/attack.png':[288,384]};
(async()=>{
  await verify(sizes,48,48);
  await verify({...sizes,'output/attack.png':[384,512]},64,64);
  console.log('PASS: all 8 directions; idle / walk / attack; frame slicing and padded alignment; pause, step, one-shot, loop, FPS, and 1x mode.');
})().catch(err=>{console.error(err);process.exitCode=1});
