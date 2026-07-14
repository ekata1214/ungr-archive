# SPDX-License-Identifier: MIT
"""France block cuts 18–28 — attack Goal_L."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

import bpy
from mathutils import Vector

from animate_soccer_match import BALL_GROUND_Z, _clear_all_nla  # noqa: E402

from cuts.common import (  # noqa: E402
    ARG_LIGHT,
    ARG_WHITE,
    FRANCE_BLUE,
    FRANCE_RED,
    FRANCE_WHITE,
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
    spawn_player,
    yaw_face_neg_x,
    yaw_face_neg_y,
)

GOAL_X = goal_l_x()
ATTACK_DIR = Vector((-1.0, 0.0, 0.0))
ATTACK_YAW = yaw_face_neg_x()
NET_IN = Vector((GOAL_X - 1.4, 0.0, GOAL_H * 0.55))


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


def _cam_hold(cam: bpy.types.Object, frames: Sequence[int], pos: Vector, tgt: Vector) -> None:
    for f in frames:
        kf_cam(cam, f, pos, tgt)


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
    back = mat_rgba("Interview_BackMat", (0.07, 0.09, 0.16, 1.0), 0.85)
    stripe = mat_rgba("Interview_StripeMat", primary, 0.45)
    acc = mat_rgba("Interview_AccentMat", accent, 0.45)
    panel = mat_rgba("Interview_PanelMat", (0.16, 0.18, 0.24, 1.0), 0.7)
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
        nod = 0.03 * math.sin(t * 2.4)
        down = base_down + 0.04 * math.sin(t * 0.7)
        return {
            "spine_01": (0.04 + down * 0.2, 0.0, 0.0),
            "spine_02": (0.06 + down * 0.3, 0.0, 0.0),
            "neck_01": (0.05 + nod + down * 0.55, 0.0, 0.02 * math.sin(t * 1.1)),
            "head": (0.06 + nod + down * 0.75, 0.0, 0.03 * math.sin(t * 1.3)),
        }

    return deltas


def _happy_fn() -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS
        bob = 0.08 * math.sin(t * 8.0)
        return {
            "spine_01": (0.02 + bob * 0.2, 0.0, 0.0),
            "spine_02": (0.03 + bob * 0.35, 0.0, 0.0),
            "neck_01": (-0.04 + bob * 0.5, 0.0, 0.04 * math.sin(t * 5.0)),
            "head": (-0.05 + bob, 0.0, 0.05 * math.sin(t * 5.5)),
        }

    return deltas


# ---------------------------------------------------------------------------
# 18 — 1v1 juke
# ---------------------------------------------------------------------------
def build_18() -> int:
    frames = 132
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    gap = SIDE_GAP
    fr_y = gap * 0.5
    sh_y = -gap * 0.5
    fr_pos = Vector((-20.0, fr_y, 0.0))
    sh_start = Vector((8.0, sh_y, 0.0))
    sh_mid = Vector((-22.0, sh_y - 0.4, 0.0))
    sh_end = Vector((-55.0, sh_y - 0.2, 0.0))

    fr_arm, fr_root = spawn_player(
        "France", FRANCE_BLUE, fr_pos, ATTACK_YAW, actions=["idle"], split=(FRANCE_BLUE, FRANCE_WHITE, 0.42)
    )

    _clear_all_nla(fr_arm)
    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, sh_start, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(sh_arm)

    # France holds lane, stab-fail near approach
    animate_root(fr_root, [(1, fr_pos), (50, fr_pos), (70, Vector((-21.2, fr_y, 0.0))), (frames, fr_pos)], ATTACK_YAW)
    add_nla_loop(fr_arm, "idle", 1, 54)
    add_nla_once(fr_arm, "fight_kick", 55, 78)
    add_nla_hold(fr_arm, "fight_idle", 79, frames, af=8)

    # Shaolin curves past on far side then accelerates
    sh_keys: List[Tuple[int, Vector]] = []
    for f in range(1, frames + 1, 2):
        if f <= 48:
            t = ease((f - 1) / 47.0)
            # curve around France: dip further negative Y then straighten
            bend = math.sin(t * math.pi) * 1.2
            p = _lerp(sh_start, sh_mid, t)
            p.y = sh_y - bend
            sh_keys.append((f, p))
        else:
            t = ease((f - 48) / max(1, frames - 48))
            p = _lerp(sh_mid, sh_end, t)
            # accelerate: bias later frames further ahead via ease already
            sh_keys.append((f, p))
    if sh_keys[-1][0] != frames:
        sh_keys.append((frames, sh_end))
    animate_root(sh_root, sh_keys, ATTACK_YAW)
    add_nla_loop(sh_arm, "run", 1, frames)

    ball = clear_ball_anim()

    def ball_path(f: int) -> Vector:
        # sample nearest keyed shaolin root
        loc = sh_start
        for kf, p in sh_keys:
            if kf <= f:
                loc = p
            else:
                break
        md = ATTACK_DIR
        if f >= 48:
            md = (sh_end - sh_mid).normalized()
        return ball_ahead_of(loc, md, f, arm=sh_arm)

    key_ball(ball, range(1, frames + 1, 2), ball_path)

    cam = setup_new_cam("Cam18", lens=30)
    _cam_dense(
        cam, 1, 50,
        Vector((12.0, -18.0, 5.5)), Vector((-8.0, -16.0, 4.8)),
        Vector((0.0, 0.0, 1.2)), Vector((-22.0, 0.0, 1.2)),
        step=2,
    )
    _cam_dense(
        cam, 50, frames,
        Vector((-8.0, -16.0, 4.8)), Vector((-40.0, -14.0, 4.2)),
        Vector((-22.0, 0.0, 1.2)), Vector((-50.0, sh_y, 1.2)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 19 — France sits
# ---------------------------------------------------------------------------
def build_19() -> int:
    frames = 96
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    pos = Vector((-10.0, 2.0, 0.0))
    arm, root = spawn_player(
        "France", FRANCE_BLUE, pos, yaw_face_neg_y(), actions=["idle"], split=(FRANCE_BLUE, FRANCE_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    keys = []
    for f in range(1, frames + 1, 3):
        t = ease((f - 1) / max(1, frames - 1))
        z = -0.15 - 0.7 * t  # ~-0.85 sit
        keys.append((f, Vector((pos.x, pos.y, z))))
    keys.append((frames, Vector((pos.x, pos.y, -0.85))))
    animate_root(root, keys, yaw_face_neg_y())
    add_nla_hold(arm, "idle", 1, frames, af=12)

    cam = setup_new_cam("Cam19", lens=35)
    _cam_dense(
        cam, 1, frames,
        Vector((-6.0, -9.5, 3.2)), Vector((-8.0, -8.5, 2.8)),
        Vector((-10.0, 2.0, 1.0)), Vector((-10.0, 2.0, 0.7)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 20 — phone from sock
# ---------------------------------------------------------------------------
def build_20() -> int:
    frames = 120
    remove_players()
    _show_pitch()
    _clear_extras("Phone_")
    set_frame_range(frames)
    hide_ball()
    pos = Vector((-10.0, 2.0, -0.85))
    arm, root = spawn_player(
        "France", FRANCE_BLUE, pos, yaw_face_neg_y(), actions=["idle"], split=(FRANCE_BLUE, FRANCE_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_hold(arm, "idle", 1, frames, af=12)

    phone_mat = mat_rgba("Phone_Mat", (0.08, 0.08, 0.1, 1.0), 0.35)
    phone = add_box("Phone_01", (0.1, 0.05, 0.18), Vector((pos.x + 0.35, pos.y - 0.15, 0.08)), phone_mat)
    # rise foot → hand region, then fidget
    foot = Vector((pos.x + 0.4, pos.y - 0.2, 0.05))
    hand = Vector((pos.x + 0.35, pos.y - 0.55, 1.15))
    force_linear(phone)
    for f in range(1, frames + 1, 2):
        if f <= 40:
            t = ease((f - 1) / 39.0)
            loc = _lerp(foot, hand, t)
        else:
            wiggle = 0.04 * math.sin((f - 40) * 0.35)
            loc = hand + Vector((wiggle, 0.02 * math.sin(f * 0.5), 0.02 * math.cos(f * 0.4)))
        phone.location = loc
        phone.keyframe_insert(data_path="location", frame=f)
    force_linear(phone)

    cam = setup_new_cam("Cam20", lens=40)
    _cam_dense(
        cam, 1, frames,
        Vector((-8.5, -6.5, 2.4)), Vector((-9.0, -5.2, 2.1)),
        Vector((-10.0, 2.0, 0.9)), Vector((-10.0, 1.8, 1.0)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 21 — France solo goal
# ---------------------------------------------------------------------------
def build_21() -> int:
    frames = 144
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    start = Vector((-30.0, 1.0, 0.0))
    kick = Vector((GOAL_X + 22.0, 0.6, 0.0))
    arm, root = spawn_player(
        "France", FRANCE_BLUE, start, ATTACK_YAW, actions=["run"], split=(FRANCE_BLUE, FRANCE_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    keys = []
    for f in range(1, 96, 2):
        t = ease((f - 1) / 94.0)
        keys.append((f, _lerp(start, kick, t)))
    keys += [(96, kick), (frames, kick)]
    animate_root(root, keys, ATTACK_YAW)
    add_nla_loop(arm, "run", 1, 95)
    add_nla_once(arm, "fight_kick", 96, 118)
    add_nla_hold(arm, "fight_idle", 119, frames, af=6)

    ball = clear_ball_anim()
    goal = Vector((GOAL_X - 1.5, -GOAL_INNER_HALF_W * 0.55, GOAL_H * 0.62))

    def path(f: int) -> Vector:
        if f < 96:
            loc = _lerp(start, kick, ease((f - 1) / 94.0))
            return ball_ahead_of(loc, ATTACK_DIR, f, arm=arm)
        if f <= 104:
            return ball_ahead_of(kick, ATTACK_DIR, f, arm=arm)
        u = ease((f - 104) / max(1, 124 - 104))
        if f > 124:
            return goal
        return _shot_arc(ball_ahead_of(kick, ATTACK_DIR, 104, arm=arm), goal, u, arc=2.8)

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam21", lens=28)
    _cam_dense(
        cam, 1, 90,
        Vector((-20.0, -20.0, 6.0)), Vector((GOAL_X + 35.0, -16.0, 5.0)),
        Vector((-30.0, 1.0, 1.2)), Vector((GOAL_X + 20.0, 0.5, 1.2)),
        step=2,
    )
    _cam_dense(
        cam, 90, frames,
        Vector((GOAL_X + 35.0, -16.0, 5.0)), Vector((GOAL_X + 18.0, -10.0, 4.0)),
        Vector((GOAL_X + 20.0, 0.5, 1.2)), Vector((GOAL_X, 0.0, 2.0)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 22 — crowd react
# ---------------------------------------------------------------------------
def build_22() -> int:
    frames = 120
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    colors = [
        FRANCE_BLUE, FRANCE_WHITE, FRANCE_RED, FRANCE_BLUE,
        SHAOLIN_ORANGE, ARG_LIGHT, FRANCE_WHITE, FRANCE_BLUE,
        (0.9, 0.85, 0.2, 1.0), FRANCE_RED, FRANCE_BLUE, ARG_WHITE,
        FRANCE_WHITE, FRANCE_BLUE, SHAOLIN_WHITE, FRANCE_RED,
        FRANCE_BLUE, FRANCE_WHITE, FRANCE_RED, FRANCE_BLUE,
    ]
    arms_roots = []
    base = Vector((-40.0, 28.0, 0.0))
    cols, rows = 5, 4
    idx = 0
    for r in range(rows):
        for c in range(cols):
            px = base.x + c * SIDE_GAP * 1.05
            py = base.y + r * 2.8
            col = colors[idx % len(colors)]
            arm, root = spawn_player(
                f"Crowd_{idx:02d}", col, Vector((px, py, 0.0)), math.pi, actions=["idle"]
            )
            _clear_all_nla(arm)
            arms_roots.append((arm, root, px, py, idx))
            idx += 1

    for arm, root, px, py, i in arms_roots:
        keys = []
        phase = i * 0.7
        for f in range(1, frames + 1, 2):
            # surprise bob — bigger mid surge
            surge = 1.0
            if 40 <= f <= 80:
                surge = 1.0 + 0.55 * math.sin((f - 40) / 40.0 * math.pi)
            z = 0.12 * surge * abs(math.sin(f * 0.28 + phase))
            keys.append((f, Vector((px, py, z))))
        animate_root(root, keys, math.pi)
        add_nla_loop(arm, "idle", 1, frames)

    cam = setup_new_cam("Cam22", lens=24)
    _cam_dense(
        cam, 1, frames,
        Vector((-30.0, 10.0, 8.0)), Vector((-55.0, 14.0, 7.0)),
        Vector((-40.0, 32.0, 2.5)), Vector((-45.0, 34.0, 3.0)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 23 — equalizer pass + shot
# ---------------------------------------------------------------------------
def build_23() -> int:
    frames = 132
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    recv = Vector((-45.0, -2.0, 0.0))
    kick = Vector((GOAL_X + 26.0, -1.2, 0.0))
    arm, root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, recv, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    keys = [(1, recv)]
    for f in range(36, 90, 2):
        t = ease((f - 36) / 53.0)
        keys.append((f, _lerp(recv, kick, t)))
    keys += [(90, kick), (frames, kick)]
    animate_root(root, keys, ATTACK_YAW)
    add_nla_loop(arm, "run", 1, 89)
    add_nla_once(arm, "fight_kick", 90, 112)
    add_nla_hold(arm, "fight_idle", 113, frames, af=6)

    ball = clear_ball_anim()
    off = Vector((-20.0, 18.0, BALL_GROUND_Z))
    arrive = ball_ahead_of(recv, ATTACK_DIR, 34, arm=arm)
    goal = Vector((GOAL_X - 1.6, GOAL_INNER_HALF_W * 0.5, GOAL_H * 0.58))

    def path(f: int) -> Vector:
        if f <= 34:
            u = ease((f - 1) / 33.0)
            return _shot_arc(off, arrive, u, arc=1.4)
        if f < 90:
            loc = _lerp(recv, kick, ease((f - 36) / 53.0) if f >= 36 else 0.0)
            return ball_ahead_of(loc if f >= 36 else recv, ATTACK_DIR, f, arm=arm)
        if f <= 98:
            return ball_ahead_of(kick, ATTACK_DIR, f, arm=arm)
        u = ease((f - 98) / max(1, 118 - 98))
        return goal if f > 118 else _shot_arc(ball_ahead_of(kick, ATTACK_DIR, 98, arm=arm), goal, u, 3.0)

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam23", lens=30)
    _cam_dense(
        cam, 1, 40,
        Vector((-15.0, -12.0, 5.0)), Vector((-40.0, -14.0, 4.5)),
        Vector((-25.0, 8.0, 1.0)), Vector((-45.0, -2.0, 1.2)),
        step=2,
    )
    _cam_dense(
        cam, 40, frames,
        Vector((-40.0, -14.0, 4.5)), Vector((GOAL_X + 20.0, -11.0, 4.0)),
        Vector((-45.0, -2.0, 1.2)), Vector((GOAL_X, 0.0, 2.0)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 24 — France tired
# ---------------------------------------------------------------------------
def build_24() -> int:
    frames = 120
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    start = Vector((-5.0, 3.0, 0.0))
    end = Vector((-18.0, 4.0, 0.0))
    arm, root = spawn_player(
        "France", FRANCE_BLUE, start, ATTACK_YAW, actions=["run"], split=(FRANCE_BLUE, FRANCE_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    keys = []
    for f in range(1, frames + 1, 3):
        t = (f - 1) / max(1, frames - 1)
        # slow with heavier sway
        sway = 0.18 * math.sin(t * math.pi * 3.0)
        p = _lerp(start, end, ease(t * 0.85))
        p.y += sway
        p.z = -0.05 * abs(math.sin(t * 6.0))
        keys.append((f, p))
    keys.append((frames, end))
    animate_root(root, keys, ATTACK_YAW)
    # slower run via stretched once segments loop feel
    add_nla_once(arm, "run", 1, frames)  # stretched slow by scale in add_nla_once over full length
    add_talk_strip(arm, "FranceTiredTalk", frames, _sad_fn(0.14), TALK_BONES, step=3)

    cam = setup_new_cam("Cam24", lens=34)
    _cam_dense(
        cam, 1, frames,
        Vector((2.0, -10.0, 3.5)), Vector((-12.0, -9.0, 3.2)),
        Vector((-5.0, 3.0, 1.4)), Vector((-18.0, 4.0, 1.2)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 25 — air walk goal
# ---------------------------------------------------------------------------
def build_25() -> int:
    frames = 156
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    start = Vector((-40.0, 0.5, 0.0))
    cruise_z = 4.6
    mid = Vector((-70.0, 0.3, cruise_z))
    kick = Vector((GOAL_X + 24.0, 0.0, cruise_z))
    arm, root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, start, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    keys = []
    for f in range(1, frames + 1, 2):
        if f <= 28:
            t = ease((f - 1) / 27.0)
            p = _lerp(start, Vector((-48.0, 0.4, cruise_z)), t)
        elif f <= 110:
            t = ease((f - 28) / 81.0)
            p = _lerp(Vector((-48.0, 0.4, cruise_z)), kick, t)
            p.z = cruise_z + 0.25 * math.sin(f * 0.15)
        else:
            p = kick.copy()
            p.z = cruise_z
        keys.append((f, p))
    animate_root(root, keys, ATTACK_YAW)
    add_nla_loop(arm, "run", 1, 109)
    add_nla_once(arm, "fight_kick", 110, 132)
    add_nla_hold(arm, "fight_idle", 133, frames, af=6)

    ball = clear_ball_anim()
    goal = Vector((GOAL_X - 1.5, -GOAL_INNER_HALF_W * 0.4, GOAL_H * 0.7))

    def path(f: int) -> Vector:
        # player sample
        loc = start
        for kf, p in keys:
            if kf <= f:
                loc = p
            else:
                break
        if f < 110:
            return ball_ahead_of(loc, ATTACK_DIR, f, arm=arm, z=loc.z + 0.45)
        if f <= 118:
            return ball_ahead_of(kick, ATTACK_DIR, f, arm=arm, z=kick.z + 0.4)
        u = ease((f - 118) / max(1, 138 - 118))
        return goal if f > 138 else _shot_arc(
            ball_ahead_of(kick, ATTACK_DIR, 118, arm=arm, z=kick.z + 0.4), goal, u, 2.0
        )

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam25", lens=28)
    _cam_dense(
        cam, 1, 50,
        Vector((-30.0, -18.0, 6.5)), Vector((-55.0, -16.0, 7.5)),
        Vector((-45.0, 0.5, 3.5)), Vector((-65.0, 0.3, 4.5)),
        step=2,
    )
    _cam_dense(
        cam, 50, frames,
        Vector((-55.0, -16.0, 7.5)), Vector((GOAL_X + 22.0, -12.0, 5.5)),
        Vector((-65.0, 0.3, 4.5)), Vector((GOAL_X, 0.0, 2.5)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 26 — celebrate
# ---------------------------------------------------------------------------
def build_26() -> int:
    frames = 108
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    gap = SIDE_GAP
    base = Vector((-8.0, 0.0, 0.0))
    offsets = [(-gap, 0.0), (0.0, 0.0), (gap, 0.0)]
    yaws = [0.15, yaw_face_neg_y(), -0.15]
    for i, ((ox, oy), yaw) in enumerate(zip(offsets, yaws)):
        pos = Vector((base.x + ox, base.y + oy, 0.0))
        arm, root = spawn_player(
            f"Shaolin_{i}",
            SHAOLIN_ORANGE,
            pos,
            yaw,
            actions=["idle"],
            split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
        )
        _clear_all_nla(arm)
        # gentle root bob only — arms stay idle
        keys = []
        for f in range(1, frames + 1, 3):
            z = 0.04 * abs(math.sin(f * 0.22 + i))
            keys.append((f, Vector((pos.x, pos.y, z))))
        animate_root(root, keys, yaw)
        add_nla_loop(arm, "idle", 1, frames)
        add_talk_strip(arm, f"ShaolinCelebrate{i}", frames, _happy_fn(), TALK_BONES, step=3)

    cam = setup_new_cam("Cam26", lens=32)
    _cam_dense(
        cam, 1, frames,
        Vector((-8.0, -12.0, 4.0)), Vector((-6.0, -10.5, 3.6)),
        Vector((-8.0, 0.0, 1.6)), Vector((-8.0, 0.2, 1.7)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 27 — France interview
# ---------------------------------------------------------------------------
def build_27() -> int:
    frames = 168
    remove_players()
    set_frame_range(frames)
    hide_ball()
    _hide_pitch_studio(("Light", "Sun", "World", "Camera", "Cam", "France_", "Interview_"))
    _interview_set(FRANCE_BLUE, FRANCE_RED)
    pos = Vector((0.0, 0.0, 0.35))
    arm, root = spawn_player(
        "France", FRANCE_BLUE, pos, yaw_face_neg_y(), actions=["idle"], split=(FRANCE_BLUE, FRANCE_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_loop(arm, "idle", 1, frames)
    add_talk_strip(arm, "FranceInterviewTalk", frames, _talk_fn(1.0), TALK_BONES, step=2)

    cam = setup_new_cam("Cam27", lens=35)
    # bust-medium
    _cam_dense(
        cam, 1, frames,
        Vector((-0.5, -7.2, 3.35)), Vector((-0.35, -6.6, 3.4)),
        Vector((0.05, 0.1, 3.05)), Vector((0.0, 0.1, 3.1)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 28 — phone disappoint
# ---------------------------------------------------------------------------
def build_28() -> int:
    frames = 108
    remove_players()
    _show_pitch()
    _clear_extras("Phone_")
    set_frame_range(frames)
    hide_ball()
    pos = Vector((-10.0, 2.0, -0.85))
    arm, root = spawn_player(
        "France", FRANCE_BLUE, pos, yaw_face_neg_y(), actions=["idle"], split=(FRANCE_BLUE, FRANCE_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_hold(arm, "idle", 1, frames, af=12)
    add_talk_strip(arm, "FrancePhoneSad", frames, _sad_fn(0.22), TALK_BONES, step=3)

    phone_mat = mat_rgba("Phone_Mat", (0.08, 0.08, 0.1, 1.0), 0.35)
    hand = Vector((pos.x + 0.3, pos.y - 0.55, 1.1))
    phone = add_box("Phone_01", (0.1, 0.05, 0.18), hand, phone_mat)
    for f in range(1, frames + 1, 3):
        wiggle = 0.02 * math.sin(f * 0.25)
        phone.location = hand + Vector((wiggle, 0.0, 0.01 * math.cos(f * 0.3)))
        phone.keyframe_insert(data_path="location", frame=f)
    force_linear(phone)

    cam = setup_new_cam("Cam28", lens=42)
    _cam_dense(
        cam, 1, frames,
        Vector((-8.8, -5.5, 2.2)), Vector((-9.2, -5.0, 2.0)),
        Vector((-10.0, 1.9, 1.0)), Vector((-10.0, 1.8, 0.85)),
        step=3,
    )
    finish_cam(cam)
    return frames


BUILDERS = {
    "18": build_18,
    "19": build_19,
    "20": build_20,
    "21": build_21,
    "22": build_22,
    "23": build_23,
    "24": build_24,
    "25": build_25,
    "26": build_26,
    "27": build_27,
    "28": build_28,
}
