---
name: block-session-link-file
enabled: true
event: file
action: block
conditions:
  - field: content
    operator: regex_match
    pattern: (claude\.ai/code/session|Claude-Session:)
  - field: file_path
    operator: regex_match
    pattern: ^(?!.*hookify\.)
---

**Claude Code session link in a file.** Commit messages and PR or issue bodies are written to files first; the session link never goes into them. Remove the line. See `docs/rules/ai/git.md`.
