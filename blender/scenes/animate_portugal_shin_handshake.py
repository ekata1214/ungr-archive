# SPDX-License-Identifier: MIT
"""ポルトガル戦 — シンがレオンに握手を求める（手前ロナウド idle、奥で握手）

流れ:
  シン: idle → 楽しそうに走っていく → 到着ホップ → 右手を差し出す
  レオン: idle のまま待つ → 左手で握手に応じる
  ロナウド: 手前で気づく → 握手を見てキレて飛び跳ねる
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

# 尺は長め — 各アクションが全部見えるまで余裕を持たせる（約18秒）
HANDSHAKE_FRAMES = 432

# タイムライン
F_INTRO = 1
F_RUN_START = 48
F_RUN_END = 216
F_ARRIVE_HOLD = 252
F_HAND_OFFER = 288
F_OFFER_HOLD = 330
F_LEAO_REPLY = 360
F_HANDSHAKE_HOLD = 432

# ロナウド — 握手を見てキレて飛び跳ねる
F_RONALDO_NOTICE = F_ARRIVE_HOLD      # 「ぉぉ？」と気づく
F_RONALDO_TANTRUM = F_HAND_OFFER - 6  # 握手要求で本格的にキレる
RONALDO_HOP_PERIOD = 12
RONALDO_HOP_HEIGHT = 0.95

SHIN_ORANGE = (0.95, 0.42, 0.06, 1.0)
PORTUGAL_RED = (0.88, 0.12, 0.12, 1.0)
PORTUGAL_GREEN = (0.12, 0.55, 0.28, 1.0)

# 左右に対面（カメラから両方見える）。シンは +X から走ってくる。
SHIN_YAW = math.pi * 1.5  # -X 向き（レオンへ）
LEAO_YAW = math.pi / 2    # +X 向き（シンへ）
# 手前ロナウド — 奥の2人の方を向く
RONALDO_YAW = math.pi

# 奥：シン＋レオン / 手前：ロナウド
# ルート間隔 ~2.7（胴体クリアしつつ手が自然に重なる）
LEAO_POS = Vector((1.85, 5.0, 0.0))
SHIN_START = Vector((18.0, 5.0, 0.0))
SHIN_END = Vector((4.55, 5.0, 0.0))
RONALDO_POS = Vector((1.0, -5.5, 0.0))


def _finger_handshake_deltas(side: str) -> Dict[str, Tuple[float, float, float]]:
    """握手：掌を開きつつ、指先は軽く相手の手に巻きつける。"""
    s = side
    d: Dict[str, Tuple[float, float, float]] = {}
    for finger in ("index", "middle", "ring"):
        # 付け根はやや開く、中〜先は握る
        d[f"{finger}_01.{s}"] = (-0.25, 0.0, 0.0)
        d[f"{finger}_02.{s}"] = (0.45, 0.0, 0.0)
        d[f"{finger}_03.{s}"] = (0.5, 0.0, 0.0)
    if s == "r":
        d["thumb_01.r"] = (0.15, 0.6, 0.4)
        d["thumb_02.r"] = (0.35, 0.1, 0.0)
        d["thumb_03.r"] = (0.25, 0.0, 0.0)
    else:
        d["thumb_01.l"] = (0.15, -0.6, -0.4)
        d["thumb_02.l"] = (0.35, -0.1, 0.0)
        d["thumb_03.l"] = (0.25, 0.0, 0.0)
    return d


# idle 上に掛ける腕＋手のオイラー差分。シン右手・レオン左手。
SHIN_OFFER_DELTA = {
    "upperarm.r": (0.95, 0.5, 1.2),
    "lowerarm.r": (-0.95, 0.15, 0.1),
    "hand.r": (0.2, 0.3, -1.0),
    "spine_02": (0.08, 0.0, 0.04),
    "neck_01": (0.04, 0.0, -0.05),
    **_finger_handshake_deltas("r"),
}
LEAO_REPLY_DELTA = {
    "upperarm.l": (0.95, -0.5, -1.2),
    "lowerarm.l": (-0.95, -0.15, -0.1),
    "hand.l": (0.2, -0.3, 1.0),
    "spine_02": (0.08, 0.0, -0.04),
    "neck_01": (0.04, 0.0, 0.05),
    **_finger_handshake_deltas("l"),
}

# キレたロナウド — 両手を上げて怒りのジェスチャー
RONALDO_ANGRY_DELTA = {
    "upperarm.r": (-0.35, -1.35, 0.45),
    "lowerarm.r": (-1.15, 0.2, 0.15),
    "hand.r": (0.2, 0.0, -0.35),
    "upperarm.l": (-0.35, 1.35, -0.45),
    "lowerarm.l": (-1.15, -0.2, -0.15),
    "hand.l": (0.2, 0.0, 0.35),
    "spine_02": (-0.18, 0.0, 0.0),
    "neck_01": (0.25, 0.0, 0.0),
    "head": (0.2, 0.0, 0.08),
}

PoseDict = Dict[str, Quaternion]


def _resolve_action_name(name: str) -> str:
    if bpy.data.actions.get(name):
        return name
    candidates = [a.name for a in bpy.data.actions if a.name == name or a.name.startswith(f"{name}.")]
    if not candidates:
        raise KeyError(name)
    # 無印があれば優先、なければ最も若いサフィックス
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


def _shin_path(frame: int) -> Vector:
    """シン — 奥でレオンの方へ走る → 到着 → 喜びのホップ"""
    if frame < F_RUN_START:
        return SHIN_START.copy()
    if frame <= F_RUN_END:
        t = (frame - F_RUN_START) / max(1, F_RUN_END - F_RUN_START)
        t = t * t * (3.0 - 2.0 * t)
        return SHIN_START.lerp(SHIN_END, t)
    p = SHIN_END.copy()
    if F_RUN_END < frame <= F_ARRIVE_HOLD:
        hop = (frame - F_RUN_END) / (F_ARRIVE_HOLD - F_RUN_END)
        # 嬉しそうなジャンプ — 高め＋二連跳ね
        p.z = 0.55 * math.sin(hop * math.pi) + 0.18 * math.sin(hop * math.pi * 2.0)
    return p


def _ronaldo_path(frame: int) -> Vector:
    """ロナウド — 手前でキレて上下に飛び跳ねる（軽い左右も）"""
    p = RONALDO_POS.copy()
    if frame < F_RONALDO_TANTRUM:
        # 気づき始め — 小さな足踏み
        if frame >= F_RONALDO_NOTICE:
            t = frame - F_RONALDO_NOTICE
            p.z = 0.12 * abs(math.sin(t * 0.55))
            p.x += 0.06 * math.sin(t * 0.35)
        return p
    t = frame - F_RONALDO_TANTRUM
    phase = (t % RONALDO_HOP_PERIOD) / float(RONALDO_HOP_PERIOD)
    # キレたジャンプ — 鋭く跳び上がる
    p.z = RONALDO_HOP_HEIGHT * (math.sin(phase * math.pi) ** 0.85)
    p.x += 0.22 * math.sin(t * 0.42)
    p.y += 0.08 * math.sin(t * 0.61)
    return p


def _snapshot_pose(arm: bpy.types.Object) -> PoseDict:
    pose: PoseDict = {}
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
        pose[bone.name] = bone.rotation_quaternion.copy()
    return pose


def _pose_with_deltas(base: PoseDict, deltas: Dict[str, Tuple[float, float, float]], weight: float = 1.0) -> PoseDict:
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


def _capture_evaluated_pose(arm: bpy.types.Object, frame: int) -> PoseDict:
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return _snapshot_pose(arm)


def _add_bone_pose_replace_strip(
    arm: bpy.types.Object,
    name: str,
    strip_start: int,
    strip_end: int,
    keyed_poses: List[Tuple[int, PoseDict]],
    bone_filter: List[str] | None = None,
) -> None:
    """指定ボーンのクォータニオンだけを REPLACE で重ねる（脚の idle は下のトラックが生きる）。"""
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


SHIN_HANDSHAKE_BONES = [
    "clavicle.r",
    "upperarm.r",
    "lowerarm.r",
    "hand.r",
    "thumb_01.r",
    "thumb_02.r",
    "thumb_03.r",
    "index_01.r",
    "index_02.r",
    "index_03.r",
    "middle_01.r",
    "middle_02.r",
    "middle_03.r",
    "ring_01.r",
    "ring_02.r",
    "ring_03.r",
    "spine_02",
    "neck_01",
    "head",
]
LEAO_HANDSHAKE_BONES = [
    "clavicle.l",
    "upperarm.l",
    "lowerarm.l",
    "hand.l",
    "thumb_01.l",
    "thumb_02.l",
    "thumb_03.l",
    "index_01.l",
    "index_02.l",
    "index_03.l",
    "middle_01.l",
    "middle_02.l",
    "middle_03.l",
    "ring_01.l",
    "ring_02.l",
    "ring_03.l",
    "spine_02",
    "neck_01",
    "head",
]

RONALDO_ANGRY_BONES = [
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


def _animate_handshake_poses(shin_arm: bpy.types.Object, leao_arm: bpy.types.Object) -> None:
    """到着後の idle を土台に、腕まわりだけ REPLACE で伸ばす。"""
    shin_base = _capture_evaluated_pose(shin_arm, F_ARRIVE_HOLD)
    leao_base = _capture_evaluated_pose(leao_arm, F_OFFER_HOLD)

    shin_keys = [
        (F_ARRIVE_HOLD, shin_base),
        (F_HAND_OFFER - 18, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 0.35)),
        (F_HAND_OFFER, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
        (F_OFFER_HOLD, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
        (HANDSHAKE_FRAMES, _pose_with_deltas(shin_base, SHIN_OFFER_DELTA, 1.0)),
    ]
    _add_bone_pose_replace_strip(
        shin_arm,
        "Shin_ExcitedHandshake",
        F_ARRIVE_HOLD,
        HANDSHAKE_FRAMES,
        shin_keys,
        SHIN_HANDSHAKE_BONES,
    )

    leao_keys = [
        (F_LEAO_REPLY - 16, leao_base),
        (F_LEAO_REPLY - 4, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 0.45)),
        (F_LEAO_REPLY + 10, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 1.0)),
        (HANDSHAKE_FRAMES, _pose_with_deltas(leao_base, LEAO_REPLY_DELTA, 1.0)),
    ]
    _add_bone_pose_replace_strip(
        leao_arm,
        "Leao_HandshakeReply",
        F_LEAO_REPLY - 16,
        HANDSHAKE_FRAMES,
        leao_keys,
        LEAO_HANDSHAKE_BONES,
    )


def _animate_ronaldo_anger(ronaldo_arm: bpy.types.Object) -> None:
    """握手を見て両手を振り上げるキレポーズ。"""
    base = _capture_evaluated_pose(ronaldo_arm, F_RONALDO_NOTICE)
    keys = [
        (F_RONALDO_NOTICE, base),
        (F_RONALDO_TANTRUM - 8, _pose_with_deltas(base, RONALDO_ANGRY_DELTA, 0.4)),
        (F_RONALDO_TANTRUM + 4, _pose_with_deltas(base, RONALDO_ANGRY_DELTA, 1.0)),
        (F_LEAO_REPLY, _pose_with_deltas(base, RONALDO_ANGRY_DELTA, 1.0)),
        (HANDSHAKE_FRAMES, _pose_with_deltas(base, RONALDO_ANGRY_DELTA, 1.0)),
    ]
    _add_bone_pose_replace_strip(
        ronaldo_arm,
        "Ronaldo_AngryTantrum",
        F_RONALDO_NOTICE,
        HANDSHAKE_FRAMES,
        keys,
        RONALDO_ANGRY_BONES,
    )


def setup_portugal_handshake_characters() -> Tuple[
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
    bpy.types.Object,
]:
    from import_mannequiny import _mesh_child, build_team, set_mesh_split_vertical  # noqa: E402

    _remove_all_players()

    shin_arm = build_team(
        "Shin",
        SHIN_ORANGE,
        [SHIN_START],
        actions=["idle"],
        facing_yaw=SHIN_YAW,
    )[0]
    leao_arm = build_team(
        "Leao",
        PORTUGAL_RED,
        [LEAO_POS],
        actions=["idle"],
        facing_yaw=LEAO_YAW,
    )[0]
    ronaldo_arm = build_team(
        "Ronaldo",
        PORTUGAL_RED,
        [RONALDO_POS],
        actions=["idle"],
        facing_yaw=RONALDO_YAW,
    )[0]

    set_mesh_split_vertical(_mesh_child(leao_arm), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)
    set_mesh_split_vertical(_mesh_child(ronaldo_arm), PORTUGAL_RED, PORTUGAL_GREEN, z_cut=0.42)

    return (
        shin_arm,
        leao_arm,
        ronaldo_arm,
        _root_of(shin_arm),
        _root_of(leao_arm),
        _root_of(ronaldo_arm),
    )


def _hide_ball() -> None:
    ball = bpy.data.objects.get("Ball")
    if ball:
        ball.hide_render = True
        ball.hide_viewport = True


def animate_portugal_shin_handshake() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = HANDSHAKE_FRAMES
    scene.render.fps = FPS

    shin_arm, leao_arm, ronaldo_arm, shin_root, leao_root, ronaldo_root = (
        setup_portugal_handshake_characters()
    )

    for arm in (shin_arm, leao_arm, ronaldo_arm):
        _clear_all_nla(arm)

    ball = bpy.data.objects.get("Ball")
    if ball and ball.animation_data:
        ball.animation_data_clear()
    _hide_ball()

    shin_keys = [(f, _shin_path(f)) for f in range(1, HANDSHAKE_FRAMES + 1)]
    leao_keys = [(f, LEAO_POS) for f in range(1, HANDSHAKE_FRAMES + 1)]
    ronaldo_keys = [(f, _ronaldo_path(f)) for f in range(1, HANDSHAKE_FRAMES + 1)]

    _animate_root_fixed(shin_root, shin_keys, SHIN_YAW)
    _animate_root_fixed(leao_root, leao_keys, LEAO_YAW)
    _animate_root_fixed(ronaldo_root, ronaldo_keys, RONALDO_YAW)

    # シン：待機 → 走る → 到着後 idle
    _add_nla_strip(shin_arm, "idle", 1, F_RUN_START - 1)
    _add_nla_strip(shin_arm, "run", F_RUN_START, F_RUN_END)
    _add_nla_strip(shin_arm, "idle", F_RUN_END + 1, HANDSHAKE_FRAMES)

    # レオン：ずっと idle（握手は REPLACE オーバーレイで応答）
    _add_nla_strip(leao_arm, "idle", 1, HANDSHAKE_FRAMES)

    # ロナウド：idle → 気づき → キレてジャンプ連打
    _add_nla_strip(ronaldo_arm, "idle", 1, F_RONALDO_NOTICE - 1)
    try:
        _add_nla_strip(ronaldo_arm, "fight_idle", F_RONALDO_NOTICE, F_RONALDO_TANTRUM - 1)
    except KeyError:
        _add_nla_strip(ronaldo_arm, "idle", F_RONALDO_NOTICE, F_RONALDO_TANTRUM - 1)
    try:
        _add_nla_strip(ronaldo_arm, "air_jump", F_RONALDO_TANTRUM, HANDSHAKE_FRAMES)
    except KeyError:
        _add_nla_strip(ronaldo_arm, "idle", F_RONALDO_TANTRUM, HANDSHAKE_FRAMES)

    _animate_handshake_poses(shin_arm, leao_arm)
    _animate_ronaldo_anger(ronaldo_arm)

    setup_portugal_handshake_camera()
    scene.frame_set(1)
    print(
        f"Portugal handshake: {HANDSHAKE_FRAMES}f @ {FPS}fps — "
        "Shin run→offer, Leao idle→reply, Ronaldo angry hop"
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


def setup_portugal_handshake_camera() -> bpy.types.Object:
    """手前ロナウド＋奥の握手が同時に見える構図"""
    _remove_cameras()
    cam_data = bpy.data.cameras.new("CamPortugalHandshake")
    cam = bpy.data.objects.new("CamPortugalHandshake", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.lens = 20

    bg_target = (SHIN_END + LEAO_POS) * 0.5 + Vector((0.0, 0.0, 2.1))

    key_frames = [
        F_INTRO,
        F_RUN_START,
        F_RUN_END,
        F_HAND_OFFER,
        F_OFFER_HOLD,
        F_LEAO_REPLY,
        HANDSHAKE_FRAMES,
    ]
    for f in key_frames:
        # ロナウド肩越し・やや寄って握手の腕が見える位置
        cam_pos = RONALDO_POS + Vector((2.2, -4.2, 4.2))
        cam_tgt = bg_target
        _kf_cam(cam, f, cam_pos, cam_tgt)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def render_portugal_handshake_video() -> Path:
    from build_part_field import RENDER_DIR, setup_black_world, setup_lights  # noqa: E402

    setup_black_world()
    setup_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = HANDSHAKE_FRAMES
    scene.eevee.taa_render_samples = 8

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"

    out = RENDER_DIR / "portugal_shin_handshake.mp4"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    print(f"Rendering portugal handshake video: {out}")
    bpy.ops.render.render(animation=True)
    print(f"Video saved: {out}")
    return out


if __name__ == "__main__":
    import sys

    from news_cg_common import open_blend, resolve_blend_path

    blend = resolve_blend_path()
    open_blend(blend)
    if "--render" in sys.argv or "--render-portugal-handshake-video" in sys.argv:
        render_portugal_handshake_video()
    else:
        animate_portugal_shin_handshake()
        bpy.ops.wm.save_mainfile(filepath=str(blend))
