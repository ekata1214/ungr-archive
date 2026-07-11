# SPDX-License-Identifier: MIT
"""日本代表・久保建英 vs 少林接着マーク — ドリブル幻惑とボール密着マーク"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import bpy
from mathutils import Euler, Vector

from animate_soccer_match import (
    BALL_GROUND_Z,
    _add_nla_strip,
    _clear_all_nla,
    _clear_anim,
    _ease_all_ball_keyframes,
    _kf_loc,
    _kf_rot_z,
    _root_of,
    _yaw_from_dir,
)

MARK_FRAMES = 240
FPS = 24

# 接着マーク距離（ボール中心から少林兄の胸元付近）
GLUE_BEHIND = 0.55
GLUE_SIDE = -0.18

# 日本＝白、少林＝赤
JAPAN_COLOR = (0.96, 0.96, 0.98, 1.0)
SHAOLIN_COLOR = (0.92, 0.18, 0.15, 1.0)


def _remove_team_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("Blue_", "Red_", "Japan_", "Shaolin_")):
            bpy.data.objects.remove(obj, do_unlink=True)


def _move_keys(
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


def _kubo_path(frame: int) -> Vector:
    """久保 — 左ゴールへ細かく切れ込むドリブルライン"""
    t = (frame - 1) / max(1, MARK_FRAMES - 1)
    x = 32.0 - t * 46.0
    y = (
        2.2 * math.sin(t * 10.0 * math.pi)
        + 1.4 * math.sin(t * 16.0 * math.pi + 0.7)
        + 0.8 * math.sin(t * 23.0 * math.pi + 1.2)
    )
    return Vector((x, y, 0.0))


def _dir_at(frame: int) -> Vector:
    p0 = _kubo_path(max(1, frame - 2))
    p1 = _kubo_path(min(MARK_FRAMES, frame + 2))
    d = p1 - p0
    d.z = 0.0
    if d.length < 1e-5:
        return Vector((-1.0, 0.0, 0.0))
    return d.normalized()


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _fine_ball_pos(kubo: Vector, frame: int, move_dir: Vector) -> Vector:
    """細かいタッチ — 足元でボールが左右に素早く転がる"""
    phase = frame * 0.62
    ahead = 0.42 + 0.10 * math.sin(phase * 2.3)
    side = 0.30 * math.sin(phase * 3.9) + 0.18 * math.sin(phase * 6.1 + 0.4)
    right = _right_of(move_dir)
    p = kubo + move_dir * ahead + right * side
    p.z = BALL_GROUND_Z
    return p


def _glue_marker_pos(ball: Vector, move_dir: Vector) -> Vector:
    """少林の兄 — ボールに接着した位置（常にボール真後ろ寄り）"""
    right = _right_of(move_dir)
    p = ball - move_dir * GLUE_BEHIND + right * GLUE_SIDE
    p.z = 0.0
    return p


def setup_kubo_mark_characters() -> Tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import build_team  # noqa: E402

    _remove_team_objects()
    kubo_arm = build_team(
        "Japan",
        JAPAN_COLOR,
        [Vector((32, 0, 0))],
        actions=["run"],
        facing_yaw=math.pi / 2,
    )[0]
    shaolin_arm = build_team(
        "Shaolin",
        SHAOLIN_COLOR,
        [Vector((31, 0.5, 0))],
        actions=["run"],
        facing_yaw=math.pi / 2,
    )[0]
    kubo_root = _root_of(kubo_arm)
    shaolin_root = _root_of(shaolin_arm)
    return kubo_arm, shaolin_arm, kubo_root, shaolin_root  # type: ignore[return-value]


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

    attack_yaw = math.pi / 2
    yaw_offset = math.pi  # Mannequiny 正面補正

    kubo_keys: List[Tuple[int, Vector]] = []
    shaolin_keys: List[Tuple[int, Vector]] = []
    for f in range(1, MARK_FRAMES + 1):
        kubo_keys.append((f, _kubo_path(f)))
        md = _dir_at(f)
        ball_p = _fine_ball_pos(kubo_keys[-1][1], f, md)
        shaolin_keys.append((f, _glue_marker_pos(ball_p, md)))

    # 向きは進行方向
    _clear_anim(kubo_root)
    _clear_anim(shaolin_root)
    last_yaw = attack_yaw
    for i, (f, loc) in enumerate(kubo_keys):
        if i + 1 < len(kubo_keys):
            d = kubo_keys[i + 1][1] - loc
            if d.length > 1e-5:
                last_yaw = _yaw_from_dir(d, last_yaw)
        yaw = last_yaw + yaw_offset
        _kf_loc(kubo_root, f, loc)
        _kf_rot_z(kubo_root, f, yaw)
        _kf_loc(shaolin_root, f, shaolin_keys[i][1])
        _kf_rot_z(shaolin_root, f, yaw)

    for fc in kubo_root.animation_data.action.fcurves:  # type: ignore[union-attr]
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
    for fc in shaolin_root.animation_data.action.fcurves:  # type: ignore[union-attr]
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"

    _add_nla_strip(kubo_arm, "run", 1, MARK_FRAMES)
    _add_nla_strip(shaolin_arm, "run", 1, MARK_FRAMES)

    for f in range(1, MARK_FRAMES + 1):
        md = _dir_at(f)
        _kf_loc(ball, f, _fine_ball_pos(_kubo_path(f), f, md))
    _ease_all_ball_keyframes(ball)

    setup_kubo_mark_camera()
    scene.frame_set(1)
    print(f"Kubo mark vignette: {MARK_FRAMES}f — Japan dribble + Shaolin glue mark")


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
    cam.data.lens = 42

    for f in (1, 60, 120, 180, MARK_FRAMES):
        k = _kubo_path(f)
        _kf_cam(cam, f, Vector((k.x + 14, k.y - 16, 4.2)), Vector((k.x - 4, k.y, 1.0)))

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
