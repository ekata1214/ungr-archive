# SPDX-License-Identifier: MIT
"""サッカーゴール — 参考画像風（斜め支柱 + フレームに固定されたネット）"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

_SCALE = 2.5
GOAL_INNER_W = 7.32 * _SCALE
GOAL_H = 2.44 * _SCALE
POST_R = 0.055 * _SCALE
NET_DEPTH = 2.0 * _SCALE
GROUND_Z = POST_R * 0.85
NET_INSET = POST_R * 1.1  # ポスト内側にネットを付ける


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
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.95, 0.96, 0.98, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
    bsdf.inputs["Metallic"].default_value = 0.0
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
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


def _lerp(a: Vector, b: Vector, t: float) -> Vector:
    return a + (b - a) * t


def _sag(u: float, v: float, amount: float, axis: str, inward: float) -> Vector:
    """中央にたるみを加えるオフセット"""
    f = math.sin(u * math.pi) * math.sin(v * math.pi)
    if axis == "x":
        return Vector((inward * f * amount, 0, 0))
    if axis == "y":
        return Vector((0, inward * f * amount, 0))
    return Vector((0, 0, -f * amount))


def _make_net_surface(
    parent: bpy.types.Object,
    name: str,
    mat: bpy.types.Material,
    corners: tuple[Vector, Vector, Vector, Vector],
    nu: int,
    nv: int,
    sag_axis: str = "none",
    sag_amount: float = 0.0,
    sag_inward: float = 1.0,
) -> bpy.types.Object:
    """
    4隅を結ぶネット面（BL, BR, TR, TL）。
    面 + ワイヤーフレームで格子状に表示。
    """
    bl, br, tr, tl = corners
    verts: list[Vector] = []
    faces: list[tuple[int, ...]] = []

    for j in range(nv + 1):
        v = j / nv
        left = _lerp(bl, tl, v)
        right = _lerp(br, tr, v)
        row: list[int] = []
        for i in range(nu + 1):
            u = i / nu
            p = _lerp(left, right, u)
            if sag_axis != "none":
                p += _sag(u, v, sag_amount, sag_axis, sag_inward)
            verts.append(p)
            row.append(len(verts) - 1)
        if j == 0:
            grid = [row]
        else:
            grid.append(row)
            for i in range(nu):
                faces.append((grid[j - 1][i], grid[j - 1][i + 1], grid[j][i + 1], grid[j][i]))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)

    subdiv = obj.modifiers.new("Subdiv", "SUBSURF")
    subdiv.levels = 2
    subdiv.render_levels = 2
    wf = obj.modifiers.new("Wireframe", "WIREFRAME")
    wf.thickness = 0.035
    wf.use_replace = True
    wf.use_boundary = True
    return obj


def _make_net_triangle(
    parent: bpy.types.Object,
    name: str,
    mat: bpy.types.Material,
    c_bl: Vector,
    c_br: Vector,
    c_top: Vector,
    nu: int,
    nv: int,
    sag_axis: str = "y",
    sag_amount: float = 0.0,
    sag_inward: float = 1.0,
) -> bpy.types.Object:
    """底辺 bl-br、頂点 top の三角形ネット"""
    verts: list[Vector] = []
    faces: list[tuple[int, ...]] = []
    grid: list[list[int]] = []

    for j in range(nv + 1):
        v = j / nv
        row: list[int] = []
        left = _lerp(c_bl, c_top, v)
        right = _lerp(c_br, c_top, v)
        cols = max(2, int(round(nu * (1.0 - v * 0.85))))
        for i in range(cols + 1):
            u = i / cols
            p = _lerp(left, right, u)
            if sag_axis != "none":
                p += _sag(u, v, sag_amount, sag_axis, sag_inward)
            verts.append(p)
            row.append(len(verts) - 1)
        grid.append(row)

    for j in range(1, len(grid)):
        for i in range(len(grid[j]) - 1):
            a, b = grid[j - 1][i], grid[j - 1][min(i + 1, len(grid[j - 1]) - 1)]
            c, d = grid[j][i + 1], grid[j][i]
            if a != b:
                faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    subdiv = obj.modifiers.new("Subdiv", "SUBSURF")
    subdiv.levels = 2
    wf = obj.modifiers.new("Wireframe", "WIREFRAME")
    wf.thickness = 0.035
    wf.use_replace = True
    return obj


def _build_attached_net(
    parent: bpy.types.Object,
    name: str,
    half_w: float,
    height: float,
    back_x: float,
    mat: bpy.types.Material,
) -> None:
    """フレームの柱・バー・斜め支柱にぴったり接続したネット"""
    hw = half_w - NET_INSET
    gz = GROUND_Z
    gh = GOAL_H
    inward = -1.0 if back_x < 0 else 1.0  # フィールド側へたるむ向き
    sag_d = abs(back_x) * 0.18
    sag_top = height * 0.14

    # 背面（奥の地面バー上端〜クロスバー高さ、奥バーに固定）
    _make_net_surface(
        parent, f"{name}_Back", mat,
        corners=(
            Vector((back_x, -hw, gz)),
            Vector((back_x, hw, gz)),
            Vector((back_x, hw, gh)),
            Vector((back_x, -hw, gh)),
        ),
        nu=18, nv=12,
        sag_axis="x", sag_amount=sag_d, sag_inward=inward,
    )

    # 天面（クロスバー前面〜奥上、たるみ）
    _make_net_surface(
        parent, f"{name}_Top", mat,
        corners=(
            Vector((0, -hw, gh)),
            Vector((0, hw, gh)),
            Vector((back_x, hw, gh)),
            Vector((back_x, -hw, gh)),
        ),
        nu=16, nv=14,
        sag_axis="z", sag_amount=sag_top, sag_inward=1.0,
    )

    # 左側面（前柱・奥地面・斜め支柱の三角形に沿う）
    _make_net_triangle(
        parent, f"{name}_SideL", mat,
        c_bl=Vector((0, -hw, gz)),
        c_br=Vector((back_x, -hw, gz)),
        c_top=Vector((0, -hw, gh)),
        nu=14, nv=10,
        sag_axis="y", sag_amount=sag_d * 0.5, sag_inward=1.0,
    )

    # 右側面
    _make_net_triangle(
        parent, f"{name}_SideR", mat,
        c_bl=Vector((0, hw, gz)),
        c_br=Vector((back_x, hw, gz)),
        c_top=Vector((0, hw, gh)),
        nu=14, nv=10,
        sag_axis="y", sag_amount=sag_d * 0.5, sag_inward=-1.0,
    )


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

    _cylinder_between(root, f"Goal_{side}_PostL", fl, tl, POST_R, post_mat)
    _cylinder_between(root, f"Goal_{side}_PostR", fr, tr, POST_R, post_mat)
    _cylinder_between(root, f"Goal_{side}_Crossbar", tl, tr, POST_R * 0.95, post_mat)
    _cylinder_between(root, f"Goal_{side}_FrontGround", fl, fr, POST_R * 0.75, post_mat)
    _cylinder_between(root, f"Goal_{side}_BackGround", bl, br, POST_R * 0.75, post_mat)
    _cylinder_between(root, f"Goal_{side}_StrutL", tl, bl, POST_R * 0.82, post_mat)
    _cylinder_between(root, f"Goal_{side}_StrutR", tr, br, POST_R * 0.82, post_mat)

    _build_attached_net(root, f"Goal_{side}_Net", half_w, GOAL_H, back_x, net_mat)

    return root


def build_both_goals(half_pitch_length: float) -> None:
    post_mat = make_post_material("GoalPost")
    net_mat = make_net_material("GoalNet")
    build_goal(-half_pitch_length, "L", post_mat, net_mat)
    build_goal(half_pitch_length, "R", post_mat, net_mat)
    print(f"Goals: frame + attached net panels  (W={GOAL_INNER_W:.1f} H={GOAL_H:.1f})")
