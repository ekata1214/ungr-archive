# シーン：レオン単独インタビュー（お立ち台）

## 台本

レオンがインタビュー受けるお立ち台で、約4秒ほど一人で話している。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **レオン（ポルトガル・赤/緑）** | 一人。お立ち台の上で idle＋話すジェスチャー |
| セット | 後ろにインタビュー用の平面パネル、足元にお立ち台、手前にマイク |
| カメラ | 正面寄りミディアム、わずかに寄る |
| 尺 | 約4秒（96f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-leao-interview --render-leao-interview-video
```

## 出力

- `blender/renders/parts/leao_interview.mp4`
