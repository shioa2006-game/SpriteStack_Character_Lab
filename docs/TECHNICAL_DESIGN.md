# SpriteStack Asset Lab 技術設計

この文書は入力と出力の契約をまとめる。制作順と反復のコマンドは [キャラクター制作ガイド](../research/CHARACTER_CREATION_GUIDE.md) にある。

## 素材台帳とギャラリー

[catalog.js](catalog.js) はブラウザからそのまま読める宣言的な台帳。ビルドを挟まず `file://` でも一覧と隊列を組み立てられるよう、通常のscriptとして読み込む。`assets` に公開素材、`projects` にゲームを登録する。素材IDは全分類を通して一意とし、名前・分類を変更しても公開先のIDとURLを保つ。

| 素材項目 | 記入する内容 |
| --- | --- |
| `id, name, displayName, role, description` | 安定した英数字とアンダースコアのID、英字名、表示名、職業・特徴、紹介文 |
| `type, subtype, status` | `character / monster / object`、冒険者・NPC・人型などのサブ分類、制作状況。現行の公開素材は `published`。追加したサブ分類の日本語名は `subtypes` に登録 |
| `projects` | 採用したゲームのIDの配列。空配列は未所属。プロジェクト側の素材リストやゲーム別の画像コピーは不要 |
| `candidateProjects` | 検証済みアセットの制作候補先。プロジェクト詳細の「制作候補」と絞り込みに使用。採用時に同じIDを `projects` へ移す |
| `directory, thumbnail, directions` | docs基準の公開ディレクトリ（末尾に `/`）、その中の表紙PNG、公開方向の配列。表紙はこの順の横一列のシートを使い、SWがあればその列を切り出す。単独画像なら `thumbnailSingle: true` |
| `views` | 表示順の状態・動作。各項目に `id, label, sheet, metadata`。単一姿勢は `state: true`。確認用の `gif`・`comparison`、比較解像度の `variants`、単発終了後の遷移先 `next` は任意 |
| `source, records` | リポジトリ基準のモデル生成ファイルと、複数の `[リンク名, 制作・検証記録パス]`。HTTPからはGitHubの該当ファイルへ、直接HTMLからはローカルのファイルへリンク |
| `partyPreview` | 現行の隊列に対応する冒険者のみ、書き出した `preview.js` を指定 |

たとえば既存のトビの `views` は `[still, breathe, walkGif, partyAttack]`。各定数は台帳冒頭のファイル参照で、実際の表示時間は `attack.json` から読む。別の動作を登録する際は `{ id: "fly", label: "飛行", sheet: "fly.png", metadata: "fly.json" }` のように、書き出したファイルに合わせて追記する。新しいモーション名をボタンやプレイヤーの分岐に加える必要はない。

**状態と再生**　静止状態はJSONの `neutral.cell / anchor / directions` を読み、方向を列として切り出す。閉じた状態と開いた状態は別々の `state: true` として、各状態のPNG・JSONを指定できる。動作は `animations[view.id]` を読み、`rows` が方向、`columns` が時間。各コマは `durations_ms`、等間隔なら `fps` に従う。方向ボタンは選んだ状態のJSONから作る。1・4・8方向に対応し、各状態の方向集合は異なってもよい。

個別ビューアでは、台帳で `previewLoop: true` を指定した攻撃を選ぶと連続再生する。「単発再生」を押すと先頭から1回再生し、`next` があれば指定の状態へ移り、省略時は最終コマを保持する。ゲーム用JSONは攻撃を `loop: false` として扱う。

**原寸と接地**　共通ビューアは各シートのアンカーから四辺までの最大距離で表示領域を決める。倍率1では出力1 pxをCSSの1 pxにし、拡大は整数倍で補間を切る。オブジェクトの床面表示ではアンカーを十字で示し、32 px間隔の比較格子を重ねる。格子は画像上の寸法比較用。ゲーム内のタイル投影・物理寸法の校正は個々の制作実験で記録する。

**プロジェクト**　`projects` の各項目は `id, name, description, repository` と任意の `party`。詳細は `projects.html?id=<id>` で、同じページが全プロジェクトの冒険者・NPC・モンスター・オブジェクトを集計する。トップには台帳の先頭のプロジェクトを展示する。GUILDWARDの隊列は従来の `party.html`。追加のゲームで同形式の隊列を使う場合は `party.html?id=<id>` を登録する。

**隊列専用の条件**　ゲーム所属の冒険者のうち `partyPreview` のある素材を台帳順に表示する。現行の隊列は共通8方向の待機・歩行・攻撃、歩幅、接地情報、カメラを使う。PNGとモーションJSONと同じベイクから [export_loops](../research/export_loops.py) で `preview.js` を生成する。ここにカメラ・再生値の抜粋と歩行終了時の補正が入る。直接HTMLで再生するときもこの生成物を読み込む。更新時はJSON・PNG・previewを同時に照合する。

**検査**　`node research/verify_catalog.cjs` は素材・プロジェクトIDと参照、方向、PNGの寸法、コマ数・再生時間、比較解像度、モデルと記録ファイルの存在を検査する。追加後は該当ページをHTTPで開き、画像カード、方向・コマ・速度、単発からの復帰、原寸の接地、ファイルリンクを確認する。分類とプロジェクトの両方から同じ詳細に到達できることも確かめる。

## 非人型とオブジェクトの制作方針

制作入力は体形ごと、公開出力はシート・アンカー・方向・時間の契約で共用する。人型モンスターは体格と装備が合えば既存リグを利用できる。四足・飛行・伸縮する素材は最初の作例で支持点、姿勢、移動方法を決める。既存の格子、材質、カメラ投影、画像の切り出しを適用できる範囲で共用し、専用の動きや検証は実測から切り分ける。

家具・建物・仕掛けは、対称形や分割モジュールも含め全状態・全動作で8方向を制作する。カメラの行順は S / SW / W / NW / N / NE / E / SE。物体ローカルの正面を+Y、転倒・転動の進行を `travel_xyz`、右手系の回転軸を `axis_xyz` とする。ワールドでカメラを `c`、物体を `h` だけ初期向きから+Z軸周りに回した時、使う行のカメラヨーは `(c-h) mod 360`。ゲームの方角の名称とは別にこの差を計算する。

剛体の造形は `objects/<id>/` に置く。`objects.bake` が各部位を支点周りに回転し、必要な範囲を格子単位で確保し、共通の `reslice / normals / Renderer` で各ヨーを独立に投影する。転動時は回転済みの各ボクセル中心の最低Zから、回転後の立方体の鉛直半径を引いて床までの移動量を得る。回転後に平行移動を加え、全行で同じ接地補正を使う。足元ピクセルのアンカーは固定する。格子境界上の光線には一定の微小偏差（1e−7 px）を加え、部材の置き場所による丸め方向の逆転を防ぐ。

公開JSONは各ビューに `geometry / placement / camera_yaw_deg` と、必要に応じて `rotation / module` を持つ。角度・占有外端・転動時の接地補正は `neutral` または `animations[id]` にコマ順で保存する。単発は台帳の `next` から終端状態へ移る。同じ部材の支持面と個別アンカーを保てば、落ちた石柱をセル単位の橋に置き換えられる。プロジェクトの任意の `objectPreview` は比較画面の入口。[オブジェクト制作ガイド](../objects/README.md) · [寸法換算と検証](../research/objects01/README.md) · [非人型モンスター](../monsters/README.md)

## 水平断面と部位の所属

1枚の水平断面は高さZを固定したY×Xの格子。これを積み重ねた `materials.npz:slices` と `part_ids.npz:parts` は同形の3次元 `uint8` 配列で、0は空。両方の占有位置が一致し、非ゼロの材質IDはパレット順、部位IDは `rig.parts` 順でそれぞれ1から始まる。ワールド座標は +Xが本人の左、+Yが前、+Zが上。配列添字と関節座標の軸順に注意する。[読込時の検査](../spritestack/character.py)

| マニフェストの入力 | 用途 |
| --- | --- |
| `model`, `rig.parts`, `rig.rest` | 元格子の原点・間隔、陰・基・明のパレットと陰影グループ、体と装備の所属、静止時の関節と装備の目印 |
| `rig.attachments` | 装備部位ごとに手とマーカーを対応づけ、手首の剛体変換で握りと先端を動かす。本人基準の左右を全方向で共有する |
| `posed_volume` | 動いた全身を収めるモデル空間の格子。境界は格子に揃える。サンプルの姿勢格子は0.5モデル単位 |
| `view`, `comparison_view` | 方向別ヨー角、仰角、画素密度、描画セルと足元基準。後者は任意の静止比較用 |
| `walk`, `breathe`, `attack`, `measurements` | 共通の歩行と任意の呼吸・攻撃。設定したクリップを読み込み、装備の可視材質と最低高さを計測する。体形別の歩行速度は任意の `walk.fps` で指定できる |

## リグからPNGまで

骨盤・胸・頭と左右の四肢の静止姿勢を基準に、腕・脚は2関節IKで解く。手・足首の目標に対し、肘と膝の曲がる方向をポールで指定する。手首の向きから装備の変換が決まる。各部位を姿勢格子へ逆サンプリングし、重なりは部位順の後方が優先される。正投影では視線上の手前の面が見える。**格子での部位の上書きと、カメラからの遮蔽は別の現象**で、前者は部位ID、後者は全身と部位単独の描画を比較して調べる。[リグ](../spritestack/rig.py) · [再スライスと描画](../spritestack/render.py) · [ベイク](../spritestack/bake.py)

正式3体の仰角は24°、標準の画素密度は1.19 px/モデル単位。全方向の順は **S、SW、W、NW、N、NE、E、SE**。静止は方向が列、モーションは方向が行・時間が列。下表は公開済みの値。新しい攻撃では装備の軌道に合わせてセルと時間を選び、実際のメタデータを再生側で読む。

| サンプルとモーション | セルと足元アンカー (x, y) | 時間・配置 |
| --- | --- | --- |
| 3体の静止／歩行 | 48×48、(24, 40) | 静止は横8枚。歩行は各方向6コマ、9 fpsでループ |
| MAGE・RONINの比較用静止 | 64×64、(32, 53) | 同一モデルを4/3倍の画素密度で再投影 |
| MARENの攻撃 | 72×72、(36, 52) | 9コマ、800 ms |
| CRYSTAL MAGEの攻撃 | 64×64、(32, 48) | 9コマ、1,000 ms |
| AZURE RONINの攻撃 | 64×64、(32, 48) | 9コマ、520 ms |
| GARD・RICO・SENAの静止／呼吸／歩行 | 64×64、(32, 57) | 静止は横8枚。呼吸4コマ、歩行6コマ |
| GARD／RICO／SENAの攻撃 | 順に100×100 (50, 75)／80×80 (40, 65)／100×100 (50, 75) | 各9コマ、順に960／590／1,000 ms |

攻撃は `loop: false`、各列の表示時間は `durations_ms`。静止アンカーの各軸に（攻撃セル − 静止セル）/ 2 を加える。床座標から各モードのアンカーを引いて描く。静止・歩行・呼吸の各セルは `view.render_cell` 以下で差は偶数。攻撃セルは静止セル以上で、通常の描画セルを超えられる。攻撃時には両者の大きい側で描画して切り出す。[入力寸法の検査](../spritestack/character.py) · [各体の公開メタデータ](assets/)

格子には三段階ある。元のNPZは静止モデルの材質と所属、`posed_volume` は通常の姿勢を再サンプリングする領域、任意の `attack.posed_volume` は攻撃時だけ使う原点・境界・格子間隔を持つ。作業用の姿勢NPZを読む際もモードごとの格子を使う。これらはモデル単位で、出力セルと足元アンカーは画素単位。武器が切れたらまず姿勢格子で欠けているか、投影後のセル端なのかを確認する。

例えば標準48 pxで、装備先端の高さを `z`、足元から見てカメラの奥へ離れる距離を `d` とすると、輪郭と上端1 pxの余白を見込む制作上の目安は `0.9135 × z + 0.4067 × d ≤ 31.5`。MAGEの右手の杖はW方向で約7単位奥にあり、高さの目安が約31.4単位まで下がる。先端の高さだけを比べるとこの制約を見落とす。別のカメラ・セルでは投影から見積もり直し、最終判定には8方向のPNGの実余白を使う。[杖の寸法と静止シート](../research/IMAGE_TO_CHARACTER_02.md)

## 歩行と頭部連動

[共通歩行](../motions/walk.json) で接地区間、遊脚の高さ、腕振り、胴の上下・左右動とひねりを定義する。`walk.tuning` は脚長・衣装・装備に合わせる倍率と左右の手の調整を持つ。元クリップの位相では同じ側の手足が前へ出るため、正式3体は腕振りの符号を調整している。[歩行の比較](../research/WALK_ANIMATION_VERIFICATION.md)

`walk.head.follow` は首の移動への左右・前後・上下の追従量（既定は全軸1）。`bob`・`surge`・`sway` は沈み・前進・左右動を足す（既定0）。`lag_frames` は既定0.25コマ。`snap` は従来の頭位置からの移動量を丸める単位（既定1.0）。`yaw_follow`・`pitch_follow`・`nod_deg`・`tilt_deg` は既定0。48 pxの目が消える場合は回転と微小移動を戻し、まず胴の `root_bob_scale` で肩と一緒に動かす。攻撃は別設定の `attack.tuning.head_snap`・`head_follow` を使う。[頭部の試作と計測](../research/HEAD_MOTION_VERIFICATION.md)

## 髪・布と細い武器

- `walk.secondary` は部位・材質と任意の `box` で領域を選ぶ。`skirt` は股関節で脚の向きに追従し、腰から裾へ重みを増やす。`pendulum` は固定した付け根から先端ほど過去の姿勢に遅れて追従する。歩行は周期的、攻撃は `attack.follow_cloth` で同じ領域を攻撃の姿勢列に適用する。毎回クリップから計算できる。布同士や装備との衝突をすべて自動解決する機能はない。[従属運動の実装](../spritestack/secondary.py)
- MARENとRONINは `walk.fine`・`attack.fine` で剣の周囲だけを1画素4×4光線で調べる。面の被覆率、刃を横切る位置で最大となる被覆率、手前の物体を考慮し、`seam: "behind"` で境界を後方の面に置く。細い刀を太くして同じ見え方にする必要はない。NEなどでは画素の段差の移動が残る。刀の自然な反りと、コマ間で不自然に曲がる見え方を区別する。[描画の比較](../research/SWORD_WALK_VERIFICATION.md) · [速斬りの計測](../research/AZURE_RONIN_QUICK_SLASH.md)

## 攻撃装備とイベント

手持ちの投擲物では、クリップのイベントに `released_part`、対応する取り付けの `marker`、0始まりの `rearm_frame` を指定する。手首上のマーカーが発動位置となる。`preview_distance` が正なら、発動の1コマだけ同じ部位・材質を射出方向へそのモデル単位数だけ移して再スライスする。0または省略なら発動時からゲーム側へ渡す。以後は再装備コマの直前までその部位を格子に置かず、再装備時に再び手首に従わせる。イベントの `baked_projectile_frames` がスプライト側で描くコマ数を示す。[トビのクリップ](../characters/tobi/bomb-throw.json)

| 入力 | 動作と確認できる実装 |
| --- | --- |
| `attack.tuning.main_hand_side` | `R` または `L`。対応する `hand_R/L` の絶対目標、同側の肘ポール、静止時の `weapon_axis` から `blade` または `aim` へ手首を回す。副手は `shield_delta` または `support_delta` と胴の移動で解く。装備の親は `rig.attachments` で指定。[リグ](../spritestack/rig.py) |
| `attack.bow` | 弓枠の部位と両端、弦・矢の寸法と材質を指定。ポーズ中は元の弦を取り除いた作業格子に弦を描く。`nocked` キーでは矢筈を副手へ置き、`flight_offset` で直前の矢軸上へ離す。空キーは静止の弓を復元。矢があるコマだけ `arrow_nock`・`arrow_tip` が存在する。[弓生成](../spritestack/bow.py) · [弓の設定](../characters/rico/character.json) |
| `attack.glow_materials`、`attack.burst` | `glow` は指定材質（任意の `glow_part`）の可視画素を着色し、`glint` は光点を加える。`burst` キーでは指定マーカーと `aim` から短い結晶片を立体格子に生成する。表示用の矢・氷片のIDは攻撃メタデータの `transient_parts` に入る。[発光処理](../spritestack/bake.py) · [結晶片](../spritestack/effects.py) |

クリップの任意の `events[]` に `name`、0始まりの `frame`、関節または装備の `marker` を指定する。ベイクは該当コマ以前の表示時間の和を `time_ms`、その姿勢のマーカー位置を `position_model_xyz` として `metadata.json → animations.attack.events` に記録する。公開用の `attack.json` に同じレイアウトが入る。各向きのPNG行名は `rows`、局面名は `phase_names`、時間列は `durations_ms` を読む。

| 作例 | `direction_model_xyz` の意味 | 描画・再生時の扱い |
| --- | --- | --- |
| GARD `hammer_impact` | `direction_source: "marker_travel"` で直前コマから現在の槌頭までの変位を正規化 | 先行コマと非ゼロ変位が必要。打点での離散変位が向きを表す |
| RICO `arrow_release` | 矢を持つ姿勢では矢筈→矢先の軸 | F6の360 msで通知。表示済みの飛翔像は `baked_projectile_frames: 1`、ゲームが矢の描画を引き継ぐ境界は400 ms |
| SENA `ice_release` | 上記以外では発動キーの `aim` | F6の580 ms、水晶先端から杖軸へ放出。目標への追尾や命中はゲーム側で扱う |
| TOBI `bomb_release` | `marker_travel` で離手直前の玉の中心の変位を正規化 | F6の470 msで通知。F6は離れた玉を1個描画し、530 msからゲーム側が描画を引き継ぐ。F9で腰袋の次弾を右手に装着 |

`direction_by_row` は単位方向を行のヨー角だけXY面で回した3次元ベクトル。発動位置は正面モデル空間に一つ記録される。ゲームの床・画面に描くときは位置にも同じ回転を適用し、所定の投影と足元アンカーを使う。時刻・ポーズを照合した作例と飛翔像の描画境界は [冒険者のイベント](../research/adventurers/ATTACKS.md) を参照。

## 検証の適用範囲

静止の検証はモデルの再生成、配色の出典、装備・手の接続、可視材質、シートの再描画を検査する。歩行では接地・腕振り・部位の残存・顔・布も見る。攻撃では設定した主要局面の全8方向の可視画素、焼いた姿勢での接地・握り・余白、始終端の静止との一致を検査する。9コマの攻撃では8区間を各12分割した97姿勢でIK、装備の固定、指定した先端材質と他部位との交差を調べる。攻撃の握りと補間姿勢は `attack.tuning.main_hand_side` で主手を決め、反対の手のIKも検証する。[静止](../research/verify_character.py) · [歩行](../research/verify_walk.py) · [攻撃](../research/verify_attack.py)

離散PNGで合格しても全立体の連続衝突判定にはならない。MAGEでは中間姿勢で杖軸や本が胴・マント等と重なる例がある。色が似て装備が判読できない、斬撃の溜めと振り抜きが同じに見える、といった問題は原寸再生で判定する。背面の復元は制作判断であり、未知の骨格、両手で同じ武器を拘束する動作、実ゲームでの停止・旋回・ヒット感は標準手順の検証範囲外。[詠唱と補間の制約](../research/CRYSTAL_MAGE_CAST.md) · [検証器の検出範囲](../research/SHARED_IDLE_BAKE_AND_VALIDATION.md)

静止検査の `quality.items.main/off` は歴史的に右／左の役名で、攻撃の主手を決める設定は独立している。呼吸付きの全ベイクには `verify_loops` を使い、足の固定・顔や装備の可視条件・公開ループを確認する。攻撃検証はイベントの時刻・座標・方向、設定された一時部位の有無も照合する。記録済みの3D点と原寸画像を同じ局面で調べるには [モーション比較ツール](../research/attack/README.md) を使う。

## 研究用の回帰

冒険者4体では静止8方向を `idle.png`、ループ待機を `breathe.png` に出力する。呼吸は腰を基準に胸・頭・腕・手装備へ同じ上下移動と小さな傾きを適用し、骨盤・脚・ブーツは静止位置に固定する。トビの `breathe.secondary` はバンダナの端と腰布の裾を指定し、呼吸に遅れて揺らす。呼吸がゼロのキーには元の静止格子とレイ条件を使う。通常ベイクはマニフェストが持つ全モーションを処理する。[ゲームへの取り込みと検証](../research/adventurers/README.md)

共通エンジン変更時は [正式3体の回帰](../research/SAMPLE_CLEANUP.md) に加え、次をルートから実行する。以下はREADMEの仮想環境を使用する。

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$run = Join-Path $PWD ('.phase1/regression-' + [guid]::NewGuid())
& $python -m spritestack --character experiments/lark/character.json --out "$run/lark"
& $python research/verify_rebuild.py "$run/lark"
& $python -m spritestack --character experiments/bram/character.json --out "$run/bram"
& $python -m research.verify_bram "$run/bram"
```

BRAMの局所ウェイトは関節品質を比較する試作。剛体版と比較する場合は同じ `$run` を使う。

```powershell
& $python -m research.phase4.run --out "$run/weighted"
& $python -m research.phase4.compare --rigid "$run/bram" --weighted "$run/weighted" --out "$run/compare"
```

LARKの旧同梱テストは元パッケージを作業用に複写して実行する。[初期パッケージの検証記録](../research/PHASE1_VERIFICATION.md) · [BRAMの比較結果](../research/PHASE4_VERIFICATION.md)
