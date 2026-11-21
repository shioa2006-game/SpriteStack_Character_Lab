# SpriteStack Character Lab 開発ガイド

## 目的

AIを活用し、ゲーム用ピクセルアートキャラクターの自動生成を研究する。中心技術は Sprite Stacking × Skeletal Rig × Weight Deformation × PNG Baking。出力はブラウザゲームで使える透過PNGスプライトシートとする。

## 現在の実装

- `generate.py` は NumPy と Pillow を使う。元モデルは材質IDを `slices` 配列（Z, Y, X の順に32×60×80、`uint8`）に保持する NPZ。LARK 固有の関節位置と17部位を使い、腕・脚を2関節IKで解き、部位ごとの剛体変換から0.5単位のボクセルへ再スライスする。[生成コード](experiments/lark_stage3/generate.py) · [元モデル](experiments/lark_stage3/baseline/base/knight_materials.npz)
- 歩行は `walk_motion.py` と `walk_motion.json`、攻撃は `attack_motion.json` のポーズとコマ時間で定義する。関節座標は `output/joints.json` に出力される。ウェイト変形と複数キャラクターの共通生成は未実装。側面・背面の斬撃の視認性、停止・旋回、実ゲームでの操作感は検証課題。
- カメラは正投影、仰角24°、1.19 px/モデル単位。方向順は **S、SW、W、NW、N、NE、E、SE**。静止は元シートを継承し、歩行・攻撃は方向別に描画して Pillow でRGBA PNGにまとめる。配置の契約は[出力メタデータ](experiments/lark_stage3/output/metadata.json)にある。

| モーション | セル | アンカー (x, y) | 配置 |
| --- | --- | --- | --- |
| 静止 | 48×48 | (24, 40) | 1行に8方向 |
| 歩行 | 48×48 | (24, 40) | 方向が行、時間が列。6コマ、9 fps |
| 攻撃 | 64×64 | (32, 48) | 方向が行、時間が列。9コマ、計800 ms |

## 開発と検証

1. 同じ立体モデルから各方向を生成し、水平反転で方向を代用しない。武器・盾の解剖学的な左右と、静止・歩行・攻撃の方向順・アンカーを維持する。LARK の剣は右手、盾は左手。
2. 元モデル、モーション、生成コード、正式なPNG、基準画像を一緒に追跡する。既存成果と再生成性を優先し、変更前の基準画像を保持する。
3. エンジン変更時は既存キャラクターを `generate.py --out` で別フォルダに再生成し、基準と寸法、RGBA、方向順、アンカー、コマ数を比較する。ファイルのバイト差も記録する。
4. `validate_package.py`、`verify_walk.py`、`verify_attack.py` は出力保全のため作業用コピーで実行する。`research/verify_rebuild.py` で再生成画像を比較する。技術的な合否と動作の自然さを別に評価し、仕様・不具合・未確認事項を分けて記録する。[実行手順](README.md#同梱成果物の検証と再生成)
5. 共通エンジンと個別キャラクターデータを分離する方向で開発し、新規キャラクターでは共通モーションの再利用を先に検証する。未依頼の大規模なリファクタリングを行わず、重要な設計変更の理由と影響範囲を記録する。[研究ロードマップ](research/ROADMAP.md)
