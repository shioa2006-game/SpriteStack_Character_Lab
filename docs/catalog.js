"use strict";

// Classic script so the catalogue and formation preview also work from file://.
const AssetCatalog = (() => {
  const compass = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"];
  const still = { id: "idle", label: "静止", state: true, sheet: "idle.png", metadata: "metadata.json" };
  const compareStill = { ...still, variants: [{ label: "比較", sheet: "idle-64.png", metadata: "idle-64.json" }] };
  const breathe = { id: "breathe", label: "待機", sheet: "breathe.png", metadata: "breathe.json", gif: "breathe.gif" };
  const walk = { id: "walk", label: "歩行", sheet: "walk.png", metadata: "walk.json" };
  const walkGif = { ...walk, gif: "walk.gif" };
  const attack = { id: "attack", label: "攻撃", sheet: "attack.png", metadata: "attack.json", gif: "attack.gif", previewLoop: true };
  const partyAttack = { ...attack, next: "breathe" };
  const objectState = (id, label) => ({ id, label, state: true, sheet: id + ".png",
    metadata: id === "idle" ? "metadata.json" : id + ".json", gif: id + ".gif" });
  const objectMotion = (id, label, next) => ({ id, label, next, sheet: id + ".png", metadata: id + ".json", gif: id + ".gif" });
  const prop = (id, name, displayName, subtype, role, description, views) => ({
    id, name, displayName, role, type: "object", subtype, description, status: "published",
    projects: [], candidateProjects: ["guildward"], directory: "assets/" + id + "/",
    thumbnail: "idle.png", directions: compass, views, source: "objects/" + id + "/build_model.py",
    records: [["設計と原寸検証", "research/objects01/README.md"], ["再生成・制作ガイド", "objects/README.md"]],
  });

  return {
    repository: "https://github.com/shioa2006-game/SpriteStack_Character_Lab/blob/main/",
    subtypes: { adventurer: "冒険者", npc: "NPC", humanoid: "人型", cargo: "荷物", treasure: "宝物", terrain: "地形の仕掛け" },
    projects: [{
      id: "guildward", name: "GUILDWARD",
      description: "ONE PROMPT WORLDSから発展した、BEYOND ONE PROMPTの第2作。",
      repository: "https://github.com/shioa2006-game/ONE_PROMPT_WORLDS/tree/main/beyond2",
      party: "party.html",
      objectPreview: "object-study.html",
    }],
    assets: [
      {
        id: "gard", name: "GARD", displayName: "ガルド", role: "重戦士",
        type: "character", subtype: "adventurer", projects: ["guildward"],
        description: "白髭の重戦士。大盾を構え、両足で踏み込んで槌を打ち下ろす。", status: "published",
        directory: "assets/gard/", thumbnail: "idle.png", directions: compass,
        views: [still, breathe, walkGif, partyAttack],
        partyPreview: "preview.js",
        source: "characters/gard/build_model.py",
        records: [
          ["造形・歩行の検証", "research/adventurers/README.md"],
          ["攻撃の検証", "research/adventurers/ATTACKS.md"],
          ["重打撃の改修記録", "research/adventurers/gard-hammer/README.md"],
        ],
      },
      {
        id: "rico", name: "RICO", displayName: "リコ", role: "弓の斥候",
        type: "character", subtype: "adventurer", projects: ["guildward"],
        description: "フードをかぶった少年の斥候。前に伸ばした弓から一矢を放つ。", status: "published",
        directory: "assets/rico/", thumbnail: "idle.png", directions: compass,
        views: [still, breathe, walkGif, partyAttack],
        partyPreview: "preview.js",
        source: "characters/rico/build_model.py",
        records: [
          ["造形・歩行の検証", "research/adventurers/README.md"],
          ["攻撃の検証", "research/adventurers/ATTACKS.md"],
        ],
      },
      {
        id: "sena", name: "SENA", displayName: "セナ", role: "氷の術師",
        type: "character", subtype: "adventurer", projects: ["guildward"],
        description: "折れた尖り帽子と銀髪の術師。水晶の杖を掲げ、氷片を放つ。", status: "published",
        directory: "assets/sena/", thumbnail: "idle.png", directions: compass,
        views: [still, breathe, walkGif, partyAttack],
        partyPreview: "preview.js",
        source: "characters/sena/build_model.py",
        records: [
          ["造形・歩行の検証", "research/adventurers/README.md"],
          ["攻撃の検証", "research/adventurers/ATTACKS.md"],
        ],
      },
      {
        id: "tobi", name: "TOBI", displayName: "トビ", role: "発破師",
        type: "character", subtype: "adventurer", projects: ["guildward"],
        description: "紫のバンダナに真鍮のゴーグル。右手で発破玉を投げ、腰袋から次の玉を取る。", status: "published",
        directory: "assets/tobi/", thumbnail: "idle.png", directions: compass,
        views: [still, breathe, walkGif, partyAttack],
        partyPreview: "preview.js",
        source: "characters/tobi/build_model.py",
        records: [
          ["造形・投擲の検証", "research/adventurers/tobi/README.md"],
        ],
      },
      {
        id: "maren", name: "MAREN", displayName: "マレン", role: "青髪の剣士",
        type: "character", subtype: "humanoid", projects: [],
        description: "長い青髪に丸盾と長剣。頭上で溜め、踏み込みながら低く振り抜く。", status: "published",
        directory: "assets/maren/", thumbnail: "idle.png", directions: compass,
        views: [still, walk, { ...attack, comparison: "slash-comparison.gif" }],
        source: "characters/maren/build_model.py",
        records: [
          ["造形・検証記録", "research/IMAGE_TO_CHARACTER_01.md"],
          ["攻撃の研究記録", "research/MAREN_DYNAMIC_SLASH.md"],
        ],
      },
      {
        id: "crystal_mage", name: "CRYSTAL MAGE", displayName: "水晶の魔法使い", role: "杖と魔導書",
        type: "character", subtype: "humanoid", projects: [],
        description: "マントをまとい、本を掲げて詠唱し、右手の水晶から魔法を放つ。", status: "published",
        directory: "assets/crystal_mage/", thumbnail: "idle.png", directions: compass,
        views: [compareStill, walk, { ...attack, comparison: "cast-comparison.gif" }],
        source: "characters/crystal_mage/build_model.py",
        records: [
          ["造形・検証記録", "research/IMAGE_TO_CHARACTER_02.md"],
          ["攻撃の研究記録", "research/CRYSTAL_MAGE_CAST.md"],
        ],
      },
      {
        id: "azure_ronin", name: "AZURE RONIN", displayName: "蒼の浪人", role: "スカーフの剣士",
        type: "character", subtype: "humanoid", projects: [],
        description: "スカーフとポニーテールを揺らし、肩に引いた刀で払い切る。", status: "published",
        directory: "assets/azure_ronin/", thumbnail: "idle.png", directions: compass,
        views: [compareStill, walk, { ...attack, comparison: "slash-comparison.gif" }],
        source: "characters/azure_ronin/build_model.py",
        records: [
          ["造形・検証記録", "research/IMAGE_TO_CHARACTER_03.md"],
          ["攻撃の研究記録", "research/AZURE_RONIN_QUICK_SLASH.md"],
        ],
      },
      {
        id: "fleur_knight", name: "FLEUR KNIGHT", displayName: "百合盾の騎士", role: "重装騎士",
        type: "character", subtype: "humanoid", projects: [],
        description: "銀のプレートアーマーと青い百合の大盾を身につけた騎士。", status: "published",
        directory: "assets/fleur_knight/", thumbnail: "idle.png", directions: compass,
        views: [still, walkGif, { ...attack, comparison: "slash-comparison.gif" }],
        source: "characters/fleur_knight/build_model.py",
        records: [
          ["造形・検証記録", "research/IMAGE_TO_CHARACTER_04.md"],
        ],
      },
      {
        id: "crimson_blade", name: "CRIMSON BLADE", displayName: "紅装の刀剣士", role: "刀剣士",
        type: "character", subtype: "humanoid", projects: [],
        description: "長い黒髪を束ねた剣士。低く引いた刀で斜め上へ斬り抜ける。", status: "published",
        directory: "assets/crimson_blade/", thumbnail: "idle.png", directions: compass,
        views: [still, walkGif, { ...attack, comparison: "slash-comparison.gif" }],
        source: "characters/crimson_blade/build_model.py",
        records: [
          ["造形・検証記録", "research/IMAGE_TO_CHARACTER_05.md"],
        ],
      },
      {
        id: "goblin_brute", name: "GOBLIN BRUTE", displayName: "ゴブリン戦士", role: "鉄帯の棍棒",
        type: "monster", subtype: "humanoid", projects: [],
        description: "大きな耳と短い脚の戦士。右肩の後ろから棍棒を振り下ろす。", status: "published",
        directory: "assets/goblin_brute/", thumbnail: "idle.png", directions: compass,
        views: [still, walkGif, { ...attack, comparison: "smash-comparison.gif" }],
        source: "characters/goblin_brute/build_model.py",
        records: [
          ["造形・検証記録", "research/IMAGE_TO_CHARACTER_06.md"],
        ],
      },
      {
        id: "skeleton_guard", name: "SKELETON GUARD", displayName: "骸骨衛兵", role: "錆剣と丸盾",
        type: "monster", subtype: "humanoid", projects: [],
        description: "象牙色の骨に青い丸盾。盾を残し、右手の錆剣を頭上から斬り下ろす。", status: "published",
        directory: "assets/skeleton_guard/", thumbnail: "idle.png", directions: compass,
        views: [still, walkGif, { ...attack, comparison: "cleave-comparison.gif" }],
        source: "characters/skeleton_guard/build_model.py",
        records: [
          ["造形・検証記録", "research/IMAGE_TO_CHARACTER_07.md"],
        ],
      },
      prop("wooden_crate", "WOODEN CRATE", "木箱", "cargo", "積み重ねる足場",
        "オークの板を斜めの桟で留めた低い荷箱。平らな天板が1段の踏み台になる。", [objectState("idle", "静止")]),
      prop("treasure_chest", "TREASURE CHEST", "宝箱", "treasure", "蝶番付きの丸蓋",
        "赤褐色の丸蓋を真鍮の帯が包む。背の蝶番で開き、空の内張りが見える。",
        [objectState("idle", "閉"), objectMotion("opening", "開ける", "open"), objectState("open", "開")]),
      prop("boulder", "BOULDER", "大岩", "terrain", "転がる岩",
        "灰紫の割れ肌に淡い鉱脈が走る。押す方向へ岩肌ごと一回転する。",
        [objectState("idle", "静止"), objectMotion("roll", "転がる")]),
      { ...prop("stone_pillar", "STONE PILLAR", "石柱", "terrain", "倒して渡る石橋",
        "浅い菱形を刻んだ三段の石柱。倒れた石材を一つずつ橋として並べられる。",
        [objectState("idle", "直立"), objectMotion("topple", "転倒", "fallen"), objectState("fallen", "横倒し"), objectState("beam", "足場 BEAM")]),
        thumbnail: "cover.png", thumbnailSingle: true },
    ],
  };
})();
