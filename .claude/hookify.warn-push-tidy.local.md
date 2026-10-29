---
name: warn-push-tidy
enabled: true
event: bash
pattern: \bgit\s+(-C\s+\S+\s+)?push\b
---

**Native changes need a clean tidy diff.** If these commits change files under `src/native/` or any C++ file, `make cpp-tidy-diff` must have passed; the owner runs it. If the owner has not confirmed a clean result, stop and give the command. Commits with no native change are pushed without it. See `docs/rules/ai/git.md`.
