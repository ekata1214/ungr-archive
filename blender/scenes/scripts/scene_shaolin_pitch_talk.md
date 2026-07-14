# シーン：少林選手 — ピッチ上トーク＋頷き

## 台本

少林チームの選手一人がピッチ上で約3秒話し、その後軽く頷く。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **少林** | オレンジ／白のユニ。一人で正面を向く |
| **トーク** | 約3秒、首・上体の小さなモーション |
| **頷き** | 話のあと軽く一頷き |
| ボール | 非表示 |
| カメラ | 低いアングルのバストショット（胸〜頭）、わずかに寄る |
| 尺 | 約4秒（96f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-shaolin-pitch-talk --render-shaolin-pitch-talk-video
```

## 出力

- `blender/renders/parts/shaolin_pitch_talk.mp4`
