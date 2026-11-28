# SpriteStack Asset Lab ギャラリー移行の検証

2026-11-28。基準は移行前の `0146f9d`。GitHub Pages向けの静的ファイルをローカルのChromeで確認した。

## 変更したファイル

| 用途 | リポジトリ内のファイル |
| --- | --- |
| 入口・分類・詳細 | `docs/index.html`、`docs/characters.html`、`docs/monsters.html`、`docs/objects.html`、`docs/projects.html`、`docs/viewer.html` |
| 台帳と表示 | `docs/catalog.js`、`docs/lab.js`、`docs/collections.js`、`docs/gallery.js`、`docs/gallery.css` |
| GUILDWARD隊列 | `docs/party.html`、`docs/party.js`、`docs/party.css` |
| 案内・制作規約・拡張方針 | `README.md`、`AGENTS.md`、`docs/TECHNICAL_DESIGN.md`、`research/CHARACTER_CREATION_GUIDE.md`、`monsters/README.md`、`objects/README.md` |
| 台帳検査・移行記録 | `research/verify_catalog.cjs`、`research/ASSET_GALLERY_VERIFICATION.md` |

## 配置と公開素材

素材のIDと公開先を固定し、[台帳](../docs/catalog.js)でキャラクター9体、モンスター2体、オブジェクト0件に分類した。GUILDWARDの採用素材はGARD・RICO・SENA・TOBIの4体。既存モンスター2体の所属は空配列。LARK・BRAMは引き続き研究用の回帰資産として元の場所にある。

`git ls-tree -r 0146f9d -- docs/assets` の各パス・Git blob IDを、作業ツリーの全ファイルと照合した。119ファイルすべてが同一バイト列で、追加・欠落は0件。パス、タブ、各ファイルのSHA-256、改行をGitのパス順に連結したマニフェストのSHA-256は `9ec5326cd22064f5a67ce8d8b91da34e9dea086f89f92e3959efedb3d308f121`。

## ブラウザで実行した検査

| 対象 | 方法と結果 |
| --- | --- |
| 一覧と遷移 | トップの4分類、全11体の画像カード、分類・所属と該当0件の絞り込み、未登録のOBJECTSと制作予定、GUILDWARDの4体と空のNPC・モンスター・オブジェクト欄を確認 |
| シートと位置 | 標準37種と比較静止2種を原寸で選択。全8方向・全コマのキャンバスを、公開PNGの該当セルをJSONのアンカーで配置した期待画像と比較。1,560枚すべてでRGBA一致 |
| 再生 | 実時間で各アニメーションの進行・停止・コマ送り・単発終了を確認。さらにブラウザの再生時計を進め、待機・歩行・攻撃26クリップの182コマ境界の前後0.25 msで表示コマを照合 |
| 解像度と操作 | CRYSTAL MAGE・AZURE RONINの48／64 px版、原寸と4倍、速度、方向の切替を確認。素材切替時に選択可能な設定を引き継ぎ、静止だけの素材ではコマ送りを隠す |
| 隊列 | 4人と各1人、8方向、足元に合わせた歩行中の床面画素の変化、歩行から攻撃への移行、単発後の待機、反復、攻撃コマ指定を確認。人物切替直後にも上限を更新し、トビは10/10、他の3人は9/9を表示 |
| リンクと配信 | ローカルHTTPのルートとPages相当の `/SpriteStack_Character_Lab/` 配下を使用。PNG・GIF・比較GIF・JSONの参照を照合。GitHub上のモデル、記録、ゲームリポジトリ計26 URLはHTTP 200 |
| 画面と直接HTML | 幅1360 pxのトップと詳細、1100 pxのカード一覧、360 pxで各入口・隊列の横はみ出しを確認。直接開いたトップ・隊列・詳細のHTTP起動案内をテスト |
| 次回登録 | ブラウザ内だけで台帳と配信データを差し替え、1方向の静止物、4方向の状態・動作、可変コマ時間と終了状態、床面格子、複数ゲームから同じ素材へのリンク、5人目の隊列への自動追加を確認 |

原寸でガルド・リコ・セナは各160枚、トビは168枚。MAREN・FLEUR KNIGHT・CRIMSON BLADE・GOBLIN BRUTE・SKELETON GUARDは各128枚、比較解像度を含むCRYSTAL MAGE・AZURE RONINは各136枚。全体画面と狭幅のスクリーンショット、ブラウザ検査スクリプトは今回の作業用 `.phase1/asset-lab-gallery-20261128/` に保存した。

## 再確認の手順と範囲

1. ルートで `node research/verify_catalog.cjs` を実行し、素材・プロジェクト・シート数と参照を検査する。
2. `python -m http.server 8000 --bind 127.0.0.1 --directory docs` でトップを開く。各分類から詳細を選び、倍率1×・速度1×で方向と動作を切り替える。比較静止は2解像度、冒険者は静止と待機の双方を確認する。
3. GUILDWARDの隊列で床面移動を有効にし、歩行→単発攻撃→待機を確認する。個別・全員を切り替え、最後の攻撃コマへ移動する。同じ隊列HTMLを直接開いて再試行する。
4. 公開時は配信後のPagesでも同じ導線を確認する。今回の実行範囲はローカル。新規モデル・ポーズの品質、非人型や物体用のベイク性能、実ゲーム内のタイル寸法は今後の制作時に評価する。生成エンジン、リグ、クリップは今回の変更対象外で、再ベイクは実施していない。
