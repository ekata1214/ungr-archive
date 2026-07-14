"""Render key frames from sho-lin-soccer.blend for preview screenshots."""
import bpy
from pathlib import Path

out_dir = Path("/opt/cursor/artifacts/shaolin_render")
out_dir.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = "PNG"

# 決定的瞬間のフレーム
frames = {
    "01_kick": 55,
    "02_shot": 85,
    "03_wall_climb": 95,
    "04_save": 110,
    "05_reaction": 170,
}

for label, frame in frames.items():
    scene.frame_set(frame)
    scene.render.filepath = str(out_dir / f"{label}.png")
    bpy.ops.render.render(write_still=True)
    print(f"Rendered frame {frame} -> {label}.png")

print("DONE", out_dir)
