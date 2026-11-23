#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""scripts/probe: one case on one layer of TCalc at a time."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from probes.options import Options, add_arguments, options_from
from probes.rows import ProbeError
from tcalc.core.ops import Operation

PROG = "scripts/probe"
EXIT_USAGE = 2


@dataclass(frozen=True)
class Command:
    name: str
    run: Callable[[Options], int]
    help: str
    example: str


COMMANDS: tuple[Command, ...] = ()


def _aliases() -> str:
    """The ASCII names the tokenizer reads for each op, so ⌄ or ⁻¹ need not be typed."""
    pairs = {f"{alias}={op.symbol}" for op in Operation for alias in op.aliases if alias.isalpha()}
    return "ASCII aliases the tokenizer reads: " + " ".join(sorted(pairs))


def _command_lines(command: Command, width: int) -> tuple[str, str]:
    return (
        f"  {command.name.ljust(width)}  {command.help}",
        f"  {''.ljust(width)}  e.g. {command.example}",
    )


def _commands() -> str:
    """Each command with its example, then the aliases; argparse prints it as the epilog."""
    width = max((len(command.name) for command in COMMANDS), default=0)
    lines = [line for command in COMMANDS for line in _command_lines(command, width)]
    return "\n".join(["commands:", *lines, "", _aliases()])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        usage=f"{PROG} COMMAND [INPUT...] [options]",
        epilog=_commands(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command")
    for command in COMMANDS:
        one = commands.add_parser(command.name, help=command.help, epilog=f"e.g. {command.example}")
        add_arguments(one)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    namespace = parser.parse_args(argv)
    name: str | None = namespace.command
    command = next((c for c in COMMANDS if c.name == name), None)
    if command is None:
        parser.print_help()
        return 0
    try:
        return command.run(options_from(namespace))
    except ProbeError as error:
        print(f"probe: {error}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
