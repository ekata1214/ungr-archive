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
PASS1_START = 88
PASS1_RELEASE = 94
PASS1_RECEIVE = 128
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


BALL_FOOT_AHEAD = 0.30  # 前足ボーンより進行方向へ（ワールド単位）


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


def _ball_at_feet_frame(
    arm: bpy.types.Object | None,
    root: bpy.types.Object,
    yaw: float,
    frame: int,
) -> Vector:
    """走行中 — 前足のやや前方にボールを置く（足の後ろに入らない）"""
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    if arm and arm.pose.bones.get("foot.l") and arm.pose.bones.get("foot.r"):
        rp = root.matrix_world.translation
        fd = _forward_from_yaw(yaw)
        fl = arm.matrix_world @ arm.pose.bones["foot.l"].head
        fr = arm.matrix_world @ arm.pose.bones["foot.r"].head
        lead = fl if (fl - rp).dot(fd) >= (fr - rp).dot(fd) else fr
        trail = fr if lead is fl else fl
        # 前足寄り + 両足の中間Yで自然なドリブル位置
        mid_y = (fl.y + fr.y) * 0.5
        p = lead + fd * BALL_FOOT_AHEAD
        p.y = mid_y
        # 万一トレイル足より後ろなら前足基準に補正
        if (p - rp).dot(fd) < (trail - rp).dot(fd):
            p = lead + fd * (BALL_FOOT_AHEAD + 0.12)
            p.y = mid_y
        p.z = BALL_GROUND_Z
        return p
    return _ball_at_player(root.matrix_world.translation.copy(), yaw)


def _ball_at_root_frame(
    root: bpy.types.Object,
    yaw: float,
    frame: int,
    arm: bpy.types.Object | None = None,
) -> Vector:
    if arm is None:
        arm = _arm_of_root(root)
    return _ball_at_feet_frame(arm, root, yaw, frame)


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
) -> None:
    """ドリブル/保持 — 前足ボーンにフレームごと追従"""
    if f1 < f0:
        return
    if arm is None:
        arm = _arm_of_root(root)
    step = 2 if f1 - f0 > 8 else 1
    for f in range(f0, f1 + 1, step):
        _kf_loc(ball, f, _ball_at_feet_frame(arm, root, yaw, f))
    if (f1 - f0) % step != 0:
        _kf_loc(ball, f1, _ball_at_feet_frame(arm, root, yaw, f1))


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
    yaw_a = math.pi / 2
    yaw_d = -math.pi / 2

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

    _move_root(rp, [(1, Vector((22, -7, 0))), (500, Vector((22, -7, 0)))], yaw_a)
    _move_root(rr, [
        (1, Vector((16, 5, 0))), (PASS1_RECEIVE, Vector((16, 5, 0))),
        (200, Vector((-2, 3, 0))), (PASS2_START, Vector((-8, 2, 0))),
        (500, Vector((-12, 2, 0))),
    ], yaw_a)
    _move_root(rw, [
        (1, Vector((18, 11, 0))), (150, Vector((18, 11, 0))),
        (280, Vector((-6, 12, 0))), (500, Vector((-6, 12, 0))),
    ], yaw_a)
    _move_root(rs, [
        (1, Vector((10, -10, 0))), (220, Vector((10, -10, 0))),
        (340, Vector((-28, -8, 0))), (500, Vector((-28, -8, 0))),
    ], yaw_a)
    _move_root(rst, [
        (1, Vector((6, 0, 0))),
        (PASS2_RECEIVE, Vector((6, 0, 0))),
        (KICK_STRIP_START - 10, Vector((-10, 0, 0))),
        (KICK_STRIP_START - 2, Vector((-18, 0, 0))),
        (500, Vector((-16, 1, 0))),
    ], yaw_a)

    # --- 青：アクション（ボールと同期） ---
    _add_nla_strip(b_passer, "idle", 1, PASS1_START - 1)
    _add_nla_strip(b_passer, "fight_punch", PASS1_START, PASS1_START + 18)  # パス動作
    _add_nla_strip(b_passer, "idle", PASS1_START + 18, 500)

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

    # --- 赤：守備 ---
    rg = roots[r_gk.name]
    _move_root(rg, [(1, Vector((goal_x + 6, 0, 0))), (500, Vector((goal_x + 6, 0, 0)))], yaw_d)
    _add_nla_strip(r_gk, "idle", 1, 140)
    _add_nla_strip(r_gk, "fight_idle", 140, KICK_BALL_RELEASE + 40)
    _add_nla_strip(r_gk, "idle", KICK_BALL_RELEASE + 40, 500)

    for arm, start_pos, rush_at, rname in [
        (r_def_l, Vector((-48, -12, 0)), 120, "r_def_l"),
        (r_def_c, Vector((-40, 0, 0)), 100, "r_def_c"),
        (r_def_r, Vector((-45, 12, 0)), 125, "r_def_r"),
        (r_fb, Vector((-28, 16, 0)), 150, "r_fb"),
    ]:
        root = roots[arm.name]
        _move_root(root, [
            (1, start_pos), (rush_at, start_pos),
            (KICK_BALL_RELEASE, Vector((start_pos.x - 18, start_pos.y * 0.9, 0))),
            (500, Vector((start_pos.x - 18, start_pos.y * 0.9, 0))),
        ], yaw_d)
        _add_nla_strip(arm, "idle", 1, rush_at - 1)
        _add_nla_strip(arm, "run", rush_at, KICK_BALL_RELEASE + 20)
        _add_nla_strip(arm, "fight_idle", KICK_BALL_RELEASE + 20, KICK_BALL_RELEASE + 55)
        _add_nla_strip(arm, "idle", KICK_BALL_RELEASE + 55, 500)

    # --- ボール（前足追従 + パス/シュート同期） ---
    p_passer = _ball_at_feet_frame(b_passer, rp, yaw_a, PASS1_START - 1)
    p_recv = _ball_at_feet_frame(b_runner, rr, yaw_a, PASS1_RECEIVE)
    p_pass2_from = _ball_at_feet_frame(b_runner, rr, yaw_a, PASS2_START - 1)
    p_pass2_to = _ball_at_feet_frame(b_striker, rst, yaw_a, PASS2_RECEIVE)
    p_shot_start = _ball_at_feet_frame(b_striker, rst, yaw_a, KICK_STRIP_START + 3)
    p_goal = Vector((goal_x + 2.0, 0.0, BALL_GROUND_Z * 0.85))

    _ball_hold(ball, rp, b_passer, yaw_a, 1, PASS1_START - 1)
    _ball_pass_roll(
        ball, PASS1_START, PASS1_RELEASE, PASS1_RECEIVE, p_passer, p_recv, yaw_a, arc=0.4,
    )
    _ball_hold(ball, rr, b_runner, yaw_a, PASS1_RECEIVE, PASS2_START - 1)
    _ball_pass_roll(
        ball, PASS2_START, PASS2_RELEASE, PASS2_RECEIVE, p_pass2_from, p_pass2_to, yaw_a, arc=0.35,
    )
    _ball_hold(ball, rst, b_striker, yaw_a, PASS2_RECEIVE, KICK_STRIP_START + 3)
    _ball_shot(ball, KICK_STRIP_START + 3, KICK_BALL_RELEASE, SHOT_LAND, p_shot_start, p_goal, yaw_a)

    _ease_all_ball_keyframes(ball)
    bpy.context.scene.frame_set(1)

    print(
        f"Match v2: pass1 f{PASS1_RELEASE} pass2 f{PASS2_RELEASE} "
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
