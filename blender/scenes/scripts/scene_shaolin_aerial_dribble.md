# シーン：少林選手 — 空中ドリブル

## 台本

少林選手がピッチから跳び上がり、空中を進みながら足元でボールをドリブルする。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **少林** | オレンジ／白。一人、正面（+Y）へ進む |
| **離陸** | しゃがみ → ジャンプで高さ約 z6.5 へ |
| **空中ドリブル** | `run` ループで脚を動かし、ボールを足元に接着 |
| **ホバー** | 巡航中はわずかに上下に浮遊 |
| ボール | 空中でも足元タッチ（上下バウンス） |
| カメラ | 斜め後方、高度に合わせて追従 |
| 尺 | 約5.5秒（132f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --render-shaolin-aerial-dribble-video
```

## 出力

- `blender/renders/parts/shaolin_aerial_dribble.mp4`
