"use strict";

async function createScaleStudy({el, ctx, canvas, project, draw, label, add, clip, game, facing, directions, profile, json}) {
  const root = "studies/objects01a/scale-study";
  const [sheet, atlas] = await Promise.all([Lab.loadImage(root+".png"), json(root+".json")]);
  const tile = profile.tile_model, step = profile.step_model;
  const pillar = clip("stone_pillar","fallen").meta;
  const oldBeam = clip("stone_pillar","beam").meta.placement.support_center_xyz[2];
  const topple = clip("stone_pillar","topple").layout;
  el("tilt").replaceChildren(...topple.angles_deg.map((a,i) => new Option(a+"°", String(i))), new Option("BEAM × 3","beam"));
  el("tilt").value = "beam";
  const captions = {
    scale: "同じ床に冒険者4人、木箱3案、宝箱、1段に換算したBEAMを並べます。",
    stand: "リコとガルドの足元を、それぞれの支持面の中心に合わせています。",
    steps: "隣接する地面・木箱・2段の台を登ります。淡緑の台は1段、濃緑の台は2段です。",
    stack: "同じ木箱を2個積みます。右の目盛りは地面から地形1段・2段の高さです。",
    rows: "同じ立体を45°刻みで撮影。枠は選択中のカメラです。",
    pillarScale: "同じ転倒姿勢を比較します。右は回転後に高さを換算し、3マスの長さを保ちます。",
  };
  const heights = () => el("specimen").value === "all" ? [14,8,6] : [Number(el("specimen").value)];
  const fitted = () => game() && el("fit").checked;
  const support = h => fitted() ? step : h;
  const names = {14:"旧版 14",8:"採用 8",6:"試作 6"};
  function controls(scene) {
    const active = Object.hasOwn(captions,scene), crates = active && scene !== "pillarScale";
    for (const [name,show] of Object.entries({specimen:crates,fit:crates && game(),marks:active,
      climb:scene === "steps",tilt:scene === "pillarScale"})) el(name+"-label").hidden = !show;
    const info = el("dimensions");
    info.hidden = !active;
    if (active) info.textContent = crates
      ? "幅・奥行 14 × 14 ｜ 箱の底面中心 (0, 0, 0)・セル内アンカー (22, 32) px ｜ 天板中心と積み間隔 z = "+heights().join(" / ")+" ｜ 支持域 ±6.5 ｜ 地形1段 = "+step+(fitted() ? " ｜ 個別換算後の天板は全案8 px" : "")
      : "底面前縁の支点 (0, 7, 0) ｜ 直立 42 → 24 ｜ 横倒し長 42 ｜ BEAM支持高 14 → 8 ｜ 中心間隔 14";
  }
  function sprite(key, point, frame = 0, dir = facing()) {
    const {rect,offset} = atlas[key][dir][frame];
    ctx.drawImage(sheet,...rect, Math.round(point[0])+offset[0], Math.round(point[1])+offset[1], rect[2], rect[3]);
  }
  function box(h,p,dir = facing()) {
    const mode = !game() ? "lab" : fitted() && h !== step ? "fit" : "game";
    sprite(mode+"/"+h+"/idle",p,0,dir);
  }
  function stone(fit,state,p,frame = 0) {
    if (fit === game()) draw("stone_pillar",state,p,frame);
    else sprite((fit ? "lab/pillar-fit/" : "game/pillar-raw/")+state,p,frame);
  }
  function mark(p,top) {
    if (!el("marks").checked) return;
    const [x,y] = p.map(Math.round);
    ctx.fillStyle = top ? "#027671" : "#a44c2e";
    ctx.fillRect(x-2,y,5,1); ctx.fillRect(x,y-2,1,5);
  }
  const up = (p,z) => add(p,project(0,0,z));
  const xAt = (i,n) => (i+.5)*canvas.width/n;
  function terrain(base,z,color) {
    const corners = [[-1,-1],[1,-1],[1,1],[-1,1]];
    const ring = h => corners.map(([x,y]) => add(base,project(x*tile/2,y*tile/2,h)));
    const lower = ring(0), upper = ring(z);
    function polygon(points, fill) {
      ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.closePath();
      ctx.fillStyle=fill; ctx.fill(); ctx.strokeStyle="#697964"; ctx.stroke();
    }
    corners.map((_,i) => [i,(i+1)%4]).sort(([a,b],[c,d]) =>
      lower[a][1]+lower[b][1]-lower[c][1]-lower[d][1]).forEach(([a,b]) => {
      polygon([lower[a],lower[b],upper[b],upper[a]],a%2 ? "#8e9a82" : "#a0ab91");
    });
    polygon(upper,color);
  }
  function paint(scene) {
    const hs = heights();
    if (scene === "scale") {
      const items = ["gard","rico","sena","tobi",...hs,"treasure_chest","beam"];
      items.forEach((id,i) => {
        const p = [xAt(i,items.length),113];
        if (typeof id === "number") box(id,p);
        else if (id === "beam") stone(true,"beam",p);
        else draw(id,"idle",p);
        label(names[id] || (id === "beam" ? "BEAM · 1段" : clip(id).asset.displayName),p[0],143);
        mark(p,false);
        if (typeof id === "number" || id === "beam") mark(up(p,id === "beam" ? step : support(id)),true);
      });
    } else if (scene === "stand") {
      const platforms = [...hs,"beam"];
      platforms.forEach((h,i) => {
        const middle = xAt(i,platforms.length);
        ["rico","gard"].forEach((hero,j) => {
          const p = [middle+(j ? 21 : -21),114];
          const top = up(p,h === "beam" ? step : support(h));
          if (h === "beam") stone(true,"beam",p); else box(h,p);
          draw(hero,"idle",top); mark(p,false); mark(top,true);
        });
        label(names[h] || "BEAM · 1段",middle,145);
      });
    } else if (scene === "steps") {
      hs.forEach((h,i) => {
        const origin = [xAt(i,hs.length),115];
        const pads = [[0,1,0,"ground"],[0,0,support(h),"crate"],[0,-1,2*step,"ledge"],[1,-1,step,"one"]]
          .map(([x,y,z,id]) => ({p:add(origin,project(x*tile,y*tile)),z,id}));
        pads.sort((a,b) => a.p[1]-b.p[1]).forEach(({p,z,id}) => {
          if (id === "crate") box(h,p);
          else terrain(p,z,id === "ledge" ? "#8ca28a" : id === "one" ? "#c1cbb1" : "#dedbc6");
          if (id === el("climb").value) draw("rico","idle",up(p,z));
          mark(p,false); mark(up(p,z),true);
        });
        label(names[h],origin[0],150);
      });
    } else if (scene === "stack") {
      hs.forEach((h,i) => {
        const p = [xAt(i,hs.length),120], z = support(h);
        box(h,p); box(h,up(p,z)); draw("rico","idle",up(p,2*z));
        mark(p,false); mark(up(p,z),true); mark(up(p,2*z),true);
        const ruler = [p[0]+22,p[1]];
        ctx.fillStyle="#697964";
        ctx.fillRect(Math.round(ruler[0]),Math.round(up(ruler,step*2)[1]),1,1+Math.round(-project(0,0,step*2)[1]));
        for (let k=0;k<=2;k++) ctx.fillRect(Math.round(ruler[0]),Math.round(up(ruler,k*step)[1]),5,1);
        label(names[h]+" × 2",p[0],149);
      });
    } else if (scene === "rows") {
      directions.forEach((d,j) => {
        const x = 94+j*65;
        if (d === facing()) { ctx.fillStyle="#709b8122"; ctx.fillRect(x-26,10,52,canvas.height-20); }
        label(d,x,31);
        hs.forEach((h,i) => {
          const y = 60+(i+.5)*147/hs.length, p = [x,y];
          if (!j) label(names[h],35,y-5);
          box(h,p,d); mark(p,false); mark(up(p,support(h)),true);
        });
      });
    } else {
      const beam = el("tilt").value === "beam", f = Number(el("tilt").value);
      [false,true].forEach((fit,i) => {
        const p = [xAt(i,2),112], z = fit ? step : oldBeam;
        if (beam) {
          const centers = pillar.placement.support_centers_xyz.map(([x,y],j) => ({p:add(p,project(x,y)),j}));
          centers.sort((a,b) => a.p[1]-b.p[1]).forEach(({p:base,j}) => {
            stone(fit,"beam",base); if (j === 1) draw("rico","idle",up(base,z));
            mark(base,false); mark(up(base,z),true);
          });
        } else {
          stone(fit,"topple",p,f);
          const [x,y] = pillar.rotation.pivot_xyz;
          mark(add(p,project(x,y)),false);
        }
        label(fit ? "高さ換算 · 24 / BEAM 8" : "原モデル · 42 / BEAM 14",p[0],151);
      });
      return beam ? "BEAM × 3" : topple.angles_deg[f]+"°";
    }
    return (game() ? "32×16" : "24°")+" · "+(fitted() ? "個別1段換算" : "共通尺度");
  }
  return {captions, controls, paint};
}
