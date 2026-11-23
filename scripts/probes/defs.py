#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Values defined once at the moment of use and named in many inputs as @NAME."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import takewhile

from probes.rows import ProbeError

# `@`, because a bare name is a TCalc variable the case may mean
MARKER = "@"
COMMENT = "#"


def _is_name(text: str) -> bool:
    """The one rule for a name, in a definition and after the marker."""
    return text.isascii() and text.isidentifier()


def _is_name_char(char: str) -> bool:
    # ASCII only: a name written next to π or Γ must end before it
    return char.isascii() and (char.isalnum() or char == "_")


def _is_entry(line: str) -> bool:
    text = line.strip()
    return bool(text) and not text.startswith(COMMENT)


def _definition(line: str) -> tuple[str, str]:
    name, equals, expr = line.partition("=")
    name = name.strip()
    if not equals or not _is_name(name):
        raise ProbeError(f"line {line!r}: expected NAME=EXPR")
    return name, expr.strip()


def parse_defs(lines: Iterable[str]) -> dict[str, str]:
    """NAME=EXPR per line; a blank line or a comment line is skipped."""
    return dict(_definition(line) for line in lines if _is_entry(line))


def _expand(after_marker: str, defs: Mapping[str, str], grouped: bool) -> str:
    """The text that follows one marker, with the name it starts with replaced by its EXPR."""
    name = "".join(takewhile(_is_name_char, after_marker))
    if not _is_name(name):
        raise ProbeError(f"{MARKER} names nothing before {after_marker!r}")
    if name not in defs:
        raise ProbeError(f"undefined {MARKER}{name}")
    value = f"({defs[name]})" if grouped else defs[name]
    return value + after_marker[len(name) :]


def substitute(text: str, defs: Mapping[str, str], grouped: bool) -> str:
    """Each @NAME becomes its EXPR; grouped as (EXPR), it keeps its place next to a digit or an
    operator, while a command that shows the form typed (editor, render) takes it as written."""
    head, *after_markers = text.split(MARKER)
    return "".join([head, *(_expand(piece, defs, grouped) for piece in after_markers)])
