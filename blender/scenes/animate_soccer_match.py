# SPDX-License-Identifier: MIT
"""500f サッカー試合風シーケンス — パス・守備・シュート・ゴール"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Vector

MATCH_FRAMES = 500
FPS = 24

# build_part_field と同スケール
_SCALE = 2.5
PITCH_HALF = 105.0 * _SCALE / 2  # 131.25
BALL_R = 0.22 * _SCALE
BALL_GROUND_Z = BALL_R


def _root_of(arm: bpy.types.Object) -> bpy.types.Object:
    if arm.parent:
        return arm.parent
    raise ValueError(f"No root parent for {arm.name}")


def _clear_anim(obj: bpy.types.Object) -> None:
    if obj.animation_data:
        obj.animation_data_clear()
    obj.animation_data_create()


def _set_linear() -> None:
    for action in bpy.data.actions:
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def _kf_loc(obj: bpy.types.Object, frame: int, loc: Vector) -> None:
    obj.location = loc
    obj.keyframe_insert(data_path="location", frame=frame)


def _kf_rot_z(obj: bpy.types.Object, frame: int, yaw: float) -> None:
    obj.rotation_euler = Euler((0, 0, yaw))
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def _lerp(a: Vector, b: Vector, t: float) -> Vector:
    return a + (b - a) * t


def _add_nla_strip(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
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
    strip.action_frame_start = act_start
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


def _ball_keyframes_pass(
    ball: bpy.types.Object,
    f0: int,
    p0: Vector,
    f1: int,
    p1: Vector,
    arc: float = 1.8,
) -> None:
    mid_f = (f0 + f1) // 2
    mid = _lerp(p0, p1, 0.5)
    mid.z = max(p0.z, p1.z) + arc
    _kf_loc(ball, f0, p0)
    _kf_loc(ball, mid_f, mid)
    _kf_loc(ball, f1, p1)


def _ball_keyframes_shot(
    ball: bpy.types.Object,
    f0: int,
    p0: Vector,
    f1: int,
    p1: Vector,
    peak: float = 4.5,
) -> None:
    """シュート弾道 — 高めの放物線"""
    steps = [0.0, 0.25, 0.5, 0.75, 1.0]
    for i, t in enumerate(steps):
        f = int(f0 + (f1 - f0) * t)
        p = _lerp(p0, p1, t)
        p.z = BALL_GROUND_Z + math.sin(t * math.pi) * peak
        _kf_loc(ball, f, p)


def _move_root(
    root: bpy.types.Object,
    frames: List[Tuple[int, Vector]],
    yaw: float,
) -> None:
    for frame, loc in frames:
        _kf_loc(root, frame, loc)
        _kf_rot_z(root, frame, yaw)


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
    """パス → 守備 → ラストパス → シュート → ゴール（500f）"""
    setup_match_timeline()

    blues = _find_arms("Blue_")
    reds = _find_arms("Red_")
    if len(blues) < 5 or len(reds) < 5:
        raise RuntimeError("Need Blue_01..05 and Red_01..05 armatures in scene")

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball object not found")

    goal_x = -PITCH_HALF
    goal_y = 0.0

    # 役割
    b_passer = blues[0]   # Blue_01
    b_runner = blues[1]   # Blue_02
    b_wing = blues[2]     # Blue_03
    b_support = blues[3]  # Blue_04
    b_striker = blues[4]  # Blue_05

    r_gk = reds[0]        # Red_01 ゴール前
    r_def_l = reds[1]
    r_def_c = reds[2]
    r_def_r = reds[3]
    r_fb = reds[4]

    roots = {arm.name: _root_of(arm) for arm in blues + reds}
    yaw_attack = math.pi / 2          # 左ゴール（-X）へ
    yaw_defend = -math.pi / 2         # 攻撃を受ける

    # --- 全員 NLA リセット ---
    for arm in blues + reds:
        _clear_all_nla(arm)

    if ball.animation_data:
        ball.animation_data_clear()

    # ===== 青チーム動き =====
    _move_root(roots[b_passer.name], [
        (1, Vector((25, -8, 0))),
        (80, Vector((25, -8, 0))),
        (130, Vector((22, -5, 0))),
        (500, Vector((22, -5, 0))),
    ], yaw_attack)
    _add_nla_strip(b_passer, "idle", 1, 75)
    _add_nla_strip(b_passer, "walk", 75, 130)
    _add_nla_strip(b_passer, "idle", 130, 500)

    _move_root(roots[b_runner.name], [
        (1, Vector((18, 4, 0))),
        (130, Vector((18, 4, 0))),
        (220, Vector((-5, 2, 0))),
        (280, Vector((-15, 1, 0))),
        (500, Vector((-15, 1, 0))),
    ], yaw_attack)
    _add_nla_strip(b_runner, "idle", 1, 130)
    _add_nla_strip(b_runner, "run", 130, 280)
    _add_nla_strip(b_runner, "idle", 280, 500)

    _move_root(roots[b_wing.name], [
        (1, Vector((20, 12, 0))),
        (130, Vector((20, 12, 0))),
        (250, Vector((-8, 14, 0))),
        (500, Vector((-8, 14, 0))),
    ], yaw_attack)
    _add_nla_strip(b_wing, "walk", 1, 130)
    _add_nla_strip(b_wing, "run", 130, 280)
    _add_nla_strip(b_wing, "idle", 280, 500)

    _move_root(roots[b_support.name], [
        (1, Vector((12, -12, 0))),
        (200, Vector((12, -12, 0))),
        (300, Vector((-25, -10, 0))),
        (500, Vector((-25, -10, 0))),
    ], yaw_attack)
    _add_nla_strip(b_support, "idle", 1, 200)
    _add_nla_strip(b_support, "run", 200, 320)
    _add_nla_strip(b_support, "idle", 320, 500)

    _move_root(roots[b_striker.name], [
        (1, Vector((8, 0, 0))),
        (240, Vector((8, 0, 0))),
        (270, Vector((-22, 0, 0))),
        (320, Vector((-22, 0, 0))),
        (500, Vector((-18, 2, 0))),
    ], yaw_attack)
    _add_nla_strip(b_striker, "idle", 1, 240)
    _add_nla_strip(b_striker, "run", 240, 268)
    _add_nla_strip(b_striker, "fight_kick", 268, 310)
    _add_nla_strip(b_striker, "idle", 310, 500)

    # ===== 赤チーム守備 =====
    _move_root(roots[r_gk.name], [
        (1, Vector((goal_x + 8, 0, 0))),
        (500, Vector((goal_x + 8, 0, 0))),
    ], yaw_defend)
    _add_nla_strip(r_gk, "idle", 1, 150)
    _add_nla_strip(r_gk, "fight_idle", 150, 320)
    _add_nla_strip(r_gk, "idle", 320, 500)

    _move_root(roots[r_def_l.name], [
        (1, Vector((-55, -14, 0))),
        (150, Vector((-55, -14, 0))),
        (280, Vector((-70, -10, 0))),
        (500, Vector((-70, -10, 0))),
    ], yaw_defend)
    _add_nla_strip(r_def_l, "idle", 1, 150)
    _add_nla_strip(r_def_l, "run", 150, 300)
    _add_nla_strip(r_def_l, "fight_idle", 300, 360)
    _add_nla_strip(r_def_l, "idle", 360, 500)

    _move_root(roots[r_def_c.name], [
        (1, Vector((-45, 0, 0))),
        (130, Vector((-45, 0, 0))),
        (290, Vector((-60, 2, 0))),
        (500, Vector((-60, 2, 0))),
    ], yaw_defend)
    _add_nla_strip(r_def_c, "idle", 1, 130)
    _add_nla_strip(r_def_c, "dash", 130, 220)
    _add_nla_strip(r_def_c, "run", 220, 310)
    _add_nla_strip(r_def_c, "fight_idle", 310, 370)
    _add_nla_strip(r_def_c, "idle", 370, 500)

    _move_root(roots[r_def_r.name], [
        (1, Vector((-50, 14, 0))),
        (160, Vector((-50, 14, 0))),
        (300, Vector((-68, 12, 0))),
        (500, Vector((-68, 12, 0))),
    ], yaw_defend)
    _add_nla_strip(r_def_r, "idle", 1, 160)
    _add_nla_strip(r_def_r, "run", 160, 310)
    _add_nla_strip(r_def_r, "fight_idle", 310, 380)
    _add_nla_strip(r_def_r, "idle", 380, 500)

    _move_root(roots[r_fb.name], [
        (1, Vector((-30, 20, 0))),
        (180, Vector((-30, 20, 0))),
        (320, Vector((-55, 18, 0))),
        (500, Vector((-55, 18, 0))),
    ], yaw_defend)
    _add_nla_strip(r_fb, "walk", 1, 180)
    _add_nla_strip(r_fb, "run", 180, 330)
    _add_nla_strip(r_fb, "idle", 330, 500)

    # ===== ボール =====
    p_passer = Vector((25, -6, BALL_GROUND_Z))
    p_receiver = Vector((18, 3, BALL_GROUND_Z))
    p_striker = Vector((-22, 0, BALL_GROUND_Z))
    p_goal = Vector((goal_x + 1.5, goal_y, BALL_GROUND_Z * 0.8))

    _kf_loc(ball, 1, p_passer)
    _ball_keyframes_pass(ball, 80, p_passer, 130, p_receiver, arc=1.2)
    _kf_loc(ball, 220, Vector((-5, 2, BALL_GROUND_Z)))
    _ball_keyframes_pass(ball, 240, Vector((-5, 2, BALL_GROUND_Z)), 270, p_striker, arc=0.6)
    _kf_loc(ball, 290, p_striker)
    _ball_keyframes_shot(ball, 295, p_striker, 400, p_goal, peak=5.0)
    _kf_loc(ball, 500, p_goal)

    _set_linear()

    print(
        f"Match animation: {MATCH_FRAMES}f @ {FPS}fps — "
        "pass(80-130) → run(130-280) → pass(240-270) → kick(268-310) → goal(295-400)"
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
    """試合の流れに合わせてカメラをパン"""
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamMatch")
    cam = bpy.data.objects.new("CamMatch", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 42

    goal_x = -PITCH_HALF
    _kf_cam(cam, 1, Vector((35, -38, 9)), Vector((20, -5, 1.5)))
    _kf_cam(cam, 100, Vector((28, -32, 8)), Vector((22, -2, 1.2)))
    _kf_cam(cam, 180, Vector((8, -28, 7)), Vector((5, 2, 1.2)))
    _kf_cam(cam, 270, Vector((-18, -24, 6.5)), Vector((-20, 0, 1.5)))
    _kf_cam(cam, 340, Vector((-55, -20, 6)), Vector((-45, 0, 2.0)))
    _kf_cam(cam, 420, Vector((goal_x + 28, -16, 5.5)), Vector((goal_x + 2, 0, 2.5)))
    _kf_cam(cam, 500, Vector((goal_x + 32, -14, 5)), Vector((goal_x, 0, 2.0)))
    return cam


def render_match_preview() -> "Path":
    """500f アニメを MP4 で書き出し"""
    from pathlib import Path

    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_match_timeline()
    setup_black_world()
    setup_lights()
    setup_match_camera()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = MATCH_FRAMES
    scene.eevee.taa_render_samples = 24

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"

    out = RENDER_DIR / "match_preview.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering video: {out} ({MATCH_FRAMES} frames)...")
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
