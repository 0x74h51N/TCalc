# A smoke run of the production path, and no input that aborts the process

Issue #246, milestone First release. Measurements: [native-abort.md](../findings/native-abort.md).

## The bug

`gcd(1e19,3)`, `gcd(2^{63},2)`, `gcd(3^{40},3)`, `lcm(10^{19},3)`, and with an exact integer `gcd(-9223372036854775807-1,2)` and `lcm(-9223372036854775807-1,1)`, end the process in a Debug build:

```
/usr/include/c++/15/numeric:130: ... Assertion '__val != __gnu_cxx::__int_traits<_Res>::__min' failed.
IOT instruction (core dumped)  python -m tcalc
```

A Release build of the same code does not abort; it goes on with undefined behavior and returns wrong numbers (#247). The code is unchanged since v0.13.2.

## How it got here

- `to_integer` (`calc/number_theory.cpp:18`, added in 7a7febb) reads a gcd or lcm operand. It accepts a whole double and converts it with `std::llround`, with no range check; past int64 that gives INT64_MIN on x86-64. An Int64 operand passes as it is, INT64_MIN included. `std::gcd` and `std::lcm` assert on the absolute value of INT64_MIN, which int64 cannot hold.
- The same abort was found on the exact trig path (3b57a06) and fixed only there.
- The rest of the code does not convert a double to int64: `to_rational` refuses a double, `require_integer` refuses one, and `coerce` refuses a double for an op with only an Int64 arm (`nCr(1e19,2)` is a math error). `to_integer` is the one place that does.
- An abort is no C++ exception: pybind11 and the error path (`CalculatorError` to `ErrorKind`) never see it, and nothing after it can catch it. The only defense is that the value never reaches the call that asserts.
- `tests/smoke/smoke_stress.cpp` exists for exactly this and allows only a `CalculatorError`, but it calls a hand-kept list of double, BigReal and BigComplex kernels with inf and nan, unchanged since 2025-12. No gcd, no int64 edge, no collection, no expression. CI runs Debug, so one row would have shown the abort.

## Approaches

- Fix `to_integer` only: closes the abort seen, finds no other.
- Fix `to_integer`, and add two smoke runs built from the ops table, one native over `apply` and one Python over the production path (chosen): an abort or a freeze anywhere the inputs reach shows as a named, red case, and an op added later is covered without editing a list.
- The above plus UBSan in CI: also reports undefined behavior that does not abort (the wrong numbers of `intdiv` and `sum`). A build and CI change of its own; not in this spec.

## The fix

### 1. `to_integer` keeps a value inside int64

`to_integer` already refuses a double that is not whole; it also refuses any operand whose absolute value int64 cannot hold: a whole double with $|x| \ge 2^{63}$ (a bound a double holds exactly), and the Int64 INT64_MIN. It refuses with the existing `math_error()`, so the user sees `Math error`. No new helper, message or error kind. gcd and lcm of a value past int64 then fail in both builds instead of aborting or giving a wrong number; computing them right is #247.

The rule for every abort this spec fixes: the input that aborted shows an error instead. Its right answer, where it has one, belongs to its own issue.

### 2. The native smoke run

A native run over `apply`, inside the `smoke stress` suite (`tests/smoke/smoke_stress.cpp`), sharing its rule (a value or a `CalculatorError` passes) through `tests/internal/smoke_helpers.hpp`:

- the ops are the rows of `kOpRows` that have a kernel; the number of operands comes from the op's `OpSpec` (arity, call arity), and a variadic op gets a Collection;
- the operands are edge Values of every arm: Int64 `0`, `1`, `-1`, INT64_MAX, INT64_MIN; Double `0`, `-0`, `0.5`, `1e19`, $2^{63}$, `1e308`, a subnormal, `inf`, `-inf`, `nan`; Rational `1/3`, INT64_MAX/1, 1/INT64_MAX; BigReal `1e400`, `1e-400`; Complex and BigComplex with an `inf` or `nan` part; Collection empty, a point, and a list of one or two scalar edges (a collection holds no Rational);
- a binary op takes every pair of them.

`apply` has no deadline, so a case that does not return within a fixed limit fails as a freeze.

### 3. The Python smoke run

A run of the production path, case by case, each case an input string:

- the editor's canonical text (`_canonicalize` of the golden e2e test, shared with it rather than copied: it already evaluates a subscript form such as `\sum_{n=1}^{3} n` raw, which the editor round trip drops), `tokenize`, `evaluate_branch`, `format_result(group=True)`, the way the controller shows a result;
- with the app's evaluation budget. `run_app` sets `set_eval_time_budget_ms(500)` today with the number written inline; it becomes a named constant beside `run_app`, and the smoke run sets the same constant, so the two cannot drift.

The inputs are built, not listed by hand:

- The ops come from the Python mirror of the ops table (`tcalc.core.ops`): each op in each form it takes, read from its row (infix, prefix, postfix, call with its call arity, variadic call over a list and over a collection).
- The operands are edge texts a user can type: `0`, `1`, `-1`, `0.5`, `1/3`, `9223372036854775807`, `-9223372036854775807-1`, `1e19`, `2^{63}`, `1e308`, `1e-320`, `1e400`, `1e-400`, `i`, `1e400i`, `1+i`, an empty list, a list of edges, a point, a nested list.
- The LaTeX constructs that carry operands (`\frac`, `\sqrt`, `\root`, power, subscript, `\sum`, `\prod`) get the same operands in each slot.

The exact operand list and forms are the plan's; this spec fixes what a case must not do.

For both runs, a case passes when it ends with a value or a `CalculatorError` (native), or with a shown result or an error the app shows (an `ErrorKind`, the timeout included: that is the production deadline doing its job). A case fails when:

- the process ends (an abort or a signal);
- it has not returned within a fixed limit well past the deadline (the deadline did not stop it);
- any other exception escapes (native), or a Python exception the app does not map to an error.

The cases run in child processes (`fork` in the native run, worker processes in the Python run). A child announces each case before it runs it, so when a worker dies or stops answering, the parent names that case (its op, its form and its operands), kills the worker if needed, starts a new one and goes on. One abort does not hide the rest.

The run does not judge whether a number is right.

### 4. What the runs find

- An abort found by the run is fixed in this spec's scope, each with its own red case first.
- A freeze is #248's scope (the deadline does not reach a kernel loop): it is reported there and pinned in the run with the issue and the date until #248 fixes it.
- A wrong number seen on the way is not fixed here. It goes into its open issue if there is one (#240, #241, #242, #244, #245, #247), or into a new issue when none covers it.

An exception the app does not map (no abort; the controller shows the generic `Invalid inputs`) goes to its own issue and is pinned to it, as #249 is.

A pinned case that starts to pass fails the run, so a pin is removed when its fix lands.

### 5. Where they run

The native run is part of `make native-test`, as `smoke stress` is. The Python run is slower and loads Qt per worker, so it is its own target, `make py-smoke`, with its own directory, `tests/py/smoke/` (a file under `tests/py/e2e/` would join `make py-test`), and its own CI job on the Debug native build. The pre-push hook does not run it.

The existing rows of `tests/smoke/smoke_stress.cpp` stay; its `smoke_allow_math_error` moves into the shared helper.

## Not in this spec

- Freezes past the deadline: #248.
- Wrong numbers: the issues above.
- UBSan in CI.
- `intdiv(1e19,1)` and `sum(9223372036854775807,1)` give a wrong number without aborting (findings); each goes to an issue when the run is in place.

## Tests

- Native, `src/native/tests/unit/test_number_theory.cpp`: gcd and lcm of a double past int64 (`1e19` with `3`; $2^{63}$ with `2`) and of the Int64 INT64_MIN with `2`. Before the fix they abort the test process; after it they throw `CalculatorError`. `INT64_MIN + 1` with `2` stays accepted.
- The two smoke runs themselves, red before the fix on the gcd and lcm cases, green after it apart from their pinned cases.
