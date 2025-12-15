from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget

from .....theme import get_theme


def _build_keypad_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing

    return f"""
QPushButton[keypadRole] {{
    background-color: {c['secondary']};
    color: {c['secondary_text']};
    border: 1px solid {c['border_default']};
    border-radius: {s['radius_small']}px;
    padding: 10px;
    font-size: 13px;
}}
QPushButton[keypadRole]:hover {{
    border: 1px solid {c['accent_text']};
}}
QPushButton[keypadRole]:pressed, QPushButton[keypadRole][pressed="true"] {{
    background-color: {c['secondary_hover']};
}}
QPushButton[keypadRole="operator"] {{
    background-color: {c['accent']};
    color: {c['accent_text']};
    border-color: {c['border_light']};
}}
QPushButton[keypadRole="operator"]:hover {{
    border: 1px solid {c['accent_text']};
}}
QPushButton[keypadRole="operator"]:pressed, QPushButton[keypadRole="operator"][pressed="true"] {{
    background-color: {c['accent_hover']};
}}
QPushButton[keypadRole="action"] {{
    background-color: {c['action']};
    color: {c['action_text']};
    border-color: {c['border_light']};
}}
QPushButton[keypadRole="action"]:hover {{
    border: 1px solid {c['accent_text']};
}}
QPushButton[keypadRole="action"]:pressed, QPushButton[keypadRole="action"][pressed="true"] {{
    background-color: {c['action_hover']};
}}
QPushButton[keypadRole="equals"] {{
    background-color: {c['primary']};
    color: {c['primary_text']};
    border-color: {c['border_focus']};
}}
QPushButton[keypadRole="equals"]:hover {{
    border: 1px solid {c['accent_text']};
}}
QPushButton[keypadRole="equals"]:pressed, QPushButton[keypadRole="equals"][pressed="true"] {{
    background-color: {c['primary_hover']};
}}
QPushButton[keypadRole="trig"] {{
    background-color: {c['action']};
    color: {c['action_text']};
    border-color: {c['border_light']};
    padding: 4px 8px;
}}
QPushButton[keypadRole="trig"]:hover {{
    border: 1px solid {c['accent_text']};
}}
QPushButton[keypadRole="trig"]:pressed, QPushButton[keypadRole="trig"][pressed="true"] {{
    background-color: {c['action_hover']};
}}
QPushButton[keypadRole="function"] {{
    background-color: {c['accent']};
    color: {c['accent_text']};
    border-color: {c['border_light']};
    padding: 4px 8px;

}}
QPushButton[keypadRole="function"]:hover {{
    border: 1px solid {c['accent_text']};
}}
QPushButton[keypadRole="function"]:pressed, QPushButton[keypadRole="function"][pressed="true"] {{
    background-color: {c['accent_hover']};
}}
QPushButton[keypadRole="power"] {{
    background-color: {c['secondary']};
    color: {c['secondary_text']};
    border-color: {c['border_light']};
    padding: 4px 8px;

}}
QPushButton[keypadRole="power"]:hover {{
    border: 1px solid {c['accent_text']};
}}
QPushButton[keypadRole="power"]:pressed, QPushButton[keypadRole="power"][pressed="true"] {{
    background-color: {c['secondary_hover']};
}}
"""


def apply_keypad_style(widget: QWidget) -> None:
    widget.setStyleSheet(_build_keypad_stylesheet())


def apply_button_style(button: QPushButton, role: str) -> None:
    button.setObjectName("keypadButton")
    button.setProperty("keypadRole", role)
    
    button.style().unpolish(button)
    button.style().polish(button)
