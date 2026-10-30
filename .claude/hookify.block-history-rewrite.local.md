---
name: block-history-rewrite
enabled: true
event: bash
action: block
pattern: \bgit\s+(-C\s+\S+\s+)?(reset\s+(\S+\s+)*--(hard|mixed)|rebase\b|push\b[^|;&\n]*\s(-f|--force\S*)(\s|$))
---

**Take the smallest git action.** No `reset --hard`, `reset --mixed`, `rebase` or `push --force` unless the owner explicitly asked for it. If a fix belongs to two commits, leave it as its own commit and say so. See `docs/rules/ai/git.md`.
