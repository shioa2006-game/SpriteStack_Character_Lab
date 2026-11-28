"use strict";

async function fixtures() {
  const el = id => document.getElementById(id);
  if (location.protocol === "file:") {
    el("status").textContent = "docs/ をローカルHTTPで配信して chapter1.html を開いてください。";
    return;
  }
  const root = "studies/chapter1/";
  async function json(url) {
    const response = await fetch(url);
    if (!response.ok) throw Error(url);
    return response.json();
  }
  const [sheet, crops, placement, oldSheet, oldCrops, profile] = await Promise.all([
    Lab.loadImage(root+"game.png"),json(root+"game.json"),json(root+"placement.json"),
    Lab.loadImage("studies/objects01/game.png"),json("studies/objects01/game.json"),json("studies/objects01/guildward-scale.json")]);
  const models = {}, panels = {};
  async function load(id,state) {
    const path = "assets/"+id+"/";
    const [img,meta] = await Promise.all([Lab.loadImage(path+state+".png"),json(path+(state==="idle"?"metadata":state)+".json")]);
    return {img,meta,layout:meta.neutral};
  }
  for (const key of Object.keys(crops)) {
    const [id,state] = key.split("/");
    (models[id] ||= {})[state] = await load(id,state);
  }
  const hero = await load("rico","idle"), pillar = await load("stone_pillar","idle");
  const directions = hero.layout.directions;
  const option = (text,value) => new Option(text,value);
  el("yaw").replaceChildren(...directions.map(d=>option(d,d))); el("yaw").value="SW";
  for (const id of Object.keys(models)) {
    const asset = AssetCatalog.assets.find(a=>a.id===id);
    const card = document.createElement("figure"); card.className="fixture";
    const choices = document.createElement("select"); choices.ariaLabel=asset.displayName+"の状態";
    choices.replaceChildren(...asset.views.map(view=>option(view.label,view.id)));
    const canvas = document.createElement("canvas"); canvas.width=156; canvas.height=114;
    canvas.ariaLabel=asset.displayName+"の仮配置";
    const setting=document.createElement("div"); setting.className="setting"; setting.append(canvas);
    const caption=document.createElement("figcaption");
    const link=document.createElement("a"); link.href=Lab.assetUrl(asset); link.textContent=asset.displayName;
    caption.append(link);
    if (choices.length>1) caption.append(choices);
    const extra = document.createElement("select");
    if (id==="stone_statue") {
      extra.ariaLabel="人物の位置"; extra.add(option("リコが手前","front")); extra.add(option("リコが奥","back")); caption.append(extra);
    }
    if (id==="ruin_gate") {
      extra.ariaLabel="灯の組み合わせ";
      for (let mask=0;mask<16;mask++) extra.add(option("灯 "+[0,1,2,3].map(i=>mask & 1<<i ? "●":"○").join(""),String(mask)));
      caption.append(extra);
    }
    card.append(setting,caption); el("scenes").append(card); el("inspect").add(option(asset.displayName,id));
    panels[id]={canvas,choices,extra};
  }
  const game = () => el("camera").value==="game";
  const yaw = () => el("yaw").value;
  function project(x,y,z,dir=yaw()) {
    const t=-directions.indexOf(dir)*Math.PI/4;
    const right=x*Math.cos(t)+y*Math.sin(t), forward=-x*Math.sin(t)+y*Math.cos(t);
    if (game()) {
      const [w,h]=profile.legacy_tile_px, span=Math.SQRT2*profile.tile_model;
      return [right*w/span,forward*h/span-z*profile.legacy_step_px/profile.step_model];
    }
    const {pixels_per_unit:scale,pitch_deg}=hero.meta.camera, pitch=pitch_deg*Math.PI/180;
    return [right*scale,scale*(forward*Math.sin(pitch)-z*Math.cos(pitch))];
  }
  function sprite(ctx,id,state,p,d) {
    if (game() && (models[id] || id==="stone_pillar")) {
      const old=id==="stone_pillar";
      const {rect,offset}=(old?oldCrops:crops)[id+"/"+state][d][0];
      ctx.drawImage(old?oldSheet:sheet,...rect,Math.round(p[0])+offset[0],Math.round(p[1])+offset[1],rect[2],rect[3]);
    } else {
      const item=id==="rico"?hero:id==="stone_pillar"?pillar:models[id][state];
      const {cell:[w,h],anchor:[ax,ay]}=item.layout;
      ctx.drawImage(item.img,directions.indexOf(d)*w,0,w,h,Math.round(p[0])-ax,Math.round(p[1])-ay,w,h);
    }
  }
  const colors={
    flag:["#adb0a4","#787e77","#656c69","#94998d"], stone:["#a7a1a0","#827d80","#676571","#91888a"],
    bank:["#aaab82","#85876e","#6c705c","#969b71"], path:["#b2a58b","#91816c","#766b5b","#a7987f"],
    water:["#80a3ad","#6a909e","#567e89","#b0c8c9"], ice:["#c9dcd9","#9cb5bf","#879fac","#adcbcd"],
    snow:["#e3e6da","#b4c9cb","#98b2bb","#c8d9d5"]
  };
  function renderScene(id) {
    const {canvas,choices,extra}=panels[id],ctx=canvas.getContext("2d");
    const state=choices.value, d=yaw();
    const origin=[77,id==="stone_statue"?84:id==="ruin_gate"?75:66];
    const pt=(x,y,z=0)=>project(x,y,z).map((v,i)=>Math.round(v+origin[i]));
    ctx.fillStyle="#e5e3d8"; ctx.fillRect(0,0,canvas.width,canvas.height);
    function poly(coords,color) {
      ctx.beginPath(); coords.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));
      ctx.closePath(); ctx.fillStyle=color; ctx.fill();
    }
    function line(a,b,color) {
      ctx.strokeStyle=color;ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();
    }
    function block(x,y,z,w,l,h,kind,detail=true) {
      const c=colors[kind];
      const edges=[[-w/2,-l/2],[w/2,-l/2],[w/2,l/2],[-w/2,l/2]];
      const ring=dz=>edges.map(([a,b])=>pt(x+a,y+b,z+dz));
      const top=ring(0), base=ring(-h);
      edges.map((_,i)=>[i,(i+1)%4]).sort(([a,b],[e,f])=>base[a][1]+base[b][1]-base[e][1]-base[f][1])
        .forEach(([a,b])=>poly([base[a],base[b],top[b],top[a]],c[1+a%2]));
      poly(top,c[0]);
      if (detail) {
        line(top[0],top[1],c[3]);line(top[0],top[3],c[3]);
        if (kind==="water" || kind==="ice") line(pt(x-4,y+1,z),pt(x,y+1,z),c[3]);
        else { const q=pt(x-2,y+2,z);ctx.fillStyle=c[3];ctx.fillRect(...q,3,1); }
      }
    }
    const queue=[];
    function queueAt(x,y,fn) { queue.push([project(x,y,0)[1],fn]); }
    const drawAt=(name,s,x,y,z)=>sprite(ctx,name,s,pt(x,y,z),d);
    const isBridge=id==="drawbridge",isWall=id==="iron_ring" || id==="archery_target";
    const isIce=id==="frost_crystal";
    const gate=id==="ruin_gate";
    for(let j=-1;j<=1;j++) for(let i=-1;i<=1;i++) {
      const x=i*14, y=j*14+(isBridge ? 7 : 0);
      const channel=isBridge && j===0;
      const kind=channel?"water":isBridge?(i===0?"path":"bank"):isIce?((i+j)%2?"snow":"ice"):gate?"flag":"stone";
      const z=channel?-7:0;
      queueAt(x,y,()=>block(x,y,z,14,14,channel?1:isBridge?8:3,kind));
    }
    // Draw the terrain first. Props and wall courses are depth sorted together;
    // the mounting face correctly occludes its hardware from the rear.
    queue.sort((a,b)=>a[0]-b[0]).forEach(t=>t[1]());queue.length=0;
    if(isWall) {
      const top=id==="iron_ring"?18:13;
      for(let j=0;j<3;j++) for(let i=-1;i<=1;i++){
        const x=i*8+(j%2)*1.5;
        queueAt(x,-3.55,()=>block(x,-3.55,(j+1)*top/3,7.9,7,top/3-.18,"stone"));
      }
    }
    if(id==="stone_statue") {
      const theta=-directions.indexOf(d)*Math.PI/4;
      const depth=extra.value==="front"?10:-10;
      const x=9*Math.cos(theta)-depth*Math.sin(theta), y=9*Math.sin(theta)+depth*Math.cos(theta);
      queueAt(-16,0,()=>drawAt("stone_pillar","idle",-16,0,0));
      queueAt(x,y,()=>drawAt("rico","idle",x,y,0));
    }
    if(gate) {
      for(const x of [-12,12]) queueAt(x,0,()=>{
        for(const top of [4,8,12]) block(x,0,top,8.5,4,3.9,"stone");
      });
      queueAt(-4,-7,()=>drawAt("rico","idle",-4,-7,0));
    }
    if(isBridge) queueAt(-14,-9,()=>drawAt("rico","idle",-14,-9,0));
    const p=pt(0,0,0), points=placement[id+"/"+state].offsets_px_from_anchor[game()?"game":"lab"][d];
    queueAt(0,isWall?3:0,()=>{
      sprite(ctx,id,state,p,d);
      if(gate) for(let i=0;i<4;i++) {
        if (!(Number(extra.value)&1<<i)) continue;
        const [x,y]=points["r"+(i+1)];ctx.fillStyle="#abedec";ctx.fillRect(p[0]+Math.round(x)-1,p[1]+Math.round(y)-1,3,2);
      }
    });
    queue.sort((a,b)=>a[0]-b[0]).forEach(t=>t[1]());
    if(el("pins").checked) Object.entries(points).forEach(([name,[dx,dy]],i)=>{
      const x=p[0]+Math.round(dx),y=p[1]+Math.round(dy);
      ctx.fillStyle=name==="hook"?"#f7bd55":i?"#00847e":"#af4036";ctx.fillRect(x-2,y,5,1);ctx.fillRect(x,y-2,1,5);
    });
    canvas.style.width=canvas.width*Number(el("zoom").value)+"px";
  }
  function render() {
    Object.keys(models).forEach(renderScene);
    const id=el("inspect").value,state=panels[id].choices.value, view=models[id][state];
    const canvas=el("strip"), step=view.layout.cell[0]+8;
    canvas.width=step*8;canvas.height=step+13;
    const ctx=canvas.getContext("2d");ctx.textAlign="center";ctx.font="10px sans-serif";
    directions.forEach((d,i)=>{
      const ox=step*i+4, p=[ox+view.layout.anchor[0],3+view.layout.anchor[1]];
      ctx.fillStyle=i%2?"#dadbd0":"#e7e6dc";ctx.fillRect(i*step,0,step,canvas.height);
      sprite(ctx,id,state,p,d);ctx.fillStyle="#405447";ctx.fillText(d,i*step+step/2,step+6);
      if(el("pins").checked){ctx.fillStyle="#a34733";ctx.fillRect(p[0]-2,p[1],5,1);ctx.fillRect(p[0],p[1]-2,1,5);}
    });
    canvas.style.width=canvas.width*Number(el("zoom").value)+"px";
    el("coordinates").textContent=Object.entries(placement[id+"/"+state].points_xyz).map(([k,v])=>k+" ("+v.join(", ")+")").join("　");
    el("status").textContent=(game()?"32×16 px・1段8 px":"24°・1.50 px/単位")+"　｜　"+yaw()+"　｜　地形は仮配置";
  }
  document.querySelector("main").addEventListener("change",render);
  render();
}
fixtures().catch(e=>{document.getElementById("status").textContent="読み込みエラー · "+e.message;console.error(e);});
