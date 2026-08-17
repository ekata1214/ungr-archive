#!/usr/bin/env bash
# UNGR ARCHIVE — mac UI installer
# Run on your Mac:  bash tools/mac-ungr-ui/install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0)" && pwd)"
BACKUP_DIR="${HOME}/.ungr-ui-backup-$(date +%Y%m%d-%H%M%S)"

die() { echo "error: $*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "This installer is for macOS only (run on your Mac)."

echo "==> UNGR mac UI"
echo "    pack: $ROOT"
mkdir -p "$BACKUP_DIR" "$HOME/.config/ghostty" "$HOME/.config"

have() { command -v "$1" >/dev/null 2>&1; }

if ! have brew; then
  echo "==> Homebrew not found. Install from https://brew.sh then re-run."
  die "brew required"
fi

echo "==> brew packages"
brew list --cask font-jetbrains-mono-nerd-font &>/dev/null || brew install --cask font-jetbrains-mono-nerd-font
brew list starship &>/dev/null || brew install starship
# Ghostty: prefer cask when available
if ! have ghostty; then
  if brew info --cask ghostty &>/dev/null; then
    brew install --cask ghostty || true
  else
    echo "    (Ghostty cask missing — install from https://ghostty.org and re-run, or use iTerm2)"
  fi
fi

# Optional quality-of-life
brew list --cask raycast &>/dev/null || brew install --cask raycast || true
brew list --cask rectangle &>/dev/null || brew install --cask rectangle || true

backup_file() {
  local f="$1"
  if [[ -f "$f" || -L "$f" ]]; then
    cp -a "$f" "$BACKUP_DIR/"
  fi
}

echo "==> configs"
backup_file "$HOME/.config/ghostty/config"
backup_file "$HOME/.config/starship.toml"
cp "$ROOT/ghostty/config" "$HOME/.config/ghostty/config"
cp "$ROOT/starship.toml" "$HOME/.config/starship.toml"

ZSHRC="$HOME/.zshrc"
touch "$ZSHRC"
backup_file "$ZSHRC"
if grep -q 'UNGR UI BEGIN' "$ZSHRC" 2>/dev/null; then
  # replace existing block
  awk '
    /UNGR UI BEGIN/ {skip=1; next}
    /UNGR UI END/ {skip=0; next}
    !skip {print}
  ' "$ZSHRC" > "${ZSHRC}.ungr-tmp"
  mv "${ZSHRC}.ungr-tmp" "$ZSHRC"
fi
{
  echo ""
  cat "$ROOT/zshrc.fragment"
} >> "$ZSHRC"

echo "==> wallpaper"
WP_SRC="$ROOT/wallpaper/ungr-desktop-dark.png"
WP_DST="$HOME/Pictures/ungr-desktop-dark.png"
mkdir -p "$HOME/Pictures"
cp "$WP_SRC" "$WP_DST"
osascript <<EOF || true
tell application "System Events"
  tell every desktop
    set picture to "$WP_DST"
  end tell
end tell
EOF

echo "==> mac defaults (dock / Finder)"
# Dock: autohide, no magnify, smaller
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock magnification -bool false
defaults write com.apple.dock tilesize -int 42
defaults write com.apple.dock show-recents -bool false
# Finder
defaults write com.apple.finder AppleShowAllExtensions -bool true
defaults write com.apple.finder ShowPathbar -bool true
defaults write NSGlobalDomain AppleShowScrollBars -string "WhenScrolling"
# Accent: red (graphited if unavailable — 0=red on modern macOS)
defaults write NSGlobalDomain AppleAccentColor -int 0
killall Dock 2>/dev/null || true
killall Finder 2>/dev/null || true

echo ""
echo "Done."
echo "  backup:  $BACKUP_DIR"
echo "  Ghostty: open Ghostty (config already placed)"
echo "  Cursor:  merge tools/mac-ungr-ui/cursor-terminal-settings.json into settings.json"
echo "  iTerm:   import tools/mac-ungr-ui/iterm/ungr-archive.json via Profiles → Colors → Import if needed"
echo "  New shell: exec zsh  (or open a new Ghostty window)"
echo ""
echo "Manual (recommended): Ice for menu bar — https://github.com/jordanbaird/Ice"
