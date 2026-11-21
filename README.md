# SpriteStack Character Lab

AIを活用したゲーム用ピクセルアートキャラクターの自動生成を研究するリポジトリです。中心技術は **Sprite Stacking × Skeletal Rig × Weight Deformation × PNG Baking**。ブラウザゲームで使える透過PNGスプライトシートの生成を目指します。

## 現在の実装状況

| 状態 | 対象 |
| --- | --- |
| 実装済み | 設定から二足歩行モデルを読み込む共通ベイク、腕・脚の2関節IK、静止・歩行・攻撃の8方向PNG、静止だけのベイク（比較用セル付き）、設定ファイルで条件を変えられる汎用品質検証、Canvasギャラリー |
| 検証済み | LARKの基準PNGとのRGBA・配置・再生時間の一致。ドワーフ戦士BRAMへの共通モーション転用 |
| 試作 | BRAMの肩・肘・膝のウェイト変形。実験用コマンドで検証。参考画像1枚から作ったMARENと、魔法使いCRYSTAL MAGEの静止8方向（48×48と64×64の比較） |
| 未実装 | 量産用のウェイト変形、別の骨格構成、画像からの生成の自動化（採色範囲・形状寸法の自動決定）、MARENの歩行・攻撃、CRYSTAL MAGEの歩行と杖の攻撃、マント・裾の従属部位 |
| 検証課題 | 他の体形への転用範囲、側面・背面の斬撃の視認性、停止・旋回、実ゲームでの操作感 |

方向順、セル寸法、アンカー、フレーム配置は[出力メタデータ](experiments/lark_stage3/output/metadata.json)に記録されています。開発時の基準は [AGENTS.md](AGENTS.md) を参照してください。

## ディレクトリ構成

| 場所 | 内容 |
| --- | --- |
| [spritestack/](spritestack/) | 共通CLI、設定読込、二足歩行リグ、ボクセル再スライス、描画、ベイク |
| [characters/lark/](characters/lark/) | LARKのモデル・モーション参照、材質、リグ、表示と計測の設定 |
| [characters/bram/](characters/bram/) | BRAMの独立モデル、部位マスク、設定、攻撃目標の転用手順 |
| [characters/maren/](characters/maren/) | 参考画像から作ったMARENのモデル生成コード、NPZ、設定、品質設定、採色範囲と抽出色、配色の出典、旧来の静止のベイク |
| [characters/crystal_mage/](characters/crystal_mage/) | 参考画像から作った魔法使いCRYSTAL MAGEのモデル生成コード、NPZ、設定（64×64の比較用の `comparison_view` を含む）、品質設定、採色範囲と抽出色、配色の出典、旧来の静止のベイク |
| [experiments/lark_stage3/](experiments/lark_stage3/) | ZIPから移植した基準コード・モデル・検証スクリプト・元のプレビュー |
| [experiments/lark_stage3/baseline/](experiments/lark_stage3/baseline/) | 旧版と、再生成に必要な元モデル・水平断面 |
| [experiments/lark_stage3/output/](experiments/lark_stage3/output/) | 8方向 PNG、関節・計測 JSON、水平断面・部位 ID の NPZ |
| [experiments/lark_stage3/comparisons/](experiments/lark_stage3/comparisons/) | 旧版との比較 GIF・PNG と計測結果 |
| [docs/](docs/) | 生成済み PNG を表示する GitHub Pages 用ギャラリー |
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
| `walk` | 既存形式の歩行クリップ、セル、歩幅に合わせる支持足・頭・腕の調整値。コマ別配列を `poses` に揃え、左右の接地は循環する連続区間、遊脚配列は接地外のコマ数に揃える |
| `attack` | 既存形式の攻撃クリップ、セル、踏み出す側・主手・装備の軸・反対側の腕の調整値。非空キーに足と手の目標値、主手に合わせた `hand_R`/`hand_L` と `elbow_pole_R`/`elbow_pole_L` を指定する。`shield_delta` は反対側の手の相対オフセット。`wrist_roll` は刃の軸回りの手首角度（度、省略時は0）。`keys`、`poses`、`durations_ms` の長さを揃える |
| `measurements` | `lowest_z` は計測名と材質IDリスト、`visibility` は計測名と部位名・材質IDリストの組。計測項目がなければ空オブジェクトを指定できる |

### 同じ骨格のキャラクターを追加する手順

1. `characters/<名前>/` に設定ファイル、材質NPZ、部位NPZ、歩行・攻撃クリップを置きます。LARKの設定を雛形にし、参照先を新しい資産へ更新します。
2. 体形に合わせて `rig.rest`、部位マスク、装備の取り付けを定義します。既存モーションを試し、接地や手の目標値と描画範囲を必要に応じて調整します。各セルを同じアンカーで切り出せるよう、描画用セルとの差を偶数にします。
3. CLIの `--character` を新しい設定に変えて生成し、8方向の左右、接地、装備、アンカー、テンポを確認します。採用したモデル、設定、モーション、基準PNGを追跡します。

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

MARENは参考イラスト1枚から作った青髪の剣士です。参考画像は権利を確認できないため追跡せず、採色範囲の座標と抽出色だけを置いています。全モードの標準CLIは転用した攻撃が64 pxセルを越えて止まるため、静止8方向は `--modes idle` で焼きます。旧来の `characters.maren.bake_idle` と `research.verify_maren` も残しており、同じ出力と合否になります。

~~~powershell
$maren = Join-Path $run 'maren'
& $python -B -m spritestack --character characters/maren/character.json --modes idle --out $maren
& $python -B -m research.verify_character --character characters/maren/character.json --out $maren
& $python -B -m research.image_to_character.compare --idle $maren --out (Join-Path $run 'maren-comparison')
~~~

モデルNPZは `python characters/maren/build_model.py --out <出力先>` で作り直せます。参考画像からの色の再抽出、参考画像を並べたローカル比較、評価は[実験01レポート](research/IMAGE_TO_CHARACTER_01.md)を参照してください。

### CRYSTAL MAGEの生成と検証（画像からの生成実験02）

CRYSTAL MAGE（仮名 `crystal_mage`）は参考イラスト1枚から作った魔法使いです。長いローブ、左右と背面へ広がるマント、首のフード、右手の水晶の杖、左手の魔法書を立体化しました。杖と本は、LARKで剣と盾が入る2つの取り付け枠に入れています。参考画像は追跡せず、採色範囲の座標と抽出色だけを置いています。

公開するのは静止8方向だけです。`--modes idle` は標準の48×48シートと、`comparison_view` に従って同じモデルを4/3倍の画素密度で描いた64×64の比較シートを焼きます。歩行・攻撃の設定は読込のためにLARKのクリップを参照するだけで、焼いていません。全モードの標準CLIは、剣の攻撃の姿勢で杖が姿勢ボリュームを出て止まります。旧来の `characters.crystal_mage.bake_idle` と `research.verify_crystal_mage` も残しており、同じ出力と合否になります。

~~~powershell
$mage = Join-Path $run 'crystal_mage'
& $python -B -m spritestack --character characters/crystal_mage/character.json --modes idle --out $mage
& $python -B -m research.verify_character --character characters/crystal_mage/character.json --out $mage
& $python -B -m research.image_to_character_02.compare --idle $mage --out (Join-Path $run 'mage-comparison')
~~~

検証は、モデルの再生成、部位のつながりと手・装備の接触、8方向の配置と余白、各コマと再描画の一致、杖と本の左右、公開素材との一致を確認します。モデルNPZは `python characters/crystal_mage/build_model.py --out <出力先>` で作り直せます。参考画像との比較、48×48と64×64の評価、推測で補った背面、マントを動かすための課題は[実験02レポート](research/IMAGE_TO_CHARACTER_02.md)を参照してください。

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

キャラクター欄でLARK、BRAM、MAREN、CRYSTAL MAGEを切り替えられます。MARENとCRYSTAL MAGEは静止8方向だけを公開し、歩行・攻撃のボタンは無効になります。CRYSTAL MAGEでは「セル解像度」欄で48×48の標準と64×64の比較を切り替えられます。初回はLARKの静止PNGとメタデータを読み込み、各シートは選択時に読み込みます。静止・歩行は48×48、攻撃は64×64のセルで、Canvasは足元アンカーを揃えます。「攻撃」を選ぶと輪郭改善版を再生します。攻撃モーション欄で同じ方向・倍率・速度のまま振りかぶり版と初期版に切り替えられます。各攻撃はコマごとの時間配分で1回再生します。LARKの素材は `docs/assets/`、BRAMの素材は `docs/assets/bram/`、MARENの素材は `docs/assets/maren/`、CRYSTAL MAGEの素材は `docs/assets/crystal_mage/` にあります。

GitHub Pages の公開元は **main ブランチの `/docs`（Deploy from a branch）** です。[キャラクターギャラリー（GitHub Pages）](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## 今後の研究

次の研究では、共通のモーション目標を体形に合わせて転用できる範囲と、剛体部位の継ぎ目を改善するウェイト変形を検討します。[研究ロードマップ](research/ROADMAP.md)

## ライセンス

`LICENSE` は未設定です。リポジトリのライセンスは所有者の今後の判断事項です。
