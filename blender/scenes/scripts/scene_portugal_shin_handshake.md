# シーン：ポルトガル戦 — シンがレオンに握手を求める

## 台本

試合開始早々、シンがレオン（WAY45）の大ファンとして、ロナウドをそっちのけで握手を求めに行く。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **ロナウド（ポルトガル・赤/緑）** | 握手を見てキレる → **カットで一人映し** → ヘディング |
| **シン（少林・橙）** | **奥**で idle → 楽しそうに走る → 到着ホップ → 右手で握手を差し出す |
| **レオン（ポルトガル・赤/緑）** | **奥**で idle のまま待つ → 左手で握手に応える |
| 立ち位置 | 左右対面（シンは +X から走ってくる）。腕は全身 REPLACE で idle から伸ばす |
| カメラ | 前半：ロナウド肩越し握手 / 後半：単独カット（シン・レオン非表示）でヘディング寄り |
| 尺 | 約20秒（480f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-handshake --render-portugal-handshake-video
```

## 出力

- `blender/renders/parts/portugal_shin_handshake.mp4`
