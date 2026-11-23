# 参考画像1枚から静止・歩行・攻撃を作る

完成品は、同じ二足歩行モデルから焼いた8方向の透過PNG、再生用JSON、攻撃GIF、原寸で確認できるギャラリー。**制作AIが決めるのは、画像を何の形・配色・関節・ポーズに置き換えるか**。決めた内容はモデル生成コードと設定に残す。ベイクと検証は既存のCLIで繰り返せる。作業前に [開発規約](../AGENTS.md) を確認する。寸法、座標軸、出力配置を調べる場合は [技術設計](../docs/TECHNICAL_DESIGN.md) を使う。

## 1. 画像を読み、何を残すか決める

元画像を原寸と拡大で見る。人物を識別する特徴を三つ、優先順に書く。例えばMARENなら長い青髪・長剣・丸盾、MAGEなら長いローブ・水晶杖・本、RONINならポニーテール・スカーフ・反りのある刀。雛形は配色の近さよりも、**動かす部位と装備構成**で選ぶ。[MAREN](../characters/maren/) · [CRYSTAL MAGE](../characters/crystal_mage/) · [AZURE RONIN](../characters/azure_ronin/)

| 記録するもの | 次工程での用途 |
| --- | --- |
| 足底、足首、膝、腰、肩、顎、頭頂。肩・裾・装備の幅 | 身長を1とした高さと幅を求め、関節と外形を別々に決める |
| 髪の流れ、服の重なり、装備の付け根・握り・先端 | 所属部位、左右、揺れる領域、攻撃時に追う点を決める |
| 見えない背面・装備の裏、絵の遠近やなびき | 観察と推定を分けて記録する。衣装の構造が側面・背面へ連続する形を選ぶ |
| 原寸で消えそうな小物、隣り合う同系色 | 色を分ける、配置をずらす、装飾を省略する候補を決める |

以下はルートで実行するPowerShell。先に [Python環境](../README.md#windowsのpython環境) を用意する。`new_character` は新規のPython識別子に、画像パスは渡されたファイルに置き換える。反復ごとに新しい `$run` を取る。

```powershell
git status -sb
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$name = 'new_character'
$char = "characters/$name"
$config = "$char/character.json"
$reference = 'C:\path\to\reference.png'
$run = Join-Path $PWD ('.phase1/' + $name + '-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $run | Out-Null
Get-FileHash -LiteralPath $reference -Algorithm SHA256
```

**次へ進む条件**　目印・主要な色・本人基準の左右が分かり、原寸で残す特徴と背面をどう補うかが説明できる。権利が不明な元画像やそれを含む確認図は公開フォルダへ置かない。

## 2. 採色し、体形・衣装・装備を設計する

選んだ雛形を基に新しい `$char` を用意し、`reference_regions.json` に原画像の寸法、材質別の複数の矩形、除外領域、色の系統、ランドマークを記入する。矩形の右端・下端は含まない。原画像に矩形を重ねて見て、髪に背景、肌に服の影が混ざっていないか確かめる。採色は [MARENの抽出関数](../characters/maren/extract_reference.py) を再利用し、必要な追加計測だけ自分の抽出モジュールに書く。例は [RONINの刀の反りと幅の計測](../characters/azure_ronin/extract_reference.py)。

```powershell
& $python -m "characters.$name.extract_reference" --image $reference --regions "$char/reference_regions.json" --out "$char/reference_palette.json"
```

抽出処理は指定領域の画素を明度で並べ、帯域ごとに代表色を求める。既存の背景除去は白に近い背景を想定するので、複雑な背景や透過画像では抽出に使った画素を点検する。採用色は `model.palette` に、出典と理由は `palette_provenance.json` に `extracted`・`adjusted`・`derived` として残す。MAGEの髪とマントは似た明度だったため、髪を暗くし、間に明るいフードを置いた。RONINのポニーテールは髪と同色の別材質・陰影グループにすると、背面で境界が立ち、可視画素も測れる。[配色と衣装](IMAGE_TO_CHARACTER_02.md) · [髪と刀](IMAGE_TO_CHARACTER_03.md)

**次へ進む条件**　抽出結果が画像の印象と一致し、大小の色面、前後の層、主要装備の握りと先端を設計できた。参考画像から変えた頭身、左右、色には理由がある。

## 3. モデルを生成し、リグに装着する

雛形の `character.json`、`build_model.py`、`quality.json` と専用攻撃クリップを新キャラクター用に編集する。旧来の個別 `bake_idle.py` は不要。モデルの相対パス、生成モジュール名、公開先、品質条件に雛形の名前を残さない。静止から始める場合も `walk.clip` に `../../motions/walk.json`、`attack.clip` に読み込める攻撃クリップを指定する。キャラクターの状態説明は実際に完成した工程に合わせる。

- `build(config)` で楕円体・カプセル・箱・殻などを組み、材質と所属部位を一緒に塗る。顔・髪は頭、肩の布は胸、腰の裾は骨盤へ割り当てる。後に塗る形状が前の所属を上書きするので、握りは手が柄を包む順序にする。[剣と盾の生成例](../characters/maren/build_model.py)
- 静止の格子はビルダーの `SHAPE`（Z/Y/X）、`model.origin_xyz`、`voxel_size_xyz` で決まる。手・裾・装備の全端点を囲むように取る。動かした剣先や布の端が越える場合は、別に `posed_volume` の境界を見直す。
- `rig.rest` の肩・肘・手、股・膝・足首を実際の形に置き、`rig.attachments` と装備マーカーを対応づける。既存の検証が扱う標準は右主手・任意の左副手。空の手側にダミー装備を作る必要はない。
- 立体の表面に裏地が点々と現れるなら殻の外層と内側の突出を点検する。細い杖は軸の連続性を、刀は刃を横から見た厚みを確かめる。実験02の杖半径0.6、実験03の刀身厚さ0.9モデル単位は、当時の格子と投影で途切れを防いだ例。[実験間の比較](IMAGE_TO_CHARACTER_COMPARISON.md)
- `quality.json` の `model_builder`、`provenance`、`motions.walk.clip`、`items`、`visibility`、`presence` と必要な `continuous` を自分のモデルに合わせる。装備名・材質ID・目印は `character.json` の `measurements` とも突き合わせる。[品質設定と検出例](SHARED_IDLE_BAKE_AND_VALIDATION.md)

```powershell
& $python -W error::RuntimeWarning "$char/build_model.py" --out "$run/model"
Copy-Item "$run/model/materials.npz","$run/model/part_ids.npz" -Destination $char
```

このコピー先は制作中の新キャラクター。既存サンプルで手順を試す場合は作業出力に留める。**次へ進む条件**　設定が読む2つのNPZがそろい、空と占有の位置、部位ID、関節と握りが [モデルの契約](../docs/TECHNICAL_DESIGN.md#水平断面と部位の所属) に合う。

## 4. 静止8方向で造形を確定する

```powershell
& $python -m spritestack --character $config --modes idle --out "$run/idle"
& $python -m research.verify_character --character $config --out "$run/idle" --no-published --verbose
```

`--no-published` は初回制作中の比較を省く。比較セルを使うなら `comparison_view` と品質設定の `cells` を揃える。MAGE・RONINは標準48と比較64を同じ立体から焼く。S・SW・SEでは顔と装備の左右、W・Eでは横顔と握り、NW・N・NEでは髪・襟・背面装備の重なりを見る。装備が方向によって見えないときは単独描画と全身描画を比較する。MAGEはWで杖頭の上に1 pxしか残らず、静止でさらに杖を高くすると歩行の余裕も失う。[静止実験01](IMAGE_TO_CHARACTER_01.md) · [静止実験02](IMAGE_TO_CHARACTER_02.md)

**次へ進む条件**　モデル再生成、接続、余白、RGBA、方向順が合格し、初めに選んだ特徴が1×で読める。閾値は実測と必要な見え方から設定する。背面で自然に隠れる本を全方向可視の条件にしない。

## 5. 共通歩行を体格に合わせる

```powershell
& $python -m spritestack --character $config --modes walk --out "$run/walk"
& $python -m research.verify_walk --character $config --out "$run/walk" --no-published --verbose
```

最初の `walk.png` を比較用に残す。脚長に合わせて `walk.tuning.stride_scale` と支持足の開始位置 `stance_start_y` を一緒に調整する。届かない足首をIKに渡すとベイクが止まる。接地中の足が滑る、腕と同じ側の脚が同時に前へ出る、盾が振れすぎる、といった症状は歩幅・腕振りの符号・左右別の振幅を順に見る。MAGEでは腕を上げると杖頭がセルを越えたため、手の高さを抑え、手首で杖を前へ傾けた。[3体の歩幅・位相・装備の比較](WALK_ANIMATION_VERIFICATION.md)

**次へ進む条件**　8方向×6コマで接地、足元アンカー、装備の接続・床との位置に破綻がなく、6→1コマ目も自然につながる。歩行の `quality.json.walk` には測る装備・材質・床の下限等を指定する。

## 6. 頭、髪、布を歩きに連動させる

| 原寸で見える症状 | 調整箇所と手本 |
| --- | --- |
| 脚だけ歩き、頭が全コマで止まる／目がちらつく | `walk.head` で首の移動に追従させ、胴の上下動と `snap` を合わせる。まず回転0・移動1単位刻みを試す。目・首の距離・肩との動きを並べて見る。[頭部連動の試行](HEAD_MOTION_VERIFICATION.md) |
| 裾が太ももを突き抜ける／長髪が棒に見える | 裾は `skirt` の起点と `drive`（長い裾は脚全体、短い裾は太ももが候補）、房は `pendulum` の付け根・先端・遅れ・最大角を調整する。背中に乗る髪は胸を追わせる。RONINのスカーフの端だけ選ぶには材質と領域を絞る。[歩行と衣装](WALK_ANIMATION_VERIFICATION.md) |
| E・NEで剣が点線に見える | 元モデルの厚みと握りを点検し、剣だけ `walk.fine` の再サンプリングを試す。手前の手袋が残り、自然な反りが1本につながって見えるか確認する。[剣の比較](SWORD_WALK_VERIFICATION.md) |

手順5のコマンドを新しい出力先で再実行する。**次へ進む条件**　頭が肩と一緒に動き、顔が読める。固定すべき布の付け根は残り、裾や先端に追従が見える。検証の `walk.head`、衣装の干渉、部位の残存を確認し、初回と最終の歩行を原寸で比べる。

歩行GIFだけを取り出すときは既存の比較器の読込・保存関数を使える。次の例では8方向が左から順に並び、各方向を48×48のまま再生する。

```powershell
@'
from pathlib import Path
import sys
from research.walk.compare import sheet_frames, save_gif

folder = Path(sys.argv[1])
layout, frames = sheet_frames(folder)
save_gif(folder / "walk-x1.gif", [frames], layout["fps"], 1)
'@ | & $python - "$run/walk"
```

## 7. 装備に合う攻撃を作る

まず構え、予備動作、最も力を蓄える姿勢、斬撃または発動、振り抜きまたは余韻、復帰を描き分ける。**各局面で「手・先端・腰を直前のコマからどこへ移すか」「どの姿勢を何ms見せるか」を決める。** 先端が奥行き方向に短く投影される正面では、腰、足幅、副手の高低差も手掛かりになる。

| 作例 | クリップを編集するときの着眼点 | 原寸での判断 |
| --- | --- | --- |
| [MARENの踏み込み斬り](MAREN_DYNAMIC_SLASH.md) | 剣先を背後から頭上、前方、膝より下へ通す。盾を引き寄せ、軸足を残して腰を沈める | S・W・E・NWで溜めと斬撃と振り抜きの3枚を区別できるか |
| [RONINの速斬り](AZURE_RONIN_QUICK_SLASH.md) | 肩へ短く引き、着地で腰を返し、反対側へ払う。短い斬撃の後に低い姿勢を見せる | NE・Eで刀がしならず、NWで切っ先が胴から出るか。速度を上げても軌道が読めるか |
| [MAGEの詠唱](CRYSTAL_MAGE_CAST.md) | 本を胸へ上げて杖を寝かせ、身体を引いて水晶を起こす。発動で杖を送り本を下げ、余韻で杖を戻す | 発光を外しても詠唱と発動のシルエットが違うか。S・SEで両手の差が見えるか |

`attack.clip` は各体の `slash.json` または `cast.json` を雛形にする。`poses`・`keys`・`durations_ms` の長さを揃え、始終端を空キー `{}` にして静止と接続する。攻撃の9コマは作例の構成。3〜6コマ目を原寸で横に並べて差を見てから間を詰める。役割の違う武器への転用では、中盤の局面から設計し直す。

- 両足・両手の到達範囲内で `root`・`yaw`・`lean`、踏み足の `front_step`・`front_lift`・任意の `front_outward` を決める。右手の `hand_R` は目標座標、`elbow_pole_R` は肘を曲げる方向。別体形へ手の絶対座標を写すと届かないことがある。
- 剣は `blade` が方向、`wrist_roll` がその軸回りの角度、副手は `shield_delta`。杖は `aim` と副手の `support_delta`・`support_pitch` を使う。静止時の `weapon_axis` と握りを合わせる。MAGEの `glow`・`glint` はポーズ確定後に使う水晶の演出例。
- `attack.follow_cloth` は既存の髪・布の領域を使える。剣の `attack.fine`、頭部の `attack.tuning` も歩行とは別に確認する。`quality.json.attack` で `feature` を `measurements.visibility` の部位・材質名に対応するキーへ、`phase` を実際の局面名へ、`minimum_visible_px` をその局面で全方向に必要な画素数へ合わせる。

**次へ進む条件**　支持足・握りを保った状態で、局面ごとに手・装備先端・身体の関係が変わる。剣が髪に完全に埋もれる、発動の前後で杖が同じ場所に留まる場合は、先端の軌道と重心を直して焼き直す。

## 8. 全モードを焼き、技術と見た目を別々に判定する

```powershell
& $python -m spritestack --character $config --out "$run/all"
& $python -m research.verify_walk --character $config --out "$run/all" --no-published
& $python -m research.verify_attack --character $config --out "$run/all" --gif "$run/all/attack.gif"
```

**技術判定**　静止専用の検証と合わせてFAIL 0。IK、支持足、装備の固定、主要局面の可視画素、セル内余白、方向順、始終端と静止の一致を確認する。WARNINGは部位・方向・見た目への影響を、SKIPは未公開などの理由を記録する。攻撃検査で補間しているのは指定した点・材質であり、装備全体が全中間姿勢で非交差だとは言えない。[検証範囲](../docs/TECHNICAL_DESIGN.md#検証の適用範囲)

**目視判定**　GIFでタイミングを見て、ギャラリーの1×・通常速度で全8方向を再生する。さらに変更前後の同方向を同時再生し、問題が出たコマだけ拡大する。剣が消える場合は、装備単独でも分断されるかを調べる。全身だけで消えるなら自然な遮蔽か、肝心の局面が読めなくなる配置かを判定する。公開GIFは拡大プレビューなので原寸判定を兼ねない。

初回の全ベイクと改善版を手順9の形式で別々の作業フォルダに保存すれば、既存の比較器で1×比較GIFとポーズ表を作れる。以下は既存素材で動く詠唱の例。新キャラクターでは `--before`・`--after` と局面名を替える。両版のセル、アンカー、方向順、局面名の列、総時間が同じ場合に使える。構成自体を変えた版では、それぞれ本来の時間で再生して比較する。

```powershell
& $python -m research.maren_slash.compare --before research/mage_cast/baseline --after docs/assets/crystal_mage --out "$run/comparison" --prefix cast --phases invoke channel focus release hold --directions S SW W NW N NE E SE
```

**次へ進む条件**　技術結果と、どの方向の何コマ目で何が読めたかの両方を説明できる。他モードにも関わる変更をした場合は同じ体の全モードを再生成し、共通処理に変更があれば [既存サンプルと旧資産の回帰](../AGENTS.md#検証と公開) を行う。

## 9. 公開形式を組み、ギャラリーで確認する

まず作業フォルダに公開候補を作る。**静止の `metadata.json` は静止専用ベイクから取る。** 歩行と攻撃のレイアウトは全ベイクのメタデータからモードごとに取り出す。次の例はWindows PowerShellでもUTF-8でJSONを保存する。

```powershell
$assets = New-Item -ItemType Directory -Path "$run/assets"
Copy-Item "$run/idle/idle.png","$run/idle/metadata.json","$run/all/walk.png","$run/all/attack.png","$run/all/attack.gif" -Destination $assets
Get-ChildItem "$run/idle/idle-*" -File | Copy-Item -Destination $assets
$meta = Get-Content "$run/all/metadata.json" -Raw -Encoding utf8 | ConvertFrom-Json
foreach ($mode in 'walk', 'attack') {
    $layout = @{ animations = @{ $mode = $meta.animations.$mode } }
    $json = $layout | ConvertTo-Json -Depth 32
    [IO.File]::WriteAllText((Join-Path $assets.FullName "$mode.json"), $json, [Text.UTF8Encoding]::new($false))
}
& $python -m research.verify_character --character $config --out "$run/idle" --published $assets.FullName
& $python -m research.verify_attack --character $config --out "$run/all" --published $assets.FullName
```

1. 検証した一式を `docs/assets/<name>/` に置く。比較GIF・ポーズ図を公開する場合はそれも加える。`quality.json.published`（歩行側で指定していれば `walk.published` も）を新しい公開先へ向ける。静止・歩行の検証を `--no-published` なしで、攻撃の検証を `--published "docs/assets/$name"` 付きで再実行する。作業用の部位IDやボリュームは公開対象から外す。
2. [index.html](../docs/index.html) の選択肢と [gallery.js](../docs/gallery.js) の `characters` に同じIDを追加する。値は `name`、`subtitle`、`assets: "assets/<name>"`、`extraAnimations: ["walk", "attack"]`。追加画像がある場合だけ `idleSheets: {48: null, 64: "idle-64"}` と `attackComparison` のファイル名を指定する。
3. READMEのローカルサーバーを起動する。1×で全方向、静止→歩行→単発攻撃→再生、GIFリンク、比較解像度を確認する。公開を依頼されたらコミット・push後にmainの `/docs` のPages反映と本番画面も確認する。
4. 制作記録には、画像で確認できた特徴と推定した背面、配色・寸法の変更理由、失敗した方向と局面、改善前後の画像、実行した検証、未評価の状況を残す。権利不明の参考画像や作業フォルダがステージされていないか `git status` で確認する。

**完成条件**　別の出力先へ再生成した静止・歩行・攻撃のRGBAとメタデータが公開候補に一致し、ギャラリーとGIFで意図した動作が読める。新しい体形での調整値と残った制約を、次の制作者が再確認できる。
