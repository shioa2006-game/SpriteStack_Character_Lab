# SpriteStack Character Lab

AIを活用したゲーム用ピクセルアートキャラクターの自動生成を研究するリポジトリです。中心技術は **Sprite Stacking × Skeletal Rig × Weight Deformation × PNG Baking**。ブラウザゲームで使える透過PNGスプライトシートの生成を目指します。

## 現在の実装状況

| 状態 | 対象 |
| --- | --- |
| 実装済み | LARK の32層モデル、17部位の剛体リグ、腕・脚の2関節IK、静止・歩行・攻撃の8方向PNG、Canvasギャラリー |
| 未実装 | ウェイト変形、別の体形や装備を扱う共通生成エンジン、キャラクターの自動生成 |
| 検証課題 | 側面・背面の斬撃の視認性、停止や旋回時の見え方、実ゲーム組み込み時の操作感 |

方向順、セル寸法、アンカー、フレーム配置は[出力メタデータ](experiments/lark_stage3/output/metadata.json)に記録されています。開発時の基準は [AGENTS.md](AGENTS.md) を参照してください。

## ディレクトリ構成

| 場所 | 内容 |
| --- | --- |
| [experiments/lark_stage3/](experiments/lark_stage3/) | ZIP から移植したコード・モデル・検証スクリプト・元のプレビュー |
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

## 同梱成果物の検証と再生成

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

各コマンドの終了コードを確認してください。同梱の `validate_package.py --rebuild` は11ファイルをバイト比較します。Windows 実測では圧縮や改行などの差でこの検証が失敗しました。`research/verify_rebuild.py` は5点すべての PNG について寸法、デコード後の RGBA、ファイルバイトを個別に報告し、方向順・アンカー・フレーム数を含む JSON を照合します。

## ギャラリー

ルートからローカルサーバーを起動し、ブラウザで [LARK ギャラリー](http://127.0.0.1:8000/) を開きます。

~~~powershell
& $python -m http.server 8000 --bind 127.0.0.1 --directory docs
~~~

初回は静止 PNG とメタデータを読み込みます。歩行・攻撃のシートは、該当するモーションの初回選択時に読み込みます。静止・歩行は48×48、攻撃は64×64のセルで、Canvas は足元アンカーを揃えて表示します。攻撃は既存のコマごとの時間配分で1回再生し、ボタンで再試行できます。`docs/assets/` の4ファイルは `output/` の対応ファイルのコピーです。

GitHub Pages の公開元は **main ブランチの `/docs`（Deploy from a branch）** です。[LARK ギャラリー（GitHub Pages）](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## 今後の研究

LARK の再生成結果を回帰基準に、描画と装備の可視計測の所要時間を切り分け、キャラクター設定と共通エンジンの境界を整えます。異なる体形へのモーション転用、ウェイト変形、装備バリエーション、ゲームへの組み込みも研究対象です。[研究ロードマップ](research/ROADMAP.md)

## ライセンス

`LICENSE` は未設定です。リポジトリのライセンスは所有者の今後の判断事項です。
