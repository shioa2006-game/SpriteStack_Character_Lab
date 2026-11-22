# AZURE RONIN　肩から前へ走る速斬り

[原寸の新旧比較GIF](../docs/assets/azure_ronin/slash-comparison.gif) · [8方向のポーズ比較](../docs/assets/azure_ronin/slash-poses.png) · [攻撃GIF](../docs/assets/azure_ronin/attack.gif) · [透過PNGシート](../docs/assets/azure_ronin/attack.png)

原寸GIFは各方向の左が初版、右が今回の速斬り。両方を同時に開始し、それぞれのコマ時間で再生する。ポーズ比較の画像では3〜6コマ目を順に2倍で並べた。ギャラリーでは「AZURE RONIN」→「攻撃」→「1×」で1方向ずつ再生できる。[GitHub Pages](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## ポーズと間合い

初版では3・4コマ目の切っ先がほぼ同じ場所にあり、背面斜めからは引きと溜めを区別しにくかった。今回は刀を肩の後ろへ引き、右足が着く瞬間に腰を返して刀を前方へ送る。次のコマでは重心を落としたまま、刀を身体の反対側へ払い切る。MARENが頭上で160 ms溜めて足元まで剣を落とすのに対し、RONINの溜めは80 ms、刀が抜ける先は横。1回の攻撃は従来と同じ520 ms。

| コマ | 初版 → 今回 | 主要な変化 |
| --- | --- | --- |
| 1・2　構え、引き | 50・50 → 30・50 ms | 構えから腰を引き、刀を身体の外へ開く。左手は前に出る |
| 3・4　振り上げ、溜め | 60・80 → 50・80 ms | 右足を浮かせながら肩と刀を引く。胴を39°ひねり、グリップを肩より高くする |
| 5　斬撃 | 40 → 30 ms | 右足を前へ4.25、外側へ2.70モデル単位踏み込み、胴を−23°へ返す。左腕は後方へ引く |
| 6　振り抜き | 50 → 90 ms | 踏み出した足を残し、腰を1.95単位沈める。切っ先が胴の反対側に出た姿勢を見せる |
| 7〜9　収め、復帰 | 60・70・60 → 60・70・60 ms | 刀を低く収めながら右足を引き、最終コマで開始時の構えに戻る |

| 切っ先と踏み込み（モデル単位） | 初版 | 今回 |
| --- | ---: | ---: |
| 3 → 4コマの切っ先の高さ | 21.7 → 23.4 | 22.4 → 28.5 |
| 4 → 5コマで切っ先が前へ進む距離 | 25.4 | 35.5 |
| 振り抜きの切っ先の左右位置（構えの正中を0、本人の左を正） | −1.4 | ＋6.5 |
| 右足の踏み込み（前方・外側） | 2.25・0 | 4.25・2.70 |

動きの変更はRONINの `slash.json` に収めた。カメラと刀の形状は従来どおりで、右手に固定した刀を既存の4×4サンプリングで描画した。ポニーテール、スカーフと腰布も攻撃時の既存処理で焼いた。

## 原寸での見え方と検証

初回の試作ではNWの斬撃が胴の後ろに完全に隠れた。切っ先を前方へ送り出す角度を変え、NWで胴の外へ出るようにした。続く試作では、振り抜きの刀がEで顔と重なった。最終版では右手を前に残し、刃が腰の前を斜めに横切る。Sでは溜めた刀が顔の右手側から反対側へ抜け、WとEでは背後から前方へ伸びる。NEでは5コマ目で刃が長く見え、低い姿勢へ移ると手と刃が身体に近づく。[原寸比較](../docs/assets/azure_ronin/slash-comparison.gif)

| 全身描画で見える刀身の画素数 | S | SW | W | NW | N | NE | E | SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 溜め（4） | 15 | 15 | 17 | 21 | 8 | 14 | 19 | 22 |
| 斬撃（5） | 14 | 20 | 25 | 11 | 7 | 19 | 25 | 17 |
| 振り抜き（6） | 16 | 17 | 21 | 21 | 8 | 11 | 21 | 20 |

Wの振り上げ（3）は全身描画で刀身が2片・14 pxに見える。刀だけを描くと1片・21 pxになり、人物に隠れる箇所を確認できる。Nの収め（7）でも刀身は単独17 pxのうち3 pxだけ見える。胴の手前へ描き足す補正は使っていない。

- **刀と握り**　元の反りを投影した中心線と描画を比べ、可視部分の最大ずれはNEで1.12 px、Eで0.97 px。この2方向では動作中の7コマすべてで可視刀身が1片につながった。97姿勢で両手足のIKと刀の取り付けを確認し、刀身と身体の交差は検出されなかった。焼いた9姿勢では揺れた髪・衣装と刀の交差はなく、右手と刀のボクセル接触は最低15面。左の支持足は全コマで接地した。
- **配置と顔**　576×512の透過RGBAシート、64×64セル、足元アンカー(32, 48)。方向順はS、SW、W、NW、N、NE、E、SE。72セルの最小余白は5 px、開始・終了は8方向とも静止とRGBA一致。頭部の単独描画では正面2 px以上、SW・SEで1 px以上の目が全コマに残った。
- **原寸再生**　Chromeで攻撃GIFと新旧GIFを通常速度で再生した。攻撃GIFの全9コマを原寸で画面から取得し、前後のシルエットを照合した。ギャラリーでも静止8・歩行48・攻撃72の計128コマをシートと照合した。
- **回帰**　RONINの48・64セルの静止と48セルの歩行は、従来の公開PNGにデコード後のRGBAが一致し、対応するJSONも一致。静止検証は63項目、歩行検証は16項目が合格し、警告・失敗はいずれも0件だった。

## 再現

リポジトリのルートで実行する。ベイク先には新しいディレクトリを指定する。比較用の初版はコミット `425e1ec` で公開したPNGと時間情報。[初版の保存先](ronin_slash/baseline/)

~~~powershell
$character = 'characters/azure_ronin/character.json'
$out = '.phase1/check-ronin-quick'
python -m spritestack --character $character --out $out
python -m research.verify_attack --character $character --out $out --gif "$out/attack.gif" --published docs/assets/azure_ronin
python -m research.attack.outline --character $character --out $out
python -m research.verify_walk --character $character --out $out
python -m spritestack --character $character --modes idle --out "$out-idle"
python -m research.verify_character --character $character --out "$out-idle"
python -m research.maren_slash.compare --before research/ronin_slash/baseline --after docs/assets/azure_ronin --out "$out-comparison" --directions S SW W NW N NE E SE
~~~
