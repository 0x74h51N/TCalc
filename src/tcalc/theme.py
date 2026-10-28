#
# Central theme configuration: one config file per theme
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt

from tcalc.ui.config import color_usage_config

# Built-in themes ship with the package: tcalc/themes/<variant>.toml
BUILT_IN_DIR = Path(__file__).parent / "themes"
BUILT_IN_VARIANTS = ("light", "dark")
# Custom themes live outside the package, one folder each: themes/<variant>/theme.toml plus
# its own assets (pictures, fonts)
CUSTOM_THEMES_DIR = Path.cwd() / "themes"


class ThemeMode(Enum):
    """Kind of theme the user chose; Qt holds built-in ones as a color scheme."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class ThemeChoice:
    """The user's theme: a built-in mode, or a custom theme file (*custom*, mode CUSTOM)."""

    mode: ThemeMode = ThemeMode.SYSTEM
    custom: str = ""

    @property
    def scheme(self) -> Qt.ColorScheme:
        """The color scheme to ask Qt for (Unknown = follow the OS)."""
        match self.mode:
            case ThemeMode.LIGHT:
                return Qt.ColorScheme.Light
            case ThemeMode.DARK:
                return Qt.ColorScheme.Dark
            case ThemeMode.CUSTOM:
                return Theme(self.custom).scheme
        return Qt.ColorScheme.Unknown

    def variant(self, scheme: Qt.ColorScheme) -> str:
        """The theme variant to show while Qt's color scheme is *scheme*."""
        if self.mode is ThemeMode.CUSTOM:
            return self.custom
        return "light" if scheme == Qt.ColorScheme.Light else "dark"


class PictureTarget(Enum):
    """Component a theme picture is painted behind."""

    WINDOW = "window"  # the whole window, behind every component
    DISPLAY = "display"
    HISTORY = "history"
    MAIN_KEYPAD = "main_keypad"
    FUNCTIONS_KEYPAD = "functions_keypad"
    TRIG_KEYPAD = "trig_keypad"
    CUSTOM_PAD = "custom_pad"


class PicturePosition(Enum):
    """Where the picture sits in its component."""

    CENTER = "center"
    TOP_LEFT = "top-left"
    TOP = "top"
    TOP_RIGHT = "top-right"
    LEFT = "left"
    RIGHT = "right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM = "bottom"
    BOTTOM_RIGHT = "bottom-right"

    @property
    def alignment(self) -> Qt.AlignmentFlag:
        a = Qt.AlignmentFlag
        return {
            PicturePosition.CENTER: a.AlignCenter,
            PicturePosition.TOP_LEFT: a.AlignTop | a.AlignLeft,
            PicturePosition.TOP: a.AlignTop | a.AlignHCenter,
            PicturePosition.TOP_RIGHT: a.AlignTop | a.AlignRight,
            PicturePosition.LEFT: a.AlignVCenter | a.AlignLeft,
            PicturePosition.RIGHT: a.AlignVCenter | a.AlignRight,
            PicturePosition.BOTTOM_LEFT: a.AlignBottom | a.AlignLeft,
            PicturePosition.BOTTOM: a.AlignBottom | a.AlignHCenter,
            PicturePosition.BOTTOM_RIGHT: a.AlignBottom | a.AlignRight,
        }[self]


class PictureFit(Enum):
    """How the picture fills its box."""

    CONTAIN = "contain"  # whole picture, aspect kept
    COVER = "cover"  # fills the box, aspect kept, overflow cropped
    STRETCH = "stretch"  # fills the box exactly

    @property
    def aspect_mode(self) -> Qt.AspectRatioMode:
        return {
            PictureFit.CONTAIN: Qt.AspectRatioMode.KeepAspectRatio,
            PictureFit.COVER: Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            PictureFit.STRETCH: Qt.AspectRatioMode.IgnoreAspectRatio,
        }[self]


@dataclass(frozen=True, slots=True)
class ThemePicture:
    """A [[pictures]] entry of a theme config file."""

    file: Path
    target: PictureTarget
    position: PicturePosition = PicturePosition.CENTER
    size: float = 1.0  # box size as a fraction of the component's width and height
    fit: PictureFit = PictureFit.CONTAIN
    opacity: float = 1.0
    margin: int = 0  # px from the component's edges
    tint: str = ""  # theme color key to repaint the picture in; empty keeps its colors

    @classmethod
    def from_config(cls, folder: Path, table: dict[str, Any]) -> ThemePicture:
        return cls(
            file=folder / table["file"],
            target=PictureTarget(table["target"]),
            position=PicturePosition(table.get("position", PicturePosition.CENTER.value)),
            size=float(table.get("size", 1.0)),
            fit=PictureFit(table.get("fit", PictureFit.CONTAIN.value)),
            opacity=float(table.get("opacity", 1.0)),
            margin=int(table.get("margin", 0)),
            tint=table.get("tint", ""),
        )


def custom_themes() -> dict[str, str]:
    """Custom theme variants found in themes/, mapped to their display names."""
    return {
        path.parent.name: Theme(path.parent.name).name
        for path in sorted(CUSTOM_THEMES_DIR.glob("*/theme.toml"))
    }


class Theme:
    """A theme: colors, spacing (corner radii...) and font overrides from its config file."""

    variant: str
    name: str
    base: str
    pictures: tuple[ThemePicture, ...]
    fonts: dict[str, Any]
    colors: dict[str, Any]
    color_usage: dict[str, str]
    spacing: dict[str, Any]

    def __init__(self, variant: str = "dark"):
        data = _read(variant)
        self.variant = variant
        self.name = data["name"]
        # A custom theme builds on a built-in one (Qt's color scheme, variant icon files) and
        # its file holds only what differs from it
        self.base = data.get("base", variant)
        base = _read(self.base) if self.base != variant else {}
        # Pictures behind components, from files in the theme's folder
        self.pictures = tuple(
            ThemePicture.from_config(CUSTOM_THEMES_DIR / variant, table)
            for table in data.get("pictures", [])
        )
        # Overrides of the UI config's [fonts]
        self.fonts = {**base.get("fonts", {}), **data.get("fonts", {})}
        self.colors = {**base.get("colors", {}), **data.get("colors", {})}
        # Which color each place uses: the UI config's [color_usage] with the theme's overrides
        self.color_usage = {
            **color_usage_config,
            **base.get("color_usage", {}),
            **data.get("color_usage", {}),
        }
        self.spacing = {**base.get("spacing", {}), **data.get("spacing", {})}

    def color(self, place: str) -> str:
        """The color *place* uses (a [color_usage] name)."""
        return self.colors[self.color_usage[place]]

    @property
    def scheme(self) -> Qt.ColorScheme:
        return Qt.ColorScheme.Light if self.base == "light" else Qt.ColorScheme.Dark


def _read(variant: str) -> dict[str, Any]:
    if variant in BUILT_IN_VARIANTS:
        path = BUILT_IN_DIR / f"{variant}.toml"
    else:
        path = CUSTOM_THEMES_DIR / variant / "theme.toml"
    with open(path, "rb") as f:
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
    """Replace the global theme with *variant* (a built-in or custom theme)."""
    global _theme_instance
    _theme_instance = Theme(variant)
    return _theme_instance
