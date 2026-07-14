# SPDX-License-Identifier: MIT
"""ポルトガル戦 — シンがレオンに握手を求める（手前ロナウド idle、奥で握手）

流れ:
  シン: idle → 楽しそうに走っていく → 到着ホップ → 右手を差し出す
  レオン: idle のまま待つ → 左手で握手に応じる
  ロナウド: 手前で idle のみ（ポーズ変更なし）
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

from animate_soccer_match import (
    _add_nla_strip as _add_nla_strip_raw,
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
F_RUN_START = 48
F_RUN_END = 216
F_ARRIVE_HOLD = 252
F_HAND_OFFER = 288
F_OFFER_HOLD = 330
F_LEAO_REPLY = 360
F_HANDSHAKE_HOLD = 432

SHIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

# カメラは -Y 側から見るので、握手ペアは Y 方向に対面させる
# （X 対面だと腕の伸びがカメラから T-pose に見える）
SHIN_YAW = math.pi          # -Y 向き（レオン＆カメラ側へ）
LEAO_YAW = 0.0              # +Y 向き（シンへ）
# 手前ロナウド — 奥の2人の方を向く
RONALDO_YAW = math.pi

# 奥：シン＋レオン / 手前：ロナウド
LEAO_POS = Vector((3.0, 4.05, 0.0))
SHIN_START = Vector((3.0, 18.0, 0.0))
SHIN_END = Vector((3.0, 5.25, 0.0))
RONALDO_POS = Vector((1.0, -5.5, 0.0))

# idle 上に掛ける腕のオイラー差分（親ローカル）。両手とも右手で前へ。
# upperarm.r の -X が、対面どちらでも相手方向へ腕が伸びる。
SHIN_OFFER_DELTA = {
    "upperarm.r": (-1.2, 0.0, 0.15),
    "lowerarm.r": (-0.85, 0.1, 0.15),
}
LEAO_REPLY_DELTA = {
    "upperarm.r": (-1.2, 0.0, 0.15),
    "lowerarm.r": (-0.85, 0.1, 0.15),
}

PoseDict = Dict[str, Quaternion]


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    # 無印があれば優先、なければ最も若いサフィックス
    exact = [c for c in candidates if c == name]
    return exact[0] if exact else sorted(candidates)[0]


def _add_nla_strip(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
    action_offset: int = 0,
    repeat: bool = True,
) -> None:
    resolved = _resolve_action_name(action_name)
    _add_nla_strip_raw(arm, resolved, frame_start, frame_end, action_offset=action_offset, repeat=repeat)
    ad = arm.animation_data
    if not ad:
        return
    track = ad.nla_tracks[-1]
    for strip in track.strips:
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
    """シン — 奥でレオンの方へ走る → 到着 → 喜びのホップ"""
    if frame < F_RUN_START:
        return SHIN_START.copy()
    if frame <= F_RUN_END:
        t = (frame - F_RUN_START) / max(1, F_RUN_END - F_RUN_START)
        t = t * t * (3.0 - 2.0 * t)
        return SHIN_START.lerp(SHIN_END, t)
    p = SHIN_END.copy()
    if F_RUN_END < frame <= F_ARRIVE_HOLD:
        hop = (frame - F_RUN_END) / (F_ARRIVE_HOLD - F_RUN_END)
        # 嬉しそうなジャンプ — 高め＋二連跳ね
        p.z = 0.55 * math.sin(hop * math.pi) + 0.18 * math.sin(hop * math.pi * 2.0)
    return p


def _snapshot_pose(arm: bpy.types.Object) -> PoseDict:
    pose: PoseDict = {}
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
        pose[bone.name] = bone.rotation_quaternion.copy()
    return pose


def _pose_with_deltas(base: PoseDict, deltas: Dict[str, Tuple[float, float, float]], weight: float = 1.0) -> PoseDict:
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


def _capture_evaluated_pose(arm: bpy.types.Object, frame: int) -> PoseDict:
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return _snapshot_pose(arm)


def _add_full_pose_replace_strip(
    arm: bpy.types.Object,
    name: str,
    strip_start: int,
    strip_end: int,
    keyed_poses: List[Tuple[int, PoseDict]],
) -> None:
    """全身クォータニオンを REPLACE で重ねる。ADD+Euler は Mannequiny で T-pose 化するので使わない。"""
    if not arm.animation_data:
        arm.animation_data_create()
    ad = arm.animation_data

    # キー投入中は既存 NLA をミュート（スナップショット済みの値だけを焼く）
    muted = [(t, t.mute) for t in ad.nla_tracks]
    for t, _ in muted:
        t.mute = True

    act_name = name
    if bpy.data.actions.get(act_name):
        act_name = f"{name}_{len(bpy.data.actions)}"
    act = bpy.data.actions.new(act_name)
    ad.action = act

    for frame, pose in keyed_poses:
        for bone_name, quat in pose.items():
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


def _animate_handshake_poses(shin_arm: bpy.types.Object, leao_arm: bpy.types.Object) -> None:
    """到着後の idle を土台に、腕だけ伸ばした全身 REPLACE を乗せる。"""
    shin_base = _capture_evaluated_pose(shin_arm, F_ARRIVE_HOLD)
    leao_base = _capture_evaluated_pose(leao_arm, F_OFFER_HOLD)

    shin_keys = [
        (F_ARRIVE_HOLD, shin_base),
        (F_HAND_OFFER - 18, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 0.35)),
        (F_HAND_OFFER, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
        (F_OFFER_HOLD, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
        (HANDSHAKE_FRAMES, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
    ]
    _add_full_pose_replace_strip(
        shin_arm,
        "Shin_ExcitedHandshake",
        F_ARRIVE_HOLD,
        HANDSHAKE_FRAMES,
        shin_keys,
    )

    leao_keys = [
        (F_LEAO_REPLY - 16, leao_base),
        (F_LEAO_REPLY - 4, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 0.45)),
        (F_LEAO_REPLY + 10, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 1.0)),
        (HANDSHAKE_FRAMES, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 1.0)),
    ]
    _add_full_pose_replace_strip(
        leao_arm,
        "Leao_HandshakeReply",
        F_LEAO_REPLY - 16,
        HANDSHAKE_FRAMES,
        leao_keys,
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

    # シン：待機 → 走る → 到着後 idle
    _add_nla_strip(shin_arm, "idle", 1, F_RUN_START - 1)
    _add_nla_strip(shin_arm, "run", F_RUN_START, F_RUN_END)
    _add_nla_strip(shin_arm, "idle", F_RUN_END + 1, HANDSHAKE_FRAMES)

    # レオン・ロナウド：ずっと idle（握手は REPLACE オーバーレイで応答）
    _add_nla_strip(leao_arm, "idle", 1, HANDSHAKE_FRAMES)
    _add_nla_strip(ronaldo_arm, "idle", 1, HANDSHAKE_FRAMES)

    _animate_handshake_poses(shin_arm, leao_arm)

    setup_portugal_handshake_camera()
    scene.frame_set(1)
    print(
        f"Portugal handshake: {HANDSHAKE_FRAMES}f @ {FPS}fps — "
        "Shin run→offer, Leao idle→reply, Ronaldo idle"
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

    bg_target = (SHIN_END + LEAO_POS) * 0.5 + Vector((0.0, 0.0, 2.1))

    key_frames = [
        F_INTRO,
        F_RUN_START,
        F_RUN_END,
        F_HAND_OFFER,
        F_OFFER_HOLD,
        F_LEAO_REPLY,
        HANDSHAKE_FRAMES,
    ]
    for f in key_frames:
        # ロナウド肩越し・やや寄って握手の腕が見える位置
        cam_pos = RONALDO_POS + Vector((2.2, -4.2, 4.2))
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
