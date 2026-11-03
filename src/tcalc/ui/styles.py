from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from string import Template

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from ..app_state import get_app_state
from ..theme import custom_theme_folders, get_theme, load_theme
from .config import STYLESHEET_TABLES, int_fields


class _ThemeEvents(QObject):
    # Emitted inside apply_theme, before any repaint: the re-polish dropped widget-set fonts
    applied = Signal()


theme_events = _ThemeEvents()

_UI_DIR = Path(__file__).parent
# common.qss first, then every component sheet; together they form the one app stylesheet
_QSS_FILES = sorted(_UI_DIR.rglob("*.qss"), key=lambda p: (p.name != "common.qss", p))


def _build_subs() -> dict[str, str]:
    """Template substitutions: the active theme's colors, the color each place uses, and the
    numbers of its stylesheet tables and fonts."""
    theme = get_theme()
    ui = theme.ui
    numbers = [(row.prefix, row.table(ui)) for row in STYLESHEET_TABLES] + [("", ui.fonts)]
    return {
        **theme.colors,
        **{place: theme.colors[color] for place, color in asdict(ui.color_usage).items()},
        **{
            prefix + name: str(value)
            for prefix, table in numbers
            for name, value in int_fields(table).items()
        },
    }


def _build_stylesheet() -> str:
    subs = _build_subs()
    return "\n".join(
        Template(path.read_text(encoding="utf-8")).safe_substitute(subs) for path in _QSS_FILES
    )


def _build_palette() -> QPalette:
    """Map theme tokens onto Qt palette roles, so un-styled widgets don't fall back to the OS
    scheme (a light OS theme would otherwise leak into dialogs, menus, scrollbars...)."""
    theme = get_theme()
    usage = theme.ui.color_usage
    role = QPalette.ColorRole
    # (button, window) constructor derives the 3D shades and disabled colors itself
    palette = QPalette(
        theme.qcolor(usage.palette_button_color), theme.qcolor(usage.palette_window_color)
    )
    for r, color in (
        (role.WindowText, usage.palette_window_text_color),
        (role.Base, usage.palette_base_color),
        (role.Text, usage.palette_text_color),
        (role.ButtonText, usage.palette_button_text_color),
        (role.Highlight, usage.palette_highlight_color),
        (role.HighlightedText, usage.palette_highlighted_text_color),
    ):
        palette.setColor(r, theme.qcolor(color))
    return palette


def init_styles(app: QApplication, variant: str) -> None:
    """One-time app styling: custom themes' fonts, the style and the first theme."""
    # A custom theme brings its fonts in its own folder (e.g. retro/VT323-Regular.ttf)
    for folder in custom_theme_folders().values():
        for path in sorted(folder.glob("*.[ot]tf")):
            QFontDatabase.addApplicationFont(str(path))
    # Fusion honours the palette fully on every platform; native styles may ignore it
    app.setStyle("Fusion")
    apply_theme(app, variant)
    # setStyle and the first setStyleSheet load the platform theme's per-class fonts (menus,
    # labels...); setFont without a class name clears them. Later switches only re-polish
    app.setFont(_app_font())


def _app_font() -> QFont:
    fonts = get_theme().ui.fonts
    return QFont(fonts.family_default, fonts.size_default)


def apply_theme(app: QApplication, variant: str) -> None:
    """Switch to theme *variant*: a new palette, and the app stylesheet re-polishes every
    widget, hidden ones included. The style stays, since replacing it would reload the
    platform theme's fonts."""
    load_theme(variant)
    app.setPalette(_build_palette())
    # Before the stylesheet: its re-polish hands each widget its parent's font as it is then
    app.setFont(_app_font())
    app.setStyleSheet(_build_stylesheet())
    theme_events.applied.emit()


def sync_theme(app: QApplication, scheme: Qt.ColorScheme) -> None:
    """Apply the user's theme choice for Qt's *scheme*, unless it is already on. The menu
    applies a choice at once, and Qt's later scheme signal for it then changes nothing."""
    variant = get_app_state().theme.variant(scheme)
    if variant != get_theme().variant:
        apply_theme(app, variant)
