# シーン：ポルトガル戦 — シンがレオンに握手を求める

## 台本

試合開始早々、シンがレオン（WAY45）の大ファンとして、ロナウドをそっちのけで握手を求めに行く。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **ロナウド（ポルトガル・青/緑）** | **手前**で idle のみ（ポーズ追加なし） |
| **シン（少林・橙）** | **奥**で歩行 → 喜んで握手を差し出す |
| **レオン（ポルトガル・青/緑）** | **奥**で握手に応える |
| カメラ | ロナウド肩越し — 手前に青、奥に橙＋青 |
| 尺 | 約18秒（432f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-handshake --render-portugal-handshake-video
```

## 出力

- `blender/renders/parts/portugal_shin_handshake.mp4`
