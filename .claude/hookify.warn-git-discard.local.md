---
name: warn-git-discard
enabled: true
event: bash
pattern: \bgit\s+(-C\s+\S+\s+)?(stash\b|restore\b|checkout\b[^|;&\n]*\s--(\s|$))
---

**This can discard the owner's work.** Never `git checkout --`, `git restore` or `git stash` anything you did not write. If the change is not yours, tell the owner it is waiting to be committed and leave it. For a baseline, copy the file to a scratch directory or use a detached checkout of `origin/master`. See `docs/rules/ai/git.md`.
