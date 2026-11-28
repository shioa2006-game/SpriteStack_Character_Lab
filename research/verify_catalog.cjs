"use strict";

// Run from any directory with Node.js. The site itself needs only a static server.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const docs = path.join(root, "docs");
const catalog = vm.runInNewContext(fs.readFileSync(path.join(docs, "catalog.js"), "utf8") + "\nAssetCatalog");
const ids = entries => entries.map(entry => entry.id);
function unique(values, label) {
  assert.equal(new Set(values).size, values.length, label + " に重複があります");
}
function exists(base, file) {
  const full = path.join(base, file);
  assert.ok(fs.statSync(full).isFile(), full);
  return full;
}
function dimensions(file) {
  const png = fs.readFileSync(file);
  assert.ok(png.subarray(1,4).equals(Buffer.from("PNG")), file);
  return [png.readUInt32BE(16), png.readUInt32BE(20)];
}
function partyLayout(dir, file) {
  const src = new URL(file, "https://preview.invalid/assets/").href;
  const context = { window: {}, document: { currentScript: { src } }, URL };
  vm.runInNewContext(fs.readFileSync(exists(dir, file), "utf8"), context);
  return structuredClone(context.window.spriteStackLayouts[new URL(".", src).href]);
}
const projectIds = ids(catalog.projects);
unique(projectIds, "projects");
unique(ids(catalog.assets), "assets");
for (const p of catalog.projects) {
  if (p.party) exists(docs, p.party.split("?")[0]);
  if (p.objectPreview) exists(docs, p.objectPreview);
  if (p.fixturePreview) exists(docs, p.fixturePreview);
  assert.ok(new URL(p.repository).protocol === "https:", p.repository);
}
let count = 0;
for (const a of catalog.assets) {
  const dir = path.join(docs, a.directory);
  const check = (ok, label) => assert.ok(ok, a.id + " " + label);
  check(["character","monster","object"].includes(a.type), "type");
  check(a.id && a.name && a.displayName && a.role && a.subtype && a.status && a.description && a.views.length && a.directions.length, "登録項目");
  check(a.directory.endsWith("/"), "directory 末尾の /");
  unique(a.projects, a.id + " projects");
  check(a.projects.every(id => projectIds.includes(id)), "所属プロジェクト");
  if (a.candidateProjects) {
    unique(a.candidateProjects, a.id + " candidateProjects");
    check(a.candidateProjects.every(id => projectIds.includes(id) && !a.projects.includes(id)), "制作候補");
  }
  unique(a.directions, a.id + " directions");
  if (a.type === "object") check(a.directions.join() === "S,SW,W,NW,N,NE,E,SE", "剛体の標準8方向");
  unique(ids(a.views), a.id + " views");
  exists(root, a.source);
  for (const [, record] of a.records) exists(root, record);
  const [coverWidth] = dimensions(exists(dir, a.thumbnail));
  check(a.thumbnailSingle || coverWidth % a.directions.length === 0, "サムネイルの方向数");
  const preview = a.partyPreview ? partyLayout(dir, a.partyPreview) : null;
  if (a.partyPreview) {
    check(preview?.camera && preview.clips, "隊列用データ");
    check(["breathe","walk","attack"].every(id => ids(a.views).includes(id)), "隊列用モーション");
  }
  const available = new Set();
  for (const view of a.views) {
    if (view.next) check(ids(a.views).includes(view.next), view.id + " next");
    for (const files of [view, ...(view.variants || [])]) {
      const metadata = JSON.parse(fs.readFileSync(exists(dir, files.metadata), "utf8"));
      const layout = view.state ? metadata.neutral : metadata.animations[view.id];
      check(layout, files.metadata + " layout");
      const order = view.state ? layout.directions : layout.rows;
      unique(order, files.metadata);
      if (a.type === "object") {
        check(order.join() === a.directions.join(), files.metadata + " 全状態・全動作の8方向順");
        if (!view.state) check(layout.next === view.next, files.metadata + " 終了状態");
      }
      order.forEach(d => available.add(d));
      const columns = view.state ? order.length : layout.columns;
      const rows = view.state ? 1 : order.length;
      const [w, h] = layout.cell;
      check(w > 0 && h > 0 && columns > 0 && rows > 0, files.sheet + " cell");
      check(layout.anchor.length === 2 && layout.anchor.every(Number.isInteger), files.metadata + " anchor");
      const [width, height] = dimensions(exists(dir, files.sheet));
      check(width === w * columns && height === h * rows, files.sheet + " シート寸法");
      if (!view.state) {
        check(layout.durations_ms ? layout.durations_ms.length === columns && layout.durations_ms.every(ms => ms > 0)
          : layout.fps > 0, files.metadata + " 再生時間");
      }
      if (preview && files === view) {
        if (view.id === "idle") assert.deepEqual(preview.camera, metadata.camera, a.id + " camera");
        if (["breathe", "walk", "attack"].includes(view.id)) {
          const clip = preview.clips[view.id];
          for (const key of ["cell", "anchor", "rows", "columns", "fps", "durations_ms", "phase_names", "suggested_forward_per_frame_model_units"]) {
            assert.deepEqual(clip[key], layout[key], a.id + " " + view.id + " " + key);
          }
          if (view.id === "walk") assert.deepEqual(clip.stance, layout.contact.inclusive_stance_cyclic, a.id + " stance");
        }
      }
      if (files.gif) exists(dir, files.gif);
      if (files.comparison) exists(dir, files.comparison);
      if (!a.thumbnailSingle && files.sheet === a.thumbnail) {
        check(view.state && order.join() === a.directions.join(), "サムネイルの方向順");
      }
      count++;
    }
  }
  check(available.size === a.directions.length && a.directions.every(d => available.has(d)), "公開方向とJSON");
}
console.log(`PASS  ${catalog.assets.length} assets / ${catalog.projects.length} projects / ${count} sheet layouts`);
