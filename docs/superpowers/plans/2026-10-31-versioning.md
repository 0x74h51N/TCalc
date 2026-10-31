# Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give TCalc a git-derived version, a changelog generated from pull request titles on top of a hand-written history, retroactive tags, milestones and labels, and a release that the owner starts and merges, then ship `v0.14.0` with it.

**Architecture:** setuptools-scm reads the version from `v*` tags. A pull request's title is its changelog line; GitHub writes it into the merge commit, and git-cliff turns the merges since the last tag into a `CHANGELOG.md` section. `release-pr.yml` computes the version and opens a release pull request; `release.yml` tags its merge and publishes the GitHub release. GitHub state (tags, labels, milestones, ruleset) is changed with `gh` from approved tables.

**Tech Stack:** setuptools-scm 10.3, git-cliff 2.14, GitHub Actions, `gh`, hookify rules.

**Spec:** `docs/superpowers/specs/2026-10-31-versioning-design.md`

**Issue:** #110

## Global Constraints

- `setuptools-scm>=10.3,<10.4` in `[build-system] requires`, `git-cliff>=2.14,<2.15` in the `dev` extra; no other new dependency.
- Version strings are `MAJOR.MINOR.PATCH`; tags are `v` plus the version, annotated.
- Pull request titles: `^(feat|fix|perf|refactor|docs|test|ci|chore|build)(/[a-z0-9-]+)?: \S` or `^release: v\d+\.\d+\.\d+$`. The pattern lives only in `.github/workflows/pr-title.yml`; everything else points to it.
- `CHANGELOG.md` follows the Keep a Changelog layout; a version heading is `## [X.Y.Z](https://github.com/0x74h51N/TCalc/compare/vPREV...vX.Y.Z) - YYYY-MM-DD`; sections only `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, in that order. No `## [Unreleased]`, no link block.
- Repository URL in every link: `https://github.com/0x74h51N/TCalc`.
- No em dash anywhere, no hard-wrapped Markdown, no horizontal rules (`docs/rules/ai/conduct.md`, `docs.md`).
- Every commit step: show the owner the files and the diff, wait for approval, stage by name (`docs/rules/ai/git.md`). Run `make py-lint-fix` before each commit.
- Every GitHub change (tag, label, milestone, ruleset, repository, PR or issue edit, workflow run) runs only after the owner approved it in this conversation.
- No clang-tidy, no `--no-verify`.

## Who runs what

Tasks 1, 2, 3, 5 and Task 4 Step 1 are repository work and can go to implementer subagents, one at a time; each stops at its commit step and reports the diff. Everything that touches GitHub (Task 3 Step 1 reads only, Task 4 Steps 2 to 4, Tasks 6, 7 and 8) runs in the main session, where the owner approves it.

## Review Focus

1. A CI job clones with depth 1 and no tags, then runs `pip install -e ".[dev]"`: install must still succeed (the version may read `0.1.devN`). Task 1 measures it.
2. A release tarball from GitHub has no `.git`: `pip install` from it must get the tag's version. Task 1 measures it with `git archive`.
3. A pull request title that does not match (`Feat/theme switching`, a branch name) fails the title job instead of dropping a changelog line. Task 2 runs the pattern over the 99 past titles.
4. The release pull request workflow runs when only docs, CI or test pull requests merged since the last tag: it fails with "nothing to release" instead of opening an empty release. Task 4 dry run.
5. A hand edit of `CHANGELOG.md` merged to `master` (a typo fix, a `[YANKED]` mark) does not tag or publish anything. Task 4 dry run.

## File Structure

- Modify `pyproject.toml`: dynamic version, setuptools-scm, `[tool.setuptools_scm]`, git-cliff in `dev`.
- Create `.git_archival.txt`, `.gitattributes`: version for source archives.
- Create `cliff.toml`: how git-cliff turns merges into a section.
- Create `.github/workflows/pr-title.yml`: the pull request title check.
- Create `.github/workflows/release-pr.yml`, `.github/workflows/release.yml`.
- Create `CHANGELOG.md`.
- Create `docs/release.md`, `docs/rules/ai/release.md`, `.claude/hookify.warn-release-action.local.md`, `.claude/hookify.warn-pr-create.local.md`, `docs/superpowers/findings/versioning.md`.
- Modify `CLAUDE.md`, `docs/rules/ai/git.md`, `docs/CONTRIBUTING.md`, `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `docs/dev.md`, `docs/superpowers/findings/README.md`.

### Task 1: setuptools-scm

Already implemented and measured in the working tree on 2026-10-31 (the commit was taken back with the owner's soft reset; the files are unchanged). This task verifies and commits it.

**Files:**
- Modify: `pyproject.toml:1-8`, `docs/dev.md`, `docs/superpowers/findings/README.md`
- Create: `.git_archival.txt`, `.gitattributes`, `docs/superpowers/findings/versioning.md`

**Interfaces:**
- Produces: `importlib.metadata.version("TCalc")` returns the git-derived version after `pip install -e .`.

- [ ] **Step 1: Check the tree** holds the setuptools-scm change: `pyproject.toml` has `dynamic = ["version"]`, `setuptools-scm>=10.3,<10.4` in `[build-system] requires` and an empty `[tool.setuptools_scm]`; `.git_archival.txt` has the three `$Format` lines setuptools-scm documents; `.gitattributes` has `.git_archival.txt  export-subst`; the six measurements are in `docs/superpowers/findings/versioning.md` under their 2026-10-31 heading.
- [ ] **Step 2: Reinstall the dev tree**: `.venv/bin/pip install -e ".[dev]" -q && .venv/bin/python -c 'import importlib.metadata as m; print(m.version("TCalc"))'`. Expected: a `0.1.devN+g...` string (no tags pushed yet).
- [ ] **Step 3: Commit** `build: derive the version from git tags with setuptools-scm` (pyproject.toml, .git_archival.txt, .gitattributes, docs/dev.md, the two findings files). The findings file also holds the tool measurements of the same day; they go in with it.

### Task 2: Changelog generation and the title check

**Files:**
- Create: `cliff.toml`
- Create: `.github/workflows/pr-title.yml`
- Modify: `pyproject.toml` (`dev` extra), `docs/dev.md`

**Interfaces:**
- Produces: `git-cliff --unreleased --tag vX.Y.Z` prints one version section; `git-cliff --unreleased --tag vX.Y.Z --prepend CHANGELOG.md` writes it under the header. `cliff.toml`'s `header` is the exact opening text of `CHANGELOG.md` (Task 3 writes the file with it).
- Produces: the `Pull Request Title` check from `pr-title.yml`.

- [ ] **Step 1: `cliff.toml`** from the tested config (`.superpowers/sdd/2026-10-31-versioning/cliff-tested.toml`, measured in `docs/superpowers/findings/versioning.md`): `conventional_commits = false`; the merge preprocessor `(?s)^Merge pull request #(\d+) from \S+\s*\n\s*([^\n]+).*` to `${2} (#${1})`; parsers `feat` to `Added`, `perf` to `Changed`, `fix` to `Fixed`, `fix` with scope `ci`, `scripts`, `hooks` or `tests` skipped, everything else skipped, each matching only a title that ends in `(#N)` and allowing the scope to be absent (`^feat(/[\w-]+)?: `); `tag_pattern = "v[0-9]+\\.[0-9]+\\.[0-9]+"`; `sort_commits = "oldest"`; the heading template with the compare link from `previous.version` to `version` and the date; one blank line after the header; `header` equal to the header Task 3 writes.
- [ ] **Step 2: `pyproject.toml`**: `"git-cliff>=2.14,<2.15"` in the `dev` extra. `.venv/bin/pip install -e ".[dev]" -q`, then `.venv/bin/git-cliff --version` prints `git-cliff 2.14.x`. `docs/dev.md`: git-cliff joins the dev tools sentence.
- [ ] **Step 3: Measure on a scratch clone** (`git clone /home/0x74h51n/Repos/calculator $SCRATCH/cliff`, copy `cliff.toml` in), each with the expected result:
  1. `v0.12.2` on the first parent of the #86 merge, HEAD on the #86 merge: `--unreleased --tag v0.13.0` prints `## [0.13.0](.../compare/v0.12.2...v0.13.0)`, `### Added`, `- Based log (#86)` and nothing from the branch commits (`logs take a base`, `cover the based log`).
  2. `v0.13.1` on the first parent of the #88 merge, HEAD on `c1811dc`: the `fix/scripts` (#88) and `fix/ci` (#92) titles are absent; #89, #90 and #103 are under `Fixed`.
  3. A file holding only the header, then `--prepend`: the section sits under the header with one blank line between.
  Record the three outputs in the findings file.
- [ ] **Step 4: The title check**, its own workflow `.github/workflows/pr-title.yml`, so editing a pull request's description reruns only it and not the whole CI: `on: pull_request` to `master` with `types: [opened, edited, synchronize, reopened]`, `permissions: contents: read`, one job `Pull Request Title` with one `run:` step that checks the title (passed through an `env:` variable, not interpolated into the script) against the Global Constraints pattern with `grep -Eq`, printing the pattern and the title on failure. Task 7 makes it a required check.
- [ ] **Step 5: Try the pattern on the past**: `git log --merges --format=%b master | grep -v '^$' | grep -v '^- \|Co-Authored' | grep -cE '<pattern>'` and the same with `-vcE`. Record both counts and five of the failing titles in the findings file. Expected: 42 match, 57 fail (measured on 2026-10-31 with the scope required; the optional scope may move a few, record what it gives).
- [ ] **Step 6: Commit** `build: generate the changelog from pull request titles with git-cliff` (cliff.toml, pr-title.yml, pyproject.toml, docs/dev.md, the findings file).

### Task 3: Backfilled CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md`
- Scratch: `$SCRATCH/research/inventory.tsv`

**Interfaces:**
- Consumes: `cliff.toml`'s `header` from Task 2; the file starts with exactly that text.
- Produces: `CHANGELOG.md` with `0.13.2` down to `0.1.0`, whose headings match the tags of Task 6.

- [ ] **Step 1: Build the inventory**: for every merged pull request #1 to #94 (`gh pr view N --json title,body,commits,files`) and, for `0.1.0` to `0.5.9`, every commit in `106e83e..b716cf1`: one TSV row `number_or_sha, version, section, line` or `number, version, none, reason`. Versions from the spec's table. The research run of 2026-10-31 already wrote it: `$SCRATCH/research/inventory.tsv` (167 rows, all 98 merged PRs, 33 `none` rows). Start from it and correct it, do not redo it; rows for #91 and #99 onward leave it, since `0.14.0` is generated.
- [ ] **Step 1b: Prove each `**Breaking:**` line.** The research marked four versions as losing saved history (44eaa69 in 0.5.0, #21 in 0.7.0, #42 in 0.9.0, #64 in 0.11.0) from reading the storage code, without running it. For each: in a detached worktree of the commit before the change, save a history entry (`scripts/seed_history.py` or the app), copy the history file out, then load it with the code after the change (`load_history()`) and see whether the entry is lost. Record the commands and results in the findings file. A line whose loss is not seen loses its `**Breaking:**` marker.
- [ ] **Step 2: Check the inventory is complete**: `cut -f1 $SCRATCH/research/inventory.tsv | grep '^#' | sort -u | wc -l` against the number of merged pull requests up to #94 (`gh pr list --state merged --limit 300 --json number --jq '[.[] | select(.number <= 94)] | length'`). Expected: equal.
- [ ] **Step 3: Write `CHANGELOG.md`**: the header (what the file is, Keep a Changelog, the version scheme in one sentence with a link to `docs/release.md`), then `0.13.2` down to `0.1.0` in the heading format of the Global Constraints with the dates of the spec's table, `0.1.0` linking to `tree/v0.1.0`, each with one or two opening sentences, the lines following the spec's Backfill rules.
- [ ] **Step 4: Verify the format by generation**: in the scratch clone of Task 2 with `v0.13.2` on `e31b1d7`, copy `CHANGELOG.md` in and run `git-cliff --unreleased --tag v0.14.0 --prepend CHANGELOG.md`. Expected: the new section lands between the header and `## [0.13.2]` with one blank line on each side, and `diff` against the copy shows only the added section.
- [ ] **Step 5: Show the owner** the changelog and the inventory's `none` rows before the commit. **Commit** `docs: add CHANGELOG.md with the history up to 0.13.2`.

### Task 4: Release workflows

**Files:**
- Create: `.github/workflows/release-pr.yml`, `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `cliff.toml`; the `dev` extra.

- [ ] **Step 1: Write the workflows**, `ubuntu-24.04`, `PYTHON_VERSION` as in `ci.yml`, `GH_TOKEN: ${{ github.token }}`, checkout with `fetch-depth: 0`. `pip install .` packages only the Python side (no `setup.py`, no extension in `pyproject.toml`), so no job needs a compiler or Boost.
  - `release-pr.yml`: `workflow_dispatch` with input `bump` (string, default `auto`); `permissions: contents: write, pull-requests: write`. Steps in the spec's order: last tag with `git describe --tags --abbrev=0 --match 'v[0-9]*'`; the level from `git log --merges --first-parent --format=%b "$last"..HEAD | grep -q '^feat[/:]'` (minor, else patch), `minor` forced, or an exact version checked greater than the last tag; fail with `nothing to release since <tag>` when `git-cliff --unreleased --tag "v$version"` prints no `### ` line; `git-cliff --unreleased --tag "v$version" --prepend CHANGELOG.md`; branch `release/v$version`, commit `release: v$version` as `github-actions[bot]`, push, `gh pr create --title "release: v$version" --body-file` with the merged pull requests (`git log --merges --first-parent --format='%b' "$last"..HEAD`) and the milestones whose issues are all closed.
  - `release.yml`: `on: push: branches: [master], paths: [CHANGELOG.md]`; `permissions: contents: write, issues: write`. Steps: read the top version heading of `CHANGELOG.md`; stop with a notice if `git rev-parse -q --verify "refs/tags/v$version"` finds the tag; fail unless the head commit's subject is `Merge pull request #N from <owner>/release/v$version`; `git tag -a "v$version" -m "TCalc $version"` and `git push origin "v$version"`; `pip install .` and compare `importlib.metadata.version("TCalc")` with `$version`; take the top section (from the first `## [` line to the line before the second) plus a blank line and `**Full changes**: https://github.com/0x74h51N/TCalc/compare/<previous tag>...v$version` as `notes.md`; `gh release create "v$version" --title "TCalc $version" --notes-file notes.md`; close milestones: `gh api repos/{owner}/{repo}/milestones --jq '.[] | select(.open_issues == 0 and .closed_issues > 0) | .number'`, then `gh api -X PATCH .../milestones/N -f state=closed` for each.
- [ ] **Step 2: Required checks**: the ruleset `masterRule` (read on 2026-10-31) requires ten checks of `ci.yml` (`Changed Paths`, the eight jobs and `CI OK`) and has no bypass actors. The `ci.yml` run on a pull request the Actions bot opened waits as `action_required` until the owner approves it; after that the checks attach and a `CHANGELOG.md`-only change passes `CI OK`. Starting `ci.yml` with `gh workflow run` instead does not attach to the pull request and runs the whole CI, so it is not used. Creating the pull request needs the setting "Allow GitHub Actions to create and approve pull requests" (Task 7 Step 2).
- [ ] **Step 3: Dry run on a scratch repository**: ask the owner to approve creating a private repository `0x74h51N/tcalc-release-test`. Push `feat/versioning` there as `master` with `v0.13.2` on `e31b1d7`. Then, each with its expected result:
  1. Start `release-pr.yml` with `bump: auto`: a pull request `release: v0.14.0` (or the level the merges give) with the generated section.
  2. Merge it: `release.yml` tags `v0.14.0`, publishes the release with the section and the compare link.
  3. Merge a pull request that only edits a `CHANGELOG.md` line: `release.yml` stops at "tag exists", no new tag.
  4. Start `release-pr.yml` again right away: it fails with `nothing to release since v0.14.0`.
  Delete the repository afterwards with the owner's approval (`gh repo delete` needs the `delete_repo` scope; if it is missing, give the owner the command).
- [ ] **Step 4: Record** the outcomes and the required-checks answer in the findings file. **Commit** `ci: open a release pull request and publish the release on its merge`.

### Task 5: Rules and docs

**Files:**
- Create: `docs/release.md`, `docs/rules/ai/release.md`, `.claude/hookify.warn-release-action.local.md`, `.claude/hookify.warn-pr-create.local.md`
- Modify: `CLAUDE.md`, `docs/rules/ai/git.md`, `docs/CONTRIBUTING.md`, `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`

- [ ] **Step 1: `docs/release.md`**: the trunk-based model in two sentences, the version scheme and the bump rule with the `bump` input, the release procedure (start `release-pr.yml`, approve the `ci.yml` run on the release pull request, review and polish the section, merge) and what each workflow checks. The only place the procedure is written.
- [ ] **Step 2: `docs/rules/ai/release.md`**, short, as the other rule files: no file holds the version; the title is the changelog line, written for users when the change is user-visible, and its pattern is in `.github/workflows/pr-title.yml`; released sections of `CHANGELOG.md` are not edited except `[YANKED]` or a factual fix; never tag, run `gh release` or `gh workflow run release-pr`, or create, close or delete a milestone, label or ruleset unless the owner asked in this conversation; before writing a spec, list open milestones (`gh api repos/0x74h51N/TCalc/milestones`) and name the one the spec serves or propose one; open PRs with `--milestone`, a `type:` label and an `area:` label; an issue opened by an assistant gets its `type:`, `area:` and `status:` labels, and the spec step of a work moves its issue from `status: needs spec` to `status: ready`; the procedure is in `docs/release.md`. Add `@docs/rules/ai/release.md` to `CLAUDE.md` after `git.md`.
- [ ] **Step 3: Hookify rules**, in the existing format (`name`, `enabled: true`, `event: bash`, `pattern`, message pointing to `release.md`):
  - `warn-release-action`: `\bgit\s+(-C\s+\S+\s+)?tag\s+(-a|-s|-d|-f|v\d)|\bgit\s+push\b[^|;&\n]*(refs/tags/|\sv\d+\.\d+\.\d+|--tags)|\bgh\s+(release|label)\s+(create|edit|delete)|\bgh\s+workflow\s+run\s+release|\bgh\s+api\b[^|;&\n]*(milestones|labels|rulesets)[^|;&\n]*(-X\s*(POST|PATCH|DELETE)|-f\s|--field)`
  - `warn-pr-create`: `\bgh\s+pr\s+create\b(?!(?=[^|;&\n]*--milestone)(?=[^|;&\n]*--label))`
- [ ] **Step 4: Verify the patterns** with `python -c` and `re.search` against: `git tag -a v0.14.0 -m x` (match), `git tag --list` (no match), `git push origin v0.14.0` (match), `gh workflow run release-pr.yml` (match), `gh api repos/x/milestones` (no match), `gh api repos/x/milestones -X POST -f title=a` (match), `gh pr create --title a --milestone M --label "area: ui"` (no match), `gh pr create --title a` (match). Expected: as listed.
- [ ] **Step 5: `git.md`**: `release` joins the commit types with `release: v0.14.0`, `release/` the branch prefixes, and pull requests merge on GitHub with a merge commit. **`CONTRIBUTING.md`**: the title is the changelog line and CI checks it, milestones and labels, and a pointer to `docs/release.md`. **PR template**: a line saying the title is the changelog line, and `**Milestone:**`. **Issue templates**: `bug_report.md` `labels: "type: bug"`, `feature_request.md` `labels: "type: feature"`; `CONTRIBUTING.md`'s Issues section names the three label groups in one line each. These template edits land after Task 7 renames the labels (a template naming a missing label adds nothing), so they go in this PR, which merges after Task 7.
- [ ] **Step 6: Commit** `docs/rules: release, pull request title and milestone rules`.

### Task 6: GitHub analysis and approval

**Files:** none in the repository; tables in `$SCRATCH/github/`.

- [ ] **Step 1: Tags table**: the 24 rows `tag, commit, date` (`v0.1.0 106e83e`, `v0.2.0 a7f015b`, `v0.5.0 06e15f8`, `v0.5.1 b599061`, `v0.5.9 d636b92`, `v0.6.0 50716e4`, `v0.6.1 87b100d`, `v0.6.2 a8bc784`, `v0.6.3 85c3394`, `v0.7.0 46f3199`, `v0.7.1 75174d9`, `v0.7.2 cf65349`, `v0.8.0 0352610`, `v0.9.0 78bf2dd`, `v0.9.1 a7dd48d`, `v0.10.0 3b05ce7`, `v0.10.1 d1ed978`, `v0.11.0 0ca04ae`, `v0.12.0 865fa28`, `v0.12.1 2bc3ac4`, `v0.12.2 25afd00`, `v0.13.0 cfc6354`, `v0.13.1 d966849`, `v0.13.2 e31b1d7`), each date the commit's committer date. Check every commit is a first-parent ancestor of `master` (`git rev-list --first-parent master | grep -c <sha>` prints 1); a tag off the first-parent line gave git-cliff a wrong previous version.
- [ ] **Step 2: Labels table**, per the spec's Labels section: the 8 `type:` labels, one `area:` label per top-level item of `README.md`'s v1 roadmap, the 3 `status:` labels, each with a one-line description and its own color (first one color per group; on 2026-10-31 the owner asked for a distinct, vivid color per label, applied with `gh label edit`). Rows say which are renames (`bug`, `enhancement`, `documentation`), which are new, and which are deleted (`duplicate`, `invalid`, `question`, `wontfix`, after rechecking that nothing uses them).
- [ ] **Step 3: Milestones table**: the proposal below, drafted on 2026-10-31 from `docs/roadmap.md`, then corrected by reading every merged pull request's body and commits. A pull request belongs to one milestone only, so each is placed where its main work went; work that finished a roadmap step that is fully done gets no milestone. "Remaining" items become open issues in Task 7, so the progress bar (closed over total) counts the work left. Each milestone gets a two or three line description (what is done when it closes, its roadmap section). Recheck the table against `docs/roadmap.md` and the PR list before showing it.

| Milestone | Area | Merged PRs | Open issues now | Remaining, one issue each | Progress |
|---|---|---|---|---|---|
| Error messages on tables | errors | #71 | | Move the remaining engine messages onto the tables | 1/2 |
| Iterated ops (Σ, Π) | scientific | #75, #76, #78, #80 | | Periodic products; arithmetico-geometric sums; trig like-term folding; term splitting | 4/8 |
| Math render widgets | ui | #5, #7, #8, #12, #13, #14, #16, #17, #22, #25, #28, #31, #32, #33, #48, #49, #66, #67, #68, #73 | | Σ and Π widgets; absolute value and floor/ceil widgets; raw and rendered toggle; selective render mode in the main display | 20/24 |
| Constant menu | menubar | #61 | | Custom constant button; constants keypad with its View menu toggle | 1/3 |
| Statistic operations | statistic | #55 | | Percentile and quantile; mode, range and unique count; sort, filter and sample; correlation, covariance and linear regression; edge cases and error messages | 1/6 |
| Themes | ui | #89, #91, #103 | #97, #98, #102, #104, #105, #106 | Custom theme settings panel | 3/10 |
| Settings window | menubar | | | General settings (digits, precision, render policy); fonts; constants settings; keyboard shortcut configuration | 0/4 |
| History options | history | | | Configurable max item count; turning history persistence off; export as a text file | 0/3 |
| Test coverage | tests | #15, #18, #19, #38, #43 | #107 | GUI unit tests | 5/7 |
| Statistic data store | statistic | | | Add, remove, edit and clear data points; mutation preview with element count; dataset persistence toggle | 0/3 |
| CSV collection load | statistic | | | Native CSV fast path; multi-column ingest into named collections; load dialog with preview and type detection; missing values and imputation; malformed input errors | 0/5 |
| Data normalization | statistic | | | Min-max and z-score scaling; log and log1p transforms; outlier detection and handling; a stored, reversible transform pipeline | 0/4 |
| Statistic panel and keypad | statistic | | | Data panel with dataset list and summary; statistic keypad with Shift operations; statistic layout preset | 0/3 |
| Line-based sheets | parser | | | Row-based expression model; ANS and previous-line references; per-sheet variable store; failed-line isolation; line actions; sheet tabs with persistence; Simple and Advanced calc modes | 0/7 |
| User-defined functions | parser | | | `f(x) = expr` definitions called like built-ins | 0/1 |
| Piecewise expressions | parser | | | Piecewise expressions with conditions; piecewise render widget | 0/2 |
| Help menu and About | menubar | | | About dialog (version, platform, Qt, commit, license); user manual; Find Action; copy debug info | 0/4 |
| Accessibility pass | ui | | | Tab order and focus; High-DPI and font scaling; tooltips for the keys that have none | 0/3 |
| Runtime paths and crash log | packaging | | | Log files under a QStandardPaths location; unhandled exception hook writing a log file | 0/2 |
| Versioning and releases | packaging | this PR | #110 | | 0/2 |
| Linux release (Flatpak) | packaging | | | Source install for users; Flatpak build; Flatpak attached to the release | 0/3 |

Not milestones: every fully done roadmap step (expression pipeline, collections, call parens, rationals, variables, constant table, scientific basics, dock layout, custom pad, collection GUI, history panel basics, the history renderer of #23, #39, #42), #56, #64, #65 and #70, whose work finished fully done steps, and Windows and macOS packaging (deferred). Open issues #95 and #108 get labels and no milestone. The per-PR evidence is in `$SCRATCH/research/assignments.md` (research run of 2026-10-31, every merged PR's body and commits read).
- [ ] **Step 4: Assignments table**: every open issue and every merged PR with its `type:` label, its `area:` label (or none), its milestone (or none), and for open issues its `status:` label, consistent with Step 3, from the research in `$SCRATCH/research/assignments.md`. Plus the roadmap drift list: "Add custom pad" (all children checked, parent not), "View menu" and "Keypad layout presets" (their one remaining child moved to Custom constants and Statistic panel and keypad), and any other found in the recheck.
- [ ] **Step 5: Issues table**: one row per "Remaining" item of Step 3 (62 rows): title `feat: <item>`, labels `type: feature`, its `area:` label and `status: needs spec`, its milestone, and a body of two or three general sentences: what the user gets, and `Roadmap: docs/roadmap.md, <section>`. The body ends with `Details come with the spec when the work starts.` No design, no mechanism: the detailed issue is written in the spec step of that work.
- [ ] **Step 6: Confirm** on one merged PR that `gh pr edit N --milestone` works, by asking the owner first for that single edit. Then show all five tables and wait for approval; changes to them are made before anything else is sent.

### Task 7: Apply the GitHub changes

- [ ] **Step 1: Tags.** For each approved row: `GIT_COMMITTER_DATE=<date> git tag -a <tag> -m "TCalc <version> (tagged retroactively)" <commit>`, then `git push origin <tag>`, one by one. Verify: `git ls-remote --tags origin 'v*' | grep -vc '\^{}'` prints 24.
- [ ] **Step 2: Repository settings**, set by the owner by hand in the GitHub settings (2026-10-31): a tag ruleset `version tags` on `refs/tags/v*`, active, with Restrict deletions and Restrict updates and no bypass actors (creating a tag stays allowed, so `release.yml` can tag); "Allow GitHub Actions to create and approve pull requests"; and, after this pull request merges, `Pull Request Title` as a required check of `masterRule` (required earlier, it would hold every other pull request, since `pr-title.yml` reaches `master` with this one). `masterRule` keeps merge, squash and rebase. Verify: `gh api repos/0x74h51N/TCalc/rulesets` lists `version tags` as active, and `gh api repos/0x74h51N/TCalc/actions/permissions/workflow` shows `can_approve_pull_request_reviews` true.
- [ ] **Step 3: Labels, milestones, assignments, issues** from the approved tables, in that order, by a script in `$SCRATCH/github/apply.sh` that reads them, so what is sent is what was approved. Labels first: the three renames with `gh label edit <old> --name <new> --color ... --description ...`, then the new ones with `gh label create`, then the four deletions. Issues are created with `gh issue create --title ... --label "type: feature" --label "area: ..." --label "status: needs spec" --milestone ... --body-file ...`, one per row, with a one second pause between calls to stay under GitHub's secondary rate limit. Verify: `gh api 'repos/0x74h51N/TCalc/milestones?state=all' --jq '.[] | "\(.title) \(.closed_issues)/\(.open_issues + .closed_issues)"'` matches the Progress column of Step 3 (Versioning and releases reads 0/1 until this PR is assigned in Task 8).
- [ ] **Step 4: Preview `0.14.0`** with the real tags: `.venv/bin/git-cliff --unreleased --tag v0.14.0` in the repository. Expected: a section from the merges after `v0.13.2`, without #91 (its title does not match); show it to the owner, who decides what the release pull request adds by hand.

### Task 8: Pull request and release v0.14.0

- [ ] **Step 1: Full suite**: `make py-test` and `make native-test`. Expected: green.
- [ ] **Step 2: Open the PR** to `master` with the owner's approval, titled `build: versioning, generated changelog and release workflows`, `--milestone "Versioning and releases"`, `--label "type: feature"` and `--label "area: packaging"`, `Closes #110`. The description says what changed, why, what to look at first (`cliff.toml`, the two release workflows), and carries the inventory: every merged PR up to #94 with its version and section or its `none` reason.
- [ ] **Step 3: After the owner merges**, the owner starts `release-pr.yml` with `bump: minor`: #91's title `Feat/theme switching` does not match `^feat[/:]`, so `bump: auto` would give a patch. The owner approves the release pull request's CI run, adds the theme switching line under `### Added` by hand, and merges it with a merge commit.
- [ ] **Step 4: Verify the release**: `git ls-remote --tags origin v0.14.0` prints the tag; `gh release view v0.14.0` shows the notes and the compare link; `gh run list --workflow release.yml -L 1` is successful.
