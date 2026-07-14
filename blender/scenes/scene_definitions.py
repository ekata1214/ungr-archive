# SPDX-License-Identifier: MIT
"""台本順のシーン定義"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict

import bpy
from mathutils import Euler, Vector

from news_cg_common import (
    FRAME_END,
    StickFigure,
    animate_camera_keyframes,
    build_ball,
    build_camera_and_light,
    build_goal_and_wall,
    build_pitch,
    build_stick_figure,
    ensure_ball,
    ensure_camera,
    ensure_caption,
    ensure_title_bug,
    set_linear_interpolation,
    setup_render,
    TEAM_BLUE,
    TEAM_RED,
)


@dataclass
class SceneSpec:
    id: str
    title: str
    bug_text: str
    caption: str
    caption_start: int
    render_frames: Dict[str, int]
    apply: Callable[[], None]


def _deg(v: float) -> float:
    return math.radians(v)


# --- シーン01: フランス戦 鉄脚功 ---

def _animate_ball_france(ball: bpy.types.Object) -> None:
    for frame, pos in [
        (1, Vector((6.0, 1.5, 0.11))),
        (35, Vector((4.5, 0.8, 0.11))),
        (50, Vector((0.5, 0.2, 0.15))),
        (58, Vector((-1.0, 0.0, 0.3))),
        (75, Vector((-10.0, 0.0, 1.2))),
        (90, Vector((-19.2, 0.0, 1.0))),
        (FRAME_END, Vector((-19.2, 0.0, 0.11))),
    ]:
        ball.location = pos
        ball.keyframe_insert(data_path="location", frame=frame)


def _animate_mbappe(fig: StickFigure) -> None:
    fig.pose(1, Vector((7.0, 2.0, 0.0)), Euler((0, 0, _deg(200))), {
        "leg_l_upper_joint": Euler((_deg(-40), 0, 0)), "leg_r_upper_joint": Euler((_deg(35), 0, 0)),
        "leg_l_lower_joint": Euler((_deg(20), 0, 0)), "leg_r_lower_joint": Euler((_deg(-15), 0, 0)),
    })
    fig.pose(40, Vector((4.0, 1.0, 0.0)), Euler((0, 0, _deg(190))), {
        "leg_l_upper_joint": Euler((_deg(-55), 0, 0)), "leg_r_upper_joint": Euler((_deg(50), 0, 0)),
    })
    fig.pose(150, Vector((2.0, 0.3, 0.0)), Euler((0, 0, _deg(160))), {
        "head_joint": Euler((_deg(15), 0, 0)),
        "arm_l_upper_joint": Euler((_deg(-75), 0, _deg(-10))),
        "arm_r_upper_joint": Euler((_deg(-75), 0, _deg(10))),
        "arm_l_lower_joint": Euler((_deg(-50), 0, 0)), "arm_r_lower_joint": Euler((_deg(-50), 0, 0)),
    })
    fig.pose(FRAME_END, Vector((2.0, 0.3, 0.0)), Euler((0, 0, _deg(160))), {})


def _animate_iron_leg(fig: StickFigure) -> None:
    fig.pose(1, Vector((-0.5, -0.5, 0.0)), Euler((0, 0, _deg(95))), {
        "leg_l_upper_joint": Euler((_deg(-15), 0, 0)), "leg_r_upper_joint": Euler((_deg(10), 0, 0)),
    })
    fig.pose(50, Vector((0.0, 0.0, 0.0)), Euler((0, 0, _deg(100))), {
        "leg_r_upper_joint": Euler((_deg(85), 0, 0)), "leg_r_lower_joint": Euler((_deg(-5), 0, 0)),
        "arm_l_upper_joint": Euler((_deg(-50), 0, _deg(-20))), "arm_r_upper_joint": Euler((_deg(40), 0, _deg(30))),
    })
    fig.pose(65, Vector((0.2, 0.0, 0.0)), Euler((0, 0, _deg(85))), {
        "leg_r_upper_joint": Euler((_deg(110), 0, 0)), "arm_r_upper_joint": Euler((_deg(60), 0, _deg(35))),
    })
    fig.pose(FRAME_END, Vector((0.2, 0.0, 0.0)), Euler((0, 0, _deg(90))), {
        "leg_r_upper_joint": Euler((_deg(45), 0, 0)),
    })


def _camera_france(cam: bpy.types.Object) -> None:
    animate_camera_keyframes(cam, [
        (1, Vector((3.0, -8.0, 5.5)), Euler((_deg(62), 0, _deg(15)))),
        (58, Vector((0.5, -5.5, 4.5)), Euler((_deg(66), 0, _deg(8)))),
        (90, Vector((0.0, -6.0, 5.0)), Euler((_deg(63), 0, _deg(10)))),
        (FRAME_END, Vector((0.0, -6.0, 5.0)), Euler((_deg(63), 0, _deg(10)))),
    ])


def run_scene_01() -> None:
    setup_render()
    build_pitch()
    build_goal_and_wall()
    ball = ensure_ball()
    cam = ensure_camera()
    ensure_title_bug("再現CG  2026W杯 グループ初戦 vs フランス")
    ensure_caption("あれは人間じゃない、多分ロボットだ", 140, FRAME_END)
    mbappe = build_stick_figure("Mbappe", TEAM_RED, Vector((7, 2, 0)))
    iron_leg = build_stick_figure("IronLeg", TEAM_BLUE, Vector((-0.5, -0.5, 0)))
    _animate_ball_france(ball)
    _animate_mbappe(mbappe)
    _animate_iron_leg(iron_leg)
    _camera_france(cam)
    set_linear_interpolation()
    bpy.context.scene.frame_set(1)


# --- シーン02: ノルウェー戦 壁駆け上がりGK ---

def _animate_ball_norway(ball: bpy.types.Object) -> None:
    for frame, pos in [
        (1, Vector((4.5, 0.0, 0.11))), (40, Vector((3.0, 0.0, 0.11))),
        (55, Vector((1.0, 0.0, 0.25))), (85, Vector((-12.0, 0.2, 1.6))),
        (105, Vector((-17.5, 0.1, 1.9))), (115, Vector((-14.0, 2.5, 2.8))),
        (150, Vector((-10.0, 4.0, 0.2))), (FRAME_END, Vector((-10.0, 4.0, 0.2))),
    ]:
        ball.location = pos
        ball.keyframe_insert(data_path="location", frame=frame)


def _animate_haaland(fig: StickFigure) -> None:
    fig.pose(1, Vector((3.2, 0.0, 0.0)), Euler((0, 0, _deg(175))), {
        "leg_l_upper_joint": Euler((_deg(-8), 0, 0)), "leg_r_upper_joint": Euler((_deg(12), 0, 0)),
    })
    fig.pose(55, Vector((1.8, 0.0, 0.0)), Euler((0, 0, _deg(178))), {
        "leg_r_upper_joint": Euler((_deg(68), 0, 0)), "arm_l_upper_joint": Euler((_deg(-45), 0, _deg(-20))),
    })
    fig.pose(150, Vector((0.5, -1.0, 0.0)), Euler((0, 0, _deg(140))), {
        "head_joint": Euler((_deg(-12), 0, 0)),
        "arm_l_upper_joint": Euler((_deg(-95), 0, _deg(-25))), "arm_r_upper_joint": Euler((_deg(-95), 0, _deg(25))),
        "arm_l_lower_joint": Euler((_deg(-70), 0, 0)), "arm_r_lower_joint": Euler((_deg(-70), 0, 0)),
    })
    fig.pose(FRAME_END, Vector((0.5, -1.0, 0.0)), Euler((0, 0, _deg(140))), {})


def _animate_gk_wall(fig: StickFigure) -> None:
    fig.pose(1, Vector((-17.0, 0.4, 0.0)), Euler((0, 0, _deg(90))), {
        "arm_l_upper_joint": Euler((_deg(-50), 0, _deg(-15))), "arm_r_upper_joint": Euler((_deg(-50), 0, _deg(15))),
    })
    fig.pose(95, Vector((-19.55, 0.2, 1.2)), Euler((0, _deg(88), _deg(90))), {
        "arm_l_upper_joint": Euler((_deg(-120), 0, _deg(-10))), "arm_r_upper_joint": Euler((_deg(-140), 0, _deg(10))),
    })
    fig.pose(110, Vector((-19.55, 0.2, 2.15)), Euler((0, _deg(90), _deg(90))), {
        "arm_l_upper_joint": Euler((_deg(-155), 0, _deg(-35))), "arm_r_upper_joint": Euler((_deg(-165), 0, _deg(35))),
    })
    fig.pose(FRAME_END, Vector((-17.5, 0.5, 0.0)), Euler((0, 0, _deg(90))), {})


def _camera_norway(cam: bpy.types.Object) -> None:
    animate_camera_keyframes(cam, [
        (1, Vector((2.0, -7.0, 5.0)), Euler((_deg(62), 0, _deg(14)))),
        (95, Vector((0.0, -5.5, 4.5)), Euler((_deg(66), 0, _deg(8)))),
        (FRAME_END, Vector((1.0, -6.5, 5.0)), Euler((_deg(63), 0, _deg(12)))),
    ])


def run_scene_02() -> None:
    setup_render()
    build_pitch()
    build_goal_and_wall()
    ball = ensure_ball()
    cam = ensure_camera()
    ensure_title_bug("再現CG  2026W杯 グループ最終戦 vs ノルウェー")
    ensure_caption("なぜあの人は重力を無視してるんだ…", 155, FRAME_END)
    haaland = build_stick_figure("Haaland", TEAM_RED, Vector((3, 0, 0)))
    gk = build_stick_figure("ShaolinGK", TEAM_BLUE, Vector((-17, 0, 0)))
    _animate_ball_norway(ball)
    _animate_haaland(haaland)
    _animate_gk_wall(gk)
    _camera_norway(cam)
    set_linear_interpolation()
    bpy.context.scene.frame_set(1)


SCENES: Dict[str, SceneSpec] = {
    "01": SceneSpec("01", "フランス戦 — 鉄脚功", "再現CG  2026W杯 グループ初戦 vs フランス",
                    "あれは人間じゃない、多分ロボットだ", 140,
                    {"01_sprint": 35, "02_iron_kick": 58, "03_goal": 90, "04_shock": 160}, run_scene_01),
    "02": SceneSpec("02", "ノルウェー戦 — 壁駆け上がりGK", "再現CG  2026W杯 グループ最終戦 vs ノルウェー",
                    "なぜあの人は重力を無視してるんだ…", 155,
                    {"01_kick": 55, "02_wall": 95, "03_save": 110, "04_react": 170}, run_scene_02),
}

# シーン03（Mannequinyベース）— 台本は scripts/scene_japan_kubo.md
# 実行: build_part_field.py -- --animate-kubo-mark --render-kubo-mark-video
SCENE_03_SCRIPT = (
    "初戦の相手は日本代表。注目は久保建英です。彼の武器は、細かいタッチで相手を幻惑する巧みなドリブルと、"
    "ゴール前での思い切りの良いシュート。しかし少林サッカーチームは、粘り気のある足技を持つ兄をぴったりと"
    "マークにつけ、まるで接着剤のようにボールごと引っ付いてしまいます。久保がどれだけ細かく足元でボールを"
    "転がしても、ボールごと吸い付いて離れない。"
)

SCENE_04_SCRIPT = (
    "もう一人の要、遠藤航の堅実な中盤の守備の前で、少林選手が真正面からゆっくりドリブル。"
    "だんだんすーっと消えていき、最後はボールだけが残る。"
)

# シーン05（Mannequinyベース）— 台本は scripts/scene_portugal_shin_handshake.md
# 実行: build_part_field.py -- --animate-portugal-handshake --render-portugal-handshake-video
SCENE_05_SCRIPT = (
    "予選第1戦、相手はポルトガル代表。シンがレオンのミュージシャンとしての活動、"
    "通称WAY45の大ファンだったため、試合開始早々ロナウドそっちのけで握手を求めに行ってしまう。"
)

# シーン06 — 台本は scripts/scene_portugal_ronaldo_header.md
# 実行: build_part_field.py -- --animate-portugal-header --render-portugal-header-video
SCENE_06_SCRIPT = (
    "キレたロナウドが単独でジャンプヘディング。スローモーションでボールを頭に合わせる。"
)
