# SPDX-License-Identifier: MIT
"""サッカーゴール — 参考画像風（斜め支柱 + たるんだネット）"""

from __future__ import annotations

import math

import bpy
from mathutils import Euler, Vector

_SCALE = 2.5
GOAL_INNER_W = 7.32 * _SCALE
GOAL_H = 2.44 * _SCALE
POST_R = 0.055 * _SCALE
NET_DEPTH = 2.0 * _SCALE
GROUND_Z = POST_R * 0.85


def make_post_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.22
    bsdf.inputs["Metallic"].default_value = 0.12
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec:
        spec.default_value = 0.35
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_net_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.92, 0.94, 0.96, 1.0)
    emit.inputs["Strength"].default_value = 0.85
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def _cylinder_between(
    parent: bpy.types.Object,
    name: str,
    a: Vector,
    b: Vector,
    radius: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    vec = b - a
    length = vec.length
    if length < 1e-6:
        return parent
    mid = (a + b) / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    obj.parent = parent
    obj.location = mid
    obj.rotation_euler = vec.to_track_quat("Z", "Y").to_euler()
    return obj


def _sag_factor(u: float, v: float) -> float:
    """中央ほどたるむ（0〜1）"""
    return math.sin(u * math.pi) * math.sin(v * math.pi)


def _build_draped_net(
    parent: bpy.types.Object,
    name: str,
    half_w: float,
    height: float,
    depth: float,
    back_x: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    """背面・天面・側面のたるんだ四角メッシュネット"""
    segs_y = 22
    segs_z = 14
    segs_x = 14
    sag_strength = depth * 0.22
    top_sag = height * 0.12

    verts: list[Vector] = []
    edges: list[tuple[int, int]] = []

    def add_v(x: float, y: float, z: float) -> int:
        verts.append(Vector((x, y, z)))
        return len(verts) - 1

    def grid_edges(row_major: list[list[int]], sx: int, sy: int) -> None:
        for iy in range(sy):
            for ix in range(sx):
                i = row_major[iy][ix]
                if ix + 1 < sx + 1:
                    edges.append((i, row_major[iy][ix + 1]))
                if iy + 1 < sy + 1:
                    edges.append((i, row_major[iy + 1][ix]))

    # --- 背面 ---
    back_grid: list[list[int]] = []
    for iz in range(segs_z + 1):
        row = []
        tz = iz / segs_z
        z = tz * height
        for iy in range(segs_y + 1):
            ty = iy / segs_y
            y = (ty - 0.5) * 2 * half_w
            sag = sag_strength * _sag_factor(ty, tz) * 0.65
            x = back_x + sag  # フィールド側へたるむ
            row.append(add_v(x, y, z))
        back_grid.append(row)
    grid_edges(back_grid, segs_y, segs_z)

    # --- 天面 ---
    top_grid: list[list[int]] = []
    for iy in range(segs_y + 1):
        row = []
        ty = iy / segs_y
        y = (ty - 0.5) * 2 * half_w
        for ix in range(segs_x + 1):
            tx = ix / segs_x
            x = tx * back_x
            sag_z = top_sag * (_sag_factor(tx, ty) * 0.8 + 0.2 * tx)
            z = height - sag_z
            row.append(add_v(x, y, z))
        top_grid.append(row)
    grid_edges(top_grid, segs_x, segs_y)

    # --- 左側面 ---
    side_l: list[list[int]] = []
    for iz in range(segs_z + 1):
        row = []
        tz = iz / segs_z
        z = tz * height
        for ix in range(segs_x + 1):
            tx = ix / segs_x
            x = tx * back_x
            sag_y = sag_strength * 0.35 * _sag_factor(tx, tz)
            y = -half_w + sag_y
            row.append(add_v(x, y, z))
        side_l.append(row)
    grid_edges(side_l, segs_x, segs_z)

    # --- 右側面 ---
    side_r: list[list[int]] = []
    for iz in range(segs_z + 1):
        row = []
        tz = iz / segs_z
        z = tz * height
        for ix in range(segs_x + 1):
            tx = ix / segs_x
            x = tx * back_x
            sag_y = sag_strength * 0.35 * _sag_factor(tx, tz)
            y = half_w - sag_y
            row.append(add_v(x, y, z))
        side_r.append(row)
    grid_edges(side_r, segs_x, segs_z)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)

    # 細い円柱風メッシュ（Skinの代わり — バッチ処理で安定）
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.affect = "EDGES"
    bevel.width = 0.022
    bevel.segments = 2
    return obj


def build_goal(goalline_x: float, side: str, post_mat, net_mat) -> bpy.types.Object:
    root = bpy.data.objects.new(f"Goal_{side}", None)
    bpy.context.collection.objects.link(root)
    root.location = Vector((goalline_x, 0, 0))

    half_w = GOAL_INNER_W / 2
    outward = -1.0 if side == "L" else 1.0
    back_x = outward * NET_DEPTH

    fl = Vector((0, -half_w, GROUND_Z))
    fr = Vector((0, half_w, GROUND_Z))
    tl = Vector((0, -half_w, GOAL_H))
    tr = Vector((0, half_w, GOAL_H))
    bl = Vector((back_x, -half_w, GROUND_Z))
    br = Vector((back_x, half_w, GROUND_Z))

    # 正面フレーム
    _cylinder_between(root, f"Goal_{side}_PostL", fl, tl, POST_R, post_mat)
    _cylinder_between(root, f"Goal_{side}_PostR", fr, tr, POST_R, post_mat)
    _cylinder_between(root, f"Goal_{side}_Crossbar", tl, tr, POST_R * 0.95, post_mat)
    _cylinder_between(root, f"Goal_{side}_FrontGround", fl, fr, POST_R * 0.75, post_mat)

    # 背面地面バー
    _cylinder_between(root, f"Goal_{side}_BackGround", bl, br, POST_R * 0.75, post_mat)

    # 斜め支柱（参考画像の三角形シルエット）
    _cylinder_between(root, f"Goal_{side}_StrutL", tl, bl, POST_R * 0.82, post_mat)
    _cylinder_between(root, f"Goal_{side}_StrutR", tr, br, POST_R * 0.82, post_mat)

    # たるんだネット
    _build_draped_net(root, f"Goal_{side}_Net", half_w, GOAL_H, NET_DEPTH, back_x, net_mat)

    return root


def build_both_goals(half_pitch_length: float) -> None:
    post_mat = make_post_material("GoalPost")
    net_mat = make_net_material("GoalNet")
    build_goal(-half_pitch_length, "L", post_mat, net_mat)
    build_goal(half_pitch_length, "R", post_mat, net_mat)
    print(f"Goals: classic frame + draped net  (W={GOAL_INNER_W:.1f} H={GOAL_H:.1f})")
