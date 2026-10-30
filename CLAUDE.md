# TCalc

Rules for AI assistants working on this repository. Everything written into the repository is in English.

The rules are in the topic files imported at the end of this file; they are loaded with it.

Breaking any rule has a penalty, paid in the reply that admits it: see [penalties](docs/rules/ai/penalties.md).

Hookify rules under `.claude/hookify.*.local.md` enforce the mechanical parts of these rules. They only run when the hookify plugin is installed; `.claude/settings.json` lists the plugins this project uses, so install them when Claude Code offers to.

## Commands

- `make native-build`: build the native module in place and regenerate the stubs; run it after every C++ change and after switching branches.
- `make native-test`: native unit tests.
- `make py-test`: the whole Python suite, as separate pytest processes (see [tests](docs/rules/ai/tests.md)).
- `PYTHONPATH=src python -m pytest <file>`: one test file in isolation.
- `make typecheck` (mypy), `make py-lint` (ruff check and format check).
- `make py-benchmark`: performance benchmarks.
- `make cpp-format`, `make py-lint-fix`: format the C++ and fix the Python lint; run both before a commit you make.
- The pre-commit hook runs format check, py-lint, typecheck, native-test and py-test. The pre-push hook runs the tidy diff when the pushed commits change native files.

## Where things are

- `src/native/`: the C++ core (tokenizer, evaluator, math kernels, value types), exposed to Python as `calc_native` through pybind11.
- `src/tcalc/`: the Python side, PySide6 UI and orchestration; it computes nothing itself.
- `docs/architecture.md`: the layers and the data flow from keystroke to result; `docs/data-flow.md`: worked examples of it. `docs/parser.md`: the parser. `docs/dev.md`: setup and requirements.
- `docs/superpowers/findings/`: recorded analysis, measurements and failed attempts, one file per subject, indexed in its `README.md`.
- `docs/CONTRIBUTING.md` and `docs/CODE_OF_CONDUCT.md`: the rules for human contributors.

## Loaded every session

The rules by topic, the setup and the architecture are imported below, so they are in context from the start of every session; they are not read again with a tool.

@docs/rules/ai/conduct.md
@docs/rules/ai/bugs.md
@docs/rules/ai/versions.md
@docs/rules/ai/code.md
@docs/rules/ai/tests.md
@docs/rules/ai/git.md
@docs/rules/ai/docs.md
@docs/rules/ai/subagents.md
@docs/rules/ai/efficiency.md
@docs/rules/ai/penalties.md
@docs/dev.md
@docs/architecture.md
