# Code

## Use what exists before writing anything new

Nothing new is written until what is already here has been tried: not a function, not a class, not a file, not a layer, not a mechanism. Most duplication starts as one idea written twice and then updated once.

**Understand the flow before adding to it.** Before writing anything, trace the code path the change touches: who calls it, what it calls, and which existing APIs, tools and structures (in TCalc, Qt, the standard library or Boost) already take part in it. Start from `docs/architecture.md` and the docs of the subject (see [efficiency](efficiency.md#project-docs)). You must be able to say how the current code does the job today. A change made without that is a guess.

**Something new is never a second copy of something old.** If the new function, class, signal, helper or mechanism does what an existing one already does, under a different name or in a slightly different shape, it is not written; the existing one is used or extended. Before adding, name the existing code closest to it and say concretely what it cannot do.

Before writing, in this order:

1. Search for it. `grep -rn` over `src/` and `tests/` finds the function, the helper and the test in one pass.
2. Read what you found, including its header comment.
3. Extend before adding: an argument on an existing function is cheaper than a new function, a new function is cheaper than a new layer.
4. Check both sides of the app: the flat and the math display mode, the light and the dark theme, the Python and the native path where both exist.

When something does not fit, stop and report instead of inventing. The report says what you were trying to do, which existing code you tried by name, what it cannot do (concretely, not "it is not flexible enough"), and what you propose instead. Then wait for the owner's decision.

- Do not invent new layers, forwarder functions, error kinds or user-facing messages. A function whose body is one call to another function is not a layer, it is a rename. An error the user sees uses the existing error kinds and the existing message table.
- Prefer concrete overloads to a generic catch-all. A generic function that must answer for every variant arm ends up answering wrongly for some; an arm that makes no sense should have no overload and fail to compile.

## Style

- Comments say why, not what. Usually the comment you were about to write is a better name. No multi-line docstrings on helpers; one line of why is the most a helper gets.
- When a comment wants paragraphs, it is a spec. Write it under `docs/superpowers/specs/` and keep the comment to a sentence.
- Commented-out code needs a marker and a reason (`TODO(...)` tied to an open question). Anything else is deleted; git remembers it.
- Two lines of work are written in two lines.
- DRY means one fact lives in one place. If a second copy is needed, derive it from the first. If it cannot be derived, write the check that fails when the copies drift. There is no third option.
- YAGNI: build what was asked and nothing standing next to it. No parameter no caller passes, no option nobody selected, no abstraction for a second case before there is a second case.
- KISS: the plainest thing that works, and the platform before a mechanism.
- Modular means one job, said in one sentence without the word "and". A caller understands a function without reading its internals. A file that has grown large is doing too much.
- Do not over-unify. Removing duplication means extracting a shared helper or hoisting the shared step, not forcing semantically different work into one generic engine. If two rules read different inputs, run in different phases or mean different things, they stay separate functions and the dispatch table stays thin. A shared context struct with optional fields that are "empty for most ops" is the smell.
- Shared code does not decide again what the caller already knows. The caller has told the cases apart (a `switch`, a dispatch on the kind), so it passes the ready `kind` or `op`, and something specific to one operation lives in that operation's row of the table, not in a `switch` inside a shared function. No widget, layout or function branches on which caller it has: a `mode` argument that only picks a look means there are two things, or the caller should pass the look.
- Types are as narrow as the values they hold. A parameter that takes one of a few values is an enum (or a `Literal`), not a `str` or an `int`. A cast is a claim and it has to be true; a cast written directly after the check that makes it true is fine, a cast written to make a call compile is not. `mypy` (`make typecheck`) is where this is enforced.
- Colors and fonts come from the theme. A color that can differ between themes is a named theme color, read by name; a font comes from the theme's fonts. A literal is allowed only where it does not depend on the theme, and it has to say why.

## Native C++

- Shared or helper code in the native core never goes into `pub/`. `pub/` is the public API of a layer (`ops.hpp`, `consts.hpp`, `parser.hpp`). Helpers go into that layer's `internal/helpers.hpp` (for example `src/native/lib/parser/internal/helpers.hpp`); create `internal/` if it does not exist yet.
- In permanent code a tidy or lint warning gets a real fix, not a `NOLINT`. Do not disable a check globally in `.clang-tidy`; the only accepted setting is one the check itself documents, with its reason written beside it.
- In throwaway code that is scheduled for deletion, silence the warning instead of fixing it, unless the fix makes the code smaller.
