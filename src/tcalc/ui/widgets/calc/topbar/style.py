from __future__ import annotations

from PySide6.QtWidgets import QWidget

from .....theme import get_theme
from ..config import style_config, topbar_config
from ..style import build_calc_base_stylesheet, rgba


def _build_topbar_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing

    memory_bg = rgba(c["accent"], float(topbar_config["memory_background_alpha"]))
    memory_bg_hover = rgba(c["accent"], float(topbar_config["memory_background_hover_alpha"]))
    memory_bg_pressed = rgba(c["accent"], float(topbar_config["memory_background_pressed_alpha"]))

    angle_bg_checked = rgba(c["accent"], float(topbar_config["angle_background_checked_alpha"]))
    angle_bg_hover = rgba(
        c["secondary_hover"], float(topbar_config["angle_background_hover_alpha"])
    )
    angle_pad_y = int(topbar_config["angle_button_padding_y"])
    angle_pad_x = int(topbar_config["angle_button_padding_x"])
    angle_spacing = int(topbar_config["angle_spacing_px"])
    angle_indicator = int(topbar_config["angle_indicator_size_px"])
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

QRadioButton[keypadRole="angle"] {{
    background-color: transparent;
    color: {c["text_secondary"]};
    border-radius: {s["radius_small"]}px;
    padding: {angle_pad_y}px {angle_pad_x}px;
    spacing: {angle_spacing}px;
}}
QRadioButton[keypadRole="angle"]::indicator {{
    width: {angle_indicator}px;
    height: {angle_indicator}px;
}}
QRadioButton[keypadRole="angle"]:hover {{
    background-color: {angle_bg_hover};
}}
QRadioButton[keypadRole="angle"]:checked {{
    background-color: {angle_bg_checked};
    color: {c["accent_text"]};
}}

QPushButton[keypadRole="memory"] {{
    padding: {compact_pad_y}px {compact_pad_x}px;
}}
"""
    )


def apply_topbar_style(widget: QWidget) -> None:
    widget.setStyleSheet(_build_topbar_stylesheet())
