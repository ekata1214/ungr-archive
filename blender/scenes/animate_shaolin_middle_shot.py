# SPDX-License-Identifier: MIT
"""少林ミドルシュート — GKが飛び出すが高速ボールがゴールイン

別カット。少林がミドルレンジからシュート、ポルトガルGKが止めきれずネットへ。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List

import bpy
from mathutils import Euler, Vector

from animate_soccer_match import (
    BALL_GROUND_Z,
    _clear_all_nla,
    _clear_anim,
    _ease_all_ball_keyframes,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24
SHOT_FRAMES = 288  # 約12秒

F_APPROACH_END = 96
F_PLANT = 108
F_KICK = 128  # 足が当たる＝ボールリリース
F_GK_DIVE = 134  # 少し早く飛び出すが、届かない
F_GOAL = 156
F_SETTLE = 220

_SCALE = 2.5
PITCH_HALF = 105.0 * _SCALE / 2  # 右ゴールライン x
GOAL_X = PITCH_HALF
GOAL_INNER_HALF_W = 7.32 * _SCALE / 2
GOAL_H = 2.44 * _SCALE

# 少林は +X ゴールへミドル（約24m相当）
SHAOLIN_YAW = math.pi / 2
GK_YAW = -math.pi / 2  # ボールを見る
SHAOLIN_START = Vector((18.0, -0.6, 0.0))
SHAOLIN_KICK_POS = Vector((GOAL_X - 58.0, -0.4, 0.0))  # ゴール前 ~23m、右気味
GK_HOME = Vector((GOAL_X - 3.2, 0.0, 0.0))

# ゴール右隅（攻撃向き＋Xから見て右側＝-Y）へ突き刺さる
BALL_GOAL = Vector((GOAL_X + 1.6, -GOAL_INNER_HALF_W * 0.78, GOAL_H * 0.70))

SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    exact = [c for c in candidates if c == name]
    return exact[0] if exact else sorted(candidates)[0]


def _add_nla_once_stretched(
    arm: bpy.types.Object, action_name: str, frame_start: int, frame_end: int
) -> None:
    resolved = _resolve_action_name(action_name)
    action = bpy.data.actions.get(resolved)
    if not action:
        raise KeyError(resolved)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = f"{resolved}_stretch"
    strip = track.strips.new(action.name, frame_start, action)
    act_start = int(action.frame_range[0])
    act_end = int(action.frame_range[1])
    act_len = max(1, act_end - act_start)
    duration = max(1, frame_end - frame_start)
    strip.action_frame_start = act_start
    strip.action_frame_end = act_end
    strip.frame_start = frame_start
    strip.scale = duration / float(act_len)
    strip.repeat = 1.0
    strip.frame_end = frame_start + act_len * strip.scale
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.use_auto_blend = False
    strip.influence = 1.0


def _add_nla_hold_pose(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
    action_frame: int = 10,
) -> None:
    resolved = _resolve_action_name(action_name)
    action = bpy.data.actions.get(resolved)
    if not action:
        raise KeyError(resolved)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = f"{resolved}_hold"
    strip = track.strips.new(action.name, frame_start, action)
    duration = max(1, frame_end - frame_start + 1)
    strip.action_frame_start = float(action_frame)
    strip.action_frame_end = float(action_frame + 1)
    strip.repeat = 1.0
    strip.scale = float(duration)
    strip.frame_start = float(frame_start)
    strip.frame_end = float(frame_start + duration)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.use_auto_blend = False
    strip.influence = 1.0


def _add_nla_loop(
    arm: bpy.types.Object, action_name: str, frame_start: int, frame_end: int
) -> None:
    resolved = _resolve_action_name(action_name)
    action = bpy.data.actions.get(resolved)
    if not action:
        raise KeyError(resolved)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = f"{resolved}_loop"
    strip = track.strips.new(action.name, frame_start, action)
    act_start = int(action.frame_range[0])
    act_end = int(action.frame_range[1])
    act_len = max(1, act_end - act_start)
    duration = max(1, frame_end - frame_start)
    strip.action_frame_start = act_start
    strip.action_frame_end = act_end
    strip.frame_start = frame_start
    strip.frame_end = frame_start + duration
    strip.repeat = max(1.0, duration / float(act_len))
    strip.scale = 1.0
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.use_auto_blend = False
    strip.influence = 1.0


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
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _shaolin_path(frame: int) -> Vector:
    if frame <= F_APPROACH_END:
        t = (frame - 1) / max(1, F_APPROACH_END - 1)
        p = SHAOLIN_START.lerp(SHAOLIN_KICK_POS, _ease_in_out(t))
        p.y += 0.35 * math.sin(t * 5.0 * math.pi)
        return p
    if frame <= F_KICK:
        t = (frame - F_APPROACH_END) / max(1, F_KICK - F_APPROACH_END)
        # 踏み込みでわずかに前進
        return SHAOLIN_KICK_POS + Vector((0.55 * _ease_in_out(t), -0.15 * t, 0.0))
    # キック後はフォローで少し前へ
    base = SHAOLIN_KICK_POS + Vector((0.55, -0.15, 0.0))
    t = (frame - F_KICK) / max(1, SHOT_FRAMES - F_KICK)
    return base + Vector((1.2 * _ease_in_out(min(1.0, t * 1.8)), 0.1 * t, 0.0))


def _gk_path(frame: int) -> Vector:
    # ゴール右（-Y）へ横っ飛び。ボール筋へ手は伸ばすが届かない
    dive_target = Vector((GOAL_X - 2.0, BALL_GOAL.y * 0.88, 0.0))
    if frame < F_GK_DIVE:
        t = (frame - 1) / max(1, F_GK_DIVE - 1)
        sway = Vector((0.0, BALL_GOAL.y * 0.18 * _ease_in_out(t), 0.0))
        return GK_HOME + sway
    if frame <= F_GOAL + 4:
        t = (frame - F_GK_DIVE) / max(1, (F_GOAL + 4) - F_GK_DIVE)
        # 低い横っ飛び（高飛びよりサイドの移動を強調）
        p = GK_HOME.lerp(dive_target, _ease_in_out(min(1.0, t * 1.15)))
        p.z = 0.75 * math.sin(min(1.0, t) * math.pi)
        return p
    t = (frame - (F_GOAL + 4)) / max(1, SHOT_FRAMES - (F_GOAL + 4))
    land = dive_target + Vector((-0.25, -0.45, 0.0))
    p = dive_target.lerp(land, _ease_in_out(min(1.0, t)))
    p.z = max(0.0, 0.25 * (1.0 - _ease_in_out(min(1.0, t * 1.6))))
    return p


def _ball_path(frame: int) -> Vector:
    shin = _shaolin_path(frame)
    move = Vector((1.0, 0.0, 0.0))
    if frame < F_KICK:
        # ドリブル〜踏み込み
        phase = frame * 0.5
        ahead = 0.45 + 0.08 * math.sin(phase * 2.0)
        side = 0.15 * math.sin(phase * 3.1)
        if frame >= F_PLANT:
            # キック前に少し引く
            t = (frame - F_PLANT) / max(1, F_KICK - F_PLANT)
            ahead = 0.45 - 0.35 * _ease_in_out(t)
        p = shin + move * ahead + Vector((0.0, side, 0.0))
        p.z = BALL_GROUND_Z
        return p

    # 高速シュート：短尺でゴールへ直线＋わずかな浮き
    t = (frame - F_KICK) / max(1, F_GOAL - F_KICK)
    t = min(1.0, t)
    # 加速感 — ほぼ直線＋わずかに加速
    u = 1.0 - (1.0 - t) ** 2.6
    start = shin + move * 0.55
    start.z = BALL_GROUND_Z
    p = start.lerp(BALL_GOAL, u)
    # 低い〜中弾道（高速ミドル）
    p.z = BALL_GROUND_Z + (BALL_GOAL.z - BALL_GROUND_Z) * u + 1.15 * math.sin(u * math.pi) * (1.0 - 0.4 * u)
    if frame > F_GOAL:
        # ネット内で少し沈む
        t2 = (frame - F_GOAL) / max(1, SHOT_FRAMES - F_GOAL)
        p = BALL_GOAL + Vector((0.8 * _ease_in_out(min(1.0, t2)), 0.12 * t2, -0.55 * _ease_in_out(min(1.0, t2))))
        p.z = max(BALL_GROUND_Z + 0.35, p.z)
    return p


def _animate_root_sparse(
    root: bpy.types.Object, path_fn, frames: List[int], yaw: float
) -> None:
    _clear_anim(root)
    for f in frames:
        _kf_loc(root, f, path_fn(f))
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def setup_characters():
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    shin = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [SHAOLIN_START],
        actions=["idle", "run", "fight_kick", "dash"],
        facing_yaw=SHAOLIN_YAW,
    )[0]
    gk = build_team(
        "PortugalGK",
        PORTUGAL_RED,
        [GK_HOME],
        actions=["idle", "fight_idle", "jump_full", "run"],
        facing_yaw=GK_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(gk), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    return shin, gk, _root_of(shin), _root_of(gk)


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
    cam_data = bpy.data.cameras.new("CamShaolinMiddleShot")
    cam = bpy.data.objects.new("CamShaolinMiddleShot", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    for f in (1, 48, F_APPROACH_END, F_KICK, F_GK_DIVE, F_GOAL, F_SETTLE, SHOT_FRAMES):
        shin = _shaolin_path(f)
        gk = _gk_path(f)
        ball = _ball_path(f)
        if f < F_KICK - 8:
            # 少林サイドからシュート準備
            pos = Vector((shin.x - 4.5, shin.y - 9.5, 3.6))
            tgt = Vector((shin.x + 3.0, shin.y * 0.3, 1.4))
            cam.data.lens = 28
        elif f < F_GOAL:
            # ボール追従＋GKが見えるサイド寄り
            mid = (ball + gk) * 0.5
            pos = Vector((mid.x - 6.0, mid.y - 11.0, 4.2))
            tgt = Vector((ball.x + 1.5, ball.y * 0.4, max(1.2, ball.z)))
            cam.data.lens = 32
        else:
            # ゴールイン瞬間〜ネット
            pos = Vector((GOAL_X - 14.0, -10.5, 4.8))
            tgt = Vector((GOAL_X - 0.5, BALL_GOAL.y * 0.4, GOAL_H * 0.45))
            cam.data.lens = 30
        cam.data.keyframe_insert(data_path="lens", frame=f)
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_shaolin_middle_shot() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = SHOT_FRAMES
    scene.render.fps = FPS

    shin_arm, gk_arm, shin_root, gk_root = setup_characters()
    _clear_all_nla(shin_arm)
    _clear_all_nla(gk_arm)

    sparse_s = sorted(
        {
            1,
            24,
            48,
            72,
            F_APPROACH_END,
            F_PLANT,
            F_KICK,
            F_KICK + 12,
            F_GOAL,
            F_SETTLE,
            SHOT_FRAMES,
        }
    )
    sparse_g = sorted(
        {
            1,
            40,
            80,
            F_GK_DIVE - 10,
            F_GK_DIVE,
            F_GK_DIVE + 10,
            F_GOAL,
            F_GOAL + 12,
            F_SETTLE,
            SHOT_FRAMES,
        }
    )
    _animate_root_sparse(shin_root, _shaolin_path, sparse_s, SHAOLIN_YAW)
    _animate_root_sparse(gk_root, _gk_path, sparse_g, GK_YAW)

    # 少林：接近 run → キック（ほぼ等速でコンタクトを F_KICK に合わせる）→ idle
    _add_nla_loop(shin_arm, "run", 1, F_KICK - 22)
    try:
        # fight_kick の接触は先頭から約20f — ストリップ先頭をそこへ合わせる
        _add_nla_once_stretched(shin_arm, "fight_kick", F_KICK - 20, F_KICK + 22)
    except KeyError:
        _add_nla_once_stretched(shin_arm, "dash", F_KICK - 16, F_KICK + 16)
    _add_nla_hold_pose(shin_arm, "idle", F_KICK + 23, SHOT_FRAMES)

    # GK：待機 → 遅れて横っ飛び → 着地
    try:
        _add_nla_hold_pose(gk_arm, "fight_idle", 1, F_GK_DIVE - 1)
    except KeyError:
        _add_nla_hold_pose(gk_arm, "idle", 1, F_GK_DIVE - 1)
    try:
        _add_nla_once_stretched(gk_arm, "jump_full", F_GK_DIVE, F_GOAL + 14)
    except KeyError:
        try:
            _add_nla_once_stretched(gk_arm, "air_jump", F_GK_DIVE, F_GOAL + 14)
        except KeyError:
            _add_nla_hold_pose(gk_arm, "idle", F_GK_DIVE, F_GOAL + 14)
    _add_nla_hold_pose(gk_arm, "idle", F_GOAL + 15, SHOT_FRAMES)

    ball = bpy.data.objects.get("Ball")
    if ball:
        _clear_anim(ball)
        ball.hide_render = False
        ball.hide_viewport = False
        for f in range(1, SHOT_FRAMES + 1, 2):
            _kf_loc(ball, f, _ball_path(f))
        for f in range(F_KICK - 2, min(SHOT_FRAMES, F_GOAL + 30) + 1):
            _kf_loc(ball, f, _ball_path(f))
        _ease_all_ball_keyframes(ball)
    else:
        print("WARN: Ball not found")

    setup_camera()
    scene.frame_set(1)
    print(
        f"Shaolin middle shot: {SHOT_FRAMES}f @ {FPS}fps — "
        f"kick f{F_KICK} goal f{F_GOAL} (GK dive late)"
    )


def render_shaolin_middle_shot_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = SHOT_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    out = RENDER_DIR / "shaolin_middle_shot.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Shaolin middle shot: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-shaolin-middle-shot-video" in sys.argv:
        render_shaolin_middle_shot_video()
    else:
        animate_shaolin_middle_shot()
