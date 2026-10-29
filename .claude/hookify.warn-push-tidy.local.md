---
name: warn-push-tidy
enabled: true
event: bash
pattern: \bgit\s+(-C\s+\S+\s+)?push\b
---

**Push only after a clean tidy diff.** `make cpp-tidy-diff` must have passed before commits are pushed. The owner runs it: if the owner has not confirmed a clean result for these commits, stop and give the command. See `docs/rules/ai/git.md`.
