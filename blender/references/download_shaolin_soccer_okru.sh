#!/usr/bin/env bash
# OK.ru から少林サッカー (2001) 720p ESP を MP4 で取得
# 例: https://ok.ru/video/7349803092643

set -euo pipefail

URL="${1:-https://ok.ru/video/7349803092643}"
OUT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT_DIR}/shaolin_soccer_2001_720_es.mp4"

if ! command -v yt-dlp >/dev/null 2>&1; then
  pip install -q yt-dlp
  export PATH="${HOME}/.local/bin:${PATH}"
fi

mkdir -p "$OUT_DIR"
echo "Downloading: $URL"
echo "Output: $OUT"
yt-dlp -f "hd/best[ext=mp4]/best" -o "$OUT" "$URL"
echo "Done: $OUT"
ls -lh "$OUT"
