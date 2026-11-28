"use strict";

async function study() {
  const el = id => document.getElementById(id);
  if (location.protocol === "file:") {
    el("caption").textContent = "比較画面はリポジトリのローカルHTTPで開いてください。";
    const link = document.createElement("a");
    link.href = "http://127.0.0.1:8000/object-study.html";
    link.textContent = "ローカルHTTPで比較";
    el("projection-note").append(link);
    return;
  }
  const canvas = el("study"), ctx = canvas.getContext("2d");
  const actors = ["gard", "rico", "sena", "tobi"];
  const props = ["wooden_crate", "treasure_chest", "boulder", "stone_pillar"];
  const clips = new Map();
  async function json(url) {
    const result = await fetch(url);
    if (!result.ok) throw new Error(url);
    return result.json();
  }
  const base = "studies/objects01/";
  const [atlas, rectangles, profile] = await Promise.all([Lab.loadImage(base + "game.png"), json(base + "game.json"), json(base + "guildward-scale.json")]);
  await Promise.all([...actors, ...props].map(async id => {
    const asset = AssetCatalog.assets.find(a => a.id === id);
    await Promise.all(asset.views.filter(v => props.includes(id) || v.id === "idle").map(async view => {
      const [sheet, meta] = await Promise.all([Lab.loadImage(asset.directory + view.sheet), json(asset.directory + view.metadata)]);
      const layout = view.state ? meta.neutral : meta.animations[view.id];
      clips.set(id + "/" + view.id, { asset, view, sheet, meta, layout });
    }));
  }));
  const clip = (id, state = "idle") => clips.get(id + "/" + state);
  const reference = clip("wooden_crate").meta;
  const tile = reference.geometry.tile_pitch_model;
  const directions = reference.neutral.directions;
  el("facing").replaceChildren(...directions.map(d => new Option(d, d)));
  el("facing").value = "SW";
  let scene = "size", elapsed = 0, playing = false, request = 0, last = 0;
  const game = () => el("projection").value === "game";
  const facing = () => el("facing").value;
  function project(x, y, z = 0) {
    const yaw = reference.camera_yaw_deg[facing()] * Math.PI/180;
    const lateral = x*Math.cos(yaw) + y*Math.sin(yaw);
    const forward = -x*Math.sin(yaw) + y*Math.cos(yaw);
    if (game()) {
      const [w,h] = profile.legacy_tile_px;
      return [w*lateral/(Math.SQRT2*tile), h*forward/(Math.SQRT2*tile)-z*profile.legacy_step_px/profile.step_model];
    }
    const pitch = reference.camera.pitch_deg * Math.PI/180, scale = reference.camera.pixels_per_unit;
    return [scale*lateral, scale*(forward*Math.sin(pitch) - z*Math.cos(pitch))];
  }
  function draw(id, state, point, frame = 0, direction = facing()) {
    const item = clip(id, state);
    const pos = point.map(Math.round);
    if (game() && props.includes(id)) {
      const {rect, offset} = rectangles[id + "/" + state][direction][frame];
      ctx.drawImage(atlas, ...rect, pos[0]+offset[0], pos[1]+offset[1], rect[2], rect[3]);
      return;
    }
    const l = item.layout, [w,h] = l.cell;
    const dir = (item.view.state ? l.directions : l.rows).indexOf(direction);
    ctx.drawImage(item.sheet, (item.view.state ? dir : frame)*w, (item.view.state ? 0 : dir)*h, w, h,
      pos[0]-l.anchor[0], pos[1]-l.anchor[1], w, h);
  }
  const add = (a,b) => [a[0]+b[0], a[1]+b[1]];
  function floor(origin) {
    ctx.fillStyle = "#e7e5d7";
    ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.strokeStyle = "#d0d0c0";
    ctx.lineWidth = 1;
    ctx.beginPath();
    const limit = 48*tile;
    for (let i = -48; i <= 48; i++) {
      const offset = (i+.5)*tile;
      for (const [a,b] of [[[offset,-limit],[offset,limit]],[[-limit,offset],[limit,offset]]]) {
        ctx.moveTo(...add(origin,project(...a)));
        ctx.lineTo(...add(origin,project(...b)));
      }
    }
    ctx.stroke();
  }
  function tileMark(origin, y) {
    ctx.beginPath();
    for (const [i,[x,dy]] of [[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].entries()) {
      const p = add(origin, project(x*tile,(y+dy)*tile));
      if (!i) ctx.moveTo(...p); else ctx.lineTo(...p);
    }
    ctx.closePath(); ctx.fillStyle="#9dad916b"; ctx.fill(); ctx.strokeStyle="#89997f"; ctx.stroke();
  }
  function label(name, x, y) {
    ctx.fillStyle = "#425448"; ctx.font = "11px 'Segoe UI', sans-serif"; ctx.textAlign = "center";
    ctx.fillText(name, x, y);
  }
  function frameAt(item, time) {
    let end = 0;
    const frame = item.layout.durations_ms.findIndex(ms => (end += ms) > time);
    return frame < 0 ? item.layout.columns-1 : frame;
  }
  const duration = item => item.layout.durations_ms.reduce((a,b) => a+b);
  const chest = clip("treasure_chest", "opening"), fall = clip("stone_pillar", "topple");
  const roll = clip("boulder","roll");
  const scaleStudy = await createScaleStudy({el, ctx, canvas, project, draw, label, add, clip, game, facing,
    directions, profile, json});
  const captions = {
    size: "同じ床面に冒険者4人と4種類のオブジェクトを配置。",
    crate: "木箱の天板中心にリコの足元を合わせる。右は2段積み。",
    chest: "蝶番を支点に丸蓋を開き、空の状態を保持。",
    roll: "床上の移動距離から回転角を取り出す。色の違う岩肌が目印。",
    bridge: "柱の前縁を支点に転倒。着地後、選んだ長さの足場にリコが立つ。",
    ...scaleStudy.captions,
  };
  function paint() {
    const origin = [296,106];
    floor(origin);
    let status = "";
    if (scene in scaleStudy.captions) {
      status = scaleStudy.paint(scene);
    } else if (scene === "size") {
      [...actors,...props].forEach((id,i) => {
        const x = 46+i*71, pos = [x,110];
        draw(id,"idle",pos);
        label(clip(id).asset.displayName,x,143);
      });
    } else if (scene === "crate") {
      const top = project(...reference.placement.support_center_xyz);
      for (const [i,count] of [1,2].entries()) {
        const base = [205+182*i,120];
        let on = base;
        for (let j=0; j<count; j++) { draw("wooden_crate","idle",on); on = add(on,top); }
        draw("rico","idle",on);
        label(count+" 段",base[0],151);
      }
    } else if (scene === "chest") {
      const opened = elapsed >= duration(chest);
      const f = frameAt(chest,elapsed);
      draw("treasure_chest",opened ? "open" : "opening",origin,opened ? 0 : f);
      status = opened ? "OPEN" : chest.layout.angles_deg[f]+"°";
    } else if (scene === "roll") {
      const radius = roll.meta.rotation.rolling_radius_model;
      const travel = elapsed*.045 % (4*Math.PI*radius);
      const phase = (360*travel/(2*Math.PI*radius)) % 360;
      const frame = roll.layout.angles_deg.findLastIndex(a => a <= phase);
      const center = travel - 2*Math.PI*radius;
      draw("boulder","roll",add(origin,project(0,center,0)),frame);
      status = roll.layout.angles_deg[frame]+"°";
    } else {
      const count = Number(el("length").value);
      for (let j=0; j<=count; j++) tileMark(origin,j);
      if (elapsed < duration(fall)) {
        const f = frameAt(fall,elapsed);
        draw("stone_pillar","topple",origin,f);
        status = fall.layout.angles_deg[f]+"°";
      } else if (elapsed < duration(fall)+320) {
        draw("stone_pillar","fallen",origin);
        status = "FALLEN";
      } else {
        const centers = clip("stone_pillar","fallen").meta.placement.support_centers_xyz.slice(0,count);
        const sourceScale = game() ? profile.step_model/profile.legacy_source_units_per_step.stone_pillar : 1;
        const stones = centers.map(([x,y,z]) => ({ base:add(origin,project(x,y)), top:add(origin,project(x,y,z*sourceScale)) }));
        const withActor = stones[stones.length-1];
        // Back-to-front compositing, including a walker on a far segment.
        for (const stone of stones.sort((a,b) => a.base[1]-b.base[1])) {
          draw("stone_pillar","beam",stone.base);
          if (stone === withActor) draw("rico","idle",stone.top);
        }
        status = "BEAM × "+count;
      }
    }
    el("pose").textContent = status;
    canvas.setAttribute("aria-label", captions[scene]+" "+facing()+" "+status);
  }
  function tick(now) {
    elapsed += Math.max(0,now-last); last = now;
    if ((scene === "chest" && elapsed >= duration(chest)) ||
        (scene === "bridge" && elapsed >= duration(fall)+320)) playing = false;
    paint();
    if (playing) request = requestAnimationFrame(tick);
    else el("play").textContent = "再生";
  }
  function play(value) {
    cancelAnimationFrame(request);
    playing = value; last = performance.now();
    el("play").textContent = value ? "一時停止" : "再生";
    if (value) request = requestAnimationFrame(tick);
  }
  function select(id) {
    scene = id; elapsed = 0;
    canvas.height = id === "rows" ? 222 : 172;
    scaleStudy.controls(id);
    const moving = ["chest","roll","bridge"].includes(scene);
    el("length-label").hidden = scene !== "bridge";
    el("play").hidden = el("restart").hidden = !moving;
    for (const button of el("scenes").querySelectorAll("button")) button.setAttribute("aria-pressed",String(button.dataset.scene === scene));
    el("caption").textContent = captions[id];
    options(); play(moving);
  }
  function options() {
    canvas.style.width = canvas.width*Number(el("zoom").value)+"px";
    scaleStudy.controls(scene);
    el("projection-note").textContent = game()
      ? "SWは現行の32×16 px投影。1段8 pxを保ち、同じ立体を45°刻みで再投影します。冒険者は原寸です。"
      : "1マス14モデル単位。冒険者と物体を仰角24°、1.50 px/モデル単位で表示しています。";
    paint();
  }
  el("options").addEventListener("change",options);
  el("scenes").onclick = event => { if (event.target.dataset.scene) select(event.target.dataset.scene); };
  el("restart").onclick = () => select(scene);
  el("play").onclick = () => {
    if (!playing && ((scene === "chest" && elapsed >= duration(chest)) ||
        (scene === "bridge" && elapsed >= duration(fall)+320))) elapsed = 0;
    play(!playing);
  };
  document.addEventListener("visibilitychange", () => { last = performance.now(); });
  const initial = new URLSearchParams(location.search).get("scene");
  select(Object.hasOwn(captions,initial) ? initial : "size");
}

study().catch(error => {
  document.getElementById("caption").textContent = "比較用の素材を読み込めませんでした。";
  console.error(error);
});
