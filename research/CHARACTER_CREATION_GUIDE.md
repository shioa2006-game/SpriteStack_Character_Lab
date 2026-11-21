# 参考画像からのキャラクター制作ガイド

参考画像を1枚渡されたClaude Codeが、画像分析から立体モデル、8方向PNG、品質検証、公開まで進めるための手順。実験01（MAREN）と実験02（CRYSTAL MAGE）の工程と問題を元にしている。2実験の比較と、共通化の提案は [IMAGE_TO_CHARACTER_COMPARISON.md](IMAGE_TO_CHARACTER_COMPARISON.md) にある。

現在の共通エンジン（`spritestack/`）を変えずに作る手順を示す。共通エンジン、LARK・BRAM・既存キャラクターの成果物は変更しない。先例のコードは複写して使う。複写元は、マント・杖など装備と衣装が多い場合はCRYSTAL MAGE、剣と盾ならMAREN。

## 0. 全体の流れと成果物

| 段階 | 作業 | 完了の条件 |
| --- | --- | --- |
| 1 | 準備：文書を読み、参考画像をローカルに置く | 画像の寸法とSHA-256を記録した |
| 2 | 画像分析：特徴、比率、配色、装備、難所を表にする | 優先順位と、推測が必要な部分の一覧がある |
| 3 | 採色範囲と目印を座標で記録し、色と比率を抽出 | 抽出JSONができ、範囲の確認図を目視した |
| 4 | 設計：頭身、高さの予算、部位、描画順、配色 | 48 pxに収まる寸法を計算した |
| 5 | `character.json` と `build_model.py` を書く | 全材質・全部位が使われ、警告なしで生成できる |
| 6 | 静止8方向を焼き、見て直す | 7. の確認表を満たす |
| 7 | 検証スクリプトと回帰テスト | すべて合格 |
| 8 | 比較図、レポート、ギャラリー、文書 | 公開素材と検証が一致 |
| 9 | コミット、push、GitHub Pagesの確認 | 公開ページで8方向を確認した |

`<name>` は小文字とアンダースコアのフォルダ名（例：`crystal_mage`）。モジュール名に使うため、Pythonの識別子にする。

~~~text
characters/<name>/
  reference_regions.json   採色範囲・目印の座標（画像は置かない）
  reference_palette.json   抽出した色と比率
  extract_reference.py     抽出のコマンド（MARENの extract を読み込む）
  palette_provenance.json  材質ごとの色の出典と理由
  character.json           材質、部位、関節、装備、カメラ、計測、状態
  build_model.py           立体モデルの生成
  materials.npz            材質ID（Z/Y/X、uint8）
  part_ids.npz             部位ID（同じ形状）
  bake_idle.py             静止8方向のベイク
docs/assets/<name>/        公開する idle.png と metadata.json（比較用があれば idle-64.*）
research/verify_<name>.py  検証
research/image_to_character_NN/compare.py と results/   比較図と計測
research/IMAGE_TO_CHARACTER_NN.md                        実験レポート
~~~

## 1. 準備

1. [AGENTS.md](../AGENTS.md)、[README.md](../README.md)、[実験01](IMAGE_TO_CHARACTER_01.md)・[実験02](IMAGE_TO_CHARACTER_02.md)のレポートを読む。特に「調整の経緯」と「既存エンジンの制約」。
2. Python環境を確認する（README「Windows の Python 環境」）。以下では `$python` を使う。
3. 参考画像を、無視されるフォルダに複写する。画像は追跡も公開もしない。

~~~powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$name = 'new_character'
$work = Join-Path $PWD ".phase1/$name"
New-Item -ItemType Directory -Force $work | Out-Null
$source = 'C:\path\to\image.png'  # 渡された画像のパスに置き換える
Copy-Item $source (Join-Path $work 'reference.png')
(Get-FileHash (Join-Path $work 'reference.png') -Algorithm SHA256).Hash
~~~

4. `git status` が空であることを確認する。作業中は既存のファイルを変更しない。ギャラリーと文書は8. で変更する。

## 2. 画像分析

画像を必ず実際に見る。全体を見た後、頭、上半身、下半身、装備を拡大して見る。座標を読むため、20 pxごとの格子を重ねた2倍の拡大図を `.phase1/<name>/` に作る。作り方は実験02と同じで、Pillowで線と座標を描く一時的なコードでよい。

次の表を作り、レポートの「参考画像から抽出した特徴」に使う。

| 項目 | 記録する内容 |
| --- | --- |
| 人物 | 性別・年齢の印象、体形、表情、画風（写実寄りか） |
| 比率 | 足底を0、頭頂（髪の先）を1とした、頭蓋の頂・目・顎・肩・腰ベルト・裾・膝・足首の高さ。頭身 |
| 幅 | 肩幅、裾の半幅、外套や装備の左右の広がり（身長に対する比） |
| 髪 | 色、長さ、前髪、毛先の向き、左右差 |
| 衣装 | 層の順（内→外）、色、裾の高さ、開き、留め具、ベルト |
| 装備 | どちらの手か（本人基準）、形、長さ（身長比）、傾き、握り位置 |
| 配色の衝突 | 明度が近い大きな塊の組（例：髪と外套、肌と明るい布）。採色後に数値で確かめる |
| 見えない部分 | 背面、側面、足底、装備の裏、髪の後ろ |
| 難所 | 風になびく布、細い装飾、手に持つ小物、背の高い装備 |

**左右の確認。** 画像を正面向きの人物として見ると、画面左が本人の右手。主装備は右手、副装備は左手が規約。画像と逆なら入れ替え、レポートに「規約による変更」と書く（MARENは入れ替えた）。

**装備の割り当て。** リグは2つの手の装備枠だけを持つ（`Biped.__init__`）。部位名は自由に付けられる（例：`staff`、`book`）。両手持ちの装備や背中の装備は今のリグでは表現できない。その場合は依頼者に相談するか、片手に持たせてレポートに記録する。

**優先順位。** 依頼文に優先順位があればそのまま使う。なければ、シルエット、最大の衣装、主装備、副装備、髪、細部の順にする。7. の目視確認と検証のしきい値に写す。

## 3. 採色範囲と目印

1. [crystal_mage/reference_regions.json](../characters/crystal_mage/reference_regions.json) を複写し、`characters/<name>/reference_regions.json` を作る。
   - `regions`：材質ごとの採色範囲 `[x0, y0, x1, y1]`。境界や線を避け、塗りの中央に置く。1材質に2〜4範囲。小さい部位（目、留め具）は `filter` を使う（`dark`、`bright`、`saturated_blue`）。
   - `landmarks_y`：`hair_top`、`skull_top`、`chin`、`sole` は必須（頭身と比率の計算に使う）。他の目印は自由。
   - `families`：面積比を出すための色系統。各材質をどれか1つに入れる。
   - 長い装備や幅の情報は、`staff_y`、`widths_x` のように別のキーに置く。
2. 範囲を描き込んだ確認図を `.phase1/<name>/` に作り、目視する。白い背景が多い範囲、隣の材質にかかる範囲を直す。実験02では範囲を2回直した（1回目に手袋と髪、2回目に髪とフード）。
3. 抽出を実行する。抽出の規則は [maren/extract_reference.py](../characters/maren/extract_reference.py) の `extract` を共有する。長い装備などの追加の比が必要なら、[crystal_mage/extract_reference.py](../characters/crystal_mage/extract_reference.py) のように読み込んで足す。

~~~powershell
Copy-Item characters/crystal_mage/extract_reference.py characters/$name/
# 中の staff_and_widths を新キャラクターの追加情報に合わせて書き換えるか削除する
& $python -B -m characters.$name.extract_reference --image (Join-Path $work 'reference.png') --out characters/$name/reference_palette.json
~~~

4. 抽出結果を確かめる。
   - 各材質の3階調が、見た目の色と合っているか。範囲に線や背景が多いと、灰色や茶色に寄る。
   - `heads_tall` と比率が目視と合うか。
   - 色の衝突の組の基色の明度差（例：実験02の髪 #696378 とマント #6b6b84 はほぼ同じ）。

## 4. 設計

### 頭身と寸法

画像由来の2体は3.3〜3.7頭身（身長30.5〜33単位）、LARK・BRAMはさらに頭が大きい。顔と髪が読めるよう、頭蓋の頂から顎まで約7.5〜8単位にする（MAREN 約8.1、CRYSTAL MAGE 7.5）。参考画像の比率は、膝・裾・装備の長さを優先して合わせ、肩は頭を大きくした分だけ下がってよい。

### 48 pxセルの高さの予算

標準セル48×48、アンカー (24, 40)、1.19 px/単位、仰角24°。描画の式（`spritestack/render.py`）から、輪郭と1 pxの余白を残す条件は次の通り。

- 上端：`0.9135·z + 0.4067·d ≤ 31.5`
- 下端：`0.9135·z − 0.4067·d' ≥ −4.6`
- 左右：`|p·right| ≤ 18.0`

`z` は高さ（単位）。`d` はカメラから遠ざかる距離、`d'` はカメラへ近づく距離（単位）。カメラの向き `forward = (−sin θ, cos θ, 0)` と画面右 `right = (cos θ, sin θ, 0)` は、方向の角度 θ（`view.directions`）から決まる。x は本人の左、y は前。

| 方向 | カメラの位置（forward） | 画面右（right） |
| --- | --- | --- |
| S | 正面（+y） | 本人の左（+x） |
| SW | 左前（+x, +y） | 左後ろ（+x, −y） |
| W | 本人の左側（+x） | 背中側（−y） |
| NW | 左後ろ（+x, −y） | 右後ろ（−x, −y） |
| N | 背面（−y） | 本人の右（−x） |
| NE | 右後ろ（−x, −y） | 右前（−x, +y） |
| E | 本人の右側（−x） | 前（+y） |
| SE | 右前（−x, +y） | 左前（+x, +y） |

例：本人の右側 x = −7 に立てた杖の頂点は、Wでは7単位遠い。`0.9135·z + 0.4067·7 ≤ 31.5` から z ≤ 31.4。実験02の杖頭はこの上限にあり、Wの上端の余白はちょうど1 pxだった。高い装備、横に長い装備、後ろへ長い外套は、焼く前にこの式で上限を確かめる。

比較用に64×64（同じモデル、1.5867 px/単位、アンカー (32, 53)）を焼く場合も、比率が同じなので上限はほぼ同じ。

### 部位と描画順

共通の17部位を使う。衣装や髪は動く親の部位に所属させる。

| 形状 | 所属 | 先例 |
| --- | --- | --- |
| 髪、顔、目、首 | `head` | 両方 |
| 胴の衣装、スカーフ、肩の外套・マント、フード、胸の留め具 | `chest` | 両方 |
| 裾、腰の外套、ベルト | `pelvis` | MARENの外套、CRYSTAL MAGEのローブの裾 |
| 袖、手袋、籠手 | 腕6部位 | 両方 |
| 主装備・副装備 | 装備の2枠 | 剣・盾、杖・本 |

`paint` は後に塗った形状が勝つ。描画順は見た目を決めるので、意図を書き残す。

- ベルトや留め具は胴の後に塗る。
- 体の後ろに垂れる布は腕より先に、肩を覆う布は腕の後に塗る。
- 握る手は装備の後に塗り、拳が装備を包んで見えるようにする。
- 殻（外套、マント）の中に別の部位の形状を置くと、殻を突き抜けた1ボクセルが迷い画素になる。突き抜けない大きさにする。

### 設計規則（2実験の問題から）

| 対象 | 規則 | 由来 |
| --- | --- | --- |
| 外套・マント・裾の殻 | 全体の厚さ ≥ 1.1 単位、外側の層 ≥ 0.8 単位。内側を裏地の色にする | 両方で裏地が点状に透けた |
| 細長い装備（杖、柄） | 半径 ≥ 0.6 単位。0.5単位のボクセルで2個以上の幅 | 実験02の杖が64 pxで切れた |
| 主役の小物（結晶、紋章） | 2.4×4.5単位以上。前後を装飾で覆わない | 実験02の結晶が枝に隠れた |
| 手に持つ本・小物 | 3.3×4.1×1.8単位程度。体と色が違う面（小口）をカメラ側へ傾ける | 実験02の本 |
| 目 | 髪・肌と別の暗色 | 実験01で目が髪に埋もれた |
| 同系色の大きな塊 | 明度差をつけ、間に別色の帯を置く | 両方の髪と外套 |
| 明るい布と肌 | 色相か明度をずらす | 実験02のローブと顔 |
| 輪郭の近くの暗い色 | 輪郭色 #241c2a より十分明るくする | 実験01の外套、ブーツ |
| 毛束 | 付け根の半径 ≥ 0.7、先端 ≥ 0.3、長さ ≥ 2 単位 | 実験02の髪 |
| 横髪・持ち物 | E・Wで顔の前に来ない | 実験02の横顔 |
| 頭頂の明るい帯 | 置かない（ヘアバンドに見える） | 実験01 |

### 配色

抽出色を出発点にし、48 pxで読めない場合だけ調整する。材質ごとに [palette_provenance.json](../characters/crystal_mage/palette_provenance.json) へ記録する。

- `extracted`：3階調をそのまま使う。検証で抽出結果と一致を確認する。
- `adjusted`：抽出色を変えた。理由（何と同化したか）を書く。
- `derived`：直接の採色がない。どの色から作ったかを書く。

陰影グループ（`group`）を分けると、深さの差がある境界に段差線が入る。髪と肌、腕と胴、外套と裏地は別のグループにする。

## 5. 設定とモデル生成

### character.json

[crystal_mage/character.json](../characters/crystal_mage/character.json) を複写して書き換える。

| キー | 書き換える内容 |
| --- | --- |
| `status` | 静止・歩行・攻撃の状態。未実装のモーションは「読込用の仮の参照、焼かない」と書く |
| `model.origin_xyz`、格子 | 外套や装備が収まる範囲。`build_model.py` の `SHAPE` と合わせる |
| `model.palette` | 4. の配色 |
| `rig.parts` | 体の15部位の後に装備2つ（主装備、副装備の順）。合計17部位 |
| `rig.rest` | 関節座標と装備の目印。目印は装備のボクセルの範囲内に置く |
| `rig.attachments` | 主装備は `hand_R`、副装備は `hand_L` |
| `view` | LARKと同じ値のまま |
| `comparison_view` | 64×64の比較を焼く場合だけ |
| `posed_volume`、`walk`、`attack` | 読込に必要。歩行・攻撃を作らないなら、LARKのクリップと調整値を参照したままにする |
| `measurements` | 装備の材質IDを書き換える |

### build_model.py

先例を複写し、`build()` の中身を書き直す。`paint`、`ellipsoid`、`capsule`、`tube`、`main` はそのまま使う。

1. 脚、骨盤の衣装とベルト、胴、体の後ろの布、腕、肩の布、留め具、フード、頭（首、毛束、髪の殻、顔、目）、主装備と右手、副装備と左手の順に書く。描画順の意図はコメントに残す。
2. 生成して、配列の形と使用状況を確かめる。

~~~powershell
& $python -B -W error::RuntimeWarning characters/$name/build_model.py --out characters/$name
~~~

`RuntimeWarning` を止めるのは、負の数の小数乗などによるNaNを見逃さないため（実験02で発生）。

### bake_idle.py

48×48だけなら [maren/bake_idle.py](../characters/maren/bake_idle.py)、64×64の比較も焼くなら [crystal_mage/bake_idle.py](../characters/crystal_mage/bake_idle.py) を複写する。標準CLIは静止・歩行・攻撃を一括で焼き、1つでも収まらないと何も出力しない。画像由来のキャラクターは、静止専用のベイクから始める。

## 6. 焼き出しと反復

反復には、生成、NPZの保存、ベイク、拡大図をまとめた一時的なスクリプトを `.phase1/<name>/preview.py` に置く（追跡しない）。実験02で使った形は次の通り。

~~~python
import json, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
NAME = "new_character"
from importlib import import_module
build = import_module(f"characters.{NAME}.build_model").build
bake_idle = import_module(f"characters.{NAME}.bake_idle").bake_idle
from spritestack.character import load_character

config_path = ROOT / f"characters/{NAME}/character.json"
materials, parts = build(json.loads(config_path.read_text(encoding="utf-8")))
np.savez_compressed(config_path.parent / "materials.npz", slices=materials)
np.savez_compressed(config_path.parent / "part_ids.npz", parts=parts)
out = ROOT / f".phase1/{NAME}/{sys.argv[1]}"
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
bake_idle(load_character(config_path), out)
sheet = Image.open(out / "idle.png").convert("RGBA")
zoom = Image.new("RGBA", (4 * 298, 2 * 310 + 120), (58, 66, 84, 255))
draw = ImageDraw.Draw(zoom)
for i, d in enumerate(["S", "SW", "W", "NW", "N", "NE", "E", "SE"]):
    x, y = 10 + (i % 4) * 298, 10 + (i // 4) * 310
    draw.text((x, y), d, fill=(230, 230, 240))
    zoom.alpha_composite(sheet.crop((i * 48, 0, i * 48 + 48, 48)).resize((288, 288), Image.NEAREST), (x, y + 12))
zoom.alpha_composite(sheet, (10, 640))
zoom.alpha_composite(sheet.resize((768, 96), Image.NEAREST), (410, 620))
zoom.save(out / "zoom_48.png")
~~~

~~~powershell
& $python -B .phase1/$name/preview.py v1
~~~

`require_margin` が失敗したら、4. の式で上限を決めている部位を探して縮める。

### 毎回の確認

拡大図（6倍）と原寸を必ず両方見る。参考画像との並びはローカルにだけ作る。

| 方向 | 確認すること |
| --- | --- |
| S・SW・SE | キャラクターと分かるか。最大の衣装、主装備、副装備、顔、髪が読めるか。装備が正しい手にあるか |
| W・E | 横顔が髪や装備に隠れていないか。装備が浮いていないか。手前の装備が顔を横切っていないか |
| NW・N・NE | 背面の構造（髪、襟、外套）が一体の塊になっていないか。装備の先端が見えるか |
| 全方向 | 斑点（殻の透け）、迷い画素、細い部位の切れ、セルの端との余白 |
| 原寸 | 1×で最も重要な3要素が読めるか。他のキャラクターと並べて体形が区別できるか |

見つけた問題、原因、直し方を、レポートの「調整の経緯」のために毎回メモする。

### 終える基準

- 依頼文の優先順位の上位3つが、原寸で読める。
- 8方向で配色・装備・体形が一貫し、装備が隠れる方向は自然な遮蔽だけ。
- 7. の検証に合格する。
- 直す価値のある問題が、48 pxの解像度の限界によるものだけになった。

## 7. 検証

### 検証スクリプト

[verify_crystal_mage.py](verify_crystal_mage.py) を `research/verify_<name>.py` に複写し、次を書き換える。

| 箇所 | 書き換え |
| --- | --- |
| `MAGE_DIR`、`MAGE`、`PUBLISHED` | 新キャラクターのパス |
| 材質IDの定数（`CRYSTAL`、`STAFF_WOOD`、`BOOK`） | 主装備の主役・本体、副装備の材質ID |
| `BOOK_VIEWS` と下限の画素数 | 副装備が見えるべき方向。主役の小物の下限 |
| `check_rig` の装備の辞書 | 装備名、手、目印 |
| `check_handedness` | 主装備 x < 0、副装備 x > 0 |
| `check_connectivity` の接触の組と連続の検査 | 装備と手、手と前腕。細長い装備は床から先端までの連続 |
| `check_sources` の歩行・攻撃の確認 | 仮の参照ならLARKのクリップと一致。転用したなら転用規則と一致 |
| 64×64の検査 | 比較シートを焼かないなら外す |

検査の内容は次の通り。

- NPZが生成コードと一致。全材質・全部位が使われる。「抽出」の色が抽出結果と一致。
- `Biped` が装備を受け付け、静止で装備が手に追従。目印が装備の範囲内。
- 主装備は本人の右、副装備は左。
- モデル全体が1つにつながる。部位の切れ端は他部位に覆われ、3ボクセル未満の切れ端は16枚のどの描画にも出ない。装備と手、手と前腕、前腕と上腕、上腕と胸が接する。
- シートの寸法、方向順、アンカー、0か255の不透明度、1 px以上の余白。各コマが再描画と一致。反対方向の反転と一致しない。
- 装備の描かれる画面側が、3次元の位置の投影と一致。
- 主役の小物の可視画素が全方向で下限以上。副装備が見えるべき方向で下限以上。
- 公開PNG・JSONが焼いた出力と一致。

~~~powershell
$run = Join-Path $PWD ('.phase1/' + $name + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
& $python -B characters/$name/build_model.py --out (Join-Path $run 'model')
& $python -B -m characters.$name.bake_idle --out (Join-Path $run 'idle')
& $python -B -m research.verify_$name (Join-Path $run 'idle') --skip-published
~~~

`--skip-published` は公開前の確認用（CRYSTAL MAGEの検証にある引数）。`model/` のNPZがコミット対象と一致することも確かめる。

### 回帰テスト

新キャラクターを足しても、既存の出力が変わらないことを確かめる。

~~~powershell
& $python -B -m spritestack --character characters/lark/character.json --out (Join-Path $run 'lark')
& $python research/verify_rebuild.py (Join-Path $run 'lark')
& $python -B -m spritestack --character characters/bram/character.json --out (Join-Path $run 'bram')
& $python -B -m research.verify_bram (Join-Path $run 'bram')
& $python -B -m characters.maren.bake_idle --out (Join-Path $run 'maren')
& $python -B -m research.verify_maren (Join-Path $run 'maren')
& $python -B -m characters.crystal_mage.bake_idle --out (Join-Path $run 'crystal_mage')
& $python -B -m research.verify_crystal_mage (Join-Path $run 'crystal_mage')
git diff --stat -- spritestack characters/lark characters/bram characters/maren characters/crystal_mage experiments docs/assets
~~~

LARKの `verify_rebuild.py` は、PNGのバイトが一致しなくても（Windowsでは通常そうなる）、メタデータとデコード後のRGBAが一致すれば合格。BRAMは標準CLIの出力と `docs/assets/bram/` の静止・歩行・攻撃PNG、メタデータも照合しておく。最後の `git diff` は空であること。

### 標準CLIの試験（任意、公開しない）

`python -m spritestack --character characters/<name>/character.json --out <.phase1の新しいフォルダ>` を試し、止まる場合はどのモード・コマで、何が原因かを記録する。実験01は攻撃のセル、実験02は姿勢ボリュームで止まった。結果は公開しない。

## 8. 比較図、レポート、ギャラリー、文書

### 比較図

[image_to_character_02/compare.py](image_to_character_02/compare.py) を `research/image_to_character_NN/compare.py` に複写し、パス、装備の材質ID（`VISIBLE`）、色系統の色（`FAMILY_COLORS`）を書き換える。追跡する図は抽出色、座標、計測値と生成したPNGだけから作る。参考画像との並びは `--local-out` で `.phase1/` にだけ出す。

~~~powershell
& $python -B -m research.image_to_character_NN.compare --idle (Join-Path $run 'idle') --out research/image_to_character_NN/results --reference (Join-Path $work 'reference.png') --local-out (Join-Path $run 'reference_comparison.png')
~~~

### レポート

`research/IMAGE_TO_CHARACTER_NN.md` を、実験02と同じ構成で書く。

1. 結論（技術面と外見面を分ける）
2. 実験目的
3. 参考画像から抽出した特徴（数値付き）と、立体化が難しい部分
4. 立体化の方法（工程表、コマンド、部位と描画順、体の寸法）
5. 自動生成で成功した点
6. 人による補完・調整（自動の処理と、制作AIの判断を分けた表。調整の経緯）
7. 確認できた特徴、推測で補った特徴、規約・解像度による変更、未再現（表）
8. 8方向の品質（方向ごとの表と可視画素）
9. 解像度の比較（行った場合）
10. 既存エンジンの制約と拡張案
11. 今後の改善候補
12. 技術検証（実行した検査だけ。環境とバージョン）
13. 権利と追跡、未確認事項

書く前に、レポートの数値を計測JSON、検証の出力、コードと照合する。実験02では、外形の寸法、裾の高さの向き、装飾のねじれの向き、装備が見える方向の4か所を照合で直した。実行していない検査を実施済みと書かない。

### ギャラリー

1. 焼いた `idle.png`、`metadata.json`（比較シートがあれば `idle-64.png`、`idle-64.json`）を `docs/assets/<name>/` に複写する。
2. `docs/index.html` のキャラクター欄に `<option value="<name>">` を足す。
3. `docs/gallery.js` の `characters` に `{ name, subtitle, assets: "assets/<name>" }` を足す。比較シートがあれば `idleSheets: { 48: null, 64: "idle-64" }` を加える。歩行・攻撃がないキャラクターでは、ボタンが自動で無効になり注記が出る。
4. ローカルサーバーで確かめる。新キャラクターの8方向（比較シートがあれば両方）、既存キャラクターの攻撃再生、375 px幅で横スクロールがないこと、コンソールエラーがないこと。

~~~powershell
& $python -m http.server 8000 --bind 127.0.0.1 --directory docs
~~~

### 文書

README（実装状況、ディレクトリ構成、生成と検証の節、ギャラリーの節）、AGENTS.md（キャラクターの項目を1つ）、[ROADMAP.md](ROADMAP.md)（実装・検証済み）を更新する。

## 9. コミットと公開

1. `git status --short --untracked-files=all` で、参考画像と `.phase1/` の中身が含まれていないことを確かめる。
2. コミットするのは、`characters/<name>/`、`docs/assets/<name>/`、ギャラリー、検証・比較スクリプトと結果、レポート、文書。
3. 依頼者が求めた場合に、mainへコミットしてpushする（GitHub Pagesの公開元はmainの `/docs`）。
4. 公開ページで新キャラクターを選び、8方向を確かめる。以前に開いたブラウザでは `gallery.js` が最大10分キャッシュされ、新しいキャラクターを選ぶとエラーになることがある。その場合は再読み込みするか、時間をおいて確認する。

URL：https://shioa2006-game.github.io/SpriteStack_Character_Lab/

## 付録：チェックリスト

- [ ] 参考画像を `.phase1/<name>/` に置き、SHA-256を記録した。画像は追跡していない
- [ ] 特徴、比率、配色の衝突、左右、装備、難所の表を作った
- [ ] 採色範囲の確認図を目視し、抽出結果が見た目と合う
- [ ] 頭身と、48 pxの高さの予算を計算した
- [ ] 設計規則（殻の厚さ、細い部位の半径、主役の小物、目、同系色の分離）を適用した
- [ ] 配色の出典を全材質に書いた
- [ ] `-W error::RuntimeWarning` で生成できる
- [ ] 8方向を拡大と原寸で確認し、調整の経緯をメモした
- [ ] 新キャラクターの検証と、LARK・BRAM・MAREN・CRYSTAL MAGEの回帰に合格した
- [ ] 既存の成果物にGit差分がない
- [ ] 比較図とレポートを書き、数値を照合した
- [ ] ギャラリーをローカルで確認した
- [ ] コミット、push、公開ページで確認した
