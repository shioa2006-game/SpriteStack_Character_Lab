# LARK / THE BLUE SQUIRE — Sprite Stacking 第3段階A

既存の第3段階Aプロジェクトを GitHub リポジトリへ移すためのアーカイブです。前回納品した ZIP の `lark_stage3/` とその配下を保持し、この README だけを追加しています。コード、モデル、モーション、画像、検証結果は変更していません。

## 1. ディレクトリ構成

```text
lark_stage3/
├── README.md
├── generate.py                 # 17部位の関節リグ、2関節IK、再スライス、描画
├── walk_motion.py              # 支持脚・遊脚、歩行時の姿勢制御
├── walk_motion.json            # 歩行タイミング・モーション設定
├── attack_motion.json          # 剣・胴体のポーズと攻撃タイミング
├── requirements.txt
├── compare.py                  # 旧版との比較GIF・比較図・計測JSON
├── package_assets.py           # プレビューの素材埋め込み
├── validate_package.py         # PNG、GIF、アンカー、再生成バイト一致の検査
├── verify_walk.py / verify_attack.py
├── verify_preview.cjs / verify_browser.cjs
├── preview.html / preview_assets.js
├── LARK_Preview_Standalone.html # PNG埋め込み済み・単体で開ける版
├── LARK_第3段階A_技術検証.md
├── output/                     # 新版のPNG・JSON・断面NPZ・診断結果
├── comparisons/                # 旧／新のGIF、8方向比較、原寸図、剣先軌跡
├── qa/                         # モック＋実PNGの描画テスト結果
└── baseline/                   # 旧版の生成・検証コード、モーション、プレビュー
    ├── base/                   # 元モデル、32水平断面、静止絵、静止生成コード
    └── output/                 # 旧スプライトシート、関節図、断面、計測結果
```

元モデルは `baseline/base/knight_materials.npz`、断面の一覧画像は `baseline/base/slices_z00-z31.png`。新版の `output/posed_slices.npz` は各ポーズの水平断面、`posed_part_ids.npz` は部位ID、`rest_part_ids.npz` は元モデルの部位割当、`joints.json` はポーズごとの関節座標です。旧リグ図は `baseline/output/rig.png`。

ZIPを展開した後、`lark_stage3/` の**中身を相対パスごと**移植先のルートへコピーするか、`lark_stage3/` をサブディレクトリとして置きます。特に `baseline/base/` は新版の生成にも必要です。GitHubへの公開・プッシュはこのアーカイブの作成に含まれません。元成果物に `LICENSE` と Node のパッケージ定義・ロックファイルはありません。公開前のライセンス指定、必要な場合のNode依存導入は別作業です。

## 2. Python環境

作業ディレクトリを `lark_stage3/` に移します。今回の確認環境は Linux、Python 3.12.14、NumPy 2.3.5、Pillow 13.0.0 です。`requirements.txt` は当初の範囲指定のままです。

Windows PowerShell（仮想環境を有効化しなくても実行できます）：

```powershell
cd lark_stage3
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate.py --out rebuild
.\.venv\Scripts\python.exe validate_package.py --rebuild rebuild
```

macOS / Linux：

```sh
cd lark_stage3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 3. PNGの再生成

同梱済みの出力を変えずに確認する場合：

```sh
python generate.py --out rebuild
python validate_package.py --rebuild rebuild
```

`rebuild/` に PNG、関節、断面、メタデータ、計測結果が書き出されます。全8方向を生成する既定設定を使ってください。詳細な比較には `--quick` を指定しないでください。環境差による PNG 圧縮などのバイト差と、見た目・RGBAピクセルの差は区別してください。

作業用コピーで通常の配布出力とプレビューを更新する場合：

```sh
python generate.py
python compare.py
python package_assets.py
```

生成済み `LARK_Preview_Standalone.html` は Python やサーバーなしでブラウザから開けます。分割版の `preview.html` と `preview_assets.js` は同じ階層に置きます。キーは矢印／WASD、斬撃は Space／J。旧版／新版、原寸、速度を切替できます。

## 4. テストの実行

```sh
python validate_package.py
python verify_walk.py
python verify_attack.py
```

`validate_package.py` はPNG・GIFを開き、透過、セル内の収まり、攻撃前後の構えを検査します。`--rebuild rebuild` を指定すると別出力先とのバイト一致も検査します。歩行・攻撃スクリプトは足の接地、剣・盾の取り付け、離散姿勢に対する剣身ボクセル中心の交差などを確認します。一部のテストは `output/` または `qa/` の診断ファイルを書き換えるため、元資料を維持する場合は作業用コピーで実行します。

Nodeの任意テスト（作業用コピーで実行）：

```sh
npm install --no-save @napi-rs/canvas playwright
node verify_preview.cjs
node verify_browser.cjs "/path/to/chromium" LARK_Preview_Standalone.html
```

前者は実PNGをCanvasへ描画するモックであり、ブラウザそのものではありません。後者はインストール済みChromiumへのパスを渡し、一時的なローカルHTTPサーバー経由で起動します。Windows は Chromium 互換ブラウザ実行ファイルのパスに読み替えてください。このアーカイブには成功した実ブラウザテストの結果はありません。

## 5. 実装済み

- 元の32層モデルを17部位に分け、関節ごとの剛体変換と腕・脚の2関節IKでポーズを作り、水平断面へ再サンプリング。右手の剣、左手の盾を維持。
- 8方向の静止・歩行・斬撃。静止・歩行は48×48セル、足元基準点(24,40)。斬撃は余白込み64×64セル、基準点(32,48)。斬撃セルが大きくてもキャラクターの縮尺は同じ。
- 静止は1行×8列。歩行・斬撃は行方向が S / SW / W / NW / N / NE / E / SE、列が順番通りの時間コマ。歩行6コマ・9fps・1コマ1.9モデル単位推奨。斬撃9コマ・可変表示時間、計800ms。厳密な切り出しや時間は `output/metadata.json` を参照。
- 生成済みPNGを使う操作プレビュー、旧新比較、速度・タイミング切替、足元基準点表示。実行時の積層計算は不要。

## 6. 今後の課題

- **ウェイト変形は未実装。** 現状は部位ごとの剛体変換。肘・膝・肩の継ぎ目をなじませるためのウェイト付き変形は、関節付近のボクセル割当と低解像度での見え方を含め、今後比較する。
- NWの斬撃は剣先中心で読みにくく、Wは一部の主斬撃や奥の足が隠れる。停止・反転の遷移、6コマ歩行の保持中の見かけ上の滑りも要検証。
- 実機のブラウザで入力から最初に変わる姿勢、主斬撃、次の入力が通る時刻を測る。本番ゲームの当たり判定・操作感、連続補間時の武器と身体の交差は未確認。

## 7. 再生成・収録確認

**再生成に成功。** 元ZIPを別の場所へ展開し、収録ソースと入力だけで8方向を再生成しました。添付済み出力と **11ファイル（PNG 5点、JSON 3点、NPZ 3点）がバイト単位で一致**。歩行・攻撃の120コマ、既存GIF 11点、歩行・攻撃の個別診断、実PNGを使うNode模擬プレビューも検査を通過しました。Chromiumの実ブラウザ試験、Windows／macOS上での再生成は今回未確認です。

元ZIPの全79ファイルとパスを保持し、新ZIPではこの README のみを加えました。

今回指定された収録カテゴリに、前回成果物からの欠落は見つかっていません。実装されていないウェイトデータや、実行未確認のブラウザテスト結果を追加したものではありません。
