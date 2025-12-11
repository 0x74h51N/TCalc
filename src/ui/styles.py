from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..theme import get_theme


def _build_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing

    return f"""
QLineEdit#displayExpression {{
    border: none;
    background-color: transparent;
    color: {c['text_secondary']};
    selection-background-color: {c['selection_background']};
    selection-color: {c['selection_text']};
}}
QLineEdit#displayExpression:focus {{
    border: none;
    background-color: transparent;
}}
QLabel#displayResult {{
    color: {c['text_primary']};
}}
QFrame#displayDivider {{
    min-height: 1px;
    max-height: 1px;
}}
QPushButton[keypadRole] {{
    background-color: {c['secondary']};
    color: {c['secondary_text']};
    border: 1px solid {c['border_default']};
    border-radius: {s['radius_medium']}px;
    padding: 10px;
    font-size: 15px;
}}
QPushButton[keypadRole]:pressed {{
    background-color: {c['secondary_hover']};
}}
QPushButton[keypadRole="operator"] {{
    background-color: {c['accent']};
    color: {c['accent_text']};
    border-color: {c['border_light']};
}}
QPushButton[keypadRole="operator"]:pressed {{
    background-color: {c['accent_hover']};
}}
QPushButton[keypadRole="action"] {{
    background-color: {c['action']};
    color: {c['action_text']};
    border-color: {c['border_light']};
}}
QPushButton[keypadRole="equals"] {{
    background-color: {c['primary']};
    color: {c['primary_text']};
    border-color: {c['border_focus']};
}}
QPushButton[keypadRole="equals"]:pressed {{
    background-color: {c['primary_hover']};
}}
"""


def apply_styles(app: QApplication) -> None:
    base = app.styleSheet()
    sheet = _build_stylesheet()
    combined = sheet if not base else f"{base}\n{sheet}"
    app.setStyleSheet(combined)
