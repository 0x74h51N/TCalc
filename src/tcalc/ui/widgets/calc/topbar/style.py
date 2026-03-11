from __future__ import annotations

from PySide6.QtWidgets import QWidget

from .....theme import get_theme
from ..config import style_config, topbar_config
from ..style import build_calc_base_stylesheet, rgba


def _build_topbar_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors

    memory_bg = rgba(c["accent"], float(topbar_config["memory_background_alpha"]))
    memory_bg_hover = rgba(c["accent"], float(topbar_config["memory_background_hover_alpha"]))
    memory_bg_pressed = rgba(c["accent"], float(topbar_config["memory_background_pressed_alpha"]))

    compact_pad_y = int(style_config["compact_button_padding_y"])
    compact_pad_x = int(style_config["compact_button_padding_x"])

    return (
        build_calc_base_stylesheet()
        + f"""
QPushButton[keypadRole="memory"] {{
    background-color: {memory_bg};
    color: {c["accent_text"]};
    border: none;
}}
QPushButton[keypadRole="memory"]:hover {{
    background-color: {memory_bg_hover};
}}
QPushButton[keypadRole="memory"]:pressed, QPushButton[keypadRole="memory"][pressed="true"] {{
    background-color: {memory_bg_pressed};
}}

QPushButton[keypadRole="memory"] {{
    padding: {compact_pad_y}px {compact_pad_x}px;
}}
"""
    )


def apply_topbar_style(widget: QWidget) -> None:
    widget.setStyleSheet(_build_topbar_stylesheet())
