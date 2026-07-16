# SPDX-License-Identifier: MIT
"""Extra cuts 38–44 — commentators, NL bench, dribble, stomp, breakdance, France phone-stomp."""

from __future__ import annotations

import math
from typing import Callable, Dict, Sequence, Tuple

import bpy
from mathutils import Euler, Vector

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
    NETHERLANDS_DARK,
    NETHERLANDS_ORANGE,
    NORWAY_RED,
    NORWAY_WHITE,
    PHONE_ARM_BONES,
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
    parent_phone_to_hand,
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


def _talk_fn(amp: float = 1.0, phase: float = 0.0, look_up: float = 0.0) -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS + phase
        nod = amp * (0.07 * math.sin(t * 6.8) + 0.04 * math.sin(t * 10.5))
        turn = amp * (0.1 * math.sin(t * 2.2 + 0.3) + 0.05 * math.sin(t * 4.7))
        lean = amp * 0.05 * math.sin(t * 1.6)
        # look_up < 0 faces camera from a raised cam (rig: neg neck X ≈ look up)
        base = look_up
        return {
            "spine_01": (0.025 + lean * 0.4 + base * 0.15, 0.0, turn * 0.25),
            "spine_02": (0.045 + lean + base * 0.2, 0.0, turn * 0.4),
            "neck_01": (0.04 + nod * 0.65 + base, 0.0, turn * 0.75),
            "head": (0.05 + nod + base * 0.85, 0.0, turn),
        }

    return deltas


def _chair_sit_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """Absolute chair sit (use add_pose_strip(..., absolute=True)).

    L knee on +X / R on −X of pelvis (no crossed shins — that looked 左右逆).
    Probed footspan ~1.4 with feet toward camera.
    """
    u = 1.0
    return {
        "thigh.l": (0.3 * u, -0.7 * u, -1.1 * u),
        "calf.l": (0.35 * u, 0.08 * u, 0.0),
        "foot.l": (-0.15 * u, 0.1 * u, 0.05 * u),
        "thigh.r": (0.3 * u, 0.7 * u, 1.1 * u),
        "calf.r": (0.35 * u, -0.08 * u, 0.0),
        "foot.r": (-0.15 * u, -0.1 * u, -0.05 * u),
        "pelvis": (0.2 * u, 0.0, 0.0),
        "spine_01": (-0.04 * u, 0.0, 0.0),
        "spine_02": (-0.02 * u, 0.0, 0.0),
        "neck_01": (-0.1 * u, 0.0, 0.0),
        "head": (-0.08 * u, 0.0, 0.0),
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


def _phone_clamp_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """Absolute pose: stomp legs + hands meeting at chest around the phone.

    Use with add_pose_strip(..., absolute=True, clamp≥2.0).
    """
    stomp = _angry_stomping(0.2)(frame)
    # Keep stomp thigh/calf motion as incremental-ish absolute (small)
    return {
        "thigh.l": (0.12 * abs(math.sin(frame / FPS * 14.0 + 0.2)), 0.05, 0.06),
        "thigh.r": (0.12 * abs(math.sin(frame / FPS * 14.0 + 0.2 + math.pi)), -0.05, -0.06),
        "calf.l": (-0.15 * abs(math.sin(frame / FPS * 14.0 + 0.2)), 0.0, 0.0),
        "calf.r": (-0.15 * abs(math.sin(frame / FPS * 14.0 + 0.2 + math.pi)), 0.0, 0.0),
        "foot.l": (0.05, 0.0, 0.0),
        "foot.r": (0.05, 0.0, 0.0),
        "pelvis": (0.08, 0.0, 0.0),
        "clavicle.l": (0.1, 0.15, 0.1),
        "upperarm.l": (-1.55, -1.55, 0.2),
        "lowerarm.l": (-1.9, -0.35, 0.05),
        "hand.l": (0.3, 0.5, 0.4),
        "clavicle.r": (0.1, -0.15, -0.1),
        "upperarm.r": (-1.55, 1.55, -0.2),
        "lowerarm.r": (-1.9, 0.35, -0.05),
        "hand.r": (0.3, -0.5, -0.4),
        "spine_01": (0.06 + stomp.get("spine_01", (0, 0, 0))[0] * 0.3, 0.0, 0.0),
        "spine_02": (0.08, 0.0, 0.0),
        "neck_01": (-0.06, 0.0, 0.0),
        "head": (-0.05, 0.0, 0.0),
    }


def _windmill_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """Breakdance windmill — wide open V-legs kicking opposite, arms sweeping."""
    t = frame / FPS
    ph = t * 11.0
    a = math.sin(ph)
    b = math.cos(ph)
    return {
        # Big V: thighs open hard, calves bent; alternate which leg is higher
        "thigh.l": (1.55 + 0.35 * a, 1.05, 0.65 + 0.25 * b),
        "calf.l": (-1.55, 0.15, 0.0),
        "foot.l": (0.45, 0.1, 0.2),
        "thigh.r": (1.55 - 0.35 * a, -1.05, -0.65 - 0.25 * b),
        "calf.r": (-1.55, -0.15, 0.0),
        "foot.r": (0.45, -0.1, -0.2),
        "pelvis": (0.2, 0.0, 0.1 * a),
        "clavicle.l": (0.25, 0.35, 0.25),
        "upperarm.l": (-0.2 - 1.0 * b, 1.35, 0.7),
        "lowerarm.l": (-1.0, 0.3, 0.2),
        "hand.l": (0.25, 0.35, 0.3),
        "clavicle.r": (0.25, -0.35, -0.25),
        "upperarm.r": (-0.2 + 1.0 * b, -1.35, -0.7),
        "lowerarm.r": (-1.0, -0.3, -0.2),
        "hand.r": (0.25, -0.35, -0.3),
        "spine_01": (0.3, 0.0, 0.15 * a),
        "spine_02": (0.25, 0.0, 0.12 * b),
        "neck_01": (0.12, 0.0, 0.0),
        "head": (0.18, 0.0, 0.0),
    }


def _breakdance_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """Alias — windmill is the breakdance move for cut 42."""
    return _windmill_deltas(frame)


STOMP_BONES = [
    "thigh.l", "calf.l", "foot.l", "thigh.r", "calf.r", "foot.r",
    "pelvis", "spine_01", "spine_02", "neck_01", "head",
]
BREAK_BONES = STOMP_BONES + [
    "clavicle.l", "upperarm.l", "lowerarm.l", "hand.l",
    "clavicle.r", "upperarm.r", "lowerarm.r", "hand.r",
]
PHONE_STOMP_BONES = list(dict.fromkeys(STOMP_BONES + PHONE_ARM_BONES))


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


def _animate_root_euler(
    root: bpy.types.Object,
    keys: Sequence[Tuple[int, Vector, Euler]],
) -> None:
    """Full euler keys — used for floor breakdance (pitch + spin)."""
    _clear_anim(root)
    for f, loc, eul in keys:
        _kf_loc(root, f, loc)
        root.rotation_euler = eul
        root.keyframe_insert(data_path="rotation_euler", frame=f)
    force_linear(root)


# ---------------------------------------------------------------------------
# 38 — News desk: tall front hides legs; chairs visible; high face cam
# ---------------------------------------------------------------------------
def build_38() -> int:
    frames = 168
    remove_players()
    set_frame_range(frames)
    hide_ball()
    _hide_pitch_studio(("Light", "Sun", "World", "Camera", "Cam", "Commentator_", "Desk_", "Mic_", "Interview_"))
    _clear_extras("Desk_", "Mic_", "Interview_")

    floor = mat_rgba("Desk_FloorMat", (0.1, 0.1, 0.12, 1.0), 0.9)
    desk_m = mat_rgba("Desk_TopMat", (0.22, 0.18, 0.14, 1.0), 0.5)
    chair_m = mat_rgba("Desk_ChairMat", (0.16, 0.14, 0.12, 1.0), 0.6)
    back_m = mat_rgba("Desk_BackMat", (0.08, 0.1, 0.14, 1.0), 0.8)
    stripe = mat_rgba("Desk_StripeMat", (0.75, 0.75, 0.78, 1.0), 0.45)
    mic_m = mat_rgba("Mic_Mat", (0.04, 0.04, 0.05, 1.0), 0.4)
    add_box("Desk_Floor", (12.0, 8.0, 0.1), Vector((0.0, 0.5, 0.05)), floor)
    add_box("Desk_Backdrop", (12.0, 0.15, 5.5), Vector((0.0, 3.4, 2.7)), back_m)
    add_box("Desk_Banner", (10.0, 0.12, 0.55), Vector((0.0, 3.28, 4.5)), stripe)

    # Tall news desk: front hides legs; only heads + upper torso above tabletop
    table_top_z = 2.15
    add_box("Desk_Table", (6.5, 1.4, 0.12), Vector((0.0, 0.2, table_top_z)), desk_m)
    add_box("Desk_Front", (6.5, 0.16, table_top_z + 0.05), Vector((0.0, -0.45, table_top_z * 0.5)), desk_m)
    add_box("Desk_LegL", (0.2, 1.1, table_top_z), Vector((-2.95, 0.25, table_top_z * 0.5)), desk_m)
    add_box("Desk_LegR", (0.2, 1.1, table_top_z), Vector((2.95, 0.25, table_top_z * 0.5)), desk_m)

    gap = SIDE_GAP
    # Root so pelvis ≈ seat; faces clear just above table (~2.7)
    seat_z = 1.15
    a_pos = Vector((-gap * 0.55, 1.95, -0.85))
    b_pos = Vector((gap * 0.55, 1.95, -0.85))
    yaw = yaw_face_neg_y()
    for name, px in (("Desk_ChairA", a_pos.x), ("Desk_ChairB", b_pos.x)):
        add_box(f"{name}_Seat", (1.0, 0.95, 0.12), Vector((px, 2.15, seat_z)), chair_m)
        add_box(f"{name}_Back", (1.0, 0.14, 1.2), Vector((px, 2.6, seat_z + 0.75)), chair_m)
        add_box(f"{name}_LegFL", (0.12, 0.12, seat_z), Vector((px - 0.38, 1.85, seat_z * 0.5)), chair_m)
        add_box(f"{name}_LegFR", (0.12, 0.12, seat_z), Vector((px + 0.38, 1.85, seat_z * 0.5)), chair_m)
        add_box(f"{name}_LegBL", (0.12, 0.12, seat_z), Vector((px - 0.38, 2.4, seat_z * 0.5)), chair_m)
        add_box(f"{name}_LegBR", (0.12, 0.12, seat_z), Vector((px + 0.38, 2.4, seat_z * 0.5)), chair_m)

    add_box("Mic_L", (0.07, 0.07, 0.28), Vector((-1.45, 0.4, table_top_z + 0.2)), mic_m)
    add_box("Mic_R", (0.07, 0.07, 0.28), Vector((1.45, 0.4, table_top_z + 0.2)), mic_m)

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
    add_pose_strip(a_arm, "CommSitA", frames, _chair_sit_deltas, SIT_BONES, step=3, clamp=1.7, absolute=True)
    add_pose_strip(b_arm, "CommSitB", frames, _chair_sit_deltas, SIT_BONES, step=3, clamp=1.7, absolute=True)
    # Face-cam talk: slight look-up so fronts of heads read from raised cam
    add_talk_strip(a_arm, "CommTalkA", frames, _talk_fn(1.0, 0.0, look_up=-0.18), TALK_BONES, step=2)
    add_talk_strip(b_arm, "CommTalkB", frames, _talk_fn(0.9, 1.7, look_up=-0.18), TALK_BONES, step=2)

    # Raised cam, slightly above face level; keep heads fully in frame
    cam = setup_new_cam("Cam38", lens=32)
    face = Vector((0.0, 1.95, 2.75))
    _cam_dense(
        cam, 1, frames,
        Vector((0.1, -5.2, 3.85)), Vector((-0.05, -4.9, 3.8)),
        face, face + Vector((0.04, 0.04, 0.03)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 39 — Netherlands bench: correct chair-style sit (not creepy splay)
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
    seat_gap = 2.0
    bench_len = (n_players - 1) * seat_gap + 2.4
    bench_y = 22.0
    seat_z = 1.35
    add_box("Bench_Seat", (bench_len, 0.85, 0.14), Vector((0.0, bench_y, seat_z)), seat_m)
    add_box("Bench_Back", (bench_len, 0.12, 0.85), Vector((0.0, bench_y + 0.42, seat_z + 0.55)), seat_m)
    add_box("Bench_LegL", (0.18, 0.7, seat_z), Vector((-bench_len * 0.45, bench_y, seat_z * 0.5)), leg_m)
    add_box("Bench_LegR", (0.18, 0.7, seat_z), Vector((bench_len * 0.45, bench_y, seat_z * 0.5)), leg_m)

    yaw = yaw_face_neg_y()
    start_x = -((n_players - 1) * seat_gap) * 0.5
    for i in range(n_players):
        x = start_x + i * seat_gap
        # Face mostly forward — large pair yaw twisted sit legs in camera view
        pair_yaw = yaw + (0.08 if i % 2 == 0 else -0.08)
        # Root so pelvis ≈ bench seat (absolute sit pose, not idle-delta)
        pos = Vector((x, bench_y - 0.05, -0.85))
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
        add_pose_strip(arm, f"NLBenchSit{i}", frames, _chair_sit_deltas, SIT_BONES, step=4, clamp=1.7, absolute=True)
        pair_phase = (i // 2) * 1.3 + (0.0 if i % 2 == 0 else 0.9)
        add_talk_strip(arm, f"NLBenchTalk{i}", frames, _talk_fn(0.85 + 0.1 * (i % 2), pair_phase), TALK_BONES, step=3)

    cam = setup_new_cam("Cam39", lens=28)
    # 3/4 side — front-on made forward thighs read as creepy V / 左右逆
    _cam_dense(
        cam, 1, frames,
        Vector((-16.0, bench_y - 11.0, 3.8)), Vector((-12.0, bench_y - 13.5, 4.2)),
        Vector((-2.0, bench_y, 1.7)), Vector((2.0, bench_y, 1.8)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 40 — Norway dribble from frame 1 (player always in shot)
# ---------------------------------------------------------------------------
def build_40() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    # Start already in-frame, midfield — run toward +X
    start = Vector((-12.0, 1.0, 0.0))
    end = Vector((25.0, -1.2, 0.0))
    move = (end - start).normalized()
    # Mannequin yaw=0 faces −Y; face travel dir: atan2(dx, −dy) (not atan2(dy, dx))
    yaw = math.atan2(move.x, -move.y)

    arm, root = spawn_player(
        "Norway", NORWAY_RED, start, yaw, actions=["run"], split=(NORWAY_RED, NORWAY_WHITE, 0.42)
    )
    _clear_all_nla(arm)

    def player_at(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        p = _lerp(start, end, ease(t))
        # Mild weave — keep ball readable in front
        p.y += 0.55 * math.sin(t * math.pi * 3.0)
        return p

    def face_dir(f: int) -> Vector:
        a = player_at(max(1, f - 1))
        b = player_at(min(frames, f + 1))
        d = Vector((b.x - a.x, b.y - a.y, 0.0))
        return d.normalized() if d.length > 1e-4 else move

    keys = [(f, player_at(f)) for f in range(1, frames + 1, 2)]
    keys.append((frames, player_at(frames)))
    animate_root(root, keys, yaw)
    add_nla_loop(arm, "run", 1, frames)

    ball = clear_ball_anim()

    def path(f: int) -> Vector:
        # Clearly past the lead foot — not under the torso / beside the hips
        p = player_at(f)
        fd = face_dir(f)
        ahead = 2.15 + 0.2 * abs(math.sin(f * 0.55))
        loc = p + fd * ahead
        loc.z = BALL_GROUND_Z
        return loc

    # Key every frame from 1 so first frame is not empty
    key_ball(ball, range(1, frames + 1), path)

    cam = setup_new_cam("Cam40", lens=34)

    def cam_pos(f: int) -> Vector:
        p = player_at(f)
        b = path(f)
        mid = (p + b) * 0.5
        return Vector((mid.x - 4.0, mid.y - 9.5, 3.4))

    def cam_tgt(f: int) -> Vector:
        p = player_at(f)
        b = path(f)
        mid = (p + b) * 0.5
        return Vector((mid.x + 2.0, mid.y * 0.3, 1.4))

    for f in range(1, frames + 1):
        kf_cam(cam, f, cam_pos(f), cam_tgt(f))
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 41 — Three Shaolin stomping (kept — user approved)
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
# 42 — Shaolin windmill breakdance (solo showcase)
# ---------------------------------------------------------------------------
def build_42() -> int:
    """少林だけ：ドロップ → ウインドミル連続回転 → 起き上がり。"""
    frames = 180
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()

    center = Vector((-2.0, 0.5, 0.0))
    start = Vector((8.0, -1.5, 0.0))
    approach_dir = (center - start).normalized()
    yaw0 = math.atan2(approach_dir.x, -approach_dir.y)

    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, start, yaw0,
        actions=["run", "fight_idle", "jump_full"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(sh_arm)

    f_approach, f_drop, f_spin0, f_spin1, f_up = 24, 36, 40, 150, 168
    # Negative pitch = tip onto BACK (positive was face-plant). Root at feet → raise Z.
    tip = -math.pi * 0.52
    spin_z = 1.55

    sh_keys_eul: list = []
    for f in range(1, frames + 1, 2):
        if f <= f_approach:
            t = ease((f - 1) / max(1, f_approach - 1))
            p = _lerp(start, center, t)
            eul = Euler((0.0, 0.0, yaw0), "XYZ")
        elif f <= f_drop:
            t = ease((f - f_approach) / max(1, f_drop - f_approach))
            p = Vector((center.x, center.y, spin_z * t))
            eul = Euler((tip * t, 0.0, yaw0), "XYZ")
        elif f <= f_spin1:
            spins = (f - f_spin0) * 0.48
            p = Vector((
                center.x + 0.12 * math.cos(spins),
                center.y + 0.12 * math.sin(spins),
                spin_z + 0.05 * abs(math.sin(spins * 2.0)),
            ))
            eul = Euler((tip + 0.08 * math.sin(spins * 2.0), 0.12 * math.cos(spins), yaw0 + spins), "XYZ")
        elif f <= f_up:
            t = ease((f - f_spin1) / max(1, f_up - f_spin1))
            p = Vector((center.x, center.y, spin_z * (1.0 - t)))
            eul = Euler((tip * (1.0 - t), 0.0, yaw0 + (f_spin1 - f_spin0) * 0.48), "XYZ")
        else:
            t = ease((f - f_up) / max(1, frames - f_up))
            p = Vector((center.x - 1.5 * t, center.y, 0.0))
            eul = Euler((0.0, 0.0, math.atan2(-1.0, 0.0)), "XYZ")
        sh_keys_eul.append((f, p, eul))
    sh_keys_eul.append(
        (frames, Vector((center.x - 1.5, center.y, 0.0)), Euler((0.0, 0.0, math.atan2(-1.0, 0.0)), "XYZ"))
    )
    _animate_root_euler(sh_root, sh_keys_eul)

    add_nla_loop(sh_arm, "run", 1, f_drop - 1)
    add_nla_hold(sh_arm, "fight_idle", f_drop, frames, af=4)
    add_pose_strip(
        sh_arm, "ShaolinWindmill", frames, _windmill_deltas, BREAK_BONES,
        step=2, clamp=1.8, absolute=True,
    )

    # Force-hide ball (hide_ball alone can leave a leftover sphere in some blend states)
    ball = bpy.data.objects.get("Ball")
    if ball:
        ball.hide_render = True
        ball.hide_viewport = True

    cam = setup_new_cam("Cam42", lens=28)

    def cam_pos(f: int) -> Vector:
        if f_drop <= f <= f_up:
            ang = (f - f_drop) * 0.09
            return Vector((
                center.x + 8.0 * math.cos(ang),
                center.y + 8.0 * math.sin(ang) - 0.4,
                4.2,
            ))
        if f < f_drop:
            p = _lerp(start, center, ease((f - 1) / max(1, f_approach - 1)))
            return Vector((p.x + 2.0, p.y - 9.0, 3.2))
        return Vector((center.x - 2.0, center.y - 9.0, 3.0))

    def cam_tgt(f: int) -> Vector:
        if f_drop <= f <= f_up:
            return Vector((center.x, center.y, 1.35))
        if f < f_drop:
            p = _lerp(start, center, ease((f - 1) / max(1, f_approach - 1)))
            return Vector((p.x, p.y, 1.2))
        return Vector((center.x, center.y, 1.3))

    for f in range(1, frames + 1, 2):
        kf_cam(cam, f, cam_pos(f), cam_tgt(f))
    kf_cam(cam, frames, cam_pos(frames), cam_tgt(frames))
    finish_cam(cam)
    return frames

# ---------------------------------------------------------------------------
# 43 / 44 — France stomping like 41, phone clamped between both hands; 2 cams
# ---------------------------------------------------------------------------
def _build_france_phone_stomp(cam_mode: str) -> int:
    frames = 144
    remove_players()
    _show_pitch()
    _clear_extras("Phone_")
    set_frame_range(frames)
    hide_ball()
    pos = Vector((-6.0, 1.0, 0.0))
    yaw = yaw_face_neg_y()
    arm, root = spawn_france("France", pos, yaw, actions=["idle", "fight_idle"])
    _clear_all_nla(arm)

    keys = []
    for f in range(1, frames + 1, 2):
        phase = f * 0.55
        z = 0.22 * abs(math.sin(phase))
        keys.append((f, Vector((pos.x, pos.y, z))))
    keys.append((frames, pos.copy()))
    animate_root(root, keys, yaw)
    add_nla_hold(arm, "fight_idle", 1, frames, af=8)
    # Absolute arm pose (clamp ≥ 2) — hands meet at chest around the phone
    add_pose_strip(
        arm, f"FrancePhoneStomp_{cam_mode}", frames, _phone_clamp_deltas, PHONE_STOMP_BONES,
        step=2, clamp=2.0, absolute=True,
    )

    phone_mat = mat_rgba("Phone_Mat", (0.02, 0.02, 0.025, 1.0), 0.35)
    palm = (0.07, 0.014, 0.12)
    phone = add_box("Phone_01", palm, Vector((0, 0, 0)), phone_mat)
    # Between palms — slightly larger so clamp reads on close cam
    parent_phone_to_hand(phone, arm, "hand.l", loc=Vector((0.04, 0.015, 0.0)), palm_size=palm)
    phone.rotation_euler = Euler((0.1, 0.0, 1.57), "XYZ")
    phone.scale = Vector(palm)

    cam = setup_new_cam(f"CamFranceStomp_{cam_mode}", lens=34 if cam_mode == "A" else 42)
    if cam_mode == "A":
        _cam_dense(
            cam, 1, frames,
            Vector((-6.0, -11.0, 3.6)), Vector((-5.0, -10.0, 3.3)),
            Vector((-6.0, 1.0, 1.7)), Vector((-6.0, 1.15, 1.75)),
            step=3,
        )
    else:
        _cam_dense(
            cam, 1, frames,
            Vector((-5.6, -5.5, 4.2)), Vector((-5.75, -5.0, 4.15)),
            Vector((-6.0, 1.0, 3.25)), Vector((-6.0, 1.05, 3.3)),
            step=2,
        )
    finish_cam(cam)
    return frames


def build_43() -> int:
    return _build_france_phone_stomp("A")


def build_44() -> int:
    return _build_france_phone_stomp("B")


BUILDERS: Dict[str, Callable[[], int]] = {
    "38": build_38,
    "39": build_39,
    "40": build_40,
    "41": build_41,
    "42": build_42,
    "43": build_43,
    "44": build_44,
}
