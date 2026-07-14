# SPDX-License-Identifier: MIT
"""少林選手 — 空中ドリブル（離陸して浮遊しながらボールを足元で運ぶ）"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import bpy
from mathutils import Vector

from animate_soccer_match import (
    BALL_GROUND_Z,
    _add_nla_strip,
    _clear_all_nla,
    _clear_anim,
    _ease_all_ball_keyframes,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24
# 約5.5秒 — 助走離陸 → 空中ドリブル巡航
TOTAL_FRAMES = 132

F_CROUCH = 12
F_TAKEOFF = 28
F_CRUISE = 44
F_HOLD = 120

# 巡航高度（ルート z）。足元がはっきり空中に見える高さ
CRUISE_Z = 6.5
HOVER_AMP = 0.32

SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
SHAOLIN_WHITE = (0.96, 0.96, 0.98, 1.0)

# 左ゴール（Goal_L, -X）へ向かう
# yaw=0 は -Y 向き。顔を -X にするには 1.5π（kubo と同じ）
MOVE_YAW = math.pi * 1.5
MOVE_DIR = Vector((-1.0, 0.0, 0.0))
GOAL_TARGET_X = -131.25  # Goal_L


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _remove_all_players() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(
            (
                "Blue_",
                "Red_",
                "Japan_",
                "Shaolin_",
                "Kubo_",
                "Endo_",
                "Shin_",
                "Leao_",
                "Ronaldo_",
                "Netherlands_",
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _move_dir(_frame: int) -> Vector:
    return MOVE_DIR.copy()


def _path_xy(frame: int) -> Tuple[float, float]:
    """ミッド付近から左ゴール（-X）へ前進＋軽い蛇行。"""
    t = (frame - 1) / max(1, TOTAL_FRAMES - 1)
    # センター寄りスタート → ゴール前まで迫る（ゴール線は x≈-131）
    x = 18.0 - t * 95.0
    y = (
        1.2 * math.sin(t * 5.5 * math.pi)
        + 0.6 * math.sin(t * 11.0 * math.pi + 0.4)
    )
    return x, y


def _altitude(frame: int) -> float:
    """地面 → 離陸 → 空中ホバー巡航。"""
    if frame <= F_CROUCH:
        t = (frame - 1) / max(1, F_CROUCH - 1)
        return -0.18 * _ease_in_out(t)
    if frame <= F_TAKEOFF:
        t = (frame - F_CROUCH) / max(1, F_TAKEOFF - F_CROUCH)
        return -0.18 - 0.1 * _ease_in_out(t)
    if frame <= F_CRUISE:
        t = (frame - F_TAKEOFF) / max(1, F_CRUISE - F_TAKEOFF)
        ease = math.sin(_ease_in_out(t) * math.pi * 0.5)
        return -0.28 + (CRUISE_Z + 0.28) * ease
    # 巡航：わずかに上下するホバー
    phase = (frame - F_CRUISE) * 0.18
    bob = HOVER_AMP * math.sin(phase)
    if frame <= F_HOLD:
        return CRUISE_Z + bob
    # 終盤も宙にとどまる（ランディングなし — 少林っぽさ）
    return CRUISE_Z + bob * 0.85


def _shaolin_path(frame: int) -> Vector:
    x, y = _path_xy(frame)
    return Vector((x, y, _altitude(frame)))


def _ball_at_air_feet(
    player: Vector,
    frame: int,
    move_dir: Vector,
    arm: bpy.types.Object | None = None,
) -> Vector:
    """体の前方・両足の最前点より前に置く（空中でも同じ）。"""
    phase = frame * 0.72
    # ルート基準の前方量（大きめ）＋足の先よりさらに前
    ahead = 2.4 + 0.1 * math.sin(phase * 2.3)
    side = 0.05 * math.sin(phase * 3.4)
    bounce = 0.08 * abs(math.sin(phase * 4.4))
    fd = move_dir.normalized()
    right = _right_of(fd)
    foot_z: float | None = None

    if arm is not None and arm.pose is not None:
        bl = arm.pose.bones.get("ball.l") or arm.pose.bones.get("foot.l")
        br = arm.pose.bones.get("ball.r") or arm.pose.bones.get("foot.r")
        if bl is not None and br is not None:
            fl = arm.matrix_world @ bl.head
            fr = arm.matrix_world @ br.head
            foot_ahead = max((fl - player).dot(fd), (fr - player).dot(fd))
            # 前足トゥより十分先（体の影の真下に見えない距離）
            ahead = max(ahead, foot_ahead + 1.6)
            foot_z = min(fl.z, fr.z)

    p = player + fd * ahead + right * side
    if player.z < 0.35:
        p.z = BALL_GROUND_Z + bounce * 0.35
    else:
        # つま先高さで前に置く（胴の真下に見えないよう少し低め）
        base_z = foot_z if foot_z is not None else player.z + 0.45
        p.z = base_z + 0.05 + bounce
    return p


def _animate_root_fixed(
    root: bpy.types.Object,
    keys: List[Tuple[int, Vector]],
    yaw: float,
) -> None:
    _clear_anim(root)
    for f, loc in keys:
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, yaw)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def setup_character() -> Tuple[bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    arm = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [Vector((10.0, 0.0, 0.0))],
        actions=["run"],
        facing_yaw=MOVE_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(arm), SHAOLIN_ORANGE, SHAOLIN_WHITE, z_cut=0.42)
    return arm, _root_of(arm)


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamShaolinAirDribble")
    cam = bpy.data.objects.new("CamShaolinAirDribble", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_data.lens = 30

    key_frames = list(range(1, TOTAL_FRAMES + 1, 8))
    if TOTAL_FRAMES not in key_frames:
        key_frames.append(TOTAL_FRAMES)

    for f in key_frames:
        p = _shaolin_path(f)
        md = _move_dir(f)
        ball = _ball_at_air_feet(p, f, md)
        right = _right_of(md)
        # ほぼ水平の横アングルで、足元とピッチの隙間が見えるようにする
        mid = Vector((p.x, p.y, max(1.2, p.z + 1.65)))
        pos = mid - md * 2.2 + right * 11.5 + Vector((0.0, 0.0, 0.4))
        tgt = mid + md * 1.0 + Vector((0.0, 0.0, -0.15))
        # ボールもフレーミングに少し寄せる
        tgt = tgt.lerp(Vector((ball.x, ball.y, ball.z + 0.3)), 0.25)
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_shaolin_aerial_dribble() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.render.fps = FPS

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball not found — run build_field_only first")

    arm, root = setup_character()
    _clear_all_nla(arm)
    if ball.animation_data:
        ball.animation_data_clear()

    # 毎フレームキーでボールと高度を同期（疎キーの Bezier ずれ防止）
    root_keys = [(f, _shaolin_path(f)) for f in range(1, TOTAL_FRAMES + 1)]
    _animate_root_fixed(root, root_keys, MOVE_YAW)

    # 空中でも脚のキックスイングが出るよう run をループ
    _add_nla_strip(arm, "run", 1, TOTAL_FRAMES)

    # NLA 評価後に両足の最前点を見て、常に体・足の前へ
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for f in range(1, TOTAL_FRAMES + 1):
        scene.frame_set(f)
        depsgraph.update()
        p = root.matrix_world.translation.copy()
        _kf_loc(ball, f, _ball_at_air_feet(p, f, _move_dir(f), arm=arm))
    _ease_all_ball_keyframes(ball)

    setup_camera()
    scene.frame_set(1)
    print(
        f"Shaolin aerial dribble: {TOTAL_FRAMES}f @ {FPS}fps — "
        f"toward Goal_L (x={GOAL_TARGET_X}), cruise z≈{CRUISE_Z}"
    )


def render_shaolin_aerial_dribble_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    animate_shaolin_aerial_dribble()
    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "shaolin_aerial_dribble.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Shaolin aerial dribble: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-shaolin-aerial-dribble-video" in sys.argv:
        render_shaolin_aerial_dribble_video()
    else:
        animate_shaolin_aerial_dribble()
