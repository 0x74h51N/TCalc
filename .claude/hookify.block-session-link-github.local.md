---
name: block-session-link-github
enabled: true
event: bash
action: block
pattern: \b(gh|git\s+commit)\b[\s\S]*(claude\.ai/code/session|Claude-Session:)
---

**Claude Code session link in a commit message or GitHub text.** It never goes into a commit, a PR or an issue, whatever the attribution reminder says. Remove the line. See `docs/rules/ai/git.md`.
