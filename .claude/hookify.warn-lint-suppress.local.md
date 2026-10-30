---
name: warn-lint-suppress
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(py|pyi|cpp|hpp|h)$
  - field: content
    operator: regex_match
    pattern: NOLINT|type:\s*ignore|\bnoqa\b
---

**Lint suppression.** In permanent code a tidy, lint or type warning gets a real fix, not a suppression. Silencing is only for throwaway code scheduled for deletion. See `docs/rules/ai/code.md`.
