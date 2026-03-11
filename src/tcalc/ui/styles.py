from __future__ import annotations

from pathlib import Path
from string import Template

from PySide6.QtWidgets import QApplication

from ..theme import get_theme
from .config import style as ui_style
from .widgets.common.utils import rgba


def _load_qss() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing
    og = ui_style["option_group"]

    checked_bg = rgba(c["accent"], float(og["checked_alpha"]))
    hover_bg = rgba(c["secondary_hover"], float(og["hover_alpha"]))
    pad_y = int(og["padding_y"])
    pad_x = int(og["padding_x"])

    qss_dir = Path(__file__).parent / "styles"
    if not qss_dir.exists():
        return ""

    subs = {
        "background_light": c["background_light"],
        "background_dark": c["background_dark"],
        "background_dark_alt": c["background_dark_alt"],
        "background": c["background"],
        "foreground": c["foreground"],
        "border_light": c["border_light"],
        "border_dark": c["border_dark"],
        "selection_background": c["selection_background"],
        "selection_text": c["selection_text"],
        "text_primary": c["text_primary"],
        "text_secondary": c["text_secondary"],
        "text_tertiary": c["text_tertiary"],
        "accent_text": c["accent_text"],
        "accent": c["accent"],
        "radius_small": str(s["radius_small"]),
        "radius_medium": str(s["radius_medium"]),
        "radius_large": str(s["radius_large"]),
        "tooltip_padding": str(int(ui_style["tooltip_padding"])),
        "icon_padding": "4",
        "option_padding_y": str(pad_y),
        "option_padding_x": str(pad_x),
        "option_checked_bg": checked_bg,
        "option_hover_bg": hover_bg,
    }

    sheets: list[str] = []
    for qss_path in sorted(qss_dir.glob("*.qss")):
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
