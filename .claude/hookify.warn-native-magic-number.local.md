---
name: warn-native-magic-number
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/native/lib/.*\.(cpp|hpp)$
  - field: content
    operator: regex_match
    pattern: '(?m)^(?!\s*(//|\*|/\*|#))(?!.*\bconstexpr\b)(?!.*")[^\n]*?(?<![\w.])(?!(?:0|1|2|100)\.0+(?![\w.]))(0x[0-9a-fA-F]+(\.[0-9a-fA-F]*)?[pP][-+]?\d+|\d+\.\d+([eE][-+]?\d+)?|\d+[eE][-+]?\d+|[5-9]|[1-9]\d+)(?![\w.])'
---

**A numeric literal outside a `constexpr` line in native code.** The pre-push tidy fails on it (`cppcoreguidelines-avoid-magic-numbers`). Name it as a `constexpr` with a one-line why, or use an existing one (`calc/internal/helpers.hpp`). See `docs/rules/ai/code.md`.
