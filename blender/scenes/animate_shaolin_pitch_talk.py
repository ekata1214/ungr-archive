# SPDX-License-Identifier: MIT
"""少林選手 — ピッチ上で約3秒話し、軽く頷く"""

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
# 約3秒話す + 軽い頷き
F_TALK_END = 72
F_NOD_PEAK = 82
F_NOD_END = 92
TOTAL_FRAMES = 96  # 約4秒

SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
SHAOLIN_WHITE = (0.96, 0.96, 0.98, 1.0)

# カメラ（-Y）正面
SHAOLIN_YAW = 0.0
SHAOLIN_POS = Vector((0.0, 0.0, 0.0))

PoseDict = Dict[str, Quaternion]

TALK_BONES = ["spine_01", "spine_02", "neck_01", "head"]
NOD_BONES = ["neck_01", "head"]


def _talk_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    t = frame / FPS
    nod = 0.07 * math.sin(t * 6.8) + 0.04 * math.sin(t * 10.5)
    turn = 0.1 * math.sin(t * 2.2 + 0.3) + 0.05 * math.sin(t * 4.7)
    lean = 0.05 * math.sin(t * 1.6)
    return {
        "spine_01": (0.025 + lean * 0.4, 0.0, turn * 0.25),
        "spine_02": (0.045 + lean, 0.0, turn * 0.4),
        "neck_01": (0.04 + nod * 0.65, 0.0, turn * 0.75),
        "head": (0.05 + nod, 0.0, turn),
    }


def _nod_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """話し終わったあとの軽い一頷き。"""
    if frame <= F_TALK_END:
        return {"neck_01": (0.0, 0.0, 0.0), "head": (0.0, 0.0, 0.0)}
    if frame <= F_NOD_PEAK:
        t = (frame - F_TALK_END) / max(1, F_NOD_PEAK - F_TALK_END)
        # ease down
        w = t * t * (3.0 - 2.0 * t)
        return {"neck_01": (0.14 * w, 0.0, 0.0), "head": (0.2 * w, 0.0, 0.0)}
    if frame <= F_NOD_END:
        t = (frame - F_NOD_PEAK) / max(1, F_NOD_END - F_NOD_PEAK)
        w = 1.0 - (t * t * (3.0 - 2.0 * t))
        return {"neck_01": (0.14 * w, 0.0, 0.0), "head": (0.2 * w, 0.0, 0.0)}
    return {"neck_01": (0.0, 0.0, 0.0), "head": (0.0, 0.0, 0.0)}


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    exact = [c for c in candidates if c == name]
    return exact[0] if exact else sorted(candidates)[0]


def _add_nla_loop(
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
    track.name = f"{resolved}_loop"
    strip = track.strips.new(action.name, frame_start, action)
    strip.frame_start = frame_start
    strip.frame_end = frame_end + 1
    act_len = max(1.0, action.frame_range[1] - action.frame_range[0])
    strip.repeat = max(1.0, (frame_end - frame_start + 1) / act_len)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.influence = 1.0
    strip.use_auto_blend = False


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


def _hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if ball:
        ball.hide_render = True
        ball.hide_viewport = True


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
        delta = Euler((xyz[0] * w, xyz[1] * w, xyz[2] * w), "XYZ").to_quaternion()
        out[name] = out[name] @ delta
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


def _animate_root(root: bpy.types.Object) -> None:
    _clear_anim(root)
    for f in (1, F_TALK_END, TOTAL_FRAMES):
        sway = Vector((0.01 * math.sin(f * 0.2), 0.0, 0.0))
        _kf_loc(root, f, SHAOLIN_POS + sway)
        _kf_rot_z(root, f, SHAOLIN_YAW)


def _animate_talk_then_nod(arm: bpy.types.Object) -> None:
    base = _capture_idle_base(arm)
    talk_keys: List[Tuple[int, PoseDict]] = []
    for f in range(1, F_TALK_END + 1, 2):
        talk_keys.append((f, _pose_with_deltas(base, _talk_deltas(f), 1.0)))
    if talk_keys[-1][0] != F_TALK_END:
        talk_keys.append((F_TALK_END, _pose_with_deltas(base, _talk_deltas(F_TALK_END), 1.0)))
    _add_bone_pose_replace_strip(arm, "Shaolin_Talk", 1, F_TALK_END, talk_keys, TALK_BONES)

    nod_keys: List[Tuple[int, PoseDict]] = [
        (F_TALK_END, base),
        (F_NOD_PEAK, _pose_with_deltas(base, _nod_deltas(F_NOD_PEAK), 1.0)),
        (F_NOD_END, base),
        (TOTAL_FRAMES, base),
    ]
    _add_bone_pose_replace_strip(arm, "Shaolin_Nod", F_TALK_END, TOTAL_FRAMES, nod_keys, NOD_BONES)


def setup_character() -> Tuple[bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    shin = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [SHAOLIN_POS],
        actions=["idle"],
        facing_yaw=SHAOLIN_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(shin), SHAOLIN_ORANGE, SHAOLIN_WHITE, z_cut=0.42)
    return shin, _root_of(shin)


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
    cam_data = bpy.data.cameras.new("CamShaolinTalk")
    cam = bpy.data.objects.new("CamShaolinTalk", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_data.lens = 35

    for f in (1, F_TALK_END, TOTAL_FRAMES):
        t = (f - 1) / max(1, TOTAL_FRAMES - 1)
        # 全身〜胸上が入る正面ミディアム
        pos = Vector((-0.35 + 0.1 * t, -8.6 + 0.5 * t, 2.55 - 0.1 * t))
        tgt = Vector((0.0, 0.05, 1.55))
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_shaolin_pitch_talk() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.render.fps = FPS

    _hide_ball()
    arm, root = setup_character()
    _clear_all_nla(arm)
    _animate_root(root)
    _add_nla_loop(arm, "idle", 1, TOTAL_FRAMES)
    _animate_talk_then_nod(arm)
    setup_camera()
    scene.frame_set(1)
    print(
        f"Shaolin pitch talk: {TOTAL_FRAMES}f @ {FPS}fps — "
        f"talk ~{F_TALK_END / FPS:.1f}s then light nod"
    )


def render_shaolin_pitch_talk_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

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
    out = RENDER_DIR / "shaolin_pitch_talk.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Shaolin pitch talk: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-shaolin-pitch-talk-video" in sys.argv:
        render_shaolin_pitch_talk_video()
    else:
        animate_shaolin_pitch_talk()
