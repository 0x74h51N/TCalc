# Python test layers, part 3: `tests/py/unit/core`

Issue #205, milestone First release (#22). Starts when [part 2](2026-11-06-ui-theme-tests-design.md) is done.

## Why

By the owner's judgment, `unit/core` is built right: it tests with dummies and no dependencies, and it is the shape the other parts copy. It has a few mistakes to fix. Its conftest is 444 lines for 9 test functions, and part of that was written for an evaluator that moved to C++.

## Goals

- `unit/core` keeps its own fake in its own conftest. `tests/py/unit/ui` has no fake `calc_native`, so there is nothing to share.
- Fakes nothing reads are gone: `DummyCalc`, `FakeToken`, the fake collection internals, the `CEKOMASTIK`, `BAD_TYPE` and `BAD_NATIVE` ids, and the `calc_native` names and `Id` and `_OpDef` members the review found unread. Each is confirmed unread by a run before it goes.
- `test_pr_body.py` moves to `tests/py/e2e/`: it runs a script through stdin and stdout and reads the real pull request template, so it is not a unit test of a module. The owner agreed, and it is the one thing this part adds to that folder.

- The Python promotion rules go, by the owner's decision: `PROMO_RULES_BY_ID`, `Operation.cx`, the `_cx_*` functions and `is_int_like` have no reader since the Python evaluator went in 0c7cfde, and the native `promote_complex` decides this. This is the one change under `src/` in this part.

## Non-goals

- Rewriting what works: the structure of `unit/core`, its fake and `_CANONICAL_CONFTST` stay.
- New tests for `core/parser.py`, `core/native_eval.py` or `core/constants.py`, by the owner's decision: the first two are tested in the native suite, and the constants end to end.

## Done when

- `tests/py/unit/core` passes with its 21 cases, less the 9 that leave with `test_pr_body.py` and the 8 of the dead promotion rules.
- `tests/py/unit/core` passes on a copy with no `calc_native*.so`.
- `make py-test`, `make py-lint` and `make typecheck` pass.
