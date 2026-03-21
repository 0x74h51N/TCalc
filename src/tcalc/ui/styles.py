from __future__ import annotations

from pathlib import Path
from string import Template

from PySide6.QtWidgets import QApplication

from ..theme import get_theme
from .config import calc_config, keypad_config
from .config import style as ui_style
from .widgets.common.utils import rgba

_QSS_DIR = Path(__file__).parent / "styles"


def _build_subs() -> dict[str, str]:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing
    og = ui_style["option_group"]

    checked_bg = rgba(c["accent"], float(og["checked_alpha"]))
    hover_bg = rgba(c["secondary_hover"], float(og["hover_alpha"]))
    pad_y = int(og["padding_y"])
    pad_x = int(og["padding_x"])

    _style = calc_config["style"]
    _display = calc_config["display"]
    _topbar = calc_config["topbar"]

    disabled_bg = rgba(c["secondary_hover"], float(_style["disabled_background_alpha"]))
    disabled_text = rgba(c["accent_text"], float(_style["disabled_text_alpha"]))

    memory_bg = rgba(c["accent"], float(_topbar["memory_background_alpha"]))
    memory_bg_hover = rgba(c["accent"], float(_topbar["memory_background_hover_alpha"]))
    memory_bg_pressed = rgba(c["accent"], float(_topbar["memory_background_pressed_alpha"]))

    return {
        "background_light": c["background_light"],
        "background_dark": c["background_dark"],
        "background_dark_alt": c["background_dark_alt"],
        "background": c["background"],
        "foreground": c["foreground"],
        "border_light": c["border_light"],
        "border_dark": c["border_dark"],
        "border_focus": c["border_focus"],
        "selection_background": c["selection_background"],
        "selection_text": c["selection_text"],
        "text_primary": c["text_primary"],
        "text_secondary": c["text_secondary"],
        "text_tertiary": c["text_tertiary"],
        "accent": c["accent"],
        "accent_text": c["accent_text"],
        "accent_hover": c["accent_hover"],
        "secondary": c["secondary"],
        "secondary_text": c["secondary_text"],
        "secondary_hover": c["secondary_hover"],
        "action": c["action"],
        "action_text": c["action_text"],
        "action_hover": c["action_hover"],
        "primary": c["primary"],
        "primary_text": c["primary_text"],
        "primary_hover": c["primary_hover"],
        "radius_small": str(s["radius_small"]),
        "radius_medium": str(s["radius_medium"]),
        "radius_large": str(s["radius_large"]),
        "tooltip_padding": str(int(ui_style["tooltip_padding"])),
        "icon_padding": "4",
        "option_padding_y": str(pad_y),
        "option_padding_x": str(pad_x),
        "option_checked_bg": checked_bg,
        "option_hover_bg": hover_bg,
        "button_padding": str(int(keypad_config["button_padding"])),
        "compact_pad_y": str(int(_style["compact_button_padding_y"])),
        "compact_pad_x": str(int(_style["compact_button_padding_x"])),
        "disabled_bg": disabled_bg,
        "disabled_text": disabled_text,
        "divider_height": str(int(_display["divider_height"])),
        "root_border_width": str(int(_display["root_border_width"])),
        "memory_bg": memory_bg,
        "memory_bg_hover": memory_bg_hover,
        "memory_bg_pressed": memory_bg_pressed,
    }


def load_qss_file(name: str) -> str:
    qss_path = _QSS_DIR / name
    template = Template(qss_path.read_text(encoding="utf-8"))
    return template.safe_substitute(_build_subs())


def _load_qss() -> str:
    if not _QSS_DIR.exists():
        return ""

    subs = _build_subs()
    sheets: list[str] = []
    for qss_path in sorted(_QSS_DIR.glob("*.qss")):
        template = Template(qss_path.read_text(encoding="utf-8"))
        sheets.append(template.safe_substitute(subs))

    return "\n".join(sheets)


def _build_stylesheet() -> str:
    return _load_qss()


def apply_styles(app: QApplication) -> None:
    base = app.styleSheet()
    sheet = _build_stylesheet()
    if sheet:
        combined = sheet if not base else f"{base}\n{sheet}"
        app.setStyleSheet(combined)
