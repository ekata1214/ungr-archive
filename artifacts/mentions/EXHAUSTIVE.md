# 動画リンク・ツイート総当たり調査

調査日: 2026-08-08

## 結論（率直に）

**公開ツールだけでは「X上の全ツイートを100%網羅」はできない。**
ただしチャンネル動画80本について、Yahooリアルタイム検索で
`youtu.be/{id}` / `youtube.com/watch?v={id}` / `"{id}"` / 主要タイトル を総当たりした結果、
**確認できた第三者シェアは7件・動画2本分だけ**だった。

### なぜ全部は拾えないか
- X公式検索/APIはログイン必須（ゲスト検索は404/401）
- Yahooリアルタイムはリンク検索がほぼ効かない（80本×youtu.be が全滅）
- タイトル検索は直近中心。古いツイートはインデックスから落ちる
- 引用RT・画像だけ・短縮URL別ドメインなどは取りこぼしやすい

### 網羅に近いことをするなら
- X公式の Advanced Search（ログイン済みブラウザ）
- 有料のソーシャルリスニング（Brandwatch / Meltwater / SocialDog 等）
- YouTube Studio の「トラフィックソース > YouTube以外のGoogle以外のサイト」で参照元を見る

## 確認できた第三者ツイート（7件）

- [gegstart_](https://x.com/gegstart_/status/2063826299349819762) fol=4757 likes=140 views=30208
  - 見てくれ / 【完全版】クラウドラップの歴史 https://youtu.be/wAZsvl483OI?si=B2ha87L_jEAJUjER @YouTubeより
  - videos: wAZsvl483OI
- [agapepe1](https://x.com/agapepe1/status/2083781983604556207) fol=642 likes=7 views=527
  - 違法ダウンロードがカルチャーに与えた影響 - YouTube https://www.youtube.com/watch?v=k8aqakMSiLQ
  - videos: k8aqakMSiLQ
- [keiharad](https://x.com/keiharad/status/2068209165890428997) fol=1064 likes=0 views=498
  - これは必見！勉強になりました
  - QT @gegstart_: 見てくれ / 【完全版】クラウドラップの歴史 https://youtu.be/wAZsvl483OI?si=B2ha87L_jEAJUjER @YouTubeより
  - videos: wAZsvl483OI
- [gamefan0627](https://x.com/gamefan0627/status/2083953507015835869) fol=1155 likes=1 views=264
  - 違法ダウンロードがカルチャーに与えた影響 https://youtu.be/k8aqakMSiLQ?si=Z5n4mkFihFoSXfYC @YouTubeより
  - videos: k8aqakMSiLQ
- [CircleKurukuru](https://x.com/CircleKurukuru/status/2085376739946160440) fol=1349 likes=4 views=245
  - 雑多だった時代をちゃんと言語化していてとても好きだった。 / 違法ダウンロードがカルチャーに与えた影響 https://youtu.be/k8aqakMSiLQ?si=W4vNd2wOyXuDlgAP @YouTubeより
  - videos: k8aqakMSiLQ
- [ano_prproj](https://x.com/ano_prproj/status/2083719274145976765) fol=123 likes=0 views=130
  - 違法ダウンロードがカルチャーに与えた影響 https://youtu.be/k8aqakMSiLQ?si=wqF2rcrlBTUtZ-JN @YouTubeより / いいね
  - videos: k8aqakMSiLQ
- [masasuke_aruga](https://x.com/masasuke_aruga/status/2084076504733167957) fol=383 likes=2 views=53
  - 違法ダウンロードがカルチャーに与えた影響 - YouTube https://www.youtube.com/watch?v=k8aqakMSiLQ 視野
  - videos: k8aqakMSiLQ

## 動画別

- **5件** `k8aqakMSiLQ` 違法ダウンロードがカルチャーに与えた影響
- **2件** `wAZsvl483OI` 【完全版】クラウドラップの歴史

シェア0件の動画: **78 / 80**

## 実行内容

- チャンネル動画/ショート計80本を一覧化 → `channel_videos.json`
- 各IDに対し youtu.be / watch?v / 引用ID をYahoo RTで検索（276クエリ）
- ヒットをfxtwitterで本文確認し、公式@ungrarchiveと無関係ノイズを除外
- 結果 → `exhaustive_x_third_party_clean.json`
