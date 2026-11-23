# 実験04　FLEUR KNIGHT ― 開いた兜と百合の大盾

銀の鎧、顔の見える兜、金の百合を載せた青い大盾を、同じ立体モデルから8方向に焼いた。実験対象は新規の二足歩行・片手剣＋盾の1体。原寸で最も特徴を読み取りやすいのはSとSW。Wでは盾の厚みと剣の重なり、Nでは革張りの裏と肩甲の幅が見える。[ギャラリー](https://shioa2006-game.github.io/SpriteStack_Character_Lab/) のキャラクター欄で FLEUR KNIGHT を選択する。

| 素材 | セル・足元アンカー | 再生と比較 |
| --- | --- | --- |
| [静止PNG](../docs/assets/fleur_knight/idle.png) | 48×48、(24, 40)、8方向横並び | [初版と完成版・原寸と2倍](image_to_character_04/idle-comparison.png) |
| [歩行PNG](../docs/assets/fleur_knight/walk.png) | 48×48、(24, 40)、8行×6列 | [原寸歩行GIF](../docs/assets/fleur_knight/walk.gif)、9 fpsのループ |
| [攻撃PNG](../docs/assets/fleur_knight/attack.png) | 72×72、(36, 52)、8行×9列 | [攻撃GIF](../docs/assets/fleur_knight/attack.gif)・[初版との原寸比較GIF](../docs/assets/fleur_knight/slash-comparison.gif)・[全方向の主要4ポーズ](../docs/assets/fleur_knight/slash-poses.png) |

## 画像からモデルへ（工程1〜4）

1. **輪郭の優先順位を決めた。** 元画像は653×861。兜頂と靴底の間は840 px、盾の頂点から下端まで396 pxで、身長の約47%。盾は左手の前で脚甲まで覆い、右手からは両刃の剣が下がる。この比率、肩当ての段差、暗いひさしの下に見える顔を残した。見えない盾裏は革と平行な握り帯2本、背中は肩から続く背甲と兜の首当てで補った。[採色領域とランドマーク](../characters/fleur_knight/reference_regions.json)
2. **9系統を採色した。** 盾の青と縁金を別の矩形で取り直した。絵の銀の中間色は `#988481` で、反射や汚れを含む。48 pxでは金の縁や肌と混同したため、胸甲は冷たい `#a5afbd`、稜線は `#c3cbd2` に分けた。革1材質は抽出色を採用し、14材質は用途に合わせて調整。原画像を持つ環境では採色結果も再生成できる。[抽出値](../characters/fleur_knight/reference_palette.json)・[材質別の採用理由](../characters/fleur_knight/palette_provenance.json)
3. **17部位・15材質の立体を作った。** MARENの剣盾用リグと幾何形状の組み立て方を参照し、大きな肩甲、胸の稜線、三段の腰甲、膝甲、脚甲を各関節に割り当てた。ローブ状の一枚板に見えないよう、前で割れた濃紺の裾と左右の腰甲を分けた。盾は中央が前へ張り、上下が尖る断面とし、縁金、青い面、百合を重ねた。百合は盾面に沿う9×13の図案で、どの方向でも左手と一緒に回る。ひさしの縁と通気穴には暗色を残した。[モデル生成コード](../characters/fleur_knight/build_model.py)・[関節、装備、カメラの設定](../characters/fleur_knight/character.json)
4. **静止を原寸で比較した。** 正面で肌とひさしの境界が見え、胸の中央と両肩に独立した白い反射が乗る。SWでは金色の中央の花弁と両側の広がりが青地に残る。真横では図案が縮み、盾の縁と先端の形が主な識別点になる。背面の裏張りは表より暗い。試作と完成版の比較図は各版を同じ背景で1倍と2倍に並べた。[静止比較](image_to_character_04/idle-comparison.png)

## 歩行・攻撃・公開（工程5〜9）

5. **重装の歩行を付けた。** 共通6コマの接地区間を使い、足を高く上げず、両足が接地するところで胴が沈むようにした。接地中の移動は1コマ2.07モデル単位。盾腕の振りを小さくし、剣を持つ肘には余裕を残した。WとSWで盾と剣先が重なるため、腕の振りと休止時の剣先を一緒に調整した。[共通歩行](../motions/walk.json)
6. **兜と腰布を動かした。** 頭は首への追従と1単位のスナップを使う。短髪は兜に収め、布の追従は紺の裾と金縁だけに適用した。左右の裾は大腿に従い、胸甲・肩甲・盾は剛体。横顔の目は原寸で1 pxしかないため、眼窩内の位置まで調整した。[原寸歩行](../docs/assets/fleur_knight/walk.gif)
7. **重い斬り下ろしを作った。** MARENから採用したのは、大きなポーズ差と手・剣先・踏み足を一緒に評価する方法。騎士の9キーは盾を胸の前に残して右肩を引き、最大の溜めで腰を32°ねじる。そこを220 ms保持し、右足を前3.65・外2.2単位に着いて50 msの斬撃へ移る。低い振り抜きを160 ms見せて起き上がる。1回980 ms。剣には歩行と攻撃の両方で既存の細部描画を適用した。[専用クリップ](../characters/fleur_knight/slash.json)
8. **初版と完成版を比較した。** 1倍のGIFは両版を同じ経過時刻で再生し、溜め時間の変化も残す。2倍の比較画像は同じ局面を左右に並べる。側面では頭上から膝近くまで剣先の高低差が読める。Sでは盾越しに右肩と柄が先行する。N・NEの発打点では奥行きに向く直剣が短く投影されるため、直前の高い剣先と直後の低い肩が重要だった。[比較元の初版シートとタイミング](image_to_character_04/baseline/)
9. **ギャラリーに追加した。** キャラクター選択、3モード、8方向、1倍表示、攻撃の再生ボタン、GIFリンクをローカルのChromeで検査した。実時間に描画されたキャンバスをPNGの該当セルと突き合わせ、128コマが一致した。[ギャラリー設定](../docs/gallery.js)・[公開素材](../docs/assets/fleur_knight/)

## 制作中の失敗と修正

初回の静止・攻撃を比較基準に残し、モデルまたはモーションを変えて再評価した単位で**初版後6回**と数えた。数値を探るための個別の試算と検証スクリプトの編集は回数に含めていない。

| 改訂 | 観察と修正 | 再確認で分かったこと |
| --- | --- | --- |
| 1 | 初版は原寸で金の図案が塊になり、ひさしと額の銀が溶けた。花弁の間に青を戻し、兜・胸甲・肩甲の明暗を整理。左右の肘に残った孤立ボクセルも袖の長さで解消した | 剣先を前へ出すとWの刀身が0→16 pxになったが、今度はNWで消えた |
| 2 | 剣先を前方と外側の2軸で振って投影を比較。兜後ろの首当て、広い裾を追加し、姿勢ボリュームの前端を26→28に拡張した | 静止の刃が全方向で見えた。全モードのベイクでは歩行SEの第2コマがセル余白に抵触した |
| 3 | 歩行中の右手を上げ、手首を5°起こした。攻撃は切り込みの剣先を前外側へ向け、最大の溜めと発打点の時間差を広げた | 歩行SWの第1コマが余白に抵触。手を上げるだけでは斜め方向の収まりを保証できなかった |
| 4 | 拡大したE・NEの盾裏に表地の色が現れた。厚みを1.22→1.86単位に増やし、裏張りと帯を独立して読める厚さにした | 背面の革と金の縁が分かれた。歩行の余白は引き続き修正が必要だった |
| 5 | 休止時の剣先を短く高くし、歩行では高くした握りを保ったまま追加の手首角を戻した | 全方向のベイクと歩行の接地・余白が合格。キー間を含む攻撃検査で引きの右籠手と刃の接触、歩行の顔検査で横顔の目が1〜2 pxに変わることを発見した |
| 6 | 引きの刃を右腕の外へ向けて肘の曲がる方向を変えた。顔では眼窩と目の位置を分けて調整した | 97姿勢の主装備検査と大盾の追加検査が合格。W・Eの目は各6コマとも1 pxで安定した |

## 技術検証

| 対象 | 実測結果 |
| --- | --- |
| 採色・再生成 | 私有の入力画像から9系統の記録を再抽出しJSONが一致。生成関数からの材質・部位配列が一致。17部位を含むモデルは10,498ボクセルの単一連結成分 |
| 静止 | PASS 30、WARNING / FAIL / SKIP 各0。最小余白2 px。顔の肌はS・SW・SEで25・16・15 px。盾の花はS・SWで38・40 px |
| 歩行 | PASS 16、WARNING / FAIL / SKIP 各0。接地ドリフト0、足元の水平中心移動は最大0.95 px。刀身と盾の可視画素は全48コマで最低2・16 px |
| 攻撃 | 72コマの余白、最初と最後の構えのRGBA、公開タイミングを照合。キー間を含む97姿勢で両手の目標・接続・刀身の干渉を検査。出力キーの握り接触数は剣30・盾32以上。発打点の刀身はNEの10 pxからWの31 px |
| 盾固有の確認 | 盾全体のボクセル中心を各部位へ逆変換し、握る左手を除く部位との重なりは歩行6姿勢・攻撃97姿勢で0。大腿に追従した布について攻撃9キーと盾の重なりも0 |
| 回帰 | 別出力先で騎士を再ベイクし、全128コマのデコードRGBAとレイアウトが一致。既存3体も合計384コマのRGBA、静止メタデータ、歩行・攻撃レイアウトが公開版と一致し、攻撃GIFもバイト一致 |
| 既存の注意項目 | 既存3体はすべてFAIL 0。MARENとMAGEの静止には部位所有に伴う小断片の既知WARNINGが各1件。MAGEの歩行には斜め顔の目の画素数変化が1件。RONINは警告0 |

[検証数値と再生成RGBAハッシュ](image_to_character_04/results.json)・[大盾の追加検査](image_to_character_04/check_shield.py)・[キャラクター別の判定条件](../characters/fleur_knight/quality.json)

### 再現コマンド

リポジトリ直下のPowerShellから実行する。公開素材と比較する際は同じ版の設定、モデル、出力を組み合わせる。

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$char = 'characters/fleur_knight'
$config = "$char/character.json"
$pub = 'docs/assets/fleur_knight'
$out = Join-Path $PWD ('.phase1/fleur-' + [guid]::NewGuid())
& $python -m characters.fleur_knight.build_model --out "$out/model"
& $python -m spritestack --character $config --modes idle --out "$out/idle"
& $python -m research.verify_character --character $config --out "$out/idle"
& $python -m spritestack --character $config --out "$out/all"
& $python -m research.verify_walk --character $config --out "$out/all"
& $python -m research.verify_attack --character $config --out "$out/all" --gif "$out/all/attack.gif" --published $pub
& $python -m research.image_to_character_04.check_shield
& $python -m research.maren_slash.compare --before research/image_to_character_04/baseline --after $pub --out "$out/compare" --directions S SW W NW N NE E SE
```

元画像の所持者は `$reference` にそのパスを設定し、`& $python -m characters.maren.extract_reference --image $reference --regions "$char/reference_regions.json" --out "$out/samples.json"` で採色を追試できる。

## ガイドの有効性と残った課題

- [制作ガイド](CHARACTER_CREATION_GUIDE.md)と[技術設計](../docs/TECHNICAL_DESIGN.md)から、採色記録、部位ID・左右、モデル生成、ベイク、検証、公開の順序と入出力を決められた。歩行、IK、頭部追従、布、細い刃の描画は既存3体で使われる実装をそのまま使えた。
- 固有の設計判断は、盾の表裏の厚さ、原寸に残る花弁の隙間、兜の下の肌と目の配置、肩当てに触れずに剣を引ける軌道だった。汎用検証の可視画素数だけでは金の塊と花弁を区別できず、背面に紋章色が漏れても盾自体は合格し得る。原寸の正面・斜めと、拡大した裏面を対にする手順が役立つ。
- ガイドの採色コマンド例は各キャラクター専用の抽出モジュールを想定している。今回はMARENの抽出CLIに新しい領域設定を渡すだけで足りた。両方の呼び方を例示すると、次回はその判断が早い。大きな副装備には、主武器の軌道検査に加えて副装備全体の体積を確認する例も有用。
- 盾裏と後頭部は1枚の画像から補完した造形。真横では百合の細い枝まで同定できず、NEの斬撃では剣先が短く見える。干渉検査は指定した姿勢・ボクセル中心での測定で、連続時間の全点を保証するものではない。ゲーム側の移動速度、攻撃判定との同期、実機でのプレイヤー評価は未検証。
