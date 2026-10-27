#
# Central theme configuration
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import tomllib
from PySide6.QtCore import Qt


class ThemeMode(Enum):
    """User's theme choice; Qt holds it as a color scheme (Unknown = follow the OS)."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    KITTY = "kitty"  # bundled example custom theme

    @property
    def scheme(self) -> Qt.ColorScheme:
        return {
            ThemeMode.LIGHT: Qt.ColorScheme.Light,
            ThemeMode.DARK: Qt.ColorScheme.Dark,
            ThemeMode.KITTY: Qt.ColorScheme.Light,
        }.get(self, Qt.ColorScheme.Unknown)

    def variant(self, scheme: Qt.ColorScheme) -> str:
        """The theme variant to show while Qt's color scheme is *scheme*."""
        if self is ThemeMode.KITTY:
            return self.value
        return "light" if scheme == Qt.ColorScheme.Light else "dark"


class Theme:
    """Central theme configuration loaded from config.toml."""

    variant: str
    base: str
    keypad_image: str | None
    colors: dict[str, Any]
    spacing: dict[str, Any]

    def __init__(self, variant: str = "dark"):
        config = self._load_config()
        theme_data: dict[str, Any] = config["theme"]
        variant_data: dict[str, Any] = theme_data[variant]
        self.variant = variant
        # The light/dark family a custom variant builds on (variant icon files follow it)
        self.base = variant_data.get("base", variant)
        self.keypad_image = variant_data.get("keypad_image")
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
