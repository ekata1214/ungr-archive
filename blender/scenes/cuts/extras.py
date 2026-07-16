# SPDX-License-Identifier: MIT
"""Extra cuts 38–46 — desk, benches, dribble, stomp, windmill, phone-stomp, Arg GK, Shaolin bench."""

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
    ARG_LIGHT,
    ARG_WHITE,
    COMMENTATOR_WHITE,
    FPS,
    GOAL_H,
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
    goal_l_x,
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
    yaw_face_neg_x,
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

    Upperarm Y: L=+Y / R=−Y (uncrossed). Hand X≈π/2 with mirrored Y/Z so
    thumb tips point up and inward (toward the phone). Explicit thumb bone
    eulers make the grip read correctly on close cam.
    Use with add_pose_strip(..., absolute=True, clamp≥π).
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
        "clavicle.l": (0.06, 0.1, 0.06),
        "upperarm.l": (-1.05, 0.55, 0.4),
        "lowerarm.l": (-1.85, 0.15, 0.3),
        "hand.l": (math.pi * 0.5, -1.2, -0.8),
        "thumb_01.l": (0.35, -0.85, -0.45),
        "thumb_02.l": (0.25, -0.1, 0.0),
        "thumb_03.l": (0.2, 0.0, 0.0),
        "clavicle.r": (0.06, -0.1, -0.06),
        "upperarm.r": (-1.05, -0.55, -0.4),
        "lowerarm.r": (-1.85, -0.15, -0.3),
        "hand.r": (math.pi * 0.5, 1.2, 0.8),
        "thumb_01.r": (0.35, 0.85, 0.45),
        "thumb_02.r": (0.25, 0.1, 0.0),
        "thumb_03.r": (0.2, 0.0, 0.0),
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
        "thigh.l": (1.65 + 0.25 * a, 1.25, 0.85 + 0.2 * b),
        "calf.l": (-1.35, 0.2, 0.0),
        "foot.l": (0.5, 0.15, 0.25),
        "thigh.r": (1.65 - 0.25 * a, -1.25, -0.85 - 0.2 * b),
        "calf.r": (-1.35, -0.2, 0.0),
        "foot.r": (0.5, -0.15, -0.25),
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
PHONE_STOMP_BONES = list(dict.fromkeys(STOMP_BONES + PHONE_ARM_BONES + [
    "thumb_01.l", "thumb_02.l", "thumb_03.l",
    "thumb_01.r", "thumb_02.r", "thumb_03.r",
]))


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

    f_approach, f_drop, f_spin0, f_spin1, f_up = 20, 32, 36, 155, 168
    # Negative pitch = tip onto BACK (positive was face-plant). Root at feet → raise Z.
    tip = -math.pi * 0.38
    spin_z = 1.15

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
            spins = (f - f_spin0) * 0.52
            p = Vector((
                center.x + 0.1 * math.cos(spins),
                center.y + 0.1 * math.sin(spins),
                spin_z + 0.1 * abs(math.sin(spins * 2.0)),
            ))
            eul = Euler((tip + 0.15 * math.sin(spins), 0.25 * math.sin(spins * 2.0), yaw0 + spins), "XYZ")
        elif f <= f_up:
            t = ease((f - f_spin1) / max(1, f_up - f_spin1))
            p = Vector((center.x, center.y, spin_z * (1.0 - t)))
            eul = Euler((tip * (1.0 - t), 0.0, yaw0 + (f_spin1 - f_spin0) * 0.52), "XYZ")
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

    cam = setup_new_cam("Cam42", lens=30)

    def cam_pos(f: int) -> Vector:
        if f_drop <= f <= f_up:
            ang = (f - f_drop) * 0.07
            return Vector((
                center.x + 9.5 * math.cos(ang),
                center.y - 5.5 + 2.0 * math.sin(ang),
                2.6,
            ))
        if f < f_drop:
            p = _lerp(start, center, ease((f - 1) / max(1, f_approach - 1)))
            return Vector((p.x + 3.0, p.y - 8.0, 2.8))
        return Vector((center.x + 4.0, center.y - 8.0, 2.6))

    def cam_tgt(f: int) -> Vector:
        if f_drop <= f <= f_up:
            return Vector((center.x, center.y, 1.4))
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
    # Absolute arm pose (clamp ≥ π) — hands meet at chest, palms in, correct L/R
    add_pose_strip(
        arm, f"FrancePhoneStomp_{cam_mode}", frames, _phone_clamp_deltas, PHONE_STOMP_BONES,
        step=2, clamp=3.3, absolute=True,
    )

    phone_mat = mat_rgba("Phone_Mat", (0.02, 0.02, 0.025, 1.0), 0.35)
    palm = (0.07, 0.014, 0.12)
    phone = add_box("Phone_01", palm, Vector((0, 0, 0)), phone_mat)
    # Between palms — slightly larger so clamp reads on close cam
    parent_phone_to_hand(phone, arm, "hand.l", loc=Vector((0.025, 0.04, 0.0)), palm_size=palm)
    phone.rotation_euler = Euler((0.2, 0.1, 1.57), "XYZ")
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
        # Frontal-ish close on the phone clamp (not high top-down on the neck)
        _cam_dense(
            cam, 1, frames,
            Vector((-6.0, -6.2, 3.0)), Vector((-5.85, -5.8, 2.95)),
            Vector((-6.0, 1.0, 2.85)), Vector((-6.0, 1.05, 2.9)),
            step=2,
        )
    finish_cam(cam)
    return frames


def build_43() -> int:
    return _build_france_phone_stomp("A")


def build_44() -> int:
    return _build_france_phone_stomp("B")


def _shot_arc(p0: Vector, p1: Vector, u: float, arc: float = 2.2) -> Vector:
    p = _lerp(p0, p1, u)
    p.z = p0.z + (p1.z - p0.z) * u + arc * math.sin(u * math.pi) * (1.0 - 0.35 * u)
    return p


def _stand_cheer_deltas(phase: float = 0.0) -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    """Absolute upright cheer — arms overhead (upperarm +X), no fight_idle lean."""

    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS + phase
        bob = 0.06 * math.sin(t * 9.0)
        shake = 0.1 * math.sin(t * 11.0 + phase)
        wave = 0.22 * abs(math.sin(t * 7.0 + phase))
        alt = 0.12 * math.sin(t * 8.5 + phase * 1.1)
        # Prefer one-arm-up on odd phases for variety
        one_arm = (int(phase * 10) % 2) == 1
        lx = 1.05 + wave
        rx = (0.35 + 0.1 * wave) if one_arm else (1.05 + wave)
        return {
            "pelvis": (0.0, 0.0, 0.0),
            "spine_01": (0.02 + bob * 0.2, 0.0, shake * 0.2),
            "spine_02": (0.03 + bob * 0.3, 0.0, shake * 0.25),
            "neck_01": (-0.08 + bob * 0.5, 0.0, shake * 0.6),
            "head": (-0.06 + bob, 0.0, shake),
            "clavicle.l": (0.06, 0.05, 0.08),
            "upperarm.l": (lx, -0.15 + alt * 0.3, 0.75),
            "lowerarm.l": (-0.45 - 0.1 * wave, 0.05, 0.05),
            "hand.l": (0.12, 0.05, 0.08),
            "clavicle.r": (0.06, -0.05, -0.08),
            "upperarm.r": (rx, 0.15 - alt * 0.3, -0.75 if not one_arm else -0.35),
            "lowerarm.r": (-0.45 - 0.1 * wave, -0.05, -0.05),
            "hand.r": (0.12, -0.05, -0.08),
            "thigh.l": (0.05 * abs(math.sin(t * 6.0)), 0.04, 0.05),
            "thigh.r": (0.05 * abs(math.sin(t * 6.0 + 1.2)), -0.04, -0.05),
            "calf.l": (-0.08 * abs(math.sin(t * 6.0)), 0.0, 0.0),
            "calf.r": (-0.08 * abs(math.sin(t * 6.0 + 1.2)), 0.0, 0.0),
        }

    return deltas


def _bench_sit_cheer_deltas(phase: float = 0.0) -> Callable[[int], Dict[str, Tuple[float, float, float]]]:
    """Absolute chair sit + overhead cheer arms in one REPLACE strip.

    Do not stack talk/wave REPLACE strips after absolute sit — they wipe sit spine.
    Upperarm uses +X so hands go up (negative X made a sideways arm-chain).
    Legs: more thigh tip + calf bend than shared _chair_sit so ankles/toes stay ≥0
    (old chair sit buried feet at z≈−0.24).
    """
    # Cam-facing sit; ankles ~z=0.02–0.08, toes slightly tipped up (not buried).
    base = {
        "thigh.l": (0.55, -0.62, -0.95),
        "calf.l": (0.75, 0.08, 0.0),
        "foot.l": (0.6, 0.08, 0.05),
        "thigh.r": (0.55, 0.62, 0.95),
        "calf.r": (0.75, -0.08, 0.0),
        "foot.r": (0.6, -0.08, -0.05),
        "pelvis": (0.2, 0.0, 0.0),
        "spine_01": (-0.04, 0.0, 0.0),
        "spine_02": (-0.02, 0.0, 0.0),
        "neck_01": (-0.1, 0.0, 0.0),
        "head": (-0.08, 0.0, 0.0),
    }
    style = int(phase * 10) % 3

    def deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
        t = frame / FPS + phase
        bob = 0.05 * math.sin(t * 8.0)
        turn = 0.08 * math.sin(t * 3.1 + phase)
        wave = 0.2 * abs(math.sin(t * 6.8 + phase))
        alt = 0.1 * math.sin(t * 8.2 + phase * 1.2)
        out = dict(base)
        out["spine_01"] = (-0.04 + bob * 0.15, 0.0, turn * 0.15)
        out["spine_02"] = (-0.02 + bob * 0.25, 0.0, turn * 0.2)
        out["neck_01"] = (-0.1 + bob * 0.45, 0.0, turn * 0.55)
        out["head"] = (-0.08 + bob, 0.0, turn)
        out["clavicle.l"] = (0.05, 0.04, 0.06)
        out["clavicle.r"] = (0.05, -0.04, -0.06)
        if style == 0:
            # both arms up
            out["upperarm.l"] = (1.0 + wave, -0.15 + alt, 0.75)
            out["lowerarm.l"] = (-0.4 - 0.1 * wave, 0.05, 0.05)
            out["hand.l"] = (0.12, 0.05, 0.08)
            out["upperarm.r"] = (1.0 + wave, 0.15 - alt, -0.75)
            out["lowerarm.r"] = (-0.4 - 0.1 * wave, -0.05, -0.05)
            out["hand.r"] = (0.12, -0.05, -0.08)
        elif style == 1:
            # left up, right gesture
            out["upperarm.l"] = (1.15 + wave, -0.1 + alt, 0.7)
            out["lowerarm.l"] = (-0.35, 0.05, 0.05)
            out["hand.l"] = (0.15, 0.05, 0.08)
            out["upperarm.r"] = (0.35 + 0.15 * wave, -0.35 - alt, -0.25)
            out["lowerarm.r"] = (-0.85, -0.1, -0.05)
            out["hand.r"] = (0.15, -0.12, -0.08)
        else:
            # right up, left gesture
            out["upperarm.l"] = (0.35 + 0.15 * wave, 0.35 + alt, 0.25)
            out["lowerarm.l"] = (-0.85, 0.1, 0.05)
            out["hand.l"] = (0.15, 0.12, 0.08)
            out["upperarm.r"] = (1.15 + wave, 0.1 - alt, -0.7)
            out["lowerarm.r"] = (-0.35, -0.05, -0.05)
            out["hand.r"] = (0.15, -0.05, -0.08)
        return out

    return deltas


BENCH_SIT_CHEER_BONES = list(dict.fromkeys(
    SIT_BONES + [
        "clavicle.l", "upperarm.l", "lowerarm.l", "hand.l",
        "clavicle.r", "upperarm.r", "lowerarm.r", "hand.r",
    ]
))

BENCH_STAND_CHEER_BONES = list(dict.fromkeys(
    SIT_BONES + [
        "clavicle.l", "upperarm.l", "lowerarm.l", "hand.l",
        "clavicle.r", "upperarm.r", "lowerarm.r", "hand.r",
    ]
))


# ---------------------------------------------------------------------------
# 45 — Argentina GK punches away an incoming shot
# ---------------------------------------------------------------------------
def build_45() -> int:
    """アルゼンチンGKが飛んでくるボールをパンチで弾く。"""
    frames = 156
    remove_players()
    _show_pitch()
    set_frame_range(frames)

    gx = goal_l_x()
    gk_home = Vector((gx + 3.5, 0.0, 0.0))
    gk_yaw = yaw_face_pos_x()
    # Shooter from midfield toward Goal_L (−X)
    shoot_pos = Vector((gx + 28.0, 2.2, 0.0))
    shoot_yaw = yaw_face_neg_x()
    attack = Vector((-1.0, 0.0, 0.0))

    sh_arm, sh_root = spawn_player(
        "Shaolin_Shooter", SHAOLIN_ORANGE, shoot_pos, shoot_yaw,
        actions=["idle", "fight_kick", "fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    gk_arm, gk_root = spawn_player(
        "Argentina_GK", ARG_LIGHT, gk_home, gk_yaw,
        actions=["idle", "fight_idle", "fight_punch", "jump_full"],
        split=(ARG_LIGHT, ARG_WHITE, 0.42),
    )
    _clear_all_nla(sh_arm)
    _clear_all_nla(gk_arm)

    f_kick, f_punch, f_land = 36, 68, 82
    punch_pos = gk_home + Vector((1.2, -2.8, 0.0))

    animate_root(sh_root, [(1, shoot_pos), (frames, shoot_pos)], shoot_yaw)
    animate_root(
        gk_root,
        [
            (1, gk_home),
            (f_punch - 14, gk_home),
            (f_punch, punch_pos + Vector((0.0, 0.0, 0.55))),
            (f_land, punch_pos),
            (frames, punch_pos),
        ],
        gk_yaw,
    )

    add_nla_hold(sh_arm, "idle", 1, f_kick - 8, af=10)
    add_nla_once(sh_arm, "fight_kick", f_kick - 7, f_kick + 14)
    add_nla_hold(sh_arm, "fight_idle", f_kick + 15, frames, af=6)

    add_nla_loop(gk_arm, "idle", 1, f_punch - 18)
    add_nla_once(gk_arm, "jump_full", f_punch - 17, f_punch - 2)
    add_nla_once(gk_arm, "fight_punch", f_punch - 1, f_punch + 14)
    add_nla_hold(gk_arm, "fight_idle", f_punch + 15, frames, af=5)

    ball = clear_ball_anim()
    start_b = ball_ahead_of(shoot_pos, attack, f_kick, arm=sh_arm)
    contact = Vector((punch_pos.x + 1.5, punch_pos.y + 0.4, GOAL_H * 0.55))
    deflect = Vector((gx + 22.0, -14.0, BALL_GROUND_Z + 0.35))

    def path(f: int) -> Vector:
        if f < f_kick:
            return Vector((start_b.x, start_b.y, BALL_GROUND_Z))
        if f <= f_punch:
            u = ease((f - f_kick) / max(1, f_punch - f_kick))
            return _shot_arc(start_b, contact, u, 2.4)
        if f <= f_punch + 40:
            u = ease((f - f_punch) / 40.0)
            return _shot_arc(contact, deflect, u, 1.6)
        return deflect.copy()

    key_ball(ball, range(1, frames + 1, 2), path)

    cam = setup_new_cam("Cam45", lens=28)
    # Keep GK + ball readable through punch (contact ~f68)
    _cam_dense(
        cam, 1, frames,
        Vector((gx + 18.0, -16.0, 4.2)), Vector((gx + 8.0, -13.0, 3.5)),
        Vector((gx + 12.0, 0.5, 1.5)), Vector((gx + 5.0, -2.0, 1.7)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 46 — Shaolin bench celebrating / making a fuss
# ---------------------------------------------------------------------------
def build_46() -> int:
    """少林チームのベンチが騒いでいる様子。"""
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    _clear_extras("Bench_")

    seat_m = mat_rgba("Bench_SeatMat", (0.12, 0.12, 0.13, 1.0), 0.75)
    leg_m = mat_rgba("Bench_LegMat", (0.2, 0.2, 0.22, 1.0), 0.7)
    n_players = 8
    seat_gap = 2.05
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
        pair_yaw = yaw + (0.1 if i % 2 == 0 else -0.1)
        sit_pos = Vector((x, bench_y - 0.05, -0.85))
        # Two standing celebrators at the ends of the bench
        standing = i in (0, n_players - 1)
        if standing:
            stand_pos = Vector((x + (0.8 if i == 0 else -0.8), bench_y - 1.6, 0.0))
            arm, root = spawn_player(
                f"Shaolin_Bench_{i}",
                SHAOLIN_ORANGE,
                stand_pos,
                pair_yaw,
                actions=["idle"],
                split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
            )
            _clear_all_nla(arm)
            keys = []
            for f in range(1, frames + 1, 2):
                phase = f * 0.45 + i * 1.1
                z = 0.22 * abs(math.sin(phase))
                keys.append((f, Vector((stand_pos.x, stand_pos.y, z))))
            keys.append((frames, stand_pos.copy()))
            animate_root(root, keys, pair_yaw)
            add_nla_hold(arm, "idle", 1, frames, af=8)
            add_pose_strip(
                arm, f"ShaolinBenchStand{i}", frames,
                _stand_cheer_deltas(i * 0.9), BENCH_STAND_CHEER_BONES,
                step=2, clamp=1.6, absolute=True,
            )
        else:
            arm, root = spawn_player(
                f"Shaolin_Bench_{i}",
                SHAOLIN_ORANGE,
                sit_pos,
                pair_yaw,
                actions=["idle"],
                split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
            )
            _clear_all_nla(arm)
            # Slight seat bounce while cheering
            keys = []
            for f in range(1, frames + 1, 3):
                z = sit_pos.z + 0.03 * abs(math.sin(f * 0.4 + i * 0.9))
                keys.append((f, Vector((sit_pos.x, sit_pos.y, z))))
            keys.append((frames, sit_pos.copy()))
            animate_root(root, keys, pair_yaw)
            add_nla_hold(arm, "idle", 1, frames, af=10)
            # One absolute strip: sit + cheer. Extra REPLACE strips wipe sit spine.
            add_pose_strip(
                arm, f"ShaolinBenchSitCheer{i}", frames,
                _bench_sit_cheer_deltas(i * 1.05),
                BENCH_SIT_CHEER_BONES,
                step=2, clamp=1.7, absolute=True,
            )

    cam = setup_new_cam("Cam46", lens=28)
    _cam_dense(
        cam, 1, frames,
        Vector((-14.0, bench_y - 12.0, 3.9)), Vector((-8.0, bench_y - 14.0, 4.3)),
        Vector((-1.0, bench_y - 0.5, 1.8)), Vector((1.5, bench_y - 0.3, 1.95)),
        step=2,
    )
    finish_cam(cam)
    return frames


BUILDERS: Dict[str, Callable[[], int]] = {
    "38": build_38,
    "39": build_39,
    "40": build_40,
    "41": build_41,
    "42": build_42,
    "43": build_43,
    "44": build_44,
    "45": build_45,
    "46": build_46,
}
