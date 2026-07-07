# SPDX-License-Identifier: MIT
"""
パーツ01: サッカーフィールドのみ（緑芝 + 白線）

  blender -b ~/Desktop/sho-lin-soccer.blend -P build_part_field.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from news_cg_common import (  # noqa: E402
    LINE_WHITE,
    make_flat_material,
    open_blend,
    resolve_blend_path,
)

# フィールド寸法（メートル相当）— ニュースCG用に大きめ
PITCH_LENGTH = 200.0
PITCH_WIDTH = 130.0
LINE_W = 0.18
GRASS_DARK = (0.05, 0.28, 0.07, 1.0)  # 濃い緑

# 標準ピッチ(105x68)からのスケール
_SCALE = PITCH_LENGTH / 105.0


def clear_all() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def add_plane(name: str, size_x: float, size_y: float, loc: Vector, mat) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size_x / 2, size_y / 2, 1)
    obj.data.materials.append(mat)
    return obj


def setup_black_world() -> None:
    scene = bpy.context.scene
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs[1].default_value = 1.0
    scene.render.film_transparent = False


def build_field_only() -> None:
    """緑の芝＋白線だけ。キャラ・ゴール・カメラ等は置かない。"""
    clear_all()
    setup_black_world()

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 1

    grass = make_flat_material("Grass", GRASS_DARK)
    white = make_flat_material("LineWhite", LINE_WHITE)

    half_l = PITCH_LENGTH / 2
    half_w = PITCH_WIDTH / 2
    z = 0.0
    lz = 0.01  # 白線を芝より少し上に

    # 芝生
    add_plane("Field_Grass", PITCH_LENGTH, PITCH_WIDTH, Vector((0, 0, z)), grass)

    # 外枠
    add_plane("Line_Touchline_Top", PITCH_LENGTH, LINE_W, Vector((0, half_w, lz)), white)
    add_plane("Line_Touchline_Bottom", PITCH_LENGTH, LINE_W, Vector((0, -half_w, lz)), white)
    add_plane("Line_Goalline_Left", LINE_W, PITCH_WIDTH, Vector((-half_l, 0, lz)), white)
    add_plane("Line_Goalline_Right", LINE_W, PITCH_WIDTH, Vector((half_l, 0, lz)), white)

    # センターライン
    add_plane("Line_Halfway", LINE_W, PITCH_WIDTH, Vector((0, 0, lz)), white)

    # センターサークル（64点の短い線分で近似）
    circle_r = 9.15 * _SCALE
    segments = 64
    import math

    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        mx = (math.cos(a0) + math.cos(a1)) / 2 * circle_r
        my = (math.sin(a0) + math.sin(a1)) / 2 * circle_r
        seg_len = math.sqrt(
            (math.cos(a1) - math.cos(a0)) ** 2 + (math.sin(a1) - math.sin(a0)) ** 2
        ) * circle_r
        angle = math.atan2(math.sin(a1) - math.sin(a0), math.cos(a1) - math.cos(a0))
        bpy.ops.mesh.primitive_plane_add(size=1, location=(mx, my, lz))
        seg = bpy.context.active_object
        seg.name = f"Line_CenterCircle_{i:02d}"
        seg.scale = (seg_len / 2, LINE_W / 2, 1)
        seg.rotation_euler = (0, 0, angle)
        seg.data.materials.append(white)

    # センタースポット
    bpy.ops.mesh.primitive_circle_add(radius=0.2 * _SCALE, location=(0, 0, lz))
    spot = bpy.context.active_object
    spot.name = "Line_CenterSpot"
    spot.data.materials.append(white)

    # ペナルティエリア（両ゴール側）— シンプルな矩形
    box_depth = 16.5 * _SCALE
    box_width = 40.32 * _SCALE
    goal_x = half_l

    for side, gx in (("Left", -goal_x), ("Right", goal_x)):
        sign = 1 if gx < 0 else -1
        inner_x = gx + sign * box_depth / 2
        add_plane(f"Line_PenaltyFront_{side}", box_width, LINE_W, Vector((gx, 0, lz)), white)
        add_plane(
            f"Line_PenaltySideTop_{side}",
            LINE_W,
            box_depth,
            Vector((inner_x, box_width / 2, lz)),
            white,
        )
        add_plane(
            f"Line_PenaltySideBottom_{side}",
            LINE_W,
            box_depth,
            Vector((inner_x, -box_width / 2, lz)),
            white,
        )

    # ゴールエリア（小さい箱）
    goal_box_depth = 5.5 * _SCALE
    goal_box_width = 18.32 * _SCALE
    for side, gx in (("Left", -goal_x), ("Right", goal_x)):
        sign = 1 if gx < 0 else -1
        inner_x = gx + sign * goal_box_depth / 2
        add_plane(f"Line_GoalBoxFront_{side}", goal_box_width, LINE_W, Vector((gx, 0, lz)), white)
        add_plane(
            f"Line_GoalBoxSideTop_{side}",
            LINE_W,
            goal_box_depth,
            Vector((inner_x, goal_box_width / 2, lz)),
            white,
        )
        add_plane(
            f"Line_GoalBoxSideBottom_{side}",
            LINE_W,
            goal_box_depth,
            Vector((inner_x, -goal_box_width / 2, lz)),
            white,
        )

    bpy.context.scene.frame_set(1)
    print("Field only: grass + white lines")


def save_blend(path: Path) -> None:
    bpy.ops.wm.save_mainfile(filepath=str(path))
    print(f"Saved: {path}")


def main() -> None:
    blend = resolve_blend_path()
    open_blend(blend)
    build_field_only()
    save_blend(blend)


if __name__ == "__main__":
    main()
