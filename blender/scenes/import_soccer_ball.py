# SPDX-License-Identifier: MIT
"""サッカーボール — 外部フリー素材 (gitdolucas/sport-assets MIT)"""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector

ASSET_GLB = Path("/workspace/blender/assets/third_party/soccer_ball/Futbol.glb")
MESH_NAME = "soccerV2"
BALL_OBJECT_NAME = "Ball"


def _remove_ball_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.name == BALL_OBJECT_NAME or obj.name == MESH_NAME:
            bpy.data.objects.remove(obj, do_unlink=True)


def _tune_materials() -> None:
    for mat in bpy.data.materials:
        if not mat.name.startswith("soccer_"):
            continue
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            continue
        if "branco" in mat.name or "white" in mat.name.lower():
            bsdf.inputs["Base Color"].default_value = (0.97, 0.97, 0.97, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.42
        elif "preto" in mat.name or "black" in mat.name.lower():
            bsdf.inputs["Base Color"].default_value = (0.03, 0.03, 0.03, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.45
        spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
        if spec:
            spec.default_value = 0.28


def import_soccer_ball(radius: float, location: Vector | None = None) -> bpy.types.Object:
    """GLB からサッカーボールを読み込み、指定半径で配置する"""
    if location is None:
        location = Vector((0.0, 0.0, radius))

    if not ASSET_GLB.exists():
        raise FileNotFoundError(f"Missing soccer ball asset: {ASSET_GLB}")

    _remove_ball_objects()

    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(ASSET_GLB))
    imported = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]

    ball_mesh = bpy.data.objects.get(MESH_NAME)
    if not ball_mesh or ball_mesh.type != "MESH":
        raise RuntimeError(f"Expected mesh '{MESH_NAME}' in {ASSET_GLB.name}")

    for obj in imported:
        if obj != ball_mesh:
            bpy.data.objects.remove(obj, do_unlink=True)

    ball_mesh.name = BALL_OBJECT_NAME
    ball_mesh.location = (0.0, 0.0, 0.0)
    ball_mesh.rotation_euler = (0.0, 0.0, 0.0)
    ball_mesh.scale = (1.0, 1.0, 1.0)

    bpy.context.view_layer.objects.active = ball_mesh
    ball_mesh.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ball_mesh.select_set(False)

    half_size = max(ball_mesh.dimensions.x, ball_mesh.dimensions.y, ball_mesh.dimensions.z) / 2.0
    if half_size < 1e-6:
        raise RuntimeError("Soccer ball mesh has zero size")
    uniform = radius / half_size
    ball_mesh.scale = (uniform, uniform, uniform)
    ball_mesh.location = location

    _tune_materials()

    bpy.context.view_layer.objects.active = ball_mesh
    ball_mesh.select_set(True)
    bpy.ops.object.shade_smooth()
    ball_mesh.select_set(False)

    return ball_mesh
