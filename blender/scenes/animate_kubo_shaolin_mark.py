# SPDX-License-Identifier: MIT
"""日本代表・久保建英 vs 少林接着マーク — 少林ドリブル＋久保並走奪取"""

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

MARK_FRAMES = 240
FPS = 24

# 久保＝青、少林＝上半身オレンジ・下半身白
KUBO_BLUE = (0.12, 0.45, 0.95, 1.0)
SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
SHAOLIN_WHITE = (0.96, 0.96, 0.98, 1.0)

# 左ゴール（-X）へ進む — 向き固定（くるくる回転を防ぐ）
MOVE_YAW = math.pi * 1.5

# 久保の並走距離（横）と奪いにかかる突込
MARK_SIDE = 1.35
MARK_LAG = 0.55


def _remove_all_players() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("Blue_", "Red_", "Japan_", "Shaolin_", "Kubo_")):
            bpy.data.objects.remove(obj, do_unlink=True)


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _move_dir(frame: int) -> Vector:
    p0 = _shaolin_path(max(1, frame - 3))
    p1 = _shaolin_path(min(MARK_FRAMES, frame + 3))
    d = p1 - p0
    d.z = 0.0
    if d.length < 1e-5:
        return Vector((-1.0, 0.0, 0.0))
    return d.normalized()


def _shaolin_path(frame: int) -> Vector:
    """少林 — 細かいタッチのドリブルで前進"""
    t = (frame - 1) / max(1, MARK_FRAMES - 1)
    x = 28.0 - t * 42.0
    y = (
        1.6 * math.sin(t * 9.0 * math.pi)
        + 1.0 * math.sin(t * 14.0 * math.pi + 0.6)
        + 0.6 * math.sin(t * 21.0 * math.pi + 1.1)
    )
    return Vector((x, y, 0.0))


def _kubo_path(frame: int, shaolin: Vector, move_dir: Vector) -> Vector:
    """久保 — 横並走しつつ足元を狙って突込む"""
    right = _right_of(move_dir)
    # 定期的にボール側へ詰める（奪取トライ）が離れない
    surge = 0.55 * max(0.0, math.sin(frame * 0.21)) ** 3
    side = MARK_SIDE - surge
    return shaolin + move_dir * MARK_LAG + right * side


def _ball_at_feet(shaolin: Vector, frame: int, move_dir: Vector) -> Vector:
    """ボール — 少林の足元に接着（細かいタッチ）"""
    phase = frame * 0.58
    ahead = 0.38 + 0.08 * math.sin(phase * 2.1)
    side = 0.22 * math.sin(phase * 3.6) + 0.12 * math.sin(phase * 5.8)
    right = _right_of(move_dir)
    p = shaolin + move_dir * ahead + right * side
    p.z = BALL_GROUND_Z
    return p


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


def setup_kubo_mark_characters() -> Tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()

    shaolin_arm = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [Vector((28, 0, 0))],
        actions=["run"],
        facing_yaw=MOVE_YAW,
    )[0]
    kubo_arm = build_team(
        "Kubo",
        KUBO_BLUE,
        [Vector((27, 1.4, 0))],
        actions=["run"],
        facing_yaw=MOVE_YAW,
    )[0]

    set_mesh_split_vertical(_mesh_child(shaolin_arm), SHAOLIN_ORANGE, SHAOLIN_WHITE, z_cut=0.42)

    return kubo_arm, shaolin_arm, _root_of(kubo_arm), _root_of(shaolin_arm)


def animate_kubo_shaolin_mark() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = MARK_FRAMES
    scene.render.fps = FPS

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball not found — run build_field_only first")

    kubo_arm, shaolin_arm, kubo_root, shaolin_root = setup_kubo_mark_characters()

    for arm in (kubo_arm, shaolin_arm):
        _clear_all_nla(arm)
    if ball.animation_data:
        ball.animation_data_clear()

    shaolin_keys: List[Tuple[int, Vector]] = []
    kubo_keys: List[Tuple[int, Vector]] = []
    for f in range(1, MARK_FRAMES + 1):
        s = _shaolin_path(f)
        md = _move_dir(f)
        shaolin_keys.append((f, s))
        kubo_keys.append((f, _kubo_path(f, s, md)))

    _animate_root_fixed(shaolin_root, shaolin_keys, MOVE_YAW)
    _animate_root_fixed(kubo_root, kubo_keys, MOVE_YAW)

    _add_nla_strip(shaolin_arm, "run", 1, MARK_FRAMES)
    _add_nla_strip(kubo_arm, "run", 1, MARK_FRAMES)

    for f in range(1, MARK_FRAMES + 1):
        s = _shaolin_path(f)
        _kf_loc(ball, f, _ball_at_feet(s, f, _move_dir(f)))
    _ease_all_ball_keyframes(ball)

    setup_kubo_mark_camera()
    scene.frame_set(1)
    print(f"Kubo mark v2: {MARK_FRAMES}f — Shaolin dribble + Kubo parallel mark")


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_kubo_mark_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamKuboMark")
    cam = bpy.data.objects.new("CamKuboMark", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 38

    for f in (1, 60, 120, 180, MARK_FRAMES):
        s = _shaolin_path(f)
        k = _kubo_path(f, s, _move_dir(f))
        mid = (s + k) * 0.5
        _kf_cam(cam, f, Vector((mid.x + 12, mid.y - 14, 3.8)), Vector((mid.x - 3, mid.y, 0.9)))

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def render_kubo_mark_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = MARK_FRAMES
    scene.eevee.taa_render_samples = 8

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "kubo_shaolin_mark.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering kubo mark video: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-kubo-mark-video" in sys.argv:
        render_kubo_mark_video()
    else:
        animate_kubo_shaolin_mark()
        bpy.ops.wm.save_mainfile(filepath=str(blend))
