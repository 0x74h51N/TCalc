# Generated stubs (#108)

## 2026-11-13, chore/type-safety-rules ed7f864: what `patch_stub` still patches

`patch_stub` in `src/native/Makefile` runs two `sed` lines over the `pybind11-stubgen` output (pybind11-stubgen 3.0.0, pybind11 3.1.0).

Raw stub, generated without the patch:

```
PYTHONPATH=src .venv/bin/python -m pybind11_stubgen calc_native -o <scratch>/raw
diff <scratch>/raw/calc_native.pyi stubs/calc_native.pyi
```

The two files differ only in the two patched lines. `grep -c "calc_native\." <scratch>/raw/calc_native.pyi` is `0`: the raw stub has no fully qualified self-reference, so the self-import (`import calc_native`) has nothing to resolve today.

mypy over the raw stub (a copy of `stubs/` with the raw `calc_native.pyi`, put first with `MYPYPATH`), with and without `--check-untyped-defs`, gives the same single error both times:

```
calc_native.pyi:180: error: Incompatible types in assignment (expression has type "None", base class "object" defined the type as "Callable[[], int]")  [assignment]
```

Line 180 is `Collection.__hash__: typing.ClassVar[None] = None`. `Collection` is the only bound class with `__eq__` and no `__hash__` (`bind_collection.cpp`), so pybind11 sets `__hash__ = None`. The `--check-untyped-defs` flag does not touch this error; without it mypy skips the bodies of untyped functions (`expression_node.py:64`, `:65`, `expression.py:608` print `annotation-unchecked` notes).

## 2026-11-13, chore/type-safety-rules ed7f864: nothing calls `Collection.__eq__`

With `Collection.__eq__` replaced by one that raises (a `-p` pytest plugin), these pass unchanged: `test_eval_e2e.py` (380), `test_collection_bindings.py` (7), `test_reductions_e2e.py` (50), and under `tests/py/e2e/ui/` `test_controller_status.py`, `test_format_result_e2e.py`, `test_result_widget.py`, `test_history.py`, `test_expression.py`. `grep` finds no `==` on a result, value or memory in `src/tcalc`.

A stale native build after a branch switch fails 8 `test_eval_e2e.py` rows (`sqrt-huge-negative-bigreal` and the other negative BigReal roots) with a math error; `make native-build` makes them pass.

## 2026-11-13, chore/type-safety-rules: `patch_stub` removed

The Python `Collection.__eq__` binding is removed (`Collection::operator==` stays in C++), so pybind11 leaves `__hash__` alone and the stub needs no patch. `patch_stub` is gone from `src/native/Makefile`; `check_untyped_defs` moved from the `makefile` into `[tool.mypy]`; `ignore_missing_imports` on `calc_native` is removed. With `stubs/calc_native.pyi` moved away, `make typecheck` fails with 26 `import-not-found` errors; with it back, it passes.
