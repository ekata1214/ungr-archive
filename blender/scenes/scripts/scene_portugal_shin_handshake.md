# シーン：ポルトガル戦 — シンがレオンに握手を求める

## 台本

試合開始早々、シンがレオン（WAY45）の大ファンとして、ロナウドをそっちのけで握手を求めに行く。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **ロナウド（ポルトガル・赤/緑）** | **手前**で idle、奥の2人の方を向く |
| **シン（少林・橙）** | **奥**で歩行 → 嬉しそうにジャンプ → 握手を差し出す |
| **レオン（ポルトガル・赤/緑）** | **奥**で握手に応える（手が重なる距離） |
| カメラ | ロナウド肩越し — 手前に赤/緑、奥に橙＋赤/緑 |
| 尺 | 約18秒（432f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-handshake --render-portugal-handshake-video
```

## 出力

- `blender/renders/parts/portugal_shin_handshake.mp4`
