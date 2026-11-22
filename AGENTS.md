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
10. 参考画像から作ったMARENは `characters/maren/` にある。参考画像はコミットせず、採色範囲の座標、抽出色、配色の出典だけを追跡する。静止8方向は `python -m spritestack --character characters/maren/character.json --modes idle --out <新しい出力先>` で焼き、`python -m research.verify_character --character characters/maren/character.json --out <出力先>` で検査する。旧来の `characters.maren.bake_idle` と `research.verify_maren` も同じ出力・合否になる。全モードの標準CLIは攻撃の振りかぶりが64 pxセルを越えて止まる。歩行は項目15の方法で公開している。[実験01レポート](research/IMAGE_TO_CHARACTER_01.md)
11. 参考画像から作った魔法使いCRYSTAL MAGEは `characters/crystal_mage/` にある。剣・盾の取り付け枠に杖（右手）と本（左手）を入れる。参考画像はコミットしない。静止は `python -m spritestack --character characters/crystal_mage/character.json --modes idle --out <新しい出力先>` で48×48と64×64の比較を焼き（64は `comparison_view`）、`python -m research.verify_character --character characters/crystal_mage/character.json --out <出力先>` で検査する。旧来の `characters.crystal_mage.bake_idle` と `research.verify_crystal_mage` も同じ出力・合否になる。48 pxセルではW方向の杖頭が上端1 pxに達するため、杖や頭を高くしない。歩行は項目15の方法で公開している（杖は前へ傾けて床から浮かせ、W方向の上端を越えないよう手を上げない）。攻撃は読込用にLARKのクリップを参照するだけで、標準CLIは攻撃で杖が姿勢ボリュームを出て止まる。[実験02レポート](research/IMAGE_TO_CHARACTER_02.md)
12. 新しい参考画像からキャラクターを作るときは、画像分析から公開までを [制作ガイド](research/CHARACTER_CREATION_GUIDE.md) の手順で進める。実験01・02で繰り返した問題の設計規則と、48 pxセルの高さの予算の式を先に適用する。共通化の提案は [比較分析](research/IMAGE_TO_CHARACTER_COMPARISON.md) にある。提案1（汎用検証）と提案2（静止だけのベイク）は実装済み、ほかは未実装。共通化後の最初の例は実験03のAZURE RONIN（`characters/azure_ronin/`）。
13. 静止だけのキャラクターは、個別のベイク・検証スクリプトを作らず、`--modes idle`（比較用セルは `character.json` の `comparison_view` と `--cells`）と `research.verify_character` を使う。キャラクター固有の条件（装備の役割、可視画素の下限と方向、存在条件、公開先、生成コード）は `characters/<名前>/quality.json` に書き、共通の検証にキャラクター名の分岐を入れない。FAILは0にする。WARNING（例：他部位に覆われた部位の切れ端）は内容を確認して記録し、検証を通すためだけに既存モデルを直したり、WARNINGをFAILに変えたりしない。`spritestack/bake.py` の静止ベイクを変えたら、MAREN・CRYSTAL MAGEの出力が公開PNG・JSONと一致することを確認する。`research/verify_character.py` を変えたら `python -m research.verify_character_selftest` を実行する。[共通化の検証レポート](research/SHARED_IDLE_BAKE_AND_VALIDATION.md)
14. 参考画像から作った剣士AZURE RONINは `characters/azure_ronin/` にある。装備は右手の反りのある剣1つで、取り付け枠は1つ（16部位）。参考画像はコミットしない。静止は `python -m spritestack --character characters/azure_ronin/character.json --modes idle --out <新しい出力先>` で48×48と64×64の比較を焼き、`python -m research.verify_character --character characters/azure_ronin/character.json --out <出力先>` で検査する。個別のベイク・検証スクリプトはない。ポニーテールは髪と同じ色の別材質 `ponytail`（別の陰影グループ）で、可視画素の規則と頭との段差線に使う。刀身は厚さ0.9単位より薄くすると、描画で途切れる（`research.image_to_character_03.compare` の `blade_pieces` が1であること）。歩行は項目15の方法で公開している。攻撃は読込用にLARKのクリップを参照するだけで、公開しない。[実験03レポート](research/IMAGE_TO_CHARACTER_03.md)
15. MAREN・CRYSTAL MAGE・AZURE RONINの歩行は、LARKの共通歩行クリップを参照したまま、`character.json` の `walk.tuning`（歩幅などの倍率、左右別の腕の値）と `walk.secondary`（布の `skirt`、髪・マント・スカーフの端の `pendulum`）だけで体格と衣装に合わせる。キャラクター用の歩行システムやスクリプトを作らない。共通処理は `spritestack/secondary.py` と `spritestack/rig.py` の `walk_clip`。これらのキーがないLARK・BRAMの出力は変わらない。焼くのは `python -m spritestack --character <設定> --modes walk --out <新しい出力先>`、検査は `python -m research.verify_walk --character <設定> --out <出力先>`（しきい値は `quality.json` の `walk` 節）、比較は `python -m research.walk.compare --after <出力の親> --out <出力先>`。公開は `docs/assets/<名前>/` の `walk.png` と `walk.json` で、静止の `metadata.json` は変えない。共通クリップは腕が同じ側の脚と一緒に前へ出るので、3体は `arm_swing_scale` の符号を反転している。LARK・BRAMのクリップと設定は変えない。`spritestack/secondary.py` やベイクを変えたら、3体の歩行が公開PNGと一致すること、LARK・BRAMが基準と一致することを確認する。[歩行レポート](research/WALK_ANIMATION_VERIFICATION.md)
16. 歩行時の頭部の連動は `character.json` の `walk.head` が標準で、新しいキャラクターにも書く。共通処理は `spritestack/rig.py` の `_walk_head`。頭は首に乗って胴の動きを `follow` の割合で追い、上下動の深さに合わせて `bob`・`surge`、左右動に合わせて `sway` だけずれる。移動は従来の頭の静止位置からの差を `snap`（既定1.0単位）に丸める。48 pxでは目や口が1ボクセル（約0.6 px）しかなく、半ボクセルの移動や数度の回転で目が消えるため、回転キー（既定0）と小さい `snap` は使わない。頭の上下は主に `walk.tuning.root_bob_scale` で胴と一緒に作る。`walk.head` がないLARK・BRAMは従来の頭のままで、出力は変わらない。`research.verify_walk` の `walk.head.motion`・`walk.head.neck`・`walk.head.face`（頭だけを描いた目の画素数）でFAILを0にし、比較は `python -m research.head.compare --after <出力の親> --out <出力先>`。変更前の公開歩行は `research/head/baseline/` に保持する。[頭部連動レポート](research/HEAD_MOTION_VERIFICATION.md)
