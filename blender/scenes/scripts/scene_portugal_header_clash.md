# シーン：ポルトガル戦 — 空中ヘディング衝突（スロー）

握手／単独ジャンプとは別カット。ロナウドと少林選手が向かい合って跳び、頂点で頭がぶつかる。

## 映像化の要点

| 要素 | 演出 |
|------|------|
| **ロナウド** | 赤/緑。+X 向きでジャンプ＆ヘディング姿勢 |
| **少林** | 橙。-X 向きで同じく |
| 衝突 | 胴体は離し、前傾で頭だけ接触。跳ね返りあり |
| ボール | 二人の頭のさらに上（挟まない） |
| 尺 | 約12.5秒（300f @ 24fps） |

## 実行

```bash
blender -b ~/Desktop/sho-lin-soccer.blend \
  -P /workspace/blender/scenes/build_part_field.py -- \
  --animate-portugal-header-clash --render-portugal-header-clash-video
```

## 出力

- `blender/renders/parts/portugal_header_clash.mp4`
