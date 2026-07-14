# SPDX-License-Identifier: MIT
"""37カット制作の共有ユーティリティ。

注意点のガード:
- カメラは LINEAR 補間のみ（Bezier の変なフレームを防ぐ）
- 人体は SIDE_GAP 以上離す
- ボールは足の最前点＋クリアランス、または明示オフセットで人体と重ねない
- 腕は穏やかな delta のみ（極端な twist 禁止）
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import bpy
from mathutils import Euler, Quaternion, Vector

from animate_soccer_match import (  # noqa: E402
    BALL_GROUND_Z,
    PITCH_HALF,
    _add_nla_strip,
    _clear_all_nla,
    _clear_anim,
    _ease_all_ball_keyframes,
    _kf_loc,
    _kf_rot_z,
    _root_of,
)

FPS = 24
_SCALE = 2.5
GOAL_INNER_HALF_W = 7.32 * _SCALE / 2
GOAL_H = 2.44 * _SCALE
SIDE_GAP = 3.5
BALL_FEET_CLEAR = 0.9
BALL_AHEAD_MIN = 1.6

# --- kits ---
SHAOLIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
SHAOLIN_WHITE = (0.96, 0.96, 0.98, 1.0)
NORWAY_RED = (0.85, 0.08, 0.1, 1.0)
NORWAY_WHITE = (0.96, 0.96, 0.98, 1.0)
SPAIN_YELLOW = (0.95, 0.78, 0.08, 1.0)
SPAIN_RED = (0.85, 0.08, 0.1, 1.0)
FRANCE_BLUE = (0.1, 0.22, 0.72, 1.0)
FRANCE_WHITE = (0.96, 0.96, 0.98, 1.0)
FRANCE_RED = (0.85, 0.1, 0.12, 1.0)
ARG_LIGHT = (0.55, 0.78, 0.92, 1.0)
ARG_WHITE = (0.96, 0.96, 0.98, 1.0)
REF_BLACK = (0.05, 0.05, 0.05, 1.0)
FEMALE_GK_PINK = (0.92, 0.55, 0.65, 1.0)
FEMALE_GK_WHITE = (0.96, 0.96, 0.98, 1.0)

RENDER_DIR = Path("/workspace/blender/renders/cuts")
BLEND_DIR = Path("/home/ubuntu/Desktop/cuts")
ART_DIR = Path("/opt/cursor/artifacts/cuts")
AGENT_BC = "bc-019f3a70-7989-73fa-8e27-b3c7cccb9fa6"


def artifact_url(filename: str) -> str:
    enc = filename.replace("/", "%2F")
    return (
        f"https://cursor.com/agents/{AGENT_BC}/artifacts"
        f"?path=%2Fopt%2Fcursor%2Fartifacts%2Fcuts%2F{enc}"
    )


PLAYER_PREFIXES = (
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
    "Netherlands_",
    "Norway_",
    "Spain_",
    "France_",
    "Argentina_",
    "Referee_",
    "Crowd_",
    "Interview_",
    "Dojo_",
    "FemaleGK_",
    "Card_",
)


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def right_of(d: Vector) -> Vector:
    r = Vector((d.y, -d.x, 0.0))
    return r.normalized() if r.length > 1e-6 else Vector((1.0, 0.0, 0.0))


def remove_players() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PLAYER_PREFIXES):
            bpy.data.objects.remove(obj, do_unlink=True)


def remove_cameras() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)


def force_linear(obj: bpy.types.Object) -> None:
    """カメラ／ルートの変な Bezier フレームを阻止。"""
    if not obj.animation_data or not obj.animation_data.action:
        return
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
            kp.handle_left_type = "FREE"
            kp.handle_right_type = "FREE"


def kf_cam(cam: bpy.types.Object, frame: int, pos: Vector, target: Vector) -> None:
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def animate_root(
    root: bpy.types.Object, keys: Sequence[Tuple[int, Vector]], yaw: float
) -> None:
    _clear_anim(root)
    for f, loc in keys:
        _kf_loc(root, f, loc)
        _kf_rot_z(root, f, yaw)
    force_linear(root)


_ACTION_ALIASES = {
    "jump_full": "air_jump",
}


def resolve_action(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    cands = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if cands:
        exact = [c for c in cands if c == name]
        return exact[0] if exact else sorted(cands)[0]
    alias = _ACTION_ALIASES.get(name)
    if alias and alias != name:
        return resolve_action(alias)
    raise KeyError(name)


def add_nla_loop(arm: bpy.types.Object, action: str, f0: int, f1: int) -> None:
    resolved = resolve_action(action)
    act = bpy.data.actions.get(resolved)
    if not act:
        raise KeyError(resolved)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = f"{resolved}_loop"
    strip = track.strips.new(act.name, f0, act)
    strip.frame_start = f0
    strip.frame_end = f1 + 1
    alen = max(1.0, act.frame_range[1] - act.frame_range[0])
    strip.repeat = max(1.0, (f1 - f0 + 1) / alen)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.use_auto_blend = False
    strip.influence = 1.0


def add_nla_once(arm: bpy.types.Object, action: str, f0: int, f1: int) -> None:
    resolved = resolve_action(action)
    act = bpy.data.actions.get(resolved)
    if not act:
        raise KeyError(resolved)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = f"{resolved}_once"
    strip = track.strips.new(act.name, f0, act)
    a0, a1 = int(act.frame_range[0]), int(act.frame_range[1])
    alen = max(1, a1 - a0)
    dur = max(1, f1 - f0)
    strip.action_frame_start = a0
    strip.action_frame_end = a1
    strip.frame_start = f0
    strip.scale = dur / float(alen)
    strip.repeat = 1.0
    strip.frame_end = f0 + alen * strip.scale
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.use_auto_blend = False
    strip.influence = 1.0


def add_nla_hold(arm: bpy.types.Object, action: str, f0: int, f1: int, af: int = 10) -> None:
    resolved = resolve_action(action)
    act = bpy.data.actions.get(resolved)
    if not act:
        raise KeyError(resolved)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = f"{resolved}_hold"
    strip = track.strips.new(act.name, f0, act)
    dur = max(1, f1 - f0 + 1)
    strip.action_frame_start = float(af)
    strip.action_frame_end = float(af + 1)
    strip.repeat = 1.0
    strip.scale = float(dur)
    strip.frame_start = float(f0)
    strip.frame_end = float(f0 + dur)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.use_auto_blend = False
    strip.influence = 1.0


def clear_ball_anim() -> bpy.types.Object:
    ball = bpy.data.objects.get("Ball")
    if not ball:
        raise RuntimeError("Ball missing")
    _clear_anim(ball)
    ball.hide_render = False
    ball.hide_viewport = False
    return ball


def hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if ball:
        ball.hide_render = True
        ball.hide_viewport = True


def key_ball(ball: bpy.types.Object, frames: Iterable[int], path_fn) -> None:
    for f in frames:
        _kf_loc(ball, f, path_fn(f))
    _ease_all_ball_keyframes(ball)
    # ball Bezier is ok for arcs, but clamp handles
    if ball.animation_data and ball.animation_data.action:
        for fc in ball.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def ball_ahead_of(
    player: Vector,
    move_dir: Vector,
    frame: int,
    arm: bpy.types.Object | None = None,
    z: float | None = None,
) -> Vector:
    """体・足より前。人体と重ねない。"""
    fd = move_dir.normalized()
    phase = frame * 0.55
    ahead = BALL_AHEAD_MIN + 0.08 * math.sin(phase * 2.1)
    side = 0.06 * math.sin(phase * 3.0)
    if arm is not None and arm.pose is not None:
        bl = arm.pose.bones.get("ball.l") or arm.pose.bones.get("foot.l")
        br = arm.pose.bones.get("ball.r") or arm.pose.bones.get("foot.r")
        if bl and br:
            fl = arm.matrix_world @ bl.head
            fr = arm.matrix_world @ br.head
            foot_ahead = max((fl - player).dot(fd), (fr - player).dot(fd))
            ahead = max(ahead, foot_ahead + BALL_FEET_CLEAR)
    p = player + fd * ahead + right_of(fd) * side
    p.z = BALL_GROUND_Z if z is None else z
    return p


def spawn_player(
    prefix: str,
    color,
    pos: Vector,
    yaw: float,
    actions: List[str] | None = None,
    split: Tuple | None = None,
    scale: float | None = None,
) -> Tuple[bpy.types.Object, bpy.types.Object]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    arm = build_team(
        prefix,
        color,
        [pos],
        actions=actions or ["idle"],
        facing_yaw=yaw,
    )[0]
    root = _root_of(arm)
    if scale is not None:
        root.scale = Vector((scale, scale, scale))
    if split is not None:
        set_mesh_split_vertical(_mesh_child(arm), split[0], split[1], z_cut=split[2] if len(split) > 2 else 0.42)
    return arm, root


def mat_rgba(name: str, rgba, rough: float = 0.7) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = rough
    return mat


def add_box(
    name: str,
    size: Tuple[float, float, float],
    loc: Vector,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    mesh = bpy.data.meshes.new(name)
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
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.scale = Vector(size)
    obj.data.materials.append(mat)
    return obj


def setup_new_cam(name: str, lens: float = 32) -> bpy.types.Object:
    remove_cameras()
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    data.lens = lens
    return cam


def finish_cam(cam: bpy.types.Object) -> None:
    force_linear(cam)
    if cam.data.animation_data and cam.data.animation_data.action:
        for fc in cam.data.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def set_frame_range(end: int) -> None:
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = end
    sc.render.fps = FPS
    sc.frame_set(1)


def render_cut_video(slug: str, frames: int) -> Path:
    from build_part_field import setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = 640
    sc.render.resolution_y = 360
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = frames
    sc.eevee.taa_render_samples = 4
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "HIGH"
    sc.render.ffmpeg.ffmpeg_preset = "REALTIME"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    out = RENDER_DIR / f"{slug}.mp4"
    sc.render.filepath = str(out)
    print(f"Rendering {slug}: {out} ({frames}f)")
    bpy.ops.render.render(animation=True)
    art = ART_DIR / f"{slug}.mp4"
    art.write_bytes(out.read_bytes())
    print(f"Artifact: {art}")
    return art


def save_cut_blend(slug: str) -> Path:
    BLEND_DIR.mkdir(parents=True, exist_ok=True)
    path = BLEND_DIR / f"{slug}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    # also copy under artifacts
    ART_DIR.mkdir(parents=True, exist_ok=True)
    art = ART_DIR / f"{slug}.blend"
    art.write_bytes(path.read_bytes())
    print(f"Saved blend: {path}")
    return path


def still_qc(slug: str, frame: int, tag: str) -> Path:
    sc = bpy.context.scene
    sc.frame_set(frame)
    sc.render.image_settings.file_format = "PNG"
    sc.render.resolution_x = 640
    sc.render.resolution_y = 360
    if hasattr(sc, "eevee"):
        sc.eevee.taa_render_samples = 4
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    out = RENDER_DIR / f"{slug}_{tag}.png"
    sc.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    art = ART_DIR / f"{slug}_{tag}.png"
    art.write_bytes(out.read_bytes())
    return art


# ---------- talking / sad pose helpers (gentle arms — idle only) ----------
PoseDict = Dict[str, Quaternion]


def snapshot_pose(arm: bpy.types.Object) -> PoseDict:
    out: PoseDict = {}
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
        out[bone.name] = bone.rotation_quaternion.copy()
    return out


def pose_with_deltas(base: PoseDict, deltas: Dict[str, Tuple[float, float, float]]) -> PoseDict:
    out = {k: v.copy() for k, v in base.items()}
    for name, xyz in deltas.items():
        if name not in out:
            continue
        dx, dy, dz = xyz
        # clamp to avoid weird arms/necks
        dx = max(-0.55, min(0.55, dx))
        dy = max(-0.45, min(0.45, dy))
        dz = max(-0.45, min(0.45, dz))
        out[name] = out[name] @ Euler((dx, dy, dz), "XYZ").to_quaternion()
    return out


def capture_idle_base(arm: bpy.types.Object) -> PoseDict:
    idle = bpy.data.actions.get(resolve_action("idle"))
    ad = arm.animation_data or arm.animation_data_create()
    prev = ad.action
    if idle:
        ad.action = idle
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        base = snapshot_pose(arm)
        ad.action = prev
        return base
    return snapshot_pose(arm)


def add_talk_strip(
    arm: bpy.types.Object,
    name: str,
    frames: int,
    deltas_fn,
    bones: List[str],
    step: int = 3,
) -> None:
    base = capture_idle_base(arm)
    keys = []
    for f in range(1, frames + 1, step):
        keys.append((f, pose_with_deltas(base, deltas_fn(f))))
    if keys[-1][0] != frames:
        keys.append((frames, pose_with_deltas(base, deltas_fn(frames))))

    if not arm.animation_data:
        arm.animation_data_create()
    ad = arm.animation_data
    muted = [(t, t.mute) for t in ad.nla_tracks]
    for t, _ in muted:
        t.mute = True
    act_name = name if not bpy.data.actions.get(name) else f"{name}_{len(bpy.data.actions)}"
    act = bpy.data.actions.new(act_name)
    ad.action = act
    allowed = set(bones)
    for frame, pose in keys:
        for bn, quat in pose.items():
            if bn not in allowed:
                continue
            bone = arm.pose.bones.get(bn)
            if not bone:
                continue
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = quat
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
    ad.action = None
    for t, was in muted:
        t.mute = was
    track = ad.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, act)
    strip.frame_start = 1
    strip.frame_end = frames + 1
    strip.action_frame_start = 1
    strip.action_frame_end = frames
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD_FORWARD"
    strip.influence = 1.0
    strip.use_auto_blend = False


TALK_BONES = ["spine_01", "spine_02", "neck_01", "head"]


def yaw_face_neg_x() -> float:
    return math.pi * 1.5


def yaw_face_pos_x() -> float:
    return math.pi * 0.5


def yaw_face_neg_y() -> float:
    return 0.0


def goal_l_x() -> float:
    return -PITCH_HALF


def goal_r_x() -> float:
    return PITCH_HALF
