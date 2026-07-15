# SPDX-License-Identifier: MIT
"""Spain block cuts 09–17 builders. Attack Goal_R for visual variety."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

import bpy
from mathutils import Vector

from animate_soccer_match import (  # noqa: E402
    BALL_GROUND_Z,
    _clear_all_nla,
)

from cuts.common import (  # noqa: E402
    FPS,
    GOAL_H,
    GOAL_INNER_HALF_W,
    REF_BLACK,
    SHAOLIN_ORANGE,
    SHAOLIN_WHITE,
    SIDE_GAP,
    SPAIN_RED,
    SPAIN_YELLOW,
    TALK_BONES,
    add_box,
    add_nla_hold,
    add_nla_loop,
    add_nla_once,
    add_talk_strip,
    animate_gk_dive,
    animate_root,
    ball_ahead_of,
    clear_ball_anim,
    ease,
    finish_cam,
    force_linear,
    goal_r_x,
    hide_ball,
    kf_cam,
    key_ball,
    mat_rgba,
    remove_players,
    set_frame_range,
    setup_new_cam,
    spawn_player,
    yaw_face_neg_x,
    yaw_face_neg_y,
    yaw_face_pos_x,
)


def _show_pitch() -> None:
    for obj in list(bpy.data.objects):
        if obj.name == "Ball" or obj.name.startswith(
            ("Field_", "Line_", "Pen", "Goal", "Corner_", "Net", "Post", "Crossbar")
        ):
            obj.hide_render = False
            obj.hide_viewport = False


def _hide_pitch(keep_extra: Tuple[str, ...] = ()) -> None:
    keep = ("Light", "Sun", "World", "Camera", "Cam") + keep_extra
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            continue
        if obj.name.startswith(keep):
            continue
        if obj.name == "Ball" or obj.name.startswith(
            ("Field_", "Line_", "Pen", "Goal", "Corner_", "Net", "Post", "Crossbar")
        ):
            obj.hide_render = True
            obj.hide_viewport = True


def _dense_cam(cam: bpy.types.Object, frames: int, pos_fn, tgt_fn, step: int = 3) -> None:
    for f in range(1, frames + 1, step):
        kf_cam(cam, f, pos_fn(f), tgt_fn(f))
    if (frames - 1) % step != 0:
        kf_cam(cam, frames, pos_fn(frames), tgt_fn(frames))
    finish_cam(cam)


def _belly_ball(player: Vector, facing: Vector, z_off: float = 2.2, ahead: float = 0.85) -> Vector:
    """Ball stuck to belly — explicit offset in front of torso."""
    fd = facing.normalized()
    p = player + fd * ahead
    p.z = player.z + z_off
    return p


def _lerp_ball_seg(p0: Vector, p1: Vector, t: float, arc: float = 0.8) -> Vector:
    u = ease(max(0.0, min(1.0, t)))
    p = p0.lerp(p1, u)
    p.z += arc * math.sin(u * math.pi)
    return p


def _protest_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    t = frame / FPS
    turn = 0.18 * math.sin(t * 2.4) + 0.08 * math.sin(t * 4.1)
    lean = 0.06 * math.sin(t * 1.7)
    nod = 0.1 * math.sin(t * 5.2)
    return {
        "spine_01": (0.03 + lean * 0.5, 0.0, turn * 0.35),
        "spine_02": (0.05 + lean, 0.0, turn * 0.55),
        "neck_01": (0.04 + nod * 0.5, 0.0, turn * 0.85),
        "head": (0.05 + nod, 0.0, turn),
    }


def _talk_deltas_calm(frame: int) -> Dict[str, Tuple[float, float, float]]:
    t = frame / FPS
    nod = 0.055 * math.sin(t * 5.2) + 0.028 * math.sin(t * 8.5)
    turn = 0.07 * math.sin(t * 1.7) + 0.035 * math.sin(t * 3.2)
    lean = 0.035 * math.sin(t * 1.2)
    return {
        "spine_01": (0.02 + lean * 0.4, 0.0, turn * 0.25),
        "spine_02": (0.035 + lean, 0.0, turn * 0.4),
        "neck_01": (0.03 + nod * 0.65, 0.0, turn * 0.75),
        "head": (0.04 + nod, 0.0, turn),
    }


def _assert_gaps(*positions: Vector) -> None:
    for i, a in enumerate(positions):
        for b in positions[i + 1 :]:
            d = Vector((a.x - b.x, a.y - b.y, 0.0)).length
            if d < SIDE_GAP - 0.05:
                raise RuntimeError(f"SIDE_GAP violation: {d:.2f} < {SIDE_GAP}")


# ---------------------------------------------------------------------------
# 09 Spain pass triangle → goal + Shaolin GK jumps UP but goal
# ---------------------------------------------------------------------------
def build_09() -> int:
    remove_players()
    _show_pitch()
    frames = 300
    gx = goal_r_x()
    yaw = yaw_face_pos_x()
    yaw_gk = yaw_face_neg_x()
    a = Vector((gx - 38.0, 0.0, 0.0))
    b = Vector((gx - 28.0, SIDE_GAP * 1.15, 0.0))
    c = Vector((gx - 22.0, -SIDE_GAP * 1.15, 0.0))
    gk_home = Vector((gx - 2.8, 0.15, 0.0))
    _assert_gaps(a, b, c)
    shoot_pos = Vector((gx - 14.0, -SIDE_GAP * 0.9, 0.0))
    ball_goal = Vector((gx + 1.5, GOAL_INNER_HALF_W * 0.55, GOAL_H * 0.58))

    arm_a, root_a = spawn_player("Spain_A", SPAIN_YELLOW, a, yaw, actions=["idle", "fight_kick", "run"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    arm_b, root_b = spawn_player("Spain_B", SPAIN_YELLOW, b, yaw, actions=["idle", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    arm_c, root_c = spawn_player("Spain_C", SPAIN_YELLOW, c, yaw, actions=["idle", "run", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    gk_arm, gk_root = spawn_player(
        "Shaolin_GK", SHAOLIN_ORANGE, gk_home, yaw_gk,
        actions=["fight_idle", "jump_full", "idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    for ar in (arm_a, arm_b, arm_c, gk_arm):
        _clear_all_nla(ar)

    f_p1, f_p2, f_p3, f_kick, f_goal = 48, 90, 132, 168, 198
    f_dive = 174

    def c_path(f: int) -> Vector:
        if f < f_p3:
            return c.copy()
        if f <= f_kick:
            t = ease((f - f_p3) / max(1, f_kick - f_p3))
            return c.lerp(shoot_pos, t)
        t = (f - f_kick) / max(1, frames - f_kick)
        return shoot_pos + Vector((0.8 * ease(min(1.0, t)), 0.05 * t, 0.0))

    animate_root(root_a, [(1, a), (frames, a)], yaw)
    animate_root(root_b, [(1, b), (frames, b)], yaw)
    keys_c = [(f, c_path(f)) for f in range(1, frames + 1, 2)]
    keys_c.append((frames, c_path(frames)))
    animate_root(root_c, keys_c, yaw)
    # vertical jump only (side=False)
    animate_gk_dive(gk_root, gk_arm, gk_home, 0.0, f_dive, f_goal + 4, frames, yaw_gk, side=False, rise=1.4)

    add_nla_hold(arm_a, "idle", 1, f_p1 - 12, af=5)
    add_nla_once(arm_a, "fight_kick", f_p1 - 10, f_p1 + 12)
    add_nla_hold(arm_a, "idle", f_p1 + 13, frames, af=6)

    add_nla_hold(arm_b, "idle", 1, f_p2 - 12, af=5)
    add_nla_once(arm_b, "fight_kick", f_p2 - 10, f_p2 + 12)
    add_nla_hold(arm_b, "idle", f_p2 + 13, frames, af=6)

    add_nla_hold(arm_c, "idle", 1, f_p3 - 4, af=5)
    add_nla_loop(arm_c, "run", f_p3, f_kick - 8)
    add_nla_once(arm_c, "fight_kick", f_kick - 10, f_kick + 14)
    add_nla_hold(arm_c, "idle", f_kick + 15, frames, af=6)

    ball = clear_ball_anim()
    move = Vector((1.0, 0.0, 0.0))
    feet_a = ball_ahead_of(a, move, 1)
    feet_b = ball_ahead_of(b, move, 1)
    feet_c0 = ball_ahead_of(c, move, 1)

    def ball_path(f: int) -> Vector:
        if f < f_p1:
            return feet_a.copy()
        if f < f_p2:
            return _lerp_ball_seg(feet_a, feet_b, (f - f_p1) / max(1, f_p2 - f_p1), 0.9)
        if f < f_p3:
            return _lerp_ball_seg(feet_b, feet_c0, (f - f_p2) / max(1, f_p3 - f_p2), 0.9)
        if f < f_kick:
            cp = c_path(f)
            return ball_ahead_of(cp, move, f, arm=arm_c)
        t = min(1.0, (f - f_kick) / max(1, f_goal - f_kick))
        s = ball_ahead_of(c_path(f_kick - 1), move, f_kick - 1, arm=arm_c)
        u = 1.0 - (1.0 - t) ** 2.4
        p = s.lerp(ball_goal, u)
        p.z = BALL_GROUND_Z + (ball_goal.z - BALL_GROUND_Z) * u + 1.1 * math.sin(u * math.pi) * (1.0 - 0.35 * u)
        if f > f_goal:
            t2 = (f - f_goal) / max(1, frames - f_goal)
            p = ball_goal + Vector((0.7 * ease(min(1.0, t2)), 0.08 * t2, -0.4 * ease(min(1.0, t2))))
            p.z = max(BALL_GROUND_Z + 0.3, p.z)
        return p

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut09", lens=30)

    def cam_pos(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x - 6.0, bp.y - 12.0, 4.2))

    def cam_tgt(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x + 1.0, bp.y * 0.3, max(1.2, bp.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 10 Spain pass triangle v2 — Shaolin GK sideways dive, still goal
# ---------------------------------------------------------------------------
def build_10() -> int:
    remove_players()
    _show_pitch()
    frames = 300
    gx = goal_r_x()
    yaw = yaw_face_pos_x()
    yaw_gk = yaw_face_neg_x()
    a = Vector((gx - 42.0, SIDE_GAP * 0.2, 0.0))
    b = Vector((gx - 30.0, SIDE_GAP * 1.6, 0.0))
    c = Vector((gx - 26.0, -SIDE_GAP * 1.6, 0.0))
    gk_home = Vector((gx - 2.8, 0.0, 0.0))
    _assert_gaps(a, b, c)
    shoot_pos = Vector((gx - 12.0, -SIDE_GAP * 0.7, 0.0))
    ball_goal = Vector((gx + 1.4, -GOAL_INNER_HALF_W * 0.65, GOAL_H * 0.5))
    f_p1, f_p2, f_p3, f_kick, f_goal = 52, 100, 148, 185, 214
    f_dive = 192

    arm_a, root_a = spawn_player("Spain_A", SPAIN_YELLOW, a, yaw, actions=["idle", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    arm_b, root_b = spawn_player("Spain_B", SPAIN_YELLOW, b, yaw, actions=["idle", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    arm_c, root_c = spawn_player("Spain_C", SPAIN_YELLOW, c, yaw, actions=["idle", "run", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    gk_arm, gk_root = spawn_player(
        "Shaolin_GK", SHAOLIN_ORANGE, gk_home, yaw_gk,
        actions=["fight_idle", "jump_full", "idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    for ar in (arm_a, arm_b, arm_c, gk_arm):
        _clear_all_nla(ar)

    def c_path(f: int) -> Vector:
        if f < f_p3:
            return c.copy()
        if f <= f_kick:
            return c.lerp(shoot_pos, ease((f - f_p3) / max(1, f_kick - f_p3)))
        t = (f - f_kick) / max(1, frames - f_kick)
        return shoot_pos + Vector((0.9 * ease(min(1.0, t)), 0.0, 0.0))

    animate_root(root_a, [(1, a), (frames, a)], yaw)
    animate_root(root_b, [(1, b), (frames, b)], yaw)
    keys_c = [(f, c_path(f)) for f in range(1, frames + 1, 2)] + [(frames, c_path(frames))]
    animate_root(root_c, keys_c, yaw)
    animate_gk_dive(
        gk_root, gk_arm, gk_home, ball_goal.y * 0.7, f_dive, f_goal + 4, frames, yaw_gk, side=True, rise=0.85
    )

    add_nla_once(arm_a, "fight_kick", f_p1 - 10, f_p1 + 12)
    add_nla_hold(arm_a, "idle", 1, f_p1 - 11, af=5)
    add_nla_hold(arm_a, "idle", f_p1 + 13, frames, af=6)
    add_nla_hold(arm_b, "idle", 1, f_p2 - 11, af=5)
    add_nla_once(arm_b, "fight_kick", f_p2 - 10, f_p2 + 12)
    add_nla_hold(arm_b, "idle", f_p2 + 13, frames, af=6)
    add_nla_hold(arm_c, "idle", 1, f_p3 - 2, af=5)
    add_nla_loop(arm_c, "run", f_p3, f_kick - 8)
    add_nla_once(arm_c, "fight_kick", f_kick - 10, f_kick + 14)
    add_nla_hold(arm_c, "idle", f_kick + 15, frames, af=6)

    ball = clear_ball_anim()
    move = Vector((1.0, 0.0, 0.0))
    fa, fb, fc0 = ball_ahead_of(a, move, 1), ball_ahead_of(b, move, 1), ball_ahead_of(c, move, 1)

    def ball_path(f: int) -> Vector:
        if f < f_p1:
            return fa.copy()
        if f < f_p2:
            return _lerp_ball_seg(fa, fb, (f - f_p1) / max(1, f_p2 - f_p1), 1.0)
        if f < f_p3:
            return _lerp_ball_seg(fb, fc0, (f - f_p2) / max(1, f_p3 - f_p2), 1.0)
        if f < f_kick:
            return ball_ahead_of(c_path(f), move, f, arm=arm_c)
        t = min(1.0, (f - f_kick) / max(1, f_goal - f_kick))
        s = ball_ahead_of(c_path(f_kick - 1), move, f_kick - 1, arm=arm_c)
        u = 1.0 - (1.0 - t) ** 2.4
        p = s.lerp(ball_goal, u)
        p.z = BALL_GROUND_Z + (ball_goal.z - BALL_GROUND_Z) * u + 1.0 * math.sin(u * math.pi)
        if f > f_goal:
            t2 = (f - f_goal) / max(1, frames - f_goal)
            p = ball_goal + Vector((0.65 * ease(min(1.0, t2)), -0.1 * t2, -0.35 * ease(min(1.0, t2))))
            p.z = max(BALL_GROUND_Z + 0.28, p.z)
        return p

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut10", lens=26)

    def cam_pos(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x - 10.0, bp.y + 16.0, 7.5))

    def cam_tgt(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x + 2.0, 0.0, max(1.0, bp.z * 0.6)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 11 Spain belly cut — wide gap, left Spain faces screen-right, ball STICKS
# ---------------------------------------------------------------------------
def build_11() -> int:
    remove_players()
    _show_pitch()
    frames = 240
    gx = goal_r_x()
    # much wider spacing
    spa_left = Vector((gx - 34.0, SIDE_GAP * 2.8, 0.0))
    sh = Vector((gx - 30.0, 0.0, 0.0))
    spa_right = Vector((gx - 34.0, -SIDE_GAP * 2.8, 0.0))
    _assert_gaps(spa_left, sh, spa_right)

    # screen-left Spain faces screen-right (-Y)
    yaw_left = yaw_face_neg_y()
    yaw_right = yaw_face_pos_y() if False else math.pi  # face +Y toward teammate? 
    # Camera from -X: screen-right is -Y. Left player should face screen-right = face -Y.
    # Passer on screen-right faces left teammate = face +Y.
    yaw_right = math.pi  # face +Y? yaw_face: 0 = -Y, pi/2 = +X, pi = +Y, 1.5pi = -X
    # yaw_face_neg_y = 0 → faces -Y
    # To face +Y use math.pi
    arm_pass, root_pass = spawn_player(
        "Spain_R", SPAIN_YELLOW, spa_right, math.pi,
        actions=["idle", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42),
    )
    arm_s, root_s = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, sh, yaw_face_neg_y(),
        actions=["idle", "fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    arm_recv, root_recv = spawn_player(
        "Spain_L", SPAIN_YELLOW, spa_left, yaw_face_neg_y(),
        actions=["idle"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42),
    )
    for ar in (arm_pass, arm_s, arm_recv):
        _clear_all_nla(ar)
    animate_root(root_pass, [(1, spa_right), (frames, spa_right)], math.pi)
    animate_root(root_s, [(1, sh), (frames, sh)], yaw_face_neg_y())
    animate_root(root_recv, [(1, spa_left), (frames, spa_left)], yaw_face_neg_y())

    f_pass, f_cut = 70, 105
    add_nla_hold(arm_pass, "idle", 1, f_pass - 12, af=5)
    add_nla_once(arm_pass, "fight_kick", f_pass - 10, f_pass + 12)
    add_nla_hold(arm_pass, "idle", f_pass + 13, frames, af=6)
    add_nla_hold(arm_s, "idle", 1, f_cut - 8, af=5)
    add_nla_hold(arm_s, "fight_idle", f_cut - 6, frames, af=12)
    add_nla_hold(arm_recv, "idle", 1, frames, af=5)

    ball = clear_ball_anim()
    face_pass = Vector((0.0, 1.0, 0.0))
    start_b = ball_ahead_of(spa_right, face_pass, 1)
    # belly in FRONT of torso (toward camera / -Y) so ball doesn't sink through body
    belly = _belly_ball(sh, Vector((0.0, -1.0, 0.0)), z_off=2.15, ahead=1.15)

    def ball_path(f: int) -> Vector:
        if f < f_pass:
            return start_b.copy()
        if f < f_cut:
            t = (f - f_pass) / max(1, f_cut - f_pass)
            # approach from passer toward front of shaolin belly
            return _lerp_ball_seg(start_b, belly, t, 0.55)
        # stick firmly on belly surface (no penetration)
        return belly.copy()

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut11", lens=28)

    def cam_pos(f: int) -> Vector:
        return Vector((sh.x - 18.0, -2.0, 7.5))

    def cam_tgt(f: int) -> Vector:
        return Vector((sh.x, 0.0, 1.6))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 12 Walk with belly-ball → drop pass → receive → shot (keep shot flow)
# ---------------------------------------------------------------------------
def build_12() -> int:
    remove_players()
    _show_pitch()
    frames = 320
    gx = goal_r_x()
    yaw = yaw_face_pos_x()
    yaw_gk = yaw_face_neg_x()
    s1_start = Vector((gx - 48.0, SIDE_GAP * 0.7, 0.0))
    s1_pass = Vector((gx - 34.0, SIDE_GAP * 0.55, 0.0))
    s2 = Vector((gx - 22.0, -SIDE_GAP * 0.55, 0.0))
    shoot = Vector((gx - 12.0, -SIDE_GAP * 0.4, 0.0))
    gk_in = Vector((gx + 0.6, 0.15, 0.0))
    _assert_gaps(s1_pass, s2)
    ball_goal = Vector((gx + 1.5, -GOAL_INNER_HALF_W * 0.45, GOAL_H * 0.6))
    f_walk_end, f_drop, f_pass, f_recv, f_kick, f_goal = 70, 82, 95, 125, 165, 195

    arm1, root1 = spawn_player("Shaolin_A", SHAOLIN_ORANGE, s1_start, yaw, actions=["idle", "run", "fight_kick"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42))
    arm2, root2 = spawn_player("Shaolin_B", SHAOLIN_ORANGE, s2, yaw, actions=["idle", "run", "fight_kick"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42))
    arm_gk, root_gk = spawn_player(
        "Spain_GK", SPAIN_YELLOW, gk_in, yaw_gk,
        actions=["fight_idle"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42),
    )
    for ar in (arm1, arm2, arm_gk):
        _clear_all_nla(ar)

    def s1_path(f: int) -> Vector:
        if f <= f_walk_end:
            return s1_start.lerp(s1_pass, ease((f - 1) / max(1, f_walk_end - 1)))
        return s1_pass.copy()

    def s2_path(f: int) -> Vector:
        if f < f_recv:
            return s2.copy()
        if f <= f_kick:
            return s2.lerp(shoot, ease((f - f_recv) / max(1, f_kick - f_recv)))
        t = (f - f_kick) / max(1, frames - f_kick)
        return shoot + Vector((0.7 * ease(min(1.0, t)), 0.0, 0.0))

    keys1 = [(f, s1_path(f)) for f in range(1, frames + 1, 2)] + [(frames, s1_path(frames))]
    keys2 = [(f, s2_path(f)) for f in range(1, frames + 1, 2)] + [(frames, s2_path(frames))]
    animate_root(root1, keys1, yaw)
    animate_root(root2, keys2, yaw)
    animate_root(root_gk, [(1, gk_in), (frames, gk_in)], yaw_gk)

    add_nla_loop(arm1, "run", 1, f_walk_end)
    add_nla_hold(arm1, "idle", f_walk_end + 1, f_pass - 12, af=5)
    add_nla_once(arm1, "fight_kick", f_pass - 10, f_pass + 12)
    add_nla_hold(arm1, "idle", f_pass + 13, frames, af=6)
    add_nla_hold(arm2, "idle", 1, f_recv - 2, af=5)
    add_nla_loop(arm2, "run", f_recv, f_kick - 8)
    add_nla_once(arm2, "fight_kick", f_kick - 10, f_kick + 14)
    add_nla_hold(arm2, "idle", f_kick + 15, frames, af=6)
    add_nla_hold(arm_gk, "fight_idle", 1, frames, af=10)

    ball = clear_ball_anim()
    move = Vector((1.0, 0.0, 0.0))

    def ball_path(f: int) -> Vector:
        p1 = s1_path(f)
        if f < f_drop:
            # stuck to belly while walking
            return _belly_ball(p1, move, z_off=2.2, ahead=0.9)
        if f < f_pass:
            # drop from belly toward feet
            belly = _belly_ball(s1_pass, move, z_off=2.2, ahead=0.9)
            feet = ball_ahead_of(s1_pass, move, f, arm=arm1)
            t = ease((f - f_drop) / max(1, f_pass - f_drop))
            return belly.lerp(feet, t)
        if f < f_recv:
            dest = ball_ahead_of(s2, move, f_recv, arm=arm2)
            s = ball_ahead_of(s1_pass, move, f_pass, arm=arm1)
            return _lerp_ball_seg(s, dest, (f - f_pass) / max(1, f_recv - f_pass), 1.1)
        if f < f_kick:
            return ball_ahead_of(s2_path(f), move, f, arm=arm2)
        t = min(1.0, (f - f_kick) / max(1, f_goal - f_kick))
        s = ball_ahead_of(s2_path(f_kick - 1), move, f_kick - 1, arm=arm2)
        u = 1.0 - (1.0 - t) ** 2.4
        p = s.lerp(ball_goal, u)
        p.z = BALL_GROUND_Z + (ball_goal.z - BALL_GROUND_Z) * u + 1.15 * math.sin(u * math.pi) * (1.0 - 0.35 * u)
        if f > f_goal:
            t2 = (f - f_goal) / max(1, frames - f_goal)
            p = ball_goal + Vector((0.7 * ease(min(1.0, t2)), -0.08 * t2, -0.4 * ease(min(1.0, t2))))
            p.z = max(BALL_GROUND_Z + 0.3, p.z)
        return p

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut12", lens=30)

    def cam_pos(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x - 5.5, bp.y - 11.5, 4.0))

    def cam_tgt(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x + 1.5, bp.y * 0.25, max(1.2, bp.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 13 Spain shoots; Shaolin blocker belly-stops in front of Shaolin GK
# ---------------------------------------------------------------------------
def build_13() -> int:
    remove_players()
    _show_pitch()
    frames = 240
    gx = goal_r_x()
    yaw_sp = yaw_face_pos_x()
    yaw_sh = yaw_face_neg_x()
    spain = Vector((gx - 28.0, 0.4, 0.0))
    blocker = Vector((gx - 10.0, 0.0, 0.0))
    gk = Vector((gx - 3.2, 0.0, 0.0))
    # blocker in FRONT of GK, SIDE_GAP between them
    assert abs(blocker.x - gk.x) >= SIDE_GAP - 0.2
    _assert_gaps(spain, blocker)

    arm_sp, root_sp = spawn_player("Spain", SPAIN_YELLOW, spain, yaw_sp, actions=["idle", "run", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    arm_bl, root_bl = spawn_player("Shaolin_Bl", SHAOLIN_ORANGE, blocker, yaw_sh, actions=["idle", "fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42))
    arm_gk, root_gk = spawn_player("Shaolin_GK", SHAOLIN_ORANGE, gk, yaw_sh, actions=["fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42))
    for ar in (arm_sp, arm_bl, arm_gk):
        _clear_all_nla(ar)

    f_kick, f_block = 90, 118
    animate_root(root_sp, [(1, spain), (frames, spain)], yaw_sp)
    animate_root(root_bl, [(1, blocker), (frames, blocker)], yaw_sh)
    animate_root(root_gk, [(1, gk), (frames, gk)], yaw_sh)
    add_nla_hold(arm_sp, "idle", 1, f_kick - 14, af=5)
    add_nla_once(arm_sp, "fight_kick", f_kick - 12, f_kick + 14)
    add_nla_hold(arm_sp, "idle", f_kick + 15, frames, af=6)
    add_nla_hold(arm_bl, "idle", 1, f_block - 10, af=5)
    add_nla_hold(arm_bl, "fight_idle", f_block - 8, frames, af=12)
    add_nla_hold(arm_gk, "fight_idle", 1, frames, af=10)

    ball = clear_ball_anim()
    move = Vector((1.0, 0.0, 0.0))
    start_b = ball_ahead_of(spain, move, 1, arm=arm_sp)
    belly = _belly_ball(blocker, Vector((-1.0, 0.0, 0.0)), z_off=2.2, ahead=0.85)

    def ball_path(f: int) -> Vector:
        if f < f_kick:
            return ball_ahead_of(spain, move, f, arm=arm_sp)
        if f < f_block:
            return _lerp_ball_seg(start_b, belly, (f - f_kick) / max(1, f_block - f_kick), 0.85)
        return belly.copy()

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut13", lens=30)

    def cam_pos(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x - 4.0, bp.y - 12.0, 4.2))

    def cam_tgt(f: int) -> Vector:
        bp = ball_path(f)
        return Vector((bp.x + 1.0, 0.0, max(1.3, bp.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 14 Shaolin belly-ball charges INTO Goal_R; Spain GK stick-still
# ---------------------------------------------------------------------------
def build_14() -> int:
    remove_players()
    _show_pitch()
    frames = 264
    gx = goal_r_x()
    yaw = yaw_face_pos_x()
    yaw_gk = yaw_face_neg_x()
    start = Vector((gx - 28.0, 0.3, 0.0))
    net_pos = Vector((gx + 1.2, 0.2, 0.0))
    gk_home = Vector((gx - 2.8, -SIDE_GAP * 0.95, 0.0))
    _assert_gaps(Vector((gx - 6.0, 0.0, 0.0)), gk_home)
    f_enter = 150

    arm, root = spawn_player("Shaolin", SHAOLIN_ORANGE, start, yaw, actions=["run", "fight_idle", "idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42))
    gk_arm, gk_root = spawn_player("Spain_GK", SPAIN_YELLOW, gk_home, yaw_gk, actions=["fight_idle"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    _clear_all_nla(arm)
    _clear_all_nla(gk_arm)

    def path(f: int) -> Vector:
        if f <= f_enter:
            t = ease((f - 1) / max(1, f_enter - 1))
            return start.lerp(net_pos, t)
        t = (f - f_enter) / max(1, frames - f_enter)
        return net_pos + Vector((0.4 * ease(min(1.0, t)), 0.05 * t, 0.0))

    keys = [(f, path(f)) for f in range(1, frames + 1, 2)] + [(frames, path(frames))]
    animate_root(root, keys, yaw)
    animate_root(gk_root, [(1, gk_home), (frames, gk_home)], yaw_gk)
    add_nla_loop(arm, "run", 1, f_enter)
    add_nla_hold(arm, "fight_idle", f_enter + 1, frames, af=12)
    add_nla_hold(gk_arm, "fight_idle", 1, frames, af=12)

    ball = clear_ball_anim()

    def ball_path(f: int) -> Vector:
        p = path(f)
        return _belly_ball(p, Vector((1.0, 0.0, 0.0)), z_off=2.2, ahead=0.9)

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut14", lens=28)

    def cam_pos(f: int) -> Vector:
        p = path(f)
        return Vector((p.x - 8.0, p.y - 10.0, 4.5))

    def cam_tgt(f: int) -> Vector:
        p = path(f)
        return Vector((p.x + 1.5, p.y * 0.2, 1.8))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 15 Spain kicks Shaolin's belly-ball (approach stop SIDE_GAP short)
# ---------------------------------------------------------------------------
def build_15() -> int:
    remove_players()
    _show_pitch()
    frames = 216
    gx = goal_r_x()
    sh = Vector((gx - 20.0, 0.0, 0.0))
    # Spain approaches from -X but stops SIDE_GAP away
    sp_start = Vector((gx - 36.0, 0.2, 0.0))
    sp_stop = Vector((sh.x - SIDE_GAP, 0.15, 0.0))
    assert (sp_stop - sh).length >= SIDE_GAP - 0.05
    yaw_sp = yaw_face_pos_x()
    yaw_sh = yaw_face_neg_x()
    f_arrive, f_kick, f_pop = 90, 110, 118

    arm_sp, root_sp = spawn_player("Spain", SPAIN_YELLOW, sp_start, yaw_sp, actions=["run", "fight_kick", "idle"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    arm_sh, root_sh = spawn_player("Shaolin", SHAOLIN_ORANGE, sh, yaw_sh, actions=["fight_idle", "idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42))
    _clear_all_nla(arm_sp)
    _clear_all_nla(arm_sh)

    def sp_path(f: int) -> Vector:
        if f <= f_arrive:
            return sp_start.lerp(sp_stop, ease((f - 1) / max(1, f_arrive - 1)))
        return sp_stop.copy()

    keys = [(f, sp_path(f)) for f in range(1, frames + 1, 2)] + [(frames, sp_path(frames))]
    animate_root(root_sp, keys, yaw_sp)
    animate_root(root_sh, [(1, sh), (frames, sh)], yaw_sh)
    add_nla_loop(arm_sp, "run", 1, f_arrive)
    add_nla_once(arm_sp, "fight_kick", f_kick - 12, f_kick + 14)
    add_nla_hold(arm_sp, "idle", f_kick + 15, frames, af=6)
    add_nla_hold(arm_sh, "fight_idle", 1, frames, af=12)

    ball = clear_ball_anim()
    belly = _belly_ball(sh, Vector((-1.0, 0.0, 0.0)), z_off=2.2, ahead=0.9)
    pop_end = belly + Vector((-4.5, 1.2, 1.5))

    def ball_path(f: int) -> Vector:
        if f < f_pop:
            return belly.copy()
        t = min(1.0, (f - f_pop) / max(1, 40))
        p = _lerp_ball_seg(belly, pop_end, t, 1.4)
        if f > f_pop + 40:
            t2 = (f - (f_pop + 40)) / max(1, frames - (f_pop + 40))
            p = pop_end + Vector((-1.5 * ease(min(1.0, t2)), 0.4 * t2, -1.2 * ease(min(1.0, t2))))
            p.z = max(BALL_GROUND_Z, p.z)
        return p

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut15", lens=32)

    def cam_pos(f: int) -> Vector:
        mid = (sp_path(f) + sh) * 0.5
        return Vector((mid.x - 2.0, mid.y - 10.0, 3.8))

    def cam_tgt(f: int) -> Vector:
        return Vector((sh.x - 1.0, 0.0, 1.9))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 16 Yellow card — face each other; raise card; then Spain angry
# ---------------------------------------------------------------------------
def build_16() -> int:
    remove_players()
    frames = 280
    _hide_pitch(keep_extra=("Referee_", "Spain_", "Card_"))
    hide_ball()
    floor_m = mat_rgba("Card_FloorMat", (0.12, 0.12, 0.13, 1.0), 0.9)
    add_box("Card_Floor", (8.0, 6.0, 0.1), Vector((0.0, 0.5, 0.05)), floor_m)
    add_box("Card_Back", (7.0, 0.15, 4.0), Vector((0.0, 2.8, 2.1)), mat_rgba("Card_BackMat", (0.08, 0.08, 0.1, 1.0), 0.85))

    ref_pos = Vector((-SIDE_GAP * 0.55, 0.0, 0.0))
    sp_pos = Vector((SIDE_GAP * 0.55, 0.15, 0.0))
    # face each other: ref looks +X, Spain looks -X
    yaw_ref = yaw_face_pos_x()
    yaw_sp = yaw_face_neg_x()

    ref_arm, ref_root = spawn_player("Referee", REF_BLACK, ref_pos, yaw_ref, actions=["idle", "fight_idle"])
    sp_arm, sp_root = spawn_player("Spain", SPAIN_YELLOW, sp_pos, yaw_sp, actions=["idle"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    _clear_all_nla(ref_arm)
    _clear_all_nla(sp_arm)
    animate_root(ref_root, [(1, ref_pos), (frames, ref_pos)], yaw_ref)
    animate_root(sp_root, [(1, sp_pos), (frames, sp_pos)], yaw_sp)
    add_nla_loop(ref_arm, "idle", 1, frames)
    add_nla_loop(sp_arm, "idle", 1, frames)

    f_raise_end = 90
    # Spain calm until card fully up, then angry
    def spain_react(frame: int):
        if frame < f_raise_end + 8:
            t = frame / FPS
            return {
                "spine_01": (0.01, 0.0, 0.02 * math.sin(t * 1.2)),
                "spine_02": (0.02, 0.0, 0.03 * math.sin(t * 1.4)),
                "neck_01": (0.02, 0.0, 0.04 * math.sin(t * 1.5)),
                "head": (0.03, 0.0, 0.05 * math.sin(t * 1.6)),
            }
        return _protest_deltas(frame)

    add_talk_strip(sp_arm, "Spain_CardReact", frames, spain_react, TALK_BONES, step=3)

    card_m = mat_rgba("Card_YellowMat", (0.95, 0.85, 0.08, 1.0), 0.4)
    # card in referee's raised hand zone (toward Spain / +X)
    card = add_box("Card_Yellow", (0.2, 0.025, 0.32), Vector((ref_pos.x + 0.55, ref_pos.y - 0.15, 1.6)), card_m)
    f_raise = 30
    for f in range(1, frames + 1, 2):
        if f < f_raise:
            z = 1.6
            y = ref_pos.y - 0.15
        else:
            t = min(1.0, (f - f_raise) / max(1, f_raise_end - f_raise))
            z = 1.6 + 2.4 * ease(t)
            y = ref_pos.y - 0.15
        card.location = Vector((ref_pos.x + 0.5, y, z))
        card.keyframe_insert(data_path="location", frame=f)
    force_linear(card)

    cam = setup_new_cam("CamCut16", lens=40)

    def cam_pos(f: int) -> Vector:
        return Vector((0.0, -7.5, 3.5))

    def cam_tgt(f: int) -> Vector:
        if f < f_raise_end:
            return Vector((ref_pos.x + 0.3, 0.0, 3.2))
        return Vector((0.2, 0.0, 3.1))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 17 Shaolin long shot from ~halfway; Spain GK jump_full dive late; ball in
# ---------------------------------------------------------------------------
def build_17() -> int:
    remove_players()
    _show_pitch()
    frames = 360
    gx = goal_r_x()
    yaw = yaw_face_pos_x()
    yaw_gk = yaw_face_neg_x()
    shin_start = Vector((0.0, -0.5, 0.0))  # halfway
    shin_kick = Vector((2.0, -0.35, 0.0))
    gk_home = Vector((gx - 3.2, 0.0, 0.0))
    ball_goal = Vector((gx + 1.6, -GOAL_INNER_HALF_W * 0.72, GOAL_H * 0.68))
    f_approach, f_kick, f_dive, f_goal = 96, 128, 138, 168

    arm, root = spawn_player("Shaolin", SHAOLIN_ORANGE, shin_start, yaw, actions=["run", "fight_kick", "idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42))
    gk_arm, gk_root = spawn_player("Spain_GK", SPAIN_YELLOW, gk_home, yaw_gk, actions=["fight_idle", "jump_full", "idle"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42))
    _clear_all_nla(arm)
    _clear_all_nla(gk_arm)

    def shin_path(f: int) -> Vector:
        if f <= f_approach:
            t = ease((f - 1) / max(1, f_approach - 1))
            p = shin_start.lerp(shin_kick, t)
            p.y += 0.3 * math.sin(t * 4.0 * math.pi)
            return p
        if f <= f_kick:
            t = (f - f_approach) / max(1, f_kick - f_approach)
            return shin_kick + Vector((0.5 * ease(t), -0.1 * t, 0.0))
        base = shin_kick + Vector((0.5, -0.1, 0.0))
        t = (f - f_kick) / max(1, frames - f_kick)
        return base + Vector((1.0 * ease(min(1.0, t * 1.5)), 0.08 * t, 0.0))

    dive_target = Vector((gx - 2.0, ball_goal.y * 0.88, 0.0))

    def gk_path(f: int) -> Vector:
        if f < f_dive:
            t = (f - 1) / max(1, f_dive - 1)
            return gk_home + Vector((0.0, ball_goal.y * 0.15 * ease(t), 0.0))
        if f <= f_goal + 4:
            t = (f - f_dive) / max(1, (f_goal + 4) - f_dive)
            p = gk_home.lerp(dive_target, ease(min(1.0, t * 1.15)))
            p.z = 0.75 * math.sin(min(1.0, t) * math.pi)
            return p
        t = (f - (f_goal + 4)) / max(1, frames - (f_goal + 4))
        land = dive_target + Vector((-0.2, -0.4, 0.0))
        p = dive_target.lerp(land, ease(min(1.0, t)))
        p.z = max(0.0, 0.25 * (1.0 - ease(min(1.0, t * 1.6))))
        return p

    keys_s = [(f, shin_path(f)) for f in range(1, frames + 1, 2)] + [(frames, shin_path(frames))]
    keys_g = [(f, gk_path(f)) for f in range(1, frames + 1, 2)] + [(frames, gk_path(frames))]
    animate_root(root, keys_s, yaw)
    animate_root(gk_root, keys_g, yaw_gk)
    add_nla_loop(arm, "run", 1, f_approach)
    add_nla_once(arm, "fight_kick", f_approach + 1, f_kick + 16)
    add_nla_hold(arm, "idle", f_kick + 17, frames, af=8)
    add_nla_hold(gk_arm, "fight_idle", 1, f_dive - 4, af=10)
    add_nla_once(gk_arm, "jump_full", f_dive - 2, f_goal + 8)
    add_nla_hold(gk_arm, "fight_idle", f_goal + 9, frames, af=10)

    ball = clear_ball_anim()
    move = Vector((1.0, 0.0, 0.0))

    def ball_path(f: int) -> Vector:
        shin = shin_path(f)
        if f < f_kick:
            return ball_ahead_of(shin, move, f, arm=arm)
        t = min(1.0, (f - f_kick) / max(1, f_goal - f_kick))
        u = 1.0 - (1.0 - t) ** 2.6
        start_b = ball_ahead_of(shin_path(f_kick - 1), move, f_kick - 1, arm=arm)
        p = start_b.lerp(ball_goal, u)
        p.z = BALL_GROUND_Z + (ball_goal.z - BALL_GROUND_Z) * u + 1.2 * math.sin(u * math.pi) * (1.0 - 0.4 * u)
        if f > f_goal:
            t2 = (f - f_goal) / max(1, frames - f_goal)
            p = ball_goal + Vector((0.8 * ease(min(1.0, t2)), 0.1 * t2, -0.5 * ease(min(1.0, t2))))
            p.z = max(BALL_GROUND_Z + 0.35, p.z)
        return p

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut17", lens=28)

    def cam_pos(f: int) -> Vector:
        b = ball_path(f)
        s = shin_path(f)
        if f < f_kick - 8:
            return Vector((s.x - 4.5, s.y - 10.0, 3.8))
        if f < f_goal:
            mid = (b + gk_path(f)) * 0.5
            return Vector((mid.x - 8.0, mid.y - 12.0, 5.0))
        return Vector((gx - 16.0, -11.0, 5.2))

    def cam_tgt(f: int) -> Vector:
        b = ball_path(f)
        if f < f_kick:
            s = shin_path(f)
            return Vector((s.x + 4.0, s.y * 0.3, 1.4))
        return Vector((b.x + 1.0, b.y * 0.35, max(1.2, b.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


BUILDERS: Dict[str, Callable[[], int]] = {
    "09": build_09,
    "10": build_10,
    "11": build_11,
    "12": build_12,
    "13": build_13,
    "14": build_14,
    "15": build_15,
    "16": build_16,
    "17": build_17,
}
