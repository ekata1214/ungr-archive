# SPDX-License-Identifier: MIT
"""遠藤航 vs 少林幽霊ドリブル — 半透明すり抜けでタックルが空振り"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import bpy
from mathutils import Vector

from animate_soccer_match import (
    BALL_GROUND_Z,
    _add_nla_strip,
    _clear_all_nla,
    _clear_anim,
    _ease_all_ball_keyframes,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

GHOST_FRAMES = 240
FPS = 24

SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
SHAOLIN_WHITE = (0.96, 0.96, 0.98, 1.0)
ENDO_NAVY = (0.07, 0.14, 0.52, 1.0)

MOVE_YAW = math.pi * 1.5

# 遠藤のタックル試行ピーク（この前後で少林が幽霊化）
TACKLE_PEAKS = (42, 102, 162)
GHOST_HALF = 20
GHOST_ALPHA_MIN = 0.22


def _remove_all_players() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("Blue_", "Red_", "Japan_", "Shaolin_", "Kubo_", "Endo_")):
            bpy.data.objects.remove(obj, do_unlink=True)


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _base_shaolin_path(frame: int) -> Vector:
    t = (frame - 1) / max(1, GHOST_FRAMES - 1)
    x = 30.0 - t * 44.0
    y = (
        1.4 * math.sin(t * 8.5 * math.pi)
        + 0.9 * math.sin(t * 13.5 * math.pi + 0.5)
        + 0.5 * math.sin(t * 20.0 * math.pi + 1.0)
    )
    return Vector((x, y, 0.0))


def _move_dir(frame: int) -> Vector:
    p0 = _base_shaolin_path(max(1, frame - 3))
    p1 = _base_shaolin_path(min(GHOST_FRAMES, frame + 3))
    d = p1 - p0
    d.z = 0.0
    if d.length < 1e-5:
        return Vector((-1.0, 0.0, 0.0))
    return d.normalized()


def _ghost_strength(frame: int) -> float:
    strength = 0.0
    for peak in TACKLE_PEAKS:
        dist = abs(frame - peak)
        if dist > GHOST_HALF:
            continue
        t = 1.0 - dist / GHOST_HALF
        strength = max(strength, t * t)
    return strength


def _shaolin_path(frame: int) -> Vector:
    """地面すれすれ — タックル時に横へ幽霊すり抜け"""
    base = _base_shaolin_path(frame)
    md = _move_dir(frame)
    g = _ghost_strength(frame)
    if g < 1e-4:
        return base
    right = _right_of(md)
    slip = right * 1.55 * g + md * 0.75 * g
    return base + slip


def _endo_path(frame: int, shaolin: Vector, ball: Vector, move_dir: Vector) -> Vector:
    """遠藤 — 前で守備、タックル突込 → 空振り"""
    right = _right_of(move_dir)
    guard = shaolin + move_dir * 2.1 + right * (-1.05)

    surge = 0.0
    for peak in TACKLE_PEAKS:
        dist = abs(frame - peak)
        if dist > 14:
            continue
        t = 1.0 - dist / 14.0
        surge = max(surge, t ** 1.6)

    if surge > 0.0:
        to_ball = ball - guard
        to_ball.z = 0.0
        if to_ball.length > 1e-5:
            guard = guard + to_ball.normalized() * 1.35 * surge
    return guard


def _ball_at_feet(shaolin: Vector, frame: int, move_dir: Vector) -> Vector:
    phase = frame * 0.58
    ahead = 0.36 + 0.07 * math.sin(phase * 2.0)
    side = 0.20 * math.sin(phase * 3.5) + 0.11 * math.sin(phase * 5.6)
    right = _right_of(move_dir)
    p = shaolin + move_dir * ahead + right * side
    p.z = BALL_GROUND_Z
    return p


def _ghost_alpha(frame: int) -> float:
    g = _ghost_strength(frame)
    if g < 1e-4:
        return 1.0
    return 1.0 - (1.0 - GHOST_ALPHA_MIN) * g


def _animate_root_fixed(
    root: bpy.types.Object,
    keys: List[Tuple[int, Vector]],
    yaw: float,
) -> None:
    _clear_anim(root)
    for f, loc in keys:
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _enable_material_blend(mesh_obj: bpy.types.Object) -> None:
    for mat in mesh_obj.data.materials:
        if not mat:
            continue
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        try:
            mat.shadow_method = "HASHED"
        except Exception:
            pass


def _kf_mesh_alpha(mesh_obj: bpy.types.Object, frame: int, alpha: float) -> None:
    for mat in mesh_obj.data.materials:
        if not mat or not mat.node_tree:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            continue
        inp = bsdf.inputs.get("Alpha")
        if inp is None:
            continue
        inp.default_value = alpha
        inp.keyframe_insert("default_value", frame=frame)


def setup_endo_ghost_characters() -> Tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()

    shaolin_arm = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [Vector((30, 0, 0))],
        actions=["run"],
        facing_yaw=MOVE_YAW,
    )[0]
    endo_arm = build_team(
        "Endo",
        ENDO_NAVY,
        [Vector((28, -1.0, 0))],
        actions=["run"],
        facing_yaw=MOVE_YAW,
    )[0]

    shaolin_mesh = _mesh_child(shaolin_arm)
    set_mesh_split_vertical(shaolin_mesh, SHAOLIN_ORANGE, SHAOLIN_WHITE, z_cut=0.42)
    _enable_material_blend(shaolin_mesh)

    return endo_arm, shaolin_arm, _root_of(endo_arm), _root_of(shaolin_arm)


def animate_endo_shaolin_ghost() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = GHOST_FRAMES
    scene.render.fps = FPS

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball not found — run build_field_only first")

    endo_arm, shaolin_arm, endo_root, shaolin_root = setup_endo_ghost_characters()
    shaolin_mesh = next(ch for ch in shaolin_arm.children if ch.type == "MESH")

    for arm in (endo_arm, shaolin_arm):
        _clear_all_nla(arm)
    if ball.animation_data:
        ball.animation_data_clear()

    shaolin_keys: List[Tuple[int, Vector]] = []
    endo_keys: List[Tuple[int, Vector]] = []
    alpha_keys: List[Tuple[int, float]] = []

    for f in range(1, GHOST_FRAMES + 1):
        s = _shaolin_path(f)
        md = _move_dir(f)
        ball_p = _ball_at_feet(s, f, md)
        shaolin_keys.append((f, s))
        endo_keys.append((f, _endo_path(f, s, ball_p, md)))
        alpha_keys.append((f, _ghost_alpha(f)))

    _animate_root_fixed(shaolin_root, shaolin_keys, MOVE_YAW)
    _animate_root_fixed(endo_root, endo_keys, MOVE_YAW)

    _add_nla_strip(shaolin_arm, "run", 1, GHOST_FRAMES)
    _add_nla_strip(endo_arm, "run", 1, GHOST_FRAMES)

    for f in range(1, GHOST_FRAMES + 1):
        s = shaolin_keys[f - 1][1]
        _kf_loc(ball, f, _ball_at_feet(s, f, _move_dir(f)))
    _ease_all_ball_keyframes(ball)

    # 幽霊化アルファ（18f刻み + タックルピーク付近）
    alpha_frame_set = set(range(1, GHOST_FRAMES + 1, 12))
    for peak in TACKLE_PEAKS:
        for d in range(-GHOST_HALF, GHOST_HALF + 1, 4):
            alpha_frame_set.add(max(1, min(GHOST_FRAMES, peak + d)))
    alpha_frame_set.add(GHOST_FRAMES)
    for f in sorted(alpha_frame_set):
        _kf_mesh_alpha(shaolin_mesh, f, alpha_keys[f - 1][1])

    setup_endo_ghost_camera()
    scene.frame_set(1)
    print(f"Endo ghost: {GHOST_FRAMES}f — Shaolin phantom dribble + Endo whiff")


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_endo_ghost_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamEndoGhost")
    cam = bpy.data.objects.new("CamEndoGhost", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 28

    key_frames = list(range(1, GHOST_FRAMES + 1, 18))
    if GHOST_FRAMES not in key_frames:
        key_frames.append(GHOST_FRAMES)

    for f in key_frames:
        s = _shaolin_path(f)
        md = _move_dir(f)
        ball = _ball_at_feet(s, f, md)
        right = _right_of(md)
        cam_pos = ball + md * 2.6 + right * (-3.4) + Vector((0.0, 0.0, 0.92))
        cam_tgt = ball + Vector((0.0, 0.0, 0.10))
        _kf_cam(cam, f, cam_pos, cam_tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def render_endo_ghost_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = GHOST_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.film_transparent = False

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "endo_shaolin_ghost.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering endo ghost video: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-endo-ghost-video" in sys.argv:
        render_endo_ghost_video()
    else:
        animate_endo_shaolin_ghost()
        bpy.ops.wm.save_mainfile(filepath=str(blend))
