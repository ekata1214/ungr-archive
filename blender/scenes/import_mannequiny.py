# SPDX-License-Identifier: MIT
"""Mannequiny (GDQuest) を .blend から読み込み、複製して配置する

Source asset:
- https://github.com/gdquest-demos/godot-3d-mannequin (CC-BY 4.0)
This repo keeps a local copy under `blender/assets/third_party/mannequiny/`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

import bpy
from mathutils import Euler, Vector

ASSET_PATH = Path("/workspace/blender/assets/third_party/mannequiny/mannequiny-0.4.0.blend")


def _ensure_loaded() -> Tuple[bpy.types.Object, bpy.types.Object]:
    """Returns (armature_obj, mesh_obj) from the asset, appended into current file.

    The asset contains only 2 objects and 1 collection, so we append objects directly.
    """
    # Asset object names (v0.4.0): armature=`root`, mesh=`body.001`
    arm = bpy.data.objects.get("root")
    mesh = bpy.data.objects.get("body.001")
    if arm and mesh:
        return arm, mesh

    if not ASSET_PATH.exists():
        raise FileNotFoundError(f"Missing Mannequiny asset: {ASSET_PATH}")

    with bpy.data.libraries.load(str(ASSET_PATH), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
        data_to.actions = list(data_from.actions)

    for obj in data_to.objects:
        if obj is None:
            continue
        if obj.name not in bpy.context.scene.collection.objects:
            bpy.context.collection.objects.link(obj)

    arm = bpy.data.objects.get("root")
    mesh = bpy.data.objects.get("body.001")
    if not arm or not mesh:
        raise RuntimeError("Failed to append Mannequiny objects (root/body.001 not found)")
    return arm, mesh


def _set_mesh_color(mesh_obj: bpy.types.Object, rgba) -> None:
    # Asset has materials; we override by setting a simple Principled color per material slot
    for mat in mesh_obj.data.materials:
        if not mat:
            continue
        _apply_principled_color(mat, rgba)


def _apply_principled_color(mat: bpy.types.Material, rgba) -> None:
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        try:
            bsdf.inputs["Alpha"].default_value = 1.0
        except Exception:
            pass
        bsdf.inputs["Roughness"].default_value = 0.85
        spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
        if spec:
            spec.default_value = 0.06
    mat.blend_method = "OPAQUE"


def set_mesh_split_vertical(
    mesh_obj: bpy.types.Object,
    upper_rgba,
    lower_rgba,
    z_cut: float = 0.42,
) -> None:
    """上半身 / 下半身で色分け（Mannequiny ローカルZ）"""
    mesh = mesh_obj.data
    mat_upper = bpy.data.materials.new(f"{mesh_obj.name}_upper")
    mat_lower = bpy.data.materials.new(f"{mesh_obj.name}_lower")
    _apply_principled_color(mat_upper, upper_rgba)
    _apply_principled_color(mat_lower, lower_rgba)
    mesh.materials.clear()
    mesh.materials.append(mat_upper)
    mesh.materials.append(mat_lower)
    for poly in mesh.polygons:
        zs = [mesh.vertices[v].co.z for v in poly.vertices]
        poly.material_index = 0 if (sum(zs) / len(zs)) >= z_cut else 1
    mesh.update()


def _mesh_child(arm: bpy.types.Object) -> bpy.types.Object:
    for ch in arm.children:
        if ch.type == "MESH":
            return ch
    raise RuntimeError(f"No mesh child on {arm.name}")


def _duplicate_character(
    base_arm: bpy.types.Object,
    base_mesh: bpy.types.Object,
    name: str,
    location: Vector,
    rotation: Euler,
    color_rgba,
) -> bpy.types.Object:
    """Duplicate armature + mesh so animations can differ per character."""
    root_empty = bpy.data.objects.new(f"{name}_Root", None)
    bpy.context.collection.objects.link(root_empty)
    root_empty.location = location
    root_empty.rotation_euler = rotation
    root_empty.scale = Vector((2.5, 2.5, 2.5))

    # Duplicate armature object & data
    arm = base_arm.copy()
    arm.data = base_arm.data.copy()
    arm.name = f"{name}_Armature"
    bpy.context.collection.objects.link(arm)
    arm.hide_viewport = False
    arm.hide_render = False
    arm.location = Vector((0, 0, 0))
    arm.rotation_euler = Euler((0, 0, 0))
    arm.scale = Vector((1, 1, 1))
    arm.parent = root_empty
    arm.matrix_parent_inverse = root_empty.matrix_world.inverted()

    # Duplicate mesh object; make mesh+materials unique per character (colors differ)
    mesh = base_mesh.copy()
    mesh.data = base_mesh.data.copy()
    mesh.name = f"{name}_Mesh"
    bpy.context.collection.objects.link(mesh)
    mesh.hide_viewport = False
    mesh.hide_render = False
    try:
        mesh.hide_set(False)
    except Exception:
        pass
    mesh.location = Vector((0, 0, 0))
    mesh.rotation_euler = Euler((0, 0, 0))
    mesh.scale = Vector((1, 1, 1))

    # Fix armature modifier to point to the duplicated armature
    for mod in mesh.modifiers:
        if mod.type == "ARMATURE":
            mod.object = arm

    # Parent mesh to armature
    mesh.parent = arm
    mesh.matrix_parent_inverse = arm.matrix_world.inverted()

    # Make materials unique too
    for i, mat in enumerate(list(mesh.data.materials)):
        if mat:
            mesh.data.materials[i] = mat.copy()

    _set_mesh_color(mesh, color_rgba)
    return arm


def assign_action(arm_obj: bpy.types.Object, action_name: str) -> None:
    action = bpy.data.actions.get(action_name)
    if not action:
        raise KeyError(f"Action not found: {action_name}")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action


def build_two_characters() -> Tuple[bpy.types.Object, bpy.types.Object]:
    base_arm, base_mesh = _ensure_loaded()

    # Hide the base imported ones (template)
    base_arm.hide_viewport = True
    base_arm.hide_render = True
    base_mesh.hide_viewport = True
    base_mesh.hide_render = True

    blue = _duplicate_character(
        base_arm,
        base_mesh,
        name="Player_Blue",
        location=Vector((-2.2, 0.0, 0)),
        rotation=Euler((0, 0, 0)),
        color_rgba=(0.12, 0.45, 0.95, 1.0),
    )
    red = _duplicate_character(
        base_arm,
        base_mesh,
        name="Player_Red",
        location=Vector((2.2, 0.0, 0)),
        rotation=Euler((0, 0, 0)),
        color_rgba=(0.92, 0.18, 0.15, 1.0),
    )

    # Default: blue runs, red kicks
    assign_action(blue, "run")
    assign_action(red, "fight_kick")

    print("Players: imported Mannequiny rig + animations (run, fight_kick)")
    return blue, red


def build_team(
    prefix: str,
    color_rgba,
    positions: Iterable[Vector],
    actions: List[str],
    facing_yaw: float = 0.0,
) -> List[bpy.types.Object]:
    """Build multiple characters, cycling through actions."""
    base_arm, base_mesh = _ensure_loaded()
    base_arm.hide_viewport = True
    base_arm.hide_render = True
    base_mesh.hide_viewport = True
    base_mesh.hide_render = True

    out: List[bpy.types.Object] = []
    actions_cycle = list(actions) if actions else ["idle"]
    for i, pos in enumerate(list(positions)):
        arm = _duplicate_character(
            base_arm,
            base_mesh,
            name=f"{prefix}_{i+1:02d}",
            location=pos,
            rotation=Euler((0, 0, facing_yaw)),
            color_rgba=color_rgba,
        )
        assign_action(arm, actions_cycle[i % len(actions_cycle)])
        out.append(arm)
    return out

