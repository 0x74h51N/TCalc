#
# Central theme configuration
from __future__ import annotations

from pathlib import Path
from typing import Any

import tomllib


class Theme:
    """Central theme configuration loaded from config.toml."""

    colors: dict[str, Any]
    spacing: dict[str, Any]
    fonts: dict[str, Any]

    def __init__(self):
        config = self._load_config()
        theme_data: dict[str, Any] = config["theme"]
        self.colors = theme_data["colors"]
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
