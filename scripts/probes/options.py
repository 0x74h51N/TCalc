#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The options every probe command shares, declared once.

Each field of Options carries its argument in its metadata; the parser is built from those
declarations and Options is read back by the same field names, so an option lives in one place.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field, fields
from enum import Enum, auto
from pathlib import Path

from probes.defs import parse_defs, substitute
from probes.rows import ProbeError
from probes.testcase import beside, collect
from probes.testcase import field as row_field

STDIN = "-"
_ARG = "arg"


@dataclass(frozen=True)
class Positional:
    """The cases, given as positional arguments."""

    help: str
    metavar: str


class FlagKind(Enum):
    REPEATED = auto()
    PATH = auto()
    SWITCH = auto()
    TEXT = auto()


@dataclass(frozen=True)
class Flag:
    flag: str
    kind: FlagKind
    help: str
    metavar: str | None = None


def _declare(arg: Positional | Flag) -> dict[str, Positional | Flag]:
    return {_ARG: arg}


@dataclass(frozen=True)
class Options:
    inputs: list[str] = field(
        metadata=_declare(Positional(f"the cases; {STDIN} reads one per line from stdin", "INPUT"))
    )
    define: list[str] = field(
        metadata=_declare(
            Flag("--def", FlagKind.REPEATED, "name a value, used in an input as @NAME", "NAME=EXPR")
        )
    )
    defs: Path | None = field(
        metadata=_declare(Flag("--defs", FlagKind.PATH, "a file of NAME=EXPR lines", "FILE"))
    )
    ref: bool = field(
        metadata=_declare(Flag("--ref", FlagKind.SWITCH, "grade each value against python-flint"))
    )
    test: str | None = field(
        metadata=_declare(
            Flag(
                "--test",
                FlagKind.TEXT,
                "take the cases from a test's parametrized rows, by pytest node id or file",
                "NODEID",
            )
        )
    )
    keyword: str | None = field(
        metadata=_declare(
            Flag("-k", FlagKind.TEXT, "the rows of --test that pytest's -k selects", "EXPR")
        )
    )
    field: str | None = field(
        metadata=_declare(
            Flag(
                "--field",
                FlagKind.TEXT,
                "the param of each --test row that is the input, or its attribute (case.expr); "
                "without it the rows are listed and nothing runs",
                "PATH",
            )
        )
    )


def _add_flag(parser: argparse.ArgumentParser, dest: str, flag: Flag) -> None:
    match flag.kind:
        case FlagKind.REPEATED:
            parser.add_argument(
                flag.flag,
                dest=dest,
                action="append",
                default=[],
                help=flag.help,
                metavar=flag.metavar,
            )
        case FlagKind.PATH:
            parser.add_argument(
                flag.flag, dest=dest, type=Path, help=flag.help, metavar=flag.metavar
            )
        case FlagKind.SWITCH:
            parser.add_argument(flag.flag, dest=dest, action="store_true", help=flag.help)
        case FlagKind.TEXT:
            parser.add_argument(flag.flag, dest=dest, help=flag.help, metavar=flag.metavar)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """One argument per Options field, as the field declares it."""
    for f in fields(Options):
        arg = f.metadata[_ARG]
        if isinstance(arg, Positional):
            parser.add_argument(f.name, nargs="*", help=arg.help, metavar=arg.metavar)
        else:
            # metadata is untyped; _declare only ever stores a Positional or a Flag
            assert isinstance(arg, Flag)
            _add_flag(parser, f.name, arg)


def options_from(namespace: argparse.Namespace) -> Options:
    # argparse's namespace is untyped; this is the one place it is read
    return Options(**{f.name: getattr(namespace, f.name) for f in fields(Options)})


def _stdin_lines() -> list[str]:
    return [line for line in sys.stdin.read().splitlines() if line.strip()]


@dataclass(frozen=True)
class Input:
    text: str
    # what a test row claims besides its input (expected value, type), printed beside the probe's rows
    beside: tuple[tuple[str, str], ...] = ()


def _typed_inputs(options: Options) -> list[Input]:
    raw = [
        line for text in options.inputs for line in (_stdin_lines() if text == STDIN else [text])
    ]
    return [Input(text) for text in raw]


def _test_inputs(test: str, options: Options) -> list[Input]:
    if options.field is None:
        raise ProbeError("--test needs --field to run a command; without it the rows are listed")
    path = options.field
    return [
        Input(row_field(row, path), beside(row, path)) for row in collect(test, options.keyword)
    ]


def read_inputs(options: Options) -> tuple[Input, ...]:
    """The inputs from the arguments, stdin or a test's rows, with every @NAME replaced."""
    inputs = (
        _test_inputs(options.test, options) if options.test is not None else _typed_inputs(options)
    )
    file_lines = options.defs.read_text().splitlines() if options.defs is not None else []
    defs = parse_defs([*options.define, *file_lines])
    return tuple(Input(substitute(one.text, defs), one.beside) for one in inputs)
