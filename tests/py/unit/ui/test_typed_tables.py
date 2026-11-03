#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import copy
import dataclasses
import logging
import tomllib
from dataclasses import dataclass
from enum import Enum

import pytest
from pytest import param

from tcalc.typed_tables import TableError, build, override
from tcalc.ui.config import CONFIG, CONFIG_PATH, UiConfig


class Fit(Enum):
    CONTAIN = "contain"
    COVER = "cover"


@dataclass(frozen=True, slots=True)
class Inner:
    n: int


@dataclass(frozen=True, slots=True)
class Outer:
    i: int
    f: float
    s: str
    b: bool
    e: Fit
    t: tuple[str, ...]
    inner: Inner
    opt: str = "x"


GOOD = {
    "i": 1,
    "f": 0.5,
    "s": "a",
    "b": True,
    "e": "cover",
    "t": ["p", "q"],
    "inner": {"n": 2},
}
BUILT = Outer(1, 0.5, "a", True, Fit.COVER, ("p", "q"), Inner(2))


# (table, expected Outer or the TableError message)
@pytest.mark.parametrize(
    "table, expected",
    [
        param(GOOD, BUILT, id="all fields"),
        param({**GOOD, "f": 2}, dataclasses.replace(BUILT, f=2.0), id="int for float"),
        param(
            {**GOOD, "e": "contain"}, dataclasses.replace(BUILT, e=Fit.CONTAIN), id="enum by value"
        ),
        param(
            {**GOOD, "e": "CONTAIN"}, dataclasses.replace(BUILT, e=Fit.CONTAIN), id="enum by name"
        ),
        param({**GOOD, "opt": "y"}, dataclasses.replace(BUILT, opt="y"), id="default replaced"),
        param({k: v for k, v in GOOD.items() if k != "i"}, "outer.i: missing", id="missing key"),
        param({**GOOD, "z": 1}, "outer.z: unknown key", id="unknown key"),
        param({**GOOD, "i": "1"}, "outer.i: expected int, got str", id="wrong type"),
        param({**GOOD, "i": True}, "outer.i: expected int, got bool", id="bool for int"),
        param({**GOOD, "e": "fill"}, "outer.e: expected Fit, got str 'fill'", id="unknown enum"),
        param({**GOOD, "t": ["p", 1]}, "outer.t: expected str, got int", id="wrong item type"),
        param([GOOD], "outer: expected a table, got list", id="not a table"),
        param(
            {**GOOD, "inner": {"n": "2"}},
            "outer.inner.n: expected int, got str",
            id="nested wrong type",
        ),
    ],
)
def test_build(table, expected):
    if isinstance(expected, str):
        with pytest.raises(TableError) as error:
            build(Outer, table, "outer")
        assert str(error.value) == expected
    else:
        assert build(Outer, table, "outer") == expected


# (partial table, the fields that change, the warning or "")
@pytest.mark.parametrize(
    "table, changed, warning",
    [
        param({"i": 5, "inner": {"n": 7}}, {"i": 5, "inner": Inner(7)}, "", id="applies"),
        param({"i": 5, "z": 1}, {"i": 5}, "theme.z: unknown key", id="unknown key skipped"),
        param(
            {"i": "5", "s": "b"},
            {"s": "b"},
            "theme.i: expected int, got str",
            id="wrong type skipped",
        ),
        param(
            {"s": "b", "i": "5", "b": False},
            {"s": "b", "b": False},
            "theme.i: expected int, got str",
            id="good, wrong type, good",
        ),
        param([{"i": 5}], {}, "theme: expected a table, got list", id="not a table skipped"),
    ],
)
def test_override(table, changed, warning, caplog):
    with caplog.at_level(logging.WARNING, logger="tcalc.typed_tables"):
        result = override(BUILT, table, "theme")
    assert result == dataclasses.replace(BUILT, **changed)
    assert [r.getMessage() for r in caplog.records] == ([warning] if warning else [])


def _loaded_config() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def test_config_toml_builds():
    assert build(UiConfig, _loaded_config(), "config") == CONFIG


# (change to a copy of config.toml, the TableError message)
@pytest.mark.parametrize(
    "change, message",
    [
        param(
            lambda c: c["calc"]["display"]["result"].pop("btn_size"),
            "config.calc.display.result.btn_size: missing",
            id="missing key",
        ),
        param(
            lambda c: c["window"].update(extra=1),
            "config.window.extra: unknown key",
            id="unknown key",
        ),
        param(
            lambda c: c["toast"].update(pad_y="6"),
            "config.toast.pad_y: expected int, got str",
            id="wrong type",
        ),
    ],
)
def test_config_toml_mistake_names_its_key(change, message):
    config = copy.deepcopy(_loaded_config())
    change(config)
    with pytest.raises(TableError) as error:
        build(UiConfig, config, "config")
    assert str(error.value) == message
