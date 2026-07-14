# SPDX-License-Identifier: MIT
"""少林空中シュート — 宙に浮いたままゴールへ撃ち、GKが横飛びするが防げずゴールイン"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import bpy
from mathutils import Vector

from animate_soccer_match import (
    BALL_GROUND_Z,
    PITCH_HALF,
    _clear_all_nla,
    _clear_anim,
    _ease_all_ball_keyframes,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24
TOTAL_FRAMES = 120  # 約5秒

# 最初から空中 → シュート → GK横飛び失敗 → ゴール
F_CRUISE_END = 36
F_KICK = 48
F_GK_DIVE = 52  # キック直後に飛び出すが届かない（middle shot と同型）
F_GOAL = 72
F_SETTLE = 100

_SCALE = 2.5
GOAL_X = -PITCH_HALF  # 左ゴール
GOAL_INNER_HALF_W = 7.32 * _SCALE / 2
GOAL_H = 2.44 * _SCALE

# 少林は左ゴール（-X）向き。yaw=0 は -Y なので 1.5π で -X
SHAOLIN_YAW = math.pi * 1.5
GK_YAW = math.pi / 2  # 射手を見る（+X）
MOVE_DIR = Vector((-1.0, 0.0, 0.0))

CRUISE_Z = 6.2
HOVER_AMP = 0.28

SHAOLIN_START = Vector((-55.0, 0.4, CRUISE_Z))
SHAOLIN_KICK = Vector((-88.0, -0.3, CRUISE_Z + 0.15))
GK_HOME = Vector((GOAL_X + 3.2, 0.0, 0.0))

# 攻撃向き -X から見て右隅（+Y）へ突き刺す — GK はそこへ横飛びするが届かない
BALL_GOAL = Vector((GOAL_X - 1.6, GOAL_INNER_HALF_W * 0.78, GOAL_H * 0.62))

SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
SHAOLIN_WHITE = (0.96, 0.96, 0.98, 1.0)
PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


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
                "Netherlands_",
                "PortugalGK_",
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _hover_z(frame: int, base: float) -> float:
    return base + HOVER_AMP * math.sin(frame * 0.22)


def _shaolin_path(frame: int) -> Vector:
    """最初から空中。ゴール方向へ進み、キック後も宙に残る。"""
    if frame <= F_CRUISE_END:
        t = (frame - 1) / max(1, F_CRUISE_END - 1)
        p = SHAOLIN_START.lerp(SHAOLIN_KICK, _ease_in_out(t))
        p.y += 0.55 * math.sin(t * 4.0 * math.pi)
        p.z = _hover_z(frame, CRUISE_Z)
        return p
    if frame <= F_KICK:
        t = (frame - F_CRUISE_END) / max(1, F_KICK - F_CRUISE_END)
        # キック前にわずかに体を沈めて蓄力
        p = SHAOLIN_KICK.copy()
        p.x -= 1.2 * _ease_in_out(t)
        p.z = _hover_z(frame, CRUISE_Z - 0.45 * _ease_in_out(t))
        return p
    # フォロースルー — 空中で少し前進しつつ浮く
    t = (frame - F_KICK) / max(1, TOTAL_FRAMES - F_KICK)
    p = SHAOLIN_KICK + Vector((-2.4 * _ease_in_out(min(1.0, t * 1.4)), 0.2 * t, 0.0))
    p.z = _hover_z(frame, CRUISE_Z + 0.35 * math.sin(min(1.0, t) * math.pi * 0.6))
    return p


def _gk_path(frame: int) -> Vector:
    """middle shot と同じ横っ飛び：ボール筋へ手を伸ばすが届かない。"""
    dive_target = Vector((GOAL_X + 2.0, BALL_GOAL.y * 0.88, 0.0))
    if frame < F_GK_DIVE:
        t = (frame - 1) / max(1, F_GK_DIVE - 1)
        sway = Vector((0.0, BALL_GOAL.y * 0.18 * _ease_in_out(t), 0.0))
        return GK_HOME + sway
    if frame <= F_GOAL + 4:
        t = (frame - F_GK_DIVE) / max(1, (F_GOAL + 4) - F_GK_DIVE)
        p = GK_HOME.lerp(dive_target, _ease_in_out(min(1.0, t * 1.15)))
        p.z = 0.75 * math.sin(min(1.0, t) * math.pi)
        return p
    t = (frame - (F_GOAL + 4)) / max(1, TOTAL_FRAMES - (F_GOAL + 4))
    land = dive_target + Vector((0.25, 0.45, 0.0))
    p = dive_target.lerp(land, _ease_in_out(min(1.0, t)))
    p.z = max(0.0, 0.25 * (1.0 - _ease_in_out(min(1.0, t * 1.6))))
    return p


def _ball_at_air_feet(player: Vector, frame: int) -> Vector:
    phase = frame * 0.7
    ahead = 2.2 + 0.1 * math.sin(phase * 2.2)
    side = 0.06 * math.sin(phase * 3.2)
    bounce = 0.08 * abs(math.sin(phase * 4.2))
    right = _right_of(MOVE_DIR)
    p = player + MOVE_DIR * ahead + right * side
    p.z = player.z + 0.35 + bounce
    return p


def _ball_path(frame: int) -> Vector:
    shin = _shaolin_path(frame)
    if frame < F_KICK:
        return _ball_at_air_feet(shin, frame)

    t = (frame - F_KICK) / max(1, F_GOAL - F_KICK)
    t = min(1.0, t)
    u = 1.0 - (1.0 - t) ** 2.4  # 加速感
    start = _ball_at_air_feet(shin, F_KICK - 1)
    p = start.lerp(BALL_GOAL, u)
    # 空中リリース → ゴール上隅へ落ち込む弧
    arc = 1.4 * math.sin(u * math.pi) * (1.0 - 0.35 * u)
    p.z = start.z + (BALL_GOAL.z - start.z) * u + arc
    if frame > F_GOAL:
        t2 = (frame - F_GOAL) / max(1, TOTAL_FRAMES - F_GOAL)
        p = BALL_GOAL + Vector(
            (
                -0.85 * _ease_in_out(min(1.0, t2)),
                0.1 * t2,
                -0.55 * _ease_in_out(min(1.0, t2)),
            )
        )
        p.z = max(BALL_GROUND_Z + 0.35, p.z)
    return p


def _animate_root(
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


def setup_characters() -> Tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    shin = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [SHAOLIN_START],
        actions=["idle", "run", "fight_kick", "dash"],
        facing_yaw=SHAOLIN_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(shin), SHAOLIN_ORANGE, SHAOLIN_WHITE, z_cut=0.42)
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
    """空中追従 → キックでボールに食いつき → ゴールインへ一気に寄せる。"""
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamShaolinAerialShot")
    cam = bpy.data.objects.new("CamShaolinAerialShot", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # 密めのキーで鞭のような追従
    keys = sorted(
        set(
            list(range(1, F_KICK + 1, 4))
            + list(range(F_KICK, F_GOAL + 1, 2))
            + list(range(F_GOAL, TOTAL_FRAMES + 1, 6))
            + [TOTAL_FRAMES]
        )
    )

    for f in keys:
        shin = _shaolin_path(f)
        gk = _gk_path(f)
        ball = _ball_path(f)
        right = _right_of(MOVE_DIR)

        if f < F_KICK - 6:
            # 斜め後方から空中少林を煽る（高低差を見せる）
            mid = shin + Vector((0.0, 0.0, 1.4))
            whip = 0.35 * math.sin(f * 0.18)
            pos = mid - MOVE_DIR * (5.0 + whip) + right * (9.5 - whip * 2.0)
            pos.z = shin.z * 0.55 + 2.2
            tgt = shin + MOVE_DIR * 2.5 + Vector((0.0, 0.0, 0.6))
            cam_data.lens = 28
        elif f < F_GOAL:
            # ボール＋GK を同じ画で追う・寄る
            mid = ball.lerp(gk, 0.35)
            t = (f - F_KICK) / max(1, F_GOAL - F_KICK)
            push = 4.5 - 1.8 * _ease_in_out(t)  # 寄って加速感
            pos = mid - MOVE_DIR * push + right * (10.0 - 2.5 * t)
            pos.z = max(2.8, ball.z * 0.45 + 2.0 + 1.2 * (1.0 - t))
            tgt = ball + MOVE_DIR * 1.2 + Vector((0.0, 0.0, 0.2))
            cam_data.lens = 30 + 6 * _ease_in_out(t)
        else:
            # ゴールイン瞬間 — ネット側に飛び込むような寄り
            t = (f - F_GOAL) / max(1, TOTAL_FRAMES - F_GOAL)
            pos = Vector(
                (
                    GOAL_X + 12.0 - 3.0 * _ease_in_out(t),
                    BALL_GOAL.y * 0.35 - 8.5 + 1.5 * t,
                    3.6 + 1.0 * t,
                )
            )
            tgt = Vector((GOAL_X + 0.5, BALL_GOAL.y * 0.55, GOAL_H * 0.5))
            cam_data.lens = 34 - 4 * _ease_in_out(min(1.0, t))

        cam_data.keyframe_insert(data_path="lens", frame=f)
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_shaolin_aerial_shot() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.render.fps = FPS

    shin_arm, gk_arm, shin_root, gk_root = setup_characters()
    _clear_all_nla(shin_arm)
    _clear_all_nla(gk_arm)

    sparse_s = sorted(
        set(
            [1]
            + list(range(1, F_KICK + 1, 4))
            + [F_CRUISE_END, F_KICK, F_KICK + 10, F_GOAL, F_SETTLE, TOTAL_FRAMES]
        )
    )
    sparse_g = sorted(
        {
            1,
            20,
            F_GK_DIVE - 8,
            F_GK_DIVE,
            F_GK_DIVE + 8,
            F_GOAL,
            F_GOAL + 10,
            F_SETTLE,
            TOTAL_FRAMES,
        }
    )
    _animate_root(shin_root, _shaolin_path, sparse_s, SHAOLIN_YAW)
    _animate_root(gk_root, _gk_path, sparse_g, GK_YAW)

    # 少林：空中ラン → キック → 空中アイドル
    _add_nla_loop(shin_arm, "run", 1, F_KICK - 20)
    try:
        _add_nla_once_stretched(shin_arm, "fight_kick", F_KICK - 18, F_KICK + 20)
    except KeyError:
        _add_nla_once_stretched(shin_arm, "dash", F_KICK - 14, F_KICK + 14)
    _add_nla_hold_pose(shin_arm, "idle", F_KICK + 21, TOTAL_FRAMES)

    # GK：middle shot と同じ — fight_idle → 遅れて jump_full 横飛び → idle
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
    _add_nla_hold_pose(gk_arm, "idle", F_GOAL + 15, TOTAL_FRAMES)

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball not found — run build_field_only first")
    _clear_anim(ball)
    ball.hide_render = False
    ball.hide_viewport = False
    for f in range(1, TOTAL_FRAMES + 1):
        _kf_loc(ball, f, _ball_path(f))
    _ease_all_ball_keyframes(ball)

    setup_camera()
    scene.frame_set(1)
    print(
        f"Shaolin aerial shot: {TOTAL_FRAMES}f @ {FPS}fps — "
        f"air→kick f{F_KICK}→goal f{F_GOAL} (GK dive late)"
    )


def render_shaolin_aerial_shot_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    animate_shaolin_aerial_shot()
    setup_black_world()
    setup_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    out = RENDER_DIR / "shaolin_aerial_shot.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Shaolin aerial shot: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-shaolin-aerial-shot-video" in sys.argv:
        render_shaolin_aerial_shot_video()
    else:
        animate_shaolin_aerial_shot()
