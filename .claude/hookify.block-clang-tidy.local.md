---
name: block-clang-tidy
enabled: true
event: bash
action: block
pattern: ^(?![\s\S]*\bgh\s+(pr|issue|release)\b)[\s\S]*?(make\b[^|;&\n]*\bcpp-tidy|run-clang-tidy|(^|[;&|]\s*)clang-tidy\s)
---

**The human agent runs tidy.** Do not run clang-tidy at any stage. Stop and give the human agent the command (`make cpp-tidy-diff`). See `docs/rules/ai/git.md`.
