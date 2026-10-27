#
# Central theme configuration
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import tomllib
from PySide6.QtCore import Qt

# Theme pictures: assets/themes/<theme name>/
THEMES_DIR = Path.cwd() / "assets" / "themes"


class ThemeMode(Enum):
    """User's theme choice; Qt holds it as a color scheme (Unknown = follow the OS)."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    # Bundled example custom themes
    KITTY = "kitty"
    OCEAN = "ocean"

    @property
    def scheme(self) -> Qt.ColorScheme:
        return {
            ThemeMode.LIGHT: Qt.ColorScheme.Light,
            ThemeMode.DARK: Qt.ColorScheme.Dark,
            ThemeMode.KITTY: Qt.ColorScheme.Light,
            ThemeMode.OCEAN: Qt.ColorScheme.Dark,
        }.get(self, Qt.ColorScheme.Unknown)

    def variant(self, scheme: Qt.ColorScheme) -> str:
        """The theme variant to show while Qt's color scheme is *scheme*."""
        if self in (ThemeMode.LIGHT, ThemeMode.DARK, ThemeMode.SYSTEM):
            return "light" if scheme == Qt.ColorScheme.Light else "dark"
        return self.value  # a custom theme is its own variant


class Theme:
    """Central theme configuration loaded from config.toml."""

    variant: str
    base: str
    keypad_image: Path
    colors: dict[str, Any]
    spacing: dict[str, Any]

    def __init__(self, variant: str = "dark"):
        config = self._load_config()
        theme_data: dict[str, Any] = config["theme"]
        variant_data: dict[str, Any] = theme_data[variant]
        self.variant = variant
        # The light/dark family a custom variant builds on (variant icon files follow it)
        self.base = variant_data.get("base", variant)
        # Shown behind the main keypad when the file exists
        self.keypad_image = THEMES_DIR / variant / "keypad.png"
        # Only the active variant's colors are kept
        self.colors = variant_data["colors"]
        self.spacing = theme_data["spacing"]

    @staticmethod
    def _load_config() -> dict[str, Any]:
        config_path = Path(__file__).parent / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f)


# Singleton instance
_theme_instance: Theme | None = None


def get_theme() -> Theme:
    """Get the global theme instance."""
    global _theme_instance
    if _theme_instance is None:
        _theme_instance = Theme()
    return _theme_instance


def load_theme(variant: str) -> Theme:
    """Replace the global theme with *variant* (a ``[theme.<variant>]`` table)."""
    global _theme_instance
    _theme_instance = Theme(variant)
    return _theme_instance
