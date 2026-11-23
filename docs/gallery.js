"use strict";

const canvas = document.querySelector("#sprite");
const context = canvas.getContext("2d");
const status = document.querySelector("#status");
const frameLabel = document.querySelector("#frame");
const scale = document.querySelector("#scale");
const speed = document.querySelector("#speed");
const resolution = document.querySelector("#resolution");
const resolutionRow = document.querySelector("#resolution-row");
const character = document.querySelector("#character");
const characterName = document.querySelector("#character-name");
const characterSubtitle = document.querySelector("#character-subtitle");
const replay = document.querySelector("#replay");
const attackGif = document.querySelector("#attack-gif");
const comparisonGif = document.querySelector("#comparison-gif");
const motionNote = document.querySelector("#motion-note");
const motionButtons = [...document.querySelectorAll("[data-motion]")];
const directionButtons = [...document.querySelectorAll("[data-direction]")];

const characters = {
  maren: {
    name: "MAREN", subtitle: "Blue-Haired Swordswoman", assets: "assets/maren",
    attackComparison: "slash-comparison.gif",
    // Motions published next to an idle-only metadata.json, each as <name>.json and <name>.png.
    extraAnimations: ["walk", "attack"],
  },
  crystal_mage: {
    name: "CRYSTAL MAGE", subtitle: "Staff and Tome", assets: "assets/crystal_mage",
    attackComparison: "cast-comparison.gif",
    // Idle sheets of the same model at two pixel densities; null keeps the standard idle.png.
    idleSheets: { 48: null, 64: "idle-64" },
    extraAnimations: ["walk", "attack"],
  },
  azure_ronin: {
    name: "AZURE RONIN", subtitle: "Scarf Swordsman", assets: "assets/azure_ronin",
    attackComparison: "slash-comparison.gif",
    idleSheets: { 48: null, 64: "idle-64" },
    extraAnimations: ["walk", "attack"],
  },
  fleur_knight: {
    name: "FLEUR KNIGHT", subtitle: "Knight of the Gilded Lily", assets: "assets/fleur_knight",
    attackComparison: "slash-comparison.gif",
    extraAnimations: ["walk", "attack"],
  },
};
// The 64 px attack cell and its anchor keep the canvas the same for idle-only characters.
const stage = { cell: [64, 64], anchor: [32, 48] };
const sheets = new Map();
const metadata = new Map();
let viewport;
let motion = "idle";
let direction = "SW";
let active = null;
let selection = 0;
let animation;

function loadSheet(url) {
  if (!sheets.has(url)) {
    const loaded = new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(url));
      image.src = url;
    }).catch(error => {
      sheets.delete(url);
      throw error;
    });
    sheets.set(url, loaded);
  }
  return sheets.get(url);
}

function loadMetadata(url) {
  if (!metadata.has(url)) {
    const loaded = fetch(url).then(response => {
      if (!response.ok) throw new Error("metadata");
      return response.json();
    }).catch(error => {
      metadata.delete(url);
      throw error;
    });
    metadata.set(url, loaded);
  }
  return metadata.get(url);
}

function configure(data, idleLayout) {
  const layouts = {
    idle: { ...(idleLayout ?? data.neutral), columns: 1 },
    ...data.animations,
  };
  const all = [stage, ...Object.values(layouts)];
  viewport = {
    width: Math.max(...all.map(layout => layout.cell[0])),
    height: Math.max(...all.map(layout => layout.cell[1])),
    anchorX: Math.max(...all.map(layout => layout.anchor[0])),
    anchorY: Math.max(...all.map(layout => layout.anchor[1])),
  };
  return layouts;
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

async function loadCharacterData(chosen) {
  const data = await loadMetadata(chosen.assets + "/metadata.json");
  if (!chosen.extraAnimations) return data;
  const extras = await Promise.all(chosen.extraAnimations.map(
    name => loadMetadata(chosen.assets + "/" + name + ".json")));
  const animations = { ...data.animations };
  for (const extra of extras) Object.assign(animations, extra.animations);
  return { ...data, animations };
}

function selectAvailableMotion(data) {
  const available = new Set(["idle", ...Object.keys(data.animations)]);
  for (const button of motionButtons) button.disabled = !available.has(button.dataset.motion);
  motionNote.hidden = motionButtons.every(button => !button.disabled);
  motionNote.textContent = available.size === 1
    ? "このキャラクターは静止8方向のみ公開しています。"
    : "このキャラクターは攻撃を公開していません。";
  if (!available.has(motion)) {
    motion = "idle";
    for (const option of motionButtons) option.setAttribute("aria-pressed", option.dataset.motion === motion);
  }
}

async function showSelection() {
  const ticket = ++selection;
  const chosen = characters[character.value];
  cancelAnimationFrame(animation);
  attackGif.hidden = true;
  comparisonGif.hidden = true;
  if (characterName.textContent !== chosen.name) {
    characterName.textContent = chosen.name;
    characterSubtitle.textContent = chosen.subtitle;
    active = null;
    context.clearRect(0, 0, canvas.width, canvas.height);
    frameLabel.textContent = "";
    status.textContent = "画像を読み込み中…";
  }
  try {
    const data = await loadCharacterData(chosen);
    if (ticket !== selection) return;
    selectAvailableMotion(data);
    const name = motion;
    const facing = direction;
    const idleVariant = name === "idle" && chosen.idleSheets ? chosen.idleSheets[resolution.value] : null;
    const sheetName = idleVariant ?? name;
    speed.disabled = name === "idle";
    replay.hidden = name !== "attack";
    resolutionRow.hidden = !(name === "idle" && chosen.idleSheets);
    const label = motionButtons.find(button => button.dataset.motion === name).textContent;
    const [image, variantLayout] = await Promise.all([
      loadSheet(chosen.assets + "/" + sheetName + ".png"),
      sheetName !== name ? loadMetadata(chosen.assets + "/" + sheetName + ".json") : null,
    ]);
    if (ticket !== selection) return;
    const layout = configure(data, variantLayout?.neutral)[name];
    active = {
      name, facing, layout, image, frame: 0, elapsed: 0, lastTick: performance.now(),
      duration: layout.durations_ms?.reduce((total, ms) => total + ms, 0),
    };
    status.textContent = label + " · " + facing + (chosen.idleSheets && name === "idle" ? " · " + layout.cell.join("×") : "");
    canvas.setAttribute("aria-label", chosen.name + " " + status.textContent);
    attackGif.hidden = name !== "attack";
    if (!attackGif.hidden) attackGif.href = chosen.assets + "/attack.gif";
    if (name === "attack" && chosen.attackComparison) {
      comparisonGif.href = chosen.assets + "/" + chosen.attackComparison;
      comparisonGif.hidden = false;
    }
    resize();
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
character.addEventListener("change", showSelection);
resolution.addEventListener("change", showSelection);
showSelection();
