# SPDX-License-Identifier: MIT
"""
少林サッカー × 2026W杯 — ニュース事件CG風サッカー再現（試作）

シーン: グループステージ最終戦 vs ノルウェー
「ハーランドの大砲シュート → 少林GKが壁を垂直に駆け上がって阻止」

使い方:
  1. Blender 3.6+ を開く
  2. Scripting タブ → このファイルを開いて Run Script
  または:
     blender --python blender/scenes/shaolin_soccer_haaland_gk_news_cg.py

  レンダーまで一気に:
     blender -b -P blender/scenes/shaolin_soccer_haaland_gk_news_cg.py -- --render

台本の該当箇所:
  「少林サッカーチームのゴールキーパーは、まさかの壁を垂直に駆け上がる守備で
   ハーランドのシュートを全て弾き返します」
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bpy
from mathutils import Euler, Vector

# ---------------------------------------------------------------------------
# 定数 — ニュースCGっぽい配色・尺
# ---------------------------------------------------------------------------

FPS = 24
DURATION_SEC = 10
FRAME_END = FPS * DURATION_SEC

TEAM_BLUE = (0.15, 0.45, 0.95, 1.0)   # 少林サッカーチーム
TEAM_RED = (0.92, 0.18, 0.15, 1.0)    # ノルウェー（ハーランド）
BALL_COLOR = (0.95, 0.95, 0.95, 1.0)
FIELD_GREEN = (0.18, 0.55, 0.22, 1.0)
LINE_WHITE = (0.95, 0.95, 0.95, 1.0)
WALL_GRAY = (0.75, 0.75, 0.78, 1.0)


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablock in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.curves,
    ):
        for block in list(datablock):
            if block.users == 0:
                datablock.remove(block)


def setup_render() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    scene.eevee.taa_render_samples = 32
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.82, 0.86, 0.90, 1.0)
    bg.inputs[1].default_value = 1.0


def make_flat_material(name: str, rgba: Tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.85
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec:
        spec.default_value = 0.15
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def link_object(obj: bpy.types.Object) -> bpy.types.Object:
    bpy.context.collection.objects.link(obj)
    return obj


def add_empty(name: str, location: Vector, parent: Optional[bpy.types.Object] = None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    link_object(obj)
    obj.empty_display_size = 0.15
    obj.location = location
    if parent:
        obj.parent = parent
    return obj


def add_cylinder(
    name: str,
    radius: float,
    depth: float,
    location: Vector,
    material: bpy.types.Material,
    parent: Optional[bpy.types.Object] = None,
    rotation: Euler = Euler((0, 0, 0)),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def add_sphere(
    name: str,
    radius: float,
    location: Vector,
    material: bpy.types.Material,
    parent: Optional[bpy.types.Object] = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def keyframe_loc_rot(obj: bpy.types.Object, frame: int) -> None:
    obj.keyframe_insert(data_path="location", frame=frame)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def set_linear_interpolation() -> None:
    for action in bpy.data.actions:
        for fcurve in action.fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = "LINEAR"


# ---------------------------------------------------------------------------
# 棒人間（青/赤）— よくあるニュース再現CGスタイル
# ---------------------------------------------------------------------------

class StickFigure:
    def __init__(self, root: bpy.types.Object, parts: Dict[str, bpy.types.Object]):
        self.root = root
        self.parts = parts

    def pose(self, frame: int, root_pos: Vector, root_rot: Euler, limb_angles: Dict[str, Euler]) -> None:
        self.root.location = root_pos
        self.root.rotation_euler = root_rot
        keyframe_loc_rot(self.root, frame)
        for name, rot in limb_angles.items():
            part = self.parts[name]
            part.rotation_euler = rot
            keyframe_loc_rot(part, frame)


def build_stick_figure(name: str, color: Tuple[float, float, float, float], location: Vector) -> StickFigure:
    mat = make_flat_material(f"{name}_mat", color)
    parts: Dict[str, bpy.types.Object] = {}

    root = add_empty(f"{name}_root", location)

    # 胴体
    torso = add_cylinder(f"{name}_torso", 0.11, 0.55, Vector((0, 0, 0.95)), mat, root)
    parts["torso"] = torso

    # 頭
    head_joint = add_empty(f"{name}_head_joint", Vector((0, 0, 1.35)), root)
    parts["head_joint"] = head_joint
    add_sphere(f"{name}_head", 0.18, Vector((0, 0, 0.18)), mat, head_joint)

    def limb(side: str, axis_sign: float, is_arm: bool) -> None:
        upper_len = 0.38 if is_arm else 0.42
        lower_len = 0.38 if is_arm else 0.44
        x = axis_sign * (0.22 if is_arm else 0.10)
        z = 1.15 if is_arm else 0.55

        upper_joint = add_empty(f"{name}_{side}_upper_joint", Vector((x, 0, z)), root)
        parts[f"{side}_upper_joint"] = upper_joint
        add_cylinder(
            f"{name}_{side}_upper",
            0.05,
            upper_len,
            Vector((0, 0, -upper_len / 2)),
            mat,
            upper_joint,
            Euler((0.2 * axis_sign, 0, 0)),
        )

        lower_joint = add_empty(f"{name}_{side}_lower_joint", Vector((0, 0, -upper_len)), upper_joint)
        parts[f"{side}_lower_joint"] = lower_joint
        add_cylinder(
            f"{name}_{side}_lower",
            0.045,
            lower_len,
            Vector((0, 0, -lower_len / 2)),
            mat,
            lower_joint,
        )

    limb("arm_l", -1.0, True)
    limb("arm_r", 1.0, True)
    limb("leg_l", -1.0, False)
    limb("leg_r", 1.0, False)

    return StickFigure(root=root, parts=parts)

def build_pitch() -> None:
    field_mat = make_flat_material("field", FIELD_GREEN)
    line_mat = make_flat_material("line", LINE_WHITE)

    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    field = bpy.context.active_object
    field.name = "Pitch"
    field.data.materials.append(field_mat)

    def line(name: str, size_x: float, size_y: float, loc: Vector) -> None:
        bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (size_x, size_y, 1)
        obj.data.materials.append(line_mat)

    line("CenterLine", 0.12, 18, Vector((0, 0, 0.01)))
    line("PenaltyArea", 12, 0.12, Vector((-14, 0, 0.01)))
    line("GoalLine", 0.12, 8, Vector((-20, 0, 0.01)))


def build_goal_and_wall() -> Tuple[bpy.types.Object, bpy.types.Object]:
    post_mat = make_flat_material("goal_post", (0.9, 0.9, 0.9, 1.0))
    wall_mat = make_flat_material("wall", WALL_GRAY)

    goal_root = add_empty("Goal", Vector((-20, 0, 0)))

    for y_sign, label in ((-1, "L"), (1, "R")):
        add_cylinder(f"Post_{label}", 0.07, 2.44, Vector((0, y_sign * 3.66, 1.22)), post_mat, goal_root)
    add_cylinder("Crossbar", 0.07, 7.32, Vector((0, 0, 2.44)), post_mat, goal_root, Euler((0, math.pi / 2, 0)))

    # ゴール裏の「壁」— GKが駆け上がる対象
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-20.3, 0, 2.5))
    wall = bpy.context.active_object
    wall.name = "BackWall"
    wall.scale = (0.1, 8, 5)
    wall.data.materials.append(wall_mat)

    return goal_root, wall


def build_ball() -> bpy.types.Object:
    mat = make_flat_material("ball", BALL_COLOR)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, location=(2, 0, 0.11))
    ball = bpy.context.active_object
    ball.name = "Ball"
    ball.data.materials.append(mat)
    return ball


def build_camera_and_light() -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("NewsCam")
    cam = bpy.data.objects.new("NewsCam", cam_data)
    link_object(cam)
    # よくある斜め俯瞰アングル
    cam.location = Vector((6, -14, 9))
    cam.rotation_euler = Euler((math.radians(58), 0, math.radians(22)))
    bpy.context.scene.camera = cam

    key_data = bpy.data.lights.new("Key", type="SUN")
    key = bpy.data.objects.new("Key", key_data)
    link_object(key)
    key.rotation_euler = Euler((math.radians(50), math.radians(10), math.radians(25)))
    key.data.energy = 2.5

    fill_data = bpy.data.lights.new("Fill", type="AREA")
    fill = bpy.data.objects.new("Fill", fill_data)
    link_object(fill)
    fill.location = Vector((0, -8, 12))
    fill.rotation_euler = Euler((math.radians(65), 0, 0))
    fill.data.energy = 350
    fill.data.size = 12

    return cam


def add_news_caption(text: str, frame_start: int, frame_end: int) -> bpy.types.Object:
    curve = bpy.data.curves.new("CaptionCurve", type="FONT")
    curve.body = text
    curve.size = 0.55
    curve.align_x = "CENTER"

    obj = bpy.data.objects.new("Caption", curve)
    link_object(obj)
    obj.location = Vector((0, 0, 6.2))
    obj.rotation_euler = Euler((math.radians(90), 0, 0))

    mat = make_flat_material("caption_mat", (0.05, 0.05, 0.05, 1.0))
    obj.data.materials.append(mat)

    obj.hide_viewport = True
    obj.hide_render = True
    obj.keyframe_insert(data_path="hide_render", frame=frame_start - 1)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame_start - 1)

    obj.hide_viewport = False
    obj.hide_render = False
    obj.keyframe_insert(data_path="hide_render", frame=frame_start)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame_start)

    obj.keyframe_insert(data_path="hide_render", frame=frame_end)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame_end)

    obj.hide_viewport = True
    obj.hide_render = True
    obj.keyframe_insert(data_path="hide_render", frame=frame_end + 1)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame_end + 1)

    return obj


def add_title_bug() -> None:
    """画面左上のニュース風テロップ帯"""
    bar_mat = make_flat_material("bug_bar", (0.08, 0.18, 0.55, 1.0))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-4, -6, 5.5))
    bar = bpy.context.active_object
    bar.name = "NewsBug"
    bar.scale = (5.5, 0.55, 1)
    bar.data.materials.append(bar_mat)

    curve = bpy.data.curves.new("BugText", type="FONT")
    curve.body = "再現CG  2026W杯グループ最終戦"
    curve.size = 0.28
    curve.align_x = "LEFT"
    txt = bpy.data.objects.new("BugLabel", curve)
    link_object(txt)
    txt.location = Vector((-6.3, -6.0, 5.55))
    txt.rotation_euler = Euler((math.radians(90), 0, 0))
    txt.data.materials.append(make_flat_material("bug_text", (1, 1, 1, 1)))


# ---------------------------------------------------------------------------
# アニメーション
# ---------------------------------------------------------------------------

def animate_ball(ball: bpy.types.Object) -> None:
    frames: List[Tuple[int, Vector]] = [
        (1, Vector((4.5, 0.0, 0.11))),
        (40, Vector((3.0, 0.0, 0.11))),      # ハーランドがボール保持
        (55, Vector((1.0, 0.0, 0.25))),     # キック瞬間
        (85, Vector((-12.0, 0.2, 1.6))),    # ゴールに向かう弾道
        (105, Vector((-17.5, 0.1, 1.9))),   # GKの手前
        (115, Vector((-14.0, 2.5, 2.8))),   # 弾き返し
        (150, Vector((-10.0, 4.0, 0.2))),   # 場外へ
        (FRAME_END, Vector((-10.0, 4.0, 0.2))),
    ]
    for frame, pos in frames:
        ball.location = pos
        ball.keyframe_insert(data_path="location", frame=frame)


def animate_haaland(striker: StickFigure) -> None:
    """赤チーム（ハーランド役）: 助走 → 強烈シュート → 困惑ポーズ"""
    p = striker.parts

    # 待機
    striker.pose(
        1,
        Vector((3.2, 0.0, 0.0)),
        Euler((0, 0, math.radians(175))),
        {
            "leg_l_upper_joint": Euler((math.radians(-8), 0, 0)),
            "leg_r_upper_joint": Euler((math.radians(12), 0, 0)),
            "leg_l_lower_joint": Euler((math.radians(5), 0, 0)),
            "leg_r_lower_joint": Euler((math.radians(-6), 0, 0)),
            "arm_l_upper_joint": Euler((math.radians(-18), 0, math.radians(-8))),
            "arm_r_upper_joint": Euler((math.radians(20), 0, math.radians(10))),
        },
    )

    # キックモーション
    striker.pose(
        55,
        Vector((1.8, 0.0, 0.0)),
        Euler((0, 0, math.radians(178))),
        {
            "leg_l_upper_joint": Euler((math.radians(-35), 0, 0)),
            "leg_r_upper_joint": Euler((math.radians(68), 0, 0)),
            "leg_r_lower_joint": Euler((math.radians(-12), 0, 0)),
            "arm_l_upper_joint": Euler((math.radians(-45), 0, math.radians(-20))),
            "arm_r_upper_joint": Euler((math.radians(35), 0, math.radians(35))),
        },
    )

    # フォロースルー
    striker.pose(
        75,
        Vector((1.5, -0.2, 0.0)),
        Euler((0, 0, math.radians(160))),
        {
            "leg_r_upper_joint": Euler((math.radians(95), 0, 0)),
            "leg_r_lower_joint": Euler((math.radians(-8), 0, 0)),
            "arm_l_upper_joint": Euler((math.radians(-60), 0, math.radians(-10))),
            "arm_r_upper_joint": Euler((math.radians(55), 0, math.radians(25))),
        },
    )

    # 困惑（頭を抱える）
    striker.pose(
        150,
        Vector((0.5, -1.0, 0.0)),
        Euler((0, 0, math.radians(140))),
        {
            "head_joint": Euler((math.radians(-12), 0, 0)),
            "arm_l_upper_joint": Euler((math.radians(-95), 0, math.radians(-25))),
            "arm_l_lower_joint": Euler((math.radians(-70), 0, 0)),
            "arm_r_upper_joint": Euler((math.radians(-95), 0, math.radians(25))),
            "arm_r_lower_joint": Euler((math.radians(-70), 0, 0)),
            "leg_l_upper_joint": Euler((math.radians(-5), 0, 0)),
            "leg_r_upper_joint": Euler((math.radians(8), 0, 0)),
        },
    )

    striker.pose(
        FRAME_END,
        Vector((0.5, -1.0, 0.0)),
        Euler((0, 0, math.radians(140))),
        {
            "head_joint": Euler((math.radians(-12), 0, 0)),
            "arm_l_upper_joint": Euler((math.radians(-95), 0, math.radians(-25))),
            "arm_l_lower_joint": Euler((math.radians(-70), 0, 0)),
            "arm_r_upper_joint": Euler((math.radians(-95), 0, math.radians(25))),
            "arm_r_lower_joint": Euler((math.radians(-70), 0, 0)),
        },
    )


def animate_goalkeeper(gk: StickFigure) -> None:
    """青チームGK: 通常構え → 壁垂直ダッシュ → 上空セーブ"""
    # 初期位置（ゴール前）
    gk.pose(
        1,
        Vector((-17.0, 0.4, 0.0)),
        Euler((0, 0, math.radians(90))),
        {
            "arm_l_upper_joint": Euler((math.radians(-50), 0, math.radians(-15))),
            "arm_r_upper_joint": Euler((math.radians(-50), 0, math.radians(15))),
            "leg_l_upper_joint": Euler((math.radians(-22), 0, 0)),
            "leg_r_upper_joint": Euler((math.radians(18), 0, 0)),
        },
    )

    # 反応開始 — 壁方向へダッシュ
    gk.pose(
        70,
        Vector((-18.5, 0.35, 0.0)),
        Euler((0, 0, math.radians(90))),
        {
            "arm_l_upper_joint": Euler((math.radians(-30), 0, math.radians(-40))),
            "arm_r_upper_joint": Euler((math.radians(-20), 0, math.radians(50))),
            "leg_l_upper_joint": Euler((math.radians(-55), 0, 0)),
            "leg_r_upper_joint": Euler((math.radians(42), 0, 0)),
        },
    )

    # 壁を垂直に駆け上がる（体を90度近く傾ける）
    gk.pose(
        95,
        Vector((-19.55, 0.2, 1.2)),
        Euler((0, math.radians(88), math.radians(90))),
        {
            "arm_l_upper_joint": Euler((math.radians(-120), 0, math.radians(-10))),
            "arm_r_upper_joint": Euler((math.radians(-140), 0, math.radians(10))),
            "leg_l_upper_joint": Euler((math.radians(-12), 0, 0)),
            "leg_r_upper_joint": Euler((math.radians(18), 0, 0)),
        },
    )

    # 上空でセーブ
    gk.pose(
        110,
        Vector((-19.55, 0.2, 2.15)),
        Euler((0, math.radians(90), math.radians(90))),
        {
            "arm_l_upper_joint": Euler((math.radians(-155), 0, math.radians(-35))),
            "arm_r_upper_joint": Euler((math.radians(-165), 0, math.radians(35))),
            "arm_l_lower_joint": Euler((math.radians(-25), 0, 0)),
            "arm_r_lower_joint": Euler((math.radians(-25), 0, 0)),
        },
    )

    # 着地
    gk.pose(
        140,
        Vector((-17.5, 0.5, 0.0)),
        Euler((0, 0, math.radians(90))),
        {
            "arm_l_upper_joint": Euler((math.radians(-70), 0, math.radians(-20))),
            "arm_r_upper_joint": Euler((math.radians(-70), 0, math.radians(20))),
            "leg_l_upper_joint": Euler((math.radians(-28), 0, 0)),
            "leg_r_upper_joint": Euler((math.radians(22), 0, 0)),
        },
    )

    gk.pose(
        FRAME_END,
        Vector((-17.5, 0.5, 0.0)),
        Euler((0, 0, math.radians(90))),
        {
            "arm_l_upper_joint": Euler((math.radians(-40), 0, math.radians(-10))),
            "arm_r_upper_joint": Euler((math.radians(-40), 0, math.radians(10))),
        },
    )


def animate_camera(cam: bpy.types.Object) -> None:
    """ニュース番組っぽく、決定的瞬間にズーム"""
    keyframes = [
        (1, Vector((6, -14, 9)), Euler((math.radians(58), 0, math.radians(22)))),
        (50, Vector((4, -11, 8)), Euler((math.radians(60), 0, math.radians(18)))),
        (95, Vector((2, -8.5, 7.2)), Euler((math.radians(62), 0, math.radians(12)))),
        (130, Vector((3, -10, 8.5)), Euler((math.radians(58), 0, math.radians(16)))),
        (FRAME_END, Vector((3, -10, 8.5)), Euler((math.radians(58), 0, math.radians(16)))),
    ]
    for frame, loc, rot in keyframes:
        cam.location = loc
        cam.rotation_euler = rot
        keyframe_loc_rot(cam, frame)


def animate_defenders() -> None:
    """青チームの補助キャラ2人 — ただ立ってるだけ（雰囲気用）"""
    blue_mat_team = TEAM_BLUE
    g1 = build_stick_figure("DefenderA", blue_mat_team, Vector((-6, -3, 0)))
    g2 = build_stick_figure("DefenderB", blue_mat_team, Vector((-6, 3, 0)))
    for fig, y in ((g1, -3), (g2, 3)):
        fig.pose(
            1,
            Vector((-6, y, 0)),
            Euler((0, 0, math.radians(95))),
            {
                "arm_l_upper_joint": Euler((math.radians(-15), 0, 0)),
                "arm_r_upper_joint": Euler((math.radians(-15), 0, 0)),
            },
        )
        fig.pose(
            FRAME_END,
            Vector((-6, y, 0)),
            Euler((0, 0, math.radians(95))),
            {
                "arm_l_upper_joint": Euler((math.radians(-15), 0, 0)),
                "arm_r_upper_joint": Euler((math.radians(-15), 0, 0)),
            },
        )


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def build_scene() -> None:
    clear_scene()
    setup_render()

    build_pitch()
    build_goal_and_wall()
    ball = build_ball()
    cam = build_camera_and_light()
    add_title_bug()

    haaland = build_stick_figure("Haaland", TEAM_RED, Vector((3, 0, 0)))
    goalkeeper = build_stick_figure("ShaolinGK", TEAM_BLUE, Vector((-17, 0, 0)))

    animate_ball(ball)
    animate_haaland(haaland)
    animate_goalkeeper(goalkeeper)
    animate_camera(cam)
    animate_defenders()

    add_news_caption("なぜあの人は重力を無視してるんだ…", 155, FRAME_END)

    set_linear_interpolation()
    bpy.context.scene.frame_set(1)


def maybe_render() -> None:
    if "--render" not in sys.argv:
        return
    out = bpy.path.abspath("//renders/shaolin_haaland_gk_####.png")
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(animation=True)
    print(f"Rendered to: {out}")


def maybe_save_desktop() -> None:
    if "--save-desktop" not in sys.argv:
        return
    out = Path.home() / "Desktop" / "shaolin_soccer_haaland_gk_news_cg.blend"
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"Saved: {out}")


def main() -> None:
    build_scene()
    maybe_save_desktop()
    maybe_render()
    print("少林サッカー ニュースCGシーン構築完了")
    print("  青 = 少林GK / 赤 = ハーランド（ノルウェー）")
    print("  タイムライン: 10秒 (24fps)")
    print("  Space で再生、または --render で書き出し")


if __name__ == "__main__":
    main()
