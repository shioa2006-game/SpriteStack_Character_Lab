# CRYSTAL MAGE　本から水晶へつなぐ詠唱

[8方向の原寸比較GIF](../docs/assets/crystal_mage/cast-comparison.gif) · [詠唱から余韻までのポーズ比較](../docs/assets/crystal_mage/cast-poses.png) · [攻撃GIF](../docs/assets/crystal_mage/attack.gif) · [透過PNG](../docs/assets/crystal_mage/attack.png)

比較GIFは各方向で左が初版、右が今回の詠唱。どちらも1秒で1回発動し、それぞれのコマ時間で再生する。ギャラリーでは「CRYSTAL MAGE」→「攻撃」→「1×」で1方向ずつ確認できる。[GitHub Pages](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## 詠唱をどう変えたか

初版は3〜5コマ目の杖先の高さが32.2〜33.6モデル単位に集中し、本の高さの差も1単位ほどだった。発動後は杖が前に残り、次のコマでも切り替わった印象が弱かった。今回は両足を接地させたまま、読んでいる本、集まりつつある水晶、前方の発動点へと視線が移るように両腕に異なる動きを与えた。

| 局面 | コマ・時間 | ポーズ |
| --- | --- | --- |
| 構え・詠唱開始 | 1–2、70・100 ms | 左手で本を持ち上げ、表紙を自分の方へ傾ける |
| 詠唱 | 3、130 ms | 本を胸の前に掲げる。右手の杖は斜めに寝かせ、水晶を低く構える |
| 蓄積・発動直前 | 4–5、170・150 ms | 胴を引き、本を支えたまま杖を起こす。水晶が頭上へ来るまで2段階で明るくなる |
| 発動 | 6、80 ms | 上体を11°前傾させ、水晶を右前方へ送る。同時に左手は本を腰へ下ろし、水晶の周囲に小さな閃光が出る |
| 余韻 | 7、100 ms | 水晶の明るさが引き、杖先が斜め上に戻る。左手は本を再び胸元で受ける |
| 復帰 | 8–9、120・80 ms | 杖を身体の横に戻し、最後は静止と同じ構えで終わる |

| モデル上の位置 | 初版 | 今回 |
| --- | ---: | ---: |
| 杖先の高さ、詠唱（3）→直前（5） | 32.2 → 33.6 | 27.3 → 34.4 |
| 杖先の前後位置、直前（5）→発動（6） | 3.1 → 18.1 | −2.8 → 18.8 |
| 本の中心の高さ、詠唱（3）→発動（6） | 17.2 → 16.5 | 20.0 → 15.9 |
| 発動（6）から余韻（7）への杖先の上昇 | 1.4 | 7.5 |

本は従来の一体モデルを左手で傾けて掲げている。ページの開閉は表現していない。発動時の `glint` は既存の `glow` で明るくした水晶を中心に、透明な場所だけに最長2 pxの光を置く任意のキー。人物や杖には重ねず、水晶が完全に隠れた方向では光を作らない。部位IDや可視画素の計測は立体の描画結果を使うため、この光は水晶の画素数に含まれない。

## 原寸再生と回帰

Chromeで原寸の新旧GIFを並べて通常速度で再生し、攻撃GIFの全9コマも画面から取り出して照合した。W・Eでは詠唱時に本を顔の前で支え、発動で本を下げて杖を前へ突き出す。次の1コマで杖先が斜め上へ戻るため、どこで魔法を放ったかが分かる。S・SEは発動の杖が奥行き方向に短く映る。ここでは左右の手の高低差と水晶の一瞬の光が目印になる。発光を外した描画でも、特に側面で本の持ち上げ、杖の起き上がり、放出後の戻りを確認した。

| 全身描画の可視画素数 | S | SW | W | NW | N | NE | E | SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 本・詠唱（3） | 14 | 16 | 16 | 17 | 0 | 11 | 10 | 17 |
| 水晶・発動直前（5） | 8 | 8 | 7 | 6 | 6 | 4 | 6 | 5 |
| 水晶・発動（6） | 4 | 5 | 7 | 5 | 4 | 7 | 3 | 5 |
| 発動で透明領域に加わった光 | 4 | 5 | 4 | 4 | 2 | 4 | 6 | 1 |

- **装備と配置**　全72セルが64×64、足元アンカーは(32, 48)、最小透明余白は5 px。開始・終了は各方向の静止とRGBA一致。9姿勢とも杖・本は手と接し、接触は最低10面・22面だった。装備の元ボクセル中心を他部位（持ち手を除く）および揺れたローブ・マントと照合し、焼いた姿勢で交差は検出されなかった。
- **補間の範囲**　8区間を各12分割した97姿勢で両手足のIK、装備の固定、水晶と身体の非交差を検査した。3Dでキーを線形補間すると、中間姿勢の一部では杖軸が胸・マントの部位へ入り、本も胴や前腕と重なる。公開PNG・GIFとギャラリーが再生するのは検査済みの9姿勢。背後から見て本がマントに隠れる局面では、手前のマントを描く。
- **顔と衣装**　試作でSW・SEの発動時に目が消えたため、攻撃時の首の移動に対する頭の追従を左右0.6倍・前後0.24倍にした。最終版の頭部単独描画は全コマでSが2〜4 px、SW・SEが3〜4 px、W・Eが各1 pxの目を保つ。姿勢ごとの揺れは歩行と共通のローブ・マント処理を利用した。
- **回帰**　MAGEの48・64セルの静止と48セルの歩行は、従来の公開PNGとデコード後RGBAが一致し、対応JSONも一致。静止・歩行はいずれも失敗0件。既知の警告は静止で他部位に分断された部位片、歩行でSW・SEの目の画素数が3〜4 pxの間で変わること。共有ベイクの回帰としてMAREN・RONIN・LARK・BRAMも別フォルダで再生成し、静止・歩行・攻撃を公開素材または基準と照合した。

## 再現

初版の透過PNGと時間情報をコミット `425e1ec` の状態で保存した。ベイクには毎回新しい出力先を指定する。[比較基準](mage_cast/baseline/)

~~~powershell
$character = 'characters/crystal_mage/character.json'
$out = '.phase1/check-mage-cast'
python -m spritestack --character $character --out $out
python -m research.verify_attack --character $character --out $out --gif "$out/attack.gif" --published docs/assets/crystal_mage
python -m research.attack.outline --character $character --out $out
python -m research.verify_walk --character $character --out $out
python -m spritestack --character $character --modes idle --out "$out-idle"
python -m research.verify_character --character $character --out "$out-idle"
python -m research.maren_slash.compare --before research/mage_cast/baseline --after docs/assets/crystal_mage --out "$out-comparison" --prefix cast --phases invoke channel focus release hold --directions S SW W NW N NE E SE
~~~
