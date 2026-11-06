#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from pytest import param


class FakeError(Exception):
    pass


class FakeMode(Enum):
    LIGHT = "fake light"
    DARK = "fake dark"
    SYSTEM = "system"
    CUSTOM = "custom"


def _messages(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records]


def _bare_theme(colors: dict[str, str]):
    from tcalc.theme import Theme

    theme = Theme.__new__(Theme)
    theme.variant, theme.colors = "x", colors
    return theme


def test_read_a_custom_theme(tmp_path, monkeypatch):
    from tcalc.theme import _read

    (tmp_path / "theme.toml").write_text('name = "x"')
    monkeypatch.setattr("tcalc.theme._folder", lambda _variant: tmp_path)
    assert _read("x") == {"name": "x"}


def test_read_a_built_in_theme(tmp_path, monkeypatch):
    from tcalc.theme import _read

    (tmp_path / "built-in.toml").write_text('name = "d"')
    monkeypatch.setattr("tcalc.theme.BUILT_IN_DIR", tmp_path)
    monkeypatch.setattr("tcalc.theme.BUILT_IN_VARIANTS", ("built-in",))
    assert _read("built-in") == {"name": "d"}


@pytest.mark.parametrize("text", [param("[", id="bad toml"), param(None, id="no file")])
def test_read_raises_on_a_file_it_cannot_use(tmp_path, monkeypatch, text):
    from tcalc.theme import _read

    if text is not None:
        (tmp_path / "theme.toml").write_text(text)
    monkeypatch.setattr("tcalc.theme._folder", lambda _variant: tmp_path)
    monkeypatch.setattr("tcalc.theme.ThemeError", FakeError)
    with pytest.raises(FakeError):
        _read("x")


def test_folder_takes_the_user_theme_first(tmp_path, monkeypatch):
    from tcalc.theme import _folder

    (tmp_path / "user/x").mkdir(parents=True)
    (tmp_path / "user/x/theme.toml").touch()
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: tmp_path / "user")
    assert _folder("x") == tmp_path / "user/x"


def test_folder_falls_back_to_the_bundled_one(tmp_path, monkeypatch):
    from tcalc.theme import _folder

    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: tmp_path / "user")
    monkeypatch.setattr("tcalc.theme.BUILT_IN_DIR", tmp_path / "built_in")
    assert _folder("x") == tmp_path / "built_in/x"


@dataclass(frozen=True, slots=True)
class FoldersCase:
    built_in: tuple[str, ...]
    user: tuple[str, ...]
    expected: dict[str, str]


@pytest.mark.parametrize(
    "case",
    [
        param(FoldersCase((), (), {}), id="none"),
        param(FoldersCase(("a",), (), {"a": "built_in"}), id="bundled"),
        param(FoldersCase((), ("a",), {"a": "user"}), id="user"),
        param(FoldersCase(("a",), ("a",), {"a": "user"}), id="user replaces bundled"),
    ],
)
def test_custom_theme_folders(case, tmp_path, monkeypatch):
    from tcalc.theme import custom_theme_folders

    for root, names in (("built_in", case.built_in), ("user", case.user)):
        (tmp_path / root).mkdir()
        for name in names:
            (tmp_path / root / name).mkdir()
            (tmp_path / root / name / "theme.toml").touch()
    monkeypatch.setattr("tcalc.theme.BUILT_IN_DIR", tmp_path / "built_in")
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: tmp_path / "user")
    assert custom_theme_folders() == {k: tmp_path / v / k for k, v in case.expected.items()}


def test_custom_theme_folders_skips_a_folder_with_no_theme_file(tmp_path, monkeypatch):
    from tcalc.theme import custom_theme_folders

    (tmp_path / "empty").mkdir()
    monkeypatch.setattr("tcalc.theme.BUILT_IN_DIR", tmp_path)
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: tmp_path / "none")
    assert custom_theme_folders() == {}


class FakeListedTheme:
    def __init__(self, variant):
        if variant == "broken":
            raise FakeError("bad")
        self.name = variant.title()


def test_custom_themes_leaves_a_broken_one_out(monkeypatch, caplog):
    from tcalc.theme import custom_themes

    monkeypatch.setattr("tcalc.theme.custom_theme_folders", lambda: {"good": 1, "broken": 2})
    monkeypatch.setattr("tcalc.theme.Theme", FakeListedTheme)
    monkeypatch.setattr("tcalc.theme.ThemeError", FakeError)
    with caplog.at_level(logging.WARNING):
        assert custom_themes() == {"good": "Good"}
    assert _messages(caplog) == ["Skipping theme broken: bad"]


def test_opaque(caplog):
    from tcalc.theme import _opaque

    colors = {"a": "#000000", "b": "#80123456", "c": "nope", "screen": "qlineargradient(x)"}
    with caplog.at_level(logging.WARNING):
        kept = _opaque(colors, "t")
    assert kept == {"a": "#000000", "screen": "qlineargradient(x)"}
    assert _messages(caplog) == [
        "t [colors].b: '#80123456' is not an opaque color",
        "t [colors].c: 'nope' is not an opaque color",
    ]


@dataclass
class FakeInnerTable:
    a: int
    b: int


@dataclass
class FakeOuterTable:
    inner: FakeInnerTable
    c: int


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        param(("c",), FakeOuterTable(FakeInnerTable(1, 2), 9), id="top"),
        param(("inner", "a"), FakeOuterTable(FakeInnerTable(9, 2), 3), id="nested"),
    ],
)
def test_restored(path, expected):
    from tcalc.theme import _restored

    table = FakeOuterTable(FakeInnerTable(1, 2), 3)
    default = FakeOuterTable(FakeInnerTable(9, 9), 9)
    assert _restored(table, default, path) == expected


@pytest.mark.parametrize(
    ("mode", "scheme"),
    [
        param(FakeMode.LIGHT, Qt.ColorScheme.Light, id="light"),
        param(FakeMode.DARK, Qt.ColorScheme.Dark, id="dark"),
        param(FakeMode.SYSTEM, Qt.ColorScheme.Unknown, id="system"),
        param(FakeMode.CUSTOM, Qt.ColorScheme.Light, id="custom asks for its base's"),
    ],
)
def test_choice_scheme(monkeypatch, mode, scheme):
    from tcalc.theme import ThemeChoice

    monkeypatch.setattr("tcalc.theme.ThemeMode", FakeMode)
    monkeypatch.setattr(
        "tcalc.theme.Theme", lambda _variant: SimpleNamespace(scheme=Qt.ColorScheme.Light)
    )
    assert ThemeChoice(mode, "x").scheme == scheme


@dataclass(frozen=True, slots=True)
class ChoiceVariantCase:
    mode: FakeMode
    scheme: Qt.ColorScheme
    variant: str


@pytest.mark.parametrize(
    "case",
    [
        param(ChoiceVariantCase(FakeMode.SYSTEM, Qt.ColorScheme.Light, "light"), id="system light"),
        param(ChoiceVariantCase(FakeMode.SYSTEM, Qt.ColorScheme.Dark, "dark"), id="system dark"),
        param(ChoiceVariantCase(FakeMode.SYSTEM, Qt.ColorScheme.Unknown, "dark"), id="system none"),
        # Right after setColorScheme Qt may still report the old scheme
        param(
            ChoiceVariantCase(FakeMode.LIGHT, Qt.ColorScheme.Dark, "fake light"), id="light stays"
        ),
        param(ChoiceVariantCase(FakeMode.DARK, Qt.ColorScheme.Light, "fake dark"), id="dark stays"),
        param(ChoiceVariantCase(FakeMode.CUSTOM, Qt.ColorScheme.Dark, "x"), id="custom"),
    ],
)
def test_choice_variant(monkeypatch, case):
    from tcalc.theme import ThemeChoice

    monkeypatch.setattr("tcalc.theme.ThemeMode", FakeMode)
    assert ThemeChoice(case.mode, "x").variant(case.scheme) == case.variant


THEME_FILES = {
    "user": {
        "name": "User",
        "base": "built-in",
        "colors": {"a": "#111111"},
        "pictures": ["p"],
        "keypad": {"size": 1},
    },
    "built-in": {"name": "Built in", "colors": {"a": "#000000", "b": "#222222"}},
    "no name": {"base": "built-in"},
    "no base": {"name": "N"},
    "bad base": {"name": "B", "base": "blue"},
}


@pytest.fixture
def theme_parts(monkeypatch):
    from tcalc.theme import Theme

    monkeypatch.setattr("tcalc.theme.ThemeError", FakeError)
    monkeypatch.setattr("tcalc.theme.BUILT_IN_VARIANTS", ("built-in",))
    monkeypatch.setattr("tcalc.theme._read", THEME_FILES.__getitem__)
    monkeypatch.setattr("tcalc.theme.values", lambda table, _kind, _where: table)
    monkeypatch.setattr("tcalc.theme._opaque", lambda colors, _where: colors)
    monkeypatch.setattr("tcalc.theme.DEFAULT_LOOK", "default")
    monkeypatch.setattr("tcalc.theme.with_shared_buttons", lambda table: table)
    monkeypatch.setattr("tcalc.theme.override", lambda default, table, _where: (default, table))
    monkeypatch.setattr(Theme, "_known_colors", lambda _self, look, _where: look)
    monkeypatch.setattr(Theme, "_pictures", lambda _self, entries, _where: tuple(entries))


@pytest.mark.usefixtures("theme_parts")
def test_theme_init_builds_on_its_base():
    from tcalc.theme import Theme

    theme = Theme("user")
    assert (theme.variant, theme.name, theme.base) == ("user", "User", "built-in")
    assert theme.colors == {"a": "#111111", "b": "#222222"}
    assert theme.look == ("default", {"keypad": {"size": 1}})
    assert theme.pictures == ("p",)


@pytest.mark.usefixtures("theme_parts")
def test_theme_init_a_built_in_is_its_own_base():
    from tcalc.theme import Theme

    theme = Theme("built-in")
    assert theme.base == "built-in" and theme.colors == {"a": "#000000", "b": "#222222"}


@pytest.mark.usefixtures("theme_parts")
@pytest.mark.parametrize(
    ("variant", "message"),
    [
        param("no name", "no name", id="no name"),
        param("no base", "base must be", id="no base"),
        param("bad base", "base must be", id="bad base"),
    ],
)
def test_theme_init_refuses(variant, message):
    from tcalc.theme import Theme

    with pytest.raises(FakeError, match=message):
        Theme(variant)


@dataclass(frozen=True, slots=True)
class FakeColorField:
    path: tuple[str, ...]
    color: str
    opacity: float = 1.0


@dataclass(frozen=True, slots=True)
class FakeValueField:
    path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class KnownColorsCase:
    field: FakeColorField | FakeValueField
    look: object
    logged: tuple[str, ...]


RESTORED = ("restored", ("p",))


@pytest.mark.parametrize(
    "case",
    [
        param(KnownColorsCase(FakeColorField(("p",), "a"), "look", ()), id="known"),
        param(KnownColorsCase(FakeColorField(("p",), "a", 0.5), "look", ()), id="known, opacity"),
        param(KnownColorsCase(FakeValueField(("p",)), "look", ()), id="not a color"),
        param(
            KnownColorsCase(
                FakeColorField(("p",), "nope"), RESTORED, ("w.p: 'nope' is not one of its colors",)
            ),
            id="unknown",
        ),
        param(
            KnownColorsCase(
                FakeColorField(("p",), "g", 0.5),
                RESTORED,
                ("w.p: 'g' is a gradient, it cannot take an opacity",),
            ),
            id="gradient with an opacity",
        ),
    ],
)
def test_known_colors(monkeypatch, caplog, case):
    monkeypatch.setattr("tcalc.theme.look_fields", lambda _look: [case.field])
    monkeypatch.setattr("tcalc.theme.ColorField", FakeColorField)
    monkeypatch.setattr("tcalc.theme.DEFAULT_LOOK", "default")
    monkeypatch.setattr("tcalc.theme._restored", lambda _l, _d, path: ("restored", path))
    theme = _bare_theme({"a": "#111111", "g": "qlineargradient(x)"})
    with caplog.at_level(logging.WARNING):
        assert theme._known_colors("look", "w") == case.look
    assert tuple(_messages(caplog)) == case.logged


@dataclass(frozen=True, slots=True)
class FakePicture:
    file: Path
    tint: str


def _fake_build(_cls, entry, where):
    if entry == "bad":
        raise FakeError(f"{where}: refused")
    return FakePicture(Path("a.svg"), entry)


@dataclass(frozen=True, slots=True)
class PicturesCase:
    entries: object
    tints: tuple[str, ...]
    logged: tuple[str, ...]


@pytest.mark.parametrize(
    "case",
    [
        param(PicturesCase(["c"], ("c",), ()), id="good, tinted"),
        param(PicturesCase([""], ("",), ()), id="good, no tint"),
        param(PicturesCase("x", (), ("w: expected a list, got str",)), id="not a list"),
        param(PicturesCase(["bad", "c"], ("c",), ("w #1: refused",)), id="refused entry"),
        param(
            PicturesCase(["nope"], (), ("w #1.tint: 'nope' is not one of its colors",)),
            id="unknown tint",
        ),
    ],
)
def test_pictures(monkeypatch, caplog, case):
    monkeypatch.setattr("tcalc.theme.build", _fake_build)
    monkeypatch.setattr("tcalc.theme.TableError", FakeError)
    monkeypatch.setattr("tcalc.theme._folder", lambda _variant: Path("root"))
    with caplog.at_level(logging.WARNING):
        pictures = _bare_theme({"c": "#111111"})._pictures(case.entries, "w")
    assert pictures == tuple(FakePicture(Path("root/a.svg"), tint) for tint in case.tints)
    assert tuple(_messages(caplog)) == case.logged


def test_qcolor():
    assert _bare_theme({"a": "#123456"}).qcolor("a") == QColor("#123456")


@pytest.mark.parametrize(
    ("base", "scheme"),
    [
        param("light", Qt.ColorScheme.Light, id="light"),
        param("dark", Qt.ColorScheme.Dark, id="dark"),
    ],
)
def test_theme_scheme(base, scheme):
    theme = _bare_theme({})
    theme.base = base
    assert theme.scheme == scheme


class FakeGlobalTheme:
    def __init__(self, variant="default"):
        self.variant = variant


@pytest.fixture
def no_global_theme(monkeypatch):
    monkeypatch.setattr("tcalc.theme.Theme", FakeGlobalTheme)
    monkeypatch.setattr("tcalc.theme._theme_instance", None)


@pytest.mark.usefixtures("no_global_theme")
def test_get_theme_creates_the_default_once():
    from tcalc.theme import get_theme

    first = get_theme()
    assert first.variant == "default"
    assert get_theme() is first


@pytest.mark.usefixtures("no_global_theme")
def test_load_theme_replaces_the_global():
    from tcalc.theme import get_theme
    from tcalc.theme import load_theme

    get_theme()
    loaded = load_theme("x")
    assert loaded.variant == "x"
    assert get_theme() is loaded
