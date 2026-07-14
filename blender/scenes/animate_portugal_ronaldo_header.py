# SPDX-License-Identifier: MIT
"""ポルトガル戦 — ロナウド単独ヘディング（スローモーション）

握手シーンとは別尺。ロナウド一人＋ボールのみ。
接触フレームでは頭ボーンから額位置を測り、ボール中心をぴったり合わせる。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

from animate_soccer_match import (
    _add_nla_strip as _add_nla_strip_raw,
    _clear_all_nla,
    _clear_anim,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24
# スロー再生：〜15秒で溜め→ジャンプ→接触余韻→着地
HEADER_FRAMES = 360

F_PREP = 36
F_WINDUP = 96
F_TAKEOFF = 132
F_CONTACT = 210
F_IMPACT_HOLD = 228
F_FOLLOW = 270
F_LAND = 318

RONALDO_HEADER_HEIGHT = 2.05
RONALDO_YAW = math.pi / 2  # +X 向き（横顔）
RONALDO_POS = Vector((0.0, 0.0, 0.0))

PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

# ボール接近：正面寄り（額に当てる）
BALL_APPROACH = Vector((0.98, 0.0, 0.2)).normalized()
BALL_START_OFFSET = Vector((7.0, 0.15, 2.0))  # contact から見た相対（開始）
BALL_END_OFFSET = Vector((-5.5, -0.6, 2.0))  # 跳ね返り後
# 実ボール半径はオブジェクトから測る（定数はフォールバック）
BALL_RADIUS_FALLBACK = 0.55
# 見た目の食い込み（きっちり当たって見えるように寄せる）
BALL_CONTACT_NEST = 0.72

RONALDO_HEADER_WINDUP = {
    "spine_02": (0.28, 0.0, 0.0),
    "neck_01": (-0.12, 0.0, 0.0),
    "head": (-0.05, 0.0, 0.0),
    "upperarm.r": (0.2, -0.95, 0.4),
    "lowerarm.r": (-0.75, 0.1, 0.0),
    "upperarm.l": (0.2, 0.95, -0.4),
    "lowerarm.l": (-0.75, -0.1, 0.0),
}
# 接触：額を前方のボールへ振り出す
RONALDO_HEADER_CONTACT = {
    "spine_02": (-0.35, 0.0, 0.0),
    "neck_01": (-0.4, 0.0, 0.0),
    "head": (-0.25, 0.0, 0.0),
    "upperarm.r": (-0.2, -1.1, 0.5),
    "lowerarm.r": (-0.9, 0.2, 0.1),
    "upperarm.l": (-0.2, 1.1, -0.5),
    "lowerarm.l": (-0.9, -0.2, -0.1),
}
RONALDO_HEADER_FOLLOW = {
    "spine_02": (-0.4, 0.0, 0.0),
    "neck_01": (-0.45, 0.0, 0.0),
    "head": (-0.25, 0.0, 0.0),
    "upperarm.r": (0.1, -0.75, 0.3),
    "lowerarm.r": (-0.55, 0.0, 0.0),
    "upperarm.l": (0.1, 0.75, -0.3),
    "lowerarm.l": (-0.55, 0.0, 0.0),
}

RONALDO_HEADER_BONES = [
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "hand.r",
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "hand.l",
    "spine_02",
    "neck_01",
    "head",
]

PoseDict = Dict[str, Quaternion]


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    exact = [c for c in candidates if c == name]
    return exact[0] if exact else sorted(candidates)[0]


def _add_nla_strip(
    arm: bpy.types.Object,
    action_name: str,
    frame_start: int,
    frame_end: int,
    action_offset: int = 0,
    repeat: bool = True,
) -> None:
    resolved = _resolve_action_name(action_name)
    _add_nla_strip_raw(arm, resolved, frame_start, frame_end, action_offset=action_offset, repeat=repeat)
    ad = arm.animation_data
    if not ad:
        return
    track = ad.nla_tracks[-1]
    for strip in track.strips:
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
            )
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _ronaldo_path(frame: int) -> Vector:
    p = RONALDO_POS.copy()
    if frame < F_PREP:
        return p
    if frame < F_WINDUP:
        t = (frame - F_PREP) / max(1, F_WINDUP - F_PREP)
        p.z = 0.06 * t
        return p
    if frame < F_TAKEOFF:
        t = (frame - F_WINDUP) / max(1, F_TAKEOFF - F_WINDUP)
        p.z = 0.06 - 0.28 * _ease_in_out(t)
        return p
    if frame <= F_CONTACT:
        t = (frame - F_TAKEOFF) / max(1, F_CONTACT - F_TAKEOFF)
        ease = math.sin(_ease_in_out(t) * math.pi * 0.5)
        p.z = -0.18 + (RONALDO_HEADER_HEIGHT + 0.18) * ease
        p.x += 0.4 * _ease_in_out(t)
        return p
    if frame <= F_LAND:
        t = (frame - F_CONTACT) / max(1, F_LAND - F_CONTACT)
        p.z = RONALDO_HEADER_HEIGHT * max(0.0, math.cos(_ease_in_out(t) * math.pi * 0.5))
        p.x += 0.4 + 0.35 * _ease_in_out(t)
        return p
    p.x += 0.75
    return p


def _snapshot_pose(arm: bpy.types.Object) -> PoseDict:
    pose: PoseDict = {}
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
        pose[bone.name] = bone.rotation_quaternion.copy()
    return pose


def _pose_with_deltas(
    base: PoseDict, deltas: Dict[str, Tuple[float, float, float]], weight: float = 1.0
) -> PoseDict:
    out: PoseDict = {name: q.copy() for name, q in base.items()}
    w = max(0.0, min(1.0, weight))
    for bone_name, euler_xyz in deltas.items():
        if bone_name not in out:
            continue
        delta = Euler(euler_xyz, "XYZ").to_quaternion()
        if w >= 0.999:
            out[bone_name] = out[bone_name] @ delta
        else:
            out[bone_name] = out[bone_name] @ Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(delta, w)
    return out


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

    act_name = name
    if bpy.data.actions.get(act_name):
        act_name = f"{name}_{len(bpy.data.actions)}"
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


def _animate_root_fixed(root: bpy.types.Object, keys: List[Tuple[int, Vector]], yaw: float) -> None:
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


def _header_contact_on_mesh(arm: bpy.types.Object, mesh: bpy.types.Object | None = None) -> Vector:
    """頭メッシュ上で「高＋正面」の点＝額付近を取る。"""
    head = arm.pose.bones.get("head")
    if not head:
        return arm.matrix_world.translation + Vector((0.0, 0.0, 4.5))
    hloc = (arm.matrix_world @ head.matrix).to_translation()
    if mesh is None:
        from import_mannequiny import _mesh_child  # noqa: E402

        mesh = _mesh_child(arm)
    if not mesh:
        # フォールバック：骨の前方やや上
        return hloc + Vector((0.35, 0.0, 0.32))

    deps = bpy.context.evaluated_depsgraph_get()
    me = mesh.evaluated_get(deps).to_mesh()
    mm = mesh.matrix_world
    best = hloc + Vector((0.4, 0.0, 0.22))
    best_score = -1e9
    for v in me.vertices:
        w = mm @ v.co
        # 頭ボーン近傍だけ（胸などへ逃げない）
        if (w - hloc).length > 0.55:
            continue
        if w.z < hloc.z - 0.08:
            continue
        # 額＝顔正面やや上
        score = (w.z - hloc.z) * 0.9 + (w.x - hloc.x) * 1.25
        if score > best_score:
            best_score = score
            best = w.copy()
    mesh.to_mesh_clear()
    # 額やや上へ微調整（顔の中心ではなく額へ）
    return best + Vector((0.05, 0.0, 0.12))


def _ball_radius_world(ball: bpy.types.Object | None) -> float:
    if not ball:
        return BALL_RADIUS_FALLBACK
    deps = bpy.context.evaluated_depsgraph_get()
    me = ball.evaluated_get(deps).to_mesh()
    mm = ball.matrix_world
    center = mm.translation
    radii = [(mm @ v.co - center).length for v in me.vertices]
    ball.to_mesh_clear()
    if not radii:
        # dimensions は評価前でもだいたい合う
        return max(ball.dimensions) * 0.5
    return sum(radii) / len(radii)


def _ball_center_on_forehead(
    forehead: Vector, approach: Vector, radius: float | None = None
) -> Vector:
    """額面からボール半径ぶん手前（接近側）に中心を置く。"""
    r = BALL_RADIUS_FALLBACK if radius is None else radius
    return forehead + approach.normalized() * (r * BALL_CONTACT_NEST)

def _eval_forehead_at(arm: bpy.types.Object, frame: int) -> Vector:
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return _header_contact_on_mesh(arm)


def _animate_ronaldo_header_pose(ronaldo_arm: bpy.types.Object) -> None:
    ad = ronaldo_arm.animation_data
    if not ad:
        ronaldo_arm.animation_data_create()
        ad = ronaldo_arm.animation_data

    muted = [(t, t.mute) for t in ad.nla_tracks]
    for t, _ in muted:
        t.mute = True

    idle = bpy.data.actions.get(_resolve_action_name("idle"))
    prev = ad.action
    ad.action = idle
    bpy.context.scene.frame_set(10)
    bpy.context.view_layer.update()
    idle_base = _snapshot_pose(ronaldo_arm)
    ad.action = prev
    for t, was_muted in muted:
        t.mute = was_muted

    wind = _pose_with_deltas(idle_base, RONALDO_HEADER_WINDUP, 1.0)
    hit = _pose_with_deltas(idle_base, RONALDO_HEADER_CONTACT, 1.0)
    follow = _pose_with_deltas(idle_base, RONALDO_HEADER_FOLLOW, 1.0)

    keys = [
        (1, idle_base),
        (F_PREP, idle_base),
        (F_WINDUP, wind),
        (F_TAKEOFF, wind),
        (F_CONTACT - 24, _pose_with_deltas(idle_base, RONALDO_HEADER_CONTACT, 0.35)),
        (F_CONTACT - 6, _pose_with_deltas(idle_base, RONALDO_HEADER_CONTACT, 0.85)),
        (F_CONTACT, hit),
        (F_IMPACT_HOLD, hit),
        (F_FOLLOW, follow),
        (F_LAND, follow),
        (HEADER_FRAMES, follow),
    ]
    _add_bone_pose_replace_strip(
        ronaldo_arm,
        "Ronaldo_SoloHeader",
        1,
        HEADER_FRAMES,
        keys,
        RONALDO_HEADER_BONES,
    )


def _animate_ball_locked_to_head(ball: bpy.types.Object, arm: bpy.types.Object) -> None:
    """接近 → 接触／余韻は額にロック → 跳ね返り。"""
    _clear_anim(ball)
    ball.hide_render = False
    ball.hide_viewport = False

    radius = _ball_radius_world(ball)
    contact_forehead = _eval_forehead_at(arm, F_CONTACT)
    contact_ball = _ball_center_on_forehead(contact_forehead, BALL_APPROACH, radius)
    start = contact_ball + BALL_START_OFFSET
    end = contact_ball + BALL_END_OFFSET

    # 接触前後は毎フレーム額を測ってロック／着弾を滑らかに
    forehead_keys: Dict[int, Vector] = {}
    sample_frames = list(range(F_TAKEOFF, F_IMPACT_HOLD + 1))
    for f in sample_frames:
        forehead_keys[f] = _eval_forehead_at(arm, f)

    for f in range(1, HEADER_FRAMES + 1):
        if f < F_WINDUP:
            t = (f - 1) / max(1, F_WINDUP - 1)
            loc = start.lerp(start.lerp(contact_ball, 0.15), _ease_in_out(t))
        elif f < F_CONTACT:
            t = (f - F_WINDUP) / max(1, F_CONTACT - F_WINDUP)
            t = _ease_in_out(t)
            if f >= F_TAKEOFF and forehead_keys:
                nearest = min(forehead_keys.keys(), key=lambda k: abs(k - f))
                target = _ball_center_on_forehead(forehead_keys[nearest], BALL_APPROACH, radius)
                target = target.lerp(
                    contact_ball, max(0.0, (f - F_TAKEOFF) / max(1, F_CONTACT - F_TAKEOFF))
                )
                loc = start.lerp(target, t)
            else:
                loc = start.lerp(contact_ball, t)
        elif f <= F_IMPACT_HOLD:
            fh = forehead_keys.get(f) or _eval_forehead_at(arm, f)
            loc = _ball_center_on_forehead(fh, BALL_APPROACH, radius)
        else:
            t = (f - F_IMPACT_HOLD) / max(1, HEADER_FRAMES - F_IMPACT_HOLD)
            t = 1.0 - (1.0 - min(1.0, t)) ** 2
            loc = contact_ball.lerp(end, t)
            loc.z += 1.1 * math.sin(min(1.0, t * 1.2) * math.pi)
        _kf_loc(ball, f, loc)

    if ball.animation_data and ball.animation_data.action:
        for fc in ball.animation_data.action.fcurves:
            if not fc.data_path.startswith("location"):
                continue
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def setup_portugal_header_character() -> Tuple[bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()
    ronaldo_arm = build_team(
        "Ronaldo",
        PORTUGAL_RED,
        [RONALDO_POS],
        actions=["idle"],
        facing_yaw=RONALDO_YAW,
    )[0]
    set_mesh_split_vertical(_mesh_child(ronaldo_arm), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    return ronaldo_arm, _root_of(ronaldo_arm)


def _remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def _kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def setup_portugal_header_camera(arm: bpy.types.Object) -> bpy.types.Object:
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamPortugalHeader")
    cam = bpy.data.objects.new("CamPortugalHeader", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 32

    for f in (1, F_PREP, F_WINDUP, F_TAKEOFF, F_CONTACT, F_IMPACT_HOLD, F_FOLLOW, F_LAND, HEADER_FRAMES):
        loc = _ronaldo_path(f)
        brow = _eval_forehead_at(arm, f)
        # 横顔：額とボールの接触がはっきり見える
        tgt = Vector((loc.x + 0.15, loc.y, brow.z * 0.72 + loc.z * 0.15 + 1.2))
        pos = Vector((loc.x + 1.2, loc.y - 8.2, 3.2 + max(0.0, loc.z) * 0.45))
        cam.data.lens = 32
        cam.data.keyframe_insert(data_path="lens", frame=f)
        _kf_cam(cam, f, pos, tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def animate_portugal_ronaldo_header() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = HEADER_FRAMES
    scene.render.fps = FPS

    ronaldo_arm, ronaldo_root = setup_portugal_header_character()
    _clear_all_nla(ronaldo_arm)

    ball = bpy.data.objects.get("Ball")
    if ball and ball.animation_data:
        ball.animation_data_clear()

    keys = [(f, _ronaldo_path(f)) for f in range(1, HEADER_FRAMES + 1)]
    _animate_root_fixed(ronaldo_root, keys, RONALDO_YAW)

    _add_nla_strip(ronaldo_arm, "idle", 1, F_TAKEOFF - 1)
    try:
        _add_nla_strip(ronaldo_arm, "air_jump", F_TAKEOFF, F_LAND)
    except KeyError:
        _add_nla_strip(ronaldo_arm, "idle", F_TAKEOFF, F_LAND)
    _add_nla_strip(ronaldo_arm, "idle", F_LAND + 1, HEADER_FRAMES)

    _animate_ronaldo_header_pose(ronaldo_arm)

    if ball:
        _animate_ball_locked_to_head(ball, ronaldo_arm)
    else:
        print("WARN: Ball not found")

    setup_portugal_header_camera(ronaldo_arm)
    scene.frame_set(1)

    # 接触精度ログ
    fh = _eval_forehead_at(ronaldo_arm, F_CONTACT)
    if ball:
        radius = _ball_radius_world(ball)
        bpy.context.scene.frame_set(F_CONTACT)
        bpy.context.view_layer.update()
        ideal = _ball_center_on_forehead(fh, BALL_APPROACH, radius)
        dist = (ball.location - ideal).length
        # メッシュ面までの隙間（ボール半径差し引き）
        from import_mannequiny import _mesh_child  # noqa: E402

        mesh = _mesh_child(ronaldo_arm)
        deps = bpy.context.evaluated_depsgraph_get()
        me = mesh.evaluated_get(deps).to_mesh()
        mm = mesh.matrix_world
        mind = min((mm @ v.co - ball.location).length for v in me.vertices)
        mesh.to_mesh_clear()
        gap = mind - radius
        print(
            f"Portugal solo header: {HEADER_FRAMES}f @ {FPS}fps slow-mo — "
            f"r={radius:.3f} ball_err={dist:.3f}m surface_gap={gap:.3f}m"
        )
    else:
        print(f"Portugal solo header: {HEADER_FRAMES}f @ {FPS}fps slow-mo")


def render_portugal_header_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = HEADER_FRAMES
    scene.eevee.taa_render_samples = 8

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "portugal_ronaldo_header.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering portugal solo header video: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-portugal-header-video" in sys.argv:
        render_portugal_header_video()
    else:
        animate_portugal_ronaldo_header()
        from news_cg_common import save_blend

        save_blend(blend)
