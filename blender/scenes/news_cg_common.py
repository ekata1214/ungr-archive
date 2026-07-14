# SPDX-License-Identifier: MIT
"""ニュースCG風サッカー再現 — 共通ユーティリティ"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bpy
from mathutils import Euler, Vector

FPS = 24
DURATION_SEC = 10
FRAME_END = FPS * DURATION_SEC

TEAM_BLUE = (0.15, 0.45, 0.95, 1.0)
TEAM_RED = (0.92, 0.18, 0.15, 1.0)
BALL_COLOR = (0.95, 0.95, 0.95, 1.0)
FIELD_GREEN = (0.18, 0.55, 0.22, 1.0)
LINE_WHITE = (0.95, 0.95, 0.95, 1.0)
WALL_GRAY = (0.75, 0.75, 0.78, 1.0)

BLEND_FILENAMES = ("sho-lin-soccer.blend", "sho-lin-soccer")
SEARCH_DIRS = (
    Path.home() / "Desktop",
    Path(__file__).resolve().parent.parent / "assets",
    Path("/workspace/blender/assets"),
)


def resolve_blend_path() -> Path:
    for directory in SEARCH_DIRS:
        for name in BLEND_FILENAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate.resolve()
    searched = ", ".join(str(d / BLEND_FILENAMES[0]) for d in SEARCH_DIRS)
    raise FileNotFoundError(f"sho-lin-soccer.blend が見つかりません:\n  {searched}")


def open_blend(path: Path) -> None:
    current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if current == path:
        return
    bpy.ops.wm.open_mainfile(filepath=str(path))


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablock in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.curves):
        for block in list(datablock):
            if block.users == 0:
                datablock.remove(block)


def clear_scene_animation() -> None:
    for obj in bpy.data.objects:
        if obj.animation_data:
            obj.animation_data_clear()


def setup_render() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    if not scene.world:
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
    name: str, radius: float, depth: float, location: Vector, material: bpy.types.Material,
    parent: Optional[bpy.types.Object] = None, rotation: Euler = Euler((0, 0, 0)),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def add_sphere(
    name: str, radius: float, location: Vector, material: bpy.types.Material,
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


def find_object(patterns: Tuple[str, ...], obj_type: Optional[str] = None) -> Optional[bpy.types.Object]:
    for obj in bpy.data.objects:
        if obj_type and obj.type != obj_type:
            continue
        lower = obj.name.lower()
        if any(p.lower() in lower for p in patterns):
            return obj
    return None


def remove_objects(patterns: Tuple[str, ...]) -> None:
    for obj in list(bpy.data.objects):
        lower = obj.name.lower()
        if any(p.lower() in lower for p in patterns):
            bpy.data.objects.remove(obj, do_unlink=True)


class StickFigure:
    def __init__(self, root: bpy.types.Object, parts: Dict[str, bpy.types.Object]):
        self.root = root
        self.parts = parts

    def pose(self, frame: int, root_pos: Vector, root_rot: Euler, limb_angles: Dict[str, Euler]) -> None:
        self.root.location = root_pos
        self.root.rotation_euler = root_rot
        keyframe_loc_rot(self.root, frame)
        for name, rot in limb_angles.items():
            if name in self.parts:
                self.parts[name].rotation_euler = rot
                keyframe_loc_rot(self.parts[name], frame)


def build_stick_figure(name: str, color: Tuple[float, float, float, float], location: Vector) -> StickFigure:
    mat = make_flat_material(f"{name}_mat", color)
    parts: Dict[str, bpy.types.Object] = {}
    root = add_empty(f"{name}_root", location)
    add_cylinder(f"{name}_torso", 0.11, 0.55, Vector((0, 0, 0.95)), mat, root)
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
        add_cylinder(f"{name}_{side}_upper", 0.05, upper_len, Vector((0, 0, -upper_len / 2)), mat, upper_joint, Euler((0.2 * axis_sign, 0, 0)))
        lower_joint = add_empty(f"{name}_{side}_lower_joint", Vector((0, 0, -upper_len)), upper_joint)
        parts[f"{side}_lower_joint"] = lower_joint
        add_cylinder(f"{name}_{side}_lower", 0.045, lower_len, Vector((0, 0, -lower_len / 2)), mat, lower_joint)

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

    def line(name: str, sx: float, sy: float, loc: Vector) -> None:
        bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (sx, sy, 1)
        obj.data.materials.append(line_mat)

    line("CenterLine", 0.12, 18, Vector((0, 0, 0.01)))
    line("PenaltyArea", 12, 0.12, Vector((-14, 0, 0.01)))
    line("GoalLine", 0.12, 8, Vector((-20, 0, 0.01)))


def build_goal_and_wall() -> None:
    post_mat = make_flat_material("goal_post", (0.9, 0.9, 0.9, 1.0))
    wall_mat = make_flat_material("wall", WALL_GRAY)
    goal_root = add_empty("Goal", Vector((-20, 0, 0)))
    for y_sign, label in ((-1, "L"), (1, "R")):
        add_cylinder(f"Post_{label}", 0.07, 2.44, Vector((0, y_sign * 3.66, 1.22)), post_mat, goal_root)
    add_cylinder("Crossbar", 0.07, 7.32, Vector((0, 0, 2.44)), post_mat, goal_root, Euler((0, math.pi / 2, 0)))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-20.3, 0, 2.5))
    wall = bpy.context.active_object
    wall.name = "BackWall"
    wall.scale = (0.1, 8, 5)
    wall.data.materials.append(wall_mat)


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
    cam.location = Vector((2.0, -7.0, 5.0))
    cam.rotation_euler = Euler((math.radians(62), 0, math.radians(14)))
    bpy.context.scene.camera = cam
    if not find_object(("key",), "LIGHT"):
        key_data = bpy.data.lights.new("Key", type="SUN")
        key = bpy.data.objects.new("Key", key_data)
        link_object(key)
        key.rotation_euler = Euler((math.radians(50), math.radians(10), math.radians(25)))
        key.data.energy = 2.5
    if not find_object(("fill",), "LIGHT"):
        fill_data = bpy.data.lights.new("Fill", type="AREA")
        fill = bpy.data.objects.new("Fill", fill_data)
        link_object(fill)
        fill.location = Vector((0, -8, 12))
        fill.rotation_euler = Euler((math.radians(65), 0, 0))
        fill.data.energy = 350
        fill.data.size = 12
    return cam


def ensure_ball() -> bpy.types.Object:
    ball = find_object(("ball", "ボール"))
    return ball if ball else build_ball()


def ensure_camera() -> bpy.types.Object:
    cam = find_object(("newscam", "camera"), "CAMERA")
    if cam:
        bpy.context.scene.camera = cam
        return cam
    return build_camera_and_light()


def ensure_title_bug(text: str) -> None:
    remove_objects(("newsbug", "buglabel"))
    bar_mat = make_flat_material("bug_bar", (0.08, 0.18, 0.55, 1.0))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-2, -4, 4.5))
    bar = bpy.context.active_object
    bar.name = "NewsBug"
    bar.scale = (6, 0.5, 1)
    bar.data.materials.append(bar_mat)
    curve = bpy.data.curves.new("BugText", type="FONT")
    curve.body = text
    curve.size = 0.22
    curve.align_x = "LEFT"
    txt = bpy.data.objects.new("BugLabel", curve)
    link_object(txt)
    txt.location = Vector((-4.8, -4.0, 4.55))
    txt.rotation_euler = Euler((math.radians(90), 0, 0))
    txt.data.materials.append(make_flat_material("bug_text", (1, 1, 1, 1)))


def ensure_caption(text: str, frame_start: int, frame_end: int) -> None:
    remove_objects(("caption",))
    curve = bpy.data.curves.new("CaptionCurve", type="FONT")
    curve.body = text
    curve.size = 0.35
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new("Caption", curve)
    link_object(obj)
    obj.location = Vector((0, 0, 4.8))
    obj.rotation_euler = Euler((math.radians(90), 0, 0))
    obj.data.materials.append(make_flat_material("caption_mat", (0.05, 0.05, 0.05, 1.0)))
    obj.hide_render = True
    obj.keyframe_insert(data_path="hide_render", frame=frame_start - 1)
    obj.hide_render = False
    obj.keyframe_insert(data_path="hide_render", frame=frame_start)
    obj.keyframe_insert(data_path="hide_render", frame=frame_end)
    obj.hide_render = True
    obj.keyframe_insert(data_path="hide_render", frame=frame_end + 1)


def animate_camera_keyframes(cam: bpy.types.Object, keyframes: List[Tuple[int, Vector, Euler]]) -> None:
    for frame, loc, rot in keyframes:
        cam.location = loc
        cam.rotation_euler = rot
        keyframe_loc_rot(cam, frame)


def prepare_fresh_scene() -> None:
    clear_scene_animation()
    clear_scene()


def render_scene_frames(scene_id: str, frames: Dict[str, int], out_base: Path) -> List[Path]:
    out_dir = out_base / f"scene_{scene_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    saved: List[Path] = []
    for label, frame in frames.items():
        scene.frame_set(frame)
        path = out_dir / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        saved.append(path)
        print(f"Rendered scene {scene_id} frame {frame} -> {path}")
    return saved
