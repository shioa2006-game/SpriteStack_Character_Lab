# 画像由来キャラクター制作基盤：静止ベイクと汎用検証の共通化

## 結論

[比較分析](IMAGE_TO_CHARACTER_COMPARISON.md)の提案1（汎用検証）と提案2（静止だけのベイク）を実装した。

- **静止ベイク。** 共通CLIに `--modes idle` と `--cells` を追加した。静止8方向だけを、歩行・攻撃の姿勢計算なしで焼く。MARENの48×48、CRYSTAL MAGEの48×48と64×64は、公開PNG・JSONと**ファイルのバイトまで一致**した。旧 `bake_idle.py` の出力とも全ファイルが一致した。従来の全モード生成（LARK・BRAM）は回帰テストに合格した。
- **汎用検証。** `research.verify_character` を追加した。キャラクター名で分岐せず、`character.json` と、キャラクターごとの品質設定 `quality.json` だけで、モデル、リグと装備、静止シートを検査する。MAREN・CRYSTAL MAGEは FAIL 0。MARENの33ボクセルの切れ端は、描画されない部位の所有・接続上の候補として WARNING で報告する。
- **検出テスト。** 一時的なコピーに20種類の異常を作り、20種類とも期待どおりに報告した。本の色をマントと同じにする配色の問題は、技術的な不具合ではないため検出しない（既知の限界として確認）。
- **保全。** LARK・BRAM・MAREN・CRYSTAL MAGEのモデル、設定、PNG、旧スクリプト、過去のレポートは変更していない。旧スクリプトは新しいCLIの出力でも合格する。

## 1. 共通化した機能

| 機能 | 場所 | 内容 |
| --- | --- | --- |
| 静止だけのベイク | [spritestack/bake.py](../spritestack/bake.py) の `bake_idle`、[spritestack/__main__.py](../spritestack/__main__.py) | 静止姿勢のモデルから8方向を描き、`idle.png`、`metadata.json`、`rest_part_ids.npz` を書く。歩行・攻撃の姿勢、姿勢ボリューム、関節JSONは作らない |
| セルの解像度 | `view_for_cell`、`idle_cells` | 標準セルは `view` のまま。別のセルは `character.json` の `comparison_view`（画素密度、セル、アンカー）で同じモデルを描き直す。暗黙の拡大はしない |
| 静止レイアウトの共有 | `neutral_layout` | 全モード生成と静止だけのベイクで、方向順、セル、アンカーの書き方を共通にした |
| 汎用検証 | [research/verify_character.py](verify_character.py) | モデル、リグと装備、シートの検査。結果は PASS・WARNING・FAIL・SKIP |
| 品質設定 | [characters/maren/quality.json](../characters/maren/quality.json)、[characters/crystal_mage/quality.json](../characters/crystal_mage/quality.json) | 装備の役割、可視画素の下限、存在の条件、公開先、生成コード、配色の出典、モーションの出典 |
| 検出テスト | [research/verify_character_selftest.py](verify_character_selftest.py) | 一時フォルダに複写したキャラクターへ異常を入れ、検証の報告を確かめる |

静止だけのベイクの `metadata.json` は、旧 `bake_idle.py` と同じ形式。全モード生成と同じキーを持ち、`animations` は空。`volume_origin_xyz` と `voxel_size_xyz` は、一緒に出力する `rest_part_ids.npz` の静止格子を指す（全モード生成では姿勢ボリュームを指す）。

## 2. 旧コードとの対応

| 旧 | 新 | 備考 |
| --- | --- | --- |
| `characters/maren/bake_idle.py` | `python -m spritestack --character characters/maren/character.json --modes idle --out <出力先>` | 出力ファイルがバイト一致 |
| `characters/crystal_mage/bake_idle.py`（48と64） | `python -m spritestack --character characters/crystal_mage/character.json --modes idle --out <出力先>` | 既定で `comparison_view` の64も焼く。バイト一致 |
| `comparison_character`（実験02） | `spritestack.bake.view_for_cell` | 同じ置き換え。`comparison_view` を検査する |
| `research/verify_maren.py` | `python -m research.verify_character --character characters/maren/character.json --out <出力先>` | 旧の全検査を移植し、検査を追加 |
| `research/verify_crystal_mage.py` | 同上（`characters/crystal_mage/character.json`） | 旧の全検査を移植。装備の目印の基準を変更（下記） |
| 各検証の定数（装備名、材質ID、方向、公開先） | `quality.json` | 材質はIDではなく名前で書く |

旧スクリプトは削除せずに残した。どちらも新しいCLIの出力で合格する。

### 検査の対応と分類の違い

| 旧の検査 | 新しい検査ID | 分類 |
| --- | --- | --- |
| NPZと生成コードの一致 | `model.regenerate` | FAIL（同じ） |
| 全材質が使われる | `model.palette` | 旧はFAIL、新は WARNING。未使用の色は描画の不具合ではない |
| 配色の出典の名前、「抽出」の色の一致（実験02のみ） | `model.provenance` | 名前の欠落はFAIL。抽出色の不一致は WARNING（記録の不整合） |
| 歩行・攻撃クリップの出典 | `model.motion_walk`、`model.motion_attack` | FAIL（同じ） |
| リグが装備を受け付け、静止で手に追従（実験02） | `rig.attachments` | FAIL（同じ） |
| 装備の左右 | `rig.handedness` | FAIL。新では設定ファイルの手と品質設定の役割、規約（主装備は右手）も照合 |
| 目印が装備の範囲内（実験02：範囲±0.5） | `rig.markers` | 最寄りの装備ボクセルまで1.5単位以内でPASS、3単位以内でWARNING、それより遠いとFAIL。LARK・BRAMの剣先の目印は刃の先から1.0〜1.2単位離れて置かれているため、範囲±0.5は汎用の基準として厳しすぎた |
| 全体のつながり、切れ端、迷い画素、接触、杖の連続（実験02） | `model.connectivity`、`model.fragments`、`model.stray_pixels`、`rig.contacts`、`rig.item_*`、`rig.continuous_*` | 切れ端は WARNING（下記）。それ以外はFAIL |
| シートの寸法、方向順、アンカー、不透明度、余白、8コマが異なる | `sheetNN.layout`、`.image`、`.alpha`、`.margins`、`.distinct` | 同じコマの重複は WARNING。ほかはFAIL |
| 再描画との一致、反転の否定、投影の左右（実験02） | `sheetNN.redraw`、`.mirror`、`.screen_side` | 反転と一致は WARNING（下記）。ほかはFAIL |
| 可視画素の下限 | `sheetNN.visible_<label>` | 規則ごとにFAILかWARNING（既定FAIL） |
| 公開PNG・JSONとの一致 | `sheetNN.published` | FAIL。ファイルのバイト差は詳細に記録 |

## 3. CLIと使用例

### 静止8方向のベイク

~~~powershell
& $python -B -m spritestack --character characters/maren/character.json --modes idle --out output/maren
& $python -B -m spritestack --character characters/crystal_mage/character.json --modes idle --out output/crystal_mage
& $python -B -m spritestack --character characters/crystal_mage/character.json --modes idle --cells 48 --out output/mage-48
& $python -B -m spritestack --character characters/crystal_mage/character.json --modes idle --cells 64 --out output/mage-64
~~~

| 引数 | 意味 |
| --- | --- |
| `--modes all`（既定） | 従来どおり、静止・歩行・攻撃をまとめて焼く |
| `--modes idle` | 静止8方向だけを焼く。姿勢計算と姿勢ボリュームの検査をしない |
| `--cells PX ...` | `--modes idle` で焼くセル。既定は `view.neutral_cell` と、あれば `comparison_view.neutral_cell`。標準セルは `idle.png`・`metadata.json`・`rest_part_ids.npz`、それ以外は `idle-<PX>.png`・`idle-<PX>.json` |

64×64のような比較用セルを使うには、`character.json` に `comparison_view` が必要。

~~~json
"comparison_view": {
  "pixels_per_unit": 1.5867,
  "neutral_cell": 64,
  "base_pivot": [32, 53]
}
~~~

`comparison_view` のないキャラクターで `--cells 64` を指定すると、何も書かずに失敗する（`no 64px idle view: character.json needs a comparison_view with neutral_cell 64`）。`--cells` を `--modes all` と一緒に指定すると、引数の誤りとして止まる。`output/` はGitで無視する。

### 汎用検証

~~~powershell
& $python -B -m research.verify_character --character characters/maren/character.json --out output/maren
& $python -B -m research.verify_character --character characters/crystal_mage/character.json --out output/crystal_mage --json output/mage-report.json
& $python -B -m research.verify_character_selftest
~~~

| 引数 | 意味 |
| --- | --- |
| `--out` | 静止シートのフォルダ。省略するとシートの検査をSKIP |
| `--quality` | 品質設定（既定は `character.json` と同じフォルダの `quality.json`）。ない場合は既定値で検査し、WARNINGを出す |
| `--published DIR`、`--no-published` | 公開PNGの比較先を上書き、または比較しない |
| `--json` | 結果をJSONでも書く |
| `--verbose` | PASSの詳細も表示 |

FAILが1つでもあれば終了コード1。WARNINGだけなら0。

### 品質設定の項目

パスは `quality.json` のフォルダからの相対パス。材質は `character.json` の配色の名前で書く。

| キー | 内容 | 省略時 |
| --- | --- | --- |
| `model_builder` | `module:function`。`function(config)` が材質と部位の配列を返す | 再生成の検査をSKIP |
| `provenance` | `palette`（配色の出典）と `samples`（抽出結果） | SKIP |
| `motions` | 各モードの出典。`{"clip": 共通クリップJSON}`、`{"same_as": 他の character.json}` または `{"call": "module:function"}` | SKIP |
| `items` | `main`・`off` の役割ごとに `part`、`hand`、`marker`。任意で `through`（装備と一続きとみなす部位） | `rig.attachments` から、右手を `main`、左手を `off` |
| `contacts` | 追加で接触を求める部位の組 | 装備と手、手・前腕・上腕・胸の連鎖だけ |
| `continuous` | `part` が z方向に途切れないこと。`through`、`from_floor` | 検査しない |
| `presence` | `part`、`materials`、`min_voxels`、`lowest_z_at_most`、`highest_z_at_least` | 検査しない |
| `visibility` | `label`、`part`、`materials`、`min_px`（数値かセルごとの辞書）、`directions`（`"all"` か一覧）、`severity`（`fail`・`warning`） | 検査しない |
| `cells` | 検査するセル | 標準セルだけ |
| `published` | 公開フォルダ | 比較しない |
| （全体） | 品質設定が存在しない部位、手、目印、材質を指すと `quality.references` がFAILになり、以降の検査を行わない | — |
| `extra_checks` | `module:function` の一覧。`function(context)` が `context.report.add(...)` で結果を足す | なし |

共通の検査はキャラクター名で分岐しない。キャラクター固有の条件は `quality.json` の規則か、`extra_checks` に置く。`extra_checks` の仕組みは実装したが、今回の2体では使っていない（既存の固有検査はすべて規則で書けた）。

## 4. MARENのテスト結果

| 項目 | 結果 |
| --- | --- |
| 共通CLI `--modes idle` | `idle.png`（384×48 RGBA）、`metadata.json`、`rest_part_ids.npz` を出力。公開の `idle.png`・`metadata.json` とファイルのバイトまで一致。旧 `bake_idle.py` の出力と3ファイルともバイト一致 |
| 方向順・アンカー・配置 | S、SW、W、NW、N、NE、E、SE。48×48、アンカー (24, 40)、1行8列 |
| 旧 `verify_maren` | 新しいCLIの出力で合格 |
| 汎用検証 | PASS 33、WARNING 1、FAIL 0、SKIP 0 |
| WARNING | `model.fragments`：胸部位の33ボクセルが胸から切り離され、骨盤だけに接している。中心 (−0.4, −0.04, 14.75)。48×48の8方向のどの描画にも出ない。胴の楕円体の最下段がベルト（骨盤）に切られた内部の層。静止画の不具合ではなく、動かすと胸と一緒に動く骨盤内の層として、部位の所有の見直し候補 |
| 追加した検査 | 剣身の可視画素 ≥ 4（8方向）、盾の面 ≥ 8（8方向）、背面3方向の髪 ≥ 120 px、髪の最下点が肩より下（z ≤ 20.0）。下限は公開シートの計測値の約半分 |

## 5. CRYSTAL MAGEのテスト結果

| 項目 | 結果 |
| --- | --- |
| 共通CLI `--modes idle`（既定のセル） | `idle.png`（384×48）、`metadata.json`、`rest_part_ids.npz`、`idle-64.png`（512×64）、`idle-64.json` を出力。公開の4ファイルとバイト一致。旧 `bake_idle.py` の5ファイルとバイト一致 |
| `--cells 64` だけ | `idle-64.png`・`idle-64.json` だけを出力し、公開ファイルとバイト一致 |
| 方向順・アンカー・配置 | 48：アンカー (24, 40)。64：アンカー (32, 53)、1.5867 px/単位。どちらも1行8列、同じ方向順 |
| 64×64の描き方 | 48×48の拡大ではなく、同じモデルを `comparison_view` の画素密度で描き直す（`sheet64.redraw` で全コマが再描画と一致） |
| 旧 `verify_crystal_mage` | 新しいCLIの出力で合格 |
| 汎用検証 | PASS 44、WARNING 1、FAIL 0、SKIP 0 |
| WARNING | `model.fragments`：4片。腿の1ボクセル×2（骨盤内、描画されない）、上腕の7・14ボクセル（肩の覆いで分かれた袖。48と64の正面側で描かれる）。旧 `verify_crystal_mage` が情報として出していた内容と同じ |
| 一致した検査値 | 杖と右手の接触14、本と左手19。杖は z = 0〜31.5 で途切れない。最小の余白は W の 1 px |

## 6. LARK・BRAMの回帰結果

| 項目 | LARK | BRAM |
| --- | --- | --- |
| 従来の全モードCLI | 成功 | 成功 |
| 基準との照合 | `verify_rebuild.py`：メタデータと正式PNG・部位ID画像5点のRGBAが一致（PNGのバイトは従来どおり不一致） | `verify_bram` に合格 |
| 公開素材 | 静止・歩行・攻撃PNGのRGBAとメタデータの内容が一致（ファイルのバイトは不一致） | 静止・歩行・攻撃PNGはバイトまで一致。メタデータは内容が一致（ファイルのバイトは不一致。改行コードなどの差） |
| 汎用検証（品質設定なし、参考） | PASS 20、WARNING 3、SKIP 3、FAIL 0 | PASS 21、WARNING 2、SKIP 3、FAIL 0 |

LARK・BRAMの汎用検証は、品質設定を作らずに既定値で実行した参考の結果。WARNINGは、品質設定がないこと、LARKの未使用の色 `undershirt`、切れ端（LARKのすねの3・2ボクセルは描画されない。BRAMの右腿の7ボクセルは正面側で描かれる）。今回は品質設定を追加していない。

CRYSTAL MAGEは、従来の全モードCLIでは、以前と同じく攻撃の姿勢で杖が姿勢ボリュームを出て失敗する（変更なし）。

## 7. 異常データによる検出テスト

`python -m research.verify_character_selftest` を実行した。キャラクターの設定、NPZ、品質設定を一時フォルダに複写し、共通の静止ベイクで焼いてから異常を1つ入れる。モデルを変えた場合は焼き直す。基準データには触れない。20ケースすべてで、期待した検査が期待した分類を報告した（実行時間 約2分30秒）。

| 異常 | 期待した報告 | 同時に出た報告 | 旧専用検証 |
| --- | --- | --- | --- |
| 杖を2単位前へ動かし、右手から離す | `rig.contacts`、`model.connectivity`、`rig.item_main` FAIL | `rig.markers` WARNING、`model.regenerate` FAIL | 対象外 |
| モデル全体を左右反転（杖と本が入れ替わる） | `rig.handedness` FAIL | `rig.markers` FAIL、`model.regenerate` FAIL | 対象外 |
| 設定の装備の手を入れ替える | `rig.handedness` FAIL | — | 対象外 |
| EのコマをWの反転に差し替える | `sheet48.redraw` FAIL、`sheet48.mirror` WARNING | — | 検出（`W is a mirrored E`） |
| Sのコマを上端に押し付ける | `sheet48.margins`、`sheet48.redraw` FAIL | — | 検出（`S`） |
| Nの1画素を半透明にする | `sheet48.alpha` FAIL | `sheet48.redraw` FAIL | 検出（`N`） |
| Nの1画素の色を変え、公開シートと比べる | `sheet48.redraw`、`sheet48.published` FAIL | — | 検出（再描画と不一致） |
| メタデータのアンカーを1 pxずらす | `sheet48.layout` FAIL | — | 検出（メッセージなし） |
| 頭の後ろに浮いた髪の塊（2×2×2） | `model.connectivity` FAIL | `model.regenerate` FAIL | 対象外 |
| 骨盤の内部の3×3×3を頭部位に変える | `model.fragments` WARNING | `model.regenerate` FAIL | 対象外 |
| 結晶を木の材質に変える | 48・64の `visible_crystal` FAIL、`model.palette` WARNING | `model.regenerate` FAIL | 対象外 |
| 杖の軸を1単位分切る | `rig.continuous_staff`、`rig.item_main` FAIL | `model.connectivity` FAIL | 対象外 |
| 隠れた1ボクセルの材質を変える | `model.regenerate` FAIL | — | 対象外 |
| `staff_tip` を5単位上へ動かす | `rig.markers` FAIL | — | 対象外 |
| 関節座標にNaN | `model.numbers` FAIL | `model.regenerate` FAIL | 対象外 |
| 品質設定に存在しない材質名を書く | `quality.references` FAIL（以降の検査を行わない） | — | 対象外 |
| 本の表紙をマントと同じ色にする | FAILなし（既知の限界） | — | 対象外 |
| MAREN：盾を2単位前へ動かし、左手から離す | `rig.contacts`、`model.connectivity`、`rig.item_off` FAIL | `visible_shield_face` FAIL、`model.regenerate` FAIL | 対象外 |
| MAREN：髪を肩より上で切る | `rig.presence_long_hair_below_the_shoulders` FAIL | `visible_long_hair_from_behind` FAIL、`model.regenerate` FAIL | 対象外 |
| MAREN：WのコマをEの反転に差し替える | `sheet48.redraw` FAIL、`sheet48.mirror` WARNING | — | 検出（公開PNGとの不一致としてのみ） |

「同時に出た報告」の `model.regenerate` FAILは、複写したモデルが生成コードと一致しなくなったため。表にない `model.fragments` WARNING（元から出る切れ端）は省略した。「対象外」は、旧専用検証がコミット済みのモデルを固定パスで読むため、複写したモデルの異常を見られないことを示す。

### 検出の限界

- **反転の検出。** 画像だけでは、反対方向の反転と一致するかしか分からない（`sheetNN.mirror` は WARNING）。左右対称なモデルは、正しく描いても一致しうる。代用でないことの証明には、各コマがモデルの再描画と一致する検査（`sheetNN.redraw`）が必要で、モデルがある場合だけできる。モデル全体を反転した場合は、再描画とは一致するため、装備の左右（`rig.handedness`）で検出する。
- **画面上の左右。** 装備が4 px未満しか見えない方向、または投影が中心から2 px未満の方向は検査しない。
- **見た目の品質。** 同系色の同化（本とマント）、顔が髪や装備に隠れる、小物が何に見えるか、参考画像に似ているかは検出しない。可視画素の下限は「見える」ことの必要条件で、「それと分かる」ことは保証しない。
- **生成コードと一緒に変わったモデル。** 生成コードとNPZを同時に変えると `model.regenerate` は通る。公開PNGとの比較と目視で確かめる。
- **切れ端の判断。** 他部位に覆われた切れ端を不具合かどうかは判断しない。描画される3ボクセル未満の小片だけをFAILにする。

## 8. 共通化できなかった項目

- **モデル生成の形状記述。** 設計どおり、キャラクターごとに書く。
- **比較図とレポート**（比較分析の提案6）。今回の範囲外。
- **色抽出の追加の比**（杖の長さなど）と、攻撃の転用関数（提案7）。範囲外。
- **配色と寸法の事前検査**（提案4）。同系色の同化は今回の検証でも検出しない。
- **画像由来キャラクターの全モード生成。** 剣の攻撃はMAREN・CRYSTAL MAGEに合わない。全モードCLIの挙動は変えていない。
- **ギャラリーへの追加。** `docs/gallery.js` の登録は手作業のまま。

## 9. 制作AIが次回省略できる作業

| 作業 | 従来 | 今後 |
| --- | --- | --- |
| 静止のベイク | `bake_idle.py` を複写して書き換える（70〜103行） | `python -m spritestack --modes idle`。比較用セルは `comparison_view` を書くだけ |
| 検証スクリプト | `verify_<name>.py` を複写して定数と検査を書き換える（102〜260行） | `quality.json`（28〜30行）に装備、可視画素、公開先を書く |
| 検証の網羅性 | キャラクターごとに検査の有無が違った（MARENにはつながりや再描画の検査がなかった） | 全キャラクターで同じ検査が走る |
| 回帰の確認 | 旧スクリプトの出力と公開PNGを手で比べる | `sheetNN.published` が RGBA、JSON、バイト差を報告 |
| 検証の検証 | なし | 自己テストで、検査が異常を見逃していないかを確認 |

造形（`build_model.py`）、配色の判断、目視の評価、レポートは引き続き制作AIが行う。

## 10. 今後の改善候補

- 配色と寸法の事前検査（比較分析の提案4）を、`extra_checks` か共通の規則として追加する。
- `model.fragments` の既知の切れ端を、ボクセル数と位置で「確認済み」と記録できるようにする。記録と違う切れ端だけを WARNING にすれば、回帰で新しい切れ端に気付きやすくなる。
- LARK・BRAMにも `quality.json` を置き、全キャラクターを同じ検証で回す。
- 比較図とレポートの図の共通化（提案6）。
- 旧 `bake_idle.py`・`verify_maren.py`・`verify_crystal_mage.py` を、新しいCLIと検証を呼ぶ薄い入口に置き換える。出力の一致は今回確認済み。

## 合格条件の確認

| 条件 | 結果 |
| --- | --- |
| 1. 共通CLIから静止8方向だけを生成できる | 達成（`--modes idle`） |
| 2. MARENの48×48がRGBA一致 | 達成（バイトも一致） |
| 3. CRYSTAL MAGEの48×48が一致 | 達成（バイトも一致） |
| 4. CRYSTAL MAGEの64×64が一致 | 達成（バイトも一致） |
| 5. 方向順・アンカー・配置の維持 | 達成（メタデータのJSONが一致） |
| 6. 従来の全モードCLIの動作 | 達成（LARK・BRAM） |
| 7. 汎用検証が2キャラクターで実行できる | 達成 |
| 8. 既存専用検証と比較できる | 達成（2. の対応表、旧検証は新しい出力で合格、検出テストで旧検証も実行） |
| 9. 壊したデータで異常を検出 | 達成（20ケース。配色の同化は限界として記録） |
| 10. LARK・BRAMの回帰 | 達成 |
| 11. 既存の正式なモデル・PNGを変更しない | 達成（Git差分なし） |
| 12. README、AGENTS.md、制作ガイドの更新 | 達成 |

Windows 11、Python 3.12.1、NumPy 2.3.5、Pillow 13.0.0で確認した。
