# 共通エンジンの技術設計

この文書は入力と出力の契約をまとめる。制作順と反復のコマンドは [キャラクター制作ガイド](../research/CHARACTER_CREATION_GUIDE.md) にある。

## 水平断面と部位の所属

1枚の水平断面は高さZを固定したY×Xの格子。これを積み重ねた `materials.npz:slices` と `part_ids.npz:parts` は同形の3次元 `uint8` 配列で、0は空。両方の占有位置が一致し、非ゼロの材質IDはパレット順、部位IDは `rig.parts` 順でそれぞれ1から始まる。ワールド座標は +Xが本人の左、+Yが前、+Zが上。配列添字と関節座標の軸順に注意する。[読込時の検査](../spritestack/character.py)

| マニフェストの入力 | 用途 |
| --- | --- |
| `model`, `rig.parts`, `rig.rest` | 元格子の原点・間隔、陰・基・明のパレットと陰影グループ、体と装備の所属、静止時の関節と装備の目印 |
| `rig.attachments` | 装備部位を手に固定。正式3体は共通の身体15部位に右手の主装備、必要に応じて左手の副装備を加える |
| `posed_volume` | 動いた全身を収めるモデル空間の格子。境界は格子に揃える。サンプルの姿勢格子は0.5モデル単位 |
| `view`, `comparison_view` | 方向別ヨー角、仰角、画素密度、描画セルと足元基準。後者は任意の静止比較用 |
| `walk`, `attack`, `measurements` | クリップの相対パス、体形別の調整、装備を測る部位・材質。静止のみのベイクでも両クリップを読み込む |

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

攻撃は1回再生し、各列の表示時間は `durations_ms` を使う。標準セルとの差の半分を静止アンカーの各軸に加えて、同じ足元に置く。`view.render_cell` は各セル以上で差は偶数。高い装備がはみ出すときは、まず姿勢格子の3D境界と投影後のセルの2D余白のどちらで切れたかを調べる。静止の高さの見積もりでは、上方向への投影に高さ×cos(仰角)と奥行き×sin(仰角)の両方が効く。[各体の公開メタデータ](assets/)

例えば標準48 pxで、装備先端の高さを `z`、足元から見てカメラの奥へ離れる距離を `d` とすると、輪郭と上端1 pxの余白を見込む制作上の目安は `0.9135 × z + 0.4067 × d ≤ 31.5`。MAGEの右手の杖はW方向で約7単位奥にあり、高さの目安が約31.4単位まで下がる。先端の高さだけを比べるとこの制約を見落とす。別のカメラ・セルでは投影から見積もり直し、最終判定には8方向のPNGの実余白を使う。[杖の寸法と静止シート](../research/IMAGE_TO_CHARACTER_02.md)

## 歩行と頭部連動

[共通歩行](../motions/walk.json) で接地区間、遊脚の高さ、腕振り、胴の上下・左右動とひねりを定義する。`walk.tuning` は脚長・衣装・装備に合わせる倍率と左右の手の調整を持つ。元クリップの位相では同じ側の手足が前へ出るため、正式3体は腕振りの符号を調整している。[歩行の比較](../research/WALK_ANIMATION_VERIFICATION.md)

`walk.head.follow` は首の移動への左右・前後・上下の追従量（既定は全軸1）。`bob`・`surge`・`sway` は沈み・前進・左右動を足す（既定0）。`lag_frames` は既定0.25コマ。`snap` は従来の頭位置からの移動量を丸める単位（既定1.0）。`yaw_follow`・`pitch_follow`・`nod_deg`・`tilt_deg` は既定0。48 pxの目が消える場合は回転と微小移動を戻し、まず胴の `root_bob_scale` で肩と一緒に動かす。攻撃は別設定の `attack.tuning.head_snap`・`head_follow` を使う。[頭部の試作と計測](../research/HEAD_MOTION_VERIFICATION.md)

## 髪・布と細い武器

- `walk.secondary` は部位・材質と任意の `box` で領域を選ぶ。`skirt` は股関節で脚の向きに追従し、腰から裾へ重みを増やす。`pendulum` は固定した付け根から先端ほど過去の姿勢に遅れて追従する。歩行は周期的、攻撃は `attack.follow_cloth` で同じ領域を攻撃の姿勢列に適用する。毎回クリップから計算できる。布同士や装備との衝突をすべて自動解決する機能はない。[従属運動の実装](../spritestack/secondary.py)
- MARENとRONINは `walk.fine`・`attack.fine` で剣の周囲だけを1画素4×4光線で調べる。面の被覆率、刃を横切る位置で最大となる被覆率、手前の物体を考慮し、`seam: "behind"` で境界を後方の面に置く。細い刀を太くして同じ見え方にする必要はない。NEなどでは画素の段差の移動が残る。刀の自然な反りと、コマ間で不自然に曲がる見え方を区別する。[描画の比較](../research/SWORD_WALK_VERIFICATION.md) · [速斬りの計測](../research/AZURE_RONIN_QUICK_SLASH.md)

## 検証の適用範囲

静止の検証はモデルの再生成、配色の出典、装備・手の接続、可視材質、シートの再描画を検査する。歩行では接地・腕振り・部位の残存・顔・布も見る。攻撃では設定した主要局面の全8方向の可視画素、焼いた姿勢での接地・握り・余白、始終端の静止との一致を検査する。9コマの攻撃では8区間を各12分割した97姿勢でIK、装備の固定、指定した先端材質と他部位との交差を調べる。現行の攻撃検証は右主手を前提とする。[静止](../research/verify_character.py) · [歩行](../research/verify_walk.py) · [攻撃](../research/verify_attack.py)

離散PNGで合格しても全立体の連続衝突判定にはならない。MAGEでは中間姿勢で杖軸や本が胴・マント等と重なる例がある。色が似て装備が判読できない、斬撃の溜めと振り抜きが同じに見える、といった問題は原寸再生で判定する。背面の復元は制作判断であり、未知の骨格、両手で同じ武器を拘束する動作、実ゲームでの停止・旋回・ヒット感は標準手順の検証範囲外。[詠唱と補間の制約](../research/CRYSTAL_MAGE_CAST.md) · [検証器の検出範囲](../research/SHARED_IDLE_BAKE_AND_VALIDATION.md)

## 研究用の回帰

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
