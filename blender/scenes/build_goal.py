# SPDX-License-Identifier: MIT
"""サッカーゴールモデル — 両端配置用"""

from __future__ import annotations

import math
from typing import Optional

import bpy
from mathutils import Euler, Vector

# FIFA寸法 × フィールドと同じスケール
_SCALE = 2.5
GOAL_INNER_W = 7.32 * _SCALE      # 門幅 18.3m
GOAL_H = 2.44 * _SCALE            # 門高 6.1m
POST_R = 0.07 * _SCALE            # ポスト半径
POST_R_TOP = POST_R * 0.88
NET_DEPTH = 2.4 * _SCALE          # ネット奥行き
BACK_BAR_H = 0.06 * _SCALE


def make_post_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.94, 0.94, 0.95, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.28
    bsdf.inputs["Metallic"].default_value = 0.35
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec:
        spec.default_value = 0.45
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_net_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.88, 0.90, 0.92, 1.0)
    bsdf.inputs["Alpha"].default_value = 0.42
    bsdf.inputs["Roughness"].default_value = 0.65
    bsdf.inputs["Metallic"].default_value = 0.0
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _link(obj: bpy.types.Object, parent: bpy.types.Object) -> bpy.types.Object:
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def _add_cyl(
    name: str,
    radius: float,
    depth: float,
    loc: Vector,
    rot: Euler,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj) if obj.name not in bpy.context.collection.objects else None
    obj.parent = parent
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def _create_net_mesh(
    name: str,
    width: float,
    height: float,
    depth: float,
    outward: float,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
) -> None:
    """ネット — ワイヤーフレームパネル（背面・側面・天面）"""
    back_x = outward * depth

    def panel(pname: str, loc: Vector, rot: Euler, sx: float, sy: float) -> None:
        bpy.ops.mesh.primitive_plane_add(size=1)
        p = bpy.context.active_object
        p.name = f"{name}_{pname}"
        p.parent = parent
        p.location = loc
        p.rotation_euler = rot
        p.scale = (sx / 2, sy / 2, 1)
        p.data.materials.append(mat)
        subdiv = p.modifiers.new("Subdiv", "SUBSURF")
        subdiv.levels = 3
        wf = p.modifiers.new("Wireframe", "WIREFRAME")
        wf.thickness = 0.03
        wf.use_replace = True

    # 背面
    panel("Back", Vector((back_x, 0, height / 2)), Euler((0, math.pi / 2, 0)), depth, height)
    # 側面
    panel("SideL", Vector((back_x / 2, -width / 2, height / 2)), Euler((0, 0, math.pi / 2)), depth, height)
    panel("SideR", Vector((back_x / 2, width / 2, height / 2)), Euler((0, 0, math.pi / 2)), depth, height)
    # 天面
    panel("Top", Vector((back_x / 2, 0, height)), Euler((math.pi / 2, 0, 0)), depth, width)


def build_goal(goalline_x: float, side: str, post_mat, net_mat) -> bpy.types.Object:
    """
    ゴールをゴールライン上に配置。
    side='L': 左ゴール（ネットはフィールド外＝-X側）
    side='R': 右ゴール（ネットは+X側）
    """
    root = bpy.data.objects.new(f"Goal_{side}", None)
    bpy.context.collection.objects.link(root)
    root.location = Vector((goalline_x, 0, 0))

    half_w = GOAL_INNER_W / 2
    outward = -1.0 if side == "L" else 1.0

    # --- 正面フレーム（ゴールライン上）---
    for label, y in (("PostL", -half_w), ("PostR", half_w)):
        _add_cyl(
            f"Goal_{side}_{label}",
            POST_R, GOAL_H,
            Vector((0, y, GOAL_H / 2)),
            Euler((0, 0, 0)),
            post_mat, root,
        )

    _add_cyl(
        f"Goal_{side}_Crossbar",
        POST_R_TOP, GOAL_INNER_W,
        Vector((0, 0, GOAL_H)),
        Euler((math.pi / 2, 0, 0)),
        post_mat, root,
    )

    # 地面バー（正面下部）
    _add_cyl(
        f"Goal_{side}_GroundBar",
        POST_R * 0.7, GOAL_INNER_W,
        Vector((0, 0, BACK_BAR_H / 2)),
        Euler((math.pi / 2, 0, 0)),
        post_mat, root,
    )

    # --- 奥フレーム ---
    back_x = outward * NET_DEPTH
    _add_cyl(
        f"Goal_{side}_BackBar",
        POST_R * 0.65, GOAL_INNER_W,
        Vector((back_x, 0, GOAL_H)),
        Euler((math.pi / 2, 0, 0)),
        post_mat, root,
    )
    _add_cyl(
        f"Goal_{side}_BackGround",
        POST_R * 0.55, GOAL_INNER_W,
        Vector((back_x, 0, BACK_BAR_H / 2)),
        Euler((math.pi / 2, 0, 0)),
        post_mat, root,
    )

    # 奥の支柱2本
    for label, y in (("BackPostL", -half_w), ("BackPostR", half_w)):
        _add_cyl(
            f"Goal_{side}_{label}",
            POST_R * 0.6, GOAL_H,
            Vector((back_x, y, GOAL_H / 2)),
            Euler((0, 0, 0)),
            post_mat, root,
        )

    # 屋根バー（上辺をつなぐ）
    _add_cyl(
        f"Goal_{side}_RoofBar",
        POST_R * 0.5, NET_DEPTH,
        Vector((back_x / 2, -half_w, GOAL_H)),
        Euler((0, math.pi / 2, 0)),
        post_mat, root,
    )
    _add_cyl(
        f"Goal_{side}_RoofBarR",
        POST_R * 0.5, NET_DEPTH,
        Vector((back_x / 2, half_w, GOAL_H)),
        Euler((0, math.pi / 2, 0)),
        post_mat, root,
    )

    # サイドの奥行きバー（四隅を接続）
    for label, y in (("SideTopL", -half_w), ("SideTopR", half_w)):
        _add_cyl(
            f"Goal_{side}_{label}",
            POST_R * 0.45, NET_DEPTH,
            Vector((back_x / 2, y, GOAL_H)),
            Euler((0, math.pi / 2, 0)),
            post_mat, root,
        )
    for label, y in (("SideBotL", -half_w), ("SideBotR", half_w)):
        _add_cyl(
            f"Goal_{side}_{label}",
            POST_R * 0.4, NET_DEPTH,
            Vector((back_x / 2, y, BACK_BAR_H)),
            Euler((0, math.pi / 2, 0)),
            post_mat, root,
        )

    # ネット
    _create_net_mesh(
        f"Goal_{side}_Net",
        GOAL_INNER_W * 0.96,
        GOAL_H * 0.96,
        NET_DEPTH,
        outward,
        net_mat,
        root,
    )

    return root


def build_both_goals(half_pitch_length: float) -> None:
    post_mat = make_post_material("GoalPost")
    net_mat = make_net_material("GoalNet")
    build_goal(-half_pitch_length, "L", post_mat, net_mat)
    build_goal(half_pitch_length, "R", post_mat, net_mat)
    print(f"Goals placed at x=±{half_pitch_length:.1f}  (W={GOAL_INNER_W:.1f} H={GOAL_H:.1f})")
