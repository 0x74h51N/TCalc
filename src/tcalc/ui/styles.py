from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import Template

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from ..theme import CUSTOM_THEMES_DIR, get_theme, load_theme
from .config import calc_config, fonts_config, keypad_config, manubar_style, toast_config
from .config import style as ui_style

_UI_DIR = Path(__file__).parent
# common.qss first, then every component sheet; together they form the one app stylesheet
_QSS_FILES = sorted(_UI_DIR.rglob("*.qss"), key=lambda p: (p.name != "common.qss", p))


def _ints(table: dict[str, object], prefix: str = "") -> dict[str, str]:
    return {f"{prefix}{k}": str(v) for k, v in table.items() if isinstance(v, int)}


def _build_subs() -> dict[str, str]:
    """Template substitutions: the active theme's colors and spacing plus the layout numbers
    the stylesheets use."""
    theme = get_theme()
    og = ui_style["option_group"]
    return {
        **{k: str(v) for k, v in {**theme.colors, **theme.spacing}.items()},
        "tooltip_padding": str(int(ui_style["tooltip_padding"])),
        "icon_padding": "4",
        "option_padding_y": str(int(og["padding_y"])),
        "option_padding_x": str(int(og["padding_x"])),
        "button_padding": str(int(keypad_config["button_padding"])),
        **_ints(manubar_style),
        "menu_font_size": str(app_fonts().menu_size),
        "picker_font_size": str(app_fonts().picker_size),
        **_ints(calc_config["style"]),
        **_ints(calc_config["topbar"]),
        **_ints(calc_config["display"]),
        **_ints(calc_config["display"]["result"]),
        **_ints(toast_config, "toast_"),
    }


def _build_stylesheet() -> str:
    subs = _build_subs()
    return "\n".join(
        Template(path.read_text(encoding="utf-8")).safe_substitute(subs) for path in _QSS_FILES
    )


def _build_palette() -> QPalette:
    """Map theme tokens onto Qt palette roles, so un-styled widgets don't fall back to the OS
    scheme (a light OS theme would otherwise leak into dialogs, menus, scrollbars...)."""
    c = get_theme().colors
    role = QPalette.ColorRole
    # (button, window) constructor derives the 3D shades and disabled colors itself
    palette = QPalette(QColor(c["background_light"]), QColor(c["background"]))
    for r, token in (
        (role.WindowText, "text_primary"),
        (role.Base, "background_dark"),
        (role.Text, "text_primary"),
        (role.ButtonText, "text_primary"),
        (role.Highlight, "selection_background"),
        (role.HighlightedText, "selection_text"),
    ):
        palette.setColor(r, QColor(c[token]))
    return palette


def init_styles(app: QApplication, variant: str) -> None:
    """One-time app styling: custom themes' fonts, the style and the first theme."""
    # A custom theme brings its fonts in its own folder (e.g. themes/retro/VT323-Regular.ttf)
    for path in sorted(CUSTOM_THEMES_DIR.glob("*/*.[ot]tf")):
        QFontDatabase.addApplicationFont(str(path))
    # Fusion honours the palette fully on every platform; native styles may ignore it
    app.setStyle("Fusion")
    apply_theme(app, variant)
    # setStyle and the first setStyleSheet load the platform theme's per-class fonts (menus,
    # labels...); setFont without a class name clears them. Later switches only re-polish
    app.setFont(_app_font())


@dataclass(frozen=True, slots=True)
class AppFonts:
    family: str
    size: int
    keypad_min_pt: int
    keypad_max_pt: int
    menu_size: int  # px
    picker_size: int  # pt


def app_fonts() -> AppFonts:
    """The UI config's [fonts] and keypad font range, with the active theme's overrides."""
    fonts = {
        **fonts_config,
        "keypad_min_pt": keypad_config["min_pt"],
        "keypad_max_pt": keypad_config["max_pt"],
        "menu_size": manubar_style["menu_font_size"],
        **get_theme().fonts,
    }
    return AppFonts(
        fonts["family_default"],
        fonts["size_default"],
        fonts["keypad_min_pt"],
        fonts["keypad_max_pt"],
        fonts["menu_size"],
        fonts.get("picker_size", fonts["size_default"]),
    )


def _app_font() -> QFont:
    fonts = app_fonts()
    return QFont(fonts.family, fonts.size)


def apply_theme(app: QApplication, variant: str) -> None:
    """Switch to theme *variant*: a new palette, and the app stylesheet re-polishes every
    widget, hidden ones included. The style stays, since replacing it would reload the
    platform theme's fonts."""
    load_theme(variant)
    app.setPalette(_build_palette())
    # Before the stylesheet: its re-polish hands each widget its parent's font as it is then
    app.setFont(_app_font())
    app.setStyleSheet(_build_stylesheet())
