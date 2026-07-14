# SPDX-License-Identifier: MIT
"""
自動パイプライン: デスクトップの sho-lin-soccer.blend を開き、シーン適用→保存→レンダー。

  blender -b -P run_scene_pipeline.py -- --scene 01
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

# スクリプトのあるディレクトリを import パスに追加
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from news_cg_common import (  # noqa: E402
    open_blend,
    prepare_fresh_scene,
    render_scene_frames,
    resolve_blend_path,
)
from scene_definitions import SCENES  # noqa: E402

REPO_RENDERS = Path("/workspace/blender/renders")
ARTIFACT_RENDERS = Path("/opt/cursor/artifacts/shaolin_render")


def get_scene_id() -> str:
    if "--scene" in sys.argv:
        return sys.argv[sys.argv.index("--scene") + 1]
    return "01"


def save_blend(path: Path) -> None:
    bpy.ops.wm.save_mainfile(filepath=str(path))
    print(f"Saved: {path}")


def write_preview_html(scene_id: str, spec_title: str, image_dir: Path) -> Path:
    html_path = image_dir / "preview.html"
    imgs = sorted(image_dir.glob("*.png"))
    lines = [
        "<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>シーン{scene_id} {spec_title}</title>",
        "<style>body{font-family:sans-serif;background:#111;color:#eee;padding:16px}",
        "img{width:100%;border-radius:8px;margin-bottom:12px}</style></head><body>",
        f"<h1>シーン{scene_id}: {spec_title}</h1>",
    ]
    for img in imgs:
        lines.append(f"<figure><img src='{img.name}'><figcaption>{img.stem}</figcaption></figure>")
    lines.append("</body></html>")
    html_path.write_text("\n".join(lines), encoding="utf-8")
    return html_path


def main() -> None:
    scene_id = get_scene_id()
    if scene_id not in SCENES:
        raise SystemExit(f"Unknown scene: {scene_id}. Available: {list(SCENES)}")

    spec = SCENES[scene_id]
    blend_path = resolve_blend_path()
    open_blend(blend_path)
    prepare_fresh_scene()
    spec.apply()

    save_blend(blend_path)

    out_base = REPO_RENDERS if REPO_RENDERS.parent.exists() else ARTIFACT_RENDERS
    saved = render_scene_frames(scene_id, spec.render_frames, out_base)
    html = write_preview_html(scene_id, spec.title, saved[0].parent)

    print("=" * 50)
    print(f"SCENE {scene_id} DONE: {spec.title}")
    print(f"Blend: {blend_path}")
    print(f"Renders ({len(saved)}):")
    for p in saved:
        print(f"  {p}")
    print(f"Preview: {html}")
    print("=" * 50)


if __name__ == "__main__":
    main()
