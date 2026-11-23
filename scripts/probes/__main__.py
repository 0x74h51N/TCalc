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

from probes import editor, eval_cmd, grade_cmd, layers, paint, render, shot
from probes.options import Options, add_arguments, options_from
from probes.rows import ProbeError
from probes.testcase import collect, rows_text
from tcalc.core.ops import Operation

PROG = "scripts/probe"
EXIT_USAGE = 2


@dataclass(frozen=True)
class Command:
    name: str
    run: Callable[[Options], int]
    help: str
    example: str


COMMANDS: tuple[Command, ...] = (
    Command(
        "eval",
        eval_cmd.run,
        "a case through the whole Python path: editor text, value, display, written text, round trip",
        'scripts/probe eval "1/3" "(2) root (3)" --ref',
    ),
    Command(
        "layers",
        layers.run,
        "a case on each layer: tokens, RPN, render tree, binding, the last op alone, format",
        'scripts/probe layers "2π" "\\root{8}{3}" --unit rad --ref',
    ),
    Command(
        "editor",
        editor.run,
        "a text in the app's editor, then --step keys: the widget tree and the cursor after each",
        'scripts/probe editor "\\frac{1}{2}" --step left --step text:7 --png e.png',
    ),
    Command(
        "render",
        render.run,
        "a text rendered read-only as the result line renders it: the widget tree and the renderer's log",
        'scripts/probe render "\\root{8}{3}"',
    ),
    Command(
        "paint",
        paint.run,
        "the painter's boxes for a text, as a history item paints it: class, x y w h above below",
        'scripts/probe paint "\\frac{1}{2}" --png p.png',
    ),
    Command(
        "shot",
        shot.run,
        "the whole window with a text typed in: what the editor and the result line show, and a PNG",
        'scripts/probe shot "1/3" --size 800x600 --theme light --png w.png',
    ),
    Command(
        "grade",
        grade_cmd.run,
        "grade a probe table against python-flint, or compare two runs of it",
        "scripts/probe grade old.txt new.txt",
    ),
)


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
    options = options_from(namespace)
    try:
        if options.test is not None and options.field is None:
            # without --field there is no input to run on: the rows are listed to pick one from
            print(rows_text(collect(options.test, options.keyword)))
            return 0
        return command.run(options)
    except ProbeError as error:
        print(f"probe: {error}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
