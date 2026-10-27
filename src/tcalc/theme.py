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

    @property
    def scheme(self) -> Qt.ColorScheme:
        return {
            ThemeMode.LIGHT: Qt.ColorScheme.Light,
            ThemeMode.DARK: Qt.ColorScheme.Dark,
        }.get(self, Qt.ColorScheme.Unknown)


class Theme:
    """Central theme configuration loaded from config.toml."""

    variant: str
    colors: dict[str, Any]
    spacing: dict[str, Any]
    fonts: dict[str, Any]

    def __init__(self, variant: str = "dark"):
        config = self._load_config()
        theme_data: dict[str, Any] = config["theme"]
        self.variant = variant
        # Only the active variant's colors are kept
        self.colors = theme_data[variant]["colors"]
        self.spacing = theme_data["spacing"]
        self.fonts = theme_data["fonts"]

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
    """Replace the global theme with *variant* ("dark" or "light")."""
    global _theme_instance
    _theme_instance = Theme(variant)
    return _theme_instance
