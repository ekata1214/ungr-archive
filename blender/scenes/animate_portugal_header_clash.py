# SPDX-License-Identifier: MIT
"""ポルトガル戦 — ロナウド vs 少林の空中ヘディング衝突（スロー）

別カット。両者ともヘディング姿勢で跳び、頂点で頭がぶつかる。
NLA は repeat なし（引き延ばし1回）でカクつき防止。
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
CLASH_FRAMES = 300  # 約12.5秒スロー

F_CROUCH = 40
F_TAKEOFF = 84
F_CLASH = 168
F_SEPARATE = 198
F_LAND = 250
F_SETTLE = 280

JUMP_HEIGHT = 2.55
# 互いに対面（ロナウド:+X / 少林:-X）
RONALDO_YAW = math.pi / 2
SHAOLIN_YAW = math.pi * 1.5
# 体が重ならないようスタート／合流を広く。頭は前傾で寄せる
# サイドカメラなので Y=0 のまま。ルート間隔〜2.7 + 前傾で頭が中央接触
RONALDO_START = Vector((-4.4, 0.0, 0.0))
SHAOLIN_START = Vector((4.4, 0.0, 0.0))
RONALDO_CLASH_X = -1.85
SHAOLIN_CLASH_X = 1.85
RONALDO_Y = 0.0
SHAOLIN_Y = 0.0
MIN_ROOT_SEPARATION = 3.5
# 頭ボーン中心の接触間隔（メッシュ半径ぶん空ける＝見た目で軽く当たる）
HEAD_CLASH_GAP = 0.88
# ボールは頭より上
BALL_ABOVE_HEAD = 1.7

PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)
SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)

# ヘディング：正の spine/neck で相手方向へ前傾。
# 腕: Rx+ で上げ、Ry は外側（右:+ / 左:-）。逆にするとクロスする
_ARMS_RAISE = {
    "upperarm.r": (1.0, 0.85, -0.1),
    "lowerarm.r": (-0.55, 0.0, 0.0),
    "upperarm.l": (1.0, -0.85, 0.1),
    "lowerarm.l": (-0.55, 0.0, 0.0),
}
HEADER_WINDUP_R = {
    "spine_02": (0.55, 0.0, 0.0),
    "neck_01": (0.35, 0.0, 0.0),
    "head": (0.18, 0.0, 0.0),
    **{k: (v[0] * 0.55, v[1] * 0.55, v[2] * 0.55) for k, v in _ARMS_RAISE.items()},
}
HEADER_CLASH_R = {
    "spine_02": (1.05, 0.0, 0.0),
    "neck_01": (0.85, 0.0, 0.0),
    "head": (0.5, 0.0, 0.0),
    **_ARMS_RAISE,
}
HEADER_WINDUP_L = dict(HEADER_WINDUP_R)
HEADER_CLASH_L = dict(HEADER_CLASH_R)

HEADER_BONES = [
    "upperarm.r",
    "lowerarm.r",
    "upperarm.l",
    "lowerarm.l",
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


def _jump_z(frame: int) -> float:
    if frame <= F_CROUCH:
        t = (frame - 1) / max(1, F_CROUCH - 1)
        return -0.2 * _ease_in_out(t)
    if frame <= F_TAKEOFF:
        t = (frame - F_CROUCH) / max(1, F_TAKEOFF - F_CROUCH)
        return -0.2 - 0.14 * _ease_in_out(t)
    if frame <= F_CLASH:
        t = (frame - F_TAKEOFF) / max(1, F_CLASH - F_TAKEOFF)
        return -0.34 + (JUMP_HEIGHT + 0.34) * math.sin(_ease_in_out(t) * math.pi * 0.5)
    if frame <= F_LAND:
        t = (frame - F_CLASH) / max(1, F_LAND - F_CLASH)
        return JUMP_HEIGHT * (1.0 - _ease_in_out(t))
    if frame <= F_SETTLE:
        t = (frame - F_LAND) / max(1, F_SETTLE - F_LAND)
        return -0.1 * math.sin(_ease_in_out(t) * math.pi)
    return 0.0


def _approach_x(frame: int, start_x: float, clash_x: float) -> float:
    """start → 衝突ルート位置 → 跳ね返り（胴体クリアランスを保つ）。"""
    travel = clash_x - start_x
    if frame <= F_TAKEOFF:
        t = (frame - 1) / max(1, F_TAKEOFF - 1)
        return start_x + travel * 0.1 * _ease_in_out(t)
    if frame <= F_CLASH:
        t = (frame - F_TAKEOFF) / max(1, F_CLASH - F_TAKEOFF)
        return start_x + travel * (0.1 + 0.9 * _ease_in_out(t))
    if frame <= F_SEPARATE:
        t = (frame - F_CLASH) / max(1, F_SEPARATE - F_CLASH)
        # 頭突きで外側へ跳ね返る
        return clash_x - travel * 0.18 * _ease_in_out(t)
    if frame <= F_LAND:
        t = (frame - F_SEPARATE) / max(1, F_LAND - F_SEPARATE)
        mid = clash_x - travel * 0.18
        return mid - travel * 0.08 * _ease_in_out(t)
    return clash_x - travel * 0.26


def _ronaldo_path(frame: int) -> Vector:
    x = _approach_x(frame, RONALDO_START.x, RONALDO_CLASH_X)
    return Vector((x, RONALDO_Y, _jump_z(frame)))


def _shaolin_path(frame: int) -> Vector:
    x = _approach_x(frame, SHAOLIN_START.x, SHAOLIN_CLASH_X)
    return Vector((x, SHAOLIN_Y, _jump_z(frame)))


def _head_world(arm: bpy.types.Object) -> Vector:
    head = arm.pose.bones.get("head")
    if not head:
        return arm.matrix_world.translation + Vector((0.0, 0.0, 4.5))
    return (arm.matrix_world @ head.matrix).to_translation()


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


def _idle_base(arm: bpy.types.Object) -> PoseDict:
    ad = arm.animation_data
    if not ad:
        arm.animation_data_create()
        ad = arm.animation_data
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


def _animate_header_pose(arm: bpy.types.Object, side: str) -> None:
    base = _idle_base(arm)
    wind = HEADER_WINDUP_R if side == "r" else HEADER_WINDUP_L
    clash = HEADER_CLASH_R if side == "r" else HEADER_CLASH_L
    wind_pose = _pose_with_deltas(base, wind, 1.0)
    clash_pose = _pose_with_deltas(base, clash, 1.0)
    follow = _pose_with_deltas(base, clash, 0.35)
    keys = [
        (1, base),
        (F_CROUCH, base),
        (F_TAKEOFF, wind_pose),
        (F_CLASH - 20, _pose_with_deltas(base, clash, 0.45)),
        (F_CLASH, clash_pose),
        (F_SEPARATE, clash_pose),
        (F_LAND, follow),
        (CLASH_FRAMES, base),
    ]
    _add_bone_pose_replace_strip(
        arm,
        f"HeaderClash_{side}",
        1,
        CLASH_FRAMES,
        keys,
        HEADER_BONES,
    )


def _animate_root_sparse(
    root: bpy.types.Object, path_fn, frames: List[int], yaw: float
) -> None:
    _clear_anim(root)
    for f in frames:
        _kf_loc(root, f, path_fn(f))
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _apply_nla_jump(arm: bpy.types.Object) -> None:
    # 空中で air_jump を入れると脚が中央に繰り出して相手に刺さるので、
    # ジャンプはルート移動のみ。姿勢は idle ホールド＋ヘディング前傾。
    _add_nla_hold_pose(arm, "idle", 1, CLASH_FRAMES)


def _hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if not ball:
        return
    if ball.animation_data:
        ball.animation_data_clear()
    # 衝突点の少し手前にボールを置き、空中デュエルの理由にする
    ball.hide_render = False
    ball.hide_viewport = False


def _animate_ball_above_heads(
    ball: bpy.types.Object,
    ron_arm: bpy.types.Object,
    shin_arm: bpy.types.Object,
) -> None:
    """ボールは常に二人の頭より上。衝突点の直上で少し跳ねる。"""
    _clear_anim(ball)
    ball.hide_render = False
    ball.hide_viewport = False

    # 頭高さをサンプリングしてボール軌道を決める
    head_z_peak = 0.0
    for f in range(F_TAKEOFF, F_SEPARATE + 1, 4):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        head_z_peak = max(head_z_peak, _head_world(ron_arm).z, _head_world(shin_arm).z)

    bpy.context.scene.frame_set(F_CLASH)
    bpy.context.view_layer.update()
    rh = _head_world(ron_arm)
    sh = _head_world(shin_arm)
    mid_x = 0.5 * (rh.x + sh.x)
    mid_y = 0.5 * (rh.y + sh.y)
    clash_ball = Vector((mid_x, mid_y, max(rh.z, sh.z) + BALL_ABOVE_HEAD))
    start = Vector((mid_x, mid_y + 0.1, clash_ball.z + 1.2))
    end = Vector((mid_x + 0.2, mid_y - 0.4, clash_ball.z + 1.5))

    for f, loc in (
        (1, start + Vector((0.0, 0.0, 0.6))),
        (F_TAKEOFF, start),
        (F_CLASH, clash_ball),
        (F_SEPARATE, clash_ball + Vector((0.1, -0.25, 0.7))),
        (F_LAND, end),
        (CLASH_FRAMES, end + Vector((0.25, -0.2, 0.3))),
    ):
        _kf_loc(ball, f, loc)
    if ball.animation_data and ball.animation_data.action:
        for fc in ball.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _nudge_roots_for_head_clash(
    ron_arm: bpy.types.Object,
    shin_arm: bpy.types.Object,
    ron_root: bpy.types.Object,
    shin_root: bpy.types.Object,
) -> None:
    """衝突フレームで頭間距離を合わせてルートを微調整（X）。Y ずらしで胴体は交わらない。"""
    scene = bpy.context.scene
    scene.frame_set(F_CLASH)
    bpy.context.view_layer.update()
    rh = _head_world(ron_arm)
    sh = _head_world(shin_arm)
    # XY 平面での頭間
    delta_xy = Vector((sh.x - rh.x, sh.y - rh.y, 0.0))
    dist = delta_xy.length
    desired = HEAD_CLASH_GAP
    if dist < 1e-4:
        return
    # X 方向に寄せる／離す（Y はキープ）
    # 目標: XY距離 ≈ desired。まず X 補正に換算
    corr = 0.5 * (desired - (sh.x - rh.x))

    scene.frame_set(F_CLASH)
    bpy.context.view_layer.update()
    root_gap = shin_root.location.x - ron_root.location.x
    if corr < 0:
        max_close = 0.5 * max(0.0, root_gap - MIN_ROOT_SEPARATION)
        corr = max(corr, -max_close)

    def _patch_x(root: bpy.types.Object, dx: float) -> None:
        ad = root.animation_data
        if not ad or not ad.action:
            return
        for fc in ad.action.fcurves:
            if fc.data_path != "location" or fc.array_index != 0:
                continue
            for kp in fc.keyframe_points:
                if F_TAKEOFF <= kp.co.x <= F_SEPARATE:
                    if kp.co.x <= F_CLASH:
                        w = (kp.co.x - F_TAKEOFF) / max(1, F_CLASH - F_TAKEOFF)
                    else:
                        w = 1.0 - (kp.co.x - F_CLASH) / max(1, F_SEPARATE - F_CLASH)
                    w = max(0.0, min(1.0, w))
                    kp.co.y += dx * w
                    kp.handle_left.y += dx * w
                    kp.handle_right.y += dx * w

    _patch_x(ron_root, -corr)
    _patch_x(shin_root, corr)

    scene.frame_set(F_CLASH)
    bpy.context.view_layer.update()
    rh2 = _head_world(ron_arm)
    sh2 = _head_world(shin_arm)
    d2 = (Vector((sh2.x - rh2.x, sh2.y - rh2.y, 0.0))).length
    overlap = _torso_overlap_amount(ron_arm, shin_arm)
    print(
        f"Head clash: xy_before={dist:.3f} xy_after={d2:.3f} "
        f"heads=({rh2.x:.2f},{rh2.y:.2f})/({sh2.x:.2f},{sh2.y:.2f}) z={rh2.z:.2f} "
        f"torso_overlap={overlap:.3f}"
    )


def _torso_overlap_amount(ron_arm: bpy.types.Object, shin_arm: bpy.types.Object) -> float:
    """胸付近（腕を除外した胴幹）メッシュの X 重なり。0＝非接触。"""
    from import_mannequiny import _mesh_child  # noqa: E402

    def _chest_span(arm: bpy.types.Object) -> Tuple[float, float]:
        mesh = _mesh_child(arm)
        head = _head_world(arm)
        root = arm.matrix_world.translation
        deps = bpy.context.evaluated_depsgraph_get()
        me = mesh.evaluated_get(deps).to_mesh()
        mm = mesh.matrix_world
        xs = []
        for v in me.vertices:
            w = mm @ v.co
            # 頭〜腰の間、かつ体幹付近（左右に張り出した腕を除外）
            if not (head.z - 2.4 < w.z < head.z - 0.55):
                continue
            if abs(w.y - root.y) > 0.55:
                continue
            xs.append(w.x)
        mesh.to_mesh_clear()
        if not xs:
            return (root.x - 0.7, root.x + 0.7)
        return (min(xs), max(xs))

    r0, r1 = _chest_span(ron_arm)
    s0, s1 = _chest_span(shin_arm)
    return max(0.0, min(r1, s1) - max(r0, s0))


def setup_characters() -> Tuple[
    bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object
]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    ron = build_team(
        "Ronaldo",
        PORTUGAL_RED,
        [RONALDO_START],
        actions=["idle"],
        facing_yaw=RONALDO_YAW,
    )[0]
    shin = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [SHAOLIN_START],
        actions=["idle"],
        facing_yaw=SHAOLIN_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(ron), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    return ron, shin, _root_of(ron), _root_of(shin)


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
    cam_data = bpy.data.cameras.new("CamHeaderClash")
    cam = bpy.data.objects.new("CamHeaderClash", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 28

    for f in (1, F_CROUCH, F_TAKEOFF, F_CLASH, F_SEPARATE, F_LAND, CLASH_FRAMES):
        rz = _ronaldo_path(f)
        sz = _shaolin_path(f)
        mid = (rz + sz) * 0.5
        peak = max(0.0, mid.z)
        tgt = Vector((mid.x, mid.y, 4.0 + peak * 0.7))
        pos = Vector((mid.x + 0.4, mid.y - 10.5, 3.4 + peak * 0.45))
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


def animate_portugal_header_clash() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = CLASH_FRAMES
    scene.render.fps = FPS

    ron_arm, shin_arm, ron_root, shin_root = setup_characters()
    _clear_all_nla(ron_arm)
    _clear_all_nla(shin_arm)

    sparse = sorted(
        {
            1,
            F_CROUCH,
            F_TAKEOFF,
            F_TAKEOFF + 20,
            (F_TAKEOFF + F_CLASH) // 2,
            F_CLASH - 8,
            F_CLASH,
            F_CLASH + 8,
            F_SEPARATE,
            (F_SEPARATE + F_LAND) // 2,
            F_LAND,
            F_SETTLE,
            CLASH_FRAMES,
        }
    )
    _animate_root_sparse(ron_root, _ronaldo_path, sparse, RONALDO_YAW)
    _animate_root_sparse(shin_root, _shaolin_path, sparse, SHAOLIN_YAW)

    _apply_nla_jump(ron_arm)
    _apply_nla_jump(shin_arm)
    _animate_header_pose(ron_arm, "r")
    _animate_header_pose(shin_arm, "l")

    ball = bpy.data.objects.get("Ball")
    # ポーズ＋頭寄せ後に、頭上のボール軌道を焼く
    _nudge_roots_for_head_clash(ron_arm, shin_arm, ron_root, shin_root)
    if ball:
        _animate_ball_above_heads(ball, ron_arm, shin_arm)
    else:
        _hide_ball()

    setup_camera()
    scene.frame_set(1)
    print(f"Portugal header clash: {CLASH_FRAMES}f @ {FPS}fps slow-mo — dual aerial headers")


def render_portugal_header_clash_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = CLASH_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    out = RENDER_DIR / "portugal_header_clash.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering portugal header clash: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path, save_blend

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-portugal-header-clash-video" in sys.argv:
        render_portugal_header_clash_video()
    else:
        animate_portugal_header_clash()
        save_blend(blend)
