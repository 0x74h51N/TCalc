---
name: block-em-dash-github
enabled: true
event: bash
action: block
pattern: \b(gh|git\s+commit)\b[\s\S]*\N{EM DASH}
---

**Em dash in a commit message or GitHub text.** Never use an em dash, anywhere. Use a comma, a colon, parentheses or a new sentence. See `docs/rules/ai/conduct.md`.
