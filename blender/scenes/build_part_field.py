# SPDX-License-Identifier: MIT
"""
パーツ01: リアルなサッカーフィールド（芝テクスチャ + FIFA白線）

  blender -b ~/Desktop/sho-lin-soccer.blend -P build_part_field.py -- --render
  → field_wide.png（引き俯瞰）と field_grass_close.png（芝寄り）を出力
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List, Tuple

import bpy
from mathutils import Euler, Vector

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from news_cg_common import open_blend, resolve_blend_path  # noqa: E402

# FIFA寸法ベース（×2.5スケール）
_SCALE = 2.5
PITCH_LENGTH = 105.0 * _SCALE   # 262.5m
PITCH_WIDTH = 68.0 * _SCALE     # 170m
LINE_W = 0.12 * _SCALE          # 12cm → 30cm

# マーキング寸法（メートル × スケール）
CENTER_R = 9.15 * _SCALE
PEN_DEPTH = 16.5 * _SCALE
PEN_WIDTH = 40.32 * _SCALE
GOAL_DEPTH = 5.5 * _SCALE
GOAL_WIDTH = 18.32 * _SCALE
PEN_SPOT_DIST = 11.0 * _SCALE
CORNER_R = 1.0 * _SCALE
SPOT_R = 0.12 * _SCALE

RENDER_DIR = Path("/workspace/blender/renders/parts")


def make_grass_material(name: str) -> bpy.types.Material:
    """芝生 — 刈り跡ストライプ + ノイズ"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.92
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec:
        spec.default_value = 0.08

    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)

    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 18.0 / _SCALE
    wave.inputs["Distortion"].default_value = 1.5
    wave.inputs["Detail"].default_value = 3.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (0.015, 0.10, 0.028, 1.0)
    ramp.color_ramp.elements[1].position = 0.58
    ramp.color_ramp.elements[1].color = (0.028, 0.16, 0.042, 1.0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 55.0
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 0.55

    mix_noise = nodes.new("ShaderNodeMixRGB")
    mix_noise.blend_type = "OVERLAY"
    mix_noise.inputs["Fac"].default_value = 0.35

    bump_noise = nodes.new("ShaderNodeTexNoise")
    bump_noise.inputs["Scale"].default_value = 120.0
    bump_noise.inputs["Detail"].default_value = 6.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix_noise.inputs[1])
    links.new(noise.outputs["Color"], mix_noise.inputs[2])
    links.new(mix_noise.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_line_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.97, 0.97, 0.97, 1.0)
    emit.inputs["Strength"].default_value = 1.0
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def clear_all() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def setup_black_world() -> None:
    scene = bpy.context.scene
    for w in list(bpy.data.worlds):
        bpy.data.worlds.remove(w)
    world = bpy.data.worlds.new("World_Black")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs[1].default_value = 1.0
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.15
    scene.view_settings.gamma = 1.0


def setup_lights() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 2.8
    sun_obj = bpy.data.objects.new("Sun", sun)
    bpy.context.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = Euler((math.radians(48), math.radians(8), math.radians(22)))
    fill = bpy.data.lights.new("Fill", "AREA")
    fill.energy = 180
    fill.size = 80
    fill_obj = bpy.data.objects.new("Fill", fill)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = Vector((0, 0, 60))
    fill_obj.rotation_euler = Euler((0, 0, 0))


def add_plane(name: str, sx: float, sy: float, loc: Vector, mat, z_rot: float = 0.0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx / 2, sy / 2, 1)
    obj.rotation_euler = (0, 0, z_rot)
    obj.data.materials.append(mat)
    return obj


def add_line_segment(name: str, x1: float, y1: float, x2: float, y2: float, mat, z: float) -> None:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    length = math.hypot(x2 - x1, y2 - y1)
    angle = math.atan2(y2 - y1, x2 - x1)
    add_plane(name, length, LINE_W, Vector((mx, my, z)), mat, angle)


def add_circle_ring(
    name: str, cx: float, cy: float, radius: float, mat, z: float,
    segments: int = 96, arc_start: float = 0.0, arc_end: float = 2 * math.pi,
) -> None:
    for i in range(segments):
        t0 = arc_start + (arc_end - arc_start) * i / segments
        t1 = arc_start + (arc_end - arc_start) * (i + 1) / segments
        x1, y1 = cx + math.cos(t0) * radius, cy + math.sin(t0) * radius
        x2, y2 = cx + math.cos(t1) * radius, cy + math.sin(t1) * radius
        add_line_segment(f"{name}_{i:03d}", x1, y1, x2, y2, mat, z)


def add_filled_spot(name: str, cx: float, cy: float, radius: float, mat, z: float) -> None:
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=radius, location=(cx, cy, z))
    spot = bpy.context.active_object
    spot.name = name
    spot.data.materials.append(mat)
    bpy.ops.object.transform_apply(scale=True)


def build_field_only() -> None:
    clear_all()
    setup_black_world()
    setup_lights()

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 1

    grass = make_grass_material("Grass")
    white = make_line_material("LineWhite")
    half_l = PITCH_LENGTH / 2
    half_w = PITCH_WIDTH / 2
    lz = 0.025

    # 芝生 — 完全な長方形（Subsurfなし＝角が丸くならない）
    add_plane("Field_Grass", PITCH_LENGTH, PITCH_WIDTH, Vector((0, 0, 0)), grass)

    # --- 外枠 ---
    add_line_segment("Line_Top", -half_l, half_w, half_l, half_w, white, lz)
    add_line_segment("Line_Bottom", -half_l, -half_w, half_l, -half_w, white, lz)
    add_line_segment("Line_Left", -half_l, -half_w, -half_l, half_w, white, lz)
    add_line_segment("Line_Right", half_l, -half_w, half_l, half_w, white, lz)

    # ハーフウェイ
    add_line_segment("Line_Halfway", 0, -half_w, 0, half_w, white, lz)

    # センターサークル & スポット
    add_circle_ring("Line_CenterCircle", 0, 0, CENTER_R, white, lz)
    add_filled_spot("Line_CenterSpot", 0, 0, SPOT_R, white, lz)

    for side, gx in (("L", -half_l), ("R", half_l)):
        sign = 1 if gx < 0 else -1
        inner_pen = gx + sign * PEN_DEPTH
        inner_goal = gx + sign * GOAL_DEPTH
        py = PEN_WIDTH / 2
        gy = GOAL_WIDTH / 2

        # ペナルティエリア
        add_line_segment(f"PenFront_{side}", gx, -py, gx, py, white, lz)
        add_line_segment(f"PenTop_{side}", gx, py, inner_pen, py, white, lz)
        add_line_segment(f"PenBottom_{side}", gx, -py, inner_pen, -py, white, lz)

        # ゴールエリア
        add_line_segment(f"GoalFront_{side}", gx, -gy, gx, gy, white, lz)
        add_line_segment(f"GoalTop_{side}", gx, gy, inner_goal, gy, white, lz)
        add_line_segment(f"GoalBottom_{side}", gx, -gy, inner_goal, -gy, white, lz)

        # PKスポット
        spot_x = gx + sign * PEN_SPOT_DIST
        add_filled_spot(f"PenSpot_{side}", spot_x, 0, SPOT_R, white, lz)

        # PKアーク（ペナルティエリアの外側＝フィールド中央側の弧）
        dx_line = PEN_DEPTH - PEN_SPOT_DIST
        if dx_line < CENTER_R:
            base = math.acos(dx_line / CENTER_R)
            if side == "L":
                add_circle_ring(f"PenArc_{side}", spot_x, 0, CENTER_R, white, lz, 48, -base, base)
            else:
                add_circle_ring(f"PenArc_{side}", spot_x, 0, CENTER_R, white, lz, 48, math.pi - base, math.pi + base)

    # コーナーアーク（1m、各隅の内側）
    corners = [
        ("TL", -half_l, half_w, -half_l + CORNER_R, half_w - CORNER_R, math.pi, math.pi * 1.5),
        ("BL", -half_l, -half_w, -half_l + CORNER_R, -half_w + CORNER_R, math.pi * 0.5, math.pi),
        ("TR", half_l, half_w, half_l - CORNER_R, half_w - CORNER_R, math.pi * 1.5, math.pi * 2),
        ("BR", half_l, -half_w, half_l - CORNER_R, -half_w + CORNER_R, 0, math.pi * 0.5),
    ]
    for label, _cx, _cy, ox, oy, a0, a1 in corners:
        add_circle_ring(f"Corner_{label}", ox, oy, CORNER_R, white, lz, 20, a0, a1)

    from build_goal import build_both_goals  # noqa: E402

    build_both_goals(half_l)

    print(f"Field: {PITCH_LENGTH:.1f}x{PITCH_WIDTH:.1f}m FIFA markings + grass stripes + 2 goals")


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def render_wide() -> Path:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    field_aspect = PITCH_LENGTH / PITCH_WIDTH
    scene.render.resolution_y = 1080
    scene.render.resolution_x = int(scene.render.resolution_y * field_aspect)
    scene.eevee.taa_render_samples = 64
    setup_black_world()
    _remove_cameras()

    cam_data = bpy.data.cameras.new("CamWide")
    cam = bpy.data.objects.new("CamWide", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, 0, 220)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    cam.data.type = "ORTHO"
    # 縦幅＝ピッチ幅ぴったり → 横もピッチ長に一致、左右の黒帯なし
    cam.data.ortho_scale = PITCH_WIDTH

    out = RENDER_DIR / "field_wide.png"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"Wide: {out}")
    return out


def render_grass_close() -> Path:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.eevee.taa_render_samples = 96
    setup_black_world()
    _remove_cameras()

    cam_data = bpy.data.cameras.new("CamGrass")
    cam = bpy.data.objects.new("CamGrass", cam_data)
    bpy.context.collection.objects.link(cam)
    # センター付近の芝を斜めから寄る
    cam.location = Vector((8.0, -12.0, 3.5))
    cam.rotation_euler = Euler((math.radians(72), 0, math.radians(28)))
    scene.camera = cam
    cam.data.type = "PERSP"
    cam.data.lens = 65

    out = RENDER_DIR / "field_grass_close.png"
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"Close: {out}")
    return out


def save_blend(path: Path) -> None:
    bpy.ops.wm.save_mainfile(filepath=str(path))
    print(f"Saved: {path}")


def render_goal_three_quarter(side: str = "L") -> Path:
    """参考画像風 — 斜め前方から"""
    from build_goal import GOAL_H  # noqa: E402

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.eevee.taa_render_samples = 80
    setup_black_world()
    setup_lights()
    _remove_cameras()

    half_l = PITCH_LENGTH / 2
    gx = -half_l if side == "L" else half_l
    sign = 1 if side == "L" else -1

    cam_data = bpy.data.cameras.new("CamGoal3Q")
    cam = bpy.data.objects.new("CamGoal3Q", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = Vector((gx + sign * 14, -16, 4.2))
    target = Vector((gx, 0, GOAL_H * 0.42))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    cam.data.lens = 55

    out = RENDER_DIR / f"goal_{side.lower()}_3quarter.png"
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"Goal 3/4: {out}")
    return out


def render_goal_front(side: str = "L") -> Path:
    """ゴール真正面 — 門の中心を正面から"""
    from build_goal import GOAL_H  # noqa: E402

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.eevee.taa_render_samples = 80
    setup_black_world()
    setup_lights()
    _remove_cameras()

    half_l = PITCH_LENGTH / 2
    gx = -half_l if side == "L" else half_l
    dist = 20.0
    eye_z = GOAL_H * 0.48
    target = Vector((gx, 0, GOAL_H * 0.5))

    if side == "L":
        cam_pos = Vector((gx + dist, 0, eye_z))
    else:
        cam_pos = Vector((gx - dist, 0, eye_z))

    cam_data = bpy.data.cameras.new("CamGoalFront")
    cam = bpy.data.objects.new("CamGoalFront", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = cam_pos
    direction = target - cam_pos
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    cam.data.lens = 42

    out = RENDER_DIR / f"goal_{side.lower()}_front.png"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"Goal front: {out}")
    return out


def render_goal_close(side: str = "L") -> Path:
    """ゴールの斜めアップ"""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.eevee.taa_render_samples = 64
    setup_black_world()
    _remove_cameras()

    half_l = PITCH_LENGTH / 2
    gx = -half_l if side == "L" else half_l

    cam_data = bpy.data.cameras.new("CamGoal")
    cam = bpy.data.objects.new("CamGoal", cam_data)
    bpy.context.collection.objects.link(cam)
    offset = 22 if side == "L" else -22
    cam.location = Vector((gx + offset, -18, 5.5))
    cam.rotation_euler = Euler((math.radians(78), 0, math.radians(32 if side == "L" else -32)))
    scene.camera = cam
    cam.data.lens = 50

    out = RENDER_DIR / f"goal_{side.lower()}_close.png"
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"Goal close: {out}")
    return out


def main() -> None:
    blend = resolve_blend_path()
    open_blend(blend)
    build_field_only()
    save_blend(blend)
    if "--render" in sys.argv:
        render_wide()
        render_grass_close()
        render_goal_close("L")
        render_goal_close("R")
    if "--render-goal-front" in sys.argv:
        render_goal_front("L")
        render_goal_front("R")
        render_goal_three_quarter("L")


if __name__ == "__main__":
    main()
