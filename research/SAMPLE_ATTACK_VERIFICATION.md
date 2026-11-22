# 仕上げ Phase 1　盾剣・刀・杖の8方向攻撃

MARENの数値と所見は初版（425e1ec）の記録。現在の斬撃は[振りかぶりの再制作と新旧比較](MAREN_DYNAMIC_SLASH.md)を参照。

各GIFは左上から S、SW、W、NW、下段に N、NE、E、SE を並べ、PNGと同じ9コマ・同じ時間配分で繰り返す。[ギャラリー](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)では方向を選んで1回ずつ再生できる。

| 動作 | セル・足元アンカー | 時間 | 主要局面で8方向中最少の可視画素 | 手と装備の最少接触面数 |
| --- | --- | ---: | --- | --- |
| [MARENの初版](https://github.com/shioa2006-game/SpriteStack_Character_Lab/blob/425e1ec/docs/assets/maren/attack.gif) | 72×72・(36, 52) | 800 ms | 斬撃の直剣11 px | 剣24、盾28 |
| [AZURE RONINの速斬り](../docs/assets/azure_ronin/attack.gif) | 64×64・(32, 48) | 520 ms | 斬撃の刀6 px | 刀14 |
| [CRYSTAL MAGEの詠唱・発動](../docs/assets/crystal_mage/attack.gif) | 64×64・(32, 48) | 1000 ms | 発動時の水晶4 px | 杖9、本22 |

## 制作と目視

- MARENは盾を前に残し、剣を斜め上に構えてから前下方へ振り抜く。64 pxでは振りかぶりが上端に届いたため、画素密度を1.19 px/単位に保ったままセルを拡張した。試作のNWでは斬撃の刃が1画素まで隠れた。右手を外へ出し、斬撃と振り抜きで別々に刃の向きを調整した。
- RONINは腰のひねりと空いた左手で構え、40 msの斬撃で刀を前方へ返す。直剣と同じ姿勢計算・細剣描画を使い、手・刃の軌道と時間配分は専用にした。刀の反りを含む元形状の投影と比較した。SW・Wの予備動作では刀身の一部が人物の後ろに回る。単独描画と全身描画の可視画素数に差があり、手前の画素を残した。
- MAGEは本を胸元へ寄せ、杖を起こして溜め、前方へ向けて発動する。クリップの `aim` は杖の向き、`support_delta`・`support_pitch` は本の位置と角度、`glow` は水晶の可視画素を白に近づける割合。発動キーで0.92になる。初稿の杖尻とマントの重なりを調べ、右手・杖の傾き・肘の位置を調整した。
- 3体とも首の移動を追って頭を1単位刻みで配置する。MARENは前後の追従を0.55倍にし、振りかぶりで斜め正面の目が消えるのを抑えた。`attack.follow_cloth` は歩行用の衣装・毛先の領域を使い、攻撃のコマ時間に合わせて少し前の胴の位置を参照する。開始前の履歴は静止姿勢とし、最後の構えで揺れを収める。

## 再生成と検査

リポジトリのルートで実行する。名前は `maren`、`azure_ronin`、`crystal_mage`。出力先には未作成のフォルダを指定する。

~~~powershell
$name = 'maren'
$character = "characters/$name/character.json"
$out = ".phase1/check-attacks/$name"
python -m spritestack --character $character --out $out
python -m research.verify_attack --character $character --out $out --gif "$out/attack.gif" --published "docs/assets/$name"
python -m research.verify_walk --character $character --out $out
python -m spritestack --character $character --modes idle --out "$out-idle"
python -m research.verify_character --character $character --out "$out-idle"
python -m research.attack.outline --character $character --out $out
~~~

攻撃検証は全72セルの余白・方向・アンカー・時間・構えへの復帰を検査し、各コマで支持足の底、部位の残存、装備と手が接する面、主装備と変形後の髪・衣装の占有セルを調べる。各キー間を12分割した97姿勢で両手・両足のIK、装備と手の変換、剣身または水晶のボクセル中心と身体の交差を検査した。検査対象は離散サンプルで、全表面の連続衝突までは評価していない。MAGEの杖軸では、発動キーに右前腕と重なるボクセル中心が1個残る。首や顔への杖の突き抜け、握りの断絶はシート上で見られない。

静止と歩行は3体とも既存公開PNGのRGBA、対応JSONと一致した。MAGE・RONINの64 px静止比較も対象。静止検証にはMAREN・MAGEの既知の部位断片、歩行検証にはMAGEの斜め方向の目が3〜4画素で変動する警告が残る。各検証のFAILは0。LARKは旧PNG・部位ID画像・メタデータの回帰に合格し、BRAMも再生成・IK・接触検証および公開PNG・メタデータの照合に合格した。

公開するのは各体の `attack.png`、`attack.gif` と、ベイクの `metadata.json` から `animations.attack` を収録した `attack.json`。静止・歩行から切り替えたときもCanvasの足元を揃え、単発再生は `durations_ms` を使う。
