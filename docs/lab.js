"use strict";

const Lab = (() => {
  const { assets, projects } = AssetCatalog;
  const categories = {
    character: { name: "CHARACTERS", title: "キャラクター", page: "characters.html", summary: "冒険者・剣士・魔法使い・NPC" },
    monster: { name: "MONSTERS", title: "モンスター", page: "monsters.html", summary: "敵キャラクターとボス" },
    object: { name: "OBJECTS", title: "オブジェクト", page: "objects.html", summary: "道具・建物・仕掛け" },
    project: { name: "PROJECTS", title: "プロジェクト", page: "projects.html", summary: "ゲーム別の素材コレクション" },
  };
  // Content comes from the versioned, local catalogue. Query values only select an existing ID.
  const projectUrl = project => `projects.html?id=${encodeURIComponent(project.id)}`;
  const assetUrl = asset => `viewer.html?id=${encodeURIComponent(asset.id)}`;
  const members = project => assets.filter(asset => asset.projects.includes(project.id));
  const subtype = asset => AssetCatalog.subtypes[asset.subtype] || asset.subtype;
  const sourceUrl = path => location.protocol === "file:" ? "../" + path : AssetCatalog.repository + path;
  const queryId = new URLSearchParams(location.search).get("id");

  function thumb(asset) {
    return `<canvas class="thumb" data-thumb="${asset.id}" width="64" height="64" aria-hidden="true"></canvas>`;
  }
  const thumbFacing = asset => asset.thumbnailSingle ? null :
    (asset.directions.includes("SW") ? "SW" : asset.directions[0]);

  const images = new Map();
  function loadImage(url) {
    if (!images.has(url)) {
      const image = new Image();
      image.src = url;
      const loaded = image.decode().then(() => image).catch(error => {
        images.delete(url);
        throw error;
      });
      images.set(url, loaded);
    }
    return images.get(url);
  }

  async function paintThumbs(root = document) {
    await Promise.all([...root.querySelectorAll("canvas[data-thumb]")].map(async canvas => {
      const asset = assets.find(item => item.id === canvas.dataset.thumb);
      try {
        const image = await loadImage(asset.directory + asset.thumbnail);
        // A cover is a one-row strip in catalogue direction order, or a standalone cover.
        const directions = asset.thumbnailSingle ? [asset.directions[0]] : asset.directions;
        const w = image.naturalWidth / directions.length;
        canvas.width = w;
        canvas.height = image.naturalHeight;
        canvas.style.setProperty("--cell-w", w + "px");
        canvas.style.setProperty("--cell-h", canvas.height + "px");
        const column = Math.max(0, directions.indexOf(thumbFacing(asset)));
        canvas.getContext("2d").drawImage(image, w * column, 0, w, canvas.height, 0, 0, w, canvas.height);
      } catch {
        canvas.replaceWith(document.createTextNode("画像を読み込めません"));
      }
    }));
  }

  function card(asset) {
    const affiliations = projects.filter(project => asset.projects.includes(project.id)).map(project => project.name);
    return `<a class="asset-card ${asset.type}" href="${assetUrl(asset)}">
      <div class="plate">${thumb(asset)}<span class="plate-tag">${subtype(asset)}</span></div>
      <div class="card-body"><h3>${asset.name}</h3><p>${asset.displayName} · ${asset.role}</p>
      <div class="card-meta">${affiliations.join(" / ") || "プロジェクト未所属"}</div>
      <div class="card-motions">${asset.views.map(view => view.label).join(" / ")}</div></div></a>`;
  }

  function navigation(active = document.body.dataset.page) {
    document.querySelector("#lab-nav").innerHTML = `<nav class="nav-inner" aria-label="メインナビゲーション">
      <a class="brand" href="index.html" ${active === "home" ? 'aria-current="page"' : ""}>
      <i class="brand-icon" aria-hidden="true"></i>SpriteStack <span>Asset Lab</span></a>
      <div class="nav-pages">${Object.entries(categories).map(([key, cat]) =>
        `<a href="${cat.page}" ${key === active ? 'aria-current="page"' : ""}>${cat.name}</a>`).join("")}</div></nav>`;
  }
  return { categories, projectUrl, assetUrl, members, subtype, sourceUrl, queryId, thumb, thumbFacing, loadImage, paintThumbs, card, navigation };
})();

Lab.navigation();
