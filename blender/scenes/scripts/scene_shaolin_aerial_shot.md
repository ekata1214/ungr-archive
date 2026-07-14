# シーン：少林選手 — 空中シュート（GK止め損ない）

## 台本

少林選手が空中に浮いた状態から左ゴールへシュートする。ポルトガルGKが横へ飛んでジャンプするが届かず、ボールはゴールイン。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **少林** | 最初から空中（z≈6.2）。左ゴール（-X）へ進みキック |
| **ボール** | 空中足元 → キック後ゴール右隅へ加速 |
| **GK** | middle shot と同じ `jump_full` 横飛び（遅れて飛び出す） |
| **結果** | GK届かずネットへ |
| カメラ | 空中追従 → ボール追従で寄り → ゴールインでネット側 |
| 尺 | 約5秒（120f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --render-shaolin-aerial-shot-video
```

## 出力

- `blender/renders/parts/shaolin_aerial_shot.mp4`
