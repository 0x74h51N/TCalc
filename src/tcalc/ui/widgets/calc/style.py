from __future__ import annotations

from PySide6.QtWidgets import QAbstractButton, QWidget

from ....theme import get_theme
from .config import style_config


def rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_calc_base_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing

    disabled_bg = rgba(c["secondary_hover"], float(style_config["disabled_background_alpha"]))
    disabled_text = rgba(c["accent_text"], float(style_config["disabled_text_alpha"]))
    button_padding = int(style_config["button_padding"])

    return f"""
QPushButton[keypadRole] {{
    background-color: {c["secondary"]};
    color: {c["secondary_text"]};
    border-radius: {s["radius_small"]}px;
    padding: {button_padding}px;
}}
QPushButton[keypadRole]:hover {{
    border: 1px solid {c["accent_text"]};
}}
QPushButton[keypadRole]:pressed, QPushButton[keypadRole][pressed="true"] {{
    background-color: {c["secondary_hover"]};
}}
QPushButton[keypadRole]:disabled {{
    background-color: {disabled_bg};
    color: {disabled_text};
    border-color: {disabled_bg};
}}

QPushButton[keypadRole]:checked {{
    background-color: {c["action_hover"]};
}}
"""


def apply_button_style(button: QAbstractButton, role: str) -> None:
    button.setObjectName("keypadButton")
    button.setProperty("keypadRole", role)
    button.style().unpolish(button)
    button.style().polish(button)


def apply_calc_style(widget: QWidget, extra: str) -> None:
    widget.setStyleSheet(build_calc_base_stylesheet() + extra)
