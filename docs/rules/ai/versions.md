# Versions and regressions

- A working version is never pulled back on the claim that a newer one is incompatible or has a regression, unless the problem has been tested or proven to affect TCalc.
- "Upstream has a regression" is not the same as "TCalc is affected". Check whether TCalc's code path actually reaches the broken code and whether TCalc's results change.
- No `FATAL_ERROR` (or any hard failure) is added to make, CMake or scripts because of an unproven version problem. A build that refuses a version shuts out every user on that version.
- Version pins are fine for reproducible environments (minor pins in `pyproject.toml` and CI).
- Raising or adding a pin goes on its own branch, and the whole suite runs before merge, benchmarks included.
- Adding a dependency is a conversation with the owner, not a commit.
