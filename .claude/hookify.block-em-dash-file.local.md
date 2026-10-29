---
name: block-em-dash-file
enabled: true
event: file
action: block
conditions:
  - field: content
    operator: regex_match
    pattern: \N{EM DASH}
  - field: old_text
    operator: regex_match
    pattern: ^(?![\s\S]*\N{EM DASH})
---

**Em dash detected.** Never use an em dash, anywhere. Use a comma, a colon, parentheses or a new sentence. See `docs/rules/ai/conduct.md`.
