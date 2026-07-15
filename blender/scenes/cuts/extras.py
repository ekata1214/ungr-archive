# SPDX-License-Identifier: MIT
"""Extra cuts 38–42 — commentators, NL bench, Norway dribble, Shaolin rage, breakdance steal."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Sequence, Tuple

import bpy
from mathutils import Vector

from animate_soccer_match import (  # noqa: E402
    BALL_GROUND_Z,
    _clear_all_nla,
    _clear_anim,
    _kf_loc,
    _kf_rot_z,
)

from cuts.common import (  # noqa: E402
    COMMENTATOR_WHITE,
    FPS,
    FRANCE_BLUE,
    FRANCE_WHITE,
    NETHERLANDS_DARK,
    NETHERLANDS_ORANGE,
    NORWAY_RED,
    NORWAY_WHITE,
    SHAOLIN_ORANGE,
    SHAOLIN_WHITE,
    SIDE_GAP,
    SIT_BONES,
    TALK_BONES,
    add_box,
    add_nla_hold,
    add_nla_loop,
    add_nla_once,
    add_pose_strip,
    add_talk_strip,
    animate_root,
    ball_ahead_of,
    clear_ball_anim,
    ease,
    finish_cam,
    force_linear,
    hide_ball,
    key_ball,
    kf_cam,
    mat_rgba,
    remove_players,
    set_frame_range,
    setup_new_cam,
    spawn_france,
    spawn_player,
    yaw_face_neg_y,
    yaw_face_pos_x,
)


def _lerp(a: Vector, b: Vector, t: float) -> Vector:
    return a.lerp(b, t)


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


def _show_pitch() -> None:
    for obj in list(bpy.data.objects):
        if obj.name == "Ball" or obj.name.startswith(
            ("Field_", "Line_", "Pen", "Goal", "Corner_", "Net", "Post", "Crossbar")
        ):
            obj.hide_render = False
            obj.hide_viewport = False


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


def _clear_extras(*prefixes: str) -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def _talk_fn(amp: float = 1.0, phase: float = 0.0) -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS + phase
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


def _bench_sit_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """Seated on a bench — knees bent forward, upright torso (less sumo-squat)."""
    u = 1.0
    return {
        "thigh.l": (0.95 * u, 0.08 * u, 0.12 * u),
        "calf.l": (-1.05 * u, 0.0, 0.0),
        "foot.l": (0.2 * u, 0.0, 0.0),
        "thigh.r": (0.95 * u, -0.08 * u, -0.12 * u),
        "calf.r": (-1.05 * u, 0.0, 0.0),
        "foot.r": (0.2 * u, 0.0, 0.0),
        "pelvis": (0.12 * u, 0.0, 0.0),
        "spine_01": (0.05 * u, 0.0, 0.0),
        "spine_02": (0.04 * u, 0.0, 0.0),
        "neck_01": (0.02 * u, 0.0, 0.0),
        "head": (0.02 * u, 0.0, 0.0),
    }


def _angry_stomping(phase: float = 0.0) -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS + phase
        stomp = 0.12 * abs(math.sin(t * 14.0))
        shake = 0.08 * math.sin(t * 18.0)
        return {
            "spine_01": (0.12 + stomp * 0.3, 0.0, shake * 0.4),
            "spine_02": (0.16 + stomp * 0.4, 0.0, shake * 0.5),
            "neck_01": (0.14 + stomp * 0.5, 0.0, shake * 0.7),
            "head": (0.18 + stomp * 0.6, 0.0, shake),
            "thigh.l": (0.15 * abs(math.sin(t * 14.0)), 0.05, 0.08),
            "thigh.r": (0.15 * abs(math.sin(t * 14.0 + math.pi)), -0.05, -0.08),
            "calf.l": (-0.2 * abs(math.sin(t * 14.0)), 0.0, 0.0),
            "calf.r": (-0.2 * abs(math.sin(t * 14.0 + math.pi)), 0.0, 0.0),
        }

    return deltas


STOMP_BONES = [
    "thigh.l", "calf.l", "foot.l", "thigh.r", "calf.r", "foot.r",
    "pelvis", "spine_01", "spine_02", "neck_01", "head",
]


def _animate_root_yaw(
    root: bpy.types.Object,
    keys: Sequence[Tuple[int, Vector]],
    yaw_fn,
) -> None:
    _clear_anim(root)
    for f, loc in keys:
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, float(yaw_fn(f)))
    force_linear(root)


# ---------------------------------------------------------------------------
# 38 — Two white commentators at a press/broadcast desk
# ---------------------------------------------------------------------------
def build_38() -> int:
    frames = 168
    remove_players()
    set_frame_range(frames)
    hide_ball()
    _hide_pitch_studio(("Light", "Sun", "World", "Camera", "Cam", "Commentator_", "Desk_", "Mic_", "Interview_"))
    _clear_extras("Desk_", "Mic_", "Interview_")

    floor = mat_rgba("Desk_FloorMat", (0.1, 0.1, 0.12, 1.0), 0.9)
    desk_m = mat_rgba("Desk_TopMat", (0.18, 0.16, 0.14, 1.0), 0.55)
    back_m = mat_rgba("Desk_BackMat", (0.08, 0.1, 0.14, 1.0), 0.8)
    stripe = mat_rgba("Desk_StripeMat", (0.75, 0.75, 0.78, 1.0), 0.45)
    mic_m = mat_rgba("Mic_Mat", (0.04, 0.04, 0.05, 1.0), 0.4)
    add_box("Desk_Floor", (10.0, 7.0, 0.1), Vector((0.0, 0.4, 0.05)), floor)
    add_box("Desk_Backdrop", (10.0, 0.15, 5.0), Vector((0.0, 3.0, 2.5)), back_m)
    add_box("Desk_Banner", (9.0, 0.12, 0.5), Vector((0.0, 2.88, 4.2)), stripe)
    # Wide desk like a broadcast / press table
    add_box("Desk_Table", (5.5, 1.2, 0.12), Vector((0.0, 0.55, 1.05)), desk_m)
    add_box("Desk_Front", (5.5, 0.1, 0.9), Vector((0.0, 0.0, 0.55)), desk_m)
    add_box("Mic_L", (0.06, 0.06, 0.22), Vector((-1.4, 0.7, 1.25)), mic_m)
    add_box("Mic_R", (0.06, 0.06, 0.22), Vector((1.4, 0.7, 1.25)), mic_m)

    gap = SIDE_GAP
    # Sit ON chairs behind desk (z positive = hips near seat height)
    a_pos = Vector((-gap * 0.55, 1.15, 0.15))
    b_pos = Vector((gap * 0.55, 1.15, 0.15))
    yaw = yaw_face_neg_y()
    # Simple stools under them
    stool_m = mat_rgba("Desk_StoolMat", (0.22, 0.2, 0.18, 1.0), 0.6)
    add_box("Desk_StoolA", (0.7, 0.7, 0.08), Vector((a_pos.x, a_pos.y + 0.15, 0.55)), stool_m)
    add_box("Desk_StoolB", (0.7, 0.7, 0.08), Vector((b_pos.x, b_pos.y + 0.15, 0.55)), stool_m)

    a_arm, a_root = spawn_player(
        "Commentator_A", COMMENTATOR_WHITE, a_pos, yaw, actions=["idle"],
        split=(COMMENTATOR_WHITE, COMMENTATOR_WHITE, 0.42),
    )
    b_arm, b_root = spawn_player(
        "Commentator_B", COMMENTATOR_WHITE, b_pos, yaw, actions=["idle"],
        split=(COMMENTATOR_WHITE, COMMENTATOR_WHITE, 0.42),
    )
    _clear_all_nla(a_arm)
    _clear_all_nla(b_arm)
    animate_root(a_root, [(1, a_pos), (frames, a_pos)], yaw)
    animate_root(b_root, [(1, b_pos), (frames, b_pos)], yaw)
    add_nla_hold(a_arm, "idle", 1, frames, af=12)
    add_nla_hold(b_arm, "idle", 1, frames, af=12)
    add_pose_strip(a_arm, "CommSitA", frames, _bench_sit_deltas, SIT_BONES, step=3, clamp=1.5)
    add_pose_strip(b_arm, "CommSitB", frames, _bench_sit_deltas, SIT_BONES, step=3, clamp=1.5)
    add_talk_strip(a_arm, "CommTalkA", frames, _talk_fn(1.15, 0.0), TALK_BONES, step=2)
    add_talk_strip(b_arm, "CommTalkB", frames, _talk_fn(1.0, 1.7), TALK_BONES, step=2)

    cam = setup_new_cam("Cam38", lens=34)
    _cam_dense(
        cam, 1, frames,
        Vector((0.0, -7.5, 3.4)), Vector((0.3, -6.8, 3.3)),
        Vector((0.0, 0.8, 1.9)), Vector((0.0, 0.9, 1.95)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 39 — Netherlands bench: ~10 seated, talking in pairs
# ---------------------------------------------------------------------------
def build_39() -> int:
    frames = 180
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    _clear_extras("Bench_")

    seat_m = mat_rgba("Bench_SeatMat", (0.12, 0.12, 0.13, 1.0), 0.75)
    leg_m = mat_rgba("Bench_LegMat", (0.2, 0.2, 0.22, 1.0), 0.7)
    n_players = 10
    seat_gap = 2.0  # teammate spacing (bench row)
    bench_len = (n_players - 1) * seat_gap + 2.4
    bench_y = 22.0
    bench_z = 0.45
    add_box("Bench_Seat", (bench_len, 0.7, 0.12), Vector((0.0, bench_y, bench_z)), seat_m)
    add_box("Bench_Back", (bench_len, 0.1, 0.55), Vector((0.0, bench_y + 0.35, bench_z + 0.4)), seat_m)
    add_box("Bench_LegL", (0.15, 0.55, 0.45), Vector((-bench_len * 0.45, bench_y, 0.22)), leg_m)
    add_box("Bench_LegR", (0.15, 0.55, 0.45), Vector((bench_len * 0.45, bench_y, 0.22)), leg_m)

    yaw = yaw_face_neg_y()
    start_x = -((n_players - 1) * seat_gap) * 0.5
    for i in range(n_players):
        x = start_x + i * seat_gap
        # slight pair lean: even look toward next, odd look toward prev
        pair_yaw = yaw + (0.22 if i % 2 == 0 else -0.22)
        # hips on the bench seat
        pos = Vector((x, bench_y - 0.08, 0.12))
        arm, root = spawn_player(
            f"Netherlands_{i}",
            NETHERLANDS_ORANGE,
            pos,
            pair_yaw,
            actions=["idle"],
            split=(NETHERLANDS_ORANGE, NETHERLANDS_DARK, 0.42),
        )
        _clear_all_nla(arm)
        animate_root(root, [(1, pos), (frames, pos)], pair_yaw)
        add_nla_hold(arm, "idle", 1, frames, af=10)
        add_pose_strip(arm, f"NLBenchSit{i}", frames, _bench_sit_deltas, SIT_BONES, step=4, clamp=1.5)
        # Pairs share similar talk phase so they look conversing
        pair_phase = (i // 2) * 1.3 + (0.0 if i % 2 == 0 else 0.9)
        add_talk_strip(arm, f"NLBenchTalk{i}", frames, _talk_fn(0.85 + 0.1 * (i % 2), pair_phase), TALK_BONES, step=3)

    cam = setup_new_cam("Cam39", lens=26)
    _cam_dense(
        cam, 1, frames,
        Vector((-10.0, bench_y - 16.0, 6.0)), Vector((8.0, bench_y - 14.0, 5.2)),
        Vector((0.0, bench_y, 1.7)), Vector((0.0, bench_y, 1.8)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 40 — Single Norway player dribbling
# ---------------------------------------------------------------------------
def build_40() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    start = Vector((-35.0, 2.0, 0.0))
    end = Vector((10.0, -1.5, 0.0))
    move = (end - start).normalized()
    yaw = math.atan2(move.y, move.x)

    arm, root = spawn_player(
        "Norway", NORWAY_RED, start, yaw, actions=["run"], split=(NORWAY_RED, NORWAY_WHITE, 0.42)
    )
    _clear_all_nla(arm)

    keys = []
    for f in range(1, frames + 1, 2):
        t = (f - 1) / max(1, frames - 1)
        p = _lerp(start, end, ease(t))
        # zig dribble lane
        p.y += 1.6 * math.sin(t * math.pi * 3.0)
        keys.append((f, p))
    keys.append((frames, end + Vector((0.0, 1.6 * math.sin(math.pi * 3.0), 0.0))))
    animate_root(root, keys, yaw)
    add_nla_loop(arm, "run", 1, frames)

    ball = clear_ball_anim()

    def path(f: int) -> Vector:
        loc = start
        for kf, p in keys:
            if kf <= f:
                loc = p
            else:
                break
        return ball_ahead_of(loc, move, f, arm=arm)

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam40", lens=34)

    def cam_pos(f: int) -> Vector:
        b = path(f)
        # Keep player+ball framed — trail slightly wider
        return Vector((b.x - 5.5, b.y - 11.0, 3.6))

    def cam_tgt(f: int) -> Vector:
        b = path(f)
        return Vector((b.x + 2.5, b.y * 0.25, 1.3))

    for f in range(1, frames + 1, 2):
        kf_cam(cam, f, cam_pos(f), cam_tgt(f))
    kf_cam(cam, frames, cam_pos(frames), cam_tgt(frames))
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 41 — Three Shaolin stomping in frustration
# ---------------------------------------------------------------------------
def build_41() -> int:
    frames = 144
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    gap = SIDE_GAP
    base = Vector((-5.0, 1.0, 0.0))
    offsets = [(-gap, 0.2), (0.0, -0.3), (gap, 0.1)]
    yaws = [yaw_face_neg_y() + 0.12, yaw_face_neg_y(), yaw_face_neg_y() - 0.12]

    for i, ((ox, oy), yaw) in enumerate(zip(offsets, yaws)):
        pos = Vector((base.x + ox, base.y + oy, 0.0))
        arm, root = spawn_player(
            f"Shaolin_{i}",
            SHAOLIN_ORANGE,
            pos,
            yaw,
            actions=["idle", "fight_idle"],
            split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
        )
        _clear_all_nla(arm)
        keys = []
        for f in range(1, frames + 1, 2):
            # 地団駄 — alternate hop stomps
            phase = f * 0.55 + i * 1.4
            z = 0.22 * abs(math.sin(phase))
            keys.append((f, Vector((pos.x, pos.y, z))))
        keys.append((frames, pos.copy()))
        animate_root(root, keys, yaw)
        add_nla_hold(arm, "fight_idle", 1, frames, af=8)
        add_pose_strip(arm, f"ShaolinStomp{i}", frames, _angry_stomping(i * 0.7), STOMP_BONES, step=2, clamp=1.4)

    cam = setup_new_cam("Cam41", lens=32)
    _cam_dense(
        cam, 1, frames,
        Vector((-5.0, -11.0, 3.6)), Vector((-4.0, -10.0, 3.3)),
        Vector((-5.0, 1.0, 1.5)), Vector((-5.0, 1.2, 1.55)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 42 — Shaolin breakdances while stealing ball from France
# ---------------------------------------------------------------------------
def build_42() -> int:
    frames = 180
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    fr_start = Vector((-20.0, 1.5, 0.0))
    fr_mid = Vector((-5.0, 0.8, 0.0))
    sh_start = Vector((8.0, -SIDE_GAP * 0.9, 0.0))
    steal_at = Vector((-2.0, 0.3, 0.0))
    sh_end = Vector((-28.0, -1.0, 0.0))
    ATTACK = Vector((-1.0, 0.0, 0.0))
    yaw_fr = math.atan2(ATTACK.y, ATTACK.x)
    yaw_sh0 = yaw_face_pos_x()

    fr_arm, fr_root = spawn_france("France", fr_start, yaw_fr, actions=["run", "idle", "fight_idle"])
    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, sh_start, yaw_sh0,
        actions=["run", "fight_idle", "fight_kick", "jump_full"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(fr_arm)
    _clear_all_nla(sh_arm)

    f_approach, f_spin0, f_steal, f_exit = 50, 70, 95, 110

    fr_keys = []
    for f in range(1, f_steal + 1, 2):
        t = ease((f - 1) / max(1, f_steal - 1))
        fr_keys.append((f, _lerp(fr_start, fr_mid, t)))
    fr_keys += [(f_steal, fr_mid), (frames, fr_mid + Vector((1.5, 0.8, 0.0)))]
    animate_root(fr_root, fr_keys, yaw_fr)
    add_nla_loop(fr_arm, "run", 1, f_steal - 1)
    add_nla_hold(fr_arm, "fight_idle", f_steal, frames, af=6)

    def sh_yaw(f: int) -> float:
        if f < f_spin0:
            return yaw_sh0
        if f < f_steal + 8:
            # Breakdance spins
            return yaw_sh0 + (f - f_spin0) * 0.55
        return math.atan2(ATTACK.y, ATTACK.x)

    sh_keys = []
    for f in range(1, frames + 1, 2):
        if f <= f_approach:
            t = ease((f - 1) / max(1, f_approach - 1))
            p = _lerp(sh_start, steal_at, t)
        elif f <= f_steal:
            # spin on the spot, slight crouch
            t = (f - f_approach) / max(1, f_steal - f_approach)
            bob = 0.35 * abs(math.sin(t * math.pi * 4.0))
            p = Vector((steal_at.x, steal_at.y, bob))
        elif f <= f_exit:
            t = ease((f - f_steal) / max(1, f_exit - f_steal))
            p = _lerp(steal_at, sh_end * 0.4 + steal_at * 0.6, t)
            p.z = 0.0
        else:
            t = ease((f - f_exit) / max(1, frames - f_exit))
            p = _lerp(steal_at * 0.4 + sh_end * 0.6, sh_end, t)
        sh_keys.append((f, p))
    sh_keys.append((frames, sh_end))
    _animate_root_yaw(sh_root, sh_keys, sh_yaw)
    add_nla_loop(sh_arm, "run", 1, f_spin0 - 1)
    add_nla_once(sh_arm, "jump_full", f_spin0, f_steal + 4)
    add_nla_once(sh_arm, "fight_kick", f_steal - 2, f_steal + 16)
    add_nla_loop(sh_arm, "run", f_exit, frames)

    ball = clear_ball_anim()

    def path(f: int) -> Vector:
        # France dribbles, then Shaolin takes over after steal
        if f < f_steal:
            loc = fr_start
            for kf, p in fr_keys:
                if kf <= f:
                    loc = p
                else:
                    break
            return ball_ahead_of(loc, ATTACK, f, arm=fr_arm)
        loc = steal_at
        for kf, p in sh_keys:
            if kf <= f:
                loc = p
            else:
                break
        return ball_ahead_of(loc, ATTACK, f, arm=sh_arm)

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam42", lens=34)

    def cam_pos(f: int) -> Vector:
        b = path(f)
        if f_spin0 <= f <= f_steal + 10:
            ang = (f - f_spin0) * 0.12
            return Vector((b.x + 7.5 * math.cos(ang), b.y + 7.5 * math.sin(ang) - 1.5, 3.8))
        return Vector((b.x - 4.0, b.y - 11.0, 3.4))

    def cam_tgt(f: int) -> Vector:
        b = path(f)
        return Vector((b.x + 1.0, b.y * 0.25, max(1.1, b.z + 0.6)))

    for f in range(1, frames + 1, 2):
        kf_cam(cam, f, cam_pos(f), cam_tgt(f))
    kf_cam(cam, frames, cam_pos(frames), cam_tgt(frames))
    finish_cam(cam)
    return frames


BUILDERS: Dict[str, Callable[[], int]] = {
    "38": build_38,
    "39": build_39,
    "40": build_40,
    "41": build_41,
    "42": build_42,
}
