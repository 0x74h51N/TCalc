---
name: warn-build-fatal-error
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: (CMakeLists\.txt|\.cmake|makefile|/scripts/)
  - field: content
    operator: regex_match
    pattern: FATAL_ERROR|\$\(error\b
---

**Hard failure in the build.** No `FATAL_ERROR` (or any hard failure) is added because of a version problem that has not been tested or proven to affect TCalc. A build that refuses a version shuts out every user on it. See `docs/rules/ai/versions.md`.
