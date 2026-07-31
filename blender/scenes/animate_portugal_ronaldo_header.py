# SPDX-License-Identifier: MIT
"""ポルトガル戦 — ロナウドゆっくりジャンプ（単独）

握手・ヘディングとは別カット。ロナウド一人だけのスロージャンプ。
NLA は繰り返さず 1 回再生を引き延ばし、ルートは疎なキーで滑らかな放物線。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

from animate_soccer_match import (
    _clear_all_nla,
    _clear_anim,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24
# 一本のスロージャンプ（約12秒）
JUMP_FRAMES = 288

F_CROUCH = 48
F_TAKEOFF = 90
F_APEX = 162
F_LAND = 228
F_SETTLE = 260

JUMP_HEIGHT = 2.2
RONALDO_YAW = math.pi / 2  # +X 向き（横顔）
RONALDO_POS = Vector((0.0, 0.0, 0.0))

PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

# ジャンプ中の腕開き（軽め・連続補間）
JUMP_ARM_DELTA = {
    "upperarm.r": (0.15, -0.85, 0.35),
    "lowerarm.r": (-0.55, 0.1, 0.0),
    "upperarm.l": (0.15, 0.85, -0.35),
    "lowerarm.l": (-0.55, -0.1, 0.0),
    "spine_02": (0.08, 0.0, 0.0),
}

JUMP_ARM_BONES = [
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "hand.r",
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "hand.l",
    "spine_02",
]

PoseDict = Dict[str, Quaternion]


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    exact = [c for c in candidates if c == name]
    return exact[0] if exact else sorted(candidates)[0]


def _add_nla_once_stretched(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
) -> None:
    """アクションを繰り返さず、指定尺に引き延ばして 1 回だけ再生。"""
    resolved = _resolve_action_name(action_name)
    action = bpy.data.actions.get(resolved)
    if not action:
        raise KeyError(resolved)

    ad = arm.animation_data
    if ad is None:
        arm.animation_data_create()
        ad = arm.animation_data
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
    # scale > 1 → ゆっくり（尺にフィット、リピートなし）
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
    action_frame: int | None = None,
) -> None:
    """アクションの1フレームを尺いっぱいに引き延ばして静止（ループなし）。"""
    resolved = _resolve_action_name(action_name)
    action = bpy.data.actions.get(resolved)
    if not action:
        raise KeyError(resolved)

    ad = arm.animation_data
    if ad is None:
        arm.animation_data_create()
        ad = arm.animation_data
    ad.action = None

    track = ad.nla_tracks.new()
    track.name = f"{resolved}_hold"
    strip = track.strips.new(action.name, frame_start, action)

    act_start = int(action.frame_range[0])
    hold_f = action_frame if action_frame is not None else act_start + 1
    duration = max(1, frame_end - frame_start + 1)

    strip.action_frame_start = float(hold_f)
    strip.action_frame_end = float(hold_f + 1)
    strip.repeat = 1.0
    strip.scale = float(duration)
    strip.frame_start = float(frame_start)
    strip.frame_end = float(frame_start + duration)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.use_auto_blend = False
    strip.influence = 1.0
    # Blender が短いアクション長へ縮め直す場合があるので再適用
    strip.scale = float(duration)
    strip.frame_end = float(frame_start + duration)


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
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _ronaldo_jump_loc(frame: int) -> Vector:
    """疎キー用の一本放物線（かくつき防止）。"""
    p = RONALDO_POS.copy()
    if frame <= F_CROUCH:
        t = (frame - 1) / max(1, F_CROUCH - 1)
        p.z = -0.22 * _ease_in_out(t)
        return p
    if frame <= F_TAKEOFF:
        t = (frame - F_CROUCH) / max(1, F_TAKEOFF - F_CROUCH)
        p.z = -0.22 - 0.12 * _ease_in_out(t)
        return p
    if frame <= F_APEX:
        t = (frame - F_TAKEOFF) / max(1, F_APEX - F_TAKEOFF)
        ease = math.sin(_ease_in_out(t) * math.pi * 0.5)
        p.z = -0.34 + (JUMP_HEIGHT + 0.34) * ease
        p.x += 0.25 * _ease_in_out(t)
        return p
    if frame <= F_LAND:
        t = (frame - F_APEX) / max(1, F_LAND - F_APEX)
        ease = _ease_in_out(t)
        p.z = JUMP_HEIGHT * (1.0 - ease)
        p.x += 0.25 + 0.2 * ease
        return p
    if frame <= F_SETTLE:
        t = (frame - F_LAND) / max(1, F_SETTLE - F_LAND)
        # 着地の軽い沈み
        p.z = -0.12 * math.sin(_ease_in_out(t) * math.pi)
        p.x += 0.45
        return p
    p.x += 0.45
    return p


def _snapshot_pose(arm: bpy.types.Object) -> PoseDict:
    pose: PoseDict = {}
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
        pose[bone.name] = bone.rotation_quaternion.copy()
    return pose


def _pose_with_deltas(
    base: PoseDict, deltas: Dict[str, Tuple[float, float, float]], weight: float = 1.0
) -> PoseDict:
    out: PoseDict = {name: q.copy() for name, q in base.items()}
    w = max(0.0, min(1.0, weight))
    for bone_name, euler_xyz in deltas.items():
        if bone_name not in out:
            continue
        delta = Euler(euler_xyz, "XYZ").to_quaternion()
        if w >= 0.999:
            out[bone_name] = out[bone_name] @ delta
        else:
            out[bone_name] = out[bone_name] @ Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(delta, w)
    return out


def _add_bone_pose_replace_strip(
    arm: bpy.types.Object,
    name: str,
    strip_start: int,
    strip_end: int,
    keyed_poses: List[Tuple[int, PoseDict]],
    bone_filter: List[str] | None = None,
) -> None:
    if not arm.animation_data:
        arm.animation_data_create()
    ad = arm.animation_data

    muted = [(t, t.mute) for t in ad.nla_tracks]
    for t, _ in muted:
        t.mute = True

    act_name = name
    if bpy.data.actions.get(act_name):
        act_name = f"{name}_{len(bpy.data.actions)}"
    act = bpy.data.actions.new(act_name)
    ad.action = act

    allowed = set(bone_filter) if bone_filter else None
    for frame, pose in keyed_poses:
        for bone_name, quat in pose.items():
            if allowed is not None and bone_name not in allowed:
                continue
            bone = arm.pose.bones.get(bone_name)
            if not bone:
                continue
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = quat
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

    if act.fcurves:
        for fc in act.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

    ad.action = None
    for t, was_muted in muted:
        t.mute = was_muted

    track = ad.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, strip_start, act)
    strip.frame_start = strip_start
    strip.frame_end = strip_end + 1
    strip.action_frame_start = min(f for f, _ in keyed_poses)
    strip.action_frame_end = max(f for f, _ in keyed_poses)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.influence = 1.0
    strip.use_auto_blend = False


def _animate_root_sparse(root: bpy.types.Object, frames: List[int], yaw: float) -> None:
    """疎なキー＋滑らか補間（毎フレキーのビジー防止）。"""
    _clear_anim(root)
    for f in frames:
        _kf_loc(root, f, _ronaldo_jump_loc(f))
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _animate_jump_arms(ronaldo_arm: bpy.types.Object) -> None:
    ad = ronaldo_arm.animation_data
    if not ad:
        ronaldo_arm.animation_data_create()
        ad = ronaldo_arm.animation_data

    muted = [(t, t.mute) for t in ad.nla_tracks]
    for t, _ in muted:
        t.mute = True

    idle = bpy.data.actions.get(_resolve_action_name("idle"))
    prev = ad.action
    ad.action = idle
    bpy.context.scene.frame_set(10)
    bpy.context.view_layer.update()
    idle_base = _snapshot_pose(ronaldo_arm)
    ad.action = prev
    for t, was_muted in muted:
        t.mute = was_muted

    arms = _pose_with_deltas(idle_base, JUMP_ARM_DELTA, 1.0)
    keys = [
        (1, idle_base),
        (F_CROUCH, idle_base),
        (F_TAKEOFF, _pose_with_deltas(idle_base, JUMP_ARM_DELTA, 0.55)),
        (F_APEX, arms),
        (F_LAND, _pose_with_deltas(idle_base, JUMP_ARM_DELTA, 0.35)),
        (F_SETTLE, idle_base),
        (JUMP_FRAMES, idle_base),
    ]
    _add_bone_pose_replace_strip(
        ronaldo_arm,
        "Ronaldo_SlowJumpArms",
        1,
        JUMP_FRAMES,
        keys,
        JUMP_ARM_BONES,
    )


def _hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if not ball:
        return
    if ball.animation_data:
        ball.animation_data_clear()
    ball.hide_render = True
    ball.hide_viewport = True


def setup_portugal_header_character() -> Tuple[bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    ronaldo_arm = build_team(
        "Ronaldo",
        PORTUGAL_RED,
        [RONALDO_POS],
        actions=["idle"],
        facing_yaw=RONALDO_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(ronaldo_arm), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    return ronaldo_arm, _root_of(ronaldo_arm)


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_portugal_header_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamPortugalHeader")
    cam = bpy.data.objects.new("CamPortugalHeader", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 30

    for f in (1, F_CROUCH, F_TAKEOFF, F_APEX, F_LAND, F_SETTLE, JUMP_FRAMES):
        loc = _ronaldo_jump_loc(f)
        body_z = 3.6 + max(0.0, loc.z) * 0.55
        tgt = Vector((loc.x + 0.1, loc.y, body_z))
        pos = Vector((loc.x + 1.0, loc.y - 8.5, 2.8 + max(0.0, loc.z) * 0.4))
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


def animate_portugal_ronaldo_header() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = JUMP_FRAMES
    scene.render.fps = FPS

    ronaldo_arm, ronaldo_root = setup_portugal_header_character()
    _clear_all_nla(ronaldo_arm)
    _hide_ball()

    sparse_frames = sorted(
        {
            1,
            F_CROUCH,
            (F_CROUCH + F_TAKEOFF) // 2,
            F_TAKEOFF,
            F_TAKEOFF + 18,
            (F_TAKEOFF + F_APEX) // 2,
            F_APEX,
            F_APEX + 18,
            (F_APEX + F_LAND) // 2,
            F_LAND,
            F_SETTLE,
            JUMP_FRAMES,
        }
    )
    _animate_root_sparse(ronaldo_root, sparse_frames, RONALDO_YAW)

    # 立ち：idle の1ポーズ固定（ループなし）
    _add_nla_hold_pose(ronaldo_arm, "idle", 1, F_TAKEOFF - 1, action_frame=10)
    # 空中：air_jump を引き延ばして1回だけ（短いクリップのリピート＝カクつきの主因だった）
    try:
        _add_nla_once_stretched(ronaldo_arm, "air_jump", F_TAKEOFF, F_LAND)
    except KeyError:
        _add_nla_hold_pose(ronaldo_arm, "idle", F_TAKEOFF, F_LAND, action_frame=10)
    _add_nla_hold_pose(ronaldo_arm, "idle", F_LAND + 1, JUMP_FRAMES, action_frame=10)

    _animate_jump_arms(ronaldo_arm)
    setup_portugal_header_camera()
    scene.frame_set(1)

    # ストリップがリピートしていないことをログ
    ad = ronaldo_arm.animation_data
    reps = []
    if ad:
        for tr in ad.nla_tracks:
            for st in tr.strips:
                reps.append(f"{tr.name}:{st.repeat:.2f}x scale={st.scale:.2f}")
    print(
        f"Portugal slow jump: {JUMP_FRAMES}f @ {FPS}fps — "
        f"no-repeat NLA [{', '.join(reps)}]"
    )


def render_portugal_header_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = JUMP_FRAMES
    scene.eevee.taa_render_samples = 8

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "portugal_ronaldo_header.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering portugal slow jump video: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-portugal-header-video" in sys.argv:
        render_portugal_header_video()
    else:
        animate_portugal_ronaldo_header()
        from news_cg_common import save_blend

        save_blend(blend)
