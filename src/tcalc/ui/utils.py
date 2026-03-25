from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

ASSETS_DIR = Path.cwd() / "assets"


def rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#RRGGBB`` + alpha to a CSS ``rgba(...)`` string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def get_icon(icon_ref: str) -> QIcon:
    if not icon_ref:
        return QIcon()

    if icon_ref.startswith(":/"):
        icon = QIcon(icon_ref)
        return icon if not icon.isNull() else QIcon()

    path = Path(icon_ref)

    if path.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".ico"}:
        if not path.is_absolute():
            path = ASSETS_DIR / path.name

        icon = QIcon(str(path))
        return icon if not icon.isNull() else QIcon()

    icon = QIcon.fromTheme(icon_ref)
    return icon if not icon.isNull() else QIcon()
