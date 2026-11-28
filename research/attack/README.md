# 攻撃の原寸比較と軌跡分析

同じ局面のスプライトとモデル空間の座標を並べて、動作がどう変わったかを調べる。まず比較GIFを原寸・通常速度で見て、意図が読みにくい方向とコマを選ぶ。次にポーズ表と軌跡を開く。GARDなら「槌頭が肩の横に落ちるか、握りより前で打ってから押し込むか」をEとNWで比較できる。[制作手順](../CHARACTER_CREATION_GUIDE.md) · [過去のGARD比較画像](../adventurers/gard-hammer/README.md)

## 実行

リポジトリのルートで実行する。入力は各版の攻撃ベイクに含まれる `attack.png`、`metadata.json`（`animations.attack`）、`joints.json`（`attack`）。`--modes attack` と全モードベイクの双方を読める。公開フォルダには関節列が含まれないため、手元にベイクがない場合は次のように作る。

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$run = Join-Path $PWD ('.phase1/motion-compare-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $run | Out-Null
# 改善前のモデルとクリップを作業用に展開する
git archive --format=zip --output "$run/before.zip" 4f77259 characters/gard motions
Expand-Archive -LiteralPath "$run/before.zip" -DestinationPath "$run/source"
& $py -m spritestack --character "$run/source/characters/gard/character.json" --modes attack --out "$run/before"
& $py -m spritestack --character characters/gard/character.json --modes attack --out "$run/after"
& $py -m research.attack.compare_motion --before "$run/before" --after "$run/after" --out "$run/gard" --markers hammer_head hand_R elbow_R shoulder_R pelvis toe_R toe_L chest --relative-to hand_R --frames 4 5 6 7 --directions E S NW --front
```

下の再現値の改善版は `ebd3dc2`。将来クリップが変わったら、改善版もこのリビジョンから旧版と同じ方法で展開する。既存ベイクが手元にあるときは最後の比較コマンドだけでよい。利用できる点名は `joints.json` の `attack` の各コマにある。装備によっては先頭の静止姿勢に点名が現れない。

旧版のない例では同じフォルダを二度渡す。次の例はリコの矢がいつ現れ、離れ、消えるかを調べる。

```powershell
& $py -m spritestack --character characters/rico/character.json --modes attack --out "$run/rico-bake"
& $py -m research.attack.compare_motion --before "$run/rico-bake" --after "$run/rico-bake" --out "$run/rico" --markers arrow_tip arrow_nock bow_tip string_center hand_L hand_R --relative-to hand_L --phases nock draw aim loose recoil --directions S E N
& $py -m unittest -v research.attack.test_compare_motion
```

## 出力の読み方

| 出力 | 内容 |
| --- | --- |
| `comparison.gif` | 上段がbefore、下段がafter。両方の足元を基準としたセル矩形の和集合に、PNGを1×で配置する。8方向を行名で対応づける。両版のコマ境界を実時間で併合し、短い版の終了後は最終姿勢に `held` を表示する。両方の終了後に比較全体がループする |
| `poses.png` | 指定方向ごとにbefore／after。両版の局面名と1始まりのF番号を記載。セル全体を原寸で収める。`--directions` はこの図のみを絞る。`--frames 4 5 6`、版ごとに番号が違えば `--frames 4=3`。名前で選ぶときは `--phases impact 'settle=drive through'`。同名の始終端は番号で区別する。省略時はどちらかの版がコマを切り替える各時刻の組を載せる |
| `trajectory.csv` | 版×コマ×マーカーで1行。F番号、開始ms、表示ms、局面名、そのコマのイベント名、実際の点名、XYZ、直前コマからのdx/dy/dz、任意の基準点と相対XYZ。+Xは本人の左、+Yは前、+Zは上。単位はすべてモデル単位。左右・高さの変化も符号付きで読める |
| `trajectory.png` | `--markers` の先頭の点を側面（Y/Z）・上面（Y/X）、`--front` で正面（X/Z）にも描く。各投影は両版の全座標から共通範囲を取り、縦横は等尺。番号は選択コマ、輪は実際に記録されたイベント。凡例に版別の時刻・局面名・イベント名を示す。別の関節を図にするには、その点を先頭へ移す |

`--markers` と `--relative-to` には `旧名=新名` も使える。例えば異なる杖のマーカーを比較するなら `staff_tip=crystal_tip`。片方の版だけに存在する同名の点は、その版の値だけを出力する。両版とも未知の点、または明示した対応の片側が誤っている場合は利用可能な名前を表示する。座標が欠けたコマはCSVで空欄とし、次に現れたコマの差分も空欄になる。図は欠けた区間で線を切る。基準点が欠ければ相対座標も空欄になる。

GIFは累積時刻を最寄りの10 msに丸める。同じ刻みに入った切り替えは表現できず、ビューアーによっては短い遅延に再生下限もある。正確な時刻はCSVのmsを使う。GIF形式には256色の制限があり、色・透過の照合には元のRGBAを使う。軌跡の線はベイクされた連続する**コマの点**を結ぶ。コマ間のIK解、衝突、目標への命中は表していない。異なるカメラの画像は各版の画素密度のまま、異なるモデルの座標は各版の原点・単位のまま比較する。

出力先には未使用のディレクトリ名を渡す。シート寸法・RGBAハッシュ（記録されている場合）、方向名、列・表示時間・関節列、有限のXYZ、イベントのコマと時刻の整合を確認してから結果を公開する。詳細は [CLI](compare_motion.py) と [投影・欠測区間の描画](trajectory_plot.py) にある。

## 検証記録

### ガルドの旧版・改善版

各版の入力シートを当該Gitリビジョンの公開PNG（デコード後RGBA）および攻撃メタデータと照合した。旧版は84×84／アンカー(42,67)、改善版は100×100／(50,75)。両版9コマ・960 msで、`hammer_impact` はF6の540 ms。CSVを旧比較器の保存値と照合したところ、2版×9コマ×7点×3軸の378値すべてが旧CSVの小数6桁の丸め内（最大差0.000000500未満）で一致した。[旧座標CSV](../adventurers/gard-hammer/trajectory.csv)

| モデル空間の測定 | 旧版 | 改善版 |
| --- | ---: | ---: |
| F5→F6 槌頭 ΔY／ΔZ | +2.225／−19.848 | +17.928／−12.657 |
| F6→F7 槌頭 ΔY | −0.786 | +3.982 |
| F5→F7 槌頭 ΔY | +1.439 | +21.910 |
| F6 打点XYZ | (−19.057, 9.983, 10.756) | (−8.501, 22.896, 17.671) |
| F7 振り切りXYZ | (−18.016, 9.197, 8.399) | (−8.422, 26.878, 14.429) |
| F6→F7 右肩／右肘／右手 ΔY | +0.620／+0.724／+0.300 | +1.792／+4.180／+4.200 |
| F6→F7 骨盤／右足先／左足先 ΔY | +0.100／0／0 | +1.000／0／0 |
| F7 槌頭が右手／胸より前に出る距離 | 3.097／6.524 | 10.128／21.773 |

旧報告本文の右肩「1.78」は、同じ報告のCSVから `shoulder_R.y` を引くと 9.508899 − 7.716457 = **1.792442** になる。両ベイク・両比較器の座標が一致し、差は本文の数値に限られる。改善版の肘内角はF6で79.0°、F7で143.3°。原寸ポーズ表のEでは握りを越える槌頭を追え、Sでは前進が奥行きに縮む。NWでは盾と柄が重なり、槌頭の位置と上体の傾きが手掛かりになる。[当時の8方向観察と同期GIF](../adventurers/gard-hammer/README.md)

### 他の武器と境界条件

| 入力・検査 | 今回確認した結果 |
| --- | --- |
| MARENの同一版 | 72×72、800 ms。`sword_tip`・`hand_R`・`shield_center` を出力。イベント未定義の剣に発動印を追加せず、局面名とコマを追えた |
| RICOの同一版 | 80×80、590 ms。`arrow_tip`・`arrow_nock` はF3〜F6だけ、F6は360 ms、F7の400 msで欠測へ戻る。弓先と左右の手は矢の前後も追跡できた |
| SENAの同一版 | 100×100、1,000 ms。`crystal_tip` と右手を詠唱・放出・余韻の局面名で選択。F6の580 msに `ice_release` が表示された |
| 4組の実ベイク | 上記3組とGARD旧／新のGIFを全コマ再デコード。各組2版×9コマ×8方向、計576タイルで、同じ床色に合成した元シートとRGBが一致。全コマの遅延も各版の表示時間と一致 |
| RICOとSENAの交差入力 | 異なるセル・アンカー、`bow_tip=crystal_tip` と左右別の基準点に対応。590／1,000 msを18区間で再生し、590 ms以降のリコは最終姿勢。異なる動作を同じ時刻に置くための検査 |
| [自動テスト](test_compare_motion.py) | 3対4コマ、密接した非整数センチ秒境界、逆順の8方向、幅・高さ・アンカーが異なる入力を生成。GIFをデコードして全方向のアンカー画素とセル両端、短い側の保持、表示時間を照合。中間欠測の前後で差分と線分が途切れること、相対座標・イベント・異名マーカーの対応を検査 |
| 入力異常 | 範囲外のF番号、存在しない局面・マーカー、誤ハッシュ・シート寸法・列数・イベント時刻、関節ファイル欠落を拒否。途中の結果が出力先に残らないことを検査 |

同一版の3組は適用範囲の検査で、各攻撃の改善量を評価する比較には使っていない。

制作ガイド§9の公開手順も、GARDとMARENの保存済み静止・全ベイクから新しい出力先へ実行した。`export_loops` の公開候補を `verify_character`・`verify_attack` で照合し、呼吸のあるGARDは `verify_loops` も通過した。`verify_walk` は両体とも16 PASS。静止はGARDが33 PASS、MARENが32 PASSと既知のWARNING 1件（胸部の33ボクセルが骨盤に接し、静止8方向では描画されない）。FAIL・SKIPは0。攻撃の補間検査は各97姿勢。

### 制作手順の見直し

- 画像制作実験01〜07、歩行・頭部・細剣と武器分離の研究、正式3体の攻撃、冒険者の造形・攻撃・槌の改訂を、10体のビルダー・マニフェスト・クリップ・品質条件と照合した。武器分離の初期案と採用された局所描画、静止検査の装着役名と攻撃主手、初版と改訂版の槌軌道を区別して [制作ガイド](../CHARACTER_CREATION_GUIDE.md) に反映した。
- 既存の [剣・詠唱の公開画像比較](../maren_slash/compare.py) から方向名でタイルを取り出す処理を再利用した。公開画像だけを比べる用途には従来の比較器が使える。[槌の旧比較器](../adventurers/gard-hammer/compare.py) は当時の図版を再現する。`research.walk.compare` は歩行、[剣輪郭の計測](outline.py) は投影と描画の調査を担当する。今回のCLIはベイクを読むだけで、キャラクター名・固有の座標範囲・特定の発動コマを内蔵しない。
- 更新先はルートREADME（入口）、AGENTS.md（開発規約）、制作ガイド（作業順・作例・公開）、[技術設計](../../docs/TECHNICAL_DESIGN.md)（左右・格子・イベント）、[ロードマップ](../ROADMAP.md)（確認範囲）、GARDの槌の報告（右肩の数値訂正）。新規ファイルはこのREADME、比較CLI、軌跡描画、回帰テスト。反復画像とCSVは `.phase1/` に生成した。

| 次の依頼を想定した導線 | 作例から検証まで |
| --- | --- |
| 新しい重戦士 | ガイド§1 → GARD・GOBLIN・FLEUR → §3の固定と§7の打点 → 槌頭・右手・腰・両足で前後差を測り、Eと背面斜めから全方向へ確認を広げる |
| 新しい弓使い | §1 → RICOの設定・攻撃クリップ → 技術設計「攻撃装備とイベント」→ 弦と両手、離弦前後の欠測、通知時刻とゲーム側の表示境界を確認する |
| 新しい魔法使い | §1 → SENAの片手詠唱／MAGEの本 → §6の裾と§7の杖 → 水晶先端の相対座標と原寸ポーズ、姿勢格子・セルの余白を確認する |
| 既存剣士の攻撃改善 | §7 → MARENまたはRONIN → 旧ベイクを保存 → §8で剣先・支持足と局面のmsを比較する。欠落があれば装備単独と全身の部位ID・局所描画を調べ、変更範囲に沿って回帰する |

上記の再生成コマンドでもGARD旧／新とRICOを新しい作業先へ焼いた。保存ベイクと攻撃RGBA・レイアウト・各コマの全関節が一致し、GARDの比較GIF・ポーズPNG・CSV・軌跡PNGは4ファイルともバイト一致した。ガイド§3のビルダー実行もGARD・MARENで試し、両体で2つのNPZの配列が保存値と一致した。

キャラクター、クリップ、リグ、既存検証器、公開ファイルに差分はない。正式3体とLARK・BRAMの全再ベイクやブラウザの再生回帰は今回は未実施。新造形の品質、連続衝突、実ゲームでの弾・当たり判定と操作感は未検証。将来、同一装備の両手拘束や柔軟な武器を扱う場合は、その拘束を表すマーカーと作例から検証する。
