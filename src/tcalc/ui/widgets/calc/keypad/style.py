from __future__ import annotations

from PySide6.QtWidgets import QWidget

from .....theme import get_theme
from ..config import style_config
from ..style import apply_calc_style


def _build_keypad_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    compact_pad_y = int(style_config["compact_button_padding_y"])
    compact_pad_x = int(style_config["compact_button_padding_x"])

    return f"""
QPushButton[keypadRole="operator"] {{
    background-color: {c["accent"]};
    color: {c["accent_text"]};
}}
QPushButton[keypadRole="operator"]:hover {{
    border: 1px solid {c["accent_text"]};
}}
QPushButton[keypadRole="operator"]:pressed, QPushButton[keypadRole="operator"][pressed="true"] {{
    background-color: {c["accent_hover"]};
}}
QPushButton[keypadRole="action"] {{
    background-color: {c["action"]};
    color: {c["action_text"]};
}}
QPushButton[keypadRole="action"]:hover {{
    border: 1px solid {c["accent_text"]};
}}
QPushButton[keypadRole="action"]:pressed, QPushButton[keypadRole="action"][pressed="true"] {{
    background-color: {c["action_hover"]};
}}
QPushButton[keypadRole="equals"] {{
    background-color: {c["primary"]};
    color: {c["primary_text"]};
    border-color: {c["border_focus"]};
}}
QPushButton[keypadRole="equals"]:hover {{
    border: 1px solid {c["accent_text"]};
}}
QPushButton[keypadRole="equals"]:pressed, QPushButton[keypadRole="equals"][pressed="true"] {{
    background-color: {c["primary_hover"]};
}}
QPushButton[keypadRole="trig"] {{
    background-color: {c["action"]};
    color: {c["action_text"]};
    border-color: {c["border_light"]};
}}
QPushButton[keypadRole="trig"]:hover {{
    border: 1px solid {c["accent_text"]};
}}
QPushButton[keypadRole="trig"]:pressed, QPushButton[keypadRole="trig"][pressed="true"] {{
    background-color: {c["action_hover"]};
}}

QPushButton[keypadRole="function"] {{
    background-color: {c["accent"]};
    color: {c["accent_text"]};
    border-color: {c["border_light"]};

}}
QPushButton[keypadRole="function"]:hover {{
    border: 1px solid {c["accent_text"]};
}}
QPushButton[keypadRole="function"]:pressed, QPushButton[keypadRole="function"][pressed="true"] {{
    background-color: {c["accent_hover"]};
}}
QPushButton[keypadRole="power"] {{
    background-color: {c["secondary"]};
    color: {c["secondary_text"]};
    border-color: {c["border_light"]};

}}
QPushButton[keypadRole="power"]:hover {{
    border: 1px solid {c["accent_text"]};
}}
QPushButton[keypadRole="power"]:pressed, QPushButton[keypadRole="power"][pressed="true"] {{
    background-color: {c["secondary_hover"]};
}}

QPushButton[keypadRole="trig"],
QPushButton[keypadRole="function"],
QPushButton[keypadRole="power"] {{
    padding: {compact_pad_y}px {compact_pad_x}px;
}}
"""


def apply_keypad_style(widget: QWidget) -> None:
    apply_calc_style(widget, _build_keypad_stylesheet())
