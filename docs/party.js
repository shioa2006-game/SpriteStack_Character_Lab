"use strict";

const field = document.querySelector("#field");
const ctx = field.getContext("2d");
const zoom = document.querySelector("#zoom");
const travel = document.querySelector("#travel");
const pause = document.querySelector("#pause");
const repeat = document.querySelector("#repeat");
const scrub = document.querySelector("#scrub");
const state = document.querySelector("#view-state");
const roster = [...document.querySelectorAll("article button[data-member]")];
const directions = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"];
const east = {S: 0, SW: -Math.SQRT1_2, W: -1, NW: -Math.SQRT1_2, N: 0, NE: Math.SQRT1_2, E: 1, SE: Math.SQRT1_2};
const south = {S: 1, SW: Math.SQRT1_2, W: 0, NW: -Math.SQRT1_2, N: -1, NE: -Math.SQRT1_2, E: 0, SE: Math.SQRT1_2};
let actors = [];
let member = "all", dir = "S", motion = "breathe", playing = true;
let time = 0, previous = null, lastDraw = "";
if (matchMedia("(max-width: 680px)").matches) zoom.value = "2";

function buttons(attribute, value) {
  document.querySelectorAll("[data-" + attribute + "]").forEach(button =>
    button.setAttribute("aria-pressed", String(button.dataset[attribute] === value)));
}

function imageAt(url) {
  const image = new Image();
  image.src = url;
  return image.decode().then(() => image);
}

async function readActor(button) {
  const id = button.dataset.member;
  const folder = "assets/" + id + "/";
  const rest = window.spriteStackLayouts[new URL(folder, document.baseURI).href];
  const clips = await Promise.all(Object.entries(rest.clips).map(async ([mode, layout]) =>
    [mode, {...layout, sheet: await imageAt(folder + mode + ".png")}]));
  const actor = {id, name: button.querySelector("strong").textContent, camera: rest.camera,
    clips: Object.fromEntries(clips), mode: "breathe", start: 0, startFrame: 0, stopAt: null,
    step: 0, groundX: 0, groundY: 0};
  return actor;
}

for (const facing of directions) {
  const button = document.createElement("button");
  button.dataset.direction = facing;
  button.textContent = facing;
  button.setAttribute("aria-pressed", String(facing === dir));
  document.querySelector("#directions").append(button);
}

function begin(actor, mode, frame = 0, start = time) {
  actor.mode = mode;
  actor.start = start;
  actor.startFrame = frame;
  actor.step = frame;
  actor.stopAt = null;
  actor.brakeDelta = null;
}

function changeMotion(value, restart = false) {
  if (value === motion && !restart) return;
  motion = value;
  for (const actor of actors) {
    if (value === "walk") {
      // At right heel contact, the forward foot agrees with the stagger of the neutral pose.
      if (actor.mode !== value) begin(actor, value, actor.clips.walk.stance.R[0]);
      actor.stopAt = null;
      actor.brakeDelta = null;
    } else if (playing && actor.mode === "walk") {
      const walk = actor.clips.walk;
      const stops = value === "attack" ? walk.stopping_poses : null;
      const bothFeet = walk.stance.R.filter(i => walk.stance.L.includes(i));
      const phase = (time-actor.start)*walk.fps + actor.startFrame;
      let next = Math.floor(phase);
      actor.brakeDelta = null;
      if (stops?.length) {
        while (!stops.some(s => s.after_frame === next % walk.columns)) next++;
        actor.brakeDelta = stops.find(s => s.after_frame === next % walk.columns).root_delta_xyz;
        next++;
      } else {
        while (!bothFeet.includes(next % walk.columns)) next++;
      }
      actor.stopAt = Math.max(time, actor.start + (next-actor.startFrame)/walk.fps);
    } else if (value === "attack" || actor.mode !== value) begin(actor, value);
  }
  buttons("motion", value);
  travel.disabled = value !== "walk";
  updateState();
}

function updateState() {
  lastDraw = "";
  const who = member === "all" ? "3人の隊列" : actors.find(a => a.id === member)?.name;
  state.textContent = [who, dir, {walk: "歩行", breathe: "待機", attack: "攻撃"}[motion]].filter(Boolean).join("  /  ");
}

document.addEventListener("click", event => {
  const button = event.target.closest("button");
  if (!button || !actors.length) return;
  if (button.dataset.motion) changeMotion(button.dataset.motion, button.dataset.motion === "attack");
  if (button.id === "replay") {
    setPlaying(true);
    repeat.checked = false;
    changeMotion("attack", true);
  }
  if (button.dataset.direction) {
    dir = button.dataset.direction;
    buttons("direction", dir);
    updateState();
  }
  if (button.dataset.member) {
    member = button.dataset.member;
    buttons("member", member);
    updateState();
  }
  if (button === pause) {
    setPlaying(!playing);
  }
});

function setPlaying(value) {
  playing = value;
  previous = null;
  pause.textContent = playing ? "一時停止" : "再生";
  pause.setAttribute("aria-pressed", String(!playing));
  lastDraw = "";
}

repeat.addEventListener("change", () => {
  if (repeat.checked && actors.length) {
    setPlaying(true);
    changeMotion("attack", true);
  }
});

scrub.addEventListener("input", () => {
  if (!actors.length) return;
  setPlaying(false);
  changeMotion("attack", true);
  for (const actor of actors) {
    const durations = actor.clips.attack.durations_ms;
    const index = Math.min(Number(scrub.value)-1, durations.length-1);
    const elapsed = durations.slice(0, index).reduce((a, b) => a+b, 0);
    begin(actor, "attack", 0, time-elapsed/1000);
  }
  draw();
});

travel.addEventListener("change", () => {
  for (const actor of actors) {
    actor.groundX = 0;
    actor.groundY = 0;
  }
  lastDraw = "";
});
zoom.addEventListener("change", () => { lastDraw = ""; });
new ResizeObserver(() => {
  field.width = Math.max(1, field.clientWidth);
  field.height = Math.max(1, field.clientHeight);
  lastDraw = "";
}).observe(field);

// A repeating patch of weathered paving. Draw and scroll it in the same pixel space as the feet.
const paving = document.createElement("canvas");
paving.width = 192;
paving.height = 96;
const stones = paving.getContext("2d");
stones.fillStyle = "#94a08a";
stones.fillRect(0, 0, 192, 96);
let seed = 407;
function random() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
const shades = ["#a8b099","#acb49d","#a6ae98","#a3ad94","#b1b6a0"];
for (let y=0; y<96; y+=12) {
  const offset = y % 24 ? 16 : 0;
  for (let x=-offset; x<192; x+=32) {
    stones.fillStyle = shades[Math.floor(random()*shades.length)];
    stones.fillRect(x+1, y+1, 31, 11);
    stones.fillStyle = "#b7bca5";
    stones.fillRect(x+2, y+1, 19+Math.floor(random()*9), 1);
    stones.fillStyle = "#99a58e";
    stones.fillRect(x+2, y+11, 10+Math.floor(random()*18), 1);
    if (random()>.48) {
      const u=x+3+Math.floor(random()*22), v=y+3+Math.floor(random()*6);
      stones.fillRect(u, v, 2, 1);
    }
    if (random()>.72) {
      stones.fillStyle = "#859878";
      stones.fillRect(x, y+9, 2, 3);
      stones.fillRect(x+2, y+10, 1, 2);
    }
  }
}
const pattern = ctx.createPattern(paving, "repeat");
function ground(w, h, dx, dy) {
  ctx.save();
  ctx.translate(-dx, -dy);
  ctx.fillStyle = pattern;
  ctx.fillRect(dx, dy, w+1, h+1);
  ctx.restore();
}

function paintActor(actor, column, x, y) {
  const clip = actor.clips[actor.mode];
  const row = clip.rows.indexOf(dir);
  const [w, h] = clip.cell;
  const [ax, ay] = clip.anchor;
  ctx.fillStyle = "#52634f55";
  ctx.fillRect(x-9, y-1, 18, 3);
  ctx.fillRect(x-6, y+2, 12, 1);
  ctx.drawImage(clip.sheet, column*w, row*h, w, h, x-ax, y-ay, w, h);
}

function advance(actor, until) {
  if (actor.mode !== "walk") return;
  const clip = actor.clips.walk;
  const step = Math.floor((until-actor.start)*clip.fps + 1e-8) + actor.startFrame;
  if (travel.checked) {
    const distance = (step-actor.step)*clip.suggested_forward_per_frame_model_units*actor.camera.pixels_per_unit;
    actor.groundX += east[dir]*distance;
    actor.groundY += south[dir]*distance*Math.sin(actor.camera.pitch_deg*Math.PI/180);
  }
  actor.step = step;
}

function wrap(position, viewport, padding) {
  const span = viewport + 2*padding;
  return ((position+padding)%span+span)%span-padding;
}

function draw() {
  const scale = Number(zoom.value);
  const w = field.width / scale, h = field.height / scale;
  const shown = actors.filter(actor => member === "all" || actor.id === member);
  if (!shown.length) return;
  for (const actor of actors) {
    // A shortened last step replaces the normal advance on the handoff boundary.
    const lastWalk = actor.stopAt === null ? time : actor.stopAt-(actor.brakeDelta ? 1e-6 : 0);
    advance(actor, Math.min(time, lastWalk));
    if (actor.stopAt !== null && time >= actor.stopAt) {
      if (actor.brakeDelta && travel.checked) {
        const [x,y] = actor.brakeDelta;
        const density = actor.camera.pixels_per_unit;
        actor.groundX += density*(x*south[dir] + y*east[dir]);
        actor.groundY += density*(-x*east[dir] + y*south[dir])*Math.sin(actor.camera.pitch_deg*Math.PI/180);
      }
      begin(actor, motion, 0, actor.stopAt);
    }
    if (actor.mode === "attack") {
      const total = actor.clips.attack.durations_ms.reduce((a,b) => a+b, 0)/1000;
      if (time >= actor.start + total) begin(actor, "breathe", 0, actor.start + total);
    }
  }
  if (motion === "attack" && shown.every(a => a.mode === "breathe" && a.stopAt === null)) {
    changeMotion(repeat.checked ? "attack" : "breathe", true);
  }
  const frames = shown.map(actor => {
    const clip = actor.clips[actor.mode];
    if (actor.mode === "attack") {
      let elapsed = (time - actor.start)*1000 + 1e-6;
      for (let i=0; i<clip.columns-1; i++) {
        if (elapsed < clip.durations_ms[i]) return i;
        elapsed -= clip.durations_ms[i];
      }
      return clip.columns-1;
    }
    return (Math.floor((time-actor.start)*clip.fps)+actor.startFrame) % clip.columns;
  });
  // Follow the first visible walker. Other walkers advance by their own stride at each PNG change.
  const camX = Math.round(shown[0].groundX), camY = Math.round(shown[0].groundY);
  const positions = shown.map(a => [Math.round(a.groundX), Math.round(a.groundY)]);
  const stamp = [field.width,field.height,scale,member,dir,motion,shown.map(a=>a.mode),frames,positions].join("/");
  if (stamp === lastDraw) return;
  lastDraw = stamp;
  scrub.max = Math.max(...shown.map(a => a.clips.attack.columns));
  const attacking = shown.findIndex(a => a.mode === "attack");
  if (attacking >= 0) scrub.value = frames[attacking]+1;
  ctx.setTransform(scale,0,0,scale,0,0);
  ctx.imageSmoothingEnabled = false;
  ground(w,h,camX,camY);
  shown.map((actor,i) => {
    const x = w/2 + (i-(shown.length-1)/2)*Math.min(w*.28,87) + positions[i][0]-camX;
    const y = Math.min(h-3, h/2+25) + positions[i][1]-camY;
    return {actor, frame:frames[i], x:Math.round(wrap(x,w,32)), y:Math.round(wrap(y,h,64))};
  }).sort((a,b)=>a.y-b.y).forEach(p=>paintActor(p.actor,p.frame,p.x,p.y));
  document.querySelector("#frame").textContent = shown.map((a,i) => {
    const clip = a.clips[a.mode];
    return a.name+" "+(frames[i]+1)+"/"+clip.columns+(clip.phase_names ? " "+clip.phase_names[frames[i]] : "");
  }).join("  ·  ");
}

function tick(now) {
  if (previous !== null && playing) time += (now-previous)/1000;
  previous = now;
  draw();
  requestAnimationFrame(tick);
}
document.addEventListener("visibilitychange", () => { previous = null; });
Promise.all(roster.map(readActor)).then(result => {
  actors = result;
  updateState();
  requestAnimationFrame(tick);
}).catch(error => {
  state.textContent = "素材を読み込めません。assets 内の画像と再生データを確認してください。";
  console.error(error);
});
