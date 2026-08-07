# UNGR ARCHIVE / アングラアーカイブ

@ungr.archive — マスではほとんど語られないけど、確実に誰かの人生を変えている作品達。僕達はそういう作品をずっとディグってきた。

## サイト

| ページ | リンク |
|------|--------|
| 公開サイト（ランディング） | [開く](https://ekata1214.github.io/ungr-archive/) / [`index.html`](index.html) |
| 企画・時事ネタリポ（内部） | [`リポ.html`](リポ.html) |

## Cursor Mobile / Cloud で使う

1. **Workspaces** → **Add Repo** → `ekata1214/ungr-archive`
2. エージェントに企画・ネタの相談（例：「7月ネタ1本、企画書にして」）

リポジトリ: `ekata1214/ungr-archive`

## アカウント

- **名称:** UNGR ARCHIVE / アングラアーカイブ
- **ハンドル:** @ungr.archive
- **軸:** 人間が作る意味・物語の矛盾を批評するメディア

## 構成

```
ungr-archive/
├── リポ.html              # 企画リポ本体（モバイル向け）
├── index.html             # GitHub Pages 用（内容同一）
├── README.md              # このファイル
└── .github/workflows/     # push で Pages 自動更新
```

## リポの更新

`リポ.html` を編集 → `index.html` も同期 → `main` に push で Pages 更新。

```bash
cp リポ.html index.html
git add .
git commit -m "Update report"
git push
```
