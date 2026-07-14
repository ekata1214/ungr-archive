# シーン：少林ミドルシュート vs ポルトガルGK

握手／ヘディング／スライディングとは別カット。少林がミドルから決め、GKが飛び出すがボールは高速でゴールイン。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **少林** | 橙。+X ゴールへ向かって接近 → ミドルシュート |
| **ポルトガルGK** | 赤/緑。遅れて横っ飛び → 届かず |
| ボール | 足元追従 → キック後、短時間で右ゴールネットへ |
| 尺 | 約12秒（288f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-shaolin-middle-shot --render-shaolin-middle-shot-video
```

## 出力

- `blender/renders/parts/shaolin_middle_shot.mp4`
