"use strict";

async function openViewer() {
  const asset = AssetCatalog.assets.find(a => a.id === Lab.queryId);
  const get = id => document.getElementById(id);
  const heading = get("viewer-heading");
  if (!asset) {
    heading.innerHTML = "<h1>素材が見つかりません</h1>";
    return;
  }
  const category = Lab.categories[asset.type];
  Lab.navigation(asset.type);
  get("back").href = category.page;
  get("back").textContent = category.name + " 一覧";
  document.title = asset.name + " | SpriteStack Asset Lab";
  heading.innerHTML = `<div><p class="folio">${Lab.subtype(asset)} · ${asset.displayName}</p>
    <h1>${asset.name}</h1><p>${asset.description}</p></div>
    <label>素材を切り替え <select id="asset-select">${AssetCatalog.assets.filter(a => a.type === asset.type)
      .map(a => `<option value="${a.id}" ${a.id === asset.id ? "selected" : ""}>${a.name}</option>`).join("")}</select></label>`;
  get("asset-select").onchange = event => {
    const url = new URL(Lab.assetUrl(AssetCatalog.assets.find(a => a.id === event.target.value)), location.href);
    if (!get("workbench").hidden) {
      for (const key of ["motion", "direction"]) {
        const selected = document.querySelector(`[data-${key}][aria-pressed=true]`);
        if (selected) url.searchParams.set(key, selected.dataset[key]);
      }
      for (const key of ["scale", "speed", "variant"]) url.searchParams.set(key, get(key).value);
    }
    location.href = url.href;
  };
  const link = (label, url) => `<a href="${url}">${label}</a>`;
  get("records").innerHTML = "<strong>制作資料</strong>" +
    link("モデル生成ソース", Lab.sourceUrl(asset.source)) +
    asset.records.map(([label, path]) => link(label, Lab.sourceUrl(path))).join("") +
    AssetCatalog.projects.filter(p => asset.projects.includes(p.id)).map(p => link(p.name, Lab.projectUrl(p))).join("");
  function fileLinks(files) {
    return link("PNG", asset.directory + files.sheet) + link("JSON", asset.directory + files.metadata) +
      (files.gif ? link("GIF", asset.directory + files.gif) : "") +
      (files.comparison ? link("新旧比較 GIF", asset.directory + files.comparison) : "");
  }
  if (location.protocol === "file:") {
    heading.insertAdjacentHTML("afterend", `<div class="empty-panel"><h2>個別再生はローカルHTTPで開けます</h2>
      <p>ブラウザは直接開いたHTMLから再生用JSONを取得できません。リポジトリのルートで次を実行してください。</p>
      <code>python -m http.server 8000 --bind 127.0.0.1 --directory docs</code>
      <p>${link("この素材をローカルHTTPで開く", "http://127.0.0.1:8000/" + Lab.assetUrl(asset))}</p></div>`);
    get("files").innerHTML = asset.views.map(v => `<div><strong>${v.label}</strong> ${fileLinks(v)}
      ${(v.variants || []).map(alt => `<strong>${alt.label}</strong> ${fileLinks(alt)}`).join("")}</div>`).join("");
    return;
  }
  get("workbench").hidden = false;
  const canvas = get("sprite");
  const ctx = canvas.getContext("2d");
  const variants = new Map();
  const cache = new Map();
  async function read(view, files = view) {
    const url = asset.directory + files.metadata;
    if (!cache.has(url)) cache.set(url, fetch(url).then(response => {
      if (!response.ok) throw new Error(files.metadata);
      return response.json();
    }));
    const metadata = await cache.get(url);
    const layout = view.state ? metadata.neutral : metadata.animations[view.id];
    const directions = view.state ? layout.directions : layout.rows;
    const frames = view.state ? 1 : layout.columns;
    const times = layout.durations_ms || Array.from({ length: frames }, () => view.state ? 0 : 1000 / layout.fps);
    const starts = [0];
    for (const ms of times) starts.push(starts[starts.length - 1] + ms);
    return { view, files, layout, directions, frames, starts, duration: starts[frames] };
  }

  const clips = await Promise.all(asset.views.map(async view => {
    const versions = await Promise.all([view, ...(view.variants || [])].map(files => read(view, files)));
    variants.set(view.id, versions);
    return versions;
  }));
  const layouts = clips.flat().map(clip => clip.layout);
  // Align all states to one floor point. Left/right extents can come from different sheets.
  const extent = axis => Math.max(...layouts.map(l => l.anchor[axis]));
  const tile = 32;
  const margin = asset.type === "object" ? tile : 0;
  const anchor = [extent(0) + margin, extent(1) + margin];
  const size = anchor.map((v, axis) => v + Math.max(...layouts.map(l => l.cell[axis] - l.anchor[axis])) + margin);
  const prefs = new URLSearchParams(location.search);
  for (const key of ["scale", "speed"]) {
    if ([...get(key).options].some(o => o.value === prefs.get(key))) get(key).value = prefs.get(key);
  }
  let active, image, facing = prefs.get("direction") || "SW", frame = 0, elapsed = 0, last = 0, animation = 0, ticket = 0;
  let playing = false;
  function draw() {
    if (!image) return;
    const { layout, view, directions } = active;
    const [w, h] = layout.cell;
    const scale = Number(get("scale").value);
    const index = directions.indexOf(facing);
    const x = anchor[0] - layout.anchor[0], y = anchor[1] - layout.anchor[1];
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.clearRect(0, 0, size[0], size[1]);
    if (get("floor").checked) {
      ctx.fillStyle = "#617d7244";
      for (let i = anchor[0] % tile; i < size[0]; i += tile) ctx.fillRect(i, 0, 1, size[1]);
      for (let j = anchor[1] % tile; j < size[1]; j += tile) ctx.fillRect(0, j, size[0], 1);
    }
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(image, (view.state ? index : frame) * w, (view.state ? 0 : index) * h, w, h, x, y, w, h);
    if (get("floor").checked) {
      ctx.fillStyle = "#9b471c";
      ctx.fillRect(anchor[0] - 3, anchor[1], 7, 1);
      ctx.fillRect(anchor[0], anchor[1] - 3, 1, 7);
    }
    get("frame").textContent = `${frame + 1} / ${active.frames}`;
    get("status").textContent = `${view.label} · ${facing} · ${w}×${h} px`;
    canvas.setAttribute("aria-label", `${asset.name} ${view.label} ${facing} ${frame + 1}コマ目`);
  }
  function resize() {
    canvas.width = size[0] * Number(get("scale").value);
    canvas.height = size[1] * Number(get("scale").value);
    draw();
  }
  function run(value) {
    cancelAnimationFrame(animation);
    playing = value;
    get("play").textContent = value ? "一時停止" : "再生";
    if (value) {
      last = performance.now();
      animation = requestAnimationFrame(tick);
    }
  }
  function tick(now) {
    elapsed += Math.max(0, now - last) * Number(get("speed").value);
    last = now;
    if (active.layout.loop) elapsed %= active.duration;
    else if (elapsed >= active.duration) {
      run(false);
      if (active.view.next) {
        select(active.view.next);
      } else {
        frame = active.frames - 1;
        draw();
      }
      return;
    }
    const next = active.starts.findIndex(start => start > elapsed) - 1;
    if (next !== frame) { frame = next; draw(); }
    animation = requestAnimationFrame(tick);
  }
  function step(delta) {
    if (!image) return;
    run(false);
    frame = (frame + delta + active.frames) % active.frames;
    elapsed = active.starts[frame];
    draw();
  }
  function buttons(items, selected, attribute) {
    return items.map(([id, label]) => `<button type="button" data-${attribute}="${id}" aria-pressed="${id === selected}">${label}</button>`).join("");
  }
  async function select(id, variant = 0) {
    const request = ++ticket;
    run(false);
    active = variants.get(id)[variant];
    image = null;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    get("frame").textContent = "";
    get("status").textContent = "読み込み中…";
    frame = elapsed = 0;
    const { view, directions } = active;
    if (!directions.includes(facing)) facing = directions[0];
    get("views").innerHTML = buttons(asset.views.map(v => [v.id, v.label]), id, "motion");
    get("directions").innerHTML = buttons(directions.map(d => [d,d]), facing, "direction");
    get("variant-row").hidden = !view.variants?.length;
    get("variant").innerHTML = variants.get(id).map(({files, layout}, index) =>
      `<option value="${index}">${layout.cell.join("×")} · ${index ? files.label : "標準"}</option>`).join("");
    get("variant").value = variant;
    get("speed").disabled = active.frames === 1;
    get("transport").hidden = active.frames === 1;
    get("replay").hidden = Boolean(active.layout.loop);
    get("files").innerHTML = `<strong>${view.label}素材</strong>` + fileLinks(active.files);
    try {
      const loaded = await Lab.loadImage(asset.directory + active.files.sheet);
      if (ticket !== request) return;
      image = loaded;
      resize();
      if (active.frames > 1) run(true);
    } catch {
      if (ticket === request) get("status").textContent = "画像を読み込めません";
    }
  }
  get("floor-row").hidden = asset.type !== "object";
  get("floor").addEventListener("change", draw);
  get("scale").addEventListener("change", resize);
  get("views").addEventListener("click", event => {
    if (event.target.dataset.motion) select(event.target.dataset.motion);
  });
  get("variant").addEventListener("change", event => select(active.view.id, Number(event.target.value)));
  get("directions").addEventListener("click", event => {
    if (!event.target.dataset.direction) return;
    facing = event.target.dataset.direction;
    for (const button of get("directions").children) button.setAttribute("aria-pressed", button.dataset.direction === facing);
    draw();
  });
  get("previous").onclick = () => step(-1);
  get("next").onclick = () => step(1);
  get("play").onclick = () => {
    if (!image) return;
    if (elapsed >= active.duration) elapsed = frame = 0;
    draw();
    run(!playing);
  };
  get("replay").onclick = () => select(active.view.id);
  document.addEventListener("visibilitychange", () => { last = performance.now(); });
  const initial = variants.has(prefs.get("motion")) ? prefs.get("motion") : asset.views[0].id;
  const version = Number(prefs.get("variant"));
  await select(initial, Number.isInteger(version) && variants.get(initial)[version] ? version : 0);
}

openViewer().catch(error => {
  document.querySelector("#status").textContent = "再生用メタデータを読み込めません";
  console.error(error);
});
