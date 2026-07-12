# シーン：ポルトガル戦 — シンがレオンに握手を求める

## 台本

試合開始早々、シンがレオン（WAY45）の大ファンとして、ロナウドをそっちのけで握手を求めに行く。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **シン（少林・橙）** | ロナウドを無視してレオンの方へ歩行 → 握手を求める |
| **レオン（ポルトガル・青/緑）** | 待機 → 握手に応える |
| **ロナウド（ポルトガル・青/緑）** | 横で待機、無視されて苛立ち |
| フィールド | 3人のみ（ボール非表示） |
| カメラ | 3人が入る中距離、やや低め |
| 尺 | 約7.5秒（180f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-handshake --render-portugal-handshake-video
```

## 出力

- `blender/renders/parts/portugal_shin_handshake.mp4`
