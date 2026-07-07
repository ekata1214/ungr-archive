# SPDX-License-Identifier: MIT
"""
~/Desktop/sho-lin-soccer.blend を開き、ハーランド vs 少林GK シーンを書き込む。

使い方（デスクトップに sho-lin-soccer.blend がある状態）:
  blender -b ~/Desktop/sho-lin-soccer.blend -P blender/scenes/apply_to_sho_lin_soccer.py

  またはファイルを開かずにパス指定:
  blender -b -P blender/scenes/apply_to_sho_lin_soccer.py

保存先: 同じ sho-lin-soccer.blend に上書き保存
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bpy
from mathutils import Euler, Vector

# 同ディレクトリのシーン定義を読み込む
_SCRIPT_DIR = Path(__file__).resolve().parent
_ns: dict = {"__name__": "shaolin_soccer_haaland_gk_news_cg"}
exec((_SCRIPT_DIR / "shaolin_soccer_haaland_gk_news_cg.py").read_text(encoding="utf-8"), _ns)

FRAME_END = _ns["FRAME_END"]
FPS = _ns["FPS"]
TEAM_BLUE = _ns["TEAM_BLUE"]
TEAM_RED = _ns["TEAM_RED"]
StickFigure = _ns["StickFigure"]
build_stick_figure = _ns["build_stick_figure"]
animate_ball = _ns["animate_ball"]
animate_haaland = _ns["animate_haaland"]
animate_goalkeeper = _ns["animate_goalkeeper"]
animate_camera = _ns["animate_camera"]
setup_render = _ns["setup_render"]
set_linear_interpolation = _ns["set_linear_interpolation"]
add_news_caption = _ns["add_news_caption"]
add_title_bug = _ns["add_title_bug"]
build_pitch = _ns["build_pitch"]
build_goal_and_wall = _ns["build_goal_and_wall"]
build_ball = _ns["build_ball"]
build_camera_and_light = _ns["build_camera_and_light"]
keyframe_loc_rot = _ns["keyframe_loc_rot"]

BLEND_FILENAMES = ("sho-lin-soccer.blend", "sho-lin-soccer")
SEARCH_DIRS = (
    Path.home() / "Desktop",
    _SCRIPT_DIR.parent / "assets",
    Path("/workspace/blender/assets"),
)


def resolve_blend_path() -> Path:
    for directory in SEARCH_DIRS:
        for name in BLEND_FILENAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate.resolve()
    searched = ", ".join(str(d / BLEND_FILENAMES[0]) for d in SEARCH_DIRS)
    raise FileNotFoundError(
        f"sho-lin-soccer.blend が見つかりません。次のいずれかに置いてください:\n  {searched}"
    )


def open_blend(path: Path) -> None:
    current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if current == path:
        print(f"Already open: {path}")
        return
    print(f"Opening: {path}")
    bpy.ops.wm.open_mainfile(filepath=str(path))


def _name_matches(name: str, patterns: Tuple[str, ...]) -> bool:
    lower = name.lower()
    return any(p.lower() in lower for p in patterns)


def find_object(patterns: Tuple[str, ...], obj_type: Optional[str] = None) -> Optional[bpy.types.Object]:
    for obj in bpy.data.objects:
        if obj_type and obj.type != obj_type:
            continue
        if _name_matches(obj.name, patterns):
            return obj
    return None


def material_rgb(obj: bpy.types.Object) -> Optional[Tuple[float, float, float]]:
    if not hasattr(obj.data, "materials"):
        return None
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            c = bsdf.inputs["Base Color"].default_value
            return (c[0], c[1], c[2])
    return None


def team_hue_score(rgb: Tuple[float, float, float]) -> str:
    r, g, b = rgb
    if b > r + 0.08 and b > g:
        return "blue"
    if r > b + 0.08 and r > g * 0.9:
        return "red"
    return "neutral"


def find_stick_roots() -> List[bpy.types.Object]:
    roots: List[bpy.types.Object] = []
    for obj in bpy.data.objects:
        if obj.type != "EMPTY" or obj.parent is not None:
            continue
        if obj.name.endswith("_root") or obj.name.endswith("Root"):
            roots.append(obj)
            continue
        joint_kids = [c for c in obj.children if c.type == "EMPTY" and "joint" in c.name.lower()]
        mesh_kids = [c for c in obj.children if c.type == "MESH"]
        if len(joint_kids) >= 2 and len(mesh_kids) >= 1:
            roots.append(obj)
    return roots


def stick_figure_from_root(root: bpy.types.Object) -> StickFigure:
    parts: Dict[str, bpy.types.Object] = {}
    prefix = root.name
    if root.name.endswith("_root"):
        prefix = root.name[: -len("_root")] + "_"

    for obj in bpy.data.objects:
        if obj.type != "EMPTY" or "joint" not in obj.name.lower():
            continue
        if not (obj.name.startswith(prefix) or obj == root):
            continue
        key = obj.name[len(prefix) :] if obj.name.startswith(prefix) else obj.name
        parts[key] = obj

    return StickFigure(root=root, parts=parts)


def classify_roots(roots: List[bpy.types.Object]) -> Tuple[Optional[bpy.types.Object], Optional[bpy.types.Object], List[bpy.types.Object]]:
    by_name_red: List[bpy.types.Object] = []
    by_name_blue: List[bpy.types.Object] = []
    by_color: Dict[str, List[bpy.types.Object]] = {"red": [], "blue": [], "neutral": []}

    for root in roots:
        name = root.name.lower()
        if _name_matches(name, ("haaland", "red", "norway", "striker", "赤")):
            by_name_red.append(root)
        elif _name_matches(name, ("gk", "keeper", "shaolin", "blue", "goal", "青")):
            by_name_blue.append(root)
        else:
            colors: List[str] = []
            for child in root.children_recursive:
                if child.type == "MESH":
                    rgb = material_rgb(child)
                    if rgb:
                        colors.append(team_hue_score(rgb))
            if colors.count("red") > colors.count("blue"):
                by_color["red"].append(root)
            elif colors.count("blue") > colors.count("red"):
                by_color["blue"].append(root)
            else:
                by_color["neutral"].append(root)

    striker = (by_name_red or by_color["red"] or [None])[0]
    gk = (by_name_blue or by_color["blue"] or [None])[0]

    used = {id(x) for x in (striker, gk) if x}
    extras = [r for r in roots if id(r) not in used]
    return striker, gk, extras


def clear_object_animation(obj: bpy.types.Object) -> None:
    if not obj.animation_data or not obj.animation_data.action:
        return
    obj.animation_data_clear()


def clear_scene_animation() -> None:
    for obj in bpy.data.objects:
        clear_object_animation(obj)


def ensure_environment() -> bpy.types.Object:
    """ピッチ・ゴール・壁・ボール・カメラ・テロップをなければ追加、あれば再利用"""
    if not find_object(("pitch", "field", "ピッチ", "ground")):
        build_pitch()
    if not find_object(("goal", "post", "crossbar")):
        build_goal_and_wall()
    elif not find_object(("wall", "backwall")):
        wall_mat = _ns["make_flat_material"]("wall", _ns["WALL_GRAY"])
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-20.3, 0, 2.5))
        wall = bpy.context.active_object
        wall.name = "BackWall"
        wall.scale = (0.1, 8, 5)
        wall.data.materials.append(wall_mat)

    ball = find_object(("ball", "ボール"))
    if ball is None:
        ball = build_ball()

    cam = find_object(("newscam", "camera", "cam"), "CAMERA")
    if cam is None:
        cam = build_camera_and_light()
    else:
        bpy.context.scene.camera = cam

    if not find_object(("newsbug", "bug")):
        add_title_bug()
    if not find_object(("caption",)):
        add_news_caption("なぜあの人は重力を無視してるんだ…", 155, FRAME_END)

    return ball


def ensure_characters() -> Tuple[StickFigure, StickFigure, List[StickFigure]]:
    roots = find_stick_roots()
    striker_root, gk_root, extras = classify_roots(roots)

    if striker_root is None:
        print("赤チーム棒人間が見つからないため Haaland を新規作成")
        striker = build_stick_figure("Haaland", TEAM_RED, Vector((3, 0, 0)))
    else:
        print(f"赤チーム（ストライカー）: {striker_root.name}")
        striker = stick_figure_from_root(striker_root)

    if gk_root is None:
        print("青チームGKが見つからないため ShaolinGK を新規作成")
        goalkeeper = build_stick_figure("ShaolinGK", TEAM_BLUE, Vector((-17, 0, 0)))
    else:
        print(f"青チーム（GK）: {gk_root.name}")
        goalkeeper = stick_figure_from_root(gk_root)

    extra_figs: List[StickFigure] = []
    for i, root in enumerate(extras[:2]):
        print(f"補助キャラ: {root.name}")
        extra_figs.append(stick_figure_from_root(root))

    return striker, goalkeeper, extra_figs


def animate_extras(extras: List[StickFigure]) -> None:
    import math

    for i, fig in enumerate(extras):
        y = -3.0 + i * 6.0
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


def apply_scene() -> None:
    clear_scene_animation()
    setup_render()
    ball = ensure_environment()

    striker, goalkeeper, extras = ensure_characters()

    cam = bpy.context.scene.camera or find_object(("newscam", "camera"), "CAMERA")
    if cam is None:
        cam = build_camera_and_light()

    animate_ball(ball)
    animate_haaland(striker)
    animate_goalkeeper(goalkeeper)
    animate_camera(cam)

    if extras:
        animate_extras(extras)
    elif find_object(("defendera", "defenderb")):
        for tag in ("defendera", "defenderb"):
            root = find_object((tag,))
            if root and root.type == "EMPTY":
                animate_extras([stick_figure_from_root(root)])
    else:
        _ns["animate_defenders"]()

    set_linear_interpolation()
    bpy.context.scene.frame_set(1)


def save_blend(path: Path) -> None:
    bpy.ops.wm.save_mainfile(filepath=str(path))
    print(f"Saved: {path}")


def main() -> None:
    path = resolve_blend_path()
    open_blend(path)
    apply_scene()
    save_blend(path)
    print("sho-lin-soccer.blend へのシーン書き込み完了")
    print("  青 = 少林GK / 赤 = ハーランド")
    print("  タイムライン: 10秒 (24fps)")


if __name__ == "__main__":
    main()
