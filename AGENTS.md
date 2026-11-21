# SpriteStack Character Lab 開発ガイド

## 目的

AIを活用し、ゲーム用ピクセルアートキャラクターの自動生成を研究する。中心技術は Sprite Stacking × Skeletal Rig × Weight Deformation × PNG Baking。出力はブラウザゲームで使える透過PNGスプライトシートとする。

## 現在の実装

- `spritestack/` は NumPy と Pillow を使い、設定読込、2関節IK、剛体変形、再スライス、正投影、RGBAベイクを担当する。`characters/lark/character.json` に材質と部位のNPZ参照、関節座標、装備の取り付け、カメラ、モーション調整値を置く。材質 `slices` と部位 `parts` は同形状の Z/Y/X 配列。[共通コード](spritestack/) · [LARK設定](characters/lark/character.json)
- 対象は二足歩行の共通リグ。LARKとBRAMは装備込み17部位を0.5単位のボクセルへ再スライスする。標準の出力は剛体版。BRAMのウェイト変形はPhase 4の実験用コマンドから実行する。旧生成コードとLARKの基準PNGは実験ディレクトリに保持する。[実験資産](experiments/lark_stage3/) · [Phase 4レポート](research/PHASE4_VERIFICATION.md)
- LARKのカメラは仰角24°、1.19 px/モデル単位。方向順は **S、SW、W、NW、N、NE、E、SE**。配置・タイミングの契約はメタデータにある。[基準メタデータ](experiments/lark_stage3/output/metadata.json)

| モーション | セル | アンカー (x, y) | 配置 |
| --- | --- | --- | --- |
| 静止 | 48×48 | (24, 40) | 1行に8方向 |
| 歩行 | 48×48 | (24, 40) | 方向が行、時間が列。6コマ、9 fps |
| 攻撃 | 64×64 | (32, 48) | 方向が行、時間が列。9コマ、計800 ms |

## 開発と検証

1. 同じ立体モデルから各方向を生成し、水平反転で方向を代用しない。武器・盾の解剖学的な左右と、静止・歩行・攻撃の方向順・アンカーを維持する。LARK の剣は右手、盾は左手。
2. 元モデル、モーション、生成コード、正式なPNG、基準画像を一緒に追跡する。既存成果と再生成性を優先し、変更前の基準画像を保持する。
3. エンジン変更時は `python -m spritestack --character characters/lark/character.json --out <新しい出力先>` でLARKを再生成する。`research/verify_rebuild.py` で寸法、RGBA、方向順、アンカー、コマ数、タイミングを比較する。描画の合否はデコード後のRGBAを使う。[再生成手順](README.md#共通エンジンでの生成)
4. `validate_package.py`、`verify_walk.py`、`verify_attack.py` は作業用コピーで実行する。技術的な合否と動作の自然さを別に評価し、仕様・不具合・未確認事項を分けて記録する。[旧コードの検証手順](README.md#旧コードと同梱成果物の検証)
5. 同じ骨格のキャラクターは `characters/<名前>/` に設定、材質・部位NPZ、モーションクリップを追加する。元の関節名と部位ID契約を守り、先に共通モーションの接地と装備の向きを確認する。未依頼の大規模なリファクタリングを行わず、設計変更の理由と影響範囲を記録する。[設定仕様と追加手順](README.md#キャラクター設定-v1)
6. BRAMの歩行はLARKと同じクリップを参照する。攻撃は `characters.bram.retarget_attack` で右手の目標だけを転用する。調整時は `python -m research.verify_bram <出力先>` で接地、装備の接続、部位の残存、PNGを検査し、見た目も8方向で確認する。[Phase 3レポート](research/PHASE3_VERIFICATION.md)
7. ウェイト試作は別フォルダへ焼き出し、`research.phase4.compare` で剛体版との関節座標、足・手・装備のボクセル、8方向のPNGを比較する。既存の公開PNGを回帰基準に使う。[実行手順](README.md#bramのウェイト変形を比較する)
8. 振りかぶり攻撃は `research/overhead/clip.json` を両体形へ転用する。編集後は `research.overhead.compare` で8方向の剣の見え方、キー間の接地と剣身の交差、静止・歩行のRGBAを照合する。旧攻撃のPNGとクリップを比較基準に保持する。[攻撃品質レポート](research/OVERHEAD_ATTACK_VERIFICATION.md)
9. 公開中の輪郭改善版は `research/blade/clip.json` を両体形へ適用する。`wrist_roll` は刃の軸回りの手首角度（度）で、省略時は0。剣身の見え方は `research.blade.compare` で投影軸と可視画素を照合し、W・E・NW・SEの拡大図と8方向の再生を確認する。[輪郭改善レポート](research/BLADE_REFINEMENT_VERIFICATION.md)
10. 参考画像から作ったMARENは `characters/maren/` にある。参考画像はコミットせず、採色範囲の座標、抽出色、配色の出典だけを追跡する。静止8方向は `python -m characters.maren.bake_idle --out <新しい出力先>` で焼き、`python -m research.verify_maren <出力先>` でモデル再生成、配置、余白、左右、公開PNGとの一致を確認する。標準CLIは攻撃の振りかぶりが64 pxセルを越えて止まる。[実験01レポート](research/IMAGE_TO_CHARACTER_01.md)
11. 参考画像から作った魔法使いCRYSTAL MAGEは `characters/crystal_mage/` にある。剣・盾の取り付け枠に杖（右手）と本（左手）を入れる。参考画像はコミットしない。静止は `python -m characters.crystal_mage.bake_idle --out <新しい出力先>` で48×48と64×64の比較を焼き、`python -m research.verify_crystal_mage <出力先>` でモデル再生成、つながり、手と装備の接触、再描画との一致、左右、公開PNGを確認する。48 pxセルではW方向の杖頭が上端1 pxに達するため、杖や頭を高くしない。歩行・攻撃は読込用にLARKのクリップを参照するだけで、標準CLIは攻撃で杖が姿勢ボリュームを出て止まる。[実験02レポート](research/IMAGE_TO_CHARACTER_02.md)
