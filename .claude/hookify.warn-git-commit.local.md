---
name: warn-git-commit
enabled: true
event: bash
pattern: \bgit\s+(-C\s+\S+\s+)?commit\b
---

**Commit only if the owner asked for this commit.** Permission to commit once does not carry over to the next change. Show the owner the files and the diff first, stage them by name and keep the message short. See `docs/rules/ai/git.md`.
