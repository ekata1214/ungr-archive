# SPDX-License-Identifier: MIT
"""再現CGメーカー風 人型キャラ（赤・青）— フィールドスケール対応"""

from __future__ import annotations

import math
from typing import Dict, Literal, Tuple

import bpy
from mathutils import Euler, Vector

from news_cg_common import StickFigure, add_empty, make_flat_material

_SCALE = 2.5
S = _SCALE

TEAM_BLUE = (0.10, 0.40, 0.90, 1.0)
TEAM_RED = (0.88, 0.12, 0.20, 1.0)

BodyType = Literal["male", "female"]


def _make_cg_material(name: str, color: Tuple[float, float, float, float]) -> bpy.types.Material:
    mat = make_flat_material(name, color)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Roughness"].default_value = 0.94
        spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
        if spec:
            spec.default_value = 0.03
    return mat


def _smooth(obj: bpy.types.Object, subdiv: int = 0) -> None:
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if subdiv > 0:
        mod = obj.modifiers.new("Subdiv", "SUBSURF")
        mod.levels = subdiv
        mod.render_levels = subdiv


def _parent_keep_world(obj: bpy.types.Object, parent: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def _parent_local(
    obj: bpy.types.Object,
    parent: bpy.types.Object,
    location: Vector,
    rotation: Euler = Euler((0, 0, 0)),
) -> None:
    obj.parent = parent
    obj.location = location
    obj.rotation_euler = rotation


def _add_box(
    name: str,
    size: Vector,
    location: Vector,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
    rotation: Euler = Euler((0, 0, 0)),
    subdiv: int = 0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0), rotation=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size.x / 2, size.y / 2, size.z / 2)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    _smooth(obj, subdiv)
    _parent_local(obj, parent, location, rotation)
    return obj


def _add_capsule(
    name: str,
    radius: float,
    length: float,
    location: Vector,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
    rotation: Euler = Euler((0, 0, 0)),
    subdiv: int = 1,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=14, radius=radius, depth=length, location=(0, 0, 0), rotation=(0, 0, 0),
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    _smooth(obj, subdiv)
    _parent_local(obj, parent, location, rotation)
    return obj


def _add_sphere(
    name: str,
    radius: float,
    location: Vector,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
    scale: Vector | None = None,
    subdiv: int = 1,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=18, ring_count=12, radius=radius, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    if scale:
        obj.scale = scale
        bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    _smooth(obj, subdiv)
    _parent_local(obj, parent, location)
    return obj


def _build_head(
    name: str,
    mat: bpy.types.Material,
    joint: bpy.types.Object,
    body_type: BodyType,
) -> None:
    r = 0.108 * S
    _add_sphere(f"{name}_head", r, Vector((0, 0, 0.10 * S)), mat, joint, Vector((0.94, 1.0, 1.06)), subdiv=1)
    # 鼻（前に出る）
    _add_box(
        f"{name}_nose",
        Vector((0.032 * S, 0.065 * S, 0.038 * S)),
        Vector((0, 0.10 * S, 0.06 * S)),
        mat, joint, subdiv=0,
    )
    # 眉
    _add_box(
        f"{name}_brow",
        Vector((0.12 * S, 0.028 * S, 0.024 * S)),
        Vector((0, 0.085 * S, 0.13 * S)),
        mat, joint, subdiv=0,
    )
    # 顎〜口
    _add_box(
        f"{name}_mouth",
        Vector((0.055 * S, 0.03 * S, 0.018 * S)),
        Vector((0, 0.09 * S, 0.0)),
        mat, joint, subdiv=0,
    )
    if body_type == "female":
        _add_sphere(
            f"{name}_hair_vol",
            r * 0.95,
            Vector((0, -0.035 * S, 0.12 * S)),
            mat, joint, Vector((1.02, 0.90, 1.02)), subdiv=1,
        )


def _build_torso_clothing(
    name: str,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
    body_type: BodyType,
) -> None:
    if body_type == "male":
        # 半袖シャツ（肩幅広め）
        _add_box(
            f"{name}_shirt",
            Vector((0.50 * S, 0.14 * S, 0.32 * S)),
            Vector((0, 0, 1.04 * S)),
            mat, parent, subdiv=1,
        )
        # 襟元
        _add_box(
            f"{name}_collar",
            Vector((0.18 * S, 0.06 * S, 0.04 * S)),
            Vector((0, 0.04 * S, 1.22 * S)),
            mat, parent, subdiv=0,
        )
        for side, tag in ((-1, "L"), (1, "R")):
            _add_capsule(
                f"{name}_sleeve_{tag}",
                0.048 * S, 0.12 * S,
                Vector((side * 0.24 * S, 0, 1.10 * S)),
                mat, parent, Euler((0, math.pi / 2, 0)), subdiv=1,
            )
        hip_w = 0.44 * S
    else:
        # 女性：トップス＋くびれ
        _add_box(
            f"{name}_top",
            Vector((0.40 * S, 0.12 * S, 0.30 * S)),
            Vector((0, 0, 1.06 * S)),
            mat, parent, subdiv=1,
        )
        _add_box(
            f"{name}_waist",
            Vector((0.32 * S, 0.10 * S, 0.12 * S)),
            Vector((0, 0, 0.86 * S)),
            mat, parent, subdiv=1,
        )
        hip_w = 0.38 * S

    _add_box(
        f"{name}_pants",
        Vector((hip_w, 0.13 * S, 0.24 * S)),
        Vector((0, 0, 0.70 * S)),
        mat, parent, subdiv=1,
    )


def _build_limb(
    name: str,
    side: str,
    axis_sign: float,
    is_arm: bool,
    mat: bpy.types.Material,
    root: bpy.types.Object,
    parts: Dict[str, bpy.types.Object],
) -> None:
    upper_len = (0.27 if is_arm else 0.40) * S
    lower_len = (0.25 if is_arm else 0.42) * S
    upper_r = (0.050 if is_arm else 0.070) * S
    lower_r = (0.040 if is_arm else 0.058) * S

    x = axis_sign * ((0.25 if is_arm else 0.11) * S)
    z = (1.06 if is_arm else 0.60) * S

    upper_joint = add_empty(f"{name}_{side}_upper_joint", Vector((x, 0, z)), root)
    parts[f"{side}_upper_joint"] = upper_joint

    _add_capsule(
        f"{name}_{side}_upper",
        upper_r, upper_len,
        Vector((0, 0, -upper_len / 2)),
        mat, upper_joint, Euler((0.12 * axis_sign, 0, 0)), subdiv=1,
    )

    lower_joint = add_empty(f"{name}_{side}_lower_joint", Vector((0, 0, -upper_len)), upper_joint)
    parts[f"{side}_lower_joint"] = lower_joint

    _add_capsule(
        f"{name}_{side}_lower",
        lower_r, lower_len,
        Vector((0, 0, -lower_len / 2)),
        mat, lower_joint, subdiv=1,
    )

    if is_arm:
        _add_box(
            f"{name}_{side}_hand",
            Vector((0.05 * S, 0.035 * S, 0.022 * S)),
            Vector((0, 0, -lower_len)),
            mat, lower_joint, subdiv=0,
        )
    else:
        _add_box(
            f"{name}_{side}_shoe",
            Vector((0.075 * S, 0.15 * S, 0.045 * S)),
            Vector((0, 0.05 * S, -lower_len)),
            mat, lower_joint, subdiv=0,
        )


def build_stick_figure(
    name: str,
    color: Tuple[float, float, float, float],
    location: Vector,
    facing_yaw: float = 0.0,
    body_type: BodyType = "male",
) -> StickFigure:
    """再現CGメーカー風の立体人型。関節は Empty でポーズ可能。"""
    mat = _make_cg_material(f"{name}_mat", color)
    parts: Dict[str, bpy.types.Object] = {}

    root = add_empty(f"{name}_root", Vector((location.x, location.y, location.z)))
    root.rotation_euler = Euler((0, 0, facing_yaw))

    head_joint = add_empty(f"{name}_head_joint", Vector((0, 0, 1.36 * S)), root)
    parts["head_joint"] = head_joint
    _build_head(name, mat, head_joint, body_type)
    _build_torso_clothing(name, mat, root, body_type)

    _build_limb(name, "arm_l", -1.0, True, mat, root, parts)
    _build_limb(name, "arm_r", 1.0, True, mat, root, parts)
    _build_limb(name, "leg_l", -1.0, False, mat, root, parts)
    _build_limb(name, "leg_r", 1.0, False, mat, root, parts)

    return StickFigure(root=root, parts=parts)


def apply_idle_pose(fig: StickFigure) -> None:
    fig.parts["arm_l_upper_joint"].rotation_euler = Euler((0.40, 0, -0.22))
    fig.parts["arm_l_lower_joint"].rotation_euler = Euler((0.18, 0, 0))
    fig.parts["arm_r_upper_joint"].rotation_euler = Euler((0.10, 0, 0.28))
    fig.parts["arm_r_lower_joint"].rotation_euler = Euler((0.25, 0, 0))
    fig.parts["leg_l_upper_joint"].rotation_euler = Euler((-0.06, 0, 0.03))
    fig.parts["leg_l_lower_joint"].rotation_euler = Euler((0.10, 0, 0))
    fig.parts["leg_r_upper_joint"].rotation_euler = Euler((0.12, 0, -0.02))
    fig.parts["leg_r_lower_joint"].rotation_euler = Euler((-0.05, 0, 0))


def build_demo_players() -> Tuple[StickFigure, StickFigure]:
    """青（男性）・赤（女性）を並べて配置 — アプリ参考画像風。"""
    blue = build_stick_figure(
        "Player_Blue", TEAM_BLUE, Vector((-3.5, 0, 0)),
        facing_yaw=0.0, body_type="male",
    )
    apply_idle_pose(blue)

    red = build_stick_figure(
        "Player_Red", TEAM_RED, Vector((3.5, 0, 0)),
        facing_yaw=0.0, body_type="female",
    )
    apply_idle_pose(red)

    print(f"Players: 再現CG風 humanoids blue(male) + red(female)  scale={S}")
    return blue, red
