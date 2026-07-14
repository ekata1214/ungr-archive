# シーン：ポルトガル戦 — フェルナンデス vs 少林ヘッドスライディング

握手／ヘディングカットとは別。フェルナンデスのドリブルに少林が頭から滑り込んで奪球。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **フェルナンデス** | 赤/緑。単独で +X へドリブル |
| **少林** | 橙。脇から接近 → 頭スライディングでボール奪取 |
| ボール | 足元追従 → 接触で弾かれて少林側へ |
| 尺 | 約12.5秒（300f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-fernandes-slide --render-portugal-fernandes-slide-video
```

## 出力

- `blender/renders/parts/portugal_fernandes_head_slide.mp4`
