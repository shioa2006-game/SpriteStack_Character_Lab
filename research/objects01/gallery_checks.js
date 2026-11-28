/* Run in the real HTTP viewer from browser_check.py. Exercise the visible controls. */
async ({id}) => {
  const asset = AssetCatalog.assets.find(a => a.id === id);
  const get = key => document.getElementById(key);
  const button = (attr, value) => document.querySelector('[data-'+attr+'="'+value+'"]');
  const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function until(test,label) {
    const start = performance.now();
    while (!test()) {
      if (performance.now()-start > 3500) throw Error(label);
      await delay(10);
    }
  }
  const check = (ok,msg) => { if (!ok) throw Error(id+" "+msg); };
  let cells = 0;
  for (const v of asset.views) {
    const meta = await (await fetch(asset.directory+v.metadata)).json();
    const layout = v.state ? meta.neutral : meta.animations[v.id];
    const sheet = await Lab.loadImage(asset.directory+v.sheet);
    button("motion",v.id).click();
    await until(() => get("status").textContent.startsWith(v.label+" ·"), "load "+v.id);
    if (!v.state) get("play").click();
    for (const a of get("files").querySelectorAll("a")) {
      check((await fetch(a.href)).ok,"file "+a.href);
    }
    const [w,h] = layout.cell;
    const expected = document.createElement("canvas");
    expected.width=w; expected.height=h;
    const ref = expected.getContext("2d",{willReadFrequently:true});
    const real = get("sprite").getContext("2d");
    for (const [row,d] of asset.directions.entries()) {
      button("direction",d).click();
      check(button("direction",d).getAttribute("aria-pressed")==="true",d);
      for (let f=0; f<(v.state ? 1 : layout.columns); f++) {
        ref.clearRect(0,0,w,h);
        ref.drawImage(sheet,(v.state?row:f)*w,(v.state?0:row)*h,w,h,0,0,w,h);
        const a=ref.getImageData(0,0,w,h).data, b=real.getImageData(32,32,w,h).data;
        check(a.every((val,i)=>val===b[i]),v.id+"/"+d+"/"+f+" canvas RGBA");
        if (!v.state) get("next").click();
        cells++;
      }
    }
    if (!v.state) {
      get("previous").click();
      check(get("frame").textContent.startsWith(layout.columns+" /"),"previous");
      const ms = layout.durations_ms.reduce((a,b)=>a+b);
      for (const d of asset.directions) {
        button("direction",d).click();
        button("motion",v.id).click();
        await until(()=>get("status").textContent.startsWith(v.label+" · "+d),"start "+d);
        if (v.next) {
          await until(()=>button("motion",v.next)?.getAttribute("aria-pressed")==="true","single play "+d);
          await until(()=>get("frame").textContent==="1 / 1","held end");
        } else {
          let last=0, wrap=false;
          for (const start=performance.now();performance.now()-start<ms+200;) {
            const f=parseInt(get("frame").textContent);
            if (f<last) wrap=true;
            last=f; await delay(15);
          }
          check(wrap && get("play").textContent==="一時停止","loop "+d);
        }
      }
    }
  }
  const canvas=get("sprite");
  get("floor").click();
  check(get("floor").checked,"floor overlay");
  const neutral=await (await fetch(asset.directory+asset.views[0].metadata)).json();
  const [ax,ay]=neutral.neutral.anchor;
  check(Array.from(canvas.getContext("2d").getImageData(32+ax,32+ay,1,1).data).join()==="155,71,28,255","ground cross");
  const init=canvas.width;
  for (const [key,value] of [["scale","2"],["speed","0.5"]]) {
    get(key).value=value; get(key).dispatchEvent(new Event("change"));
  }
  check(canvas.width===init*2,"integer zoom");
  const motion=asset.views.find(v=>!v.state);
  if (motion) {
    const m=await (await fetch(asset.directory+motion.metadata)).json();
    const ms=m.animations[motion.id].durations_ms.reduce((a,b)=>a+b);
    const start=performance.now();
    button("motion",motion.id).click();
    await until(()=>get("status").textContent.startsWith(motion.label+" ·"),"half speed start");
    if (motion.next) await until(()=>button("motion",motion.next).getAttribute("aria-pressed")==="true","half speed end");
    else {
      await until(()=>parseInt(get("frame").textContent)===m.animations[motion.id].columns,"half speed last");
      await until(()=>parseInt(get("frame").textContent)===1,"half speed wrap");
    }
    const taken=performance.now()-start;
    check(taken>1.8*ms && taken<2.4*ms,"half speed timing "+taken);
  }
  return cells;
}
