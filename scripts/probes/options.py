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
        metadata=_declare(Flag("--ref", FlagKind.SWITCH, "grade each value against mpmath"))
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


def read_inputs(options: Options) -> tuple[str, ...]:
    """The inputs from the arguments or stdin, with every @NAME replaced."""
    raw = [
        line for text in options.inputs for line in (_stdin_lines() if text == STDIN else [text])
    ]
    file_lines = options.defs.read_text().splitlines() if options.defs is not None else []
    defs = parse_defs([*options.define, *file_lines])
    return tuple(substitute(text, defs) for text in raw)
