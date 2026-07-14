# SPDX-License-Identifier: MIT
"""ポルトガル戦 — シンがレオンに握手を求める（手前ロナウド → 単独ヘディング）

流れ:
  シン: idle → 楽しそうに走っていく → 到着ホップ → 右手を差し出す
  レオン: idle のまま待つ → 左手で握手に応じる
  ロナウド: 握手を見てキレる → カットで一人映し → ヘディング
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

from animate_soccer_match import (
    BALL_GROUND_Z,
    _add_nla_strip as _add_nla_strip_raw,
    _clear_all_nla,
    _clear_anim,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24

# 尺 — 握手＋ロナウド単独ヘディング（約20秒）
HANDSHAKE_FRAMES = 480

# タイムライン
F_INTRO = 1
F_RUN_START = 48
F_RUN_END = 200
F_ARRIVE_HOLD = 236
F_HAND_OFFER = 268
F_OFFER_HOLD = 300
F_LEAO_REPLY = 330
F_HANDSHAKE_HOLD = 360

# ロナウド — 気づき → 単独カットでヘディング
F_RONALDO_NOTICE = F_ARRIVE_HOLD
F_HEADER_SOLO = 372
F_HEADER_PREP = 392
F_HEADER_TAKEOFF = 408
F_HEADER_CONTACT = 422
F_HEADER_LAND = 448
RONALDO_HEADER_HEIGHT = 2.15

SHIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

# 左右に対面（カメラから両方見える）。シンは +X から走ってくる。
SHIN_YAW = math.pi * 1.5  # -X 向き（レオンへ）
LEAO_YAW = math.pi / 2    # +X 向き（シンへ）
# 握手フェーズ：奥を向く / ヘディング：横顔が見える向き
RONALDO_WATCH_YAW = math.pi
RONALDO_HEADER_YAW = math.pi / 2

# 奥：シン＋レオン / 手前：ロナウド
LEAO_POS = Vector((1.85, 5.0, 0.0))
SHIN_START = Vector((18.0, 5.0, 0.0))
SHIN_END = Vector((4.55, 5.0, 0.0))
RONALDO_POS = Vector((1.0, -5.5, 0.0))
# スケール×2.5時の頭高さを基準（ジャンプ頂点の頭部 ≈ z 5.7）
HEADER_BALL_START = RONALDO_POS + Vector((6.5, 0.2, 5.5))
HEADER_BALL_CONTACT = RONALDO_POS + Vector((0.45, 0.03, 5.9))
HEADER_BALL_END = RONALDO_POS + Vector((-3.8, -0.8, 7.2))


def _finger_handshake_deltas(side: str) -> Dict[str, Tuple[float, float, float]]:
    """握手：掌を開きつつ、指先は軽く相手の手に巻きつける。"""
    s = side
    d: Dict[str, Tuple[float, float, float]] = {}
    for finger in ("index", "middle", "ring"):
        # 付け根はやや開く、中〜先は握る
        d[f"{finger}_01.{s}"] = (-0.25, 0.0, 0.0)
        d[f"{finger}_02.{s}"] = (0.45, 0.0, 0.0)
        d[f"{finger}_03.{s}"] = (0.5, 0.0, 0.0)
    if s == "r":
        d["thumb_01.r"] = (0.15, 0.6, 0.4)
        d["thumb_02.r"] = (0.35, 0.1, 0.0)
        d["thumb_03.r"] = (0.25, 0.0, 0.0)
    else:
        d["thumb_01.l"] = (0.15, -0.6, -0.4)
        d["thumb_02.l"] = (0.35, -0.1, 0.0)
        d["thumb_03.l"] = (0.25, 0.0, 0.0)
    return d


# idle 上に掛ける腕＋手のオイラー差分。シン右手・レオン左手。
SHIN_OFFER_DELTA = {
    "upperarm.r": (0.95, 0.5, 1.2),
    "lowerarm.r": (-0.95, 0.15, 0.1),
    "hand.r": (0.2, 0.3, -1.0),
    "spine_02": (0.08, 0.0, 0.04),
    "neck_01": (0.04, 0.0, -0.05),
    **_finger_handshake_deltas("r"),
}
LEAO_REPLY_DELTA = {
    "upperarm.l": (0.95, -0.5, -1.2),
    "lowerarm.l": (-0.95, -0.15, -0.1),
    "hand.l": (0.2, -0.3, 1.0),
    "spine_02": (0.08, 0.0, -0.04),
    "neck_01": (0.04, 0.0, 0.05),
    **_finger_handshake_deltas("l"),
}

# ヘディング — 溜めは後ろへ、着弾で頭をボールへ振り出す
RONALDO_HEADER_WINDUP = {
    "spine_02": (0.45, 0.0, 0.0),
    "neck_01": (-0.2, 0.0, 0.0),
    "head": (-0.1, 0.0, 0.0),
    "upperarm.r": (0.15, -0.9, 0.35),
    "lowerarm.r": (-0.7, 0.1, 0.0),
    "upperarm.l": (0.15, 0.9, -0.35),
    "lowerarm.l": (-0.7, -0.1, 0.0),
}
RONALDO_HEADER_CONTACT = {
    "spine_02": (-0.7, 0.0, 0.05),
    "neck_01": (-0.9, 0.0, 0.0),
    "head": (-0.55, 0.0, 0.0),
    "upperarm.r": (-0.25, -1.15, 0.55),
    "lowerarm.r": (-0.95, 0.2, 0.1),
    "upperarm.l": (-0.25, 1.15, -0.55),
    "lowerarm.l": (-0.95, -0.2, -0.1),
}
RONALDO_HEADER_FOLLOW = {
    "spine_02": (-0.35, 0.0, 0.0),
    "neck_01": (-0.4, 0.0, 0.0),
    "head": (-0.2, 0.0, 0.0),
    "upperarm.r": (0.1, -0.7, 0.25),
    "lowerarm.r": (-0.5, 0.0, 0.0),
    "upperarm.l": (0.1, 0.7, -0.25),
    "lowerarm.l": (-0.5, 0.0, 0.0),
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


def _animate_root_keys(
    root: bpy.types.Object,
    keys: List[Tuple[int, Vector, float]],
) -> None:
    """位置＋Yawをキーする（ヘディングで向きを変える用）。"""
    _clear_anim(root)
    for f, loc, yaw in keys:
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
        p.z = 0.55 * math.sin(hop * math.pi) + 0.18 * math.sin(hop * math.pi * 2.0)
    return p


def _ronaldo_path(frame: int) -> Tuple[Vector, float]:
    """ロナウド — 握手を見たあと単独で跳びヘディング。"""
    p = RONALDO_POS.copy()
    yaw = RONALDO_WATCH_YAW

    if frame < F_HEADER_SOLO:
        if frame >= F_RONALDO_NOTICE:
            t = frame - F_RONALDO_NOTICE
            p.z = 0.1 * abs(math.sin(t * 0.45))
            p.x += 0.05 * math.sin(t * 0.3)
        return p, yaw

    yaw = RONALDO_HEADER_YAW
    if frame < F_HEADER_PREP:
        # 向き変え・構える
        t = (frame - F_HEADER_SOLO) / max(1, F_HEADER_PREP - F_HEADER_SOLO)
        p.z = 0.08 * t
        return p, yaw

    if frame < F_HEADER_TAKEOFF:
        # 溜め：少し沈み込み
        t = (frame - F_HEADER_PREP) / max(1, F_HEADER_TAKEOFF - F_HEADER_PREP)
        p.z = 0.08 - 0.22 * t
        return p, yaw

    if frame <= F_HEADER_CONTACT:
        t = (frame - F_HEADER_TAKEOFF) / max(1, F_HEADER_CONTACT - F_HEADER_TAKEOFF)
        ease = math.sin(t * math.pi * 0.5)
        p.z = -0.14 + (RONALDO_HEADER_HEIGHT + 0.14) * ease
        p.x += 0.35 * t
        return p, yaw

    if frame <= F_HEADER_LAND:
        t = (frame - F_HEADER_CONTACT) / max(1, F_HEADER_LAND - F_HEADER_CONTACT)
        p.z = RONALDO_HEADER_HEIGHT * max(0.0, math.cos(t * math.pi * 0.5))
        p.x += 0.35 + 0.25 * t
        return p, yaw

    # 着地後少し余韻
    p.x += 0.6
    return p, yaw


def _header_ball_path(frame: int) -> Vector:
    if frame < F_HEADER_SOLO:
        return HEADER_BALL_START.copy()
    if frame < F_HEADER_CONTACT:
        t = (frame - F_HEADER_SOLO) / max(1, F_HEADER_CONTACT - F_HEADER_SOLO)
        t = t * t * (3.0 - 2.0 * t)
        return HEADER_BALL_START.lerp(HEADER_BALL_CONTACT, t)
    t = (frame - F_HEADER_CONTACT) / max(1, HANDSHAKE_FRAMES - F_HEADER_CONTACT)
    t = min(1.0, t)
    # 当たって吹き飛ぶ
    ease = 1.0 - (1.0 - t) ** 2
    p = HEADER_BALL_CONTACT.lerp(HEADER_BALL_END, ease)
    p.z += 0.9 * math.sin(min(1.0, t * 1.35) * math.pi)
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


def _add_bone_pose_replace_strip(
    arm: bpy.types.Object,
    name: str,
    strip_start: int,
    strip_end: int,
    keyed_poses: List[Tuple[int, PoseDict]],
    bone_filter: List[str] | None = None,
) -> None:
    """指定ボーンのクォータニオンだけを REPLACE で重ねる（脚の idle は下のトラックが生きる）。"""
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


SHIN_HANDSHAKE_BONES = [
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "hand.r",
    "thumb_01.r",
    "thumb_02.r",
    "thumb_03.r",
    "index_01.r",
    "index_02.r",
    "index_03.r",
    "middle_01.r",
    "middle_02.r",
    "middle_03.r",
    "ring_01.r",
    "ring_02.r",
    "ring_03.r",
    "spine_02",
    "neck_01",
    "head",
]
LEAO_HANDSHAKE_BONES = [
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "hand.l",
    "thumb_01.l",
    "thumb_02.l",
    "thumb_03.l",
    "index_01.l",
    "index_02.l",
    "index_03.l",
    "middle_01.l",
    "middle_02.l",
    "middle_03.l",
    "ring_01.l",
    "ring_02.l",
    "ring_03.l",
    "spine_02",
    "neck_01",
    "head",
]

RONALDO_HEADER_BONES = [
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "hand.r",
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "hand.l",
    "spine_02",
    "neck_01",
    "head",
]


def _animate_handshake_poses(shin_arm: bpy.types.Object, leao_arm: bpy.types.Object) -> None:
    """到着後の idle を土台に、腕まわりだけ REPLACE で伸ばす。"""
    shin_base = _capture_evaluated_pose(shin_arm, F_ARRIVE_HOLD)
    leao_base = _capture_evaluated_pose(leao_arm, F_OFFER_HOLD)

    shin_keys = [
        (F_ARRIVE_HOLD, shin_base),
        (F_HAND_OFFER - 18, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 0.35)),
        (F_HAND_OFFER, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
        (F_OFFER_HOLD, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
        (HANDSHAKE_FRAMES, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
    ]
    _add_bone_pose_replace_strip(
        shin_arm,
        "Shin_ExcitedHandshake",
        F_ARRIVE_HOLD,
        HANDSHAKE_FRAMES,
        shin_keys,
        SHIN_HANDSHAKE_BONES,
    )

    leao_keys = [
        (F_LEAO_REPLY - 16, leao_base),
        (F_LEAO_REPLY - 4, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 0.45)),
        (F_LEAO_REPLY + 10, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 1.0)),
        (HANDSHAKE_FRAMES, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 1.0)),
    ]
    _add_bone_pose_replace_strip(
        leao_arm,
        "Leao_HandshakeReply",
        F_LEAO_REPLY - 16,
        HANDSHAKE_FRAMES,
        leao_keys,
        LEAO_HANDSHAKE_BONES,
    )


def _animate_ronaldo_header(ronaldo_arm: bpy.types.Object) -> None:
    """単独ヘディングの溜め→ヒット→フォロー。idle 基準で焼く。"""
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

    wind = _pose_with_deltas(idle_base, RONALDO_HEADER_WINDUP, 1.0)
    hit = _pose_with_deltas(idle_base, RONALDO_HEADER_CONTACT, 1.0)
    follow = _pose_with_deltas(idle_base, RONALDO_HEADER_FOLLOW, 1.0)

    keys = [
        (F_HEADER_SOLO, idle_base),
        (F_HEADER_PREP, wind),
        (F_HEADER_TAKEOFF, wind),
        (F_HEADER_CONTACT - 2, _pose_with_deltas(idle_base, RONALDO_HEADER_CONTACT, 0.55)),
        (F_HEADER_CONTACT, hit),
        (F_HEADER_CONTACT + 8, hit),
        (F_HEADER_LAND, follow),
        (HANDSHAKE_FRAMES, follow),
    ]
    _add_bone_pose_replace_strip(
        ronaldo_arm,
        "Ronaldo_Header",
        F_HEADER_SOLO,
        HANDSHAKE_FRAMES,
        keys,
        RONALDO_HEADER_BONES,
    )


def _set_hide_keyed(obj: bpy.types.Object, frame: int, hide: bool) -> None:
    obj.hide_render = hide
    obj.hide_viewport = hide
    obj.keyframe_insert(data_path="hide_render", frame=frame)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)


def _solo_hide_other_players(shin_arm: bpy.types.Object, leao_arm: bpy.types.Object) -> None:
    """ヘディング単独カット以降、シン/レオンを映さない。"""
    from import_mannequiny import _mesh_child  # noqa: E402

    objs = [
        shin_arm,
        leao_arm,
        _mesh_child(shin_arm),
        _mesh_child(leao_arm),
        bpy.data.objects.get("Shin_01_Root"),
        bpy.data.objects.get("Leao_01_Root"),
    ]
    for obj in objs:
        if not obj:
            continue
        _set_hide_keyed(obj, F_HEADER_SOLO - 1, False)
        _set_hide_keyed(obj, F_HEADER_SOLO, True)
        _set_hide_keyed(obj, HANDSHAKE_FRAMES, True)


def _animate_header_ball(ball: bpy.types.Object) -> None:
    _clear_anim(ball)
    ball.hide_render = True
    ball.hide_viewport = True
    ball.keyframe_insert(data_path="hide_render", frame=1)
    ball.keyframe_insert(data_path="hide_viewport", frame=1)

    ball.hide_render = False
    ball.hide_viewport = False
    ball.keyframe_insert(data_path="hide_render", frame=F_HEADER_SOLO)
    ball.keyframe_insert(data_path="hide_viewport", frame=F_HEADER_SOLO)

    for f in range(F_HEADER_SOLO, HANDSHAKE_FRAMES + 1):
        _kf_loc(ball, f, _header_ball_path(f))
    if ball.animation_data and ball.animation_data.action:
        for fc in ball.animation_data.action.fcurves:
            if not fc.data_path.startswith("location"):
                continue
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"



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
        facing_yaw=RONALDO_WATCH_YAW,
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

    shin_keys = [(f, _shin_path(f)) for f in range(1, HANDSHAKE_FRAMES + 1)]
    leao_keys = [(f, LEAO_POS) for f in range(1, HANDSHAKE_FRAMES + 1)]
    ronaldo_pose_keys = [(f, *_ronaldo_path(f)) for f in range(1, HANDSHAKE_FRAMES + 1)]

    _animate_root_fixed(shin_root, shin_keys, SHIN_YAW)
    _animate_root_fixed(leao_root, leao_keys, LEAO_YAW)
    _animate_root_keys(ronaldo_root, ronaldo_pose_keys)

    # シン：待機 → 走る → 到着後 idle
    _add_nla_strip(shin_arm, "idle", 1, F_RUN_START - 1)
    _add_nla_strip(shin_arm, "run", F_RUN_START, F_RUN_END)
    _add_nla_strip(shin_arm, "idle", F_RUN_END + 1, HANDSHAKE_FRAMES)

    # レオン：ずっと idle
    _add_nla_strip(leao_arm, "idle", 1, HANDSHAKE_FRAMES)

    # ロナウド：idle → 気づき → ヘディングはルート＋ポーズ
    _add_nla_strip(ronaldo_arm, "idle", 1, F_HEADER_SOLO - 1)
    try:
        _add_nla_strip(ronaldo_arm, "air_jump", F_HEADER_TAKEOFF, F_HEADER_LAND)
    except KeyError:
        _add_nla_strip(ronaldo_arm, "idle", F_HEADER_TAKEOFF, F_HEADER_LAND)
    _add_nla_strip(ronaldo_arm, "idle", F_HEADER_LAND + 1, HANDSHAKE_FRAMES)

    _animate_handshake_poses(shin_arm, leao_arm)
    _animate_ronaldo_header(ronaldo_arm)
    _solo_hide_other_players(shin_arm, leao_arm)

    if ball:
        _animate_header_ball(ball)
    else:
        print("WARN: Ball not found — header without ball")

    setup_portugal_handshake_camera()
    scene.frame_set(1)
    print(
        f"Portugal handshake: {HANDSHAKE_FRAMES}f @ {FPS}fps — "
        "Shin-Leao handshake, then solo Ronaldo header"
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
    """前半はロナウド肩越し握手、後半はロナウド単独ヘディング。"""
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamPortugalHandshake")
    cam = bpy.data.objects.new("CamPortugalHandshake", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    bg_target = (SHIN_END + LEAO_POS) * 0.5 + Vector((0.0, 0.0, 2.1))
    over_shoulder = RONALDO_POS + Vector((2.2, -4.2, 4.2))

    # 前半：握手ワイド
    for f in (F_INTRO, F_RUN_START, F_RUN_END, F_HAND_OFFER, F_LEAO_REPLY, F_HEADER_SOLO - 1):
        cam.data.lens = 20
        cam.data.keyframe_insert(data_path="lens", frame=f)
        _kf_cam(cam, f, over_shoulder, bg_target)

    # 後半：ロナウド一人・横から。頭＋ボールが切れない高さで追う
    for f in (F_HEADER_SOLO, F_HEADER_PREP, F_HEADER_TAKEOFF, F_HEADER_CONTACT, F_HEADER_LAND, HANDSHAKE_FRAMES):
        cam.data.lens = 28
        cam.data.keyframe_insert(data_path="lens", frame=f)
        loc, _yaw = _ronaldo_path(f)
        head_z = 3.9 + max(0.0, loc.z)
        tgt = Vector((loc.x + 0.35, loc.y, head_z * 0.9))
        pos = Vector((loc.x + 4.5, loc.y - 6.4, 3.4 + max(0.0, loc.z) * 0.55))
        _kf_cam(cam, f, pos, tgt)

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
