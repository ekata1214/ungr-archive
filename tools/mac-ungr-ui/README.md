# UNGR ARCHIVE — Mac desktop / terminal UI pack

編集室っぽい黒＋赤。紫ネオンなし。Ghostty + Starship + 壁紙 + Dock/Finder を一式。

## いちばん早い入れ方（自分の Mac で）

```bash
cd /path/to/ungr-archive
bash tools/mac-ungr-ui/install.sh
```

必要: macOS + Homebrew。

入れるもの:
- JetBrains Mono Nerd Font
- Starship
- Ghostty（cask があれば）
- Raycast / Rectangle（なければ）
- `~/.config/ghostty/config`
- `~/.config/starship.toml`
- `~/.zshrc` に UNGR ブロック追記
- 壁紙 `~/Pictures/ungr-desktop-dark.png` を適用
- Dock 自動非表示・拡大オフ、Finder 拡張子表示、アクセント赤寄り

既存設定は `~/.ungr-ui-backup-日時/` に退避。

## 中身

| パス | 用途 |
|---|---|
| `ghostty/config` | 黒地・赤カーソル・低透過 |
| `starship.toml` | プロンプト最小（dir + git + ❯） |
| `zshrc.fragment` | starship init など |
| `wallpaper/ungr-desktop-dark.png` | 暗いフィルム粒壁紙 |
| `cursor-terminal-settings.json` | Cursor/VS Code 統合ターミナル色 |
| `iterm/ungr-archive.json` | iTerm 用カラー |
| `palette.md` | 色トークン |
| `raycast/NOTES.json` | Raycast / Ice メモ |

## Cursor ターミナル

`cursor-terminal-settings.json` の中身を Cursor の `settings.json` にマージ。

## Ghostty が入れられなかった場合

1. https://ghostty.org からインストール後、再実行  
2. または iTerm2 + `iterm/ungr-archive.json`

## 戻す

```bash
# 例
cp ~/.ungr-ui-backup-XXXX/config ~/.config/ghostty/config
cp ~/.ungr-ui-backup-XXXX/starship.toml ~/.config/starship.toml
# zshrc はバックアップから戻すか、UNGR UI BEGIN〜END を削除
```

## 方針

- 透明度ほぼなし
- プロンプトに言語バージョン・電池・時計を出さない
- 赤はカーソル／エラー／git dirty だけ
