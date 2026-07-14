# SPDX-License-Identifier: MIT
"""オランダ代表 vs 少林 — 横並走ドリブル争奪

二人は同じ向きで並走。体は重ねず、ボールをどちらが取るか競る。
オランダは濃いオレンジ一色。
"""

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

FPS = 24
CONTEST_FRAMES = 216  # 約9秒

# 左ゴール（-X）へ前進。二人とも同じ向き
MOVE_YAW = math.pi * 1.5

# 横の最小離隔（体を重ねない）
SIDE_GAP = 2.1
# 少し前後ずらしつつ並走
NED_LAG = -0.15
SHAOLIN_LAG = 0.25

# オランダ：濃いオレンジ一色 / 少林：明るいオレンジ一色
NETHERLANDS_ORANGE = (0.62, 0.16, 0.0, 1.0)
SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)


def _remove_all_players() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(
            (
                "Blue_",
                "Red_",
                "Japan_",
                "Shaolin_",
                "Kubo_",
                "Endo_",
                "Shin_",
                "Leao_",
                "Ronaldo_",
                "Fernandes_",
                "PortugalGK_",
                "Netherlands_",
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _pack_center(frame: int) -> Vector:
    """二人の並走パック中心（左方向へ前進）。"""
    t = (frame - 1) / max(1, CONTEST_FRAMES - 1)
    x = 18.0 - t * 36.0
    # わずかなカーブでピッチ感
    y = 0.8 * math.sin(t * 2.2 * math.pi) + 0.35 * math.sin(t * 5.5 * math.pi + 0.4)
    return Vector((x, y, 0.0))


def _move_dir(frame: int) -> Vector:
    p0 = _pack_center(max(1, frame - 3))
    p1 = _pack_center(min(CONTEST_FRAMES, frame + 3))
    d = p1 - p0
    d.z = 0.0
    if d.length < 1e-5:
        return Vector((-1.0, 0.0, 0.0))
    return d.normalized()


def _possession(frame: int) -> float:
    """-1=少林寄り、+1=オランダ寄り。どちらが取るか揺れる。"""
    # ゆっくり交代＋短い奪取トライ
    slow = math.sin(frame * 0.045)
    jab = math.sin(frame * 0.19) ** 3
    return max(-1.0, min(1.0, 0.75 * slow + 0.45 * jab))


def _ned_path(frame: int) -> Vector:
    """オランダ — 進行方向正面、右側レーンを並走。"""
    mid = _pack_center(frame)
    md = _move_dir(frame)
    right = _right_of(md)
    # ボール寄りの寄りは控えめ（離隔を保つ）
    pos = _possession(frame)
    close = 0.18 * max(0.0, pos)  # ボール側（中央）へ少しだけ
    return mid + md * NED_LAG + right * (SIDE_GAP * 0.5 - close)


def _shaolin_path(frame: int) -> Vector:
    """少林 — 進行方向正面、左側レーンを並走。"""
    mid = _pack_center(frame)
    md = _move_dir(frame)
    right = _right_of(md)
    pos = _possession(frame)
    close = 0.18 * max(0.0, -pos)
    return mid + md * SHAOLIN_LAG + right * (-SIDE_GAP * 0.5 + close)


def _ball_path(frame: int) -> Vector:
    """二人の間・足元でタッチ争奪。どちら寄りかは possession で揺らす。"""
    ned = _ned_path(frame)
    shin = _shaolin_path(frame)
    md = _move_dir(frame)
    right = _right_of(md)
    pos = _possession(frame)
    # 基本は二人の中点、寄りは両レーンの間だけ（体と重ねない）
    mid = (ned + shin) * 0.5
    toward = right * (0.55 * pos)
    phase = frame * 0.62
    ahead = 0.42 + 0.1 * math.sin(phase * 2.0)
    touch = 0.14 * math.sin(phase * 3.4) * right
    p = mid + md * ahead + toward + touch
    p.z = BALL_GROUND_Z + abs(math.sin(phase * 2.6)) * 0.08
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


def setup_characters() -> Tuple[
    bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object
]:
    from import_mannequiny import build_team  # noqa: E402

    _remove_all_players()
    start = _pack_center(1)
    md = _move_dir(1)
    right = _right_of(md)
    ned = build_team(
        "Netherlands",
        NETHERLANDS_ORANGE,
        [start + md * NED_LAG + right * (SIDE_GAP * 0.5)],
        actions=["run"],
        facing_yaw=MOVE_YAW,
    )[0]
    shin = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [start + md * SHAOLIN_LAG + right * (-SIDE_GAP * 0.5)],
        actions=["run"],
        facing_yaw=MOVE_YAW,
    )[0]
    # オランダは濃いオレンジ一色（split なし）
    return ned, shin, _root_of(ned), _root_of(shin)


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamNetherlandsContest")
    cam = bpy.data.objects.new("CamNetherlandsContest", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_data.lens = 30

    key_frames = list(range(1, CONTEST_FRAMES + 1, 12))
    if CONTEST_FRAMES not in key_frames:
        key_frames.append(CONTEST_FRAMES)

    for f in key_frames:
        mid = (_ned_path(f) + _shaolin_path(f)) * 0.5
        md = _move_dir(f)
        right = _right_of(md)
        ball = _ball_path(f)
        # 斜め後方から二人＋ボールを捉える
        pos = ball - md * 6.5 + right * 4.2 + Vector((0.0, 0.0, 2.8))
        tgt = mid + md * 1.2 + Vector((0.0, 0.0, 1.15))
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_netherlands_shaolin_contest() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = CONTEST_FRAMES
    scene.render.fps = FPS

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball not found — run build_field_only first")

    ned_arm, shin_arm, ned_root, shin_root = setup_characters()
    for arm in (ned_arm, shin_arm):
        _clear_all_nla(arm)
    if ball.animation_data:
        ball.animation_data_clear()

    ned_keys: List[Tuple[int, Vector]] = []
    shin_keys: List[Tuple[int, Vector]] = []
    for f in range(1, CONTEST_FRAMES + 1):
        ned_keys.append((f, _ned_path(f)))
        shin_keys.append((f, _shaolin_path(f)))

    _animate_root_fixed(ned_root, ned_keys, MOVE_YAW)
    _animate_root_fixed(shin_root, shin_keys, MOVE_YAW)

    _add_nla_strip(ned_arm, "run", 1, CONTEST_FRAMES)
    _add_nla_strip(shin_arm, "run", 1, CONTEST_FRAMES)

    for f in range(1, CONTEST_FRAMES + 1):
        _kf_loc(ball, f, _ball_path(f))
    _ease_all_ball_keyframes(ball)

    setup_camera()
    scene.frame_set(1)
    print(
        f"Netherlands vs Shaolin parallel dribble: {CONTEST_FRAMES}f @ {FPS}fps — "
        "same-facing side-by-side contest (~9s)"
    )


def render_netherlands_shaolin_contest_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = CONTEST_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    out = RENDER_DIR / "netherlands_shaolin_contest.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Netherlands parallel contest: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-netherlands-contest-video" in sys.argv:
        render_netherlands_shaolin_contest_video()
    else:
        animate_netherlands_shaolin_contest()
