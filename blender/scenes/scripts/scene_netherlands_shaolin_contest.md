# シーン：オランダ代表 vs 少林 — 横並走ドリブル争奪

## 台本

オランダ代表（濃いオレンジ一色）と少林選手が、同じ向きに横並走しながらボールを取り合う。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **オランダ** | 濃いオレンジ一色。進行方向を向いて右側レーンを並走 |
| **少林** | 明るいオレンジ。同じ向きで左側レーンを並走 |
| **間隔** | 体が重ならないよう横に離す |
| **ボール** | 二人の間の足元でタッチ。どちら寄りかが交互に揺れる |
| カメラ | 斜め後方から二人とボールを追う |
| 尺 | 約9秒（216f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-netherlands-contest --render-netherlands-contest-video
```

## 出力

- `blender/renders/parts/netherlands_shaolin_contest.mp4`
