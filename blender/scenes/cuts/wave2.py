# SPDX-License-Identifier: MIT
"""Extra cuts 47–61 — toddle, cage, windmill chain, Arg saves/crowd, GK sub."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

import bpy
from mathutils import Euler, Vector

from animate_soccer_match import (  # noqa: E402
    BALL_GROUND_Z,
    _clear_all_nla,
)

from cuts.common import (  # noqa: E402
    ARG_LIGHT,
    ARG_WHITE,
    FPS,
    GOAL_H,
    NORWAY_RED,
    NORWAY_WHITE,
    SHAOLIN_ORANGE,
    SHAOLIN_WHITE,
    SPAIN_RED,
    SPAIN_YELLOW,
    TALK_BONES,
    add_box,
    add_nla_hold,
    add_nla_loop,
    add_nla_once,
    add_pose_strip,
    animate_root,
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
    spawn_france,
    spawn_player,
    yaw_face_neg_x,
    yaw_face_neg_y,
    yaw_face_pos_x,
)
from cuts.extras import (  # noqa: E402
    BREAK_BONES,
    _animate_root_euler,
    _cam_dense,
    _clear_extras,
    _lerp,
    _shot_arc,
    _show_pitch,
    _windmill_deltas,
)


def _belly_ball(player: Vector, facing: Vector, z_off: float = 2.2, ahead: float = 0.85) -> Vector:
    fd = facing.normalized()
    p = player + fd * ahead
    p.z = player.z + z_off
    return p


def _ball_arc(p0: Vector, p1: Vector, u: float, arc: float = 1.2) -> Vector:
    t = ease(max(0.0, min(1.0, u)))
    p = p0.lerp(p1, t)
    p.z = p0.z + (p1.z - p0.z) * t + arc * math.sin(t * math.pi)
    return p


def _head_hold_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    t = frame / FPS
    bob = 0.04 * math.sin(t * 4.0)
    return {
        "spine_01": (0.18 + bob * 0.2, 0.0, 0.0),
        "spine_02": (0.22 + bob * 0.3, 0.0, 0.0),
        "neck_01": (0.35 + bob, 0.0, 0.0),
        "head": (0.45 + bob, 0.0, 0.0),
        "clavicle.l": (0.15, 0.2, 0.15),
        "upperarm.l": (-1.1, 0.55, 0.85),
        "lowerarm.l": (-1.4, 0.2, 0.15),
        "hand.l": (0.4, 0.3, 0.35),
        "clavicle.r": (0.15, -0.2, -0.15),
        "upperarm.r": (-1.1, -0.55, -0.85),
        "lowerarm.r": (-1.4, -0.2, -0.15),
        "hand.r": (0.4, -0.3, -0.35),
    }


HEAD_HOLD_BONES = [
    "spine_01", "spine_02", "neck_01", "head",
    "clavicle.l", "upperarm.l", "lowerarm.l", "hand.l",
    "clavicle.r", "upperarm.r", "lowerarm.r", "hand.r",
]


def _header_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    t = frame / FPS
    snap = 0.35 * abs(math.sin(t * 8.0))
    return {
        "spine_01": (0.1 + snap * 0.2, 0.0, 0.0),
        "spine_02": (0.15 + snap * 0.3, 0.0, 0.0),
        "neck_01": (-0.25 - snap, 0.0, 0.0),
        "head": (-0.35 - snap * 0.5, 0.0, 0.0),
        "upperarm.l": (-0.4, 0.5, 0.3),
        "upperarm.r": (-0.4, -0.5, -0.3),
    }


# ---------------------------------------------------------------------------
# 47 — Norway toddling / trudging walk
# ---------------------------------------------------------------------------
def build_47() -> int:
    """Slow trudging walk — real run cycle scaled down (not frozen idle legs)."""
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    start = Vector((-8.0, 1.0, 0.12))
    end = Vector((10.0, -0.5, 0.12))

    arm, root = spawn_player(
        "Norway", NORWAY_RED, start, yaw_face_pos_x(),
        actions=["run"], split=(NORWAY_RED, NORWAY_WHITE, 0.42),
    )
    _clear_all_nla(arm)
    keys = []
    for f in range(1, frames + 1, 2):
        t = (f - 1) / max(1, frames - 1)
        # Near-linear slow trudge (no ease that freezes mid-stride)
        p = _lerp(start, end, t)
        p.y += 0.12 * math.sin(t * math.pi * 2.0)
        p.z = 0.12 + 0.03 * abs(math.sin(f * 0.35))
        keys.append((f, p))
    keys.append((frames, end.copy()))
    animate_root(root, keys, yaw_face_pos_x())
    add_nla_loop(arm, "run", 1, frames)
    # Slow the run cycle so it reads as a tired toddle, not a sprint
    ad = arm.animation_data
    if ad:
        for track in ad.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    alen = max(1.0, strip.action.frame_range[1] - strip.action.frame_range[0])
                    strip.scale = 0.28
                    strip.repeat = max(1.0, (frames + 1) / (alen * strip.scale))

    cam = setup_new_cam("Cam47", lens=32)
    _cam_dense(
        cam, 1, frames,
        Vector((-6.0, -10.0, 3.2)), Vector((8.0, -11.0, 3.0)),
        Vector((-4.0, 1.0, 1.3)), Vector((8.0, -0.5, 1.3)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 48 — Spain cage pass around Shaolin in the middle
# ---------------------------------------------------------------------------
def build_48() -> int:
    frames = 216
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    cx, cy = -4.0, 0.0
    r = 7.5
    angles = [0.0, 2.094, 4.189]  # 120°
    spain = []
    for i, a0 in enumerate(angles):
        pos = Vector((cx + r * math.cos(a0), cy + r * math.sin(a0), 0.0))
        yaw = math.atan2(cx - pos.x, -(cy - pos.y))  # face center
        arm, root = spawn_player(
            f"Spain_{i}", SPAIN_YELLOW, pos, yaw,
            actions=["idle", "fight_kick"], split=(SPAIN_YELLOW, SPAIN_RED, 0.42),
        )
        _clear_all_nla(arm)
        animate_root(root, [(1, pos), (frames, pos)], yaw)
        spain.append((arm, root, pos, yaw, a0))

    sh_pos = Vector((cx, cy, 0.0))
    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, sh_pos, yaw_face_neg_y(),
        actions=["idle", "fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(sh_arm)
    # trapped — spin looking around
    sh_keys = []
    for f in range(1, frames + 1, 2):
        yaw = yaw_face_neg_y() + 0.9 * math.sin(f * 0.08)
        sh_keys.append((f, sh_pos.copy()))
    animate_root(sh_root, sh_keys, yaw_face_neg_y())
    add_nla_hold(sh_arm, "fight_idle", 1, frames, af=8)
    add_pose_strip(
        sh_arm, "CageLook", frames,
        lambda f: {
            "spine_01": (0.05, 0.0, 0.25 * math.sin(f * 0.09)),
            "spine_02": (0.06, 0.0, 0.3 * math.sin(f * 0.09)),
            "neck_01": (0.08, 0.0, 0.45 * math.sin(f * 0.11)),
            "head": (0.1, 0.0, 0.5 * math.sin(f * 0.11)),
        },
        TALK_BONES, step=2, clamp=1.0,
    )

    # Pass triangle: 0→1→2→0 …
    passes = [(0, 1, 30), (1, 2, 70), (2, 0, 110), (0, 1, 150), (1, 2, 190)]
    for arm, _, _, _, _ in spain:
        add_nla_hold(arm, "idle", 1, frames, af=6)
    for a, b, fk in passes:
        add_nla_once(spain[a][0], "fight_kick", fk - 8, fk + 12)

    ball = clear_ball_anim()
    face_in = [Vector((cx - p.x, cy - p.y, 0.0)).normalized() for _, _, p, _, _ in spain]

    def ball_at_player(i: int, f: int) -> Vector:
        return ball_ahead_of(spain[i][2], -face_in[i], f, arm=spain[i][0])

    def path(f: int) -> Vector:
        cur = ball_at_player(0, 1)
        for i in range(len(passes)):
            a, b, fk = passes[i]
            f_end = passes[i + 1][2] if i + 1 < len(passes) else frames
            if f < fk:
                return cur
            if f <= fk + 18:
                u = (f - fk) / 18.0
                return _ball_arc(ball_at_player(a, fk), ball_at_player(b, fk + 18), u, 1.4)
            cur = ball_at_player(b, f)
            if f < f_end:
                return cur
        return cur

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam48", lens=28)
    _cam_dense(
        cam, 1, frames,
        Vector((cx - 2.0, cy - 18.0, 8.0)), Vector((cx + 4.0, cy - 16.0, 7.5)),
        Vector((cx, cy, 1.4)), Vector((cx, cy, 1.5)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 49 — Shaolin windmill steals ball from France dribbler
# ---------------------------------------------------------------------------
def build_49() -> int:
    frames = 180
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    fr_start = Vector((-14.0, 0.5, 0.0))
    fr_mid = Vector((-2.0, 0.8, 0.0))
    fr_end = Vector((6.0, 2.5, 0.0))
    steal = Vector((-1.5, 0.0, 0.0))
    sh_start = Vector((8.0, -4.0, 0.0))

    fr_arm, fr_root = spawn_france("France", fr_start, yaw_face_pos_x(), actions=["run", "idle", "fight_idle"])
    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, sh_start, yaw_face_neg_x(),
        actions=["run", "fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(fr_arm)
    _clear_all_nla(sh_arm)

    f_meet, f_drop, f_spin0, f_spin1 = 48, 58, 62, 140
    tip = -math.pi * 0.38
    spin_z = 1.1

    fr_keys = []
    for f in range(1, frames + 1, 2):
        if f <= f_meet:
            p = _lerp(fr_start, fr_mid, ease((f - 1) / max(1, f_meet - 1)))
        else:
            p = _lerp(fr_mid, fr_end, ease((f - f_meet) / max(1, frames - f_meet)))
        fr_keys.append((f, p))
    animate_root(fr_root, fr_keys, yaw_face_pos_x())
    add_nla_loop(fr_arm, "run", 1, f_meet)
    add_nla_hold(fr_arm, "fight_idle", f_meet + 1, frames, af=6)

    sh_keys_eul: List[Tuple[int, Vector, Euler]] = []
    yaw0 = yaw_face_neg_x()
    for f in range(1, frames + 1, 2):
        if f <= f_meet:
            t = ease((f - 1) / max(1, f_meet - 1))
            p = _lerp(sh_start, steal, t)
            eul = Euler((0.0, 0.0, yaw0), "XYZ")
        elif f <= f_drop:
            t = ease((f - f_meet) / max(1, f_drop - f_meet))
            p = Vector((steal.x, steal.y, spin_z * t))
            eul = Euler((tip * t, 0.0, yaw0), "XYZ")
        elif f <= f_spin1:
            spins = (f - f_spin0) * 0.5
            p = Vector((steal.x + 0.1 * math.cos(spins), steal.y + 0.1 * math.sin(spins), spin_z))
            eul = Euler((tip, 0.2 * math.sin(spins * 2), yaw0 + spins), "XYZ")
        else:
            t = ease((f - f_spin1) / max(1, frames - f_spin1))
            p = Vector((steal.x - 2.0 * t, steal.y, spin_z * (1.0 - t)))
            eul = Euler((tip * (1.0 - t), 0.0, yaw0), "XYZ")
        sh_keys_eul.append((f, p, eul))
    _animate_root_euler(sh_root, sh_keys_eul)
    add_nla_loop(sh_arm, "run", 1, f_drop - 1)
    add_nla_hold(sh_arm, "fight_idle", f_drop, frames, af=4)
    add_pose_strip(sh_arm, "StealWindmill", frames, _windmill_deltas, BREAK_BONES, step=2, clamp=1.8, absolute=True)

    ball = clear_ball_anim()

    def fr_at(f: int) -> Vector:
        if f <= f_meet:
            return _lerp(fr_start, fr_mid, ease((f - 1) / max(1, f_meet - 1)))
        return _lerp(fr_mid, fr_end, ease((f - f_meet) / max(1, frames - f_meet)))

    def path(f: int) -> Vector:
        if f < f_meet:
            return ball_ahead_of(fr_at(f), Vector((1, 0, 0)), f, arm=fr_arm)
        # stolen — orbit near windmill then leave with Shaolin
        if f <= f_spin1:
            spins = (f - f_spin0) * 0.5
            return Vector((steal.x + 1.6 * math.cos(spins), steal.y + 1.6 * math.sin(spins), 0.9))
        t = ease((f - f_spin1) / max(1, frames - f_spin1))
        return Vector((steal.x - 2.0 * t + 1.5, steal.y, BALL_GROUND_Z))

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam49", lens=30)
    _cam_dense(
        cam, 1, frames,
        Vector((-10.0, -12.0, 3.8)), Vector((2.0, -11.0, 3.2)),
        Vector((-6.0, 0.5, 1.3)), Vector((-1.0, 0.0, 1.4)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 50 — Windmill Shaolin passes to another Shaolin
# ---------------------------------------------------------------------------
def build_50() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    wm = Vector((-4.0, 0.0, 0.0))
    recv = Vector((8.0, -1.0, 0.0))
    tip = -math.pi * 0.38
    spin_z = 1.1
    f_spin0, f_pass, f_recv = 20, 90, 120

    a_arm, a_root = spawn_player(
        "Shaolin_WM", SHAOLIN_ORANGE, wm, yaw_face_neg_y(),
        actions=["fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    b_arm, b_root = spawn_player(
        "Shaolin_Recv", SHAOLIN_ORANGE, recv, yaw_face_neg_x(),
        actions=["idle", "run", "fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(a_arm)
    _clear_all_nla(b_arm)

    keys_eul = []
    for f in range(1, frames + 1, 2):
        spins = (f - f_spin0) * 0.48
        p = Vector((wm.x + 0.08 * math.cos(spins), wm.y + 0.08 * math.sin(spins), spin_z))
        eul = Euler((tip, 0.15 * math.sin(spins * 2), spins), "XYZ")
        keys_eul.append((f, p, eul))
    _animate_root_euler(a_root, keys_eul)
    add_nla_hold(a_arm, "fight_idle", 1, frames, af=4)
    add_pose_strip(a_arm, "WMPass", frames, _windmill_deltas, BREAK_BONES, step=2, clamp=1.8, absolute=True)

    animate_root(b_root, [(1, recv), (frames, recv)], yaw_face_neg_x())
    add_nla_hold(b_arm, "idle", 1, f_recv - 4, af=6)
    add_nla_hold(b_arm, "fight_idle", f_recv - 3, frames, af=8)

    ball = clear_ball_anim()

    def path(f: int) -> Vector:
        spins = (f - f_spin0) * 0.48
        orbit = Vector((wm.x + 1.5 * math.cos(spins), wm.y + 1.5 * math.sin(spins), 1.0))
        if f < f_pass:
            return orbit
        if f <= f_recv:
            dest = ball_ahead_of(recv, Vector((-1, 0, 0)), f_recv, arm=b_arm)
            return _ball_arc(orbit, dest, (f - f_pass) / max(1, f_recv - f_pass), 2.0)
        return ball_ahead_of(recv, Vector((-1, 0, 0)), f, arm=b_arm)

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam50", lens=30)
    _cam_dense(
        cam, 1, frames,
        Vector((-6.0, -12.0, 3.6)), Vector((4.0, -12.0, 3.4)),
        Vector((-2.0, 0.0, 1.4)), Vector((4.0, -0.5, 1.4)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 51 — France holding head in despair
# ---------------------------------------------------------------------------
def build_51() -> int:
    frames = 144
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    pos = Vector((-6.0, 1.0, 0.0))
    arm, root = spawn_france("France", pos, yaw_face_neg_y(), actions=["idle"])
    _clear_all_nla(arm)
    keys = []
    for f in range(1, frames + 1, 2):
        z = 0.03 * abs(math.sin(f * 0.15))
        keys.append((f, Vector((pos.x, pos.y, z))))
    animate_root(root, keys, yaw_face_neg_y())
    add_nla_hold(arm, "idle", 1, frames, af=10)
    add_pose_strip(arm, "FranceHeadHold", frames, _head_hold_deltas, HEAD_HOLD_BONES, step=2, clamp=1.5)

    cam = setup_new_cam("Cam51", lens=34)
    _cam_dense(
        cam, 1, frames,
        Vector((-4.0, -8.0, 2.4)), Vector((-5.0, -7.5, 2.2)),
        Vector((-6.0, 1.0, 1.7)), Vector((-6.0, 1.0, 1.75)),
        step=3,
    )
    finish_cam(cam)
    return frames


def _argentina_save(variant: str) -> int:
    """Shared Shaolin shot → Argentina GK save. variant: dive|catch|punch."""
    frames = 156
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    gx = goal_l_x()
    gk_home = Vector((gx + 3.2, 0.0, 0.0))
    shoot_pos = Vector((gx + 26.0, 1.8 if variant != "dive" else -2.2, 0.0))
    attack = Vector((-1.0, 0.0, 0.0))

    sh_arm, sh_root = spawn_player(
        "Shaolin_Shooter", SHAOLIN_ORANGE, shoot_pos, yaw_face_neg_x(),
        actions=["idle", "fight_kick", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    gk_arm, gk_root = spawn_player(
        "Argentina_GK", ARG_LIGHT, gk_home, yaw_face_pos_x(),
        actions=["idle", "fight_idle", "fight_punch", "jump_full"],
        split=(ARG_LIGHT, ARG_WHITE, 0.42),
    )
    _clear_all_nla(sh_arm)
    _clear_all_nla(gk_arm)

    f_kick, f_save = 36, 70
    if variant == "dive":
        save_pos = gk_home + Vector((0.8, 3.5, 0.0))
        contact = Vector((save_pos.x + 1.2, save_pos.y - 0.5, GOAL_H * 0.35))
        deflect = Vector((gx + 18.0, 12.0, BALL_GROUND_Z + 0.3))
    elif variant == "catch":
        save_pos = gk_home + Vector((1.0, 0.0, 0.0))
        contact = Vector((save_pos.x + 1.4, save_pos.y, GOAL_H * 0.5))
        deflect = contact.copy()  # held
    else:
        save_pos = gk_home + Vector((1.0, -2.2, 0.0))
        contact = Vector((save_pos.x + 1.5, save_pos.y + 0.3, GOAL_H * 0.6))
        deflect = Vector((gx + 20.0, -12.0, BALL_GROUND_Z + 0.4))

    animate_root(sh_root, [(1, shoot_pos), (frames, shoot_pos)], yaw_face_neg_x())
    animate_root(
        gk_root,
        [
            (1, gk_home),
            (f_save - 16, gk_home),
            (f_save, save_pos + Vector((0.0, 0.0, 0.45 if variant != "dive" else 0.15))),
            (f_save + 16, save_pos if variant != "dive" else save_pos + Vector((0, 0, 0.05))),
            (frames, save_pos),
        ],
        yaw_face_pos_x(),
    )
    add_nla_hold(sh_arm, "idle", 1, f_kick - 8, af=10)
    add_nla_once(sh_arm, "fight_kick", f_kick - 7, f_kick + 14)
    add_nla_hold(sh_arm, "fight_idle", f_kick + 15, frames, af=6)
    add_nla_loop(gk_arm, "idle", 1, f_save - 18)
    add_nla_once(gk_arm, "jump_full", f_save - 17, f_save - 2)
    add_nla_once(gk_arm, "fight_punch", f_save - 1, f_save + 14)
    add_nla_hold(gk_arm, "fight_idle", f_save + 15, frames, af=5)

    ball = clear_ball_anim()
    start_b = ball_ahead_of(shoot_pos, attack, f_kick, arm=sh_arm)

    def path(f: int) -> Vector:
        if f < f_kick:
            return Vector((start_b.x, start_b.y, BALL_GROUND_Z))
        if f <= f_save:
            return _shot_arc(start_b, contact, ease((f - f_kick) / max(1, f_save - f_kick)), 2.2)
        if variant == "catch":
            # ball sticks in gloves — slight settle
            t = min(1.0, (f - f_save) / 20.0)
            p = contact.copy()
            p.z -= 0.15 * t
            return p
        return _shot_arc(contact, deflect, ease((f - f_save) / 40.0), 1.5)

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam(f"CamArgSave_{variant}", lens=28)
    if variant == "dive":
        _cam_dense(
            cam, 1, frames,
            Vector((gx + 16.0, -14.0, 4.0)), Vector((gx + 6.0, -10.0, 3.2)),
            Vector((gx + 10.0, 1.0, 1.4)), Vector((gx + 4.0, 2.5, 1.5)),
            step=2,
        )
    elif variant == "catch":
        _cam_dense(
            cam, 1, frames,
            Vector((gx + 14.0, -12.0, 3.6)), Vector((gx + 7.0, -9.0, 3.0)),
            Vector((gx + 8.0, 0.0, 1.5)), Vector((gx + 4.0, 0.0, 1.7)),
            step=2,
        )
    else:
        _cam_dense(
            cam, 1, frames,
            Vector((gx + 20.0, -15.0, 4.5)), Vector((gx + 10.0, -12.0, 3.6)),
            Vector((gx + 12.0, 0.0, 1.5)), Vector((gx + 5.0, -1.5, 1.6)),
            step=2,
        )
    finish_cam(cam)
    return frames


def build_52() -> int:
    return _argentina_save("dive")


def build_53() -> int:
    return _argentina_save("catch")


def build_54() -> int:
    return _argentina_save("punch")


# ---------------------------------------------------------------------------
# 55 — Argentina crowd: light-blue / white alternating horizontal stripes
# ---------------------------------------------------------------------------
def build_55() -> int:
    frames = 180
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    _clear_extras("Crowd_")
    blue_m = mat_rgba("Crowd_ArgBlue", ARG_LIGHT, 0.7)
    wht_m = mat_rgba("Crowd_ArgWht", ARG_WHITE, 0.7)
    stand_m = mat_rgba("Crowd_ArgStand", (0.22, 0.22, 0.25, 1.0), 0.9)
    add_box("Crowd_StandDeck", (50.0, 10.0, 0.4), Vector((0.0, 38.0, 6.0)), stand_m)
    add_box("Crowd_StandRisers", (50.0, 8.0, 3.5), Vector((0.0, 40.5, 4.0)), stand_m)

    cols, rows = 22, 6
    idx = 0
    for r in range(rows):
        for c in range(cols):
            x = -24.0 + c * 2.2 + (0.25 if r % 2 else 0.0)
            y = 34.2 + r * 1.65
            z = 6.3 + r * 0.52
            # horizontal stripes: alternate by ROW (light blue / white)
            mat = blue_m if r % 2 == 0 else wht_m
            name = f"Crowd_Fan{idx:03d}"
            obj = add_box(name, (0.48, 0.36, 0.95), Vector((x, y, z + 0.48)), mat)
            phase = idx * 0.31
            for f in range(1, frames + 1, 2):
                t = f / FPS
                bob = 0.16 * math.sin(t * 7.2 + phase)
                lean = 0.1 * math.sin(t * 5.2 + phase)
                obj.location = Vector((x + lean * 0.12, y, z + 0.48 + bob))
                obj.rotation_euler = Euler((lean * 0.2, 0.0, lean * 0.12), "XYZ")
                obj.keyframe_insert(data_path="location", frame=f)
                obj.keyframe_insert(data_path="rotation_euler", frame=f)
            force_linear(obj)
            idx += 1

    cam = setup_new_cam("Cam55", lens=28)
    for f in range(1, frames + 1, 3):
        t = (f - 1) / max(1, frames - 1)
        pos = Vector((-16.0 + 32.0 * ease(t), 20.0, 9.0 + 1.2 * math.sin(t * math.pi)))
        tgt = Vector((-8.0 + 16.0 * t, 38.0, 7.2))
        kf_cam(cam, f, pos, tgt)
    kf_cam(cam, frames, Vector((16.0, 20.0, 9.0)), Vector((8.0, 38.0, 7.2)))
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 56 — Shaolin GK passes to windmill Shaolin
# ---------------------------------------------------------------------------
def build_56() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    gx = goal_l_x()
    gk = Vector((gx + 4.0, 0.0, 0.0))
    wm = Vector((gx + 22.0, -3.0, 0.0))
    tip = -math.pi * 0.38
    spin_z = 1.1
    f_kick, f_recv, f_spin0 = 40, 70, 74

    gk_arm, gk_root = spawn_player(
        "Shaolin_GK", SHAOLIN_ORANGE, gk, yaw_face_pos_x(),
        actions=["idle", "fight_kick", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    wm_arm, wm_root = spawn_player(
        "Shaolin_WM", SHAOLIN_ORANGE, wm, yaw_face_neg_x(),
        actions=["fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(gk_arm)
    _clear_all_nla(wm_arm)
    animate_root(gk_root, [(1, gk), (frames, gk)], yaw_face_pos_x())
    keys_eul = []
    for f in range(1, frames + 1, 2):
        if f < f_recv:
            keys_eul.append((f, wm.copy(), Euler((0, 0, yaw_face_neg_x()), "XYZ")))
        else:
            spins = (f - f_spin0) * 0.48
            p = Vector((wm.x + 0.08 * math.cos(spins), wm.y + 0.08 * math.sin(spins), spin_z))
            keys_eul.append((f, p, Euler((tip, 0.15 * math.sin(spins * 2), yaw_face_neg_x() + spins), "XYZ")))
    _animate_root_euler(wm_root, keys_eul)
    add_nla_hold(gk_arm, "idle", 1, f_kick - 10, af=8)
    add_nla_once(gk_arm, "fight_kick", f_kick - 9, f_kick + 14)
    add_nla_hold(gk_arm, "fight_idle", f_kick + 15, frames, af=6)
    add_nla_hold(wm_arm, "fight_idle", 1, frames, af=4)
    add_pose_strip(wm_arm, "GkToWm", frames, _windmill_deltas, BREAK_BONES, step=2, clamp=1.8, absolute=True)

    ball = clear_ball_anim()
    start_b = ball_ahead_of(gk, Vector((1, 0, 0)), f_kick, arm=gk_arm)

    def path(f: int) -> Vector:
        if f < f_kick:
            return Vector((start_b.x, start_b.y, BALL_GROUND_Z))
        if f <= f_recv:
            dest = Vector((wm.x, wm.y, 1.0))
            return _ball_arc(start_b, dest, (f - f_kick) / max(1, f_recv - f_kick), 1.8)
        spins = (f - f_spin0) * 0.48
        return Vector((wm.x + 1.5 * math.cos(spins), wm.y + 1.5 * math.sin(spins), 1.0))

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam56", lens=28)
    _cam_dense(
        cam, 1, frames,
        Vector((gx + 10.0, -14.0, 4.0)), Vector((gx + 18.0, -13.0, 3.5)),
        Vector((gx + 12.0, -1.0, 1.4)), Vector((gx + 20.0, -2.5, 1.4)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 57 — Windmill passes to Shaolin belly
# ---------------------------------------------------------------------------
def build_57() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    wm = Vector((-6.0, 0.0, 0.0))
    belly_p = Vector((6.0, 0.5, 0.0))
    tip = -math.pi * 0.38
    spin_z = 1.1
    f_spin0, f_pass, f_stick = 16, 80, 110

    a_arm, a_root = spawn_player(
        "Shaolin_WM", SHAOLIN_ORANGE, wm, yaw_face_pos_x(),
        actions=["fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    b_arm, b_root = spawn_player(
        "Shaolin_Belly", SHAOLIN_ORANGE, belly_p, yaw_face_neg_x(),
        actions=["idle", "fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(a_arm)
    _clear_all_nla(b_arm)
    keys_eul = []
    for f in range(1, frames + 1, 2):
        spins = (f - f_spin0) * 0.48
        p = Vector((wm.x + 0.08 * math.cos(spins), wm.y + 0.08 * math.sin(spins), spin_z))
        keys_eul.append((f, p, Euler((tip, 0.12 * math.sin(spins * 2), spins), "XYZ")))
    _animate_root_euler(a_root, keys_eul)
    add_nla_hold(a_arm, "fight_idle", 1, frames, af=4)
    add_pose_strip(a_arm, "WmBelly", frames, _windmill_deltas, BREAK_BONES, step=2, clamp=1.8, absolute=True)
    animate_root(b_root, [(1, belly_p), (frames, belly_p)], yaw_face_neg_x())
    add_nla_hold(b_arm, "idle", 1, f_stick - 6, af=6)
    add_nla_hold(b_arm, "fight_idle", f_stick - 5, frames, af=10)

    ball = clear_ball_anim()
    belly = _belly_ball(belly_p, Vector((-1, 0, 0)), z_off=2.15, ahead=1.1)

    def path(f: int) -> Vector:
        spins = (f - f_spin0) * 0.48
        orbit = Vector((wm.x + 1.5 * math.cos(spins), wm.y + 1.5 * math.sin(spins), 1.0))
        if f < f_pass:
            return orbit
        if f <= f_stick:
            return _ball_arc(orbit, belly, (f - f_pass) / max(1, f_stick - f_pass), 1.6)
        return belly.copy()

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam57", lens=30)
    _cam_dense(
        cam, 1, frames,
        Vector((-4.0, -12.0, 3.8)), Vector((4.0, -12.0, 3.5)),
        Vector((-2.0, 0.0, 1.5)), Vector((4.0, 0.3, 1.6)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 58 — Belly ball passes up to aerial Shaolin
# ---------------------------------------------------------------------------
def build_58() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    belly_p = Vector((-4.0, 0.0, 0.0))
    air_p = Vector((6.0, -1.0, 0.0))
    f_pass, f_recv = 50, 95

    b_arm, b_root = spawn_player(
        "Shaolin_Belly", SHAOLIN_ORANGE, belly_p, yaw_face_pos_x(),
        actions=["idle", "fight_kick", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    a_arm, a_root = spawn_player(
        "Shaolin_Air", SHAOLIN_ORANGE, air_p, yaw_face_neg_x(),
        actions=["idle", "jump_full", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(b_arm)
    _clear_all_nla(a_arm)
    animate_root(b_root, [(1, belly_p), (frames, belly_p)], yaw_face_pos_x())
    air_keys = []
    for f in range(1, frames + 1, 2):
        if f < f_recv - 20:
            z = 0.0
        elif f <= f_recv + 30:
            u = (f - (f_recv - 20)) / 50.0
            z = 3.2 * math.sin(min(1.0, u) * math.pi)
        else:
            z = max(0.0, 3.2 * (1.0 - (f - f_recv - 30) / 40.0))
        air_keys.append((f, Vector((air_p.x, air_p.y, z))))
    animate_root(a_root, air_keys, yaw_face_neg_x())
    add_nla_hold(b_arm, "idle", 1, f_pass - 10, af=6)
    add_nla_once(b_arm, "fight_kick", f_pass - 9, f_pass + 12)
    add_nla_hold(b_arm, "fight_idle", f_pass + 13, frames, af=6)
    add_nla_hold(a_arm, "idle", 1, f_recv - 24, af=6)
    add_nla_once(a_arm, "jump_full", f_recv - 23, f_recv + 10)
    add_nla_hold(a_arm, "fight_idle", f_recv + 11, frames, af=6)

    ball = clear_ball_anim()
    belly = _belly_ball(belly_p, Vector((1, 0, 0)), z_off=2.15, ahead=1.0)

    def path(f: int) -> Vector:
        if f < f_pass:
            return belly.copy()
        # aerial catch height
        air_ball = Vector((air_p.x - 0.5, air_p.y, 3.4))
        if f <= f_recv:
            return _ball_arc(belly, air_ball, (f - f_pass) / max(1, f_recv - f_pass), 1.2)
        # stick near aerial player
        z = 3.2 * math.sin(min(1.0, (f - (f_recv - 20)) / 50.0) * math.pi) if f <= f_recv + 30 else 1.2
        return Vector((air_p.x - 0.4, air_p.y, max(1.2, z + 0.3)))

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam58", lens=30)
    _cam_dense(
        cam, 1, frames,
        Vector((-2.0, -12.0, 3.5)), Vector((4.0, -11.0, 4.5)),
        Vector((-2.0, 0.0, 1.8)), Vector((5.0, -1.0, 2.8)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 59 — Aerial Shaolin passes to ground Shaolin (header receive)
# ---------------------------------------------------------------------------
def build_59() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    air_p = Vector((-4.0, 0.0, 0.0))
    gnd = Vector((8.0, -0.5, 0.0))
    f_pass, f_hdr = 55, 95

    a_arm, a_root = spawn_player(
        "Shaolin_Air", SHAOLIN_ORANGE, air_p, yaw_face_pos_x(),
        actions=["jump_full", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    g_arm, g_root = spawn_player(
        "Shaolin_Hdr", SHAOLIN_ORANGE, gnd, yaw_face_neg_x(),
        actions=["idle", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(a_arm)
    _clear_all_nla(g_arm)
    air_keys = []
    for f in range(1, frames + 1, 2):
        if f < f_pass + 20:
            z = 3.0 + 0.15 * math.sin(f * 0.2)
        else:
            z = max(0.0, 3.0 * (1.0 - (f - f_pass - 20) / 60.0))
        air_keys.append((f, Vector((air_p.x, air_p.y, z))))
    animate_root(a_root, air_keys, yaw_face_pos_x())
    animate_root(g_root, [(1, gnd), (frames, gnd)], yaw_face_neg_x())
    add_nla_once(a_arm, "jump_full", 1, 40)
    add_nla_hold(a_arm, "fight_idle", 41, frames, af=6)
    add_nla_hold(g_arm, "idle", 1, f_hdr - 10, af=6)
    add_nla_hold(g_arm, "fight_idle", f_hdr - 9, frames, af=8)
    add_pose_strip(g_arm, "HeaderRecv", frames, _header_deltas, TALK_BONES + ["upperarm.l", "upperarm.r"], step=2, clamp=1.2)

    ball = clear_ball_anim()

    def path(f: int) -> Vector:
        air_ball = Vector((air_p.x + 0.5, air_p.y, 3.3))
        if f < f_pass:
            return air_ball
        head = Vector((gnd.x - 0.3, gnd.y, 2.7))
        if f <= f_hdr:
            return _ball_arc(air_ball, head, (f - f_pass) / max(1, f_hdr - f_pass), 0.8)
        # drop after header
        t = min(1.0, (f - f_hdr) / 40.0)
        return Vector((gnd.x + 1.5 * t, gnd.y, 2.7 - 2.2 * t))

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam59", lens=30)
    _cam_dense(
        cam, 1, frames,
        Vector((-2.0, -12.0, 4.2)), Vector((6.0, -11.0, 3.5)),
        Vector((-2.0, 0.0, 2.6)), Vector((6.0, -0.5, 2.0)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 60 — Shaolin shot blows Argentina GK away
# ---------------------------------------------------------------------------
def build_60() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    gx = goal_l_x()
    gk_home = Vector((gx + 3.0, 0.0, 0.0))
    shoot_pos = Vector((gx + 24.0, 0.5, 0.0))
    f_kick, f_hit = 40, 72

    sh_arm, sh_root = spawn_player(
        "Shaolin_Shooter", SHAOLIN_ORANGE, shoot_pos, yaw_face_neg_x(),
        actions=["idle", "fight_kick", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    gk_arm, gk_root = spawn_player(
        "Argentina_GK", ARG_LIGHT, gk_home, yaw_face_pos_x(),
        actions=["idle", "fight_idle", "jump_full"],
        split=(ARG_LIGHT, ARG_WHITE, 0.42),
    )
    _clear_all_nla(sh_arm)
    _clear_all_nla(gk_arm)
    animate_root(sh_root, [(1, shoot_pos), (frames, shoot_pos)], yaw_face_neg_x())
    # GK blown into the net / back with tumble
    blown = Vector((gx - 4.0, -1.5, 0.0))
    gk_keys_eul: List[Tuple[int, Vector, Euler]] = []
    for f in range(1, frames + 1, 2):
        if f < f_hit:
            gk_keys_eul.append((f, gk_home.copy(), Euler((0.0, 0.0, yaw_face_pos_x()), "XYZ")))
        else:
            t = ease((f - f_hit) / max(1, frames - f_hit))
            p = _lerp(gk_home, blown, min(1.0, t * 1.3))
            p.z = 2.2 * math.sin(min(1.0, t) * math.pi) * (1.0 - 0.3 * t)
            gk_keys_eul.append(
                (f, p, Euler((t * 2.2, t * 0.8, yaw_face_pos_x() + t * 1.5), "XYZ"))
            )
    _animate_root_euler(gk_root, gk_keys_eul)

    add_nla_hold(sh_arm, "idle", 1, f_kick - 8, af=10)
    add_nla_once(sh_arm, "fight_kick", f_kick - 7, f_kick + 14)
    add_nla_hold(sh_arm, "fight_idle", f_kick + 15, frames, af=6)
    add_nla_loop(gk_arm, "idle", 1, f_hit - 12)
    add_nla_once(gk_arm, "jump_full", f_hit - 11, f_hit + 5)
    add_nla_hold(gk_arm, "fight_idle", f_hit + 6, frames, af=4)

    ball = clear_ball_anim()
    start_b = ball_ahead_of(shoot_pos, Vector((-1, 0, 0)), f_kick, arm=sh_arm)
    goal_b = Vector((gx - 1.5, -0.8, GOAL_H * 0.55))

    def path(f: int) -> Vector:
        if f < f_kick:
            return Vector((start_b.x, start_b.y, BALL_GROUND_Z))
        if f <= f_hit:
            return _shot_arc(start_b, Vector((gk_home.x + 1.0, 0.0, GOAL_H * 0.5)), ease((f - f_kick) / max(1, f_hit - f_kick)), 2.0)
        return _shot_arc(Vector((gk_home.x + 1.0, 0.0, GOAL_H * 0.5)), goal_b, ease((f - f_hit) / 40.0), 1.2)

    key_ball(ball, range(1, frames + 1, 2), path)
    cam = setup_new_cam("Cam60", lens=28)
    _cam_dense(
        cam, 1, frames,
        Vector((gx + 18.0, -14.0, 4.0)), Vector((gx + 2.0, -12.0, 3.5)),
        Vector((gx + 10.0, 0.0, 1.5)), Vector((gx - 1.0, -1.0, 1.8)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 61 — Shaolin GK substitution: two Shaolin cross in front of goal
# ---------------------------------------------------------------------------
def build_61() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    gx = goal_l_x()
    # Outgoing GK walks off; incoming walks on — they cross mid goal mouth
    out_a = Vector((gx + 3.5, 2.0, 0.0))
    out_b = Vector((gx + 12.0, -10.0, 0.0))
    in_a = Vector((gx + 12.0, 10.0, 0.0))
    in_b = Vector((gx + 3.5, -1.5, 0.0))

    out_arm, out_root = spawn_player(
        "Shaolin_Out", SHAOLIN_ORANGE, out_a, yaw_face_pos_x(),
        actions=["run", "idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    in_arm, in_root = spawn_player(
        "Shaolin_In", SHAOLIN_ORANGE, in_a, yaw_face_neg_x(),
        actions=["run", "idle", "fight_idle"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(out_arm)
    _clear_all_nla(in_arm)

    out_keys = [(f, _lerp(out_a, out_b, ease((f - 1) / max(1, frames - 1)))) for f in range(1, frames + 1, 2)]
    in_keys = [(f, _lerp(in_a, in_b, ease((f - 1) / max(1, frames - 1)))) for f in range(1, frames + 1, 2)]
    out_keys.append((frames, out_b.copy()))
    in_keys.append((frames, in_b.copy()))
    # Face travel: out toward pitch / sideline, in toward goal
    animate_root(out_root, out_keys, math.atan2((out_b - out_a).x, -(out_b - out_a).y))
    animate_root(in_root, in_keys, math.atan2((in_b - in_a).x, -(in_b - in_a).y))
    add_nla_loop(out_arm, "run", 1, frames)
    add_nla_loop(in_arm, "run", 1, 130)
    add_nla_hold(in_arm, "fight_idle", 131, frames, af=8)

    cam = setup_new_cam("Cam61", lens=28)
    _cam_dense(
        cam, 1, frames,
        Vector((gx + 8.0, -16.0, 4.2)), Vector((gx + 6.0, -14.0, 3.8)),
        Vector((gx + 6.0, 0.0, 1.5)), Vector((gx + 5.0, 0.0, 1.5)),
        step=2,
    )
    finish_cam(cam)
    return frames


BUILDERS: Dict[str, Callable[[], int]] = {
    "47": build_47,
    "48": build_48,
    "49": build_49,
    "50": build_50,
    "51": build_51,
    "52": build_52,
    "53": build_53,
    "54": build_54,
    "55": build_55,
    "56": build_56,
    "57": build_57,
    "58": build_58,
    "59": build_59,
    "60": build_60,
    "61": build_61,
}
