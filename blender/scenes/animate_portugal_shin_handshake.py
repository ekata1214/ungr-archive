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

LEAO_POS = Vector((2.5, 0.6, 0.0))
RONALDO_POS = Vector((9.0, -2.8, 0.0))
SHIN_START = Vector((16.0, -1.8, 0.0))
SHIN_END = Vector((3.8, 0.75, 0.0))

WALK_END = 108
HAND_REACH = 132


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
    """シン — ロナウドを横目に、レオンの方へ直進"""
    if frame <= WALK_END:
        t = min(1.0, (frame - 1) / max(1, WALK_END - 1))
        t = t * t * (3.0 - 2.0 * t)  # smoothstep
        return SHIN_START.lerp(SHIN_END, t)
    return SHIN_END


def _ronaldo_path(frame: int) -> Vector:
    """ロナウド — 待機、シン通過で少し振り向く"""
    p = RONALDO_POS.copy()
    if 70 <= frame <= 95:
        t = (frame - 70) / 25.0
        p.y += 0.35 * math.sin(t * math.pi)
    return p


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


def _animate_handshake_poses(
    shin_arm: bpy.types.Object,
    leao_arm: bpy.types.Object,
    ronaldo_arm: bpy.types.Object,
) -> None:
    """握手ポーズ — シンが手を差し伸べ、レオンが応える。ロナウドは腕組み気味。"""
    for arm in (shin_arm, leao_arm, ronaldo_arm):
        if not arm.animation_data:
            arm.animation_data_create()

    for f in (1, WALK_END - 8, HAND_REACH, HANDSHAKE_FRAMES):
        _kf_pose_euler(shin_arm, "upperarm.l", f, (0.15, 0.0, 0.0))
        _kf_pose_euler(shin_arm, "lowerarm.l", f, (0.05, 0.0, 0.0))

    for f, ua, la in (
        (WALK_END, (0.15, 0.0, 0.0), (0.05, 0.0, 0.0)),
        (HAND_REACH - 6, (0.55, 0.0, -0.35), (0.85, 0.0, 0.0)),
        (HAND_REACH, (0.95, 0.0, -0.55), (1.15, 0.0, 0.0)),
        (HANDSHAKE_FRAMES, (0.95, 0.0, -0.55), (1.15, 0.0, 0.0)),
    ):
        _kf_pose_euler(shin_arm, "upperarm.l", f, ua)
        _kf_pose_euler(shin_arm, "lowerarm.l", f, la)

    for f, ua, la in (
        (1, (0.15, 0.0, 0.0), (0.05, 0.0, 0.0)),
        (HAND_REACH - 4, (0.45, 0.0, 0.35), (0.75, 0.0, 0.0)),
        (HAND_REACH + 6, (0.75, 0.0, 0.45), (1.05, 0.0, 0.0)),
        (HANDSHAKE_FRAMES, (0.75, 0.0, 0.45), (1.05, 0.0, 0.0)),
    ):
        _kf_pose_euler(leao_arm, "upperarm.r", f, ua)
        _kf_pose_euler(leao_arm, "lowerarm.r", f, la)

    for f, ua, la in (
        (1, (0.15, 0.0, 0.0), (0.05, 0.0, 0.0)),
        (80, (0.35, 0.0, -0.25), (0.55, 0.0, 0.0)),
        (HANDSHAKE_FRAMES, (0.55, 0.0, -0.35), (0.95, 0.0, 0.0)),
    ):
        _kf_pose_euler(ronaldo_arm, "upperarm.l", f, ua)
        _kf_pose_euler(ronaldo_arm, "lowerarm.l", f, la)


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
    ronaldo_keys = [(f, _ronaldo_path(f)) for f in range(1, HANDSHAKE_FRAMES + 1)]

    _animate_root_fixed(shin_root, shin_keys, SHIN_YAW)
    _animate_root_fixed(leao_root, leao_keys, PORTUGAL_YAW)
    _animate_root_fixed(ronaldo_root, ronaldo_keys, PORTUGAL_YAW)

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
    cam.data.lens = 32

    key_frames = [1, 50, WALK_END, HAND_REACH, HANDSHAKE_FRAMES]
    for f in key_frames:
        shin = _shin_path(f)
        mid = (shin + LEAO_POS + RONALDO_POS) / 3.0
        cam_pos = mid + Vector((0.0, -7.8, 1.85))
        cam_tgt = (shin + LEAO_POS) * 0.5 + Vector((0.0, 0.0, 1.05))
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
