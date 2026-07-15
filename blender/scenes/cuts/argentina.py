# SPDX-License-Identifier: MIT
"""Argentina block cuts 29–37 — attack Goal_L."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

import bpy
from mathutils import Vector

from animate_soccer_match import BALL_GROUND_Z, _clear_all_nla  # noqa: E402

from cuts.common import (  # noqa: E402
    ARG_LIGHT,
    ARG_WHITE,
    FPS,
    GOAL_H,
    GOAL_INNER_HALF_W,
    SHAOLIN_ORANGE,
    SHAOLIN_WHITE,
    SIDE_GAP,
    TALK_BONES,
    add_box,
    add_nla_hold,
    add_nla_loop,
    add_nla_once,
    add_talk_strip,
    animate_gk_dive,
    animate_root,
    attach_long_hair,
    ball_ahead_of,
    clear_ball_anim,
    ease,
    finish_cam,
    force_linear,
    goal_l_x,
    hide_ball,
    key_ball,
    kf_cam,
    mat_rgba,
    remove_players,
    set_frame_range,
    setup_new_cam,
    spawn_player,
    yaw_face_neg_x,
    yaw_face_neg_y,
    yaw_face_pos_x,
)

GOAL_X = goal_l_x()
ATTACK_DIR = Vector((-1.0, 0.0, 0.0))
ATTACK_YAW = yaw_face_neg_x()
# Penalty spot ~11m from Goal_L
PEN_X = GOAL_X + 11.0 * 2.5  # toward field from goal line
GK_HOME = Vector((GOAL_X + 3.5, 0.0, 0.0))
GK_YAW = yaw_face_pos_x()


def _lerp(a: Vector, b: Vector, t: float) -> Vector:
    return a.lerp(b, t)


def _show_pitch() -> None:
    for obj in list(bpy.data.objects):
        if obj.name == "Ball" or obj.name.startswith(
            ("Field_", "Line_", "Pen", "Goal", "Corner_", "Net", "Post", "Crossbar")
        ):
            obj.hide_render = False
            obj.hide_viewport = False


def _cam_dense(
    cam: bpy.types.Object,
    f0: int,
    f1: int,
    pos0: Vector,
    pos1: Vector,
    tgt0: Vector,
    tgt1: Vector,
    step: int = 2,
) -> None:
    for f in range(f0, f1 + 1, step):
        t = ease((f - f0) / max(1, f1 - f0))
        kf_cam(cam, f, _lerp(pos0, pos1, t), _lerp(tgt0, tgt1, t))
    if (f1 - f0) % step != 0 or f1 == f0:
        kf_cam(cam, f1, pos1, tgt1)


def _clear_extras(*prefixes: str) -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def _shot_arc(p0: Vector, p1: Vector, u: float, arc: float = 2.2) -> Vector:
    p = _lerp(p0, p1, u)
    p.z = p0.z + (p1.z - p0.z) * u + arc * math.sin(u * math.pi) * (1.0 - 0.35 * u)
    return p


def _hide_pitch_studio(keep: Tuple[str, ...]) -> None:
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


def _interview_set(primary, accent) -> None:
    _clear_extras("Interview_")
    floor = mat_rgba("Interview_FloorMat", (0.12, 0.12, 0.14, 1.0), 0.9)
    podium = mat_rgba("Interview_PodiumMat", (0.18, 0.18, 0.2, 1.0), 0.55)
    back = mat_rgba("Interview_BackMat", (0.07, 0.1, 0.14, 1.0), 0.85)
    stripe = mat_rgba("Interview_StripeMat", primary, 0.45)
    acc = mat_rgba("Interview_AccentMat", accent, 0.45)
    panel = mat_rgba("Interview_PanelMat", (0.16, 0.18, 0.22, 1.0), 0.7)
    add_box("Interview_Floor", (7.0, 5.0, 0.1), Vector((0.0, 0.6, 0.05)), floor)
    add_box("Interview_Podium", (2.0, 1.5, 0.35), Vector((0.0, 0.0, 0.175)), podium)
    add_box("Interview_Backdrop", (8.0, 0.12, 5.4), Vector((0.0, 2.4, 2.7)), back)
    add_box("Interview_Banner", (7.6, 0.14, 0.55), Vector((0.0, 2.28, 4.55)), stripe)
    add_box("Interview_Accent", (7.6, 0.14, 0.28), Vector((0.0, 2.28, 0.85)), acc)
    add_box("Interview_LogoL", (1.6, 0.08, 1.6), Vector((-2.3, 2.26, 2.5)), panel)
    add_box("Interview_LogoR", (1.6, 0.08, 1.6), Vector((2.3, 2.26, 2.5)), panel)


def _talk_fn(amp: float = 1.0) -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS
        nod = amp * (0.07 * math.sin(t * 6.8) + 0.04 * math.sin(t * 10.5))
        turn = amp * (0.1 * math.sin(t * 2.2 + 0.3) + 0.05 * math.sin(t * 4.7))
        lean = amp * 0.05 * math.sin(t * 1.6)
        return {
            "spine_01": (0.025 + lean * 0.4, 0.0, turn * 0.25),
            "spine_02": (0.045 + lean, 0.0, turn * 0.4),
            "neck_01": (0.04 + nod * 0.65, 0.0, turn * 0.75),
            "head": (0.05 + nod, 0.0, turn),
        }

    return deltas


def _sad_fn(base_down: float = 0.18) -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS
        nod = 0.025 * math.sin(t * 2.0)
        down = base_down + 0.03 * math.sin(t * 0.6)
        return {
            "spine_01": (0.05 + down * 0.2, 0.0, 0.0),
            "spine_02": (0.07 + down * 0.3, 0.0, 0.0),
            "neck_01": (0.06 + nod + down * 0.55, 0.0, 0.0),
            "head": (0.07 + nod + down * 0.8, 0.0, 0.02 * math.sin(t * 1.1)),
        }

    return deltas


def _mutter_fn() -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS
        nod = 0.05 * math.sin(t * 5.5) + 0.03 * math.sin(t * 9.0)
        turn = 0.06 * math.sin(t * 1.8)
        return {
            "spine_01": (0.02, 0.0, turn * 0.2),
            "spine_02": (0.035, 0.0, turn * 0.35),
            "neck_01": (0.035 + nod * 0.6, 0.0, turn * 0.7),
            "head": (0.04 + nod, 0.0, turn),
        }

    return deltas


# ---------------------------------------------------------------------------
# 29 — middle equalizer 2-2; Arg GK sideways dive
# ---------------------------------------------------------------------------
def build_29() -> int:
    frames = 144
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    start = Vector((-35.0, 0.4, 0.0))
    kick = Vector((GOAL_X + 55.0, -0.3, 0.0))
    arm, root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, start, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    gk_arm, gk_root = spawn_player(
        "Argentina", ARG_LIGHT, GK_HOME, GK_YAW,
        actions=["fight_idle", "jump_full"], split=(ARG_LIGHT, ARG_WHITE, 0.42),
    )
    _clear_all_nla(gk_arm)
    keys = []
    for f in range(1, 90, 2):
        keys.append((f, _lerp(start, kick, ease((f - 1) / 88.0))))
    keys += [(90, kick), (frames, kick)]
    animate_root(root, keys, ATTACK_YAW)
    add_nla_loop(arm, "run", 1, 89)
    add_nla_once(arm, "fight_kick", 90, 112)
    add_nla_hold(arm, "fight_idle", 113, frames, af=6)

    ball = clear_ball_anim()
    goal = Vector((GOAL_X - 1.8, -GOAL_INNER_HALF_W * 0.72, GOAL_H * 0.68))
    animate_gk_dive(gk_root, gk_arm, GK_HOME, goal.y * 0.7, 100, 122, frames, GK_YAW, side=True)

    def path(f: int) -> Vector:
        if f < 90:
            loc = _lerp(start, kick, ease((f - 1) / 88.0))
            return ball_ahead_of(loc, ATTACK_DIR, f, arm=arm)
        if f <= 98:
            return ball_ahead_of(kick, ATTACK_DIR, f, arm=arm)
        u = ease((f - 98) / max(1, 116 - 98))
        return goal if f > 116 else _shot_arc(
            ball_ahead_of(kick, ATTACK_DIR, 98, arm=arm), goal, min(1.0, u * 1.15), arc=1.4
        )

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam29", lens=28)
    _cam_dense(
        cam, 1, 85,
        Vector((-20.0, -22.0, 6.5)), Vector((GOAL_X + 60.0, -18.0, 5.5)),
        Vector((-35.0, 0.4, 1.2)), Vector((GOAL_X + 50.0, 0.0, 1.3)),
        step=2,
    )
    _cam_dense(
        cam, 85, frames,
        Vector((GOAL_X + 60.0, -18.0, 5.5)), Vector((GOAL_X + 16.0, -12.0, 4.2)),
        Vector((GOAL_X + 50.0, 0.0, 1.3)), Vector((GOAL_X, -1.0, 2.2)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 30 — ET misses mashup with both GKs; some saves
# One file sequences 4 beats (cam hard-cuts): miss / miss / save / miss
# ---------------------------------------------------------------------------
def build_30() -> int:
    frames = 320
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    gap = SIDE_GAP
    sh_pos = Vector((-50.0, -gap * 0.5, 0.0))
    ar_pos = Vector((-55.0, gap * 0.5, 0.0))
    sh_kick1 = Vector((GOAL_X + 30.0, -gap * 0.5, 0.0))
    ar_kick = Vector((GOAL_X + 28.0, gap * 0.55, 0.0))
    sh_kick2 = Vector((GOAL_X + 32.0, -gap * 0.4, 0.0))
    ar_kick2 = Vector((GOAL_X + 30.0, gap * 0.35, 0.0))

    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, sh_pos, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(sh_arm)
    ar_arm, ar_root = spawn_player(
        "Argentina", ARG_LIGHT, ar_pos, ATTACK_YAW, actions=["run"], split=(ARG_LIGHT, ARG_WHITE, 0.42)
    )
    _clear_all_nla(ar_arm)
    # defending GKs in goal
    arg_gk_arm, arg_gk_root = spawn_player(
        "Argentina_GK", ARG_LIGHT, GK_HOME, GK_YAW,
        actions=["fight_idle", "jump_full"], split=(ARG_LIGHT, ARG_WHITE, 0.42),
    )
    _clear_all_nla(arg_gk_arm)
    sh_gk_arm, sh_gk_root = spawn_player(
        "Shaolin_GK", SHAOLIN_ORANGE, GK_HOME + Vector((0.0, SIDE_GAP * 1.4, 0.0)), GK_YAW,
        actions=["fight_idle", "jump_full"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(sh_gk_arm)

    park_sh = Vector((-40.0, -gap - 1.0, 0.0))
    park_ar = Vector((-42.0, gap + 1.0, 0.0))
    # A 1-80 Shaolin miss over; B 81-160 Arg wide; C 161-240 Shaolin SAVED; D 241-320 Arg miss
    sh_keys: List[Tuple[int, Vector]] = []
    for f in range(1, 60, 2):
        sh_keys.append((f, _lerp(sh_pos, sh_kick1, ease((f - 1) / 58.0))))
    sh_keys += [(60, sh_kick1), (80, sh_kick1), (81, park_sh), (160, park_sh)]
    for f in range(161, 210, 2):
        sh_keys.append((f, _lerp(Vector((-48.0, -gap * 0.4, 0.0)), sh_kick2, ease((f - 161) / 48.0))))
    sh_keys += [(210, sh_kick2), (240, sh_kick2), (241, park_sh), (frames, park_sh)]
    animate_root(sh_root, sh_keys, ATTACK_YAW)

    ar_keys: List[Tuple[int, Vector]] = []
    ar_keys += [(1, park_ar), (80, park_ar)]
    for f in range(81, 130, 2):
        ar_keys.append((f, _lerp(ar_pos, ar_kick, ease((f - 81) / 48.0))))
    ar_keys += [(130, ar_kick), (160, ar_kick)]
    ar_keys += [(161, park_ar), (240, park_ar)]
    for f in range(241, 290, 2):
        ar_keys.append((f, _lerp(Vector((-50.0, gap * 0.4, 0.0)), ar_kick2, ease((f - 241) / 48.0))))
    ar_keys += [(290, ar_kick2), (frames, ar_kick2)]
    animate_root(ar_root, ar_keys, ATTACK_YAW)

    # Arg GK active on Shaolin shots (A,C); Shaolin GK on Arg shots (B,D)
    animate_root(arg_gk_root, [(1, GK_HOME), (160, GK_HOME), (161, GK_HOME), (240, GK_HOME), (241, GK_HOME + Vector((0, 8, 0))), (frames, GK_HOME + Vector((0, 8, 0)))], GK_YAW)
    animate_root(sh_gk_root, [(1, GK_HOME + Vector((0, 8, 0))), (80, GK_HOME + Vector((0, 8, 0))), (81, GK_HOME), (160, GK_HOME), (161, GK_HOME + Vector((0, 8, 0))), (240, GK_HOME + Vector((0, 8, 0))), (241, GK_HOME), (frames, GK_HOME)], GK_YAW)

    add_nla_loop(sh_arm, "run", 1, 59)
    add_nla_once(sh_arm, "fight_kick", 60, 78)
    add_nla_hold(sh_arm, "idle", 79, 160, af=10)
    add_nla_loop(sh_arm, "run", 161, 209)
    add_nla_once(sh_arm, "fight_kick", 210, 228)
    add_nla_hold(sh_arm, "idle", 229, frames, af=10)

    add_nla_hold(ar_arm, "idle", 1, 80, af=10)
    add_nla_loop(ar_arm, "run", 81, 129)
    add_nla_once(ar_arm, "fight_kick", 130, 148)
    add_nla_hold(ar_arm, "idle", 149, 240, af=10)
    add_nla_loop(ar_arm, "run", 241, 289)
    add_nla_once(ar_arm, "fight_kick", 290, 308)
    add_nla_hold(ar_arm, "idle", 309, frames, af=10)

    # GK animations: A miss dive, B miss dive, C SAVE dive, D miss dive
    add_nla_hold(arg_gk_arm, "fight_idle", 1, 55, af=10)
    add_nla_once(arg_gk_arm, "jump_full", 56, 78)
    add_nla_hold(arg_gk_arm, "fight_idle", 79, 200, af=8)
    add_nla_once(arg_gk_arm, "jump_full", 201, 230)  # save
    add_nla_hold(arg_gk_arm, "fight_idle", 231, frames, af=8)

    add_nla_hold(sh_gk_arm, "fight_idle", 1, 120, af=10)
    add_nla_once(sh_gk_arm, "jump_full", 121, 150)
    add_nla_hold(sh_gk_arm, "fight_idle", 151, 285, af=8)
    add_nla_once(sh_gk_arm, "jump_full", 286, 312)
    add_nla_hold(sh_gk_arm, "fight_idle", 313, frames, af=8)

    # dive root offsets during saves/misses
    def gk_dive_keys(home, dive_y, f0, f1, rise=0.9):
        keys = [(1, home)]
        for f in range(f0, f1 + 1, 2):
            t = (f - f0) / max(1, f1 - f0)
            p = home + Vector((0.5, dive_y * ease(t), rise * math.sin(min(1.0, t) * math.pi)))
            keys.append((f, p))
        keys.append((frames, home + Vector((0.5, dive_y, 0.0))))
        return keys

    # Only apply extra motion via overlapping keyframes on arg_gk during A and C
    arg_keys = [(1, GK_HOME)]
    for f in range(56, 80, 2):
        t = (f - 56) / 24.0
        arg_keys.append((f, GK_HOME + Vector((0.4, -3.5 * ease(t), 0.85 * math.sin(min(1, t) * math.pi)))))
    arg_keys += [(80, GK_HOME + Vector((0.4, -3.5, 0.0))), (160, GK_HOME)]
    for f in range(201, 235, 2):
        t = (f - 201) / 34.0
        # save: dive farther into ball path
        arg_keys.append((f, GK_HOME + Vector((0.8, -5.0 * ease(t), 1.0 * math.sin(min(1, t) * math.pi)))))
    arg_keys += [(240, GK_HOME + Vector((0.8, -5.0, 0.0))), (241, GK_HOME + Vector((0, 8, 0))), (frames, GK_HOME + Vector((0, 8, 0)))]
    animate_root(arg_gk_root, arg_keys, GK_YAW)

    shgk_keys = [(1, GK_HOME + Vector((0, 8, 0))), (80, GK_HOME + Vector((0, 8, 0)))]
    for f in range(121, 160, 2):
        t = (f - 121) / 39.0
        shgk_keys.append((f, GK_HOME + Vector((0.5, 4.0 * ease(t), 0.9 * math.sin(min(1, t) * math.pi)))))
    shgk_keys += [(160, GK_HOME + Vector((0.5, 4.0, 0.0))), (161, GK_HOME + Vector((0, 8, 0))), (240, GK_HOME + Vector((0, 8, 0)))]
    for f in range(286, 320, 2):
        t = (f - 286) / 34.0
        shgk_keys.append((f, GK_HOME + Vector((0.5, -4.2 * ease(t), 0.85 * math.sin(min(1, t) * math.pi)))))
    shgk_keys.append((frames, GK_HOME + Vector((0.5, -4.2, 0.0))))
    animate_root(sh_gk_root, shgk_keys, GK_YAW)

    ball = clear_ball_anim()
    over = Vector((GOAL_X - 4.0, 0.5, GOAL_H + 4.5))
    wide = Vector((GOAL_X - 2.0, GOAL_INNER_HALF_W + 6.0, GOAL_H * 0.4))
    saved = Vector((GOAL_X + 16.0, -10.0, BALL_GROUND_Z + 0.5))  # punched away
    toward_save = Vector((GOAL_X + 2.0, -4.0, GOAL_H * 0.5))
    miss4 = Vector((GOAL_X - 3.0, -GOAL_INNER_HALF_W - 5.5, GOAL_H * 0.9))

    def path(f: int) -> Vector:
        if f <= 60:
            loc = _lerp(sh_pos, sh_kick1, ease((f - 1) / 58.0))
            return ball_ahead_of(loc, ATTACK_DIR, f, arm=sh_arm)
        if f <= 80:
            return _shot_arc(ball_ahead_of(sh_kick1, ATTACK_DIR, 60, arm=sh_arm), over, ease((f - 60) / 20.0), 5.5)
        if f <= 130:
            loc = _lerp(ar_pos, ar_kick, ease((f - 81) / 48.0) if f >= 81 else 0.0)
            return ball_ahead_of(loc if f >= 81 else ar_kick, ATTACK_DIR, f, arm=ar_arm)
        if f <= 160:
            return _shot_arc(ball_ahead_of(ar_kick, ATTACK_DIR, 130, arm=ar_arm), wide, ease((f - 130) / 30.0), 2.0)
        if f <= 210:
            loc = _lerp(Vector((-48.0, -gap * 0.4, 0.0)), sh_kick2, ease((f - 161) / 48.0) if f >= 161 else 0.0)
            return ball_ahead_of(loc if f >= 161 else sh_kick2, ATTACK_DIR, f, arm=sh_arm)
        if f <= 220:
            return _shot_arc(ball_ahead_of(sh_kick2, ATTACK_DIR, 210, arm=sh_arm), toward_save, ease((f - 210) / 10.0), 2.0)
        if f <= 240:
            return _shot_arc(toward_save, saved, ease((f - 220) / 20.0), 1.0)
        if f <= 290:
            loc = _lerp(Vector((-50.0, gap * 0.4, 0.0)), ar_kick2, ease((f - 241) / 48.0) if f >= 241 else 0.0)
            return ball_ahead_of(loc if f >= 241 else ar_kick2, ATTACK_DIR, f, arm=ar_arm)
        return _shot_arc(ball_ahead_of(ar_kick2, ATTACK_DIR, 290, arm=ar_arm), miss4, ease((f - 290) / max(1, frames - 290)), 3.0)

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam30", lens=28)
    _cam_dense(cam, 1, 80, Vector((-35.0, -18.0, 5.5)), Vector((GOAL_X + 25.0, -14.0, 5.0)), Vector((-50.0, -1.5, 1.2)), Vector((GOAL_X + 10.0, 0.0, 2.5)), step=2)
    _cam_dense(cam, 81, 160, Vector((-30.0, 16.0, 5.5)), Vector((GOAL_X + 22.0, 12.0, 4.8)), Vector((-50.0, 2.0, 1.2)), Vector((GOAL_X + 8.0, 4.0, 2.0)), step=2)
    _cam_dense(cam, 161, 240, Vector((-40.0, -16.0, 5.8)), Vector((GOAL_X + 20.0, -12.0, 5.0)), Vector((-48.0, -1.5, 1.2)), Vector((GOAL_X, -3.0, 2.0)), step=2)
    _cam_dense(cam, 241, frames, Vector((-35.0, 14.0, 5.5)), Vector((GOAL_X + 18.0, 10.0, 4.8)), Vector((-48.0, 2.0, 1.2)), Vector((GOAL_X, -2.0, 2.2)), step=2)
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 31 — PK alternating; GKs dive sideways sometimes
# ---------------------------------------------------------------------------
def build_31() -> int:
    n_pks = 5
    seg = 72
    frames = n_pks * seg
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    _clear_extras("Card_")

    spot = Vector((PEN_X, 0.0, 0.0))
    mark_mat = mat_rgba("PK_MarkMat", (0.95, 0.95, 0.9, 1.0), 0.8)
    add_box("Card_PKSpot", (0.6, 0.6, 0.04), Vector((PEN_X, 0.0, 0.02)), mark_mat)

    teams = ["SHAOLIN", "ARGENTINA", "SHAOLIN", "ARGENTINA", "SHAOLIN"]
    kickers = []
    gks = []
    for i, team in enumerate(teams):
        if team == "SHAOLIN":
            col, split, prefix = SHAOLIN_ORANGE, (SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42), f"Shaolin_{i}"
            gk_col, gk_split, gk_pref = ARG_LIGHT, (ARG_LIGHT, ARG_WHITE, 0.42), f"Argentina_{i}"
        else:
            col, split, prefix = ARG_LIGHT, (ARG_LIGHT, ARG_WHITE, 0.42), f"Argentina_{i}"
            gk_col, gk_split, gk_pref = SHAOLIN_ORANGE, (SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42), f"Shaolin_{i}"
        park = Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0, 0.0))
        k_arm, k_root = spawn_player(prefix, col, park, ATTACK_YAW, actions=["idle"], split=split)
        _clear_all_nla(k_arm)
        g_arm, g_root = spawn_player(gk_pref + "GK", gk_col, park + Vector((0, SIDE_GAP, 0)), GK_YAW, actions=["idle"], split=gk_split)
        _clear_all_nla(g_arm)
        kickers.append((k_arm, k_root, team))
        gks.append((g_arm, g_root))

    ball = clear_ball_anim()
    ball_keys_fn_segments: List[Tuple[int, int, Callable]] = []

    for i, ((k_arm, k_root, team), (g_arm, g_root)) in enumerate(zip(kickers, gks)):
        f0 = i * seg + 1
        f1 = (i + 1) * seg
        kick_f = f0 + 28
        land_f = f0 + 48
        corner_y = (-1 if i % 2 == 0 else 1) * GOAL_INNER_HALF_W * 0.65
        goal = Vector((GOAL_X - 1.5, corner_y, GOAL_H * (0.45 + 0.08 * (i % 3))))
        active_spot = spot + Vector((0.0, (i - 2) * 0.15, 0.0))
        side_dive = (i % 2 == 0)  # alternate up vs sideways

        animate_root(
            k_root,
            [
                (1, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0, 0.0))),
                (f0 - 1 if f0 > 1 else 1, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0, 0.0))),
                (f0, active_spot),
                (f1, active_spot),
                (f1 + 1 if f1 < frames else frames, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0, 0.0))),
                (frames, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0, 0.0))),
            ],
            ATTACK_YAW,
        )
        dive_y = corner_y * 0.55 if side_dive else 0.0
        dive_pos = GK_HOME + Vector((0.6 if side_dive else 0.2, dive_y, 0.0))
        gk_keys = [
            (1, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0 + SIDE_GAP, 0.0))),
            (f0 - 1 if f0 > 1 else 1, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0 + SIDE_GAP, 0.0))),
            (f0, GK_HOME),
            (land_f - 8, GK_HOME),
        ]
        for f in range(land_f - 6, land_f + 12, 2):
            t = (f - (land_f - 6)) / 18.0
            p = GK_HOME.lerp(dive_pos, ease(min(1.0, t)))
            p.z = (0.95 if side_dive else 1.35) * math.sin(min(1.0, t) * math.pi)
            gk_keys.append((f, p))
        gk_keys += [
            (f1, dive_pos),
            (f1 + 1 if f1 < frames else frames, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0 + SIDE_GAP, 0.0))),
            (frames, Vector((40.0 + i * SIDE_GAP, 30.0 + i * 2.0 + SIDE_GAP, 0.0))),
        ]
        animate_root(g_root, gk_keys, GK_YAW)
        add_nla_hold(k_arm, "idle", 1, kick_f - 1, af=10)
        add_nla_once(k_arm, "fight_kick", kick_f, kick_f + 22)
        add_nla_hold(k_arm, "fight_idle", kick_f + 23, frames, af=5)
        add_nla_loop(g_arm, "idle", 1, land_f - 5)
        add_nla_once(g_arm, "jump_full", land_f - 4, land_f + 16)
        add_nla_hold(g_arm, "fight_idle", land_f + 17, frames, af=4)

        start_ball = ball_ahead_of(active_spot, ATTACK_DIR, kick_f, arm=k_arm)

        def make_seg(kf=kick_f, lf=land_f, sb=start_ball, gl=goal, a0=f0, a1=f1):
            def seg_path(f: int) -> Optional[Vector]:
                if f < a0 or f > a1:
                    return None
                if f < kf:
                    return Vector((sb.x, sb.y, BALL_GROUND_Z))
                if f <= lf:
                    u = ease((f - kf) / max(1, lf - kf))
                    return _shot_arc(sb, gl, u, 2.4)
                return gl

            return seg_path

        ball_keys_fn_segments.append((f0, f1, make_seg()))

    def path(f: int) -> Vector:
        for a0, a1, fn in ball_keys_fn_segments:
            if a0 <= f <= a1:
                r = fn(f)
                if r is not None:
                    return r
        return Vector((PEN_X - 1.6, 0.0, BALL_GROUND_Z))

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam31", lens=30)
    for i in range(n_pks):
        f0 = i * seg + 1
        f1 = (i + 1) * seg
        _cam_dense(
            cam, f0, f1,
            Vector((PEN_X + 12.0, -14.0, 4.5)), Vector((GOAL_X + 18.0, -10.0, 4.0)),
            Vector((PEN_X, 0.0, 1.2)), Vector((GOAL_X, 0.0, 2.0)),
            step=2,
        )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 32 — Female GK enter (Shaolin kit + long hair, no crowd)
# ---------------------------------------------------------------------------
def build_32() -> int:
    frames = 132
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    start = Vector((-20.0, -18.0, 0.0))
    end = GK_HOME.copy()
    arm, root = spawn_player(
        "FemaleGK",
        SHAOLIN_ORANGE,
        start,
        ATTACK_YAW,
        actions=["run"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
        scale=2.2,
    )
    _clear_all_nla(arm)
    attach_long_hair(arm)
    keys = []
    for f in range(1, frames + 1, 2):
        t = ease((f - 1) / max(1, frames - 1))
        keys.append((f, _lerp(start, end, t)))
    animate_root(root, keys, ATTACK_YAW)
    add_nla_loop(arm, "run", 1, 110)
    add_nla_hold(arm, "idle", 111, frames, af=10)

    cam = setup_new_cam("Cam32", lens=28)
    _cam_dense(
        cam, 1, frames,
        Vector((-10.0, -22.0, 5.0)), Vector((GOAL_X + 25.0, -14.0, 4.5)),
        Vector((-15.0, -10.0, 1.5)), Vector((GOAL_X + 5.0, 0.0, 1.8)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 33 — Arg PK, Female GK (Shaolin kit + long hair) SAVE
# ---------------------------------------------------------------------------
def build_33() -> int:
    frames = 120
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    spot = Vector((PEN_X, 1.0, 0.0))
    ar_arm, ar_root = spawn_player(
        "Argentina", ARG_LIGHT, spot, ATTACK_YAW, actions=["idle"], split=(ARG_LIGHT, ARG_WHITE, 0.42)
    )
    _clear_all_nla(ar_arm)
    gk_arm, gk_root = spawn_player(
        "FemaleGK",
        SHAOLIN_ORANGE,
        GK_HOME,
        GK_YAW,
        actions=["idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
        scale=2.2,
    )
    _clear_all_nla(gk_arm)
    attach_long_hair(gk_arm)
    animate_root(ar_root, [(1, spot), (frames, spot)], ATTACK_YAW)
    dive_pos = GK_HOME + Vector((1.0, -4.5, 0.0))
    animate_root(
        gk_root,
        [(1, GK_HOME), (55, GK_HOME), (72, dive_pos), (frames, dive_pos)],
        GK_YAW,
    )
    add_nla_hold(ar_arm, "idle", 1, 40, af=10)
    add_nla_once(ar_arm, "fight_kick", 41, 63)
    add_nla_hold(ar_arm, "fight_idle", 64, frames, af=5)
    add_nla_loop(gk_arm, "idle", 1, 52)
    add_nla_once(gk_arm, "jump_full", 53, 85)
    add_nla_hold(gk_arm, "fight_idle", 86, frames, af=4)

    ball = clear_ball_anim()
    toward = Vector((GOAL_X + 2.0, -3.5, GOAL_H * 0.45))
    deflect = Vector((GOAL_X + 18.0, -12.0, BALL_GROUND_Z + 0.4))
    start_b = ball_ahead_of(spot, ATTACK_DIR, 41, arm=ar_arm)

    def path(f: int) -> Vector:
        if f < 41:
            return Vector((start_b.x, start_b.y, BALL_GROUND_Z))
        if f <= 60:
            u = ease((f - 41) / 19.0)
            return _shot_arc(start_b, toward, u, 2.0)
        u = ease((f - 60) / max(1, 90 - 60))
        return deflect if f > 90 else _shot_arc(toward, deflect, u, 1.2)

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam33", lens=30)
    _cam_dense(
        cam, 1, frames,
        Vector((PEN_X + 10.0, -12.0, 4.2)), Vector((GOAL_X + 14.0, -10.0, 3.8)),
        Vector((PEN_X, 0.5, 1.2)), Vector((GOAL_X + 5.0, -4.0, 1.5)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 34 — Female GK mutter (Shaolin kit + long hair)
# ---------------------------------------------------------------------------
def build_34() -> int:
    frames = 120
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    pos = GK_HOME + Vector((2.0, 0.0, 0.0))
    arm, root = spawn_player(
        "FemaleGK",
        SHAOLIN_ORANGE,
        pos,
        yaw_face_neg_y(),
        actions=["idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
        scale=2.2,
    )
    _clear_all_nla(arm)
    attach_long_hair(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_loop(arm, "idle", 1, frames)
    add_talk_strip(arm, "FemaleGKMutter", frames, _mutter_fn(), TALK_BONES, step=2)

    cam = setup_new_cam("Cam34", lens=38)
    _cam_dense(
        cam, 1, frames,
        Vector((pos.x - 0.4, pos.y - 6.5, 3.5)), Vector((pos.x - 0.2, pos.y - 5.8, 3.55)),
        Vector((pos.x, pos.y, 3.15)), Vector((pos.x, pos.y + 0.05, 3.2)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 35 — Shaolin winning PK; GK in Argentina kit (else unchanged)
# ---------------------------------------------------------------------------
def build_35() -> int:
    frames = 120
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    spot = Vector((PEN_X, -0.5, 0.0))
    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, spot, ATTACK_YAW, actions=["idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(sh_arm)
    gk_arm, gk_root = spawn_player(
        "Argentina_GK",
        ARG_LIGHT,
        GK_HOME,
        GK_YAW,
        actions=["idle"],
        split=(ARG_LIGHT, ARG_WHITE, 0.42),
        scale=2.2,
    )
    _clear_all_nla(gk_arm)
    animate_root(sh_root, [(1, spot), (frames, spot)], ATTACK_YAW)
    miss_dive = GK_HOME + Vector((0.8, 5.5, 0.0))
    animate_root(
        gk_root,
        [(1, GK_HOME), (55, GK_HOME), (75, miss_dive), (frames, miss_dive)],
        GK_YAW,
    )
    add_nla_hold(sh_arm, "idle", 1, 40, af=10)
    add_nla_once(sh_arm, "fight_kick", 41, 63)
    add_nla_hold(sh_arm, "fight_idle", 64, frames, af=5)
    add_nla_loop(gk_arm, "idle", 1, 52)
    add_nla_once(gk_arm, "jump_full", 53, 85)
    add_nla_hold(gk_arm, "fight_idle", 86, frames, af=4)

    ball = clear_ball_anim()
    corner = Vector((GOAL_X - 1.6, -GOAL_INNER_HALF_W * 0.78, GOAL_H * 0.55))
    start_b = ball_ahead_of(spot, ATTACK_DIR, 41, arm=sh_arm)

    def path(f: int) -> Vector:
        if f < 41:
            return Vector((start_b.x, start_b.y, BALL_GROUND_Z))
        if f <= 62:
            u = ease((f - 41) / 21.0)
            return _shot_arc(start_b, corner, u, 2.2)
        return corner

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam35", lens=30)
    _cam_dense(
        cam, 1, frames,
        Vector((PEN_X + 11.0, -13.0, 4.3)), Vector((GOAL_X + 15.0, -9.0, 3.9)),
        Vector((PEN_X, -0.3, 1.2)), Vector((GOAL_X, -2.0, 2.0)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 36 — ceremony
# ---------------------------------------------------------------------------
def build_36() -> int:
    frames = 120
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    gap = SIDE_GAP
    # optional podium
    podium_mat = mat_rgba("Interview_PodiumMat", (0.2, 0.2, 0.22, 1.0), 0.55)
    add_box("Interview_Podium", (6.0, 2.2, 0.3), Vector((0.0, 0.0, 0.15)), podium_mat)

    ar_pos = Vector((-gap * 1.2, 0.0, 0.3))
    sh1 = Vector((gap * 0.4, -0.4, 0.3))
    sh2 = Vector((gap * 0.4 + gap, 0.4, 0.3))
    # Shaolin face each other
    yaw_sh1 = math.pi * 0.5  # +X toward partner
    yaw_sh2 = math.pi * 1.5  # -X toward partner

    ar_arm, ar_root = spawn_player(
        "Argentina", ARG_LIGHT, ar_pos, yaw_face_neg_y(), actions=["idle"], split=(ARG_LIGHT, ARG_WHITE, 0.42)
    )

    _clear_all_nla(ar_arm)
    s1_arm, s1_root = spawn_player(
        "Shaolin_A", SHAOLIN_ORANGE, sh1, yaw_sh1, actions=["idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(s1_arm)
    s2_arm, s2_root = spawn_player(
        "Shaolin_B", SHAOLIN_ORANGE, sh2, yaw_sh2, actions=["idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(s2_arm)

    animate_root(ar_root, [(1, ar_pos), (frames, ar_pos)], yaw_face_neg_y())
    animate_root(s1_root, [(1, sh1), (frames, sh1)], yaw_sh1)
    animate_root(s2_root, [(1, sh2), (frames, sh2)], yaw_sh2)
    add_nla_loop(ar_arm, "idle", 1, frames)
    add_nla_loop(s1_arm, "idle", 1, frames)
    add_nla_loop(s2_arm, "idle", 1, frames)
    add_talk_strip(ar_arm, "ArgStunned", frames, _sad_fn(0.24), TALK_BONES, step=3)
    # mild happy/facing presence — head only, no arm weirdness
    add_talk_strip(s1_arm, "ShaolinCeremony1", frames, _talk_fn(0.45), TALK_BONES, step=3)
    add_talk_strip(s2_arm, "ShaolinCeremony2", frames, _talk_fn(0.45), TALK_BONES, step=3)

    cam = setup_new_cam("Cam36", lens=32)
    _cam_dense(
        cam, 1, frames,
        Vector((0.5, -11.0, 3.8)), Vector((0.8, -9.5, 3.5)),
        Vector((0.2, 0.0, 1.8)), Vector((0.4, 0.0, 1.85)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 37 — Shaolin podium interview
# ---------------------------------------------------------------------------
def build_37() -> int:
    frames = 144
    remove_players()
    set_frame_range(frames)
    hide_ball()
    _hide_pitch_studio(("Light", "Sun", "World", "Camera", "Cam", "Shaolin_", "Interview_"))
    _interview_set(SHAOLIN_ORANGE, SHAOLIN_WHITE)
    pos = Vector((0.0, 0.0, 0.35))
    arm, root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, pos, yaw_face_neg_y(), actions=["idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_loop(arm, "idle", 1, frames)
    add_talk_strip(arm, "ShaolinInterviewTalk", frames, _talk_fn(1.0), TALK_BONES, step=2)

    cam = setup_new_cam("Cam37", lens=35)
    _cam_dense(
        cam, 1, frames,
        Vector((-0.45, -7.0, 3.35)), Vector((-0.3, -6.5, 3.4)),
        Vector((0.05, 0.1, 3.05)), Vector((0.0, 0.1, 3.1)),
        step=3,
    )
    finish_cam(cam)
    return frames


BUILDERS = {
    "29": build_29,
    "30": build_30,
    "31": build_31,
    "32": build_32,
    "33": build_33,
    "34": build_34,
    "35": build_35,
    "36": build_36,
    "37": build_37,
}
