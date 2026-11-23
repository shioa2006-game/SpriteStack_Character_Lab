# Phase 2　正式サンプルの整理と回帰検証

公開ギャラリーと `characters/` の制作対象を **MAREN・CRYSTAL MAGE・AZURE RONIN** の3体に統一した。新しいキャラクターの体格、配色、装備、モーションを決めるときもこの3体を参照する。比較基準は整理直前の [Phase 1 の公開ツリー](https://github.com/shioa2006-game/SpriteStack_Character_Lab/tree/48a8ae1/docs/assets)。[公開ギャラリー](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## 削除・移動したもの

旧ギャラリーからLARK・BRAMの選択肢、表示設定、旧攻撃3版の切り替え、専用のPNG・JSON計16ファイルを外した。公開側に残る31ファイルはすべて正式3体の素材で、整理前とバイト単位で一致する。

| 対象 | 整理後の場所・扱い | 理由 |
| --- | --- | --- |
| LARK初期版の静止・歩行・攻撃PNGとメタデータ（4点） | 公開用の重複を削除し、[元の同梱出力](../experiments/lark_stage3/output/)に一本化 | デコード後の画像とメタデータが一致し、旧コードと共通エンジンの回帰基準を兼ねられる |
| BRAM初期版の同じ4点 | [BRAMの回帰基準](../experiments/bram/baseline/)へ移動 | 低い体格での剛体ベイク、ウェイト試作、装備接続の比較に使う |
| 両体の振りかぶり版PNG・JSON（各2点） | [振りかぶり版の基準](overhead/baseline/)へ移動 | 輪郭改善前の独立した比較対象を保存する |
| 両体の輪郭改善版PNG・JSON（各2点） | 公開用出力を削除。[クリップ](blade/clip.json)、比較コード、計測結果、研究レポートを保存 | 再生成した両体のRGBAと攻撃メタデータが旧公開版に一致した |
| LARK・BRAMの設定とモデル | [LARKの共通エンジン用設定](../experiments/lark/)、[元の同梱パッケージ](../experiments/lark_stage3/)、[BRAMのモデル・生成コード・検証用設定](../experiments/bram/) | 異なる体格、旧エンジンとの互換性、ウェイト変形を引き続き検査できる |
| 正式3体の歩行 | [共通歩行クリップ](../motions/walk.json)を3体のモデル設定・品質設定から直接参照 | 6コマの内容は同梱版と同一。LARKの元パッケージには、それ単体で再現するため当時のコピーを保存した |
| MAREN初期実験の攻撃転用 | [初期の生成結果](image_to_character/attack_motion.json)を研究側へ移動。重複した生成コードを[研究用の転用処理](../experiments/bram/retarget_attack.py)に統合 | BRAMと初期MARENの両方を再現できる。現行MARENの攻撃は専用の `slash.json` を使う |

共通リグ、IK、再スライス、ベイク、頭部連動、髪・布の揺れ、刀身描画は既存の `spritestack/` を使用する。検証側では手と装備が接するボクセル面の数え方を共有し、正式3体の攻撃・歩行検証からBRAM専用検証への依存を外した。

## 正式3体の検証結果

空の出力先で各モデルをベイクした。各体につき静止8コマ、歩行48コマ、攻撃72コマの合計128コマをPhase 1と照合した。PNGは寸法とデコード後のRGBA、JSONは方向順・セル・足元アンカー・タイミングを含む内容、攻撃GIFは各フレームと表示時間を確認した。CRYSTAL MAGE・AZURE RONINの比較用64×64静止も各8方向で一致した。

| キャラクター | 主要128コマ・メタデータ・攻撃GIF | 静止の検証 | 歩行の検証 | 攻撃の検証 |
| --- | --- | --- | --- | --- |
| MAREN | 一致 | PASS 32、警告1 | PASS 16 | 97姿勢合格、最小接触面数は剣27・盾21 |
| CRYSTAL MAGE | 一致 | PASS 43、警告1 | PASS 15、警告1 | 97姿勢合格、杖10・本22 |
| AZURE RONIN | 一致 | PASS 63 | PASS 16 | 97姿勢合格、刀15 |

全モードでFAILは0。静止の警告は他部位に覆われて分かれた同一部位の断片（MAREN 1個、CRYSTAL MAGE 4個）。歩行の警告はCRYSTAL MAGEのSW・SEで目の画素数が変動する既知のもの。いずれもPhase 1と同じ画素で再現する。

ブラウザではMARENが初期表示され、選べるキャラクターが3体であることを確認した。全方向・全コマのCanvas表示をシートと照合し、歩行のループ、攻撃の終了・再生、速度・拡大率、攻撃GIF・比較GIFのデコードと総時間、対応する2体の48／64切り替えを確認した。幅320 pxの表示でも横スクロールは発生しなかった。

### 再検証の入口

以下をリポジトリのルートで実行する。`$runDir` には新しい作業用フォルダを指定する。全モード出力と公開用の静止メタデータは構成が異なるため、静止専用ベイクも別に作る。

```powershell
$runDir = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
foreach ($name in 'maren', 'crystal_mage', 'azure_ronin') {
    $config = "characters/$name/character.json"
    $bake = Join-Path $runDir $name
    $idle = Join-Path $runDir "$name-idle"
    python -m spritestack --character $config --out $bake
    python -m research.verify_walk --character $config --out $bake
    python -m research.verify_attack --character $config --out $bake --published "docs/assets/$name"
    python -m spritestack --character $config --modes idle --out $idle
    python -m research.verify_character --character $config --out $idle
}
```

旧資産ではLARKの基準との再生成比較、BRAMのモデル・接地・装備の検査、BRAMの剛体／ウェイト比較、両体の振りかぶり版と輪郭改善版の再生成・比較が通った。初期MARENとBRAMの転用攻撃も保存したJSONと一致した。正式3体の旧静止比較、歩行比較、意図的に欠陥を入れる検証器のセルフテスト20件を再実行した。[旧エンジンの再生成手順とウェイト比較](../docs/TECHNICAL_DESIGN.md#研究用の回帰)

## Phase 3に引き継ぐ文書課題

- 制作ガイドの静止中心の手順から、参考画像の特徴抽出、造形、歩行、装備別の攻撃、公開までを一続きでたどれるようにする。
- README・AGENTS・制作ガイドで重なるセル、アンカー、方向順、タイミングの説明は、正式3体のメタデータと突き合わせて参照先を統一する。
- 研究レポートの当時の制約と現行仕様を区別し、装備の遮蔽、顔の画素変動、布・髪の揺れを原寸で比較できる事例へ案内する。
