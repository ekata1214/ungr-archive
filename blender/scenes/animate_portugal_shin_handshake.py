# SPDX-License-Identifier: MIT
"""ポルトガル戦 — シンがレオンに握手を求める（ロナウド無視）"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import bpy
from mathutils import Euler, Vector

from animate_soccer_match import (
    _add_nla_strip,
    _clear_all_nla,
    _clear_anim,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

HANDSHAKE_FRAMES = 180
FPS = 24

SHIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
PORTUGAL_BLUE = (0.08, 0.22, 0.65, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

# シンは -X へ、ポルトガルは +X 向き
SHIN_YAW = math.pi * 1.5
PORTUGAL_YAW = math.pi / 2

LEAO_POS = Vector((1.5, 0.8, 0.0))
RONALDO_POS = Vector((11.0, -4.2, 0.0))
SHIN_START = Vector((18.0, -1.2, 0.0))
SHIN_END = Vector((7.6, 0.85, 0.0))  # レオンの前で止まる（握手は腕だけ伸ばす）

WALK_END = 105
HAND_OFFER = 118
HAND_HOLD = 140

# 握手ポーズ（idle への ADD オーバーレイ — 右腕を前方へ）
SHIN_OFFER_DELTA = {
    "upperarm.r": (0.0, 0.0, 1.4),
    "lowerarm.r": (0.3, 0.0, 0.0),
}
LEAO_OFFER_DELTA = {
    "upperarm.r": (0.0, 0.0, 1.4),
    "lowerarm.r": (0.3, 0.0, 0.0),
}
ARM_NEUTRAL = (0.0, 0.0, 0.0)

RONALDO_WATCH_YAW = 2.2


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


def _shin_path(frame: int) -> Vector:
    """シン — ロナウドを横目に、レオンの方へ直進 → 到着で小ジャンプ"""
    if frame <= WALK_END:
        t = min(1.0, (frame - 1) / max(1, WALK_END - 1))
        t = t * t * (3.0 - 2.0 * t)
        p = SHIN_START.lerp(SHIN_END, t)
    else:
        p = SHIN_END.copy()
    if WALK_END < frame <= WALK_END + 14:
        hop = (frame - WALK_END) / 14.0
        p.z = 0.28 * math.sin(hop * math.pi)
    return p


def _ronaldo_yaw(frame: int) -> float:
    """ロナウド — 握手の様子を見るために振り向く"""
    watch_start, watch_end = 92, 118
    if frame < watch_start:
        return PORTUGAL_YAW
    if frame >= watch_end:
        return RONALDO_WATCH_YAW
    t = (frame - watch_start) / (watch_end - watch_start)
    t = t * t * (3.0 - 2.0 * t)
    return PORTUGAL_YAW + (RONALDO_WATCH_YAW - PORTUGAL_YAW) * t


def _animate_root_with_yaw(
    root: bpy.types.Object,
    keys: List[Tuple[int, Vector]],
    yaw_at: callable,
) -> None:
    _clear_anim(root)
    for f, loc in keys:
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, yaw_at(f))
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _kf_pose_euler(
    arm: bpy.types.Object,
    bone_name: str,
    frame: int,
    rot: Tuple[float, float, float],
) -> None:
    bpy.context.scene.frame_set(frame)
    bone = arm.pose.bones.get(bone_name)
    if not bone:
        return
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = Euler(rot)
    bone.keyframe_insert(data_path="rotation_euler", frame=frame)


def _add_pose_overlay_strip(
    arm: bpy.types.Object,
    name: str,
    strip_start: int,
    strip_end: int,
    bone_keys: List[Tuple[int, dict]],
) -> None:
    """idle/walk の上に ADD でポーズを重ねる（NLA が腕を潰さないように）"""
    if not arm.animation_data:
        arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    for frame, rotations in bone_keys:
        bpy.context.scene.frame_set(frame)
        for bone_name, rot in rotations.items():
            bone = arm.pose.bones.get(bone_name)
            if not bone:
                continue
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = Euler(rot)
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
    arm.animation_data.action = None
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, strip_start, act)
    strip.frame_end = strip_end
    strip.action_frame_start = min(f for f, _ in bone_keys)
    strip.action_frame_end = max(f for f, _ in bone_keys)
    strip.blend_type = "ADD"
    strip.extrapolation = "HOLD_FORWARD"


def _bones(**kwargs: Tuple[float, float, float]) -> dict:
    """キーワード引数をボーン名へ（upperarm_r → upperarm.r）"""
    return {k.replace("_", "."): v for k, v in kwargs.items()}


def _animate_handshake_poses(
    shin_arm: bpy.types.Object,
    leao_arm: bpy.types.Object,
    ronaldo_arm: bpy.types.Object,
) -> None:
    """喜んで握手を差し出すシン、応えるレオン、それを見るロナウド"""
    z = ARM_NEUTRAL
    sd, ld = SHIN_OFFER_DELTA, LEAO_OFFER_DELTA

    _add_pose_overlay_strip(
        shin_arm,
        "Shin_ExcitedHandshake",
        WALK_END,
        HANDSHAKE_FRAMES,
        [
            (WALK_END, _bones(upperarm_r=z, lowerarm_r=z, spine_02=z, neck_01=z, head=z)),
            (WALK_END + 6, _bones(
                upperarm_r=z, lowerarm_r=z,
                spine_02=(0.1, 0.0, 0.0), neck_01=(0.08, 0.0, -0.06), head=(0.05, 0.0, -0.08),
            )),
            (HAND_OFFER, _bones(
                upperarm_r=sd["upperarm.r"], lowerarm_r=sd["lowerarm.r"],
                spine_02=(0.12, 0.0, 0.0), neck_01=(0.1, 0.0, -0.08), head=(0.06, 0.0, -0.1),
            )),
            (HANDSHAKE_FRAMES, _bones(
                upperarm_r=sd["upperarm.r"], lowerarm_r=sd["lowerarm.r"],
                spine_02=(0.12, 0.0, 0.0), neck_01=(0.1, 0.0, -0.08), head=(0.06, 0.0, -0.1),
            )),
        ],
    )

    _add_pose_overlay_strip(
        leao_arm,
        "Leao_HandshakeReply",
        HAND_OFFER + 6,
        HANDSHAKE_FRAMES,
        [
            (HAND_OFFER + 6, _bones(upperarm_r=z, lowerarm_r=z)),
            (HAND_OFFER + 16, _bones(upperarm_r=ld["upperarm.r"], lowerarm_r=ld["lowerarm.r"])),
            (HANDSHAKE_FRAMES, _bones(upperarm_r=ld["upperarm.r"], lowerarm_r=ld["lowerarm.r"])),
        ],
    )

    _add_pose_overlay_strip(
        ronaldo_arm,
        "Ronaldo_Watching",
        95,
        HANDSHAKE_FRAMES,
        [
            (95, _bones(neck_01=z, head=z, upperarm_r=z, lowerarm_r=z, upperarm_l=z, lowerarm_l=z)),
            (120, _bones(
                neck_01=(0.18, 0.0, 0.55), head=(0.12, 0.0, 0.45),
                upperarm_r=(0.35, 0.0, -0.15), lowerarm_r=(0.25, 0.0, 0.0),
                upperarm_l=(0.35, 0.0, 0.15), lowerarm_l=(0.25, 0.0, 0.0),
            )),
            (HANDSHAKE_FRAMES, _bones(
                neck_01=(0.18, 0.0, 0.55), head=(0.12, 0.0, 0.45),
                upperarm_r=(0.35, 0.0, -0.15), lowerarm_r=(0.25, 0.0, 0.0),
                upperarm_l=(0.35, 0.0, 0.15), lowerarm_l=(0.25, 0.0, 0.0),
            )),
        ],
    )


def setup_portugal_handshake_characters() -> Tuple[
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()

    shin_arm = build_team(
        "Shin",
        SHIN_ORANGE,
        [SHIN_START],
        actions=["walk"],
        facing_yaw=SHIN_YAW,
    )[0]
    leao_arm = build_team(
        "Leao",
        PORTUGAL_BLUE,
        [LEAO_POS],
        actions=["idle"],
        facing_yaw=PORTUGAL_YAW,
    )[0]
    ronaldo_arm = build_team(
        "Ronaldo",
        PORTUGAL_BLUE,
        [RONALDO_POS],
        actions=["idle"],
        facing_yaw=PORTUGAL_YAW,
    )[0]

    set_mesh_split_vertical(_mesh_child(leao_arm), PORTUGAL_BLUE, PORTUGAL_GREEN, z_cut=0.42)
    set_mesh_split_vertical(_mesh_child(ronaldo_arm), PORTUGAL_BLUE, PORTUGAL_GREEN, z_cut=0.42)

    return (
        shin_arm,
        leao_arm,
        ronaldo_arm,
        _root_of(shin_arm),
        _root_of(leao_arm),
        _root_of(ronaldo_arm),
    )


def _hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if ball:
        ball.hide_render = True
        ball.hide_viewport = True


def animate_portugal_shin_handshake() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = HANDSHAKE_FRAMES
    scene.render.fps = FPS

    shin_arm, leao_arm, ronaldo_arm, shin_root, leao_root, ronaldo_root = (
        setup_portugal_handshake_characters()
    )

    for arm in (shin_arm, leao_arm, ronaldo_arm):
        _clear_all_nla(arm)

    ball = bpy.data.objects.get("Ball")
    if ball and ball.animation_data:
        ball.animation_data_clear()
    _hide_ball()

    shin_keys = [(f, _shin_path(f)) for f in range(1, HANDSHAKE_FRAMES + 1)]
    leao_keys = [(f, LEAO_POS) for f in range(1, HANDSHAKE_FRAMES + 1)]
    ronaldo_keys = [(f, RONALDO_POS) for f in range(1, HANDSHAKE_FRAMES + 1)]

    _animate_root_fixed(shin_root, shin_keys, SHIN_YAW)
    _animate_root_fixed(leao_root, leao_keys, PORTUGAL_YAW)
    _animate_root_with_yaw(ronaldo_root, ronaldo_keys, _ronaldo_yaw)

    _add_nla_strip(shin_arm, "walk", 1, WALK_END)
    _add_nla_strip(shin_arm, "idle", WALK_END + 1, HANDSHAKE_FRAMES)
    _add_nla_strip(leao_arm, "idle", 1, HANDSHAKE_FRAMES)
    _add_nla_strip(ronaldo_arm, "idle", 1, HANDSHAKE_FRAMES)

    _animate_handshake_poses(shin_arm, leao_arm, ronaldo_arm)

    setup_portugal_handshake_camera()
    scene.frame_set(1)
    print(
        f"Portugal handshake: {HANDSHAKE_FRAMES}f — "
        "Shin seeks Leao handshake, Ronaldo ignored"
    )


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_portugal_handshake_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamPortugalHandshake")
    cam = bpy.data.objects.new("CamPortugalHandshake", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 22  # 広角で3人全身

    key_frames = [1, 50, WALK_END, HAND_OFFER, HANDSHAKE_FRAMES]
    for f in key_frames:
        shin = _shin_path(f)
        group_center = (shin + LEAO_POS + RONALDO_POS) / 3.0
        cam_pos = group_center + Vector((0.0, -17.5, 5.2))
        cam_tgt = group_center + Vector((0.0, 0.0, 2.1))
        _kf_cam(cam, f, cam_pos, cam_tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def render_portugal_handshake_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = HANDSHAKE_FRAMES
    scene.eevee.taa_render_samples = 8

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "portugal_shin_handshake.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering portugal handshake video: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-portugal-handshake-video" in sys.argv:
        render_portugal_handshake_video()
    else:
        animate_portugal_shin_handshake()
        bpy.ops.wm.save_mainfile(filepath=str(blend))
