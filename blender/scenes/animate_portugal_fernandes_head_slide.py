# SPDX-License-Identifier: MIT
"""ポルトガル戦 — フェルナンデスのドリブルに少林が頭スライディングで奪球

別カット。フェルナンデス単独ドリブル → 少林が頭から滑り込みボールを奪う。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

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
SLIDE_FRAMES = 300  # 約12.5秒

F_DRIBBLE_END = 150
F_SLIDE_START = 132
F_SLIDE_CONTACT = 178
F_SLIDE_END = 210
F_SETTLE = 250

# フェルナンデスは +X へドリブル、少林は +Y 側から -Y 向きに頭スライディング
FERN_YAW = math.pi / 2
SHAOLIN_YAW = math.pi  # -Y 向き（ボールへ横から）
FERN_START = Vector((-8.0, 0.0, 0.0))
SHAOLIN_START = Vector((0.0, 7.5, 0.0))

PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)
SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)

# ルートで約90°前傾するので、ボーンは腕の開き＋脚の伸展を中心に
SLIDE_WINDUP = {
    "spine_01": (0.15, 0.0, 0.0),
    "spine_02": (0.2, 0.0, 0.05),
    "neck_01": (0.25, 0.0, 0.05),
    "head": (0.2, 0.0, 0.0),
    "upperarm.r": (0.9, 1.0, -0.2),
    "upperarm.l": (0.9, -1.0, 0.2),
    "thigh.r": (0.35, 0.15, 0.0),
    "thigh.l": (0.15, -0.1, 0.0),
    "calf.r": (-0.2, 0.0, 0.0),
    "calf.l": (-0.15, 0.0, 0.0),
}
SLIDE_CONTACT = {
    "spine_01": (0.2, 0.0, 0.0),
    "spine_02": (0.28, 0.0, 0.08),
    "neck_01": (0.35, 0.0, 0.05),
    "head": (0.28, 0.0, 0.0),
    "upperarm.r": (1.1, 1.15, -0.25),
    "lowerarm.r": (-0.35, 0.0, 0.0),
    "upperarm.l": (1.1, -1.15, 0.25),
    "lowerarm.l": (-0.35, 0.0, 0.0),
    "thigh.r": (0.45, 0.2, 0.05),
    "thigh.l": (0.2, -0.15, -0.05),
    "calf.r": (-0.25, 0.0, 0.0),
    "calf.l": (-0.2, 0.0, 0.0),
}
SLIDE_BONES = [
    "upperarm.r",
    "lowerarm.r",
    "upperarm.l",
    "lowerarm.l",
    "thigh.r",
    "calf.r",
    "thigh.l",
    "calf.l",
    "spine_01",
    "spine_02",
    "neck_01",
    "head",
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
    strip.scale = float(duration)
    strip.frame_end = float(frame_start + duration)


def _add_nla_loop(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
) -> None:
    """走るなど短いループが必要な区間のみ。"""
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
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _fernandes_path(frame: int) -> Vector:
    """+X へ細かいドリブル。奪われ後は少しつんのめる。"""
    if frame <= F_SLIDE_CONTACT:
        t = (frame - 1) / max(1, F_SLIDE_CONTACT - 1)
        x = FERN_START.x + t * 14.5
        y = 0.55 * math.sin(t * 7.0 * math.pi) + 0.28 * math.sin(t * 13.0 * math.pi + 0.4)
        return Vector((x, y, 0.0))
    # 接触後：ブレーキ＆よろけ
    base = _fernandes_path(F_SLIDE_CONTACT)
    t = (frame - F_SLIDE_CONTACT) / max(1, SLIDE_FRAMES - F_SLIDE_CONTACT)
    stumble = 0.35 * math.sin(min(1.0, t * 2.2) * math.pi)
    return Vector((base.x + 1.1 * _ease_in_out(t), base.y + stumble, 0.0))


def _shaolin_contact() -> Vector:
    """接触時ルート。足元ピボット＋約90°前傾で頭がボール側（-Y）へ届く距離。"""
    fern_at_contact = _fernandes_path(F_SLIDE_CONTACT)
    # ボールはフェルン前方。頭がボール、胴体が +Y 側に残る
    return fern_at_contact + Vector((0.85, 4.1, 0.95))


def _shaolin_pitch(frame: int) -> float:
    """スライディング中にルートを前傾させて水平に近い姿勢にする。"""
    if frame < F_SLIDE_START:
        return 0.0
    if frame <= F_SLIDE_CONTACT:
        t = (frame - F_SLIDE_START) / max(1, F_SLIDE_CONTACT - F_SLIDE_START)
        return 1.35 * _ease_in_out(t)  # ~77°
    if frame <= F_SLIDE_END:
        t = (frame - F_SLIDE_CONTACT) / max(1, F_SLIDE_END - F_SLIDE_CONTACT)
        return 1.35 * (1.0 - 0.55 * _ease_in_out(t))
    t = (frame - F_SLIDE_END) / max(1, F_SETTLE - F_SLIDE_END)
    return max(0.0, 1.35 * 0.45 * (1.0 - _ease_in_out(min(1.0, t))))


def _shaolin_path(frame: int) -> Vector:
    """+Y 側から -Y 向きに滑り、ボールへ頭から突っ込む。"""
    contact = _shaolin_contact()

    if frame < F_SLIDE_START:
        t = (frame - 1) / max(1, F_SLIDE_START - 1)
        wait = Vector((contact.x - 1.5, 11.0, 0.0))
        pre = Vector((contact.x, contact.y + 4.5, 0.0))
        return wait.lerp(pre, _ease_in_out(t))

    if frame <= F_SLIDE_CONTACT:
        t = (frame - F_SLIDE_START) / max(1, F_SLIDE_CONTACT - F_SLIDE_START)
        start = Vector((contact.x, contact.y + 4.5, 0.0))
        p = start.lerp(contact, _ease_in_out(t))
        # 前傾に合わせてルートを上げ、地面貫通を防ぐ
        p.z = 0.95 * _ease_in_out(t)
        return p

    if frame <= F_SLIDE_END:
        t = (frame - F_SLIDE_CONTACT) / max(1, F_SLIDE_END - F_SLIDE_CONTACT)
        end = contact + Vector((2.4, -2.2, 0.35))
        p = contact.lerp(end, _ease_in_out(t))
        p.z = contact.z * (1.0 - 0.55 * t)
        return p

    end = contact + Vector((2.4, -2.2, 0.35))
    t = (frame - F_SLIDE_END) / max(1, SLIDE_FRAMES - F_SLIDE_END)
    p = end + Vector((1.4 * _ease_in_out(t), -0.5 * t, 0.0))
    p.z = max(0.0, end.z * (1.0 - _ease_in_out(min(1.0, t * 1.4))))
    return p


def _ball_path(frame: int, fern: Vector, shaolin: Vector) -> Vector:
    move = Vector((1.0, 0.0, 0.0))
    right = _right_of(move)
    if frame < F_SLIDE_CONTACT:
        phase = frame * 0.55
        ahead = 0.42 + 0.08 * math.sin(phase * 2.2)
        side = 0.2 * math.sin(phase * 3.4)
        p = fern + move * ahead + right * side
        p.z = BALL_GROUND_Z
        return p
    # 接触：少林の頭付近を通って押し出す
    t = (frame - F_SLIDE_CONTACT) / max(1, SLIDE_FRAMES - F_SLIDE_CONTACT)
    t = min(1.0, t)
    start = fern + move * 0.45
    start.z = BALL_GROUND_Z
    # 前傾した少林の頭側（ルートより -Y）で接触
    mid = Vector((shaolin.x + 0.15, shaolin.y - 3.2, max(0.6, shaolin.z + 0.35)))
    end = shaolin + Vector((3.2, -2.0, 0.0))
    end.z = BALL_GROUND_Z
    if t < 0.15:
        u = t / 0.15
        p = start.lerp(mid, _ease_in_out(u))
    else:
        u = (t - 0.15) / 0.85
        p = mid.lerp(end, _ease_in_out(u))
        p.z = BALL_GROUND_Z + 0.85 * math.sin(min(1.0, u * 1.15) * math.pi)
        if u > 0.5:
            p.z = max(BALL_GROUND_Z, p.z * (1.0 - (u - 0.5) / 0.5) + BALL_GROUND_Z * ((u - 0.5) / 0.5))
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


def _idle_base(arm: bpy.types.Object) -> PoseDict:
    ad = arm.animation_data or arm.animation_data_create()
    muted = [(t, t.mute) for t in ad.nla_tracks]
    for t, _ in muted:
        t.mute = True
    idle = bpy.data.actions.get(_resolve_action_name("idle"))
    prev = ad.action
    ad.action = idle
    bpy.context.scene.frame_set(10)
    bpy.context.view_layer.update()
    base = _snapshot_pose(arm)
    ad.action = prev
    for t, was_muted in muted:
        t.mute = was_muted
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


def _animate_shaolin_slide_pose(arm: bpy.types.Object) -> None:
    base = _idle_base(arm)
    wind = _pose_with_deltas(base, SLIDE_WINDUP, 1.0)
    hit = _pose_with_deltas(base, SLIDE_CONTACT, 1.0)
    up = _pose_with_deltas(base, SLIDE_CONTACT, 0.25)
    keys = [
        (1, base),
        (F_SLIDE_START, base),
        (F_SLIDE_START + 12, wind),
        (F_SLIDE_CONTACT - 6, hit),
        (F_SLIDE_CONTACT, hit),
        (F_SLIDE_END, hit),
        (F_SETTLE, up),
        (SLIDE_FRAMES, base),
    ]
    _add_bone_pose_replace_strip(arm, "Shaolin_HeadSlide", 1, SLIDE_FRAMES, keys, SLIDE_BONES)


def _kf_rot_pitch_yaw(obj: bpy.types.Object, frame: int, pitch: float, yaw: float) -> None:
    obj.rotation_euler = Euler((pitch, 0.0, yaw))
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def _animate_root_sparse(
    root: bpy.types.Object,
    path_fn,
    frames: List[int],
    yaw: float,
    pitch_fn=None,
) -> None:
    _clear_anim(root)
    for f in frames:
        _kf_loc(root, f, path_fn(f))
        pitch = float(pitch_fn(f)) if pitch_fn else 0.0
        _kf_rot_pitch_yaw(root, f, pitch, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _set_hide_keyed(obj: bpy.types.Object, frame: int, hide: bool) -> None:
    obj.hide_render = hide
    obj.hide_viewport = hide
    obj.keyframe_insert(data_path="hide_render", frame=frame)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)


def _solo_dribble_hide_shaolin(shin_arm: bpy.types.Object) -> None:
    """前半はフェルナンデス単独ドリブルに見せるため少林を隠す。"""
    from import_mannequiny import _mesh_child  # noqa: E402

    objs = [shin_arm, _mesh_child(shin_arm), bpy.data.objects.get("Shaolin_01_Root")]
    for obj in objs:
        if not obj:
            continue
        _set_hide_keyed(obj, 1, True)
        _set_hide_keyed(obj, F_SLIDE_START - 12, True)
        _set_hide_keyed(obj, F_SLIDE_START - 11, False)
        _set_hide_keyed(obj, SLIDE_FRAMES, False)


def setup_characters() -> Tuple[
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    fern = build_team(
        "Fernandes",
        PORTUGAL_RED,
        [FERN_START],
        actions=["idle", "run"],
        facing_yaw=FERN_YAW,
    )[0]
    shin = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [SHAOLIN_START],
        actions=["idle", "run", "dash"],
        facing_yaw=SHAOLIN_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(fern), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    return fern, shin, _root_of(fern), _root_of(shin)


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
    cam_data = bpy.data.cameras.new("CamFernandesSlide")
    cam = bpy.data.objects.new("CamFernandesSlide", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    for f in (1, 60, F_SLIDE_START, F_SLIDE_CONTACT, F_SLIDE_END, F_SETTLE, SLIDE_FRAMES):
        fern = _fernandes_path(f)
        shin = _shaolin_path(f)
        if f < F_SLIDE_START:
            mid = fern
            pos = Vector((fern.x - 1.5, fern.y - 8.5, 3.4))
            tgt = Vector((fern.x + 1.2, fern.y, 1.6))
            cam.data.lens = 28
        else:
            mid = (fern + shin) * 0.5
            pos = Vector((mid.x - 0.5, mid.y - 9.2, 3.2))
            tgt = Vector((mid.x + 0.8, mid.y, 1.4))
            cam.data.lens = 26
        cam.data.keyframe_insert(data_path="lens", frame=f)
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_portugal_fernandes_head_slide() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = SLIDE_FRAMES
    scene.render.fps = FPS

    fern_arm, shin_arm, fern_root, shin_root = setup_characters()
    _clear_all_nla(fern_arm)
    _clear_all_nla(shin_arm)

    sparse_f = sorted(
        {
            1,
            30,
            60,
            90,
            120,
            F_SLIDE_START,
            F_SLIDE_CONTACT - 10,
            F_SLIDE_CONTACT,
            F_SLIDE_CONTACT + 12,
            F_SLIDE_END,
            F_SETTLE,
            SLIDE_FRAMES,
        }
    )
    sparse_s = sorted(
        {
            1,
            F_SLIDE_START - 20,
            F_SLIDE_START,
            F_SLIDE_START + 20,
            F_SLIDE_CONTACT - 8,
            F_SLIDE_CONTACT,
            F_SLIDE_CONTACT + 10,
            F_SLIDE_END,
            F_SETTLE,
            SLIDE_FRAMES,
        }
    )
    _animate_root_sparse(fern_root, _fernandes_path, sparse_f, FERN_YAW)
    _animate_root_sparse(
        shin_root, _shaolin_path, sparse_s, SHAOLIN_YAW, pitch_fn=_shaolin_pitch
    )

    # フェルナンデス：走るドリブル → 接触後 idle
    _add_nla_loop(fern_arm, "run", 1, F_SLIDE_CONTACT)
    _add_nla_hold_pose(fern_arm, "idle", F_SLIDE_CONTACT + 1, SLIDE_FRAMES)

    # 少林：接近は dash/run → 接触直前から idle + 前傾ポーズ（脚ループでクリップしない）
    _add_nla_hold_pose(shin_arm, "idle", 1, F_SLIDE_START - 1)
    try:
        _add_nla_once_stretched(shin_arm, "dash", F_SLIDE_START, F_SLIDE_CONTACT - 16)
    except KeyError:
        _add_nla_once_stretched(shin_arm, "run", F_SLIDE_START, F_SLIDE_CONTACT - 16)
    _add_nla_hold_pose(shin_arm, "idle", F_SLIDE_CONTACT - 15, SLIDE_FRAMES)
    _animate_shaolin_slide_pose(shin_arm)
    _solo_dribble_hide_shaolin(shin_arm)

    ball = bpy.data.objects.get("Ball")
    if ball:
        _clear_anim(ball)
        ball.hide_render = False
        ball.hide_viewport = False
        for f in range(1, SLIDE_FRAMES + 1, 2):
            _kf_loc(ball, f, _ball_path(f, _fernandes_path(f), _shaolin_path(f)))
        # 接触周辺は毎フレ
        for f in range(F_SLIDE_CONTACT - 4, min(SLIDE_FRAMES, F_SLIDE_END + 20) + 1):
            _kf_loc(ball, f, _ball_path(f, _fernandes_path(f), _shaolin_path(f)))
        _ease_all_ball_keyframes(ball)
    else:
        print("WARN: Ball not found")

    setup_camera()
    scene.frame_set(1)
    print(
        f"Portugal Fernandes head-slide: {SLIDE_FRAMES}f @ {FPS}fps — "
        "dribble then Shaolin steals with head slide"
    )


def render_portugal_fernandes_head_slide_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = SLIDE_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    out = RENDER_DIR / "portugal_fernandes_head_slide.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Fernandes head-slide: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path, save_blend

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-portugal-fernandes-slide-video" in sys.argv:
        render_portugal_fernandes_head_slide_video()
    else:
        animate_portugal_fernandes_head_slide()
        save_blend(blend)
