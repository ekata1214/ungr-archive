# シーン：ポルトガル戦 — ロナウド単独ヘディング（スロー）

握手シーン（scene_portugal_shin_handshake）とは別カット。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **ロナウド** | 一人だけ。溜め → スロージャンプ → 額でボール接触 → 着地 |
| ボール | 接触〜余韻は頭ボーン（額）にロックしてズレ防止 |
| カメラ | 横寄り、頭＋ボールが切れない高さ |
| 尺 | 約15秒（360f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-header --render-portugal-header-video
```

## 出力

- `blender/renders/parts/portugal_ronaldo_header.mp4`
