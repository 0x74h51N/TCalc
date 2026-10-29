---
name: warn-pytest-all
enabled: true
event: bash
pattern: \bpytest\b(?![^|;&\n]*\s\S*tests/(py/[\w-]|(?!py\b)[\w-]))
---

**One pytest process for the whole suite.** Running `tests/py` (or everything) in one pytest process leaks Qt state between the suites and gives false failures. Use `make py-test`, which runs unit core, unit ui, ui and e2e separately, or point pytest at one directory or file. See `docs/rules/ai/tests.md`.
