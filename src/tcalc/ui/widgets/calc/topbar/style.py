from __future__ import annotations

from PySide6.QtWidgets import QWidget

from .....theme import get_theme
from ..style import build_calc_base_stylesheet, rgba


def _build_topbar_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing

    memory_bg = rgba(c["accent"], 0.2)
    memory_bg_hover = rgba(c["accent"], 0.28)
    memory_bg_pressed = rgba(c["accent"], 0.38)

    angle_bg_checked = rgba(c["accent"], 0.25)
    angle_bg_hover = rgba(c["secondary_hover"], 0.35)

    return build_calc_base_stylesheet() + f"""
QPushButton[keypadRole="memory"] {{
    background-color: {memory_bg};
    color: {c['accent_text']};
    border: none;
}}
QPushButton[keypadRole="memory"]:hover {{
    background-color: {memory_bg_hover};
}}
QPushButton[keypadRole="memory"]:pressed, QPushButton[keypadRole="memory"][pressed="true"] {{
    background-color: {memory_bg_pressed};
}}

QRadioButton[keypadRole="angle"] {{
    background-color: transparent;
    color: {c['text_secondary']};
    border-radius: {s['radius_small']}px;
    padding: 4px 10px;
    spacing: 0px;
}}
QRadioButton[keypadRole="angle"]::indicator {{
    width: 0px;
    height: 0px;
}}
QRadioButton[keypadRole="angle"]:hover {{
    background-color: {angle_bg_hover};
}}
QRadioButton[keypadRole="angle"]:checked {{
    background-color: {angle_bg_checked};
    color: {c['accent_text']};
}}

QPushButton[keypadRole="memory"] {{
    padding: 4px 8px;
}}
"""


def apply_topbar_style(widget: QWidget) -> None:
    widget.setStyleSheet(_build_topbar_stylesheet())

