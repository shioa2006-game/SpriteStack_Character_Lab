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

### 目的別の作例

最初に頭身・腕と脚の長さ・肩幅、本人基準の主手と副装備、衣装の固定点、必要なモーションを記録する。造形、歩行、攻撃それぞれで近い作例を選ぶ。例えば小柄な重装の戦士なら、肩甲の重なりはFLEUR、短い脚の支持はGOBLIN、槌頭の振り切りはGARDから調べられる。

| 作りたい人物・動き | 参考にする部分 |
| --- | --- |
| 剣と盾 | [MAREN](../characters/maren/) の踏み込みと副手、[FLEUR KNIGHT](IMAGE_TO_CHARACTER_04.md) の大盾・兜・肩甲、[SKELETON GUARD](IMAGE_TO_CHARACTER_07.md) の細い腕と盾の前後関係 |
| 速い刀剣士 | [AZURE RONIN](AZURE_RONIN_QUICK_SLASH.md) の予備動作と短い斬撃、[CRIMSON BLADE](IMAGE_TO_CHARACTER_05.md) の鞘・刀・腰布の所属 |
| 重戦士・打撃 | [GARD](adventurers/gard-hammer/README.md) の槌頭・体重移動と重いマント、[GOBLIN BRUTE](IMAGE_TO_CHARACTER_06.md) の短い脚と棍棒。重装の外形にはFLEURも使える |
| 小柄な斥候・弓使い | [RICO](../characters/rico/) の短い歩幅、フード・襟巻・矢筒で残す色面、左手の弓と右手の弦。短い脚でもがっしりした体形にはGOBLINの歩行を比較する |
| 杖・長いローブ | [SENA](../characters/sena/) の銀髪・裾・片手詠唱・放出、[CRYSTAL MAGE](CRYSTAL_MAGE_CAST.md) の本と杖の高低差・発光・杖の余白 |

正式3体が再生成の基準になる。冒険者の歩行テンポ・背面の識別点・正面の目が揃うまでの比較は [待機・歩行の制作記録](adventurers/README.md)、左手の弓や氷片は [攻撃の制作記録](adventurers/ATTACKS.md) から該当する設定へ進める。

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
& $python -m characters.maren.extract_reference --image $reference --regions "$char/reference_regions.json" --out "$char/reference_palette.json"
```

抽出処理は指定領域の画素を明度で並べ、帯域ごとに代表色を求める。既存の背景除去は白に近い背景を想定するので、複雑な背景や透過画像では抽出に使った画素を点検する。採用色は `model.palette` に、出典と理由は `palette_provenance.json` に `extracted`・`adjusted`・`derived` として残す。MAGEの髪とマントは似た明度だったため、髪を暗くし、間に明るいフードを置いた。RONINのポニーテールは髪と同色の別材質・陰影グループにすると、背面で境界が立ち、可視画素も測れる。[配色と衣装](IMAGE_TO_CHARACTER_02.md) · [髪と刀](IMAGE_TO_CHARACTER_03.md)

**次へ進む条件**　抽出結果が画像の印象と一致し、大小の色面、前後の層、主要装備の握りと先端を設計できた。参考画像から変えた頭身、左右、色には理由がある。

## 3. モデルを生成し、リグに装着する

雛形の `character.json`、`build_model.py`、`quality.json` を新キャラクター用に編集する。旧来の個別 `bake_idle.py` は不要。モデルの相対パス、生成モジュール名、公開先、品質条件に雛形の名前を残さない。`walk.clip` に `../../motions/walk.json` を指定し、呼吸待機を作る場合は `breathe`、専用攻撃を作る場合は `attack` を設定する。[待機4コマ・歩行6コマの制作例](adventurers/README.md)

- `build(config)` で楕円体・カプセル・箱・殻などを組み、材質と所属部位を一緒に塗る。顔・髪は頭、肩の布は胸、腰の裾は骨盤へ割り当てる。後に塗る形状が前の所属を上書きするので、握りは手が柄を包む順序にする。[剣と盾の生成例](../characters/maren/build_model.py)
- 冒険者のビルダーは [Volume](../characters/voxel_shapes.py) を共有し、`model.shape_zyx`・`origin_xyz`・`voxel_size_xyz` から静止格子を作る。正式3体の格子寸法は各ビルダーの `SHAPE`（Z/Y/X）。手・裾・装備の全端点を囲み、動かした部位だけが越える場合は姿勢格子を見直す。
- `rig.rest` の肩・肘・手、股・膝・足首を実際の形に置く。`rig.attachments` の各部位に実際の手とマーカーを指定し、攻撃の主手を `attack.tuning.main_hand_side` に設定する。静止検査の `quality.items` は左右の取り付けを表す。リコの左手弓は静止検査で `off`、攻撃で `L`。空いた右手にも引き絞り時のIK目標がある。[リコの品質条件](../characters/rico/quality.json) · [左手主武器の設定](../characters/rico/character.json)
- 立体の表面に裏地が点々と現れるなら殻の外層と内側の突出を点検する。細い杖は軸の連続性を、刀は刃を横から見た厚みを確かめる。実験02の杖半径0.6、実験03の刀身厚さ0.9モデル単位は、当時の格子と投影で途切れを防いだ例。[実験間の比較](IMAGE_TO_CHARACTER_COMPARISON.md)
- `quality.json` の `model_builder`、`provenance`、`motions.walk.clip`、`items`、`visibility`、`presence` と必要な `continuous` を自分のモデルに合わせる。装備名・材質ID・目印は `character.json` の `measurements` とも突き合わせる。[品質設定と検出例](SHARED_IDLE_BAKE_AND_VALIDATION.md)

```powershell
& $python -W error::RuntimeWarning -m "characters.$name.build_model" --out "$run/model"
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

呼吸待機を作るときは静止を始点に胸と肩を小さく動かし、靴底と握りを確認する。全ベイクの `breathe` を正面で1コマずつ送り、両目の上端・下端と前髪の重なりを見る。肌と瞳が原寸で混ざる場合は頭部モデルの色・深さを点検する。リコとセナでは、静止だけを見た段階で見逃した顔の非対称が待機・歩行で現れた。[顔の比較画像](adventurers/README.md)

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

歩行を単独で比較するには [歩行比較器](walk/compare.py) を使う。手順9の公開候補には、モードごとに8方向を原寸で並べ、再生時間を累積してGIFの刻みに合わせたプレビューが含まれる。

## 7. 装備に合う攻撃を作る

まず「画面のどこにいる相手へ、どの部位で何をする動きか」を一文で決める。モデル空間（+Yが前）で打点・射出点を選び、発動の位置から予備動作と振り抜き・戻りを逆算する。**各局面で、骨盤・肩・肘・手首・先端と両足をどこに置き、何ms見せるかを決める。** 正面では奥行きが縮むので、腰、足幅、副手の高低差も手掛かりになる。剣の横払いなら横方向の弧、槍の突きの研究なら穂先と肩の前後差が候補になる。槍を用いた作例は未検証。

| 作例 | クリップを編集するときの着眼点 | 原寸での判断 |
| --- | --- | --- |
| [MARENの踏み込み斬り](MAREN_DYNAMIC_SLASH.md) | 剣先を背後から頭上、前方、膝より下へ通す。盾を引き寄せ、軸足を残して腰を沈める | S・W・E・NWで溜めと斬撃と振り抜きの3枚を区別できるか |
| [RONINの速斬り](AZURE_RONIN_QUICK_SLASH.md) | 肩へ短く引き、着地で腰を返し、反対側へ払う。短い斬撃の後に低い姿勢を見せる | NE・Eで刀がしならず、NWで切っ先が胴から出るか。速度を上げても軌道が読めるか |
| [MAGEの詠唱](CRYSTAL_MAGE_CAST.md) | 本を胸へ上げて杖を寝かせ、身体を引いて水晶を起こす。発動で杖を送り本を下げ、余韻で杖を戻す | 発光を外しても詠唱と発動のシルエットが違うか。S・SEで両手の差が見えるか |
| [GARDの重打撃](adventurers/gard-hammer/README.md) | 打点は槌頭中心。支持足を残し、腰・肩を返して踏み込み、打撃後も肘を開いて身体ごと押し込む | E・Wで槌頭が右手と胸を越え、次のコマでも進むか。N・NWで盾と重なったときも振り切りが読めるか |
| [RICOの射撃](../characters/rico/bow-shot.json) | 左の弓を上げ、右手に矢筈を付けて弦を引く。照準を保ち、離弦後だけ矢を離す | S・Nで短く見える矢を、両手の開き・弓枠・弦の変化からも読み取れるか。発射後に二重の矢が残らないか |
| [SENAの氷魔法](../characters/sena/frost-cast.json) | 水晶に力を集め、身体ごと杖を送り、髪とローブを遅れて戻す。粒子は発動コマに絞る | 杖を上げた詠唱と前へ向けた放出を、光る前の姿勢から区別できるか |

`attack.clip` は各体の `slash.json` または `cast.json` を雛形にする。`poses`・`keys`・`durations_ms` の長さを揃え、始終端を空キー `{}` にして静止と接続する。攻撃の9コマは作例の構成。3〜6コマ目を原寸で横に並べて差を見てから間を詰める。役割の違う武器への転用では、中盤の局面から設計し直す。

- 両足・両手の到達範囲内で `root`・`yaw`・`lean`、踏み足の `front_step`・`front_lift`・任意の `front_outward` を決める。主手側の `hand_R` または `hand_L` は目標座標、同側の `elbow_pole_R/L` は肘を曲げる方向。反対の手は胴の移動に副手の差分を加えて解く。肩・腰・足を含め、新しい腕長で届く座標を選ぶ。
- 剣は `blade` が方向、`wrist_roll` がその軸回りの角度、副手は `shield_delta`。杖は `aim` と副手の `support_delta`・`support_pitch` を使う。静止時の `weapon_axis` と握りを合わせる。MAGEの `glow`・`glint` はポーズ確定後に使う水晶の演出例。
- `attack.follow_cloth` は既存の髪・布の領域を使える。剣の `attack.fine`、頭部の `attack.tuning` も歩行とは別に確認する。`quality.json.attack` で `feature` を `measurements.visibility` の部位・材質名に対応するキーへ、`phase` を実際の局面名へ、`minimum_visible_px` をその局面で全方向に必要な画素数へ合わせる。
- 大きな軌道は先に姿勢格子の境界、次に8方向のセル余白を調べる。攻撃だけはみ出すときは `attack.posed_volume`、画面端なら `attack.cell` を調整し、モード別アンカーで足元を揃える。通常格子の原点を動かすと、同じ待機・歩行でも再サンプリングされる。
- ゲームへ渡す打撃・発射・放出はクリップの `events` で発動コマとマーカーを指定する。イベント時刻、モデル位置、方向をベイクから読み、矢の引き継ぎはシート内の飛翔像が終わる境界に合わせる。[弓・発光・イベントと座標の仕様](../docs/TECHNICAL_DESIGN.md#攻撃装備とイベント)

**次へ進む条件**　支持足・握りを保った状態で、局面ごとに手・装備先端・身体の関係が変わる。剣が髪に完全に埋もれる、発動の前後で杖が同じ場所に留まる場合は、先端の軌道と重心を直して焼き直す。

## 8. 全モードを焼き、技術と見た目を別々に判定する

```powershell
& $python -m spritestack --character $config --out "$run/all"
& $python -m research.verify_walk --character $config --out "$run/all" --no-published
& $python -m research.verify_attack --character $config --out "$run/all" --gif "$run/all/attack.gif"
```

**技術判定**　静止専用の検証と合わせてFAIL 0。IK、支持足、装備の固定、主要局面の可視画素、セル内余白、方向順、始終端と静止の一致を確認する。WARNINGは部位・方向・見た目への影響を、SKIPは未公開などの理由を記録する。攻撃検査で補間しているのは指定した点・材質であり、装備全体が全中間姿勢で非交差だとは言えない。[検証範囲](../docs/TECHNICAL_DESIGN.md#検証の適用範囲)

**目視判定**　ギャラリーの1×・通常速度で全8方向を再生する。待機→攻撃→待機と歩行→攻撃を試し、溜め・発動・余韻の差、体格に合った速さ、足元と復帰を見る。原寸GIFで変更前後を同時再生し、問題が出た方向・コマだけ拡大する。公開GIFの倍率と配置は作例で異なる。

**原寸と3Dで原因を切り分ける。** 装備単独でも欠けたら、元の形・姿勢格子の切れ・細い部分の描画を調べる。全身だけで消えたら部位IDと前後関係を見る。自然に隠れる柄を許容できても、打点のコマで何をしたか読めなければ、先端・肩・肘・腰・足の軌跡と同方向の原寸像を突き合わせる。GARDの初版はIK・握り・可視画素の検査を通り、槌頭が身体の横へ落ちていた。打点と押し込みを先に直し、NWで隠れた復帰コマを最後に調整した。ここで測った前進量はこの槌と演出の結果である。

変更前後の**ベイクフォルダ**を保存すれば、コマ数やセルが変わっても比較できる。以下の `$before` は修正前の攻撃ベイク。計測点は各体の `joints.json` から選ぶ。同一版を両引数に指定すると、その版の単独分析にも使える。[入出力・弓の欠測・検証例](attack/README.md)

```powershell
& $python -m research.attack.compare_motion --before $before --after "$run/all" --out "$run/comparison" --markers hammer_head hand_R shoulder_R pelvis toe_L --relative-to hand_R --frames 4 5 6 7 --directions E S NW
```

**次へ進む条件**　技術結果と、どの方向の何コマ目で何が読めたかの両方を説明できる。他モードにも関わる変更をした場合は同じ体の全モードを再生成し、共通処理に変更があれば [既存サンプルと旧資産の回帰](../AGENTS.md#検証と公開) を行う。

## 9. 公開形式を組み、ギャラリーで確認する

まず作業フォルダに公開候補を作る。`research.export_loops` は静止専用ベイクと全ベイクのカメラ・静止像を照合し、静止のメタデータと各モードのPNG・JSON・原寸GIFを組にする。呼吸待機があれば `breathe` も含む。比較解像度の静止ファイルは別にコピーする。

```powershell
$assets = "$run/assets"
& $python -m research.export_loops --neutral "$run/idle" --animated "$run/all" --out $assets
Get-ChildItem "$run/idle/idle-*" -File | Copy-Item -Destination $assets
& $python -m research.verify_character --character $config --out "$run/idle" --published $assets
& $python -m research.verify_attack --character $config --out "$run/all" --published $assets
if (Test-Path "$assets/breathe.json") {
    & $python -m research.verify_loops --character $config --out "$run/all" --published $assets
}
```

1. 検証した一式を `docs/assets/<name>/` に置く。比較GIF・ポーズ図を公開する場合はそれも加える。`quality.json.published`（歩行側で指定していれば `walk.published` も）を新しい公開先へ向ける。静止・歩行の検証を `--no-published` なしで、攻撃の検証を `--published "docs/assets/$name"` 付きで再実行する。作業用の部位IDやボリュームは公開対象から外す。
2. [index.html](../docs/index.html) の選択肢と [gallery.js](../docs/gallery.js) の `characters` に同じIDを追加する。`name`、`subtitle`、`assets` と実際に出力した `extraAnimations` を登録する。冒険者は `["breathe", "walk", "attack"]`。比較解像度や旧版との比較も公開するときに `idleSheets`・`attackComparison` を指定する。
3. READMEのローカルサーバーを起動する。1×で全方向、静止→歩行→単発攻撃→再生、GIFリンク、比較解像度を確認する。公開を依頼されたらコミット・push後にmainの `/docs` のPages反映と本番画面も確認する。
4. 制作記録には、画像で確認できた特徴と推定した背面、配色・寸法の変更理由、失敗した方向と局面、改善前後の画像、実行した検証、未評価の状況を残す。権利不明の参考画像や作業フォルダがステージされていないか `git status` で確認する。

**完成条件**　別の出力先へ再生成した静止・歩行・攻撃のRGBAとメタデータが公開候補に一致し、ギャラリーとGIFで意図した動作が読める。新しい体形での調整値と残った制約を、次の制作者が再確認できる。
