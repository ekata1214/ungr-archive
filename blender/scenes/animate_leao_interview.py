# SPDX-License-Identifier: MIT
"""レオン単独インタビュー — お立ち台＋背景パネルで約4秒話す

ポルトガルのレオン（WAY45）が、インタビュー受ける場所っぽい平面の前で
一人で話す短カット。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

from animate_soccer_match import (
    _clear_all_nla,
    _clear_anim,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24
# 約4秒
INTERVIEW_FRAMES = 96

PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

# カメラ側（-Y）を向いて話す（Mannequiny の yaw=0 が -Y）
LEAO_YAW = 0.0
LEAO_POS = Vector((0.0, 0.0, 0.35))  # お立ち台の上

PoseDict = Dict[str, Quaternion]

TALK_BONES = [
    "spine_01",
    "spine_02",
    "neck_01",
    "head",
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "hand.r",
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "hand.l",
]


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    exact = [c for c in candidates if c == name]
    return exact[0] if exact else sorted(candidates)[0]


def _add_nla_loop(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
) -> None:
    resolved = _resolve_action_name(action_name)
    action = bpy.data.actions.get(resolved)
    if not action:
        raise KeyError(resolved)

    ad = arm.animation_data
    if ad is None:
        arm.animation_data_create()
        ad = arm.animation_data
    ad.action = None

    track = ad.nla_tracks.new()
    track.name = f"{resolved}_loop"
    strip = track.strips.new(action.name, frame_start, action)
    strip.frame_start = frame_start
    strip.frame_end = frame_end + 1
    strip.repeat = max(1.0, (frame_end - frame_start + 1) / max(1.0, action.frame_range[1] - action.frame_range[0]))
    strip.blend_type = "REPLACE"
    strip.extrapolation = "NOTHING"
    strip.influence = 1.0
    strip.use_auto_blend = False


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
                "Fernandes_",
                "PortugalGK_",
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _hide_pitch_for_studio() -> None:
    """芝生・ライン・ゴールを隠してスタジオっぽくする。"""
    keep_prefixes = ("Light", "Sun", "World", "Camera", "Cam", "Leao_", "Interview_")
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            continue
        if obj.name.startswith(keep_prefixes):
            continue
        if obj.name == "Ball" or obj.name.startswith(
            (
                "Field_",
                "Line_",
                "Pen",
                "Goal",
                "Corner_",
                "Net",
                "Post",
                "Crossbar",
            )
        ):
            obj.hide_render = True
            obj.hide_viewport = True


def _hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if ball:
        ball.hide_render = True
        ball.hide_viewport = True


def _mat_rgba(name: str, rgba, rough: float = 0.75) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = rough
        spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
        if spec:
            spec.default_value = 0.15
    return mat


def _add_box(
    name: str,
    size: Tuple[float, float, float],
    location: Vector,
    rotation: Euler | None,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    # unit cube centered at origin, then scale via object
    verts = [
        (-0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5),
        (0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5),
        (-0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5),
        (0.5, 0.5, 0.5),
        (-0.5, 0.5, 0.5),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.scale = Vector(size)
    if rotation is not None:
        obj.rotation_euler = rotation
    obj.data.materials.append(mat)
    return obj


def setup_interview_set() -> None:
    """お立ち台＋インタビュー背景の平面パネル。"""
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Interview_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    floor_mat = _mat_rgba("Interview_FloorMat", (0.12, 0.12, 0.14, 1.0), 0.9)
    podium_mat = _mat_rgba("Interview_PodiumMat", (0.18, 0.18, 0.2, 1.0), 0.55)
    back_mat = _mat_rgba("Interview_BackMat", (0.08, 0.1, 0.16, 1.0), 0.85)
    stripe_mat = _mat_rgba("Interview_StripeMat", PORTUGAL_RED, 0.45)
    accent_mat = _mat_rgba("Interview_AccentMat", PORTUGAL_GREEN, 0.45)
    panel_mat = _mat_rgba("Interview_PanelMat", (0.16, 0.18, 0.24, 1.0), 0.7)
    mic_mat = _mat_rgba("Interview_MicMat", (0.05, 0.05, 0.06, 1.0), 0.35)

    # 床（足元周り）
    _add_box(
        "Interview_Floor",
        (7.0, 5.0, 0.1),
        Vector((0.0, 0.6, 0.05)),
        None,
        floor_mat,
    )
    # お立ち台
    _add_box(
        "Interview_Podium",
        (2.0, 1.5, 0.35),
        Vector((0.0, 0.0, 0.175)),
        None,
        podium_mat,
    )
    # メイン背景パネル（レオン後ろ＝+Y）
    _add_box(
        "Interview_Backdrop",
        (8.0, 0.12, 5.4),
        Vector((0.0, 2.4, 2.7)),
        None,
        back_mat,
    )
    # インタビューっぽい帯（上）
    _add_box(
        "Interview_Banner",
        (7.6, 0.14, 0.55),
        Vector((0.0, 2.28, 4.55)),
        None,
        stripe_mat,
    )
    # 下のアクセント帯
    _add_box(
        "Interview_Accent",
        (7.6, 0.14, 0.28),
        Vector((0.0, 2.28, 0.85)),
        None,
        accent_mat,
    )
    # 左右のロゴ風パネル
    _add_box(
        "Interview_LogoL",
        (1.6, 0.08, 1.6),
        Vector((-2.3, 2.26, 2.5)),
        None,
        panel_mat,
    )
    _add_box(
        "Interview_LogoR",
        (1.6, 0.08, 1.6),
        Vector((2.3, 2.26, 2.5)),
        None,
        panel_mat,
    )
    # マイクスタンド（手前・カメラ側）
    _add_box(
        "Interview_MicPole",
        (0.05, 0.05, 1.6),
        Vector((0.85, -1.05, 1.15)),
        None,
        mic_mat,
    )
    _add_box(
        "Interview_MicHead",
        (0.16, 0.1, 0.1),
        Vector((0.62, -1.05, 2.0)),
        Euler((0.0, 0.45, 0.0)),
        mic_mat,
    )


def _snapshot_pose(arm: bpy.types.Object) -> PoseDict:
    out: PoseDict = {}
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
        out[bone.name] = bone.rotation_quaternion.copy()
    return out


def _pose_with_deltas(base: PoseDict, deltas: Dict[str, Tuple[float, float, float]], weight: float = 1.0) -> PoseDict:
    out = {k: v.copy() for k, v in base.items()}
    for name, xyz in deltas.items():
        if name not in out:
            continue
        dx, dy, dz = xyz
        delta = Euler((dx * weight, dy * weight, dz * weight), "XYZ").to_quaternion()
        out[name] = out[name] @ delta
    return out


def _capture_idle_base(arm: bpy.types.Object) -> PoseDict:
    """idle NLA を評価した上半身ベース姿勢。"""
    muted = []
    ad = arm.animation_data
    if ad:
        muted = [(t, t.mute) for t in ad.nla_tracks]
        for t, _ in muted:
            # talk overlay 以外を有効のまま評価したいので mute はしない
            pass
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    idle = bpy.data.actions.get(_resolve_action_name("idle"))
    if idle:
        if not ad:
            arm.animation_data_create()
            ad = arm.animation_data
        prev = ad.action
        ad.action = idle
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        base = _snapshot_pose(arm)
        ad.action = prev
        return base
    return _snapshot_pose(arm)


def _talk_deltas(frame: int) -> Dict[str, Tuple[float, float, float]]:
    """話している風の頭・胴・手ぶり。"""
    t = frame / FPS
    nod = 0.07 * math.sin(t * 7.2) + 0.04 * math.sin(t * 11.0)
    turn = 0.11 * math.sin(t * 2.4 + 0.3) + 0.05 * math.sin(t * 5.1)
    lean = 0.05 * math.sin(t * 1.7)
    # 右手で説明している感じ（常に前に出して後ろ手にならない）
    gest = 0.55 + 0.45 * math.sin(t * 3.3)
    gest2 = 0.55 + 0.45 * math.sin(t * 2.1 + 1.2)
    return {
        "spine_01": (0.03 + lean * 0.4, 0.0, turn * 0.25),
        "spine_02": (0.06 + lean, 0.0, turn * 0.45),
        "neck_01": (0.04 + nod * 0.6, 0.0, turn * 0.7),
        "head": (0.05 + nod, 0.0, turn),
        "clavicle.r": (0.06, -0.08 - 0.04 * gest, 0.1),
        "upperarm.r": (0.55 + 0.2 * gest, -0.75 - 0.15 * gest2, 0.85 + 0.2 * gest),
        "lowerarm.r": (-1.05 - 0.15 * gest2, 0.25, 0.2),
        "hand.r": (0.3, 0.4 + 0.12 * gest, -0.65),
        "clavicle.l": (0.03, 0.05, -0.05),
        "upperarm.l": (0.22, 0.45, -0.28),
        "lowerarm.l": (-0.45, -0.12, -0.08),
        "hand.l": (0.08, -0.12, 0.18),
    }


def _add_bone_pose_replace_strip(
    arm: bpy.types.Object,
    name: str,
    strip_start: int,
    strip_end: int,
    keyed_poses: List[Tuple[int, PoseDict]],
    bone_filter: List[str] | None = None,
) -> None:
    if not arm.animation_data:
        arm.animation_data_create()
    ad = arm.animation_data

    muted = [(t, t.mute) for t in ad.nla_tracks]
    for t, _ in muted:
        t.mute = True

    act_name = name if not bpy.data.actions.get(name) else f"{name}_{len(bpy.data.actions)}"
    act = bpy.data.actions.new(act_name)
    ad.action = act

    allowed = set(bone_filter) if bone_filter else None
    for frame, pose in keyed_poses:
        for bone_name, quat in pose.items():
            if allowed is not None and bone_name not in allowed:
                continue
            bone = arm.pose.bones.get(bone_name)
            if not bone:
                continue
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = quat
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

    if act.fcurves:
        for fc in act.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

    ad.action = None
    for t, was_muted in muted:
        t.mute = was_muted

    track = ad.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, strip_start, act)
    strip.frame_start = strip_start
    strip.frame_end = strip_end + 1
    strip.action_frame_start = min(f for f, _ in keyed_poses)
    strip.action_frame_end = max(f for f, _ in keyed_poses)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.influence = 1.0
    strip.use_auto_blend = False


def _animate_talking(arm: bpy.types.Object) -> None:
    base = _capture_idle_base(arm)
    keys: List[Tuple[int, PoseDict]] = []
    for f in range(1, INTERVIEW_FRAMES + 1, 2):
        keys.append((f, _pose_with_deltas(base, _talk_deltas(f), 1.0)))
    # 終わりのフレームも確実に
    if keys[-1][0] != INTERVIEW_FRAMES:
        keys.append((INTERVIEW_FRAMES, _pose_with_deltas(base, _talk_deltas(INTERVIEW_FRAMES), 1.0)))
    _add_bone_pose_replace_strip(arm, "Leao_Talk", 1, INTERVIEW_FRAMES, keys, TALK_BONES)


def _animate_root_fixed(
    root: bpy.types.Object,
    keys: List[Tuple[int, Vector]],
    yaw: float,
) -> None:
    _clear_anim(root)
    for f, loc in keys:
        # 話しているときの微かな体重移動
        sway = 0.015 * math.sin(f * 0.18)
        p = loc.copy()
        p.x += sway
        _kf_loc(root, f, p)
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
    leao = build_team(
        "Leao",
        PORTUGAL_RED,
        [LEAO_POS],
        actions=["idle"],
        facing_yaw=LEAO_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(leao), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    return leao, _root_of(leao)


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    direction = target - pos
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_camera() -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamLeaoInterview")
    cam = bpy.data.objects.new("CamLeaoInterview", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_data.lens = 35

    # 正面寄りミディアム（頭〜お立ち台が見える）
    for f in (1, 36, 64, INTERVIEW_FRAMES):
        t = (f - 1) / max(1, INTERVIEW_FRAMES - 1)
        pos = Vector((-0.7 + 0.15 * t, -8.4 + 0.4 * t, 3.45))
        tgt = Vector((0.05 * math.sin(t * math.pi), 0.1, 3.15 + 0.1 * t))
        _kf_cam(cam, f, pos, tgt)
    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def _setup_soft_studio_world() -> None:
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("InterviewWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.06, 0.07, 0.1, 1.0)
        bg.inputs["Strength"].default_value = 0.85


def animate_leao_interview() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = INTERVIEW_FRAMES
    scene.render.fps = FPS

    _hide_pitch_for_studio()
    _hide_ball()
    setup_interview_set()
    _setup_soft_studio_world()

    leao_arm, leao_root = setup_character()
    _clear_all_nla(leao_arm)

    keys = [(f, LEAO_POS) for f in range(1, INTERVIEW_FRAMES + 1, 3)]
    if keys[-1][0] != INTERVIEW_FRAMES:
        keys.append((INTERVIEW_FRAMES, LEAO_POS))
    _animate_root_fixed(leao_root, keys, LEAO_YAW)

    _add_nla_loop(leao_arm, "idle", 1, INTERVIEW_FRAMES)
    _animate_talking(leao_arm)
    setup_camera()
    scene.frame_set(1)
    print(f"Leao interview: {INTERVIEW_FRAMES}f @ {FPS}fps — solo talk on podium (~4s)")


def render_leao_interview_video() -> Path:
    from build_part_field import RENDER_DIR, setup_lights  # noqa: E402

    _setup_soft_studio_world()
    setup_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = INTERVIEW_FRAMES
    scene.eevee.taa_render_samples = 8
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    out = RENDER_DIR / "leao_interview.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    print(f"Rendering Leao interview: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    if "--render" in sys.argv or "--render-leao-interview-video" in sys.argv:
        render_leao_interview_video()
    else:
        animate_leao_interview()
