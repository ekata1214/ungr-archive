# SPDX-License-Identifier: MIT
"""
パーツ01: サッカーフィールドのみ（緑芝 + 白線）

  blender -b ~/Desktop/sho-lin-soccer.blend -P build_part_field.py
  blender -b ~/Desktop/sho-lin-soccer.blend -P build_part_field.py -- --render
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from news_cg_common import open_blend, resolve_blend_path  # noqa: E402

# フィールド寸法 — 画面いっぱいに見えるよう大きめ
PITCH_LENGTH = 260.0
PITCH_WIDTH = 170.0
LINE_W = 0.22
GRASS_DARK = (0.006, 0.045, 0.012, 1.0)  # かなり濃い緑
LINE_COLOR = (0.95, 0.95, 0.95, 1.0)
_SCALE = PITCH_LENGTH / 105.0


def make_emission_material(name: str, rgba: tuple) -> bpy.types.Material:
    """ニュースCG風フラット色 — ライトに左右されない"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = rgba
    emit.inputs["Strength"].default_value = 1.0
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def clear_all() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def setup_black_world() -> None:
    scene = bpy.context.scene
    for w in bpy.data.worlds:
        bpy.data.worlds.remove(w)
    world = bpy.data.worlds.new("World_Black")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs[1].default_value = 1.0
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def add_plane(name: str, size_x: float, size_y: float, loc: Vector, mat) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size_x / 2, size_y / 2, 1)
    obj.data.materials.append(mat)
    return obj


def build_field_only() -> None:
    clear_all()
    setup_black_world()

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 1

    grass = make_emission_material("Grass", GRASS_DARK)
    white = make_emission_material("LineWhite", LINE_COLOR)

    half_l = PITCH_LENGTH / 2
    half_w = PITCH_WIDTH / 2
    lz = 0.02

    add_plane("Field_Grass", PITCH_LENGTH, PITCH_WIDTH, Vector((0, 0, 0)), grass)

    add_plane("Line_Touchline_Top", PITCH_LENGTH, LINE_W, Vector((0, half_w, lz)), white)
    add_plane("Line_Touchline_Bottom", PITCH_LENGTH, LINE_W, Vector((0, -half_w, lz)), white)
    add_plane("Line_Goalline_Left", LINE_W, PITCH_WIDTH, Vector((-half_l, 0, lz)), white)
    add_plane("Line_Goalline_Right", LINE_W, PITCH_WIDTH, Vector((half_l, 0, lz)), white)
    add_plane("Line_Halfway", LINE_W, PITCH_WIDTH, Vector((0, 0, lz)), white)

    circle_r = 9.15 * _SCALE
    segments = 72
    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        mx = (math.cos(a0) + math.cos(a1)) / 2 * circle_r
        my = (math.sin(a0) + math.sin(a1)) / 2 * circle_r
        seg_len = math.hypot(math.cos(a1) - math.cos(a0), math.sin(a1) - math.sin(a0)) * circle_r
        angle = math.atan2(math.sin(a1) - math.sin(a0), math.cos(a1) - math.cos(a0))
        bpy.ops.mesh.primitive_plane_add(size=1, location=(mx, my, lz))
        seg = bpy.context.active_object
        seg.name = f"Line_CenterCircle_{i:02d}"
        seg.scale = (seg_len / 2, LINE_W / 2, 1)
        seg.rotation_euler = (0, 0, angle)
        seg.data.materials.append(white)

    bpy.ops.mesh.primitive_circle_add(radius=0.25 * _SCALE, location=(0, 0, lz))
    bpy.context.active_object.name = "Line_CenterSpot"
    bpy.context.active_object.data.materials.append(white)

    box_depth = 16.5 * _SCALE
    box_width = 40.32 * _SCALE
    goal_box_depth = 5.5 * _SCALE
    goal_box_width = 18.32 * _SCALE

    for side, gx in (("Left", -half_l), ("Right", half_l)):
        sign = 1 if gx < 0 else -1
        add_plane(f"Line_PenaltyFront_{side}", box_width, LINE_W, Vector((gx, 0, lz)), white)
        ix = gx + sign * box_depth / 2
        add_plane(f"Line_PenaltySideTop_{side}", LINE_W, box_depth, Vector((ix, box_width / 2, lz)), white)
        add_plane(f"Line_PenaltySideBottom_{side}", LINE_W, box_depth, Vector((ix, -box_width / 2, lz)), white)
        ix2 = gx + sign * goal_box_depth / 2
        add_plane(f"Line_GoalBoxFront_{side}", goal_box_width, LINE_W, Vector((gx, 0, lz)), white)
        add_plane(f"Line_GoalBoxSideTop_{side}", LINE_W, goal_box_depth, Vector((ix2, goal_box_width / 2, lz)), white)
        add_plane(f"Line_GoalBoxSideBottom_{side}", LINE_W, goal_box_depth, Vector((ix2, -goal_box_width / 2, lz)), white)

    print(f"Field built: {PITCH_LENGTH}x{PITCH_WIDTH}m, dark green emission, black world")


def render_preview() -> Path:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    setup_black_world()

    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)

    cam_data = bpy.data.cameras.new("FieldCam")
    cam = bpy.data.objects.new("FieldCam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, 0, 200)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(PITCH_LENGTH, PITCH_WIDTH) * 1.02  # 画面いっぱい

    out = Path("/workspace/blender/renders/parts/field_only.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {out}")
    return out


def save_blend(path: Path) -> None:
    bpy.ops.wm.save_mainfile(filepath=str(path))
    print(f"Saved: {path}")


def main() -> None:
    blend = resolve_blend_path()
    open_blend(blend)
    build_field_only()
    save_blend(blend)
    if "--render" in sys.argv:
        render_preview()


if __name__ == "__main__":
    main()
