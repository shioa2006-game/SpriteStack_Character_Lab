# 実験07　SKELETON GUARD ― 錆剣の骸骨衛兵

人間用の二足歩行リグで、骨だけの戦士を静止・歩行・攻撃の全8方向に生成した。頭身は人間剣士に近く、胸郭と骨盤の間を細い背骨だけでつなぐ。正面の肋骨を識別するには、骨の可視画素に加え、輪郭を引いた後も背景が透ける幅が必要だった。[ギャラリーで SKELETON GUARD を選択](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

| モード | 透過PNG・足元アンカー | 再生・比較 |
| --- | --- | --- |
| 静止 | [48×48、横8枚](../docs/assets/skeleton_guard/idle.png)・(24, 40) | [FLEUR KNIGHT・GOBLIN BRUTE・初版・完成版の原寸比較](image_to_character_07/idle-comparison.png) |
| 歩行 | [48×48、8行×6列](../docs/assets/skeleton_guard/walk.png)・(24, 40) | [9 fpsの歩行](../docs/assets/skeleton_guard/walk.gif)・[上段が初版、下段が完成版](image_to_character_07/walk-comparison.gif) |
| 攻撃 | [72×72、8行×9列](../docs/assets/skeleton_guard/attack.png)・(36, 52) | [840 msの単発攻撃のプレビュー](../docs/assets/skeleton_guard/attack.gif)・[初版と完成版の同時再生](../docs/assets/skeleton_guard/cleave-comparison.gif) |

## 画像から動作へ

1. **骨の目印を選ぶ。** 原画は556×738 px。頭頂・顎・足底がそれぞれ y=8、91、716で8.53頭身。大きな黒い眼窩と小さい下顎、胸郭と骨盤を隔てる腰椎、細い四肢と対照的な丸盾を残した。正面から見て左の錆びた肩当てと剣が本人の右。背後は推定し、背骨の突起、革を張った盾裏、ベルトの後ろから垂れる短い裾を作った。[採寸点・採色矩形](../characters/skeleton_guard/reference_regions.json)
2. **原寸用に寸法と色を決める。** 造形は足底から頭頂まで約32単位、頭蓋骨の上下約8.2単位で約3.9頭身。9系統を採色し、歯と暗赤の布には抽出色を使用した。眼の赤は原画の微光を明るくし、盾は灰色に寄った原画の地色から青みを増した。骨の陰は温かい灰褐色、眼窩は暗褐色、剣は灰青の地に赤錆と明るい刃縁を置いた。[抽出色](../characters/skeleton_guard/reference_palette.json)・[18材質の出典と調整](../characters/skeleton_guard/palette_provenance.json)
3. **一体の立体とリグを作る。** 頭蓋から眼窩をえぐり、奥に赤い点を置いた。胸郭は中空の湾曲した骨、背骨は小さな椎骨の連なり、骨盤は左右に穴を持つ腸骨と中央の仙骨で作った。大腿・すね・上腕・前腕には細い骨幹と太い関節端を使った。右肩当ては上腕、斜め革帯は胸、剣と盾は各手につながる独立部位。0.5単位格子の単一モデルを17部位で動かす。[モデル生成コード](../characters/skeleton_guard/build_model.py)・[リグと材質](../characters/skeleton_guard/character.json)
4. **静止を原寸で見る。** 初版の正面には肋骨の材質が41 pxあったが、三段の骨と輪郭が一枚につながった。上部と下部の大きな弧に整理し、鎖骨と胸骨を残した。盾の表面は浅く膨らませ、左手より少し高く外側に置いた。S・SWでは左右の赤い眼、Eでは頬と前に出る顎、Nでは頭蓋の丸い背面と背骨で向きが読める。[原寸比較](image_to_character_07/idle-comparison.png)
5. **歩幅と腕の位相を決める。** 共通6コマを9 fpsで使い、歩幅を0.89倍、胴の捻りを0.46倍にした。荷重時に頭が一段下がって戻る。細い脚が交差する横向きでも、膝のふくらみと足先が別々に動く。左手の振幅を抑えて盾を胸の横に保ち、反対側の足に合わせて剣の手を振る。[共通クリップ](../motions/walk.json)・[歩行GIF](../docs/assets/skeleton_guard/walk.gif)
6. **頭部・布・装備を追従させる。** 首への追従を1単位刻みにし、荷重で頭頂が1 px動いても眼窩の中の赤い画素が欠けないようにした。暗赤の裂け布は腰に固定した上端から裾に向けて左右の大腿の回転を受ける。盾と剣は固い単一部位で、剣には共通の細部描画を適用した。輪郭や装備を方向別に描き足す工程はない。[歩行設定](../characters/skeleton_guard/character.json)
7. **専用の斬撃を作る。** 構えから肘をほどき、肩を後ろへ捻る。4コマ目は剣を頭上で190 ms止め、5コマ目は40 msで振り下ろす。右足に踏み込み、6コマ目で切っ先と腰を低く止める。短い反動を挟み、8〜9コマ目で構えへ戻る。左の盾は胸の高さの近くを保つ。72 pxセルには静止と同じ縮尺で剣の上方の軌道を収めた。[9キーの専用クリップ](../characters/skeleton_guard/cleave.json)・[主要4局面](../docs/assets/skeleton_guard/cleave-poses.png)
8. **同じ方向・経過時間で比較する。** 比較GIFは初版と完成版に同じコマ時間を使う。技術検査とは別に、原寸の表示で肋骨の帯、盾に隠れる腕と剣、頭上の停止と斬撃直後の切っ先を見た。比較用に残した初版も同じ共通エンジンで焼いた。[初版の攻撃とレイアウト](image_to_character_07/baseline/)・[同期再生](../docs/assets/skeleton_guard/cleave-comparison.gif)
9. **ギャラリーで再生する。** 静止のメタデータ、歩行・攻撃それぞれのレイアウトとPNGを登録した。原寸・速度1×のChromeで8方向を切り替え、再生中のキャンバス全128セルをシートの対応セルと照合する。攻撃の再生ボタンと2つのGIFリンクも検査対象とした。[公開素材](../docs/assets/skeleton_guard/)・[検証結果](image_to_character_07/results.json)

## 初版からの修正

初版の後、モデルまたはクリップを変えて静止・歩行・攻撃のベイクを評価した改訂は **5回**。同じ版の中で角度・形状を比較した試し描きはこの数に含めていない。

| 改訂 | 原寸・補間で見つけた問題 | 修正と再検証 |
| --- | --- | --- |
| 1 | 初版は静止FAIL 0でも正面の胸郭が白い胸当てに見えた。NWの攻撃5〜7コマ目では刀身が0 px。骨盤に両大腿の小片が埋まった | 肋骨を二段に広げ、隠れる大腿上端を整理。正面に透明2 pxを確保したが、剣を前に倒すと静止NWの刀身が隠れ、歩行SWの1コマ目が余白検査で停止した |
| 2 | 剣先・盾・脚が同じ投影位置に集まった。頭蓋の左右の眼窩もつながって見えた | 構えの剣先を外・下へ、盾を少し上へ動かし、鼻梁を造形。静止と歩行がFAIL 0、刀身は歩行全体で5 px以上。攻撃の中間姿勢で刀身が頭部に触れた |
| 3 | 振り下ろしはキー間で頭を横切り、単体表示では鍔の付近に刀身の1〜2 pxが離れて出た | 振りかぶる拳を前へ移動し、鍔を短く、刃元と刃の厚みを調整。剣の97姿勢と単体刃の128セルが合格。胸郭の上側を広げた結果、右上腕が短い補助肋骨に最大6ボクセル中心分入り込んだ |
| 4 | 肩を捻ったときだけ右腕の下に補助肋骨が当たった | 上部の短い補助肋骨を除き、左右の主な弧と鎖骨を残した。歩行6・攻撃97姿勢で胸郭と腕の重なりが0。正面では斬撃の刃縁が盾と胸の色に紛れた |
| 5 | 刃の可視画素が足りても、正面からは剣が胸の中で動いているように見えた | 剣を持つ側の空間へ刃を出し、頭上の停止から水平に近い斬撃、膝の下へ向かう切っ先までを輪郭で追えるようにした。振り出しと反動の角度も調整し、全方向と補間を再検査した |

## 技術検証

完成版は静止35項目・歩行16項目がすべてPASS（WARNING・FAIL・SKIP各0）。攻撃の汎用検査と骨格・装備の追加検査も合格した。独立した出力先から再ベイクした全128セルの復号RGBA、各レイアウト、攻撃GIFの全9コマの画素と表示時間が公開候補に一致した。ローカルのギャラリーでは原寸・通常速度で128セルの表示、再生ボタン、攻撃と比較のGIFリンクを確認した。

| 対象 | 結果 |
| --- | --- |
| 静止 | 18材質・17部位が接続。ビルダーから2つのNPZ配列が一致。8方向すべて余白4 px以上。S・SW・SEで眼の赤が各2 px。正面の肋骨は盾あり37 px、盾なし38 px。上下の骨に挟まれる空の投射線は13→28、輪郭処理後の透明画素は0→2 |
| 歩行 | 左右の支持足の滑りは0、足裏アンカーとの差は最大1 px。全48セルで刀身6 px、盾29 px、肋骨18 px以上。剣・盾と手の接触面は最小7・21。各方向の眼の面積は6コマを通して一定。裾の他部位への重なりは腰に固定した対照7.88%から大腿追従後5.84%に減少 |
| 攻撃 | 共通検査で72セルの余白、端の静止との一致、支持足、両手への装備固定、97補間姿勢の刃と全身の交差を検査。両手の接触面は剣5・盾19以上。全方向で溜め25 px、斬撃18 px、低い停止9 px以上の刀身が見えた。切っ先の高さは頭上36.82から低い停止5.69へ、同区間の盾中心は19.28から17.88へ移動 |
| 骨と装備の追加検査 | 歩行6・攻撃97姿勢で胸郭と腕・装備の中心点の交差0。盾と持ち手以外の交差0。歩行6・攻撃9キーで布と武器・前腕・手の交差0。遮蔽前の鋼の刃は静止8・歩行48・攻撃72の全セルで8近傍の一続き |
| 公開済み6体 | MAREN、CRYSTAL MAGE、AZURE RONIN、FLEUR KNIGHT、CRIMSON BLADE、GOBLIN BRUTEを再生成。通常サイズ計768セルと、MAGE・RONINの静止64 px計16セルを公開PNGの復号RGBA・レイアウトと照合。既存の攻撃GIF計54コマの復号結果・表示時間も比較した |

既存体の既知WARNINGは、MAREN・CRYSTAL MAGEの静止に各1件（部位所有の細片）、CRYSTAL MAGEの歩行に1件（斜め前の眼の面積変化）。初期試作では公開候補がなく静止1件・歩行2件の照合をスキップした。LARK・BRAMの旧パッケージは共通コードの変更時に行う回帰の対象で、今回は再生成していない。[品質条件](../characters/skeleton_guard/quality.json)・[モーションの追加検査](image_to_character_07/inspect_motion.py)・[全方向の実測値と回帰ハッシュ](image_to_character_07/results.json)

## 原寸での見え方

- S・SW・SEでは眼窩の赤、顎、肋骨の弧、骨盤、赤い裾が上から順に読める。Sの6コマ間では頭が一段ずつ沈み、盾に比べて剣の手が大きく動く。正面の攻撃5コマ目では刃が盾と反対側へ張り出し、次のコマで足元へ落ちる。
- N・NE・NWでは丸い後頭部の下に露出した椎骨が続く。初版のNWは攻撃5・6・7コマ目すべてで刃が消えた。完成版では同じ位置で29・9・18 px。低い停止は一部が胴に隠れるが、振り抜いた向きを切っ先から追える。
- E・Wでは張り出した頬と顎、細いすねの形が手掛かりになる。盾側のWでは丸盾が前腕と胸の一部を隠し、刀身も奥行き方向に短く見える。48 pxでは腸骨の左右の穴や一本ずつの歯を全方向で識別するのは難しく、骨盤は腰椎の両側に開く明るい輪郭として読む。[原寸静止比較](image_to_character_07/idle-comparison.png)・[原寸攻撃比較](../docs/assets/skeleton_guard/cleave-comparison.gif)

## 再利用と次の制作への提案

ガイドの9工程で、採色、部位IDと左右、二足IK、布の追従、PNGベイク、比較GIF、ギャラリー登録まで進められた。FLEUR KNIGHTから剣と盾の所有・盾の干渉検査、MARENから振りかぶりと踏み込みの評価、CRIMSON BLADEから細い刃の画素接続検査、GOBLIN BRUTEから再スライス前に部位中心を調べる方法を再利用した。共通エンジン、共通歩行、既存体の設定や素材への変更はない。

FLEUR KNIGHTの胸当てとGOBLIN BRUTEの大きな頭・低い腰に対し、今回は肋骨の間の背景、狭い腰椎、両側へ張る骨盤、長骨と関節端の太さの差が種別を示す。背面では左右の装備色に加え、肩の間から腰へ続く椎骨が目印になった。次の骨・枝・格子構造のキャラクターでも、早い段階で「輪郭後にも穴が残るか」「装備を外すと読める骨が何画素戻るか」を対にして測ると、視認性の問題を切り分けやすい。三次元の穴の数は、原寸で見える穴の数と一致しない。

## 再現

リポジトリのWindows用仮想環境を使用する。座標、抽出色、生成モデルと比較画像を収録した。参考原画はローカルで保管する。

```powershell
$python = '.\.venv\Scripts\python.exe'
$char = 'characters/skeleton_guard'
$config = "$char/character.json"
$pub = 'docs/assets/skeleton_guard'
$run = Join-Path $PWD ('.phase1/skeleton-' + [guid]::NewGuid())
& $python -W error::RuntimeWarning -m characters.skeleton_guard.build_model --out "$run/model"
& $python -m spritestack --character $config --modes idle --out "$run/idle"
& $python -m research.verify_character --character $config --out "$run/idle"
& $python -m spritestack --character $config --out "$run/all"
& $python -m research.verify_walk --character $config --out "$run/all"
& $python -m research.verify_attack --character $config --out "$run/all" --gif "$run/all/attack.gif" --published $pub
& $python -m research.image_to_character_07.inspect_motion --character $config --bake "$run/all" --out "$run/inspection.json"
& $python -m research.maren_slash.compare --before research/image_to_character_07/baseline --after $pub --out "$run/comparison" --prefix cleave --phases hitch 'locked high' cleave 'low stop' --directions S SW W NW N NE E SE
```

原画を所持している場合は、ローカルのパスを `$reference` に指定して採色を再現できる。

```powershell
& $python -m characters.maren.extract_reference --image $reference --regions "$char/reference_regions.json" --out "$run/reference_palette.json"
```
