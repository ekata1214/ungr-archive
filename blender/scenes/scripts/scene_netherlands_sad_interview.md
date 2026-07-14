# シーン：オランダ選手 — 悲しげなお立ち台インタビュー

## 台本

オランダ選手一人がお立ち台で、悲しげにゆっくりと話している。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **オランダ** | 濃いオレンジ一色。一人でお立ち台の上 |
| **トーク** | レオン同様のセット。低周波・うつむき気味のゆっくりした頷き |
| セット | インタビュー背景パネル＋お立ち台（オランダオレンジ帯） |
| カメラ | 正面寄りミディアム、ごくゆっくり寄る |
| 尺 | 約16秒（384f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --render-netherlands-sad-interview-video
```

## 出力

- `blender/renders/parts/netherlands_sad_interview.mp4`
