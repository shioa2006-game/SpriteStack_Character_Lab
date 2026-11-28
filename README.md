# SpriteStack Character Lab

参考イラスト1枚から、ゲーム用キャラクターの**静止・歩行・攻撃の8方向透過PNG**を制作する研究環境です。制作AIが画像を読み、見えない背面の形、部位の寸法、配色、装備の動きを設計します。その設計をPythonとJSONに残すと、同じボクセルモデルと共通リグから全方向を焼き直せます。[GitHub Pagesで8方向を再生](https://shioa2006-game.github.io/SpriteStack_Character_Lab/)

## 冒険者の一行

ガルドの重打撃、リコの弓射撃、セナの氷魔法、発破師トビの投擲を、同じ石畳で8方向から比較できます。単発再生は攻撃終了後に待機へ戻ります。待機4コマ・歩行6コマの共通セルは64×64、足元アンカーは (32, 57)。攻撃は人物ごとのセル・アンカー・コマ時間を使います。[4人の隊列・個別プレビュー](docs/party.html) · [生成手順と攻撃の検証記録](research/adventurers/ATTACKS.md)

| キャラクター | 待機 | 歩行 | 攻撃 | ゲーム用シートとメタデータ |
| --- | --- | --- | --- | --- |
| ガルド | [GIF](docs/assets/gard/breathe.gif) | [GIF](docs/assets/gard/walk.gif) | [重打撃](docs/assets/gard/attack.gif) | [gard](docs/assets/gard/) |
| リコ | [GIF](docs/assets/rico/breathe.gif) | [GIF](docs/assets/rico/walk.gif) | [射撃](docs/assets/rico/attack.gif) | [rico](docs/assets/rico/) |
| セナ | [GIF](docs/assets/sena/breathe.gif) | [GIF](docs/assets/sena/walk.gif) | [氷魔法](docs/assets/sena/attack.gif) | [sena](docs/assets/sena/) |
| トビ | [GIF](docs/assets/tobi/breathe.gif) | [GIF](docs/assets/tobi/walk.gif) | [発破玉の投擲](docs/assets/tobi/attack.gif) | [tobi](docs/assets/tobi/) |

トビは右手の発破玉を6コマ目で放ち、腰袋から次の玉を取り出します。保持・離手・再装備を同じ立体部位で表現しています。[トビの造形と投擲の検証](research/adventurers/tobi/README.md)

[待機・歩行の制作記録と足元の合わせ方](research/adventurers/README.md)

| 正式サンプル | 造形と動きの見どころ | 素材 |
| --- | --- | --- |
| [MAREN](characters/maren/) | 長い青髪、長剣と丸盾。頭上で溜め、踏み込んで低く振り抜く | [攻撃GIF](docs/assets/maren/attack.gif) |
| [CRYSTAL MAGE](characters/crystal_mage/) | ローブとマント。本を掲げて詠唱し、右手の水晶から放つ | [攻撃GIF](docs/assets/crystal_mage/attack.gif) |
| [AZURE RONIN](characters/azure_ronin/) | スカーフとポニーテール。肩へ刀を引き、短い踏み込みで払い切る | [攻撃GIF](docs/assets/azure_ronin/attack.gif) |

実験04では、新しい参考画像から銀のプレートアーマーと青い百合盾の **FLEUR KNIGHT** を制作しました。ギャラリーのキャラクター欄で再生できます。[制作・検証記録](research/IMAGE_TO_CHARACTER_04.md) · [試作と完成版の原寸比較](docs/assets/fleur_knight/slash-comparison.gif)

実験05の **CRIMSON BLADE** は、長い黒髪を高く束ねた紅装の刀剣士です。低く刀を引き、踏み込みながら斜め上へ斬り抜けます。[制作・検証記録](research/IMAGE_TO_CHARACTER_05.md) · [8方向の攻撃GIF](docs/assets/crimson_blade/attack.gif)

実験06の **GOBLIN BRUTE** は、大きな耳と短い脚のゴブリン戦士です。右肩の後ろへ木の棍棒を振りかぶり、腰を落として叩きつけます。[制作・検証記録](research/IMAGE_TO_CHARACTER_06.md) · [初版と完成版の攻撃比較](docs/assets/goblin_brute/smash-comparison.gif)

実験07の **SKELETON GUARD** は、象牙色の頭蓋骨、背景が透ける肋骨、青い丸盾を持つ骸骨衛兵です。左の盾を構えたまま、右の錆剣を頭上で止めて斬り下ろします。[制作・検証記録](research/IMAGE_TO_CHARACTER_07.md) · [初版と完成版の攻撃比較](docs/assets/skeleton_guard/cleave-comparison.gif)

**新しい画像を受け取ったら**、[開発規約](AGENTS.md) と [キャラクター制作ガイド](research/CHARACTER_CREATION_GUIDE.md) を使ってください。制作ガイドに、採色から原寸評価、公開までの手順があります。

**攻撃を見直すとき**は、変更前後のベイクから足元を揃えた8方向GIF・主要ポーズ・関節座標・武器の軌跡図を生成できます。[比較コマンドと検証例](research/attack/README.md)

## 仕組み

`characters/<name>/` に造形コード、材質・部位の水平断面（NPZ）、関節と装備の設定、専用攻撃クリップ、品質条件を置きます。歩行は [共通クリップ](motions/walk.json) を体格別に調整します。[共通エンジン](spritestack/) が腕・脚のIK、部位の変形、髪や布の追従、再スライス、8方向の正投影を処理します。公開用PNGと再生用メタデータは [docs/assets/](docs/assets/) にあります。[技術設計と出力仕様](docs/TECHNICAL_DESIGN.md)

## WindowsのPython環境

リポジトリのルートでPowerShellを開きます。再生成を確認した組み合わせはPython 3.12.1、NumPy 2.3.5、Pillow 13.0.0です。初回のみ仮想環境を作成します。

```powershell
py -3.12 -m venv .venv
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $python -m pip install -r requirements.txt "numpy==2.3.5" "Pillow==13.0.0"
```

## 共通エンジンでの生成

次の例はMARENを作業用フォルダに再生成し、公開版と照合します。ほかの2体は `$name` を `crystal_mage` または `azure_ronin` に変えます。新しいPowerShellでは `$python` を再設定してください。

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$name = 'maren'
$config = "characters/$name/character.json"
$run = Join-Path $PWD ('.phase1/' + $name + '-' + [guid]::NewGuid())
& $python -m spritestack --character $config --modes idle --out "$run/idle"
& $python -m research.verify_character --character $config --out "$run/idle"
& $python -m spritestack --character $config --out "$run/all"
& $python -m research.verify_walk --character $config --out "$run/all"
& $python -m research.verify_attack --character $config --out "$run/all" --gif "$run/all/attack.gif" --published "docs/assets/$name"
```

`all/` に `idle.png`・`walk.png`・`attack.png` と全モードの `metadata.json` ができます。`idle/` は静止の公開用メタデータと、設定がある場合の比較用静止シートを含みます。歩行を反復する間は `--modes walk` で静止と歩行だけを焼けます。CLIには毎回、まだ存在しない出力先を指定します。

## ギャラリーと研究資料

手元では `& $python -m http.server 8000 --bind 127.0.0.1 --directory docs` を実行し、ブラウザで [ローカルギャラリー](http://127.0.0.1:8000/) を開きます。キャラクター、モーション、方向、表示倍率を選び、攻撃は再生し直せます。

LARK・BRAMは旧エンジンとの互換性や関節変形を調べる研究用資産です。過去の数値、失敗例、比較画像は各実験の記録に残しています。[資産整理と回帰基準](research/SAMPLE_CLEANUP.md) · [研究の経緯](research/ROADMAP.md)

リポジトリのライセンスは未設定です。
