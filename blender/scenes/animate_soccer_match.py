# SPDX-License-Identifier: MIT
"""500f サッカー試合 — パス・守備・シュート・ゴール（同期・イージング改善版）"""

from __future__ import annotations

import math
from typing import List, Tuple

import bpy
from mathutils import Euler, Vector

MATCH_FRAMES = 500
FPS = 24

_SCALE = 2.5
PITCH_HALF = 105.0 * _SCALE / 2
BALL_R = 0.22 * _SCALE
BALL_GROUND_Z = BALL_R

# fight_kick 内で足がボールに当たるおおよそのフレーム（アクション先頭=0）
KICK_CONTACT_FRAME = 20
# キックオフ（試合開始）— センターで足タッチ→短パス
PASS1_START = 12
PASS1_RELEASE = PASS1_START + KICK_CONTACT_FRAME
PASS1_RECEIVE = 52
PASS2_START = 248
PASS2_RELEASE = 254
PASS2_RECEIVE = 270
KICK_STRIP_START = 288
KICK_BALL_RELEASE = KICK_STRIP_START + KICK_CONTACT_FRAME
SHOT_LAND = 395


def _root_of(arm: bpy.types.Object) -> bpy.types.Object:
    if arm.parent:
        return arm.parent
    raise ValueError(f"No root parent for {arm.name}")


def _clear_anim(obj: bpy.types.Object) -> None:
    if obj.animation_data:
        obj.animation_data_clear()
    obj.animation_data_create()


def _apply_bezier_ease(obj: bpy.types.Object, path: str = "location") -> None:
    if not obj.animation_data or not obj.animation_data.action:
        ad = obj.animation_data
        if not ad:
            return
    action = obj.animation_data.action
    if not action:
        # NLA only objects: fcurves on action from keyframes might be on object
        if not obj.animation_data:
            return
    for fc in obj.animation_data.action.fcurves if obj.animation_data.action else []:
        if fc.data_path != path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"

    # Object-level FCurves (keyframes without action)
    if obj.animation_data and obj.animation_data.action is None:
        pass
    # Blender stores keyframes on action created implicitly
    if obj.animation_data:
        action = obj.animation_data.action
        if action:
            for fc in action.fcurves:
                if not fc.data_path.startswith(path.split("[")[0]):
                    continue
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.handle_left_type = "AUTO_CLAMPED"
                    kp.handle_right_type = "AUTO_CLAMPED"


def _ease_all_ball_keyframes(ball: bpy.types.Object) -> None:
    if ball.animation_data and ball.animation_data.action:
        for fc in ball.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _kf_loc(obj: bpy.types.Object, frame: int, loc: Vector) -> None:
    obj.location = loc
    obj.keyframe_insert(data_path="location", frame=frame)


def _kf_rot_z(obj: bpy.types.Object, frame: int, yaw: float) -> None:
    obj.rotation_euler = Euler((0, 0, yaw))
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def _lerp(a: Vector, b: Vector, t: float) -> Vector:
    return a + (b - a) * t


BALL_DRIBBLE_AHEAD = 1.15  # ドリブル時: 体の前方（ワールド単位）
BALL_DRIBBLE_SIDE = 0.10   # ドリブル時: 左右の微揺れ幅
BALL_FEET_CLEARANCE = 0.55  # 両足の最前点より前に出す量（トゥより前）


def _forward_from_yaw(yaw: float) -> Vector:
    return Vector((-math.sin(yaw), math.cos(yaw), 0.0))


def _arm_of_root(root: bpy.types.Object) -> bpy.types.Object | None:
    for ch in root.children:
        if ch.type == "ARMATURE":
            return ch
    return None


def _ball_at_player(root_pos: Vector, yaw: float, ahead: float = 0.55, side: float = 0.0) -> Vector:
    fwd = _forward_from_yaw(yaw)
    right = Vector((fwd.y, -fwd.x, 0.0))
    p = root_pos + fwd * ahead + right * side
    p.z = BALL_GROUND_Z
    return p


def _root_world_at(root: bpy.types.Object, frame: int) -> Vector:
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    return root.matrix_world.translation.copy()


def _dribble_dir(root: bpy.types.Object, yaw: float, frame: int) -> Vector:
    """移動方向（速度）を優先。停止中は yaw から算出。"""
    scene = bpy.context.scene
    f0 = max(scene.frame_start, frame - 1)
    p0 = _root_world_at(root, f0)
    p1 = _root_world_at(root, frame)
    v = (p1 - p0)
    v.z = 0.0
    if v.length > 1e-4:
        return v.normalized()
    return _forward_from_yaw(yaw)


def _ball_at_dribble_frame(
    root: bpy.types.Object,
    arm: bpy.types.Object | None,
    yaw: float,
    frame: int,
    phase: float = 0.0,
    preferred_dir: Vector | None = None,
) -> Vector:
    """ドリブル — **両足の最前点より常に前** に置く（右足でも左足でも前）"""
    rp = _root_world_at(root, frame)
    fd = preferred_dir.normalized() if preferred_dir and preferred_dir.length > 1e-6 else _dribble_dir(root, yaw, frame)
    right = Vector((fd.y, -fd.x, 0.0))
    side = BALL_DRIBBLE_SIDE * math.sin(phase)

    min_ahead = BALL_DRIBBLE_AHEAD
    if arm and arm.pose and arm.pose.bones.get("foot.l") and arm.pose.bones.get("foot.r"):
        # 足先(=ball.*) を優先して “前に出てる足” を検出 → その少し前へ
        bl = arm.pose.bones.get("ball.l") or arm.pose.bones["foot.l"]
        br = arm.pose.bones.get("ball.r") or arm.pose.bones["foot.r"]
        fl = arm.matrix_world @ bl.head
        fr = arm.matrix_world @ br.head
        smax = max((fl - rp).dot(fd), (fr - rp).dot(fd))
        min_ahead = max(min_ahead, smax + BALL_FEET_CLEARANCE)

    p = rp + fd * min_ahead + right * side
    p.z = BALL_GROUND_Z
    return p


def _ball_at_root_frame(
    root: bpy.types.Object,
    yaw: float,
    frame: int,
    arm: bpy.types.Object | None = None,
) -> Vector:
    if arm is None:
        arm = _arm_of_root(root)
    return _ball_at_dribble_frame(root, arm, yaw, frame)


def _add_nla_strip(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
    action_offset: int = 0,
    repeat: bool = True,
) -> None:
    action = bpy.data.actions.get(action_name)
    if not action:
        raise KeyError(action_name)
    ad = arm.animation_data
    if ad is None:
        arm.animation_data_create()
        ad = arm.animation_data
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = action_name
    strip = track.strips.new(action.name, frame_start, action)
    act_start = int(action.frame_range[0])
    act_end = int(action.frame_range[1])
    act_len = max(1, act_end - act_start)
    duration = max(1, frame_end - frame_start)
    strip.action_frame_start = act_start + action_offset
    strip.action_frame_end = act_end
    strip.frame_start = frame_start
    strip.frame_end = frame_start + duration
    strip.extrapolation = "HOLD_FORWARD"
    if repeat and duration > act_len:
        strip.repeat = max(1, int(math.ceil(duration / act_len)))
    strip.blend_type = "REPLACE"
    strip.use_auto_blend = False


def _clear_all_nla(arm: bpy.types.Object) -> None:
    _clear_anim(arm)
    ad = arm.animation_data
    while ad.nla_tracks:
        ad.nla_tracks.remove(ad.nla_tracks[0])


def _ball_hold(
    ball: bpy.types.Object,
    root: bpy.types.Object,
    arm: bpy.types.Object | None,
    yaw: float,
    f0: int,
    f1: int,
    preferred_dir: Vector | None = None,
) -> None:
    """ドリブル/保持 — 常に体の前（速度方向）に追従"""
    if f1 < f0:
        return
    # 1fごとにキーを打つ（足の切り替えで後ろに回り込むのを防ぐ）
    if arm is None:
        arm = _arm_of_root(root)
    for i, f in enumerate(range(f0, f1 + 1)):
        phase = (i / 6.0) * math.tau  # 軽い左右タッチ感
        _kf_loc(ball, f, _ball_at_dribble_frame(root, arm, yaw, f, phase=phase, preferred_dir=preferred_dir))


def _ball_pass_roll(
    ball: bpy.types.Object,
    f_windup: int,
    f_release: int,
    f_arrive: int,
    p_from: Vector,
    p_to: Vector,
    yaw: float,
    arc: float = 0.35,
) -> None:
    """パス — 溜め→転がり→低い弧で受け取り"""
    fwd = _forward_from_yaw(yaw)
    _kf_loc(ball, f_windup, p_from)
    _kf_loc(ball, f_windup + 4, p_from)  # 蹴る前の静止
    mid_f = (f_release + f_arrive) // 2
    mid = _lerp(p_from, p_to, 0.5)
    mid.z = BALL_GROUND_Z + arc
    _kf_loc(ball, f_release - 1, p_from)
    _kf_loc(ball, f_release, p_from + fwd * 0.18)
    _kf_loc(ball, mid_f, mid)
    _kf_loc(ball, f_arrive - 3, p_to + fwd * 0.05)
    _kf_loc(ball, f_arrive, p_to)


def _ball_shot(
    ball: bpy.types.Object,
    f_windup: int,
    f_release: int,
    f_goal: int,
    p_start: Vector,
    p_goal: Vector,
    yaw: float,
) -> None:
    """シュート — 蹴る前の微引き→低弾道→ゴール"""
    fwd = _forward_from_yaw(yaw)
    pull = p_start - fwd * 0.22
    pull.z = BALL_GROUND_Z
    _kf_loc(ball, f_windup, p_start)
    _kf_loc(ball, f_windup + 5, pull)
    _kf_loc(ball, f_release - 1, pull)
    _kf_loc(ball, f_release, p_start + fwd * 0.22)
    t1 = f_release + int((f_goal - f_release) * 0.35)
    t2 = f_release + int((f_goal - f_release) * 0.7)
    p1 = _lerp(p_start, p_goal, 0.35)
    p1.z = BALL_GROUND_Z + 1.2
    p2 = _lerp(p_start, p_goal, 0.7)
    p2.z = BALL_GROUND_Z + 0.6
    _kf_loc(ball, t1, p1)
    _kf_loc(ball, t2, p2)
    _kf_loc(ball, f_goal, p_goal)
    _kf_loc(ball, f_goal + 20, p_goal)


def _move_root(
    root: bpy.types.Object,
    frames: List[Tuple[int, Vector]],
    yaw: float,
) -> None:
    for frame, loc in frames:
        _kf_loc(root, frame, loc)
        _kf_rot_z(root, frame, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _defender_track_y(ball: bpy.types.Object, frame: int, strength: float, offset: float, limit: float) -> float:
    """ボールのYに反応して守備ライン上をスライド（強すぎない）"""
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    by = ball.matrix_world.translation.y
    return _clamp(by * strength + offset, -limit, limit)


def _key_track_root(
    root: bpy.types.Object,
    yaw: float,
    keyframes: List[Tuple[int, Vector]],
) -> None:
    _clear_anim(root)
    for f, loc in keyframes:
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _yaw_from_dir(d: Vector, fallback: float) -> float:
    d2 = Vector((d.x, d.y, 0.0))
    if d2.length < 1e-6:
        return fallback
    # our forward vector is (-sin(yaw), cos(yaw)) -> yaw = atan2(-x, y)
    return math.atan2(-d2.x, d2.y)


def _move_root_face_dir(
    root: bpy.types.Object,
    key_pos: List[Tuple[int, Vector]],
    fallback_yaw: float,
    yaw_offset: float = 0.0,
) -> None:
    """位置キーから移動方向を推定して向きを付ける（offset は1回だけ加算）"""
    _clear_anim(root)
    last_yaw = fallback_yaw
    for i, (f, loc) in enumerate(key_pos):
        if i + 1 < len(key_pos):
            d = key_pos[i + 1][1] - loc
            if d.length > 1e-6:
                last_yaw = _yaw_from_dir(d, last_yaw)
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, last_yaw + yaw_offset)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _move_root_fixed_yaw(
    root: bpy.types.Object,
    key_pos: List[Tuple[int, Vector]],
    yaw: float,
) -> None:
    """全キーで同じ向き（キックオフの整列用）"""
    _clear_anim(root)
    for f, loc in key_pos:
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def _find_arms(prefix: str) -> List[bpy.types.Object]:
    return sorted(
        [o for o in bpy.data.objects if o.name.startswith(prefix) and o.name.endswith("_Armature")],
        key=lambda o: o.name,
    )


def setup_match_timeline() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = MATCH_FRAMES
    scene.render.fps = FPS
    scene.frame_set(1)


def animate_soccer_match_500f() -> None:
    setup_match_timeline()

    blues = _find_arms("Blue_")
    reds = _find_arms("Red_")
    if len(blues) < 5 or len(reds) < 5:
        raise RuntimeError("Need Blue_01..05 and Red_01..05 armatures in scene")

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball object not found")

    goal_x = -PITCH_HALF
    # 青は左ゴール（-X）へ攻める → 前方向は (-1, 0) → base yaw = pi/2
    attack_yaw = math.pi / 2
    yaw_d = -math.pi / 2   # 赤DF: フィールド中央（+X）向き
    yaw_gk = math.pi / 2   # GKだけモデル向きが逆なので +X（フィールド）向き

    b_passer, b_runner, b_wing, b_support, b_striker = blues[:5]
    r_gk, r_def_l, r_def_c, r_def_r, r_fb = reds[:5]
    roots = {a.name: _root_of(a) for a in blues + reds}

    for arm in blues + reds:
        _clear_all_nla(arm)
    if ball.animation_data:
        ball.animation_data_clear()

    # --- 青：位置 ---
    rp = roots[b_passer.name]
    rr = roots[b_runner.name]
    rw = roots[b_wing.name]
    rs = roots[b_support.name]
    rst = roots[b_striker.name]

    # Mannequiny の正面が逆なので、青は yaw を 180°反転して進行方向へ向ける
    blue_yaw_offset = math.pi
    blue_face = attack_yaw + blue_yaw_offset  # 全員そろえて左ゴール向き

    # キックオフ配置（自陣ハーフ・全員左ゴール向き → 走り出し後は進行方向）
    _move_root_face_dir(rp, [
        (1, Vector((1.5, 0, 0))),
        (PASS1_RECEIVE, Vector((1.5, 0, 0))),
        (PASS1_RECEIVE + 1, Vector((14, -6, 0))),
        (500, Vector((14, -6, 0))),
    ], attack_yaw, yaw_offset=blue_yaw_offset)
    _move_root_face_dir(rr, [
        (1, Vector((10, 5, 0))),
        (PASS1_RECEIVE - 1, Vector((10, 5, 0))),
        (200, Vector((-2, 3, 0))),
        (PASS2_START, Vector((-8, 2, 0))),
        (500, Vector((-12, 2, 0))),
    ], attack_yaw, yaw_offset=blue_yaw_offset)
    _move_root_face_dir(rw, [
        (1, Vector((20, 11, 0))),
        (150, Vector((20, 11, 0))),
        (280, Vector((-6, 12, 0))),
        (500, Vector((-6, 12, 0))),
    ], attack_yaw, yaw_offset=blue_yaw_offset)
    _move_root_face_dir(rs, [
        (1, Vector((18, -10, 0))),
        (220, Vector((18, -10, 0))),
        (340, Vector((-28, -8, 0))),
        (500, Vector((-28, -8, 0))),
    ], attack_yaw, yaw_offset=blue_yaw_offset)
    _move_root_face_dir(rst, [
        (1, Vector((22, -3, 0))),
        (PASS2_RECEIVE - 1, Vector((22, -3, 0))),
        (PASS2_RECEIVE, Vector((6, 0, 0))),
        (KICK_STRIP_START - 10, Vector((-10, 0, 0))),
        (KICK_STRIP_START - 2, Vector((-18, 0, 0))),
        (500, Vector((-16, 1, 0))),
    ], attack_yaw, yaw_offset=blue_yaw_offset)

    # --- 青：アクション（キックオフ＝足でタッチ→パス） ---
    _add_nla_strip(b_passer, "idle", 1, PASS1_START - 1)
    _add_nla_strip(b_passer, "fight_kick", PASS1_START, PASS1_START + 37)  # 足でキックオフパス
    _add_nla_strip(b_passer, "idle", PASS1_START + 37, 500)

    _add_nla_strip(b_runner, "idle", 1, PASS1_RECEIVE - 1)
    _add_nla_strip(b_runner, "run", PASS1_RECEIVE, PASS2_START + 10)
    _add_nla_strip(b_runner, "idle", PASS2_START + 10, 500)

    _add_nla_strip(b_wing, "idle", 1, 140)
    _add_nla_strip(b_wing, "run", 140, 300)
    _add_nla_strip(b_wing, "idle", 300, 500)

    _add_nla_strip(b_support, "idle", 1, 210)
    _add_nla_strip(b_support, "run", 210, 350)
    _add_nla_strip(b_support, "idle", 350, 500)

    _add_nla_strip(b_striker, "idle", 1, PASS2_RECEIVE - 1)
    _add_nla_strip(b_striker, "run", PASS2_RECEIVE, KICK_STRIP_START - 1)
    _add_nla_strip(b_striker, "fight_kick", KICK_STRIP_START, KICK_STRIP_START + 37)
    _add_nla_strip(b_striker, "idle", KICK_STRIP_START + 37, 500)

    # --- ボール（キックオフ=センター → 足パス → ドリブル） ---
    p_center = Vector((0.0, 0.0, BALL_GROUND_Z))
    p_passer = Vector((0.0, 0.0, BALL_GROUND_Z))
    p_recv = _ball_at_root_frame(rr, attack_yaw, PASS1_RECEIVE)
    p_pass2_from = _ball_at_root_frame(rr, attack_yaw, PASS2_START - 1)
    p_pass2_to = _ball_at_root_frame(rst, attack_yaw, PASS2_RECEIVE)
    p_shot_start = _ball_at_root_frame(rst, attack_yaw, KICK_STRIP_START + 3)
    p_goal = Vector((goal_x + 6.8, 3.2, BALL_GROUND_Z * 0.85))

    blue_goal_dir = Vector((goal_x, 0.0, 0.0)) - Vector((1.5, 0.0, 0.0))

    _kf_loc(ball, 1, p_center)
    _kf_loc(ball, PASS1_START - 1, p_center)
    _ball_pass_roll(
        ball, PASS1_START, PASS1_RELEASE, PASS1_RECEIVE, p_passer, p_recv, attack_yaw, arc=0.25,
    )
    _ball_hold(ball, rr, b_runner, attack_yaw, PASS1_RECEIVE, PASS2_START - 1, preferred_dir=blue_goal_dir)
    _ball_pass_roll(
        ball, PASS2_START, PASS2_RELEASE, PASS2_RECEIVE, p_pass2_from, p_pass2_to, attack_yaw, arc=0.35,
    )
    _ball_hold(ball, rst, b_striker, attack_yaw, PASS2_RECEIVE, KICK_STRIP_START + 3, preferred_dir=blue_goal_dir)
    _ball_shot(ball, KICK_STRIP_START + 3, KICK_BALL_RELEASE, SHOT_LAND, p_shot_start, p_goal, attack_yaw)
    # セーブ後のこぼれ球（右方向へ弾く）
    _kf_loc(ball, SHOT_LAND + 1, p_goal)
    spill = Vector((goal_x + 18.0, 11.0, BALL_GROUND_Z))
    _kf_loc(ball, SHOT_LAND + 14, spill)
    _kf_loc(ball, SHOT_LAND + 60, spill)

    _ease_all_ball_keyframes(ball)
    bpy.context.scene.frame_set(1)

    # --- 赤：守備（ボールに反応してスライド + GKも動く） ---
    half_w = 68.0 * _SCALE / 2
    y_lim = half_w - 6.0 * _SCALE

    rg = roots[r_gk.name]
    # GK: ゴールライン上でボールのYを追う + シュートで一歩前
    gk_keys: list[tuple[int, Vector]] = []
    for f in range(1, MATCH_FRAMES + 1, 3):
        y = _defender_track_y(ball, f, strength=0.28, offset=0.0, limit=7.0 * _SCALE)
        x = goal_x + 6.0
        if f >= KICK_BALL_RELEASE and f <= KICK_BALL_RELEASE + 18:
            x = goal_x + 8.5  # 一歩前に出る
        gk_keys.append((f, Vector((x, y, 0.0))))
    gk_keys.append((MATCH_FRAMES, gk_keys[-1][1]))
    _key_track_root(rg, yaw_gk, gk_keys)
    _add_nla_strip(r_gk, "fight_idle", 1, SHOT_LAND - 18)
    # 横っ飛び（jump_full）をシュート着弾に合わせる
    _add_nla_strip(r_gk, "jump_full", SHOT_LAND - 16, SHOT_LAND + 18)
    _add_nla_strip(r_gk, "fight_idle", SHOT_LAND + 18, MATCH_FRAMES)

    # GKの横っ飛び（ルートを横へ「移動」させて、ジャンプモーションと合成）
    dive_x0 = goal_x + 6.0
    dive_x1 = goal_x + 8.8
    for f, t in ((SHOT_LAND - 18, 0.0), (SHOT_LAND - 10, 0.55), (SHOT_LAND - 4, 0.9), (SHOT_LAND, 1.0)):
        x = dive_x0 + (dive_x1 - dive_x0) * t
        y = p_goal.y * (0.85 + 0.15 * t)
        gk_keys.append((f, Vector((x, y, 0.0))))
    # 着地後は少し戻る
    gk_keys.append((SHOT_LAND + 22, Vector((goal_x + 7.2, p_goal.y * 0.6, 0.0))))
    gk_keys.append((MATCH_FRAMES, gk_keys[-1][1]))
    gk_keys = sorted({f: v for f, v in gk_keys}.items(), key=lambda kv: kv[0])
    _key_track_root(rg, yaw_gk, [(f, v) for f, v in gk_keys])

    # DFライン: ボールのYへスライドしつつ、ボールが近づいたら下がる
    def_specs = [
        (r_def_l, Vector((-62, -14, 0)), 0.55, -6.0 * _SCALE),
        (r_def_c, Vector((-58, 0, 0)), 0.70, 0.0),
        (r_def_r, Vector((-62, 14, 0)), 0.55, 6.0 * _SCALE),
        (r_fb, Vector((-48, 18, 0)), 0.45, 10.0 * _SCALE),
    ]
    for arm, base, strength, off in def_specs:
        root = roots[arm.name]
        keys: list[tuple[int, Vector]] = []
        for f in range(1, MATCH_FRAMES + 1, 4):
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            bp = ball.matrix_world.translation
            # ボールが自陣深く来るほどゴール寄りに下がる（xを減らす）
            retreat = _clamp(((-bp.x) - 10.0) / 50.0, 0.0, 1.0)
            x = base.x - retreat * 18.0
            y = _defender_track_y(ball, f, strength=strength, offset=off, limit=y_lim)
            keys.append((f, Vector((x, y, 0.0))))
        keys.append((MATCH_FRAMES, keys[-1][1]))
        _key_track_root(root, yaw_d, keys)
        _add_nla_strip(arm, "run", 1, MATCH_FRAMES)

    print(
        f"Match v3 kickoff: pass1 f{PASS1_RELEASE} pass2 f{PASS2_RELEASE} "
        f"kick f{KICK_BALL_RELEASE} goal f{SHOT_LAND}"
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


def setup_match_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamMatch")
    cam = bpy.data.objects.new("CamMatch", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 40
    gx = -PITCH_HALF
    _kf_cam(cam, 1, Vector((30, -32, 7)), Vector((20, -5, 1.2)))
    _kf_cam(cam, PASS1_RELEASE, Vector((26, -28, 6.5)), Vector((18, 0, 1.0)))
    _kf_cam(cam, 180, Vector((8, -24, 6)), Vector((0, 2, 1.0)))
    _kf_cam(cam, PASS2_RELEASE, Vector((-5, -22, 5.5)), Vector((-10, 1, 1.0)))
    _kf_cam(cam, KICK_BALL_RELEASE, Vector((-35, -18, 5)), Vector((-22, 0, 1.5)))
    _kf_cam(cam, SHOT_LAND, Vector((gx + 22, -14, 4.5)), Vector((gx + 1, 0, 1.8)))
    _kf_cam(cam, 500, Vector((gx + 26, -12, 4.2)), Vector((gx, 0, 1.5)))
    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def render_match_preview() -> "Path":
    from pathlib import Path

    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_match_timeline()
    setup_black_world()
    setup_lights()
    setup_match_camera()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = MATCH_FRAMES
    scene.eevee.taa_render_samples = 8

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "match_preview.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering video (fast): {out} ({MATCH_FRAMES}f)...")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path

    _dir = Path(__file__).resolve().parent
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-match-video" in sys.argv:
        render_match_preview()
    elif "--animate" in sys.argv:
        animate_soccer_match_500f()
        bpy.ops.wm.save_mainfile(filepath=str(blend))
    elif "--full" in sys.argv:
        from build_part_field import build_field_only  # noqa: E402

        build_field_only()
        animate_soccer_match_500f()
        bpy.ops.wm.save_mainfile(filepath=str(blend))
        if "--render" in sys.argv:
            render_match_preview()
