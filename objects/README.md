# オブジェクト制作ガイド

木箱は支持面、宝箱は部位の蝶番、大岩は接地する全体回転、石柱は前縁を支点にした転倒と歩行用モジュールの作例です。[4種の設計・画像・検査結果](../research/objects01/README.md) · [OBJECTS](../docs/objects.html) · [冒険者との床面比較](../docs/object-study.html)

## 次の家具・建物・仕掛けを作る順序

GUILDWARDの足場は、水平1マスを14×14、鉛直1段を8モデル単位として設計します。旧石柱のように別の尺度で作った素材は、姿勢を決めてからプロジェクト側で支持高を合わせます。[寸法・足元・変換のガイド](../research/GUILDWARD_ASSET_SCALE_GUIDE.md)

1. ゲームの占有マス、床面、支持面、用途、状態遷移を決めます。橋・積荷なら、人物の両足と隣の部材に接する位置を先に決めます。動く部位にはモデル座標の軸と支点を置きます。
2. `objects/<id>/object.json` に実寸、部位順、パレット、元格子、セル、足元アンカー、状態とコマ時間を定義します。`build_model.py` の `build(spec)` が材質と部位を持つ `Volume` を返します。板の継ぎ目や石目は立体上に置き、奥に回った部分は共通の描画器に遮蔽させます。
3. **すべての静止状態・動作・独立モジュールを8方向**で焼きます。順序は **S / SW / W / NW / N / NE / E / SE**。対称な模型にも全8列・全8行を用意します。一つの立体を毎回投影し、正面・進行・回転軸をカメラのヨー角から独立させます。
4. 初版を `.phase1/` の新しい作業先に保存します。人物と同じ仰角24°・1.50 px/単位で、原寸のシルエット、材質、支持面、遮蔽を見ると、修正箇所を絞れます。異なる投影のゲームでは、地面の2本の基底ベクトルと鉛直1段の画面変位を別々に測ります。
5. `quality.json` に対象の可視材質、支持面、始終端、動作固有の条件を記入します。蝶番は角度の途中も検査し、転動は360°の閉路を確認します。分割足場は同じ部位の格子、端面、1〜3個の並び、人物の接地を確認します。
6. 検証したシート・GIF・JSONをまとめて `docs/assets/<id>/` に置き、台帳に登録します。Labで完成したGUILDWARD候補には `candidateProjects` を使います。採用時に `projects` へ移します。ブラウザで原寸・通常速度、全方向、単発遷移、素材リンクを確認します。

## 再生成

リポジトリのルートで、既存のNumPy・Pillow環境を使います。次は独立したモデルから宝箱を作る例です。ほかのIDも同じ手順です。`--model` を省略すると各素材ディレクトリの保存済み `model.npz` を読みます。

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
$id = 'treasure_chest'
$run = Join-Path $PWD ('.phase1/objects-' + [guid]::NewGuid())
& $python -m "objects.$id.build_model" --out "$run/$id.npz"
& $python -m objects.bake $id --model "$run/$id.npz" --out "$run/$id"
```

4種を元の造形コードから再生成し、公開データと比較します。検証器は新しい出力先を作り、公開ディレクトリを読み取り専用の比較対象として扱います。

```powershell
& $python -m research.verify_objects --out "$run/verified"
& $python -m research.objects01.game_projection --out "$run/game-projection"
node research/verify_catalog.cjs
& $python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

[素材一覧](http://127.0.0.1:8000/objects.html) · [床面比較](http://127.0.0.1:8000/object-study.html) · [GUILDWARDの制作候補](http://127.0.0.1:8000/projects.html?id=guildward)

## データの読み方

| 項目 | 意味 |
| --- | --- |
| `object.json` / `model.npz` | 形状、材質別の陰・基・明3色、部位名、元格子。NPZの `slices` と `parts` は同じ形のZ/Y/X配列。0は空、IDは定義順の1始まり |
| `geometry` | 底面基準、閉・直立時の実測幅／奥行き／高さ、タイルピッチ。+Yが物体正面、+Zが上 |
| `rotation` | モデル内の `pivot_xyz`、右手系 `axis_xyz`、適用部位。大岩は `settle` と有効半径を指定。移動方向は `travel_xyz` |
| `views` | 状態ごとの角度列と配置。動作には `durations_ms` と `loop`、単発には `next`。BEAMでは切り出す部位と、モジュールの中央を原点に戻す平行移動を指定 |
| 公開JSON | 各シートのアンカー・セルはピクセル単位。`neutral` は方向を列、`animations[id]` は方向を行・時間を列に持つ。`bounds_xyz_by_frame` はポーズ後の占有ボクセルの外端。`placement` の支持点は物体ローカル座標 |
| 確認用GIF | 同時刻の8方向を上段S〜NW、下段N〜SEに配置。確認用の淡色背景を持つ。ゲーム用PNGの背景は透過 |

既存の人型ベイクと剛体ベイクは、同じ `Grid`、回転行列、逆写像の再スライス、法線とレイ描画を呼び出します。オブジェクト側にはIK・歩行クリップを設定する必要がありません。[実装](bake.py) · [技術仕様](../docs/TECHNICAL_DESIGN.md#非人型とオブジェクトの制作方針)
