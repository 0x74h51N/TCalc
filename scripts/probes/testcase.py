#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""A parametrized row of a Python test suite, read by its pytest node id instead of copied by hand."""

from __future__ import annotations

import contextlib
import io
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from functools import reduce

import pytest

from probes.rows import ProbeError

PATH_SEPARATOR = "."
TEST_PREFIX = "test."


@dataclass(frozen=True)
class TestRow:
    __test__ = False  # not a pytest test class, though its name starts with Test

    nodeid: str
    params: Mapping[str, object]


class _Collector:
    """A pytest plugin that keeps the items collection found."""

    def __init__(self) -> None:
        self.items: list[pytest.Item] = []

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.items = list(session.items)


def _row(item: pytest.Item) -> TestRow | None:
    # a test that is not parametrized has no callspec, so no row to read
    if not isinstance(item, pytest.Function) or not hasattr(item, "callspec"):
        return None
    return TestRow(item.nodeid, dict(item.callspec.params))


def collect(target: str, keyword: str | None) -> list[TestRow]:
    """The parametrized rows of a node id or file, as pytest's own collection finds them."""
    collector = _Collector()
    selection = ["-k", keyword] if keyword is not None else []
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        pytest.main(
            ["--collect-only", "-q", "-p", "no:cacheprovider", target, *selection],
            plugins=[collector],
        )
    rows = [row for row in map(_row, collector.items) if row is not None]
    if not rows:
        raise ProbeError(f"no parametrized case for {target}\n{output.getvalue()}")
    return rows


def _segments(path: str) -> tuple[str, list[str]]:
    name, *attributes = path.split(PATH_SEPARATOR)
    return name, attributes


def _path_error(row: TestRow, path: str, problem: str) -> ProbeError:
    return ProbeError(f"{path} of {row.nodeid} {problem}; its params are {', '.join(row.params)}")


def _attribute(row: TestRow, path: str) -> Callable[[object, str], object]:
    def read(value: object, name: str) -> object:
        if not hasattr(value, name):
            raise _path_error(row, path, "does not exist")
        return getattr(value, name)

    return read


def field(row: TestRow, path: str) -> str:
    """The input a path names in a row: a param (expr), or an attribute of one (case.expr)."""
    name, attributes = _segments(path)
    if name not in row.params:
        raise _path_error(row, path, "does not exist")
    value = reduce(_attribute(row, path), attributes, row.params[name])
    if not isinstance(value, str):
        raise _path_error(row, path, f"is a {type(value).__name__}, not an input text")
    return value


def _dataclass_fields(name: str, value: object, skip: str) -> list[tuple[str, str]]:
    if not is_dataclass(value) or isinstance(value, type):
        return []
    return [
        (f"{name}.{f.name}", str(getattr(value, f.name))) for f in fields(value) if f.name != skip
    ]


def beside(row: TestRow, path: str) -> tuple[tuple[str, str], ...]:
    """What the row claims besides its input, printed next to the probe's rows: the other params or attributes."""
    name, attributes = _segments(path)
    others = [(other, str(value)) for other, value in row.params.items() if other != name]
    siblings = _dataclass_fields(name, row.params[name], attributes[-1]) if attributes else []
    # prefixed, so a test's own expected never shares a column with the grader's
    return tuple((f"{TEST_PREFIX}{column}", text) for column, text in (*siblings, *others))


def rows_text(rows: list[TestRow]) -> str:
    """Each row's node id and params, to pick a --field from."""
    return "\n".join(
        f"{row.nodeid}  " + "  ".join(f"{name}={value!r}" for name, value in row.params.items())
        for row in rows
    )
