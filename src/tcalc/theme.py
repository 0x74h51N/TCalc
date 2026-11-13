#
# Central theme configuration: one config file per theme
from __future__ import annotations

import dataclasses
import logging
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QColor

from tcalc.typed_tables import TableError, Toml, build, override, values
from tcalc.ui.look import (
    DEFAULT_LOOK,
    ColorField,
    ColorName,
    Look,
    look_fields,
    with_shared_buttons,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_log = logging.getLogger(__name__)


def _opaque(colors: dict[str, str], where: str) -> dict[str, str]:
    # Opacity belongs to the place that uses a color; a theme that writes it here gets its base's
    kept = {}
    for name, value in colors.items():
        color = QColor(value)
        if (name == "screen" and "gradient" in value) or (color.isValid() and color.alpha() == 255):
            kept[name] = value
        else:
            _log.warning("%s [colors].%s: %r is not an opaque color", where, name, value)
    return kept


# Themes that ship with the package: Light and Dark as tcalc/themes/<variant>.toml, and the
# example custom themes as tcalc/themes/<variant>/theme.toml with their own assets
BUILT_IN_DIR = Path(__file__).parent / "themes"
BUILT_IN_VARIANTS = ("light", "dark")


def user_themes_dir() -> Path:
    """The user's own custom themes, one folder each, next to the app's other data."""
    location = QStandardPaths.StandardLocation.AppDataLocation
    return Path(QStandardPaths.writableLocation(location)) / "themes"


def custom_theme_folders() -> dict[str, Path]:
    """Every custom theme's folder by variant; a user theme replaces a bundled one."""
    folders: dict[str, Path] = {}
    for root in (BUILT_IN_DIR, user_themes_dir()):
        for path in root.glob("*/theme.toml"):
            folders[path.parent.name] = path.parent
    return dict(sorted(folders.items()))


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
        # Read before the match: mypy types the value of a narrowed member as Any
        built_in = self.mode.value
        match self.mode:
            case ThemeMode.LIGHT | ThemeMode.DARK:
                return built_in
            case ThemeMode.CUSTOM:
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
    tint: ColorName = ColorName("")  # theme color to repaint the picture in; empty keeps its colors


class ThemeError(Exception):
    """A theme file that cannot be used."""


def custom_themes() -> dict[str, str]:
    """Custom theme variants mapped to their display names; a broken theme is left out so
    it cannot stop the app."""
    themes: dict[str, str] = {}
    for variant in custom_theme_folders():
        try:
            themes[variant] = Theme(variant).name
        except ThemeError as e:
            _log.warning("Skipping theme %s: %s", variant, e)
    return themes


class Theme:
    """A theme: its colors, and the look with its overrides, resolved once on load."""

    variant: str
    name: str
    base: str
    colors: dict[ColorName, str]
    look: Look
    pictures: tuple[ThemePicture, ...]

    def __init__(self, variant: str = "dark") -> None:
        data = _read(variant)
        self.variant = variant
        if "name" not in data:
            raise ThemeError("no name")
        name = data["name"]
        if not isinstance(name, str):
            raise ThemeError(f"name must be text, not {name!r}")
        self.name = name
        # A custom theme builds on a built-in one (Qt's color scheme, variant icon files) and
        # its file holds only what differs from it
        base_variant = data.get("base", variant if variant in BUILT_IN_VARIANTS else "")
        if not isinstance(base_variant, str) or base_variant not in BUILT_IN_VARIANTS:
            raise ThemeError(f"base must be one of {BUILT_IN_VARIANTS}, not {base_variant!r}")
        self.base = base_variant
        base = _read(self.base) if self.base != variant else {}
        where = f"theme {variant}"
        colors = {
            **values(base.get("colors", {}), str, f"theme {self.base} [colors]"),
            **_opaque(values(data.get("colors", {}), str, f"{where} [colors]"), where),
        }
        self.colors = {ColorName(name): color for name, color in colors.items()}
        look = override(
            DEFAULT_LOOK,
            with_shared_buttons(
                {k: v for k, v in data.items() if k not in ("name", "base", "colors", "pictures")},
            ),
            where,
        )
        self.look = self._known_colors(look, where)
        self.pictures = self._pictures(data.get("pictures", []), f"{where} [[pictures]]")

    def _known_colors(self, look: Look, where: str) -> Look:
        """*look* with each place naming a color the theme lacks set back to the default's."""
        for field in look_fields(look):
            if not isinstance(field, ColorField):
                continue
            place = ".".join(field.path)
            if field.color not in self.colors:
                _log.warning("%s.%s: %r is not one of its colors", where, place, field.color)
                look = _restored(look, DEFAULT_LOOK, field.path)
            elif field.opacity != 1.0 and not QColor(self.colors[field.color]).isValid():
                _log.warning(
                    "%s.%s: %r is a gradient, it cannot take an opacity", where, place, field.color
                )
                look = _restored(look, DEFAULT_LOOK, field.path)
        return look

    def _pictures(self, entries: object, where: str) -> tuple[ThemePicture, ...]:
        if not isinstance(entries, list):
            _log.warning("%s: expected a list, got %s", where, type(entries).__name__)
            return ()
        pictures = []
        for n, entry in enumerate(entries, 1):
            try:
                picture = build(ThemePicture, entry, f"{where} #{n}")
            except TableError as error:
                _log.warning("%s", error)
                continue
            if picture.tint and picture.tint not in self.colors:
                _log.warning("%s #%d.tint: %r is not one of its colors", where, n, picture.tint)
                continue
            pictures.append(dataclasses.replace(picture, file=_folder(self.variant) / picture.file))
        return tuple(pictures)

    def qcolor(self, name: ColorName) -> QColor:
        """Theme color *name* as a QColor."""
        return QColor(self.colors[name])

    @property
    def scheme(self) -> Qt.ColorScheme:
        return Qt.ColorScheme.Light if self.base == "light" else Qt.ColorScheme.Dark


def _restored[T: DataclassInstance](table: T, default: T, path: tuple[str, ...]) -> T:
    """*table* with the field at *path* taken from *default*."""
    key, *rest = path
    value = getattr(default, key)
    if rest:
        value = _restored(getattr(table, key), value, tuple(rest))
    return dataclasses.replace(table, **{key: value})


def _folder(variant: str) -> Path:
    user = user_themes_dir() / variant
    return user if (user / "theme.toml").exists() else BUILT_IN_DIR / variant


def _read(variant: str) -> dict[str, Toml]:
    if variant in BUILT_IN_VARIANTS:
        path = BUILT_IN_DIR / f"{variant}.toml"
    else:
        path = _folder(variant) / "theme.toml"
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ThemeError(f"{path}: {e}") from e


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
