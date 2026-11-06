# Python test layers, part 3: `tests/py/unit/core` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `unit/core` keeps its structure and its own fake, and loses the fakes nothing reads.

**Architecture:** The conftest is trimmed in place, and `test_pr_body.py` moves out.

**Tech Stack:** pytest.

**Spec:** [2026-11-06-unit-core-tests-design.md](../specs/2026-11-06-unit-core-tests-design.md)

## Global Constraints

- No file under `src/` changes.
- The structure of `unit/core` stays. Only what the spec names changes.
- A commit needs the owner's approval: each commit step shows the diff and stops. Run `make py-lint-fix` first.

## Review Focus

- A fake that looked unread but is read at import: the directory runs after each removal.
- A `test_ops.py` check that loses its meaning: `test_root_rule` and `test_promo_rules_wired` must still fail when `_cx_root` or the promo table is broken.

## Task 1: Trim the conftest, move `test_pr_body.py`

**Files:**
- Modify: `tests/py/unit/core/conftest.py`
- Move: `git mv tests/py/unit/core/test_pr_body.py tests/py/e2e/test_pr_body.py`

**Builds on:** the fake in `tests/py/unit/core/conftest.py`.

- [ ] **Step 1: Remove the fakes the spec names, one at a time, running the directory after each**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/core -q`
Expected: no change in the count. A removal that breaks something is put back and reported.

- [ ] **Step 2: Move `test_pr_body.py` and fix its `parents[4]` to the new depth**

- [ ] **Step 3: Prove two checks still bite**

On a scratch copy of `src/`, and of the conftest: break `_cx_root` and expect `test_root_rule` to fail; remove the `Sqrt` row and expect `test_promo_rules_wired` to name it.

- [ ] **Step 4: Run**

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/core -q
make py-test PYTEST_ARGS=-q py-lint typecheck
grep -rn 'unit/core/test_pr_body' tests docs/rules makefile
```

Copy `src/` and `tests/` to the scratchpad with no `calc_native*.so` and run `tests/py/unit/core` there.

Expected: `unit/core` 12 passed (21 less `test_pr_body.py`'s 9), all else as after part 2.

- [ ] **Step 5: Show the diff, commit on approval**

`test/core: the fakes nothing reads go, test_pr_body is not a unit test`
