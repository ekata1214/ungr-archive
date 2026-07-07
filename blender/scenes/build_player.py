# SPDX-License-Identifier: MIT
"""ニュースCG風 棒人間（赤・青）— フィールドスケール対応"""

from __future__ import annotations

import math
from typing import Dict, Tuple

import bpy
from mathutils import Euler, Vector

from news_cg_common import StickFigure, add_cylinder, add_empty, add_sphere, make_flat_material

_SCALE = 2.5
S = _SCALE

TEAM_BLUE = (0.15, 0.45, 0.95, 1.0)
TEAM_RED = (0.92, 0.18, 0.15, 1.0)

# 足裏が z=0 に来るよう root を少し上げる（脚の長さから算出）
_FOOT_CLEARANCE = 0.31 * S


def build_stick_figure(
    name: str,
    color: Tuple[float, float, float, float],
    location: Vector,
    facing_yaw: float = 0.0,
) -> StickFigure:
    """フィールドスケールの棒人間。頭＋胴＋四肢は円柱、関節は Empty。"""
    mat = make_flat_material(f"{name}_mat", color)
    parts: Dict[str, bpy.types.Object] = {}

    root_loc = Vector((location.x, location.y, location.z + _FOOT_CLEARANCE))
    root = add_empty(f"{name}_root", root_loc)
    root.rotation_euler = Euler((0, 0, facing_yaw))

    add_cylinder(f"{name}_torso", 0.11 * S, 0.55 * S, Vector((0, 0, 0.95 * S)), mat, root)

    head_joint = add_empty(f"{name}_head_joint", Vector((0, 0, 1.35 * S)), root)
    parts["head_joint"] = head_joint
    add_sphere(f"{name}_head", 0.18 * S, Vector((0, 0, 0.18 * S)), mat, head_joint)

    def limb(side: str, axis_sign: float, is_arm: bool) -> None:
        upper_len = (0.38 if is_arm else 0.42) * S
        lower_len = (0.38 if is_arm else 0.44) * S
        x = axis_sign * ((0.22 if is_arm else 0.10) * S)
        z = (1.15 if is_arm else 0.55) * S

        upper_joint = add_empty(f"{name}_{side}_upper_joint", Vector((x, 0, z)), root)
        parts[f"{side}_upper_joint"] = upper_joint
        add_cylinder(
            f"{name}_{side}_upper",
            0.05 * S,
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
            0.045 * S,
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


def apply_idle_pose(fig: StickFigure) -> None:
    """立ちポーズ — 軽く膝を曲げ、腕を少し開く。"""
    fig.parts["arm_l_upper_joint"].rotation_euler = Euler((0.55, 0, -0.35))
    fig.parts["arm_l_lower_joint"].rotation_euler = Euler((0.25, 0, 0))
    fig.parts["arm_r_upper_joint"].rotation_euler = Euler((0.15, 0, 0.45))
    fig.parts["arm_r_lower_joint"].rotation_euler = Euler((0.35, 0, 0))
    fig.parts["leg_l_upper_joint"].rotation_euler = Euler((-0.12, 0, 0.05))
    fig.parts["leg_l_lower_joint"].rotation_euler = Euler((0.18, 0, 0))
    fig.parts["leg_r_upper_joint"].rotation_euler = Euler((0.22, 0, -0.04))
    fig.parts["leg_r_lower_joint"].rotation_euler = Euler((-0.08, 0, 0))


def build_demo_players() -> Tuple[StickFigure, StickFigure]:
    """青1体・赤1体をセンターサークル付近に配置。"""
    blue = build_stick_figure("Player_Blue", TEAM_BLUE, Vector((-14.0, -6.0, 0)), facing_yaw=math.radians(28))
    apply_idle_pose(blue)

    red = build_stick_figure("Player_Red", TEAM_RED, Vector((14.0, 6.0, 0)), facing_yaw=math.radians(-152))
    apply_idle_pose(red)

    height = 1.71 * S
    print(f"Players: blue + red stick figures  (H≈{height:.1f}m at scale {S})")
    return blue, red
