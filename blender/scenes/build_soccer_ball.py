# SPDX-License-Identifier: MIT
"""本物のサッカーボール — 截頭二十面体（12五角形 + 20六角形）"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import bpy
from mathutils import Vector

IcoVerts = List[Vector]
IcoFaces = List[Tuple[int, int, int]]


def _normalize(v: Vector) -> Vector:
    return v.normalized()


def _icosahedron() -> Tuple[IcoVerts, IcoFaces]:
    raw = [
        (0.0, 0.0, -1.0),
        (0.7236, -0.52572, -0.447215),
        (-0.276385, -0.85064, -0.447215),
        (-0.894425, 0.0, -0.447215),
        (-0.276385, 0.85064, -0.447215),
        (0.7236, 0.52572, -0.447215),
        (0.276385, -0.85064, 0.447215),
        (-0.7236, -0.52572, 0.447215),
        (-0.7236, 0.52572, 0.447215),
        (0.276385, 0.85064, 0.447215),
        (0.894425, 0.0, 0.447215),
        (0.0, 0.0, 1.0),
    ]
    verts = [_normalize(Vector(v)) for v in raw]
    faces = [
        (0, 1, 2), (1, 0, 5), (0, 2, 3), (0, 3, 4), (0, 4, 5),
        (1, 5, 10), (2, 1, 6), (3, 2, 7), (4, 3, 8), (5, 4, 9),
        (1, 10, 6), (2, 6, 7), (3, 7, 8), (4, 8, 9), (5, 9, 10),
        (6, 10, 11), (7, 6, 11), (8, 7, 11), (9, 8, 11), (10, 9, 11),
    ]
    return verts, faces


def _truncated_icosahedron(frac: float = 1.0 / 3.0) -> Tuple[List[Vector], List[List[int]], List[bool]]:
    """截頭二十面体 — pentagon=True / hexagon=False"""
    ico_v, ico_f = _icosahedron()
    edge_near: Dict[Tuple[int, int], Tuple[int, int]] = {}
    verts: List[Vector] = []

    def _edge_key(a: int, b: int) -> Tuple[int, int]:
        return (a, b) if a < b else (b, a)

    def _near_idx(a: int, b: int, from_a: bool) -> int:
        key = _edge_key(a, b)
        if key not in edge_near:
            va, vb = ico_v[key[0]], ico_v[key[1]]
            p_near_a = _normalize(va + (vb - va) * frac)
            p_near_b = _normalize(vb + (va - vb) * frac)
            edge_near[key] = (len(verts), len(verts) + 1)
            verts.extend([p_near_a, p_near_b])
        return edge_near[key][0 if from_a else 1]

    # 各二十面体の頂点 → 五角形
    neighbors: Dict[int, List[int]] = {i: [] for i in range(12)}
    for a, b, c in ico_f:
        for u, v in ((a, b), (b, a), (b, c), (c, b), (c, a), (a, c)):
            if v not in neighbors[u]:
                neighbors[u].append(v)

    def _sort_cyclic(vi: int, nbrs: List[int]) -> List[int]:
        center = ico_v[vi]
        n = center.normalized()
        ref = Vector((1.0, 0.0, 0.0)) if abs(n.x) < 0.9 else Vector((0.0, 1.0, 0.0))
        u = n.cross(ref).normalized()
        v = n.cross(u).normalized()

        def _angle(nb: int) -> float:
            d = ico_v[nb] - center
            return math.atan2(d.dot(v), d.dot(u))

        return sorted(nbrs, key=_angle)

    faces: List[List[int]] = []
    is_pent: List[bool] = []
    for vi, nbrs in neighbors.items():
        if len(nbrs) != 5:
            raise RuntimeError(f"icosa vertex {vi} has {len(nbrs)} neighbors")
        ring = [_near_idx(vi, nb, from_a=True) for nb in _sort_cyclic(vi, nbrs)]
        faces.append(ring)
        is_pent.append(True)

    # 各三角面 → 六角形
    for a, b, c in ico_f:
        hex_face = [
            _near_idx(a, b, from_a=True),
            _near_idx(a, b, from_a=False),
            _near_idx(b, c, from_a=True),
            _near_idx(b, c, from_a=False),
            _near_idx(c, a, from_a=True),
            _near_idx(c, a, from_a=False),
        ]
        faces.append(hex_face)
        is_pent.append(False)

    return verts, faces, is_pent


def _make_panel_material(name: str, color: Tuple[float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.38
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec:
        spec.default_value = 0.25
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def build_soccer_ball_mesh(
    name: str = "Ball",
    radius: float = 0.55,
    location: Vector | None = None,
) -> bpy.types.Object:
    """截頭二十面体メッシュのサッカーボールを生成"""
    if location is None:
        location = Vector((0, 0, radius))

    verts, faces, is_pent = _truncated_icosahedron()
    # 半径に合わせてスケール（截頭二十面体の外接球 ≈ 1.0）
    scale = radius / max(v.length for v in verts)
    verts = [v * scale for v in verts]

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location

    mat_white = _make_panel_material("BallPanelWhite", (0.96, 0.96, 0.96))
    mat_black = _make_panel_material("BallPanelBlack", (0.05, 0.05, 0.05))
    mesh.materials.append(mat_white)
    mesh.materials.append(mat_black)

    for i, pent in enumerate(is_pent):
        mesh.polygons[i].material_index = 1 if pent else 0

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)

    return obj
