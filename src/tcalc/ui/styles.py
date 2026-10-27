from __future__ import annotations

from pathlib import Path
from string import Template

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from ..theme import get_theme
from .config import style as ui_style
from .utils import rgba

_STYLES_DIR = Path(__file__).parent / "styles"


def build_subs() -> dict[str, str]:
    """Build the base template-substitution dictionary from theme tokens."""
    theme = get_theme()
    c = theme.colors
    s = theme.spacing
    og = ui_style["option_group"]

    subs: dict[str, str] = {k: str(v) for k, v in {**c, **s}.items()}

    # -- common.qss needs --
    subs["tooltip_padding"] = str(int(ui_style["tooltip_padding"]))
    subs["icon_padding"] = "4"
    subs["option_padding_y"] = str(int(og["padding_y"]))
    subs["option_padding_x"] = str(int(og["padding_x"]))
    subs["option_checked_bg"] = rgba(c[og["checked_base"]], float(og["checked_alpha"]))
    subs["option_hover_bg"] = rgba(c[og["hover_base"]], float(og["hover_alpha"]))

    return subs


def load_qss(qss_path: Path, subs: dict[str, str] | None = None) -> str:
    """Read a ``.qss`` template and return the substituted stylesheet string."""
    if subs is None:
        subs = build_subs()
    template = Template(qss_path.read_text(encoding="utf-8"))
    return template.safe_substitute(subs)


def apply_widget_qss(widget: QWidget, qss_path: Path, subs: dict[str, str] | None = None) -> None:
    """Load a QSS template and apply it to *widget* via ``setStyleSheet``."""
    sheet = load_qss(qss_path, subs)
    base = widget.styleSheet()
    merged = sheet if not base else f"{base}\n{sheet}"
    widget.setStyleSheet(merged)


# ---------------------------------------------------------------------------
# App-level styles
# ---------------------------------------------------------------------------


def _load_common_qss() -> str:
    common = _STYLES_DIR / "common.qss"
    if not common.exists():
        return ""
    return load_qss(common)


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


def apply_styles(app: QApplication) -> None:
    # Fusion honours the palette fully on every platform; native styles may ignore it
    app.setStyle("Fusion")
    app.setPalette(_build_palette())

    base = app.styleSheet()
    sheet = _load_common_qss()
    if sheet:
        combined = sheet if not base else f"{base}\n{sheet}"
        app.setStyleSheet(combined)
