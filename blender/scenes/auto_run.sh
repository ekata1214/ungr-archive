#!/bin/bash
# デスクトップにスクリプト同期 → シーン適用 → レンダー
set -euo pipefail

SCENE="${1:-01}"
DESKTOP="$HOME/Desktop"
SCENES_DIR="/workspace/blender/scenes"

echo "=== Sync scripts to Desktop ==="
cp "$SCENES_DIR"/news_cg_common.py \
   "$SCENES_DIR"/scene_definitions.py \
   "$SCENES_DIR"/run_scene_pipeline.py \
   "$SCENES_DIR"/inspect_blend.py \
   "$DESKTOP/"

echo "=== Run scene $SCENE on sho-lin-soccer.blend ==="
blender -b "$DESKTOP/sho-lin-soccer.blend" -P "$SCENES_DIR/run_scene_pipeline.py" -- --scene "$SCENE"

echo "=== Copy renders to repo ==="
mkdir -p /workspace/blender/renders/scene_"$SCENE"
cp -r /workspace/blender/renders/scene_"$SCENE"/* /workspace/blender/renders/scene_"$SCENE"/ 2>/dev/null || true

echo "DONE scene $SCENE"
