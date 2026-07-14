# SPDX-License-Identifier: MIT
"""Norway block cuts 01–08 builders."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

import bpy
from mathutils import Euler, Vector

from animate_soccer_match import BALL_GROUND_Z, _clear_all_nla  # noqa: E402

from cuts.common import (  # noqa: E402
    FPS,
    GOAL_H,
    GOAL_INNER_HALF_W,
    NORWAY_RED,
    NORWAY_WHITE,
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


def _show_pitch() -> None:
    for obj in list(bpy.data.objects):
        if obj.name == "Ball" or obj.name.startswith(
            ("Field_", "Line_", "Pen", "Goal", "Corner_", "Net", "Post", "Crossbar")
        ):
            obj.hide_render = False
            obj.hide_viewport = False


def _dense_cam(
    cam: bpy.types.Object,
    frames: int,
    pos_fn,
    tgt_fn,
    step: int = 3,
) -> None:
    for f in range(1, frames + 1, step):
        kf_cam(cam, f, pos_fn(f), tgt_fn(f))
    if (frames - 1) % step != 0:
        kf_cam(cam, frames, pos_fn(frames), tgt_fn(frames))
    finish_cam(cam)


def _add_cylinder(
    name: str,
    radius: float,
    depth: float,
    loc: Vector,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    # approximate cylinder with 8 sides
    n = 8
    verts = []
    for i in range(n):
        a = 2.0 * math.pi * i / n
        verts.append((math.cos(a) * radius, math.sin(a) * radius, -depth * 0.5))
    for i in range(n):
        a = 2.0 * math.pi * i / n
        verts.append((math.cos(a) * radius, math.sin(a) * radius, depth * 0.5))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.data.materials.append(mat)
    return obj


def _setup_interview_set(accent_a, accent_b) -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Interview_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    floor_mat = mat_rgba("Interview_FloorMat", (0.1, 0.1, 0.11, 1.0), 0.9)
    podium_mat = mat_rgba("Interview_PodiumMat", (0.16, 0.15, 0.14, 1.0), 0.55)
    back_mat = mat_rgba("Interview_BackMat", (0.09, 0.07, 0.06, 1.0), 0.85)
    stripe_mat = mat_rgba("Interview_StripeMat", accent_a, 0.45)
    accent_mat = mat_rgba("Interview_AccentMat", accent_b, 0.5)
    panel_mat = mat_rgba("Interview_PanelMat", (0.18, 0.12, 0.06, 1.0), 0.7)
    add_box("Interview_Floor", (7.0, 5.0, 0.1), Vector((0.0, 0.6, 0.05)), floor_mat)
    add_box("Interview_Podium", (2.0, 1.5, 0.35), Vector((0.0, 0.0, 0.175)), podium_mat)
    add_box("Interview_Backdrop", (8.0, 0.12, 5.4), Vector((0.0, 2.4, 2.7)), back_mat)
    add_box("Interview_Banner", (7.6, 0.14, 0.55), Vector((0.0, 2.28, 4.55)), stripe_mat)
    add_box("Interview_Accent", (7.6, 0.14, 0.28), Vector((0.0, 2.28, 0.85)), accent_mat)
    add_box("Interview_LogoL", (1.6, 0.08, 1.6), Vector((-2.3, 2.26, 2.5)), panel_mat)
    add_box("Interview_LogoR", (1.6, 0.08, 1.6), Vector((2.3, 2.26, 2.5)), panel_mat)


def _setup_dojo() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Dojo_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    mat_floor = mat_rgba("Dojo_FloorMat", (0.45, 0.28, 0.12, 1.0), 0.85)
    mat_mat = mat_rgba("Dojo_MatMat", (0.55, 0.12, 0.1, 1.0), 0.75)
    mat_wood = mat_rgba("Dojo_WoodMat", (0.32, 0.2, 0.1, 1.0), 0.7)
    mat_panel = mat_rgba("Dojo_PanelMat", (0.38, 0.24, 0.12, 1.0), 0.65)
    add_box("Dojo_Floor", (10.0, 8.0, 0.12), Vector((0.0, 0.0, 0.06)), mat_floor)
    add_box("Dojo_Mat", (5.5, 4.0, 0.08), Vector((0.0, 0.0, 0.14)), mat_mat)
    add_box("Dojo_Back", (9.5, 0.18, 4.2), Vector((0.0, 3.6, 2.2)), mat_wood)
    add_box("Dojo_PanelL", (0.18, 6.0, 4.0), Vector((-4.6, 0.5, 2.1)), mat_panel)
    add_box("Dojo_PanelR", (0.18, 6.0, 4.0), Vector((4.6, 0.5, 2.1)), mat_panel)
    add_box("Dojo_Beam", (9.2, 0.25, 0.35), Vector((0.0, 3.4, 4.0)), mat_wood)


def _talk_deltas_calm(frame: int) -> Dict[str, Tuple[float, float, float]]:
    t = frame / FPS
    nod = 0.06 * math.sin(t * 5.5) + 0.03 * math.sin(t * 9.0)
    turn = 0.08 * math.sin(t * 1.8 + 0.2) + 0.04 * math.sin(t * 3.5)
    lean = 0.04 * math.sin(t * 1.3)
    return {
        "spine_01": (0.02 + lean * 0.4, 0.0, turn * 0.25),
        "spine_02": (0.04 + lean, 0.0, turn * 0.4),
        "neck_01": (0.035 + nod * 0.65, 0.0, turn * 0.75),
        "head": (0.045 + nod, 0.0, turn),
    }


# ---------------------------------------------------------------------------
# 01 norway counter
# ---------------------------------------------------------------------------
def build_01() -> int:
    remove_players()
    _show_pitch()
    frames = 240
    gx = goal_l_x()
    yaw_n = yaw_face_neg_x()
    yaw_gk = yaw_face_pos_x()
    start = Vector((gx + 42.0, 1.2, 0.0))
    kick_pos = Vector((gx + 12.0, 0.35, 0.0))
    gk_home = Vector((gx + 3.0, -0.4, 0.0))
    ball_goal = Vector((gx - 1.4, GOAL_INNER_HALF_W * 0.72, GOAL_H * 0.55))

    f_run_end = 110
    f_kick = 132
    f_goal = 160

    nor_arm, nor_root = spawn_player(
        "Norway",
        NORWAY_RED,
        start,
        yaw_n,
        actions=["run", "fight_kick", "idle"],
        split=(NORWAY_RED, NORWAY_WHITE, 0.42),
    )
    gk_arm, gk_root = spawn_player(
        "Shaolin",
        SHAOLIN_ORANGE,
        gk_home,
        yaw_gk,
        actions=["fight_idle", "idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(nor_arm)
    _clear_all_nla(gk_arm)

    def nor_path(f: int) -> Vector:
        if f <= f_run_end:
            t = ease((f - 1) / max(1, f_run_end - 1))
            p = start.lerp(kick_pos, t)
            p.y += 0.25 * math.sin(t * 4.0 * math.pi)
            return p
        if f <= f_kick:
            t = (f - f_run_end) / max(1, f_kick - f_run_end)
            return kick_pos + Vector((-0.4 * ease(t), -0.08 * t, 0.0))
        base = kick_pos + Vector((-0.4, -0.08, 0.0))
        t = (f - f_kick) / max(1, frames - f_kick)
        return base + Vector((-0.9 * ease(min(1.0, t * 1.5)), 0.05 * t, 0.0))

    nor_keys = [(f, nor_path(f)) for f in range(1, frames + 1, 2)]
    if nor_keys[-1][0] != frames:
        nor_keys.append((frames, nor_path(frames)))
    animate_root(nor_root, nor_keys, yaw_n)
    animate_root(gk_root, [(1, gk_home), (frames, gk_home)], yaw_gk)

    add_nla_loop(nor_arm, "run", 1, f_run_end)
    add_nla_once(nor_arm, "fight_kick", f_run_end + 1, f_kick + 18)
    add_nla_hold(nor_arm, "idle", f_kick + 19, frames, af=8)
    add_nla_hold(gk_arm, "fight_idle", 1, frames, af=12)

    ball = clear_ball_anim()
    move = Vector((-1.0, 0.0, 0.0))

    def ball_path(f: int) -> Vector:
        p_n = nor_path(f)
        if f < f_kick:
            return ball_ahead_of(p_n, move, f, arm=nor_arm)
        t = min(1.0, (f - f_kick) / max(1, f_goal - f_kick))
        u = 1.0 - (1.0 - t) ** 2.4
        start_b = ball_ahead_of(p_n, move, f_kick - 1, arm=nor_arm)
        p = start_b.lerp(ball_goal, u)
        p.z = BALL_GROUND_Z + (ball_goal.z - BALL_GROUND_Z) * u + 1.0 * math.sin(u * math.pi) * (1.0 - 0.35 * u)
        if f > f_goal:
            t2 = (f - f_goal) / max(1, frames - f_goal)
            p = ball_goal + Vector((-0.7 * ease(min(1.0, t2)), 0.08 * t2, -0.4 * ease(min(1.0, t2))))
            p.z = max(BALL_GROUND_Z + 0.3, p.z)
        return p

    key_ball(ball, range(1, frames + 1, 2), ball_path)

    cam = setup_new_cam("CamCut01", lens=30)

    def cam_pos(f: int) -> Vector:
        b = ball_path(f)
        n = nor_path(f)
        if f < f_kick:
            return Vector((n.x + 6.0, n.y - 10.0, 3.8))
        if f < f_goal:
            return Vector((b.x + 8.0, b.y - 11.5, 4.2))
        return Vector((gx + 14.0, -9.5, 4.6))

    def cam_tgt(f: int) -> Vector:
        b = ball_path(f)
        n = nor_path(f)
        if f < f_kick:
            return Vector((n.x - 2.0, n.y * 0.3, 1.3))
        return Vector((b.x, b.y * 0.4, max(1.2, b.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 02 norway fans
# ---------------------------------------------------------------------------
def build_02() -> int:
    remove_players()
    hide_ball()
    frames = 192
    # elevated stands on +Y
    red_m = mat_rgba("Crowd_NorRed", NORWAY_RED, 0.7)
    wht_m = mat_rgba("Crowd_NorWht", NORWAY_WHITE, 0.7)
    stand_m = mat_rgba("Crowd_StandMat", (0.25, 0.25, 0.28, 1.0), 0.9)
    add_box("Crowd_StandDeck", (48.0, 10.0, 0.4), Vector((0.0, 38.0, 6.0)), stand_m)
    add_box("Crowd_StandRisers", (48.0, 8.0, 3.5), Vector((0.0, 40.5, 4.0)), stand_m)

    crowd: List[bpy.types.Object] = []
    n_fans = 100
    cols, rows = 20, 5
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= n_fans:
                break
            x = -22.0 + c * 2.3 + (0.3 if r % 2 else 0.0)
            y = 34.5 + r * 1.7
            z = 6.4 + r * 0.55
            mat = red_m if (c + r) % 2 == 0 else wht_m
            name = f"Crowd_Fan{idx:03d}"
            if (c + r) % 3 == 0:
                obj = _add_cylinder(name, 0.28, 0.95, Vector((x, y, z + 0.48)), mat)
            else:
                obj = add_box(name, (0.45, 0.35, 0.95), Vector((x, y, z + 0.48)), mat)
            crowd.append(obj)
            # bobbing + slight lean
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
        if idx >= n_fans:
            break

    cam = setup_new_cam("CamCut02", lens=28)

    def cam_pos(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        return Vector((-18.0 + 36.0 * ease(t), 22.0, 9.5 + 1.5 * math.sin(t * math.pi)))

    def cam_tgt(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        return Vector((-10.0 + 20.0 * t, 38.0, 7.5))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 03 shaolin GK talk bust
# ---------------------------------------------------------------------------
def build_03() -> int:
    remove_players()
    _show_pitch()
    hide_ball()
    frames = 216
    gx = goal_l_x()
    pos = Vector((gx + 5.5, 0.2, 0.0))
    yaw = yaw_face_neg_y()  # face camera (-Y)

    arm, root = spawn_player(
        "Shaolin",
        SHAOLIN_ORANGE,
        pos,
        yaw,
        actions=["idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw)
    add_nla_loop(arm, "idle", 1, frames)
    add_talk_strip(arm, "ShaolinGK_Talk", frames, _talk_deltas_calm, TALK_BONES, step=3)

    cam = setup_new_cam("CamCut03", lens=40)

    def cam_pos(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        return Vector((pos.x + 0.4, pos.y - 5.2 + 0.35 * t, 2.85))

    def cam_tgt(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        return Vector((pos.x, pos.y + 0.1, 2.55 + 0.08 * t))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=4)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 04 volley rally — 4 exchanges Norway ↔ Shaolin GK
# ---------------------------------------------------------------------------
def build_04() -> int:
    remove_players()
    _show_pitch()
    frames = 360
    gx = goal_l_x()
    # spaced on y so SIDE_GAP holds; Norway at +y, GK at -y near goal
    nor_pos = Vector((gx + 16.0, SIDE_GAP * 0.65, 0.0))
    gk_pos = Vector((gx + 5.5, -SIDE_GAP * 0.65, 0.0))
    assert (nor_pos - gk_pos).length >= SIDE_GAP

    yaw_n = yaw_face_neg_x()
    yaw_gk = yaw_face_pos_x()

    nor_arm, nor_root = spawn_player(
        "Norway",
        NORWAY_RED,
        nor_pos,
        yaw_n,
        actions=["idle", "fight_kick"],
        split=(NORWAY_RED, NORWAY_WHITE, 0.42),
    )
    gk_arm, gk_root = spawn_player(
        "Shaolin",
        SHAOLIN_ORANGE,
        gk_pos,
        yaw_gk,
        actions=["fight_idle", "fight_punch", "idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(nor_arm)
    _clear_all_nla(gk_arm)
    animate_root(nor_root, [(1, nor_pos), (frames, nor_pos)], yaw_n)
    animate_root(gk_root, [(1, gk_pos), (frames, gk_pos)], yaw_gk)

    # timeline: kick1, clear1, kick2, clear2, kick3, clear3, kick4, clear4
    events = [40, 70, 110, 140, 180, 210, 250, 280]  # 4 kicks + 4 clears
    kicks = events[0::2]
    clears = events[1::2]

    add_nla_hold(nor_arm, "idle", 1, kicks[0] - 8, af=5)
    add_nla_hold(gk_arm, "fight_idle", 1, clears[0] - 8, af=10)
    for i, fk in enumerate(kicks):
        add_nla_once(nor_arm, "fight_kick", fk - 10, fk + 14)
        nxt = kicks[i + 1] - 11 if i + 1 < len(kicks) else frames
        add_nla_hold(nor_arm, "idle", fk + 15, nxt, af=6)
    for i, fc in enumerate(clears):
        add_nla_once(gk_arm, "fight_punch", fc - 8, fc + 12)
        nxt = clears[i + 1] - 9 if i + 1 < len(clears) else frames
        add_nla_hold(gk_arm, "fight_idle", fc + 13, nxt, af=10)

    ball = clear_ball_anim()
    # waypoints along the midpoint lane between bodies (never through torsos)
    mid_y = (nor_pos.y + gk_pos.y) * 0.5
    nor_feet = Vector((nor_pos.x - 1.8, mid_y + 0.9, BALL_GROUND_Z + 0.4))
    gk_hand = Vector((gk_pos.x + 1.5, mid_y - 0.9, BALL_GROUND_Z + 1.6))
    points = [nor_feet]
    for i in range(4):
        points.append(gk_hand.copy())
        points.append(nor_feet.copy() if i < 3 else Vector((gx - 1.2, mid_y * 0.2, GOAL_H * 0.45)))
    # events map to arrivals at points[1..]
    arrival = [1] + events

    def ball_path(f: int) -> Vector:
        # find segment
        if f <= arrival[0]:
            return points[0].copy()
        for i in range(len(arrival) - 1):
            a0, a1 = arrival[i], arrival[i + 1]
            if f <= a1 or i == len(arrival) - 2:
                t = ease((f - a0) / max(1, a1 - a0))
                p0, p1 = points[i], points[min(i + 1, len(points) - 1)]
                p = p0.lerp(p1, min(1.0, t))
                p.z += 0.55 * math.sin(min(1.0, t) * math.pi)
                return p
        return points[-1].copy()

    key_ball(ball, range(1, frames + 1, 2), ball_path)

    cam = setup_new_cam("CamCut04", lens=32)

    def cam_pos(f: int) -> Vector:
        b = ball_path(f)
        return Vector((b.x + 4.0, b.y - 12.0, 4.0))

    def cam_tgt(f: int) -> Vector:
        b = ball_path(f)
        return Vector((b.x, b.y * 0.3, max(1.2, b.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 05 shaolin goal v1 — classic mid-range into Goal_L
# ---------------------------------------------------------------------------
def build_05() -> int:
    remove_players()
    _show_pitch()
    frames = 264
    gx = goal_l_x()
    yaw = yaw_face_neg_x()
    start = Vector((gx + 48.0, -0.5, 0.0))
    kick_pos = Vector((gx + 22.0, -0.3, 0.0))
    # distant unused GK
    gk_far = Vector((gx + 3.0, 14.0, 0.0))
    ball_goal = Vector((gx - 1.5, -GOAL_INNER_HALF_W * 0.55, GOAL_H * 0.62))
    f_run = 100
    f_kick = 122
    f_goal = 152

    arm, root = spawn_player(
        "Shaolin",
        SHAOLIN_ORANGE,
        start,
        yaw,
        actions=["run", "fight_kick", "idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    gk_arm, gk_root = spawn_player(
        "Shaolin_GK",
        SHAOLIN_ORANGE,
        gk_far,
        yaw_face_pos_x(),
        actions=["fight_idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(arm)
    _clear_all_nla(gk_arm)

    def path(f: int) -> Vector:
        if f <= f_run:
            t = ease((f - 1) / max(1, f_run - 1))
            return start.lerp(kick_pos, t)
        if f <= f_kick:
            t = (f - f_run) / max(1, f_kick - f_run)
            return kick_pos + Vector((-0.45 * ease(t), 0.0, 0.0))
        t = (f - f_kick) / max(1, frames - f_kick)
        return kick_pos + Vector((-0.45 - 1.0 * ease(min(1.0, t)), 0.1 * t, 0.0))

    keys = [(f, path(f)) for f in range(1, frames + 1, 2)]
    keys.append((frames, path(frames)))
    animate_root(root, keys, yaw)
    animate_root(gk_root, [(1, gk_far), (frames, gk_far)], yaw_face_pos_x())
    add_nla_loop(arm, "run", 1, f_run)
    add_nla_once(arm, "fight_kick", f_run + 1, f_kick + 16)
    add_nla_hold(arm, "idle", f_kick + 17, frames, af=8)
    add_nla_hold(gk_arm, "fight_idle", 1, frames, af=10)

    ball = clear_ball_anim()
    move = Vector((-1.0, 0.0, 0.0))

    def ball_path(f: int) -> Vector:
        p = path(f)
        if f < f_kick:
            return ball_ahead_of(p, move, f, arm=arm)
        t = min(1.0, (f - f_kick) / max(1, f_goal - f_kick))
        u = 1.0 - (1.0 - t) ** 2.5
        s = ball_ahead_of(path(f_kick - 1), move, f_kick - 1, arm=arm)
        out = s.lerp(ball_goal, u)
        out.z = BALL_GROUND_Z + (ball_goal.z - BALL_GROUND_Z) * u + 1.2 * math.sin(u * math.pi) * (1.0 - 0.4 * u)
        if f > f_goal:
            t2 = (f - f_goal) / max(1, frames - f_goal)
            out = ball_goal + Vector((-0.6 * ease(min(1.0, t2)), 0.1 * t2, -0.45 * ease(min(1.0, t2))))
            out.z = max(BALL_GROUND_Z + 0.3, out.z)
        return out

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    cam = setup_new_cam("CamCut05", lens=30)

    def cam_pos(f: int) -> Vector:
        b = ball_path(f)
        p = path(f)
        if f < f_kick:
            return Vector((p.x + 5.0, p.y - 11.0, 3.6))
        return Vector((b.x + 7.0, b.y - 12.0, 4.4))

    def cam_tgt(f: int) -> Vector:
        b = ball_path(f)
        return Vector((b.x - 1.0, b.y * 0.3, max(1.2, b.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 06 shaolin goal v2 — aerial / near-post, other camera side
# ---------------------------------------------------------------------------
def build_06() -> int:
    remove_players()
    _show_pitch()
    frames = 264
    gx = goal_l_x()
    yaw = yaw_face_neg_x()
    start = Vector((gx + 40.0, 1.8, 0.0))
    kick_pos = Vector((gx + 14.0, 1.1, 0.0))
    ball_goal = Vector((gx - 1.3, GOAL_INNER_HALF_W * 0.82, GOAL_H * 0.4))  # near post
    f_run = 96
    f_air = 112
    f_kick = 128
    f_goal = 154

    arm, root = spawn_player(
        "Shaolin",
        SHAOLIN_ORANGE,
        start,
        yaw,
        actions=["run", "fight_kick", "jump_full", "idle"],
        split=(SHAOLIN_ORANGE, SHAOLIN_WHITE, 0.42),
    )
    _clear_all_nla(arm)

    def path(f: int) -> Vector:
        if f <= f_run:
            t = ease((f - 1) / max(1, f_run - 1))
            return start.lerp(kick_pos, t)
        if f <= f_kick:
            t = (f - f_run) / max(1, f_kick - f_run)
            p = kick_pos + Vector((-0.5 * ease(t), -0.15 * t, 0.0))
            # brief aerial rise
            if f_air <= f <= f_kick:
                u = (f - f_air) / max(1, f_kick - f_air)
                p.z = 1.1 * math.sin(min(1.0, u) * math.pi)
            return p
        t = (f - f_kick) / max(1, frames - f_kick)
        p = kick_pos + Vector((-0.5 - 0.8 * ease(min(1.0, t)), -0.1, 0.0))
        p.z = max(0.0, 0.35 * (1.0 - ease(min(1.0, t * 2.0))))
        return p

    keys = [(f, path(f)) for f in range(1, frames + 1, 2)]
    keys.append((frames, path(frames)))
    animate_root(root, keys, yaw)
    add_nla_loop(arm, "run", 1, f_run)
    add_nla_once(arm, "jump_full", f_run + 1, f_air + 6)
    add_nla_once(arm, "fight_kick", f_air + 7, f_kick + 14)
    add_nla_hold(arm, "idle", f_kick + 15, frames, af=8)

    ball = clear_ball_anim()
    move = Vector((-1.0, 0.0, 0.0))

    def ball_path(f: int) -> Vector:
        p = path(f)
        if f < f_kick:
            bp = ball_ahead_of(Vector((p.x, p.y, 0.0)), move, f, arm=arm)
            bp.z = BALL_GROUND_Z + p.z * 0.35
            return bp
        t = min(1.0, (f - f_kick) / max(1, f_goal - f_kick))
        u = 1.0 - (1.0 - t) ** 2.3
        s = ball_ahead_of(Vector((path(f_kick - 1).x, path(f_kick - 1).y, 0.0)), move, f_kick - 1, arm=arm)
        s.z = BALL_GROUND_Z + 0.6
        out = s.lerp(ball_goal, u)
        out.z = s.z + (ball_goal.z - s.z) * u + 0.7 * math.sin(u * math.pi)
        if f > f_goal:
            t2 = (f - f_goal) / max(1, frames - f_goal)
            out = ball_goal + Vector((-0.55 * ease(min(1.0, t2)), -0.05 * t2, -0.35 * ease(min(1.0, t2))))
            out.z = max(BALL_GROUND_Z + 0.25, out.z)
        return out

    key_ball(ball, range(1, frames + 1, 2), ball_path)
    # other camera side (+Y)
    cam = setup_new_cam("CamCut06", lens=28)

    def cam_pos(f: int) -> Vector:
        b = ball_path(f)
        p = path(f)
        if f < f_kick:
            return Vector((p.x + 4.5, p.y + 11.5, 4.8 + p.z * 0.4))
        return Vector((b.x + 6.5, b.y + 10.5, 5.2))

    def cam_tgt(f: int) -> Vector:
        b = ball_path(f)
        return Vector((b.x - 1.0, b.y * 0.2, max(1.3, b.z)))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=3)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 07 norway interview
# ---------------------------------------------------------------------------
def build_07() -> int:
    remove_players()
    frames = 288
    _hide_pitch(keep_extra=("Norway_", "Interview_"))
    hide_ball()
    _setup_interview_set(NORWAY_RED, NORWAY_WHITE)
    pos = Vector((0.0, 0.0, 0.35))
    yaw = yaw_face_neg_y()
    arm, root = spawn_player(
        "Norway",
        NORWAY_RED,
        pos,
        yaw,
        actions=["idle"],
        split=(NORWAY_RED, NORWAY_WHITE, 0.42),
    )
    _clear_all_nla(arm)
    keys = []
    for f in range(1, frames + 1, 3):
        sway = 0.012 * math.sin(f * 0.16)
        keys.append((f, Vector((pos.x + sway, pos.y, pos.z))))
    keys.append((frames, pos))
    animate_root(root, keys, yaw)
    add_nla_loop(arm, "idle", 1, frames)
    add_talk_strip(arm, "Norway_Talk", frames, _talk_deltas_calm, TALK_BONES, step=3)

    cam = setup_new_cam("CamCut07", lens=35)

    def cam_pos(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        return Vector((-0.6 + 0.12 * t, -8.2 + 0.35 * t, 3.4))

    def cam_tgt(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        return Vector((0.04 * math.sin(t * math.pi), 0.1, 3.1 + 0.08 * t))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=4)
    set_frame_range(frames)
    return frames


# ---------------------------------------------------------------------------
# 08 norway kungfu dojo
# ---------------------------------------------------------------------------
def build_08() -> int:
    remove_players()
    frames = 300
    _hide_pitch(keep_extra=("Norway_", "Dojo_"))
    hide_ball()
    _setup_dojo()
    pos = Vector((0.0, 0.0, 0.18))
    yaw = yaw_face_neg_y()
    arm, root = spawn_player(
        "Norway",
        NORWAY_RED,
        pos,
        yaw,
        actions=["fight_idle", "fight_punch", "fight_kick", "idle"],
        split=(NORWAY_RED, NORWAY_WHITE, 0.42),
    )
    _clear_all_nla(arm)
    animate_root(root, [(1, pos), (frames, pos)], yaw)

    # slow sequenced kungfu
    add_nla_hold(arm, "fight_idle", 1, 60, af=12)
    add_nla_once(arm, "fight_punch", 61, 110)
    add_nla_hold(arm, "fight_idle", 111, 150, af=14)
    add_nla_once(arm, "fight_kick", 151, 210)
    add_nla_hold(arm, "fight_idle", 211, 250, af=10)
    add_nla_once(arm, "fight_punch", 251, 280)
    add_nla_hold(arm, "fight_idle", 281, frames, af=12)

    cam = setup_new_cam("CamCut08", lens=32)

    def cam_pos(f: int) -> Vector:
        t = (f - 1) / max(1, frames - 1)
        return Vector((0.3 * math.sin(t * math.pi), -7.5 + 0.4 * t, 2.6))

    def cam_tgt(f: int) -> Vector:
        return Vector((0.0, 0.2, 1.85))

    _dense_cam(cam, frames, cam_pos, cam_tgt, step=4)
    set_frame_range(frames)
    return frames


BUILDERS: Dict[str, Callable[[], int]] = {
    "01": build_01,
    "02": build_02,
    "03": build_03,
    "04": build_04,
    "05": build_05,
    "06": build_06,
    "07": build_07,
    "08": build_08,
}
