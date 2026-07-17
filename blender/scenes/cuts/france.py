# SPDX-License-Identifier: MIT
"""France block cuts 18–28 — attack Goal_L."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

import bpy
from mathutils import Euler, Vector

from animate_soccer_match import BALL_GROUND_Z, _clear_all_nla  # noqa: E402

from cuts.common import (  # noqa: E402
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
    add_pose_strip,
    add_talk_strip,
    animate_gk_dive,
    PHONE_ARM_BONES,
    SIT_BONES,
    parent_phone_to_hand,
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


def _ball_chase_cam(
    cam: bpy.types.Object,
    frames: int,
    path,
    *,
    lens: float = 42,
    look_ahead: int = 6,
    dist: float = 3.8,
    side: float = 2.8,
    height: float = 1.6,
) -> None:
    """Ball-glued chase cam: every frame, look ahead, stay close so motion reads fast."""
    cam.data.lens = lens
    for f in range(1, frames + 1):
        b = path(f)
        ahead = path(min(frames, f + look_ahead))
        vel = ahead - b
        if vel.length < 1e-4:
            vel = Vector((1.0, 0.0, 0.0))
        else:
            vel.normalize()
        lateral = Vector((-vel.y, vel.x, 0.0))
        if lateral.length < 1e-4:
            lateral = Vector((0.0, -1.0, 0.0))
        else:
            lateral.normalize()
        pos = b - vel * dist + lateral * side + Vector((0.0, 0.0, height))
        pos.z = max(1.8, pos.z)
        tgt = ahead + Vector((0.0, 0.0, 0.15))
        kf_cam(cam, f, pos, tgt)
    finish_cam(cam)


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



def _phone_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """Absolute two-hand phone hold at chest height (facing −Y cam).

    Probed: bent elbows with hands meeting at spine_02 height (midZ≈chest,
    span≈0.02). Older holds sat the phone at the pelvis.
    """
    t = frame / FPS
    tap = 0.04 * math.sin(t * 14.0)
    return {
        "clavicle.l": (0.08, 0.12, 0.1),
        "upperarm.l": (1.17, 0.52, -1.24),
        "lowerarm.l": (-0.92 - 0.05 * abs(tap), -0.67, 0.22),
        "hand.l": (0.64, 0.62, -0.42),
        "clavicle.r": (0.08, -0.12, -0.1),
        "upperarm.r": (1.17, -0.52, 1.24),
        "lowerarm.r": (-0.92 + tap, 0.67, -0.22),
        "hand.r": (0.64 + tap * 0.15, -0.62, 0.42),
        "spine_01": (0.06, 0.0, 0.0),
        "spine_02": (0.1, 0.0, 0.0),
        "neck_01": (0.22, 0.0, 0.02 * math.sin(t * 2.0)),
        "head": (0.28, 0.0, 0.03 * math.sin(t * 2.2)),
    }


def _sit_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    # 体育座り — deep knee fold + slight forward pelvis tip (not a back-arch)
    u = ease(min(1.0, (frame - 1) / 40.0))
    return {
        "thigh.l": (1.35 * u, 0.28 * u, 0.3 * u),
        "calf.l": (-1.45 * u, 0.05 * u, 0.0),
        "foot.l": (0.5 * u, 0.0, 0.1 * u),
        "thigh.r": (1.35 * u, -0.28 * u, -0.3 * u),
        "calf.r": (-1.45 * u, -0.05 * u, 0.0),
        "foot.r": (0.5 * u, 0.0, -0.1 * u),
        "pelvis": (0.4 * u, 0.0, 0.0),
        "spine_01": (0.18 * u, 0.0, 0.0),
        "spine_02": (0.12 * u, 0.0, 0.0),
        "neck_01": (-0.05 * u, 0.0, 0.0),
        "head": (-0.04 * u, 0.0, 0.0),
    }

# ---------------------------------------------------------------------------
# 18 — 1v1 juke; France facing reversed
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
    fr_yaw = yaw_face_pos_x()

    fr_arm, fr_root = spawn_france("France", fr_pos, fr_yaw, actions=["idle", "fight_kick", "fight_idle"])
    _clear_all_nla(fr_arm)
    sh_arm, sh_root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, sh_start, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(sh_arm)

    animate_root(fr_root, [(1, fr_pos), (50, fr_pos), (70, Vector((-21.2, fr_y, 0.0))), (frames, fr_pos)], fr_yaw)
    add_nla_loop(fr_arm, "idle", 1, 54)
    add_nla_once(fr_arm, "fight_kick", 55, 78)
    add_nla_hold(fr_arm, "fight_idle", 79, frames, af=8)

    sh_keys: List[Tuple[int, Vector]] = []
    for f in range(1, frames + 1, 2):
        if f <= 48:
            t = ease((f - 1) / 47.0)
            bend = math.sin(t * math.pi) * 1.2
            p = _lerp(sh_start, sh_mid, t)
            p.y = sh_y - bend
            sh_keys.append((f, p))
        else:
            t = ease((f - 48) / max(1, frames - 48))
            p = _lerp(sh_mid, sh_end, t)
            sh_keys.append((f, p))
    if sh_keys[-1][0] != frames:
        sh_keys.append((frames, sh_end))
    animate_root(sh_root, sh_keys, ATTACK_YAW)
    add_nla_loop(sh_arm, "run", 1, frames)

    ball = clear_ball_anim()

    def ball_path(f: int) -> Vector:
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
# 19 — France sits with bent legs (体育座り)
# ---------------------------------------------------------------------------
def build_19() -> int:
    frames = 144
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    pos = Vector((-10.0, 2.0, 0.0))
    arm, root = spawn_france("France", pos, yaw_face_neg_y(), actions=["idle"])
    _clear_all_nla(arm)
    # Deep settle so buttocks reach the pitch with bent legs
    sit = Vector((pos.x, pos.y, -1.05))
    keys = []
    for f in range(1, frames + 1, 2):
        if f <= 48:
            t = ease((f - 1) / 47.0)
            p = _lerp(pos, sit, t)
        else:
            p = sit.copy()
        keys.append((f, p))
    keys.append((frames, sit))
    animate_root(root, keys, yaw_face_neg_y())
    add_nla_hold(arm, "idle", 1, frames, af=12)
    add_pose_strip(arm, "FranceSitPose", frames, _sit_deltas, SIT_BONES, step=2, clamp=1.6)

    cam = setup_new_cam("Cam19", lens=32)
    _cam_dense(
        cam, 1, frames,
        Vector((-5.5, -10.5, 2.0)), Vector((-7.5, -9.5, 1.8)),
        Vector((-10.0, 2.0, 0.7)), Vector((-10.0, 2.0, 0.55)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 20 — phone: left hand holds, right operates; camera shows head+hands
# ---------------------------------------------------------------------------
def build_20() -> int:
    frames = 144
    remove_players()
    _show_pitch()
    _clear_extras("Phone_")
    set_frame_range(frames)
    hide_ball()
    # Root lift so idle foot mesh clears pitch (zmin≈0.01 at z=0.18; +margin)
    pos = Vector((-10.0, 2.0, 0.28))
    arm, root = spawn_france("France", pos, yaw_face_neg_y(), actions=["idle"])
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_hold(arm, "idle", 1, frames, af=12)
    add_pose_strip(
        arm, "FrancePhonePose", frames, _phone_deltas, PHONE_ARM_BONES,
        step=2, clamp=1.8, absolute=True,
    )

    phone_mat = mat_rgba("Phone_Mat", (0.02, 0.02, 0.025, 1.0), 0.35)
    # Palm-sized black rectangle (サイゼ風の薄い黒プレート)
    palm = (0.045, 0.008, 0.075)
    phone = add_box("Phone_01", palm, Vector((0, 0, 0)), phone_mat)
    parent_phone_to_hand(phone, arm, "hand.l", palm_size=palm)
    for f in range(1, frames + 1, 3):
        w = 0.004 * math.sin(f * 0.45)
        phone.location = Vector((0.02 + w, 0.035, 0.05))
        phone.scale = Vector(palm)
        phone.keyframe_insert(data_path="location", frame=f)
        phone.keyframe_insert(data_path="scale", frame=f)
    force_linear(phone)

    cam = setup_new_cam("Cam20", lens=38)
    # Wider bust: head + both hands on phone; pull back so lower legs stay in frame
    _cam_dense(
        cam, 1, frames,
        Vector((-8.5, -5.5, 3.4)), Vector((-8.7, -5.2, 3.3)),
        Vector((-10.0, 1.7, 3.1)), Vector((-10.0, 1.65, 3.05)),
        step=2,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 21 — France solo goal + Shaolin GK sideways miss
# ---------------------------------------------------------------------------
def build_21() -> int:
    frames = 160
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    start = Vector((-30.0, 1.0, 0.0))
    kick = Vector((GOAL_X + 22.0, 0.6, 0.0))
    gk_home = Vector((GOAL_X + 3.0, -0.2, 0.0))
    arm, root = spawn_france("France", start, ATTACK_YAW, actions=["run", "fight_kick", "fight_idle"])
    _clear_all_nla(arm)
    gk_arm, gk_root = spawn_player(
        "Shaolin_GK", SHAOLIN_ORANGE, gk_home, yaw_face_pos_x(),
        actions=["fight_idle", "jump_full"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(gk_arm)

    f_kick, f_leave, f_goal = 72, 78, 92
    keys = []
    for f in range(1, f_kick, 2):
        t = ease((f - 1) / max(1, f_kick - 2))
        keys.append((f, _lerp(start, kick, t)))
    keys += [(f_kick, kick), (frames, kick)]
    animate_root(root, keys, ATTACK_YAW)
    add_nla_loop(arm, "run", 1, f_kick - 1)
    add_nla_once(arm, "fight_kick", f_kick, f_kick + 20)
    add_nla_hold(arm, "fight_idle", f_kick + 21, frames, af=6)

    ball = clear_ball_anim()
    goal = Vector((GOAL_X - 1.5, -GOAL_INNER_HALF_W * 0.55, GOAL_H * 0.62))
    animate_gk_dive(gk_root, gk_arm, gk_home, goal.y * 0.7, f_leave + 2, f_goal + 8, frames, yaw_face_pos_x(), side=True)

    def path(f: int) -> Vector:
        if f < f_kick:
            loc = _lerp(start, kick, ease((f - 1) / max(1, f_kick - 2)))
            return ball_ahead_of(loc, ATTACK_DIR, f, arm=arm)
        if f <= f_leave:
            return ball_ahead_of(kick, ATTACK_DIR, f, arm=arm)
        # Fast linear-ish flight (minimal ease so cam chase feels snappy)
        u = min(1.0, (f - f_leave) / max(1, f_goal - f_leave))
        u = u * u * (3.0 - 2.0 * u)  # smoothstep — quicker mid-flight
        if f > f_goal:
            return goal
        return _shot_arc(ball_ahead_of(kick, ATTACK_DIR, f_leave, arm=arm), goal, u, arc=2.0)

    key_ball(ball, range(1, frames + 1), path)

    cam = setup_new_cam("Cam21", lens=42)
    _ball_chase_cam(cam, frames, path, lens=42, look_ahead=5, dist=3.5, side=-2.6, height=1.5)
    return frames


# ---------------------------------------------------------------------------
# 22 — Norway-style crowd; L blue / M white / R red
# ---------------------------------------------------------------------------
def build_22() -> int:
    frames = 192
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    _clear_extras("Crowd_")
    blue_m = mat_rgba("Crowd_FrBlue", FRANCE_BLUE, 0.7)
    wht_m = mat_rgba("Crowd_FrWht", FRANCE_WHITE, 0.7)
    red_m = mat_rgba("Crowd_FrRed", FRANCE_RED, 0.7)
    stand_m = mat_rgba("Crowd_StandMat", (0.25, 0.25, 0.28, 1.0), 0.9)
    add_box("Crowd_StandDeck", (48.0, 10.0, 0.4), Vector((0.0, 38.0, 6.0)), stand_m)
    add_box("Crowd_StandRisers", (48.0, 8.0, 3.5), Vector((0.0, 40.5, 4.0)), stand_m)

    def _cyl(name, radius, depth, loc, mat):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        mesh = bpy.data.meshes.new(name)
        n = 8
        verts = []
        for i in range(n):
            a = 2.0 * math.pi * i / n
            verts.append((math.cos(a) * radius, math.sin(a) * radius, -depth * 0.5))
        for i in range(n):
            a = 2.0 * math.pi * i / n
            verts.append((math.cos(a) * radius, math.sin(a) * radius, depth * 0.5))
        faces = [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
        faces.append(tuple(range(n - 1, -1, -1)))
        faces.append(tuple(range(n, 2 * n)))
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        obj.data.materials.append(mat)
        return obj

    cols, rows = 20, 5
    idx = 0
    for r in range(rows):
        for c in range(cols):
            x = -22.0 + c * 2.3 + (0.3 if r % 2 else 0.0)
            y = 34.5 + r * 1.7
            z = 6.4 + r * 0.55
            mat = blue_m if c < 7 else (wht_m if c < 13 else red_m)
            name = f"Crowd_Fan{idx:03d}"
            if (c + r) % 3 == 0:
                obj = _cyl(name, 0.28, 0.95, Vector((x, y, z + 0.48)), mat)
            else:
                obj = add_box(name, (0.45, 0.35, 0.95), Vector((x, y, z + 0.48)), mat)
            phase = idx * 0.37
            for f in range(1, frames + 1, 2):
                t = f / FPS
                bob = 0.18 * math.sin(t * 7.0 + phase) + 0.08 * math.sin(t * 11.0 + phase * 0.5)
                lean = 0.12 * math.sin(t * 5.5 + phase)
                obj.location = Vector((x + lean * 0.15, y, z + 0.48 + bob))
                obj.rotation_euler = Euler((lean * 0.25, 0.0, lean * 0.15), "XYZ")
                obj.keyframe_insert(data_path="location", frame=f)
                obj.keyframe_insert(data_path="rotation_euler", frame=f)
            force_linear(obj)
            idx += 1

    cam = setup_new_cam("Cam22", lens=28)
    for f in range(1, frames + 1, 3):
        t = (f - 1) / max(1, frames - 1)
        pos = Vector((-18.0 + 36.0 * ease(t), 22.0, 9.5 + 1.5 * math.sin(t * math.pi)))
        tgt = Vector((-10.0 + 20.0 * t, 38.0, 7.5))
        kf_cam(cam, f, pos, tgt)
    t = 1.0
    kf_cam(cam, frames, Vector((-18.0 + 36.0 * ease(t), 22.0, 9.5)), Vector((-10.0 + 20.0 * t, 38.0, 7.5)))
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 23 — equalizer + France GK jumps up but fails
# ---------------------------------------------------------------------------
def build_23() -> int:
    frames = 150
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    recv = Vector((-45.0, -2.0, 0.0))
    kick = Vector((GOAL_X + 26.0, -1.2, 0.0))
    gk_home = Vector((GOAL_X + 3.0, 0.2, 0.0))
    arm, root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, recv, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    gk_arm, gk_root = spawn_france("France_GK", gk_home, yaw_face_pos_x(), actions=["fight_idle", "jump_full"])
    _clear_all_nla(gk_arm)

    f_kick, f_leave, f_goal = 64, 70, 84
    keys = [(1, recv)]
    for f in range(24, f_kick, 2):
        t = ease((f - 24) / max(1, f_kick - 25))
        keys.append((f, _lerp(recv, kick, t)))
    keys += [(f_kick, kick), (frames, kick)]
    animate_root(root, keys, ATTACK_YAW)
    add_nla_loop(arm, "run", 1, f_kick - 1)
    add_nla_once(arm, "fight_kick", f_kick, f_kick + 18)
    add_nla_hold(arm, "fight_idle", f_kick + 19, frames, af=6)
    animate_gk_dive(gk_root, gk_arm, gk_home, 0.0, f_leave + 2, f_goal + 6, frames, yaw_face_pos_x(), side=False, rise=1.45)

    ball = clear_ball_anim()
    off = Vector((-20.0, 18.0, BALL_GROUND_Z))
    arrive = ball_ahead_of(recv, ATTACK_DIR, 22, arm=arm)
    goal = Vector((GOAL_X - 1.6, GOAL_INNER_HALF_W * 0.5, GOAL_H * 0.58))

    def path(f: int) -> Vector:
        if f <= 22:
            u = min(1.0, (f - 1) / 21.0)
            return _shot_arc(off, arrive, u, arc=1.0)
        if f < f_kick:
            loc = _lerp(recv, kick, ease((f - 24) / max(1, f_kick - 25)) if f >= 24 else 0.0)
            return ball_ahead_of(loc if f >= 24 else recv, ATTACK_DIR, f, arm=arm)
        if f <= f_leave:
            return ball_ahead_of(kick, ATTACK_DIR, f, arm=arm)
        u = min(1.0, (f - f_leave) / max(1, f_goal - f_leave))
        u = u * u * (3.0 - 2.0 * u)
        return goal if f > f_goal else _shot_arc(ball_ahead_of(kick, ATTACK_DIR, f_leave, arm=arm), goal, u, 2.2)

    key_ball(ball, range(1, frames + 1), path)

    cam = setup_new_cam("Cam23", lens=42)
    _ball_chase_cam(cam, frames, path, lens=42, look_ahead=5, dist=3.4, side=2.6, height=1.45)
    return frames


# ---------------------------------------------------------------------------
# 24 — France walks slowly with slumped shoulders (not slow-mo run)
# ---------------------------------------------------------------------------
def build_24() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    hide_ball()
    start = Vector((-5.0, 3.0, 0.0))
    end = Vector((-24.0, 4.5, 0.0))
    arm, root = spawn_france("France", start, ATTACK_YAW, actions=["idle", "fight_idle"])
    _clear_all_nla(arm)
    keys = []
    for f in range(1, frames + 1, 2):
        t = (f - 1) / max(1, frames - 1)
        p = _lerp(start, end, ease(t))
        # walking bob small
        p.z = 0.03 * abs(math.sin(t * math.pi * 6.0))
        p.y += 0.08 * math.sin(t * math.pi * 3.0)
        keys.append((f, p))
    keys.append((frames, end))
    animate_root(root, keys, ATTACK_YAW)
    add_nla_hold(arm, "idle", 1, frames, af=10)
    add_talk_strip(arm, "FranceSlumpWalk", frames, _sad_fn(0.36), TALK_BONES, step=3)

    cam = setup_new_cam("Cam24", lens=34)
    _cam_dense(
        cam, 1, frames,
        Vector((2.0, -11.0, 3.2)), Vector((-14.0, -10.0, 3.0)),
        Vector((-5.0, 3.0, 1.35)), Vector((-24.0, 4.0, 1.15)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 25 — air walk goal + France GK sideways miss; else unchanged
# ---------------------------------------------------------------------------
def build_25() -> int:
    frames = 220
    remove_players()
    _show_pitch()
    set_frame_range(frames)
    start = Vector((-40.0, 0.5, 0.0))
    cruise_z = 4.6
    kick = Vector((GOAL_X + 24.0, 0.0, cruise_z))
    gk_home = Vector((GOAL_X + 3.0, 0.2, 0.0))
    arm, root = spawn_player(
        "Shaolin", SHAOLIN_ORANGE, start, ATTACK_YAW, actions=["run"], split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42)
    )
    _clear_all_nla(arm)
    gk_arm, gk_root = spawn_france("France_GK", gk_home, yaw_face_pos_x(), actions=["fight_idle", "jump_full"])
    _clear_all_nla(gk_arm)

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
    animate_gk_dive(gk_root, gk_arm, gk_home, goal.y * 0.75, 118, 140, frames, yaw_face_pos_x(), side=True)

    def path(f: int) -> Vector:
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
# 26 — celebrate (unchanged)
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
# 27 — France interview kit colors (+ red foot)
# ---------------------------------------------------------------------------
def build_27() -> int:
    frames = 168
    remove_players()
    set_frame_range(frames)
    hide_ball()
    _hide_pitch_studio(("Light", "Sun", "World", "Camera", "Cam", "France_", "Interview_"))
    _interview_set(FRANCE_BLUE, FRANCE_RED)
    pos = Vector((0.0, 0.0, 0.35))
    arm, root = spawn_france("France", pos, yaw_face_neg_y(), actions=["idle"])
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_loop(arm, "idle", 1, frames)
    add_talk_strip(arm, "FranceInterviewTalk", frames, _talk_fn(1.0), TALK_BONES, step=2)

    cam = setup_new_cam("Cam27", lens=35)
    _cam_dense(
        cam, 1, frames,
        Vector((-0.5, -7.2, 3.35)), Vector((-0.35, -6.6, 3.4)),
        Vector((0.05, 0.1, 3.05)), Vector((0.0, 0.1, 3.1)),
        step=3,
    )
    finish_cam(cam)
    return frames


# ---------------------------------------------------------------------------
# 28 — phone left-hand + right operate, then shoulders drop; pull camera
# ---------------------------------------------------------------------------
def build_28() -> int:
    frames = 168
    remove_players()
    _show_pitch()
    _clear_extras("Phone_")
    set_frame_range(frames)
    hide_ball()
    pos = Vector((-10.0, 2.0, 0.0))
    arm, root = spawn_france("France", pos, yaw_face_neg_y(), actions=["idle"])
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw_face_neg_y())
    add_nla_hold(arm, "idle", 1, frames, af=12)

    def phone_then_sad(frame: int):
        base = _phone_deltas(frame)
        if frame >= 70:
            sad = _sad_fn(0.34)(frame)
            # merge: keep arms, override spine/head to slumped
            base.update({k: sad[k] for k in ("spine_01", "spine_02", "neck_01", "head") if k in sad})
        return base

    add_pose_strip(arm, "FrancePhoneThenSad", frames, phone_then_sad, PHONE_ARM_BONES, step=2, clamp=1.3)

    phone_mat = mat_rgba("Phone_Mat", (0.02, 0.02, 0.025, 1.0), 0.35)
    palm = (0.045, 0.008, 0.075)
    phone = add_box("Phone_01", palm, Vector((0, 0, 0)), phone_mat)
    parent_phone_to_hand(phone, arm, "hand.l", palm_size=palm)
    for f in range(1, frames + 1, 3):
        w = 0.004 * math.sin(f * 0.35)
        phone.location = Vector((0.02 + w, 0.035, 0.05))
        phone.scale = Vector(palm)
        phone.keyframe_insert(data_path="location", frame=f)
        phone.keyframe_insert(data_path="scale", frame=f)
    force_linear(phone)

    cam = setup_new_cam("Cam28", lens=40)
    _cam_dense(
        cam, 1, frames,
        Vector((-9.0, -5.4, 3.5)), Vector((-9.5, -5.0, 3.2)),
        Vector((-10.0, 1.85, 2.5)), Vector((-10.0, 1.75, 2.35)),
        step=2,
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
