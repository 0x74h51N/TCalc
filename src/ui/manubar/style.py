from __future__ import annotations

from PySide6.QtWidgets import QMenuBar

from ...theme import get_theme
from .config import style


def _build_menu_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = style

    return f"""
QMenu {{
    background: {c['background_medium']};
    color: {c['text_primary']};
    border: 1px solid {c['border_light']};
    padding: {s['menu_padding']}px;
    font-size: {s['font_size']}px;
}}

QMenu::item {{
    padding: {s['item_padding_vertical']}px {s['item_padding_horizontal']}px;
    border-radius: {s['item_border_radius']}px;
    margin: {s['item_margin']}px 0;
    min-width: {s['item_min_width']}px;
}}

QMenu::item:selected {{
    background: {c['selection_background']};
    color: {c['selection_text']};
    border: 1px solid {c['border_focus']};
}}

QMenu::icon {{
    padding-left: {s['icon_padding_left']}px;
    padding-right: {s['icon_padding_right']}px;
}}

QMenu::separator {{
    height: {s['separator_height']}px;
    background: {c['border_light']};
    margin: {s['separator_margin_vertical']}px {s['separator_margin_horizontal']}px;
}}
"""


def apply_menu_styles(menu_bar: QMenuBar) -> None:
    base = menu_bar.styleSheet()
    sheet = _build_menu_stylesheet()
    merged = sheet if not base else f"{base}\n{sheet}"
    menu_bar.setStyleSheet(merged)
