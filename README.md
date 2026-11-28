# SpriteStack Asset Lab

複数のゲームで使う立体スプライトを制作し、原寸で動きと接地を確かめ、生成ソースとともに管理する研究環境です。現在の人型モデルでは、参考画像の配色・背面・装備の設計をPythonとJSONに残し、一つの立体から8方向の静止・アニメーションを再生成できます。[公開ギャラリー](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## ギャラリーを開く

リポジトリのルートで次を実行し、[ローカルギャラリー](http://127.0.0.1:8000/) を開きます。サイトは `docs/` の静的ファイルで動作します。

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

| 入口 | 閲覧できる内容 |
| --- | --- |
| [CHARACTERS](docs/characters.html) | 冒険者と人型キャラクター。画像カードを分類・プロジェクトで絞り込み、方向や再生速度を切り替えて比較 |
| [MONSTERS](docs/monsters.html) | GOBLIN BRUTE・SKELETON GUARD。共通ビューアで公開モーションと制作記録を確認 |
| [OBJECTS](docs/objects.html) | 木箱・宝箱・大岩・石柱と遺跡・渡り場の仕掛け6種。8方向の静止・可動状態、足場モジュール |
| [PROJECTS](docs/projects.html) | GUILDWARDの冒険者4人とオブジェクト制作候補10種。隊列、床面、使う場所での配置比較 |

HTMLを直接開いてもトップ・一覧・隊列は利用できます。個別ビューアはモーション別JSONを `fetch` するため、ブラウザのローカルファイル制限が適用されます。直接開いた詳細画面には素材リンク、起動コマンド、同じ素材のHTTP版へのリンクを表示します。

## 配置と登録

| 場所 | 内容 |
| --- | --- |
| `characters/<id>/` | 既存11体のモデル生成コード、材質・部位、リグ、専用クリップ、品質条件 |
| [monsters/](monsters/README.md)・[objects/](objects/README.md) | 新規モンスター・オブジェクトの生成ソースの置き場と制作方針 |
| `spritestack/`・`motions/` | 共通の描画・ベイク、人型のリグと歩行クリップ |
| `research/`・`experiments/` | 制作ガイド、比較資料、再生成と検証の手順、研究用パッケージ |
| `docs/assets/<id>/` | ゲームで使用する公開PNG・GIF・再生JSON。各IDにつき一式を共有 |
| [docs/catalog.js](docs/catalog.js) | 素材とプロジェクトの台帳。分類・カード・件数・ビューア・隊列の登録元 |

**素材を追加する**

1. 分類に対応するディレクトリで制作し、検証したシートとJSONを `docs/assets/<id>/`、制作記録を `research/` に置きます。人型制作の手順は[キャラクター制作ガイド](research/CHARACTER_CREATION_GUIDE.md)にあります。
2. 台帳の `assets` に一件追加し、実在するシート、再生JSON、任意のGIF・比較解像度、生成ソースと制作記録を指定します。`projects` に採用先のIDを列挙します。未所属は空配列です。
3. Node.jsがある環境で `node research/verify_catalog.cjs` を実行し、登録したカードから全方向・各状態・再生・リンクを確認します。新しい隊列メンバーには生成した `preview.js` も指定します。[項目・登録例と対応範囲](docs/TECHNICAL_DESIGN.md#素材台帳とギャラリー)

**プロジェクトを追加する**

台帳の `projects` に一意な `id`、`name`、`description`、`repository` を登録し、採用素材の `projects` にそのIDを追加します。詳細URLは `projects.html?id=<id>` です。所属一覧・件数はこの関係から生成します。隊列に対応する場合は詳細ページに `party` のリンクが現れます。

## 冒険者の一行

第一章の仕掛けを通常2倍の配置画面で比較できます。鉄の輪の接続点、的の命中、跳ね橋と扉の開閉、水晶の点灯、石像と人物の前後関係を確認できます。[仕掛けの配置と8方向一覧](docs/chapter1.html) · [原型・設置表・再生成](research/chapter1/README.md)

木箱の上に立つリコ、宝箱が開く瞬間、大岩の転がり、石柱が1〜3マスの橋に変わる様子を、冒険者と同じ密度で確認できます。比較画面の投影を切り替えると、GUILDWARDの32×16 pxの床と1段8 pxでの見え方も確認できます。[床面比較](docs/object-study.html) · [オブジェクト制作ガイド](objects/README.md) · [初版と完成版の比較・検証結果](research/objects01/README.md)

木箱の寸法研究では、高さ14・8・6の荷箱を踏み台、2段積み、石橋と比較できます。ギャラリーの木箱には高さ8を採用しました。[原寸の寸法比較](docs/object-study.html?scene=scale) · [GUILDWARD用寸法ガイド](research/GUILDWARD_ASSET_SCALE_GUIDE.md)

ガルドの重打撃、リコの弓射撃、セナの氷魔法、発破師トビの投擲を、同じ石畳で8方向から比較できます。単発再生は攻撃終了後に待機へ戻ります。待機4コマ・歩行6コマの共通セルは64×64、足元アンカーは (32, 57)。攻撃は人物ごとのセル・アンカー・コマ時間を使います。[4人の隊列・個別プレビュー](docs/party.html) · [生成手順と攻撃の検証記録](research/adventurers/ATTACKS.md)

| キャラクター | 待機 | 歩行 | 攻撃 | ゲーム用シートとメタデータ |
| --- | --- | --- | --- | --- |
| ガルド | [GIF](docs/assets/gard/breathe.gif) | [GIF](docs/assets/gard/walk.gif) | [重打撃](docs/assets/gard/attack.gif) | [gard](docs/assets/gard/) |
| リコ | [GIF](docs/assets/rico/breathe.gif) | [GIF](docs/assets/rico/walk.gif) | [射撃](docs/assets/rico/attack.gif) | [rico](docs/assets/rico/) |
| セナ | [GIF](docs/assets/sena/breathe.gif) | [GIF](docs/assets/sena/walk.gif) | [氷魔法](docs/assets/sena/attack.gif) | [sena](docs/assets/sena/) |
| トビ | [GIF](docs/assets/tobi/breathe.gif) | [GIF](docs/assets/tobi/walk.gif) | [発破玉の投擲](docs/assets/tobi/attack.gif) | [tobi](docs/assets/tobi/) |

トビは右手の発破玉を6コマ目で放ち、腰袋から次の玉を取り出します。保持・離手・再装備を同じ立体部位で表現しています。[トビの造形と投擲の検証](research/adventurers/tobi/README.md)

[待機・歩行の制作記録と足元の合わせ方](research/adventurers/README.md)

| 正式サンプル | 造形と動きの見どころ | 素材 |
| --- | --- | --- |
| [MAREN](characters/maren/) | 長い青髪、長剣と丸盾。頭上で溜め、踏み込んで低く振り抜く | [攻撃GIF](docs/assets/maren/attack.gif) |
| [CRYSTAL MAGE](characters/crystal_mage/) | ローブとマント。本を掲げて詠唱し、右手の水晶から放つ | [攻撃GIF](docs/assets/crystal_mage/attack.gif) |
| [AZURE RONIN](characters/azure_ronin/) | スカーフとポニーテール。肩へ刀を引き、短い踏み込みで払い切る | [攻撃GIF](docs/assets/azure_ronin/attack.gif) |

実験04では、新しい参考画像から銀のプレートアーマーと青い百合盾の **FLEUR KNIGHT** を制作しました。ギャラリーのキャラクター欄で再生できます。[制作・検証記録](research/IMAGE_TO_CHARACTER_04.md) · [試作と完成版の原寸比較](docs/assets/fleur_knight/slash-comparison.gif)

実験05の **CRIMSON BLADE** は、長い黒髪を高く束ねた紅装の刀剣士です。低く刀を引き、踏み込みながら斜め上へ斬り抜けます。[制作・検証記録](research/IMAGE_TO_CHARACTER_05.md) · [8方向の攻撃GIF](docs/assets/crimson_blade/attack.gif)

実験06の **GOBLIN BRUTE** は、大きな耳と短い脚のゴブリン戦士です。右肩の後ろへ木の棍棒を振りかぶり、腰を落として叩きつけます。[制作・検証記録](research/IMAGE_TO_CHARACTER_06.md) · [初版と完成版の攻撃比較](docs/assets/goblin_brute/smash-comparison.gif)

実験07の **SKELETON GUARD** は、象牙色の頭蓋骨、背景が透ける肋骨、青い丸盾を持つ骸骨衛兵です。左の盾を構えたまま、右の錆剣を頭上で止めて斬り下ろします。[制作・検証記録](research/IMAGE_TO_CHARACTER_07.md) · [初版と完成版の攻撃比較](docs/assets/skeleton_guard/cleave-comparison.gif)

**新しい画像を受け取ったら**、[開発規約](AGENTS.md) と [キャラクター制作ガイド](research/CHARACTER_CREATION_GUIDE.md) を使ってください。制作ガイドに、採色から原寸評価、公開までの手順があります。

**攻撃を見直すとき**は、変更前後のベイクから足元を揃えた8方向GIF・主要ポーズ・関節座標・武器の軌跡図を生成できます。[比較コマンドと検証例](research/attack/README.md)

## 仕組み

`characters/<name>/` に造形コード、材質・部位の水平断面（NPZ）、関節と装備の設定、専用攻撃クリップ、品質条件を置きます。歩行は [共通クリップ](motions/walk.json) を体格別に調整します。[共通エンジン](spritestack/) が腕・脚のIK、部位の変形、髪や布の追従、再スライス、8方向の正投影を処理します。公開用PNGと再生用メタデータは [docs/assets/](docs/assets/) にあります。[技術設計と出力仕様](docs/TECHNICAL_DESIGN.md)

## WindowsのPython環境

リポジトリのルートでPowerShellを開きます。再生成を確認した組み合わせはPython 3.12.1、NumPy 2.3.5、Pillow 13.0.0です。初回のみ仮想環境を作成します。

```powershell
py -3.12 -m venv .venv
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $python -m pip install -r requirements.txt "numpy==2.3.5" "Pillow==13.0.0"
```

## 共通エンジンでの生成

次の例はMARENを作業用フォルダに再生成し、公開版と照合します。ほかの2体は `$name` を `crystal_mage` または `azure_ronin` に変えます。新しいPowerShellでは `$python` を再設定してください。

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$name = 'maren'
$config = "characters/$name/character.json"
$run = Join-Path $PWD ('.phase1/' + $name + '-' + [guid]::NewGuid())
& $python -m spritestack --character $config --modes idle --out "$run/idle"
& $python -m research.verify_character --character $config --out "$run/idle"
& $python -m spritestack --character $config --out "$run/all"
& $python -m research.verify_walk --character $config --out "$run/all"
& $python -m research.verify_attack --character $config --out "$run/all" --gif "$run/all/attack.gif" --published "docs/assets/$name"
```

`all/` に `idle.png`・`walk.png`・`attack.png` と全モードの `metadata.json` ができます。`idle/` は静止の公開用メタデータと、設定がある場合の比較用静止シートを含みます。歩行を反復する間は `--modes walk` で静止と歩行だけを焼けます。CLIには毎回、まだ存在しない出力先を指定します。

## ギャラリーと研究資料

移行時の公開ファイル照合、8方向・全コマのブラウザ検査、隊列と直接HTMLの確認結果を記録しています。[ギャラリー移行の検証](research/ASSET_GALLERY_VERIFICATION.md)

冒険者の再生成・ループ書き出し・公開素材との照合には、[攻撃の再生成手順](research/adventurers/ATTACKS.md#再生成と照合)と[トビの再現手順](research/adventurers/tobi/README.md#再現手順)を参照してください。

LARK・BRAMは旧エンジンとの互換性や関節変形を調べる研究用資産です。過去の数値、失敗例、比較画像は各実験の記録に残しています。[資産整理と回帰基準](research/SAMPLE_CLEANUP.md) · [研究の経緯](research/ROADMAP.md)

リポジトリのライセンスは未設定です。
