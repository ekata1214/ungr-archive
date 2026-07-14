# シーン：ポルトガル戦 — ロナウド・トラウマしゃがみ

## 台本

ヘディング衝突のトラウマでヘディングができなくなったロナウドが、頭を両手で抱えてしゃがみ込む。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **ロナウド（ポルトガル・赤/緑）** | 一人。立位で動揺 → しゃがみ込み → 両手で頭を抱える |
| ボール | 非表示 |
| カメラ | 正面寄り。しゃがむにつれて寄る |
| 尺 | 約10秒（240f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-ronaldo-trauma --render-portugal-ronaldo-trauma-video
```

## 出力

- `blender/renders/parts/portugal_ronaldo_trauma.mp4`
