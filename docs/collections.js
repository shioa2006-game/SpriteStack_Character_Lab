"use strict";

const collection = document.querySelector("#collection");
const { assets, projects } = AssetCatalog;
const { categories, projectUrl, assetUrl, members, thumb, card } = Lab;

function lineup(items) {
  return `<div class="lineup">${items.map(asset =>
    `<a href="${assetUrl(asset)}">${thumb(asset)}<span>${asset.name}</span></a>`).join("")}</div>`;
}

function home() {
  const featured = projects[0];
  const cast = featured ? members(featured) : [];
  const display = (cast.length ? cast : assets).slice(0, 4);
  const facings = new Set(display.map(Lab.thumbFacing));
  const facing = facings.size === 1 ? Lab.thumbFacing(display[0]) : "";
  collection.innerHTML = `<section class="hero">
    <div class="hero-copy"><p class="folio">立体スプライト研究室</p>
    <h1>SpriteStack<br><em>Asset Lab</em></h1>
    <p>ひとつの立体から、多方向のスプライトへ。<br>ゲーム用素材の造形・動き・制作記録を収蔵しています。</p></div>
    <div class="exhibit"><div class="exhibit-head"><span>${cast.length ? featured.name : "制作済み素材"}</span>
    ${featured ? `<a href="${projectUrl(featured)}">プロジェクトを見る</a>` : ""}</div>
    ${lineup(display)}<div class="exhibit-caption">静止スプライト <span>${facing || ""}</span></div></div></section>
    <section><div class="section-heading"><h2>素材を探す</h2><span class="tally">${assets.length} 素材 &nbsp; / &nbsp; ${projects.length} プロジェクト</span></div>
    <div class="shelves">${Object.entries(categories).map(([key, cat]) => {
      const items = key === "project" ? cast : assets.filter(a => a.type === key);
      const count = key === "project" ? projects.length : items.length;
      const covers = key === "character" ? [...items.filter(a => !cast.includes(a)), ...items.filter(a => cast.includes(a))] : items;
      return `<a class="shelf ${key}" href="${cat.page}"><div class="shelf-head"><span>${cat.title}</span>
        <b>${count} <small>${key === "project" ? "PROJECT" : "ASSET"}${count === 1 ? "" : "S"}</small></b></div>
        <h3>${cat.name}</h3><p>${key === "project" ? "ゲーム別の採用素材 · " + assets.filter(a => a.projects.length).length + " 件" : cat.summary}</p>
        <div class="shelf-art">${covers.length ? covers.slice(0, 3).map(thumb).join("") :
          '<span class="empty-shelf">登録素材なし</span>'}</div></a>`;
    }).join("")}</div></section>`;
}

function introduction(title, subtitle, count) {
  return `<div class="intro"><div><h1>${title}</h1><p>${subtitle}</p></div><span class="count">${count}</span></div>`;
}

function category(key) {
  const cat = categories[key];
  const list = assets.filter(asset => asset.type === key);
  collection.innerHTML = introduction(cat.name, cat.summary, `${list.length} 素材`);
  if (!list.length) {
    collection.insertAdjacentHTML("beforeend", `<div class="empty-panel"><h2>${cat.title}は未登録です</h2>
      ${key === "object" ? `<p>最初に制作を予定しているオブジェクト</p>
      <dl class="roadmap"><div><dt>木箱</dt><dd>静止</dd></div><div><dt>宝箱</dt><dd>閉・開閉・開</dd></div>
      <div><dt>大岩</dt><dd>静止・回転</dd></div><div><dt>石柱</dt><dd>直立・転倒・横倒し</dd></div></dl>` : ""}</div>`);
    return;
  }
  const types = [...new Set(list.map(asset => asset.subtype))];
  const used = projects.filter(project => list.some(asset => asset.projects.includes(project.id)));
  collection.insertAdjacentHTML("beforeend", `<div class="filters"><label>分類 <select id="subtype"><option value="">すべて</option>
    ${types.map(type => `<option value="${type}">${AssetCatalog.subtypes[type] || type}</option>`).join("")}</select></label>
    <label>プロジェクト <select id="project-filter"><option value="">すべて</option>
    ${used.map(p => `<option value="${p.id}">${p.name}</option>`).join("")}
    ${list.some(a => !a.projects.length) ? '<option value="-">未所属</option>' : ""}</select></label>
    <output id="matches"></output></div><div class="card-grid" id="results"></div>`);
  function filter() {
    const type = document.querySelector("#subtype").value;
    const project = document.querySelector("#project-filter").value;
    const matches = list.filter(a => (!type || a.subtype === type) &&
      (!project || (project === "-" ? !a.projects.length : a.projects.includes(project))));
    const results = document.querySelector("#results");
    document.querySelector("#matches").textContent = matches.length + " 件表示";
    results.innerHTML = matches.map(card).join("") || "<p>条件に一致する素材はありません。</p>";
    Lab.paintThumbs(results);
  }
  collection.querySelector(".filters").addEventListener("change", filter);
  filter();
}

function projectIndex() {
  collection.innerHTML = introduction("PROJECTS", "ゲーム別に、採用された素材をまとめて見る。", `${projects.length} プロジェクト`) +
    projects.map(project => `<a class="project-panel" href="${projectUrl(project)}"><div><span class="folio">${members(project).length} 登録素材</span>
      <h2>${project.name}</h2><p>${project.description}</p></div>
      <div class="project-art">${members(project).slice(0,4).map(thumb).join("")}</div></a>`).join("");
}

function projectDetail(project) {
  if (!project) {
    collection.innerHTML = '<h1>プロジェクトが見つかりません</h1><a href="projects.html">PROJECTS 一覧</a>';
    return;
  }
  document.title = project.name + " | SpriteStack Asset Lab";
  const items = members(project);
  const groups = [
    ["冒険者", items.filter(a => a.type === "character" && a.subtype === "adventurer")],
    ["NPC", items.filter(a => a.type === "character" && a.subtype === "npc")],
    ["その他のキャラクター", items.filter(a => a.type === "character" && !["adventurer","npc"].includes(a.subtype))],
    ["モンスター", items.filter(a => a.type === "monster")],
    ["オブジェクト", items.filter(a => a.type === "object")],
  ];
  collection.innerHTML = `<a class="crumb" href="projects.html">PROJECTS 一覧</a>` +
    introduction(project.name, project.description, `${items.length} 素材`) +
    `<div class="project-links">${project.party ? `<a class="primary-link" href="${project.party}">隊列プレビュー</a>` : ""}
    <a class="text-link" href="${project.repository}">ゲームリポジトリ</a></div>` +
    groups.filter(([title, group]) => title !== "その他のキャラクター" || group.length).map(([title, group]) =>
      `<section class="project-section"><div class="section-heading"><h2>${title}</h2><span class="tally">${group.length} 素材</span></div>
      ${group.length ? `<div class="card-grid">${group.map(card).join("")}</div>` : '<p class="empty-line">登録素材はありません。</p>'}</section>`).join("");
}

const page = document.body.dataset.page;
if (page === "home") home();
else if (page === "project") {
  if (Lab.queryId) projectDetail(projects.find(p => p.id === Lab.queryId));
  else projectIndex();
} else category(page);
if (page === "home" || page === "project") Lab.paintThumbs();
