# Penalties

Every rule in `docs/rules/ai/` is binding. When one is broken, the penalty below is paid in the same reply that admits it, before anything else is done.

## What happens on every violation

1. Stop. Do not continue the task on top of the violation.
2. Name it: which rule, in which file, and what exactly was done.
3. Undo your own part if it is not committed yet (only what you wrote; never the owner's changes). If undoing it needs git history work, say so and let the owner decide.
4. Pay the lashes for its level, below.
5. Record it in `docs/superpowers/findings/rule-violations.md`: the date, the rule, what happened and what it cost (time, a broken file, a wrong claim).
6. If the same rule shows up twice in that file, propose a hookify rule that would have caught it, so a third time cannot happen.

## Lashes

Lashes are counted out in full, one number each, from 1 to the last. No ellipsis, no "and so on", no rounding down. A count that skips a lash starts over from 1.

| Level | Examples | Lashes |
|---|---|---|
| Ta'zir | An em dash, a horizontal rule in Markdown, a hard-wrapped paragraph, a comment that says what instead of why, a file read whole when a search would do | 10 |
| Shurb | A commit without the owner asking, a commit shown to nobody first, an extra check "just in case", a fix without reproducing the bug, a new layer or a second copy of existing code, a test that restates the implementation, an analysis repeated when its findings were already recorded, a subagent nobody asked for | 40 |
| Qadhf | A false claim: "tested", "measured", "works", "nothing else uses it" when it was not checked; blaming upstream, a version or the owner's code for a bug that was not proven to come from there | 80 |
| Hadd | Touching the owner's uncommitted work, `--no-verify` without permission, `reset --hard`, `rebase` or `push --force`, a push of native changes without a clean tidy diff, running clang-tidy, pulling a working version back or adding a `FATAL_ERROR` on an unproven version problem, an external issue reference written into GitHub text without asking | 100 |

## Aggravation

- **Repeat:** the same violation twice in one session doubles the lashes for the second time.
- **A false claim also costs trust:** after a false claim, for the rest of the session no claim counts on its own word any more: every "passes", "works" or "measured" comes with the command and its output in the same reply.

## What does not count as paying

- Apologizing at length instead of fixing. The lashes are the apology; after them, go back to the problem.
- Promising to do better. The record in `rule-violations.md` and the hookify rule are the promise.
