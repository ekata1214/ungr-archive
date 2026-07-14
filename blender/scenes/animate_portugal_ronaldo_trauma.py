# SPDX-License-Identifier: MIT
"""ポルトガル戦 — トラウマでヘディングできないロナウド

ヘディング衝突のトラウマで、頭を両手で抱えしゃがみ込む単独カット。
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
# 約10秒
TRAUMA_FRAMES = 240

F_NOTICE = 36
F_CROUCH = 108
F_HOLD = 150

RONALDO_YAW = 0.0  # カメラ（-Y）正面
RONALDO_POS = Vector((0.0, 0.0, 0.0))

PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

PoseDict = Dict[str, Quaternion]

# しゃがみ込み＋頭を抱える
CROUCH_BONES = [
    "pelvis",
    "thigh.l",
    "calf.l",
    "foot.l",
    "thigh.r",
    "calf.r",
    "foot.r",
    "spine_01",
    "spine_02",
    "neck_01",
    "head",
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "hand.r",
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "hand.l",
]

# idle 上に掛けるオイラー差分。
# 胴の前傾は弱め、腕は Rx+ で前へ上げて顔脇（頭ボーン local +Y 側）を押さえる。
# 負の upperarm.X だと肘が背後に回り「背中に手」になるので使わない。
CROUCH_DELTA = {
    "pelvis": (0.16, 0.0, 0.0),
    "thigh.l": (1.12, 0.1, -0.1),
    "thigh.r": (1.12, -0.1, 0.1),
    "calf.l": (-1.32, 0.0, 0.0),
    "calf.r": (-1.32, 0.0, 0.0),
    "foot.l": (0.22, 0.0, 0.0),
    "foot.r": (0.22, 0.0, 0.0),
    "spine_01": (0.04, 0.0, 0.0),
    "spine_02": (0.06, 0.0, 0.0),
    "neck_01": (0.28, 0.0, 0.0),
    "head": (0.35, 0.0, 0.0),
    "clavicle.r": (0.22, -0.18, 0.12),
    "upperarm.r": (1.85, -0.01, 0.54),
    "lowerarm.r": (-1.01, 2.16, -0.2),
    "hand.r": (0.25, 0.45, -0.55),
    "clavicle.l": (0.22, 0.18, -0.12),
    "upperarm.l": (1.85, 0.01, -0.54),
    "lowerarm.l": (-1.01, -2.16, 0.2),
    "hand.l": (0.25, -0.45, 0.55),
}

# しゃがむ前：頭を押さえ始める（後方回り込みなし）
GUARD_DELTA = {
    "spine_01": (0.02, 0.0, 0.0),
    "spine_02": (0.03, 0.0, 0.0),
    "neck_01": (0.12, 0.0, 0.0),
    "head": (0.15, 0.0, 0.0),
    "clavicle.r": (0.1, -0.1, 0.06),
    "upperarm.r": (0.75, 0.15, 0.25),
    "lowerarm.r": (-0.55, 0.85, -0.05),
    "hand.r": (0.12, 0.2, -0.25),
    "clavicle.l": (0.1, 0.1, -0.06),
    "upperarm.l": (0.75, -0.15, -0.25),
    "lowerarm.l": (-0.55, -0.85, 0.05),
    "hand.l": (0.12, -0.2, 0.25),
}


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    exact = [c for c in candidates if c == name]
    return exact[0] if exact else sorted(candidates)[0]


def _add_nla_hold_pose(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
    action_frame: int | None = None,
) -> None:
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
                "Fernandes_",
                "PortugalGK_",
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if ball:
        ball.hide_render = True
        ball.hide_viewport = True


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _snapshot_pose(arm: bpy.types.Object) -> PoseDict:
    out: PoseDict = {}
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
        out[bone.name] = bone.rotation_quaternion.copy()
    return out


def _pose_with_deltas(
    base: PoseDict,
    deltas: Dict[str, Tuple[float, float, float]],
    weight: float = 1.0,
) -> PoseDict:
    out = {k: v.copy() for k, v in base.items()}
    w = max(0.0, min(1.0, weight))
    for name, xyz in deltas.items():
        if name not in out:
            continue
        delta = Euler(xyz, "XYZ").to_quaternion()
        if w >= 0.999:
            out[name] = out[name] @ delta
        else:
            out[name] = out[name] @ Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(delta, w)
    return out


def _capture_idle_base(arm: bpy.types.Object) -> PoseDict:
    idle = bpy.data.actions.get(_resolve_action_name("idle"))
    ad = arm.animation_data
    if ad is None:
        arm.animation_data_create()
        ad = arm.animation_data
    prev = ad.action
    if idle:
        ad.action = idle
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    base = _snapshot_pose(arm)
    ad.action = prev
    return base


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

    act_name = name if not bpy.data.actions.get(name) else f"{name}_{len(bpy.data.actions)}"
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


def _ronaldo_path(frame: int) -> Vector:
    """立位 → しゃがみ込み。ルートを下げて腰の高さを出す。"""
    p = RONALDO_POS.copy()
    tremble = 0.0
    if frame >= F_HOLD:
        tremble = 0.03 * math.sin((frame - F_HOLD) * 0.55)

    if frame <= F_NOTICE:
        return p
    if frame <= F_CROUCH:
        t = _ease_in_out((frame - F_NOTICE) / max(1, F_CROUCH - F_NOTICE))
        p.z = -0.9 * t
        p.x += 0.04 * math.sin(t * math.pi)
        return p
    # 抱え込んで微動
    p.z = -0.9 + tremble
    p.x = 0.02 * math.sin((frame - F_CROUCH) * 0.22)
    return p


def _animate_root(root: bpy.types.Object) -> None:
    _clear_anim(root)
    sparse = [1, F_NOTICE, F_CROUCH - 20, F_CROUCH, F_HOLD, F_HOLD + 30, TRAUMA_FRAMES]
    for f in sparse:
        _kf_loc(root, f, _ronaldo_path(f))
        _kf_rot_z(root, f, RONALDO_YAW)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _animate_trauma_pose(arm: bpy.types.Object) -> None:
    base = _capture_idle_base(arm)
    keys: List[Tuple[int, PoseDict]] = [
        (1, base),
        (F_NOTICE, _pose_with_deltas(base, GUARD_DELTA, 0.55)),
        (F_NOTICE + 18, _pose_with_deltas(base, GUARD_DELTA, 1.0)),
        (F_CROUCH - 24, _pose_with_deltas(base, CROUCH_DELTA, 0.35)),
        (F_CROUCH, _pose_with_deltas(base, CROUCH_DELTA, 1.0)),
        (F_HOLD, _pose_with_deltas(base, CROUCH_DELTA, 1.0)),
    ]
    # 微かな震え（頭抱えのまま）
    for f in range(F_HOLD + 8, TRAUMA_FRAMES + 1, 6):
        wiggle = 0.02 * math.sin((f - F_HOLD) * 0.7)
        d = {
            k: (v[0] + (wiggle if "head" in k or "neck" in k or "spine" in k else 0.0), v[1], v[2])
            for k, v in CROUCH_DELTA.items()
        }
        # 両手を頭に押し付ける微動
        d["upperarm.r"] = (
            CROUCH_DELTA["upperarm.r"][0] + 0.04 * math.sin(f * 0.45),
            CROUCH_DELTA["upperarm.r"][1],
            CROUCH_DELTA["upperarm.r"][2],
        )
        d["upperarm.l"] = (
            CROUCH_DELTA["upperarm.l"][0] + 0.04 * math.sin(f * 0.45 + 1.0),
            CROUCH_DELTA["upperarm.l"][1],
            CROUCH_DELTA["upperarm.l"][2],
        )
        keys.append((f, _pose_with_deltas(base, d, 1.0)))
    if keys[-1][0] != TRAUMA_FRAMES:
        keys.append((TRAUMA_FRAMES, _pose_with_deltas(base, CROUCH_DELTA, 1.0)))
    _add_bone_pose_replace_strip(arm, "Ronaldo_Trauma", 1, TRAUMA_FRAMES, keys, CROUCH_BONES)


def setup_character() -> Tuple[bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    ron = build_team(
        "Ronaldo",
        PORTUGAL_RED,
        [RONALDO_POS],
        actions=["idle"],
        facing_yaw=RONALDO_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(ron), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    return ron, _root_of(ron)


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
    cam_data = bpy.data.cameras.new("CamRonaldoTrauma")
    cam = bpy.data.objects.new("CamRonaldoTrauma", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_data.lens = 32

    for f in (1, F_NOTICE, F_CROUCH, F_HOLD, TRAUMA_FRAMES):
        t = (f - 1) / max(1, TRAUMA_FRAMES - 1)
        loc = _ronaldo_path(f)
        # 立位ワイド → しゃがみ込みへ寄り
        pos = Vector((-1.2 + 0.4 * t, -9.2 + 1.6 * t, 3.6 - 0.9 * min(1.0, max(0.0, -loc.z))))
        tgt = Vector((loc.x * 0.3, loc.y, 2.6 + loc.z * 0.55))
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_portugal_ronaldo_trauma() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = TRAUMA_FRAMES
    scene.render.fps = FPS

    _hide_ball()
    ron_arm, ron_root = setup_character()
    _clear_all_nla(ron_arm)

    _animate_root(ron_root)
    # 脚ループを避け idle を固定、ポーズでしゃがみを乗せる
    _add_nla_hold_pose(ron_arm, "idle", 1, TRAUMA_FRAMES)
    _animate_trauma_pose(ron_arm)
    setup_camera()
    scene.frame_set(1)
    print(
        f"Ronaldo trauma crouch: {TRAUMA_FRAMES}f @ {FPS}fps — "
        "covers head and crouches (~10s)"
    )


def render_portugal_ronaldo_trauma_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = TRAUMA_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    out = RENDER_DIR / "portugal_ronaldo_trauma.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Ronaldo trauma: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-portugal-ronaldo-trauma-video" in sys.argv:
        render_portugal_ronaldo_trauma_video()
    else:
        animate_portugal_ronaldo_trauma()
