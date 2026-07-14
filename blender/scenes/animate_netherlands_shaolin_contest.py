# SPDX-License-Identifier: MIT
"""オランダ代表 vs 少林 — ボール争奪

オランダ（濃いオレンジ一色）と少林選手が、中央のボールを肩を寄せて奪い合う。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

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

F_APPROACH_END = 48
F_CONTACT = 72
F_STRUGGLE = 108
F_SETTLE = 150

# 互いに向かい合う（±X）
NED_YAW = math.pi / 2  # +X
SHAOLIN_YAW = -math.pi / 2  # -X
NED_START = Vector((-7.5, 0.15, 0.0))
SHAOLIN_START = Vector((7.5, -0.15, 0.0))
# 接触時の根の目標（中心で肩がぶつかる距離）
NED_CONTACT = Vector((-1.15, 0.2, 0.0))
SHAOLIN_CONTACT = Vector((1.15, -0.2, 0.0))

# オランダ：濃いオレンジ一色 / 少林：明るいオレンジ一色（区別用）
NETHERLANDS_ORANGE = (0.78, 0.28, 0.02, 1.0)
SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)

PoseDict = Dict[str, Quaternion]

CONTEST_BONES = [
    "pelvis",
    "spine_01",
    "spine_02",
    "neck_01",
    "head",
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "thigh.l",
    "thigh.r",
    "calf.l",
    "calf.r",
]

# 右向き（オランダ）：相手方向へ前傾＋腕を前に出してボールを切る
CONTEST_DELTA_R = {
    "pelvis": (0.18, 0.0, 0.0),
    "spine_01": (0.28, 0.0, 0.06),
    "spine_02": (0.35, 0.0, 0.08),
    "neck_01": (0.22, 0.0, 0.0),
    "head": (0.15, 0.0, 0.0),
    "clavicle.r": (0.2, -0.15, 0.1),
    "upperarm.r": (0.85, 0.55, 0.25),
    "lowerarm.r": (-1.1, 0.35, 0.15),
    "clavicle.l": (0.15, 0.2, -0.08),
    "upperarm.l": (0.7, -0.65, -0.2),
    "lowerarm.l": (-0.95, -0.25, -0.1),
    "thigh.l": (0.35, 0.12, -0.08),
    "thigh.r": (0.45, -0.1, 0.1),
    "calf.l": (-0.25, 0.0, 0.0),
    "calf.r": (-0.35, 0.0, 0.0),
}

# 左向き（少林）：ミラー
CONTEST_DELTA_L = {
    "pelvis": (0.18, 0.0, 0.0),
    "spine_01": (0.28, 0.0, -0.06),
    "spine_02": (0.35, 0.0, -0.08),
    "neck_01": (0.22, 0.0, 0.0),
    "head": (0.15, 0.0, 0.0),
    "clavicle.r": (0.15, -0.2, 0.08),
    "upperarm.r": (0.7, 0.65, 0.2),
    "lowerarm.r": (-0.95, 0.25, 0.1),
    "clavicle.l": (0.2, 0.15, -0.1),
    "upperarm.l": (0.85, -0.55, -0.25),
    "lowerarm.l": (-1.1, -0.35, -0.15),
    "thigh.l": (0.45, 0.1, -0.1),
    "thigh.r": (0.35, -0.12, 0.08),
    "calf.l": (-0.35, 0.0, 0.0),
    "calf.r": (-0.25, 0.0, 0.0),
}


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


def _ned_path(frame: int) -> Vector:
    if frame <= F_APPROACH_END:
        t = _ease_in_out((frame - 1) / max(1, F_APPROACH_END - 1))
        p = NED_START.lerp(NED_CONTACT, t)
        p.y += 0.12 * math.sin(t * math.pi)
        return p
    # 接触後：押し合いで微小に揺れる
    phase = (frame - F_APPROACH_END) * 0.28
    shove = 0.12 * math.sin(phase) + 0.06 * math.sin(phase * 1.7 + 0.4)
    p = NED_CONTACT.copy()
    p.x += shove
    p.y += 0.08 * math.sin(phase * 1.3)
    if frame >= F_STRUGGLE:
        p.x += 0.05 * math.sin((frame - F_STRUGGLE) * 0.35)
    return p


def _shaolin_path(frame: int) -> Vector:
    if frame <= F_APPROACH_END:
        t = _ease_in_out((frame - 1) / max(1, F_APPROACH_END - 1))
        p = SHAOLIN_START.lerp(SHAOLIN_CONTACT, t)
        p.y -= 0.12 * math.sin(t * math.pi)
        return p
    phase = (frame - F_APPROACH_END) * 0.28
    shove = 0.12 * math.sin(phase + 0.9) + 0.06 * math.sin(phase * 1.7 + 1.2)
    p = SHAOLIN_CONTACT.copy()
    p.x -= shove
    p.y -= 0.08 * math.sin(phase * 1.3 + 0.5)
    if frame >= F_STRUGGLE:
        p.x -= 0.05 * math.sin((frame - F_STRUGGLE) * 0.35 + 0.7)
    return p


def _ball_path(frame: int) -> Vector:
    """両足の間で跳ねる争奪ボール。"""
    ned = _ned_path(frame)
    shin = _shaolin_path(frame)
    mid = (ned + shin) * 0.5
    if frame < F_CONTACT:
        # 中央へ転がる
        t = _ease_in_out((frame - 1) / max(1, F_CONTACT - 1))
        start = Vector((0.0, 0.0, BALL_GROUND_Z))
        p = start.lerp(Vector((mid.x, mid.y, BALL_GROUND_Z)), t)
        p.z = BALL_GROUND_Z
        return p
    # 接触後：足元で小刻みに弾む
    phase = (frame - F_CONTACT) * 0.55
    wobble = Vector(
        (
            0.22 * math.sin(phase * 1.4),
            0.18 * math.sin(phase * 1.9 + 0.6),
            0.0,
        )
    )
    bounce = abs(math.sin(phase * 2.2)) * 0.22
    p = Vector((mid.x, mid.y, BALL_GROUND_Z)) + wobble
    p.z = BALL_GROUND_Z + bounce
    return p


def _animate_root(
    root: bpy.types.Object,
    path_fn,
    yaw: float,
) -> None:
    _clear_anim(root)
    sparse = sorted(
        {
            1,
            F_APPROACH_END // 2,
            F_APPROACH_END,
            F_CONTACT,
            F_STRUGGLE,
            F_SETTLE,
            CONTEST_FRAMES,
        }
    )
    for f in sparse:
        _kf_loc(root, f, path_fn(f))
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _animate_contest_pose(arm: bpy.types.Object, deltas: Dict[str, Tuple[float, float, float]], tag: str) -> None:
    base = _capture_idle_base(arm)
    keys: List[Tuple[int, PoseDict]] = [
        (1, base),
        (F_APPROACH_END, _pose_with_deltas(base, deltas, 0.25)),
        (F_CONTACT, _pose_with_deltas(base, deltas, 0.75)),
        (F_STRUGGLE, _pose_with_deltas(base, deltas, 1.0)),
        (F_SETTLE, _pose_with_deltas(base, deltas, 1.0)),
    ]
    for f in range(F_SETTLE + 6, CONTEST_FRAMES + 1, 6):
        wiggle = 0.03 * math.sin((f - F_SETTLE) * 0.55)
        d = {
            k: (
                v[0] + (wiggle if "spine" in k or "pelvis" in k else 0.0),
                v[1],
                v[2] + (0.02 * math.sin(f * 0.4) if "upperarm" in k else 0.0),
            )
            for k, v in deltas.items()
        }
        keys.append((f, _pose_with_deltas(base, d, 1.0)))
    if keys[-1][0] != CONTEST_FRAMES:
        keys.append((CONTEST_FRAMES, _pose_with_deltas(base, deltas, 1.0)))
    _add_bone_pose_replace_strip(arm, f"{tag}_Contest", 1, CONTEST_FRAMES, keys, CONTEST_BONES)


def setup_characters() -> Tuple[
    bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object
]:
    from import_mannequiny import build_team  # noqa: E402

    _remove_all_players()
    ned = build_team(
        "Netherlands",
        NETHERLANDS_ORANGE,
        [NED_START],
        actions=["run", "idle"],
        facing_yaw=NED_YAW,
    )[0]
    shin = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [SHAOLIN_START],
        actions=["run", "idle"],
        facing_yaw=SHAOLIN_YAW,
    )[0]
    # オランダは濃いオレンジ一色（split しない）
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
    cam_data.lens = 28

    for f in (1, F_APPROACH_END, F_CONTACT, F_STRUGGLE, F_SETTLE, CONTEST_FRAMES):
        mid = (_ned_path(f) + _shaolin_path(f)) * 0.5
        t = (f - 1) / max(1, CONTEST_FRAMES - 1)
        # ワイド → 争奪へ寄る
        pos = Vector((mid.x * 0.2, -11.5 + 2.2 * t, 3.4 - 0.4 * t))
        tgt = Vector((mid.x, mid.y, 1.7))
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
    _clear_all_nla(ned_arm)
    _clear_all_nla(shin_arm)
    if ball.animation_data:
        ball.animation_data_clear()

    _animate_root(ned_root, _ned_path, NED_YAW)
    _animate_root(shin_root, _shaolin_path, SHAOLIN_YAW)

    # 接近はラン、接触からは idle＋争奪ポーズ
    _add_nla_strip(ned_arm, "run", 1, F_CONTACT)
    _add_nla_strip(shin_arm, "run", 1, F_CONTACT)
    _add_nla_hold_pose(ned_arm, "idle", F_CONTACT, CONTEST_FRAMES)
    _add_nla_hold_pose(shin_arm, "idle", F_CONTACT, CONTEST_FRAMES)
    _animate_contest_pose(ned_arm, CONTEST_DELTA_R, "Ned")
    _animate_contest_pose(shin_arm, CONTEST_DELTA_L, "Shaolin")

    sparse_ball = sorted(
        set(range(1, CONTEST_FRAMES + 1, 3)) | {1, F_CONTACT, F_STRUGGLE, CONTEST_FRAMES}
    )
    for f in sparse_ball:
        _kf_loc(ball, f, _ball_path(f))
    _ease_all_ball_keyframes(ball)

    setup_camera()
    scene.frame_set(1)
    print(
        f"Netherlands vs Shaolin contest: {CONTEST_FRAMES}f @ {FPS}fps — "
        "dark-orange Ned + Shaolin fight for the ball (~9s)"
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
    print(f"Rendering Netherlands contest: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-netherlands-contest-video" in sys.argv:
        render_netherlands_shaolin_contest_video()
    else:
        animate_netherlands_shaolin_contest()
