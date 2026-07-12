# SPDX-License-Identifier: MIT
"""ポルトガル戦 — シンがレオンに握手を求める（手前ロナウド idle、奥で握手）"""

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

FPS = 24

# 尺は長め — 各アクションが全部見えるまで余裕を持たせる（約18秒）
HANDSHAKE_FRAMES = 432

# タイムライン
F_INTRO = 1
F_WALK_START = 72
F_WALK_END = 228
F_ARRIVE_HOLD = 258
F_HAND_OFFER = 288
F_OFFER_HOLD = 330
F_LEAO_REPLY = 360
F_HANDSHAKE_HOLD = 432

SHIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

SHIN_YAW = math.pi * 1.5
LEAO_YAW = math.pi / 2
# 手前ロナウド — 奥の2人の方を向く（今までと逆）
RONALDO_YAW = math.pi

# 奥：シン＋レオン / 手前：ロナウド
LEAO_POS = Vector((2.15, 5.0, 0.0))
SHIN_START = Vector((20.0, 4.8, 0.0))
SHIN_END = Vector((5.05, 5.0, 0.0))  # 握手時に手が重なる距離
RONALDO_POS = Vector((1.0, -5.5, 0.0))

SHIN_OFFER_DELTA = {
    "upperarm.r": (0.0, 0.0, 1.9),
    "lowerarm.r": (0.85, 0.0, 0.0),
}
LEAO_OFFER_DELTA = {
    "upperarm.r": (0.0, 0.0, 1.9),
    "lowerarm.r": (0.85, 0.0, 0.0),
}
ARM_NEUTRAL = (0.0, 0.0, 0.0)


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
    """シン — 奥でレオンの方へ歩行 → 到着 → 喜びのホップ"""
    if frame < F_WALK_START:
        return SHIN_START.copy()
    if frame <= F_WALK_END:
        t = (frame - F_WALK_START) / max(1, F_WALK_END - F_WALK_START)
        t = t * t * (3.0 - 2.0 * t)
        return SHIN_START.lerp(SHIN_END, t)
    p = SHIN_END.copy()
    if F_WALK_END < frame <= F_ARRIVE_HOLD:
        hop = (frame - F_WALK_END) / (F_ARRIVE_HOLD - F_WALK_END)
        # 嬉しそうなジャンプ — 高め＋二連跳ね
        p.z = 0.65 * math.sin(hop * math.pi) + 0.22 * math.sin(hop * math.pi * 2.0)
    return p


def _add_pose_overlay_strip(
    arm: bpy.types.Object,
    name: str,
    strip_start: int,
    strip_end: int,
    bone_keys: List[Tuple[int, dict]],
) -> None:
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
    strip.frame_end = strip_end + 1
    strip.action_frame_start = min(f for f, _ in bone_keys)
    strip.action_frame_end = max(f for f, _ in bone_keys)
    strip.blend_type = "ADD"
    strip.extrapolation = "HOLD_FORWARD"


def _bones(**kwargs: Tuple[float, float, float]) -> dict:
    return {k.replace("_", "."): v for k, v in kwargs.items()}


def _animate_handshake_poses(shin_arm: bpy.types.Object, leao_arm: bpy.types.Object) -> None:
    """奥のシン＋レオンのみ握手。ロナウドにはポーズを付けない。"""
    z = ARM_NEUTRAL
    sd, ld = SHIN_OFFER_DELTA, LEAO_OFFER_DELTA

    _add_pose_overlay_strip(
        shin_arm,
        "Shin_ExcitedHandshake",
        F_WALK_END,
        HANDSHAKE_FRAMES,
        [
            (F_WALK_END, _bones(upperarm_r=z, lowerarm_r=z, spine_02=z, neck_01=z, head=z)),
            (F_WALK_END + 18, _bones(
                upperarm_r=z, lowerarm_r=z,
                spine_02=(0.1, 0.0, 0.0), neck_01=(0.08, 0.0, -0.06), head=(0.05, 0.0, -0.08),
            )),
            (F_ARRIVE_HOLD, _bones(
                upperarm_r=z, lowerarm_r=z,
                spine_02=(0.1, 0.0, 0.0), neck_01=(0.08, 0.0, -0.06), head=(0.05, 0.0, -0.08),
            )),
            (F_HAND_OFFER - 12, _bones(
                upperarm_r=(sd["upperarm.r"][0] * 0.4, sd["upperarm.r"][1], sd["upperarm.r"][2] * 0.4),
                lowerarm_r=(sd["lowerarm.r"][0] * 0.4, 0.0, 0.0),
                spine_02=(0.11, 0.0, 0.0), neck_01=(0.09, 0.0, -0.07), head=(0.05, 0.0, -0.09),
            )),
            (F_HAND_OFFER, _bones(
                upperarm_r=sd["upperarm.r"], lowerarm_r=sd["lowerarm.r"],
                spine_02=(0.12, 0.0, 0.0), neck_01=(0.1, 0.0, -0.08), head=(0.06, 0.0, -0.1),
            )),
            (F_OFFER_HOLD, _bones(
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
        F_LEAO_REPLY - 12,
        HANDSHAKE_FRAMES,
        [
            (F_LEAO_REPLY - 12, _bones(upperarm_r=z, lowerarm_r=z)),
            (F_LEAO_REPLY, _bones(
                upperarm_r=(ld["upperarm.r"][0] * 0.5, 0.0, ld["upperarm.r"][2] * 0.5),
                lowerarm_r=(ld["lowerarm.r"][0] * 0.5, 0.0, 0.0),
            )),
            (F_LEAO_REPLY + 18, _bones(upperarm_r=ld["upperarm.r"], lowerarm_r=ld["lowerarm.r"])),
            (HANDSHAKE_FRAMES, _bones(upperarm_r=ld["upperarm.r"], lowerarm_r=ld["lowerarm.r"])),
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
        actions=["idle"],
        facing_yaw=SHIN_YAW,
    )[0]
    leao_arm = build_team(
        "Leao",
        PORTUGAL_RED,
        [LEAO_POS],
        actions=["idle"],
        facing_yaw=LEAO_YAW,
    )[0]
    ronaldo_arm = build_team(
        "Ronaldo",
        PORTUGAL_RED,
        [RONALDO_POS],
        actions=["idle"],
        facing_yaw=RONALDO_YAW,
    )[0]

    set_mesh_split_vertical(_mesh_child(leao_arm), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    set_mesh_split_vertical(_mesh_child(ronaldo_arm), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)

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
    _animate_root_fixed(leao_root, leao_keys, LEAO_YAW)
    _animate_root_fixed(ronaldo_root, ronaldo_keys, RONALDO_YAW)

    # シン：待機 → 歩行 → 到着後 idle
    _add_nla_strip(shin_arm, "idle", 1, F_WALK_START - 1)
    _add_nla_strip(shin_arm, "walk", F_WALK_START, F_WALK_END)
    _add_nla_strip(shin_arm, "idle", F_WALK_END + 1, HANDSHAKE_FRAMES)

    # レオン・ロナウド：ずっと idle のみ（ロナウドにポーズ追加なし）
    _add_nla_strip(leao_arm, "idle", 1, HANDSHAKE_FRAMES)
    _add_nla_strip(ronaldo_arm, "idle", 1, HANDSHAKE_FRAMES)

    _animate_handshake_poses(shin_arm, leao_arm)

    setup_portugal_handshake_camera()
    scene.frame_set(1)
    print(
        f"Portugal handshake: {HANDSHAKE_FRAMES}f @ {FPS}fps — "
        "foreground Ronaldo idle, background Shin-Leao handshake"
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
    """手前ロナウド＋奥の握手が同時に見える構図"""
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamPortugalHandshake")
    cam = bpy.data.objects.new("CamPortugalHandshake", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 20

    bg_target = (SHIN_END + LEAO_POS) * 0.5 + Vector((0.0, 0.0, 2.2))

    key_frames = [
        F_INTRO,
        F_WALK_START,
        F_WALK_END,
        F_HAND_OFFER,
        F_OFFER_HOLD,
        F_LEAO_REPLY,
        HANDSHAKE_FRAMES,
    ]
    for f in key_frames:
        # やや引いた肩越し — 手前ロナウド全身＋奥の握手
        cam_pos = RONALDO_POS + Vector((2.5, -5.5, 4.8))
        cam_tgt = bg_target
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
