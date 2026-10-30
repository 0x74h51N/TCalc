# CI runtime

## 2026-10-30: where a docs-only PR spends its time

Run `41032935347` (branch `docs/issue-templates`, docs only) ran every job of `.github/workflows/ci.yml`, about 10 minutes wall time. Command: `gh run view 41032935347 --json jobs -q '.jobs[] | "\(.name)\t\(.startedAt)\t\(.completedAt)"'`.

| Job | Duration |
|---|---|
| Native Build | 2m46s (the build step alone 2m09s) |
| Python Tests | 1m33s |
| Benchmark Tests | 5m18s (the benchmark step alone 4m24s) |
| clang-tidy, mypy, ruff, clang-format, Native Tests | under 50s each |

The critical path is Native Build, then Python Tests, then Benchmark Tests, because the benchmark job `needs` every test job, not only the build. Two runs of the same branch overlapped (09:22 and 09:26), since the workflow has no `concurrency` group.

## 2026-10-30: required checks and skipped jobs

The `masterRule` ruleset requires seven checks by job name: `C++ Format Check (clang-format)`, `Python Format Check (ruff)`, `Native Tests`, `C++ Code Quality (clang-tidy)`, `Python Type Check (mypy)`, `Python Tests`, `Benchmark Tests`. Command: `gh api repos/{owner}/{repo}/rulesets/11700156 -q .rules`.

Per the GitHub docs: a workflow skipped by an `on.pull_request.paths` filter never reports its checks, so a required check stays "Expected" and blocks the merge. A job skipped by a job-level `if:` reports "Skipped", which a required check accepts as passing. A job skipped because a job it `needs` failed also reports "Skipped", so a broken change-detection job would turn every check green; a final gate job that reads `needs.*.result` closes that hole.

`Native Build` is not in that list either, so a C++ compile error skips every job that needs the build and the seven required checks still pass. This hole predates the path rules. The fix chosen: add `Changed Paths`, `Native Build` and `CI OK` to the required checks after the path-rules PR merges (before it, open PRs never report `CI OK` and would wait forever).

## 2026-10-30: sandbox run of the path rules

In the private repository `0x74h51N/tcalc-ci-sandbox` (master = commit `0b5b69a`), a docs-only PR ran only `Changed Paths` and `CI OK`, both `success`, every other job `skipped`. A PR touching only `src/native/tests/` ran clang-format and Native Build and skipped ruff. The first two PRs, opened about 15 seconds after the first push to the new repository, got no run at all; closing and reopening them started the runs. A free plan does not enforce rulesets on a private repository, so the merge block itself was not seen there.
