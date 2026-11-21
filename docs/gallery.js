"use strict";

const canvas = document.querySelector("#sprite");
const context = canvas.getContext("2d");
const status = document.querySelector("#status");
const frameLabel = document.querySelector("#frame");
const scale = document.querySelector("#scale");
const speed = document.querySelector("#speed");
const replay = document.querySelector("#replay");
const motionButtons = [...document.querySelectorAll("[data-motion]")];
const directionButtons = [...document.querySelectorAll("[data-direction]")];

const sheets = new Map();
let layouts;
let viewport;
let motion = "idle";
let direction = "SW";
let active = null;
let selection = 0;
let animation;

function loadSheet(name) {
  if (!sheets.has(name)) {
    const loaded = new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(name));
      image.src = "assets/" + name + ".png";
    }).catch(error => {
      sheets.delete(name);
      throw error;
    });
    sheets.set(name, loaded);
  }
  return sheets.get(name);
}

function configure(metadata) {
  layouts = {
    idle: { ...metadata.neutral, columns: 1 },
    ...metadata.animations,
  };
  viewport = {
    width: Math.max(...Object.values(layouts).map(layout => layout.cell[0])),
    height: Math.max(...Object.values(layouts).map(layout => layout.cell[1])),
    anchorX: Math.max(...Object.values(layouts).map(layout => layout.anchor[0])),
    anchorY: Math.max(...Object.values(layouts).map(layout => layout.anchor[1])),
  };
}

function draw() {
  if (!active) return;
  const { name, layout, image, facing, frame } = active;
  const [width, height] = layout.cell;
  const idle = name === "idle";
  const column = idle ? layout.directions.indexOf(facing) : frame;
  const row = idle ? 0 : layout.rows.indexOf(facing);
  const zoom = Number(scale.value);
  const x = (viewport.anchorX - layout.anchor[0]) * zoom;
  const y = (viewport.anchorY - layout.anchor[1]) * zoom;

  context.clearRect(0, 0, canvas.width, canvas.height);
  context.imageSmoothingEnabled = false;
  context.drawImage(image, column * width, row * height, width, height,
    x, y, width * zoom, height * zoom);
  frameLabel.textContent = (frame + 1) + " / " + layout.columns;
}

function resize() {
  if (!viewport) return;
  canvas.width = viewport.width * Number(scale.value);
  canvas.height = viewport.height * Number(scale.value);
  draw();
}

function animate(now) {
  const clip = active;
  clip.elapsed += (now - clip.lastTick) * Number(speed.value);
  clip.lastTick = now;
  const timeline = clip.layout.durations_ms;
  let frame = 0;
  if (timeline) {
    let end = timeline[frame];
    while (frame < timeline.length - 1 && clip.elapsed >= end) {
      frame += 1;
      end += timeline[frame];
    }
  } else {
    frame = Math.floor(clip.elapsed * clip.layout.fps / 1000) % clip.layout.columns;
  }
  if (frame !== clip.frame) {
    clip.frame = frame;
    draw();
  }
  if (clip.layout.loop || clip.elapsed < clip.duration) {
    animation = requestAnimationFrame(animate);
  }
}

async function showSelection() {
  if (!layouts) return;
  const ticket = ++selection;
  const name = motion;
  const facing = direction;
  const layout = layouts[name];
  cancelAnimationFrame(animation);
  speed.disabled = name === "idle";
  replay.hidden = name !== "attack";
  const label = motionButtons.find(button => button.dataset.motion === name).textContent;
  status.textContent = label + " · " + facing;
  try {
    const image = await loadSheet(name);
    if (ticket !== selection) return;
    active = {
      name, facing, layout, image, frame: 0, elapsed: 0, lastTick: performance.now(),
      duration: layout.durations_ms?.reduce((total, ms) => total + ms, 0),
    };
    canvas.setAttribute("aria-label", "LARK " + status.textContent);
    draw();
    if (name !== "idle") animation = requestAnimationFrame(animate);
  } catch {
    if (ticket !== selection) return;
    active = null;
    context.clearRect(0, 0, canvas.width, canvas.height);
    frameLabel.textContent = "";
    status.textContent = "画像を読み込めませんでした";
  }
}

for (const button of motionButtons) {
  button.addEventListener("click", () => {
    motion = button.dataset.motion;
    for (const option of motionButtons) option.setAttribute("aria-pressed", option === button);
    showSelection();
  });
}

for (const button of directionButtons) {
  button.addEventListener("click", () => {
    direction = button.dataset.direction;
    for (const option of directionButtons) option.setAttribute("aria-pressed", option === button);
    showSelection();
  });
}

replay.addEventListener("click", showSelection);
scale.addEventListener("change", resize);

async function start() {
  try {
    const [metadata] = await Promise.all([
      fetch("assets/metadata.json").then(response => {
        if (!response.ok) throw new Error("metadata");
        return response.json();
      }),
      loadSheet("idle"),
    ]);
    configure(metadata);
    resize();
    await showSelection();
  } catch {
    status.textContent = "初期素材を読み込めませんでした";
  }
}

start();
