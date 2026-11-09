---
name: warn-pytest-all
enabled: true
event: bash
pattern: \bpytest\b(?![^|;&\n]*\s\S*tests/(py/[\w-]|(?!py\b)[\w-]))|\bmake\s+py-test\b
---

**The whole Python suite.** It takes minutes and the pre-push hook runs it; an assistant runs the tests of what it changed, one file or directory at a time, and the whole suite only when it is really needed. Running `tests/py` (or everything) in one pytest process also leaks Qt state between the suites and gives false failures. See `docs/rules/ai/tests.md`.
