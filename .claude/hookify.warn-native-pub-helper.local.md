---
name: warn-native-pub-helper
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/native/.*/pub/
---

**Editing a native `pub/` header.** `pub/` is the public API of a layer. Helpers go into that layer's `internal/helpers.hpp`, not here. See `docs/rules/ai/code.md`.
