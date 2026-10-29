---
name: block-git-add-all
enabled: true
event: bash
action: block
pattern: \bgit\s+(-C\s+\S+\s+)?(add\s+(\S+\s+)*(-A|--all|\.)(\s|$)|commit\b[^|;&\n]*\s-(?!-)\w*a)
---

**Stage files by name.** Never `git add -A`, `git add .` or `git commit -a`; the owner edits this tree too. See `docs/rules/ai/git.md`.
