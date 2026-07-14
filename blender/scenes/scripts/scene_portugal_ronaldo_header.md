# シーン：ポルトガル戦 — ロナウドゆっくりジャンプ（単独）

握手／ヘディングとは別カット。ボールなし・ロナウド一人。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **ロナウド** | 溜め → スロージャンプ → 着地。ループなし |
| ボール | 非表示 |
| NLA | `air_jump` は短いので **scale で引き延ばし1回**（repeat 禁止＝カクつき防止） |
| 尺 | 約12秒（288f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-header --render-portugal-header-video
```

## 出力

- `blender/renders/parts/portugal_ronaldo_header.mp4`
