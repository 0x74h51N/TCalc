---
name: warn-md-horizontal-rule
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: ^(?!.*/\.claude/).*\.md$
  - field: content
    operator: regex_match
    pattern: (^|\n)[ \t]*(-[ \t]*){3,}(\n|$)
---

**Horizontal rule in Markdown.** Do not use horizontal rules; headings separate sections. See `docs/rules/ai/docs.md`.
