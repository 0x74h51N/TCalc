---
name: block-no-verify
enabled: true
event: bash
action: block
pattern: \bgit\s+(-C\s+\S+\s+)?(commit|push)\b[^|;&\n]*\s(--no-verify|-n)(\s|$)
---

**Skipping the hooks.** Never use `--no-verify` (or `-n`) on a commit or a push without the owner's explicit permission. See `docs/rules/ai/git.md`.
