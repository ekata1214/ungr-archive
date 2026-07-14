# SPDX-License-Identifier: MIT
"""遠藤航 vs 少林 — 正面ドリブルから幽霊のように消失、ボールだけ残る"""

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

VANISH_FRAMES = 260
FPS = 24

SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
SHAOLIN_WHITE = (0.96, 0.96, 0.98, 1.0)
ENDO_NAVY = (0.07, 0.14, 0.52, 1.0)

# 遠藤は +X 向き（少林がいる方向）、少林は -X 向き
ENDO_YAW = math.pi / 2
SHAOLIN_YAW = math.pi * 1.5

FADE_START = 55
FADE_END = 195
ENDO_POS = Vector((4.0, 0.0, 0.0))


def _remove_all_players() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("Blue_", "Red_", "Japan_", "Shaolin_", "Kubo_", "Endo_")):
            bpy.data.objects.remove(obj, do_unlink=True)


def _right_of(d: Vector) -> Vector:
    return Vector((d.y, -d.x, 0.0)).normalized()


def _shaolin_alpha(frame: int) -> float:
    if frame < FADE_START:
        return 1.0
    if frame >= FADE_END:
        return 0.0
    t = (frame - FADE_START) / (FADE_END - FADE_START)
    # すーっと消える — 後半で急に薄くなる
    return max(0.0, 1.0 - t ** 1.35)


def _shaolin_path(frame: int) -> Vector:
    """少林 — 遠藤の真正面へゆっくりドリブル"""
    t = min(1.0, (frame - 1) / 150.0)
    x = 14.0 - t * 8.5  # 遠藤(x=4)の真正面 ~5.5m まで接近
    y = 0.12 * math.sin(frame * 0.09) + 0.05 * math.sin(frame * 0.19)
    return Vector((x, y, 0.0))


def _endo_path(frame: int) -> Vector:
    """遠藤 — 堅実に立って見失う"""
    sway = 0.06 * math.sin(frame * 0.07)
    lean = 0.04 * math.sin(frame * 0.14 + 0.5)
    return Vector((ENDO_POS.x, ENDO_POS.y + sway, 0.0)) + Vector((lean, 0, 0))


def _ball_pos(frame: int, shaolin: Vector) -> Vector:
    """ボール — 少林足元 → 消失後も残る"""
    phase = frame * 0.45
    ahead = 0.34 + 0.06 * math.sin(phase * 2.0)
    side = 0.14 * math.sin(phase * 3.2)
    move_dir = Vector((-1.0, 0.0, 0.0))
    right = _right_of(move_dir)

    if frame < FADE_END:
        p = shaolin + move_dir * ahead + right * side
    else:
        # 消えたあとも同じ場所で微動
        anchor = _shaolin_path(FADE_END - 1)
        p = anchor + move_dir * 0.36 + right * (0.12 * math.sin(phase * 0.8))
    p.z = BALL_GROUND_Z
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


def _enable_material_blend(mesh_obj: bpy.types.Object) -> None:
    for mat in mesh_obj.data.materials:
        if not mat:
            continue
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        try:
            mat.shadow_method = "HASHED"
        except Exception:
            pass


def _kf_mesh_alpha(mesh_obj: bpy.types.Object, frame: int, alpha: float) -> None:
    for mat in mesh_obj.data.materials:
        if not mat or not mat.node_tree:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            continue
        inp = bsdf.inputs.get("Alpha")
        if inp is None:
            continue
        inp.default_value = alpha
        inp.keyframe_insert("default_value", frame=frame)


def setup_endo_vanish_characters() -> Tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()

    shaolin_arm = build_team(
        "Shaolin",
        SHAOLIN_ORANGE,
        [Vector((15, 0, 0))],
        actions=["walk"],
        facing_yaw=SHAOLIN_YAW,
    )[0]
    endo_arm = build_team(
        "Endo",
        ENDO_NAVY,
        [ENDO_POS],
        actions=["idle"],
        facing_yaw=ENDO_YAW,
    )[0]

    shaolin_mesh = _mesh_child(shaolin_arm)
    set_mesh_split_vertical(shaolin_mesh, SHAOLIN_ORANGE, SHAOLIN_WHITE, z_cut=0.42)
    _enable_material_blend(shaolin_mesh)

    return endo_arm, shaolin_arm, _root_of(endo_arm), _root_of(shaolin_arm)


def animate_endo_shaolin_ghost() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = VANISH_FRAMES
    scene.render.fps = FPS

    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball not found — run build_field_only first")

    endo_arm, shaolin_arm, endo_root, shaolin_root = setup_endo_vanish_characters()
    shaolin_mesh = next(ch for ch in shaolin_arm.children if ch.type == "MESH")

    for arm in (endo_arm, shaolin_arm):
        _clear_all_nla(arm)
    if ball.animation_data:
        ball.animation_data_clear()

    shaolin_keys = [(f, _shaolin_path(f)) for f in range(1, VANISH_FRAMES + 1)]
    endo_keys = [(f, _endo_path(f)) for f in range(1, VANISH_FRAMES + 1)]

    _animate_root_fixed(shaolin_root, shaolin_keys, SHAOLIN_YAW)
    _animate_root_fixed(endo_root, endo_keys, ENDO_YAW)

    _add_nla_strip(shaolin_arm, "walk", 1, FADE_END)
    _add_nla_strip(endo_arm, "idle", 1, VANISH_FRAMES)

    for f in range(1, VANISH_FRAMES + 1):
        s = _shaolin_path(f)
        _kf_loc(ball, f, _ball_pos(f, s))
    _ease_all_ball_keyframes(ball)

    for f in range(1, VANISH_FRAMES + 1, 4):
        _kf_mesh_alpha(shaolin_mesh, f, _shaolin_alpha(f))
    _kf_mesh_alpha(shaolin_mesh, FADE_END, 0.0)
    _kf_mesh_alpha(shaolin_mesh, VANISH_FRAMES, 0.0)

    setup_endo_vanish_camera()
    scene.frame_set(1)
    print(f"Endo vanish: {VANISH_FRAMES}f — face-off dribble, Shaolin fades, ball remains")


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_endo_vanish_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamEndoVanish")
    cam = bpy.data.objects.new("CamEndoVanish", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 30

    key_frames = list(range(1, VANISH_FRAMES + 1, 20))
    if VANISH_FRAMES not in key_frames:
        key_frames.append(VANISH_FRAMES)

    for f in key_frames:
        endo = _endo_path(f)
        sh = _shaolin_path(f)
        ball = _ball_pos(f, sh)
        mid = (endo + sh) * 0.5
        # 正面構図 — 2人の間、足元寄り
        cam_pos = mid + Vector((0.0, -6.5, 1.05))
        cam_tgt = ball + Vector((0.0, 0.0, 0.08))
        _kf_cam(cam, f, cam_pos, cam_tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def render_endo_ghost_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = VANISH_FRAMES
    scene.eevee.taa_render_samples = 8

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "endo_shaolin_vanish.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering endo vanish video: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-endo-ghost-video" in sys.argv:
        render_endo_ghost_video()
    else:
        animate_endo_shaolin_ghost()
        bpy.ops.wm.save_mainfile(filepath=str(blend))
