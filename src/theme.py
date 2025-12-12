#
# Central theme configuration
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Dict


class Theme:
    """Central theme configuration loaded from config.toml."""
    
    def __init__(self):
        self._config = self._load_config()
        self.colors = self._config["theme"]["colors"]
        self.spacing = self._config["theme"]["spacing"]
        self.fonts = self._config["theme"]["fonts"]

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        config_path = Path(__file__).parent.parent / "config.toml"
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
