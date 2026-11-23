# 実験05　CRIMSON BLADE ― 紅装の刀剣士

参考画像1枚から、金の留め具で黒髪を高く束ね、赤い上衣と袴に濃紺の小札を重ねた剣士を制作した。静止では両足を腰幅ほどに置く。攻撃で初めて右足を大きく開き、右腰の外に引いた刀を斜め上へ抜く。1つの16部位の立体から全128コマを生成した。[ギャラリーで CRIMSON BLADE を選択](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

| モード | 透過PNGと配置 | 再生・比較 |
| --- | --- | --- |
| 静止 | [48×48、8方向横並び](../docs/assets/crimson_blade/idle.png)・足元 (24, 40) | [初版／完成版の原寸比較](image_to_character_05/idle-comparison.png) |
| 歩行 | [48×48、8行×6列](../docs/assets/crimson_blade/walk.png)・足元 (24, 40) | [8方向の原寸GIF](../docs/assets/crimson_blade/walk.gif)・9 fpsループ |
| 攻撃 | [72×72、8行×9列](../docs/assets/crimson_blade/attack.png)・足元 (36, 52) | [攻撃GIF](../docs/assets/crimson_blade/attack.gif)・[初版との原寸同時再生](../docs/assets/crimson_blade/slash-comparison.gif)・[主要4局面の比較図](../docs/assets/crimson_blade/slash-poses.png) |

## 画像から造形へ（工程1〜4）

1. **残す輪郭を決めた。** 1184×880の原画で、髪留めは (648, 120)、鍔は (582, 317)、刀先は (838, 195)、帯の結び目は (692, 445)。高く束ねて分かれる毛先、赤い上下の間に挟まる紺と金、脛まで伸びる青白の布を優先した。横に広い元絵の足幅は攻撃の着地に移した。背中の赤い合わせ、後ろへ流れる布の裏、鞘の留め方は単一視点からの補完である。[顔・関節・装備の採寸点](../characters/crimson_blade/reference_regions.json)
2. **9系統を採色した。** はじめは刺繍を拾い、青い布の中間色が茶色に寄った。地の見える小矩形へ取り直すと布地は `#6a6a84`、白布は `#ebd4ca`、金は `#cca88c` になった。原寸では赤地の中間色を `#c9726c` から `#b4404c` へ、紺鎧を `#5b545a` から `#394567` へ寄せた。青布には鎧より明るい `#5f78a1` を使った。19材質のうち2材質は革の抽出値を採用し、17材質は陰影を調整した。[抽出値](../characters/crimson_blade/reference_palette.json)・[各材質の採用理由](../characters/crimson_blade/palette_provenance.json)
3. **髪・鎧・布・刀を立体にした。** 頬に細い後れ毛を残し、斜めの前髪の下に眉と目を置いた。結び目から一度持ち上げた髪を二房に分け、背面の黒い面に短い房と長い房の段差を作った。紺の肩当て・手甲・脚甲には金の縁を載せ、左肩には原画の明るい装飾を一面だけ残した。腰には幅と折り目を変えた2枚の帯布を付けた。左腰の鞘は骨盤と一緒に回り、右手の鍔・柄・銀の反り刃は右手首と一緒に回る。[モデル生成コード](../characters/crimson_blade/build_model.py)・[関節、材質、揺れの設定](../characters/crimson_blade/character.json)
4. **静止の8方向を原寸で比較した。** Sでは顔・赤い胴・白縁の青布が縦に並ぶ。SEでは布が脚の外へ離れ、刀身と両方が見える。WとEでは鞘の金の石突と、反対の手から伸びる銀の刀身が違う明度で読める。NW・Nでは長短の毛先が肩の外で分かれ、NEでは髪が留め具を隠す。SWでは髪が奥行き方向に縮むので、頭頂より高い束と金の留め具が髪型の目印になる。[原寸比較](image_to_character_05/idle-comparison.png)

## 動きと公開（工程5〜9）

5. **歩幅と腕を合わせた。** 共通6コマの支持足を使い、歩幅倍率1.26、遊脚の持ち上げ倍率1.16、利き手側の腕振りを小さくした。S・Nでは左右の支持が入れ替わり、W・Eでは遊脚と逆側の腕が前に出る。歩行中は刀をやや下げ、背面斜めでも切先が体から出る角度を選んだ。[共通歩行クリップ](../motions/walk.json)・[歩行GIF](../docs/assets/crimson_blade/walk.gif)
6. **頭と布に異なる遅れを付けた。** 目は首の移動に追従させ、1単位刻みで安定させた。後頭部の長い束は胸の動きを1.05コマ遅れて追う。前の青白布は同じ側の脚に沿い、後ろの帯は骨盤から0.85コマ遅れて動く。顔の向き、肩当て、鞘、腰の結び目にはこの揺れをかけていない。NEで左脚を持ち上げる局面も確認し、脚から前布が浮く余裕を設けた。
7. **低い溜めから斜め上へ抜く9キーを新規に作った。** 4コマ目で胸を44°ひねり、腰の外に引いた刀を160 ms見せる。5コマ目は右足を前5.9、外4.65モデル単位に置き、40 msで切り返す。6コマ目では胸が反対側へ43°回り、左手を開き、右手から左上へ差す刀を140 ms見せる。7コマ目まで切先が上がってから8〜9コマ目で戻る。総時間は720 ms。全身の踏み込みと毛先の遅れを同じ足元で比較できるよう、攻撃セルには72 pxを取った。[専用クリップ](../characters/crimson_blade/slash.json)
8. **同じ経過時刻で初版と完成版を比較した。** 原寸GIFはそれぞれのコマ時間を使う。S・SEでは4→5コマ目に足幅が開き、6コマ目に銀の線が反対側へ立ち上がる。SW・Wでは引いた刀と着地後の刀が前後で入れ替わる。NW・Nでは腰から上体の回転が読め、NE・Eでは横へ出る切先と遅れて返る黒髪を追える。奥向きに縮む局面では、手が隠れても足幅と毛先にポーズ差が残る。[原寸GIF](../docs/assets/crimson_blade/slash-comparison.gif)・[局面を揃えた比較図](../docs/assets/crimson_blade/slash-poses.png)・[比較元シートとタイミング](image_to_character_05/baseline/)
9. **ギャラリーに登録した。** 静止専用ベイクのメタデータと、全モードベイクから分けた歩行・攻撃のレイアウトを公開した。Chromeの原寸・通常速度で3モードを全方向に切り替え、キャンバスに現れた128コマを各PNGの対応セルと照合した。単発攻撃の再生ボタン、攻撃GIFと比較GIFのリンクも検査した。[公開用素材](../docs/assets/crimson_blade/)・[ギャラリー設定](../docs/gallery.js)

## 初版からの修正

初版の静止・歩行・攻撃を比較元に残し、その後に全身をベイクして判定した版は5版。方向や寸法の候補を同じ版で試した回数は含めていない。

| 改訂 | 初版または直前の問題 | 変更と再確認 |
| --- | --- | --- |
| 1 | 正面で前髪が顔を覆い、飾り布が脚と一体に見えた。4→5コマ間で刃が右手甲に接触した | 額を開け、毛先を二股へ伸ばし、前の布を外へ逃がした。刀の引き方を変えて97姿勢の接触を解消。肩甲の条件も、側面で実際に手前に来る左右を測るよう直した |
| 2 | 太くした袴の上端に孤立した1ボクセルが残り、NEで描かれた。着地の足幅も原寸では小さかった | 袴の関節より上を腰甲に収めて静止の断片を0に。右足の前進を4.9→5.9、外への開きを2.45→4.65にし、腰をさらに沈めた |
| 3 | 歩行で前布の自由端が左脚に入り、NWの歩行刀身は最小1 px、Nの発打点は2 pxだった | 前布の中段を前・外へ移し、歩行の右手首を−16°にした。発打点の刃を横へ開き、歩行の刀身は最小7 px、発打点は全方向12 px以上になった |
| 4 | 汎用検査に合格した版でも、刀単独では静止NWと歩行Wの3コマ目・NWの6コマ目に刃色が1 px離れた | 切先の奥行きと高さを直し、刀身の全厚を1.00→1.18にした。金の髪留めを髪の軸に巻く形に変更。刀単独の128セルで刃色が8近傍で連結した |
| 5 | 発打点は合格しても、Wの最大の溜めでは刀が体に隠れ1 pxしか見えなかった | 4コマ目の右手を後ろへ0.30移し、切先を低く引いた。Wで溜めの刃が9 pxとなり、全方向の溜め・発打・振り抜きがそれぞれの可視条件を満たした |

## 技術検証

| 対象 | 完成版で確認したこと |
| --- | --- |
| 採色・静止 | 採色を再実行してJSON一致。再生成した2つの配列が一致し、5,158ボクセルが1つの連結成分。静止はPASS 39、WARNING・FAIL・SKIP 各0。顔の肌はS・SW・SEで各17 px、目は2・5・5 px |
| 歩行 | PASS 16、WARNING・FAIL・SKIP 各0。接地ドリフト0。全48コマで刀身9 px、ポニーテール17 px、腰布25 px以上。頭部の上下動は全8方向にあり、各方向の目の画素数は6コマを通して一定 |
| 攻撃 | 8方向×9コマの余白・方向順・始終端・足元・握りを検査。補間を含む97姿勢で左右の手足の目標、装備固定、刃の他部位との交差を検査。発打点の刃は全方向15 px以上。部位と装備の条件はキャラクター側に記録した。[品質条件](../characters/crimson_blade/quality.json) |
| 髪・腰布・鞘 | 髪・前布・後ろ布のうち追従重みが最大値の半分以上の132・68・70中心点を、歩行6姿勢と攻撃9キーで他部位および鞘の漆面と照合して重なり0。骨盤に固定した鞘の漆面84中心点は、歩行6・攻撃97姿勢で他の剛体部位との重なり0 |
| 刃の連続性 | 見た目の剛性を調べるため、刀単独の**刃色**を静止8・歩行48・攻撃72セルで測定。全セルで1つの8近傍連結成分。全身で自然に遮蔽される箇所は局面別の可視画素を別に測定 |
| 再生成・既存4体の回帰 | CRIMSON BLADEを別の出力先に再ベイクし、128コマのデコードRGBA、メタデータ、攻撃GIFが一致。既存4体も512コマのRGBA、静止・歩行・攻撃のメタデータ、攻撃GIFが公開済み素材と一致。既存4体のFAILは0 |

既存体ではMAREN・CRYSTAL MAGEの静止に部位所有の断片に関する既知WARNINGが各1件、CRYSTAL MAGEの歩行に斜め顔の目の面積変化が1件あった。AZURE RONIN・FLEUR KNIGHTは警告0。試作時に公開候補との照合を省いたSKIPは、完成版の公開用検証で再実行した。[方向別の実測値・回帰ハッシュ](image_to_character_05/results.json)・[髪、布、鞘、刀の追加計測](image_to_character_05/inspect_motion.py)

## 制作手法の再現性と限界

- ガイドで順序と入出力が決まっていたのは、採寸点の記録、MARENの採色器の利用、リグ・IK・姿勢格子、静止と全モードのベイク、公開ファイルの組み立てまで。正式3体と実験04に続き、今回の片手装備と複数の布でも共通エンジン・共通歩行クリップをそのまま利用できた。
- AZURE RONINから高い結び目の重み付け、反り刃の立体断面と細部描画を、MARENから刀先・手・支持足を同時に追う評価を、CRYSTAL MAGEから近い色を材質グループで分ける方法を使った。FLEUR KNIGHTの実験で使った装備体積とブラウザ画素の照合を、今回は鞘と腰布にも適用した。
- 新たに判断が必要だったのは、後ろへ戻る短い毛先、肌を隠さない非対称の前髪、紺地を残す肩甲の金縁、脚から離れる帯の曲線、低く引いた刀を背面からも読める手首角。原寸の二股・布と脚の分離・溜めの予告は、全身の連結性や発打点だけを調べても判定できなかった。
- ガイドには、細い武器で「単独描画の連結数」と「全身での可視面積」を併記する表、溜め・発打・振り抜きそれぞれで最も読みにくい方向を探す手順を加えたい。衣装には、固定した縫い目と重みの高い自由端を区別して比較すると、直すべき位置を絞りやすい。
- 顔の識別は正面と斜め前が中心で、原画の細い刺繍は白縁・金の帯に集約した。背面の生地と装飾の配置は推定。交差の数値は指定した姿勢・材質・中心点を対象とする。実ゲームの当たり判定、旋回からのつなぎ、プレイヤーによる識別評価は未検証。

## 再現手順

リポジトリ直下のPowerShellで実行する。元画像を所持する場合は、同じ採色領域をMARENの抽出器に渡せる。

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
$char = 'characters/crimson_blade'
$config = "$char/character.json"
$pub = 'docs/assets/crimson_blade'
$run = Join-Path $PWD ('.phase1/crimson-' + [guid]::NewGuid())
& $python -W error::RuntimeWarning -m characters.crimson_blade.build_model --out "$run/model"
& $python -m spritestack --character $config --modes idle --out "$run/idle"
& $python -m research.verify_character --character $config --out "$run/idle"
& $python -m spritestack --character $config --out "$run/all"
& $python -m research.verify_walk --character $config --out "$run/all"
& $python -m research.verify_attack --character $config --out "$run/all" --gif "$run/all/attack.gif" --published $pub
& $python -m research.image_to_character_05.inspect_motion --bake "$run/all"
& $python -m research.maren_slash.compare --before research/image_to_character_05/baseline --after $pub --out "$run/comparison" --phases sink coil cut "follow through" --directions S SW W NW N NE E SE
```

採色の追試では `$reference` にローカルの原画パスを設定し、`& $python -m characters.maren.extract_reference --image $reference --regions "$char/reference_regions.json" --out "$run/reference_palette.json"` を実行する。原画と採色枠を重ねた確認図はローカルに保持した。
