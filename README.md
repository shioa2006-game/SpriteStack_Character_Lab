# SpriteStack Character Lab

AIを活用したゲーム用ピクセルアートキャラクターの自動生成を研究するリポジトリです。中心技術は **Sprite Stacking × Skeletal Rig × Weight Deformation × PNG Baking**。ブラウザゲームで使える透過PNGスプライトシートの生成を目指します。

[3体の攻撃GIF・検証結果・再生成手順](research/SAMPLE_ATTACK_VERIFICATION.md)

## 現在の実装状況

| 状態 | 対象 |
| --- | --- |
| 実装済み | 設定から二足歩行モデルを読み込む共通ベイク、腕・脚の2関節IK、静止・歩行・攻撃の8方向PNG、静止だけのベイク（比較用セル付き）、静止と歩行だけのベイク、歩行の体格別の調整値、布・髪の従属運動（`walk.secondary`）、歩行時の頭部の連動（`walk.head`）、細い剣の歩行の描画（`walk.fine`）、設定ファイルで条件を変えられる汎用品質検証、歩行・攻撃検証、剣士2体の斬撃と魔法使いの詠唱・発動、Canvasギャラリー |
| 検証済み | LARKの基準PNGとのRGBA・配置・再生時間の一致。ドワーフ戦士BRAMへの共通モーション転用 |
| 試作 | BRAMの肩・肘・膝のウェイト変形。実験用コマンドで検証。参考画像1枚から作ったMAREN、魔法使いCRYSTAL MAGE、スカーフの剣士AZURE RONINの静止8方向（CRYSTAL MAGEとAZURE RONINは48×48と64×64の比較）と歩行8方向×6コマ |
| 未実装 | 量産用のウェイト変形、別の骨格構成、画像からの生成の自動化（採色範囲・形状寸法の自動決定）、杖を地面に突く歩き方 |
| 検証課題 | 他の体形への転用範囲、側面・背面の斬撃の視認性、停止・旋回、実ゲームでの操作感 |

方向順、セル寸法、アンカー、フレーム配置は[出力メタデータ](experiments/lark_stage3/output/metadata.json)に記録されています。開発時の基準は [AGENTS.md](AGENTS.md) を参照してください。

## ディレクトリ構成

| 場所 | 内容 |
| --- | --- |
| [spritestack/](spritestack/) | 共通CLI、設定読込、二足歩行リグ、ボクセル再スライス、布・髪の従属運動、描画、ベイク |
| [characters/lark/](characters/lark/) | LARKのモデル・モーション参照、材質、リグ、表示と計測の設定 |
| [characters/bram/](characters/bram/) | BRAMの独立モデル、部位マスク、設定、攻撃目標の転用手順 |
| [characters/maren/](characters/maren/) | 参考画像から作ったMARENのモデル生成コード、NPZ、設定、品質設定、採色範囲と抽出色、配色の出典、旧来の静止のベイク |
| [characters/crystal_mage/](characters/crystal_mage/) | 参考画像から作った魔法使いCRYSTAL MAGEのモデル生成コード、NPZ、設定（64×64の比較用の `comparison_view` を含む）、品質設定、採色範囲と抽出色、配色の出典、旧来の静止のベイク |
| [characters/azure_ronin/](characters/azure_ronin/) | 参考画像から作ったスカーフの剣士AZURE RONINのモデル生成コード、NPZ、設定（装備は右手の剣1つ、64×64の比較用の `comparison_view` を含む）、品質設定、採色範囲と抽出色、配色の出典。ベイクと検証は共通CLIと汎用検証だけを使う |
| [experiments/lark_stage3/](experiments/lark_stage3/) | ZIPから移植した基準コード・モデル・検証スクリプト・元のプレビュー |
| [experiments/lark_stage3/baseline/](experiments/lark_stage3/baseline/) | 旧版と、再生成に必要な元モデル・水平断面 |
| [experiments/lark_stage3/output/](experiments/lark_stage3/output/) | 8方向 PNG、関節・計測 JSON、水平断面・部位 ID の NPZ |
| [experiments/lark_stage3/comparisons/](experiments/lark_stage3/comparisons/) | 旧版との比較 GIF・PNG と計測結果 |
| [docs/](docs/) | 生成済み PNG を表示する GitHub Pages 用ギャラリー |
| [research/walk/](research/walk/) | 3体の歩行のGIF・調整前後の比較画像・計測値を作るスクリプトと結果 |
| [research/head/](research/head/) | 頭部の連動（`walk.head`）を入れる前の公開歩行、前後比較のGIF・頭の拡大図・計測値を作るスクリプトと結果 |
| [research/sword/](research/sword/) | 剣の描画（`walk.fine`）を入れる前のMARENとAZURE RONINの公開歩行、前後比較のGIF・剣の拡大図・計測値を作るスクリプトと結果 |
| [research/](research/) | [ロードマップ](research/ROADMAP.md)と[Phase 1 検証記録](research/PHASE1_VERIFICATION.md) |

移植元は `LARK_Stage_3A_GitHub_Import.zip` です。生成コード、モデル構成および同梱成果物は、ZIP 内の相対パスとファイル内容を保持して格納しました。元の仕様と既知の見た目の課題は[同梱 README](experiments/lark_stage3/README.md)と[技術検証レポート](experiments/lark_stage3/LARK_第3段階A_技術検証.md)を参照してください。

## Windows の Python 環境

ルートで PowerShell を開きます。既に `.venv` がある場合は仮想環境の作成を省略できます。実行確認に使ったのは Windows 11、Python 3.12.1、NumPy 2.3.5、Pillow 13.0.0 です。Python Launcher で 3.12 が見つからず、`python --version` が 3.12 を示す場合は、1行目を `python -m venv .venv` に置き換えてください。

`$python` は以降のコマンドでも使います。依存条件は同梱の `requirements.txt` を参照し、下記では再生成時の NumPy・Pillow のバージョンを指定しています。

~~~powershell
py -3.12 -m venv .venv
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $python -m pip install -r requirements.txt "numpy==2.3.5" "Pillow==13.0.0"
~~~

## 共通エンジンでの生成

ルートから `--character` に設定ファイル、`--out` に新しい出力先を指定します。静止も材質ボクセルから描画し、攻撃の空キーでは同じ静止フレームを使います。保存したPNGとJSONは[基準データ](experiments/lark_stage3/output/)と照合できます。

~~~powershell
$run = Join-Path $PWD ('.phase1/phase2-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$rebuild = Join-Path $run 'common'
& $python -B -m spritestack --character characters/lark/character.json --out $rebuild
& $python research/verify_rebuild.py $rebuild
~~~

出力は `idle.png`、`walk.png`、`attack.png`、歩行・攻撃の部位ID画像、`metadata.json`、関節と計測のJSON、材質・部位IDのNPZです。比較スクリプトはPNGの寸法とデコード後の全RGBAピクセル、方向順、アンカー、コマ数、歩行FPS、攻撃のコマ別表示時間を含むメタデータを比較します。PNGバイト差も表示します。

### 静止8方向だけを焼く

`--modes idle` は静止姿勢のモデルから8方向だけを焼きます。歩行・攻撃の姿勢計算と姿勢ボリュームの検査はしません。攻撃が合わないキャラクター（MAREN、CRYSTAL MAGE）でも静止は出力されます。既定の `--modes all` は従来どおり3モードを焼きます。

~~~powershell
& $python -B -m spritestack --character characters/maren/character.json --modes idle --out output/maren
& $python -B -m spritestack --character characters/crystal_mage/character.json --modes idle --out output/crystal_mage
& $python -B -m spritestack --character characters/crystal_mage/character.json --modes idle --cells 64 --out output/mage-64
~~~

出力は `idle.png`、`metadata.json`（`animations` は空）、`rest_part_ids.npz`。`--cells` で焼くセルを選べます。既定は `view.neutral_cell` と、`character.json` に `comparison_view` があればそのセルです。比較用セルは、同じモデルを `comparison_view` の画素密度・セル・アンカーで描き直し、`idle-<PX>.png` と `idle-<PX>.json` に書きます（48×48の拡大ではありません）。`comparison_view` のないセルを指定すると失敗します。`output/` はGitで無視されます。

### 静止と歩行だけを焼く

`--modes walk` は静止8方向と歩行8方向×6コマを焼き、攻撃は計算しません。攻撃が未完成のキャラクターでも歩行を焼けます。出力は全モードと同じ形式で、`metadata.json` の `animations` に歩行だけが入ります。

```powershell
& $python -B -m spritestack --character characters/maren/character.json --modes walk --out output/walk/maren
& $python -B -m research.verify_walk --character characters/maren/character.json --out output/walk/maren
```

`research.verify_walk` は歩行の技術的な条件を検査します。シートの配置、支持足の滑り（0であること）、接地、部位の残存、装備と手の接触と左右、本体から離れた破片、腕と反対側の脚の位相、描いたブーツの下端と足裏の投影の一致、装備の可視画素、布・髪が他の部位に入り込む割合、頭部の動き・首との距離・顔の画素（`walk.head` があるとき）、公開版との一致です。キャラクター固有のしきい値は `quality.json` の `walk` 節に書きます。結果の区分は汎用検証と同じで、FAILがあれば終了コードは1です。見た目の自然さは検査しないので、GIFで確認します。

```powershell
& $python -B -m research.walk.compare --after output/walk --out (Join-Path $run 'walk-comparison')
```

調整前（LARKの歩行設定をそのまま適用）と調整後のGIF・比較画像・計測値を書き出します。公開中の結果は [research/walk/results/](research/walk/results/) にあり、経緯は[歩行レポート](research/WALK_ANIMATION_VERIFICATION.md)にあります。

```powershell
& $python -B -m research.head.compare --after output/walk --out (Join-Path $run 'head-comparison')
```

`walk.head` を入れる前の公開歩行（[research/head/baseline/](research/head/baseline/)）と新しい歩行を並べ、8方向のGIF、頭と肩の拡大図、頭・胸の上端の行と目の画素数を書き出します。公開中の結果は [research/head/results/](research/head/results/)、経緯は[頭部連動レポート](research/HEAD_MOTION_VERIFICATION.md)にあります。

```powershell
& $python -B -m research.sword.compare --after output/sword --out (Join-Path $run 'sword-comparison')
```

`walk.fine` を入れる前のMAREN・AZURE RONINの公開歩行（[research/sword/baseline/](research/sword/baseline/)）と新しい歩行を並べ、8方向のGIF、NE・E・W・NWの剣の周りの拡大GIF、全コマの剣の拡大図を書き出します。剣身の画素数、片の数、途切れ、理想形状からの中心線のずれ、幅、手との接触も計測します。公開中の結果は [research/sword/results/](research/sword/results/)、経緯は[剣の修正レポート](research/SWORD_WALK_VERIFICATION.md)にあります。

### キャラクターの汎用検証

`research.verify_character` は、キャラクター名で分岐せず、設定ファイルと静止シートからモデル、リグと装備、シートを検査します。結果は PASS、WARNING（問題の可能性）、FAIL（仕様違反・生成不具合）、SKIP（未実施）で、FAILがあると終了コード1になります。

~~~powershell
& $python -B -m research.verify_character --character characters/maren/character.json --out output/maren
& $python -B -m research.verify_character --character characters/crystal_mage/character.json --out output/crystal_mage
& $python -B -m research.verify_character_selftest
~~~

キャラクターごとの条件は `character.json` と同じフォルダの `quality.json` に書きます。装備の役割（主装備は右手、副装備は左手）、可視画素の下限と方向、部位の存在条件、途切れてはいけない装備、公開先、モデル生成コード、配色とモーションの出典を設定できます。材質は配色の名前で書きます。項目の一覧、旧スクリプトとの対応、異常データでの検出テストは[共通化の検証レポート](research/SHARED_IDLE_BAKE_AND_VALIDATION.md)を参照してください。`verify_character_selftest` は一時フォルダに複写したキャラクターへ異常を入れ、検証が報告するかを確かめます（約2分）。

### 振りかぶり攻撃の生成

標準CLIで初期版の攻撃を再現できます。公開ギャラリーの振りかぶり版と輪郭改善版は、同じ剛体リグに攻撃クリップを適用して焼き出します。`--character` は `lark` または `bram`。どちらも9コマ、800 ms、64×64の攻撃セルです。

~~~powershell
$overhead = Join-Path $run 'overhead-lark'
& $python -B -m research.overhead.run --character lark --out $overhead
& $python -B -m research.overhead.compare --character lark --before $rebuild --after $overhead --out (Join-Path $run 'overhead-comparison')
$refined = Join-Path $run 'refined-lark'
& $python -B -m research.overhead.run --character lark --clip research/blade/clip.json --out $refined
& $python -B -m research.blade.compare --character lark --before $overhead --after $refined --out (Join-Path $run 'blade-comparison')
~~~

[振りかぶり版の検証](research/OVERHEAD_ATTACK_VERIFICATION.md) · [剣の輪郭改善と比較資料](research/BLADE_REFINEMENT_VERIFICATION.md)

## キャラクター設定 v1

[LARKの設定例](characters/lark/character.json)を参照してください。ファイル参照は設定ファイルの位置を基準に解決します。座標は X+ が身体の左、Y+ が前方、Z+ が上方です。

| 項目 | 内容 |
| --- | --- |
| `version` | 現在は `1` |
| `model` | 材質NPZの `slices` と、同じ形状の部位NPZの `parts`。どちらも Z/Y/X 順の `uint8`。0は空で、占有位置を揃える。原点とボクセル間隔は X/Y/Z 順。パレットは材質ID 1から順に、RGBの影色・基色・明色と陰影グループを指定する |
| `rig` | `parts` の並びを部位IDの1始まりと重なり時の優先順に使用する。胴体の `head`、`chest`、`pelvis`、左右の `thigh`、`shin`、`boot`、`upper`、`fore`、`hand`（`_R`、`_L`）と、装備の部位を指定する。`rest` は構えの関節座標、`attachments` は装備部位ごとの手と基準点の名前 |
| `posed_volume` | ポーズ後のボクセル原点・上限（X/Y/Z）と共通のボクセル間隔。各姿勢の全部位が余白付きで収まる大きさ |
| `view` | 挿入順で並ぶ8方向のヨー角、カメラ仰角、1単位当たりの画素数、足元アンカー、静止セルと描画用セル、静止・動作のレイの開始・終了・刻み、輪郭色 |
| `walk` | 既存形式の歩行クリップ、セル、歩幅に合わせる支持足・頭・腕の調整値。コマ別配列を `poses` に揃え、左右の接地は循環する連続区間、遊脚配列は接地外のコマ数に揃える。体格に合わせる任意の倍率（`stride_scale`、`swing_lift_scale`、`root_bob_scale`、`root_sway_scale`、`twist_scale`）、`root_level_offset`、`torso_lean`、左右別の `hand_lift`・`hand_outward`・`wrist_pitch_scale`、一定の手首角度 `wrist_pitch` を書ける。省略時はクリップのまま。任意の `secondary` に布・髪の領域を並べ、任意の `head` で頭部の連動を、任意の `fine` で細い剣の描画を指定する（下記） |
| `attack` | 既存形式の攻撃クリップ、セル、踏み出す側・主手・装備の軸・反対側の腕の調整値。非空キーに足と手の目標値、主手に合わせた `hand_R`/`hand_L` と `elbow_pole_R`/`elbow_pole_L` を指定する。`shield_delta` は反対側の手の相対オフセット。`wrist_roll` は刃の軸回りの手首角度（度、省略時は0）。`keys`、`poses`、`durations_ms` の長さを揃える |
| `measurements` | `lowest_z` は計測名と材質IDリスト、`visibility` は計測名と部位名・材質IDリストの組。計測項目がなければ空オブジェクトを指定できる |

### 布・髪の従属運動（`walk.secondary`）

歩行だけに効く任意の設定です。各領域は1つの部位の中から材質名と任意の範囲 `box`（モデル座標の `x`・`y`・`z` の下限と上限）でボクセルを選び、0から1の重みを付けます。重み0のボクセルは部位と一緒に剛体で動きます。それ以外は重みに応じた変換で各ボクセルを3×3×3点に分けて姿勢ボリュームへ書き込むので、隣り合うボクセルの角度が少し違っても穴が開きません。重なりでは `rig.parts` で後の部位が勝つ規則を保ちます。物理状態の積分はせず、姿勢は歩行クリップだけで決まります。静止・攻撃には影響しません。実装は [spritestack/secondary.py](spritestack/secondary.py) です。

| 種類 | 動き | 主な値 |
| --- | --- | --- |
| `skirt` | 骨盤から下がる布が同じ側の脚に付いて股関節の周りに回る。既定の `drive: "leg"` は股関節から足首への線の回転を使い、後ろへ蹴り上げたかかとが裾を押す。脚に沿う短い布は `drive: "thigh"` で太ももの回転を使う | `top_z`（重み0の高さ）、`hem_z`（重みが `follow` に達する高さ）、`follow`（0より大きく1以下）、`side_width`（中央 x=0 から重みが最大になるまでの幅） |
| `pendulum` | 髪・ポニーテール・マント・スカーフの端が、`pivot` から `tip` へ下がる房として、`lag_frames` コマ前の位置（歩いた距離を含む）を追って `pivot` の周りに回る。歩行は循環するので、最初のコマも最後のコマを追い、つなぎ目が出ない | `pivot`・`tip`（部位の静止座標）、`lag_frames`、`follow`（数値または x・y・z 別の倍率。z を大きくすると上下動で房が弾む）、`max_deg`（90以下）、`exponent`（重みの曲線、既定1）、`driver`（動きを追う部位。既定は自身の部位。背中に乗る長髪は `chest`）、`travel`（歩いた距離の効き、既定1） |

### 歩行時の頭部の連動（`walk.head`）

歩行だけに効く任意の設定で、今後のキャラクターの標準です。ない場合は従来の頭（首の左右動の `head_lateral_scale` 倍、上下動の `head_bob_scale` 倍、回転なし）になり、LARK・BRAMの出力は変わりません。従来の頭は胴の上下動の3割しか追わず、MAREN・AZURE RONINでは全8方向・全コマで頭の上端の行が同じでした。

`walk.head` があると、頭は首の関節に乗り、胴の左右・前傾・上下動を `follow` の割合で追います。さらに、上下動の深さ（最も低いコマで1）を `lag_frames` コマ遅らせた値で `bob` だけ沈み、`surge` だけ前へ出ます。左右動の割合で `sway` だけ横へずれます。頭は1画素に光線1本で描かれ、目や口は約0.6 pxの1ボクセルです。そのため、頭の移動は従来の頭の静止位置からの差を `snap` 単位（既定1.0＝姿勢ボクセル2個、約1 px）に丸めます。これで顔のボクセルがそのまま平行移動し、目が欠けたりちらついたりしません。半ボクセルの移動や数度の回転では、S方向の目が消えることを確かめています（[頭部連動レポート](research/HEAD_MOTION_VERIFICATION.md)）。実装は [spritestack/rig.py](spritestack/rig.py) の `_walk_head` です。

| キー | 既定 | 内容 |
| --- | --- | --- |
| `follow` | `[1, 1, 1]` | 首の関節の移動（x 左右、y 前後、z 上下）を頭が追う割合 |
| `bob` | 0 | 上下動の最も深いコマで頭がさらに沈む量（モデル単位、0〜1.5） |
| `surge` | 0 | 同じタイミングで頭が前へ出る量（−1〜1） |
| `sway` | 0 | 左右動の最も大きいコマで頭が横へずれる量（−1〜1） |
| `lag_frames` | 0.25 | `bob`・`surge`・`sway`・`nod_deg`・`tilt_deg` が体から遅れるコマ数 |
| `snap` | 1.0 | 従来の頭の静止位置からの差を丸める単位。0で丸めない（顔が欠けるおそれがある） |
| `forward_offset` | 0 | 頭の前後の一定のずれ |
| `yaw_follow`・`pitch_follow` | 0 | 胸のひねり・前傾を頭が追う割合（回転）。48 pxでは顔が欠けやすいので既定は0 |
| `nod_deg`・`tilt_deg` | 0 | 上下動に合わせたうなずき、左右動に合わせた傾き（度、±6以下）。同上 |

頭の上下は胴の上下動（`walk.tuning.root_bob_scale`）と合わせて決めます。胴の沈みが `snap` の半分（0.5単位）を超えれば、頭は肩と一緒に1 px下がります。胴を深く沈められない体形では、`bob` で頭だけを少し沈めます。検証は `research.verify_walk` の `walk.head.motion`（全8方向で頭が動く）、`walk.head.neck`（首との距離）、`walk.head.face`（頭だけを描いたときの目の画素数がコマで変わらない）です。しきい値は `quality.json` の `walk.head` に `min_moving_directions`・`max_neck_offset`・`max_neck_rise`・`features` として書けます。

### 歩行の細い剣の描画（`walk.fine`）

歩行だけに効く任意の設定で、MARENとAZURE RONINが使います。ない場合の描画は変わらず、LARK・BRAM・CRYSTAL MAGEの出力も、静止と攻撃も変わりません。剣を真横に近い向きから見ると、投影した刀身は1画素より細くなり、1画素に光線1本の描画では点線のように途切れます。また、別の面の前にある幅1 pxの刀身は、全体が境界線として最も暗い色になり、暗い服の上で消えて見えます。

`walk.fine` があると、`parts` の部位の周りの画素だけを1画素あたり `rays`×`rays` 本の光線で描き直します（[spritestack/render.py](spritestack/render.py) の `Renderer._fine`）。剣の形が `coverage` 以上覆う画素と、刀身を横切る方向で最も覆われ `line` 以上覆う画素を剣にします。手前の物（握りの手、腕、体）に隠れる光線のほうが多い画素は、これまでどおり手前の物を描きます。1本の光線で剣になる画素はそのまま残します。`seam` を `behind` にすると、剣の画素は暗くせず、剣の後ろの面に境界線を引きます。

| キー | 内容 |
| --- | --- |
| `parts` | 描き直す部位（例 `["sword"]`） |
| `rays` | 1画素の1辺の光線数（2〜8。両体は4） |
| `coverage` | 剣の形がこの割合以上覆う画素を剣にする（両体は0.5） |
| `line` | 刀身を横切る方向で最も覆われた画素を、この割合以上で剣にする（両体は0.25）。省略時は `coverage` だけで決める |
| `seam` | `front`（既定、従来の境界線）か `behind`（剣の後ろの面に境界線を引く） |

2体のE方向で、剣は1本につながり、最も暗い色で描かれる刀身の画素は約半分から1割以下になりました。刀身の幅は11〜16%増えます。手首角度の変更、刀身を太くするモデル変更、覆いの割合だけで決める方法との比較は[剣の修正レポート](research/SWORD_WALK_VERIFICATION.md)にあります。

### 同じ骨格のキャラクターを追加する手順

1. `characters/<名前>/` に設定ファイル、材質NPZ、部位NPZ、歩行・攻撃クリップを置きます。LARKの設定を雛形にし、参照先を新しい資産へ更新します。
2. 体形に合わせて `rig.rest`、部位マスク、装備の取り付けを定義します。既存モーションを試し、接地や手の目標値と描画範囲を必要に応じて調整します。各セルを同じアンカーで切り出せるよう、描画用セルとの差を偶数にします。
3. CLIの `--character` を新しい設定に変えて生成し、8方向の左右、接地、装備、アンカー、テンポを確認します。採用したモデル、設定、モーション、基準PNGを追跡します。

歩行を加える場合は、`--modes walk` で焼いてGIFで8方向を見ながら、`walk.tuning` の倍率で歩幅を脚の長さに合わせ、腕が反対側の脚と逆に振れる符号を選び、布・髪を `walk.secondary` に、頭部の連動を `walk.head` に書きます。`research.verify_walk` でFAILを0にし、`quality.json` の `walk` 節に装備の床・可視画素のしきい値と公開先を書きます。公開するのは `walk.png` と、`metadata.json` の歩行の項目を `{"animations": {"walk": ...}}` として書いた `walk.json` です。静止の `metadata.json` は変えません。

参考画像から静止だけのキャラクターを作る場合の推奨手順です。詳しくは[制作ガイド](research/CHARACTER_CREATION_GUIDE.md)を参照してください。

1. `characters/<名前>/` に `character.json`、`build_model.py`、生成したNPZ、`quality.json` を置きます。個別のベイクスクリプトと検証スクリプトは不要です。
2. `python -m spritestack --character characters/<名前>/character.json --modes idle --out <新しい出力先>` で焼き、拡大図と原寸で見て造形を直します。
3. `python -m research.verify_character --character characters/<名前>/character.json --out <出力先>` でFAILを0にします。WARNINGは内容を確認し、レポートに記録します。
4. 出力を `docs/assets/<名前>/` に置き、`quality.json` の `published` を設定して、公開素材との一致まで検証します。

共通側は二足歩行の関節名と歩行・攻撃の計算方式を共有します。LARKのモデルを作る手続き、材質から部位を割り当てる処理、過去の比較・検証スクリプトは実験ディレクトリにあります。

### BRAMの生成と検証

BRAMは低い身長、幅広い胴、短い四肢を持つドワーフ戦士です。LARKと歩行クリップを共有し、攻撃は元のタイミングと刃の向きを使い、右手の目標だけを肩と腕の長さに合わせています。

~~~powershell
$bram = Join-Path $run 'bram'
& $python -B -m spritestack --character characters/bram/character.json --out $bram
& $python -B -m research.verify_bram $bram
~~~

モデルと部位NPZを別フォルダへ作るには `python characters/bram/build_model.py --out <出力先>`、転用した攻撃クリップを再計算するには `python -m characters.bram.retarget_attack --out <JSONの出力先>` を使います。設計と検証の記録は[Phase 3レポート](research/PHASE3_VERIFICATION.md)を参照してください。

### BRAMのウェイト変形を比較する

Phase 4の試作はBRAMの肩・肘・膝のボクセルを局所的に補間します。標準の `spritestack` コマンドと公開ギャラリーでは剛体版を使います。以下のコマンドで同じモーションを別々に生成し、8方向の比較GIFと計測JSONを出力します。

~~~powershell
$trial = Join-Path $PWD ('.phase1/phase4-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$rigid = Join-Path $trial 'rigid'
$weighted = Join-Path $trial 'weighted'
& $python -B -m spritestack --character characters/bram/character.json --out $rigid
& $python -B -m research.phase4.run --out $weighted
& $python -B -m research.phase4.compare --rigid $rigid --weighted $weighted --out (Join-Path $trial 'comparison')
~~~

[Phase 4の検証結果と比較GIF](research/PHASE4_VERIFICATION.md)

### MARENの生成と検証（画像からの生成実験01）

MARENは参考イラスト1枚から作った青髪の剣士です。参考画像は権利を確認できないため追跡せず、採色範囲の座標と抽出色だけを置いています。標準CLIは剣と盾の斬撃を72 pxセルで焼きます。旧転用クリップは比較用です。旧来の `characters.maren.bake_idle` と `research.verify_maren` も残しており、同じ出力と合否になります。歩行は `--modes walk` で焼いて公開しています。コートの裾は脚に、長髪は胴の動きに付いて揺れ、頭は肩と一緒に上下します。直剣は `walk.fine` で描き、E方向でも途切れません（[歩行レポート](research/WALK_ANIMATION_VERIFICATION.md)、[頭部連動レポート](research/HEAD_MOTION_VERIFICATION.md)、[剣の修正レポート](research/SWORD_WALK_VERIFICATION.md)）。

~~~powershell
$maren = Join-Path $run 'maren'
& $python -B -m spritestack --character characters/maren/character.json --modes idle --out $maren
& $python -B -m research.verify_character --character characters/maren/character.json --out $maren
& $python -B -m research.image_to_character.compare --idle $maren --out (Join-Path $run 'maren-comparison')
~~~

モデルNPZは `python characters/maren/build_model.py --out <出力先>` で作り直せます。参考画像からの色の再抽出、参考画像を並べたローカル比較、評価は[実験01レポート](research/IMAGE_TO_CHARACTER_01.md)を参照してください。

### CRYSTAL MAGEの生成と検証（画像からの生成実験02）

CRYSTAL MAGE（仮名 `crystal_mage`）は参考イラスト1枚から作った魔法使いです。長いローブ、左右と背面へ広がるマント、首のフード、右手の水晶の杖、左手の魔法書を立体化しました。杖と本は、LARKで剣と盾が入る2つの取り付け枠に入れています。参考画像は追跡せず、採色範囲の座標と抽出色だけを置いています。

静止・歩行・杖の詠唱と発動を8方向で公開しています。`--modes idle` は標準の48×48シートと、`comparison_view` に従って同じモデルを4/3倍の画素密度で描いた64×64の比較シートを焼きます。歩行は `--modes walk` で焼き、杖を前に傾けて床から浮かせて持ち、マントと裾が揺れ、頭が控えめに沈みます（[歩行レポート](research/WALK_ANIMATION_VERIFICATION.md)、[頭部連動レポート](research/HEAD_MOTION_VERIFICATION.md)）。攻撃は右手の杖を前へ向け、左手の本を支え、水晶を発動時に発光させます。旧来の `characters.crystal_mage.bake_idle` と `research.verify_crystal_mage` も残しており、同じ出力と合否になります。

~~~powershell
$mage = Join-Path $run 'crystal_mage'
& $python -B -m spritestack --character characters/crystal_mage/character.json --modes idle --out $mage
& $python -B -m research.verify_character --character characters/crystal_mage/character.json --out $mage
& $python -B -m research.image_to_character_02.compare --idle $mage --out (Join-Path $run 'mage-comparison')
~~~

検証は、モデルの再生成、部位のつながりと手・装備の接触、8方向の配置と余白、各コマと再描画の一致、杖と本の左右、公開素材との一致を確認します。モデルNPZは `python characters/crystal_mage/build_model.py --out <出力先>` で作り直せます。参考画像との比較、48×48と64×64の評価、推測で補った背面、マントを動かすための課題は[実験02レポート](research/IMAGE_TO_CHARACTER_02.md)を参照してください。

### AZURE RONINの生成と検証（画像からの生成実験03）

AZURE RONIN（`azure_ronin`）は参考イラスト1枚から作った軽装の剣士です。高い位置で束ねた紺の髪と青い結び紐、鼻から下を覆う濃灰のスカーフと後ろに垂れる端、ベージュの上衣と青い布の2層の裾、濃色のズボン、右手の反りのある片手剣を立体化しました。左手は空で、取り付け枠は剣の1つだけです（16部位）。参考画像は追跡せず、採色範囲の座標と抽出色だけを置いています。

共通化後に作った最初のキャラクターで、キャラクター用のベイク・検証スクリプトはありません。静止は共通CLIの `--modes idle` で48×48の標準と64×64の比較を焼き、`quality.json` の条件で汎用検証します。歩行は `--modes walk` で焼いて公開しています。腰布は脚に、ポニーテールとスカーフの端は胴の動きに付いて揺れ、頭は肩と一緒に上下します。反りのある刀は `walk.fine` で描き、E方向でも途切れません（[歩行レポート](research/WALK_ANIMATION_VERIFICATION.md)、[頭部連動レポート](research/HEAD_MOTION_VERIFICATION.md)、[剣の修正レポート](research/SWORD_WALK_VERIFICATION.md)）。攻撃は刀専用の9コマ・520 msのクリップです。

~~~powershell
$ronin = Join-Path $run 'azure_ronin'
& $python -B -m spritestack --character characters/azure_ronin/character.json --modes idle --out $ronin
& $python -B -m research.verify_character --character characters/azure_ronin/character.json --out $ronin
& $python -B -m research.image_to_character_03.compare --idle $ronin --out (Join-Path $run 'ronin-comparison')
~~~

検証は、モデルの再生成、剣と右手の接触と途切れ、8方向の配置と余白、各コマと再描画の一致、スカーフ・ポニーテール・剣・衣装の層の可視画素、形の存在条件、公開素材との一致を確認します。比較スクリプトは、描画上で刀身が1つながりかも数えます。参考画像との比較、推測で補った背面、共通化で省略できた作業と残った個別判断は[実験03レポート](research/IMAGE_TO_CHARACTER_03.md)を参照してください。

新しい参考画像からキャラクターを作る手順は[制作ガイド](research/CHARACTER_CREATION_GUIDE.md)、実験01・02の比較と共通化の提案は[比較分析](research/IMAGE_TO_CHARACTER_COMPARISON.md)にまとめています。

## 旧コードと同梱成果物の検証

`validate_package.py` と `verify_attack.py` は `output/` に診断を書き込みます。以下の手順では検証用コピーと再生成先を `.phase1/` 内の新規フォルダに作ります。`--out` を指定し、全8方向と装備の可視計測を有効にした既定設定で実行します。

~~~powershell
$run = Join-Path $PWD ('.phase1/run-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$bundled = Join-Path $run 'bundled'
$rebuild = Join-Path $run 'rebuild'
New-Item -ItemType Directory -Path $run -Force | Out-Null
Copy-Item -Recurse -LiteralPath experiments/lark_stage3 -Destination $bundled

& $python "$bundled/validate_package.py"
& $python "$bundled/verify_walk.py"
& $python "$bundled/verify_attack.py"

& $python -B experiments/lark_stage3/generate.py --out $rebuild
& $python "$bundled/validate_package.py" --rebuild $rebuild
& $python research/verify_rebuild.py $rebuild
~~~

各コマンドの終了コードを確認してください。同梱の `validate_package.py --rebuild` は11ファイルをバイト比較します。Windows実測では圧縮や改行などの差でこの検証が失敗しました。共通エンジンの描画回帰は `research/verify_rebuild.py` で判定します。

## ギャラリー

ルートからローカルサーバーを起動し、ブラウザで [LARK ギャラリー](http://127.0.0.1:8000/) を開きます。

~~~powershell
& $python -m http.server 8000 --bind 127.0.0.1 --directory docs
~~~

キャラクター欄でLARK、BRAM、MAREN、CRYSTAL MAGE、AZURE RONINを切り替えられます。3体の追加モーションは静止用メタデータの隣の `walk.json` と `attack.json` から読み込みます。攻撃を選ぶと、同じタイミングの8方向GIFも開けます。CRYSTAL MAGEとAZURE RONINでは「セル解像度」欄で48×48の標準と64×64の比較を切り替えられます。初回はLARKの静止PNGとメタデータを読み込み、各シートは選択時に読み込みます。静止・歩行は48×48、攻撃はMARENが72×72、他が64×64のセルで、Canvasは足元アンカーを揃えます。LARK・BRAMで「攻撃」を選ぶと輪郭改善版を再生します。攻撃モーション欄で同じ方向・倍率・速度のまま振りかぶり版と初期版に切り替えられます。各攻撃はコマごとの時間配分で1回再生します。LARKの素材は `docs/assets/`、BRAMの素材は `docs/assets/bram/`、MARENの素材は `docs/assets/maren/`、CRYSTAL MAGEの素材は `docs/assets/crystal_mage/`、AZURE RONINの素材は `docs/assets/azure_ronin/` にあります。

GitHub Pages の公開元は **main ブランチの `/docs`（Deploy from a branch）** です。[キャラクターギャラリー（GitHub Pages）](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## 今後の研究

次の研究では、共通のモーション目標を体形に合わせて転用できる範囲と、剛体部位の継ぎ目を改善するウェイト変形を検討します。[研究ロードマップ](research/ROADMAP.md)

## ライセンス

`LICENSE` は未設定です。リポジトリのライセンスは所有者の今後の判断事項です。
