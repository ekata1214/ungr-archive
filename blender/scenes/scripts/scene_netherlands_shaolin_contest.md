# シーン：オランダ代表 vs 少林 — ボール争奪

## 台本

オランダ代表（濃いオレンジ一色）の選手一人と、少林の選手一人がボールを奪い合う。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **オランダ** | 濃いオレンジ一色ユニ。右側へ走り込み、肩を入れて争う |
| **少林** | 明るいオレンジ一色。反対側から接触し押し合う |
| **ボール** | 中心へ。接触後は両足の間で弾みながら争奪 |
| カメラ | サイド寄り。争奪に寄っていく |
| 尺 | 約9秒（216f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-netherlands-contest --render-netherlands-contest-video
```

## 出力

- `blender/renders/parts/netherlands_shaolin_contest.mp4`
