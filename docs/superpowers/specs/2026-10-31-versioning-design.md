# Versioning, changelog, milestones and releases

Phase 1 of the release work: how TCalc is numbered, how its history is written down, how work is targeted and how a release is made. Phase 2 is a source install for users (`make install ARGS=release`, launcher, desktop entry) and phase 3 is a Flatpak attached to the GitHub release; each gets its own spec. The About dialog and the license metadata fix get their own spec as well. macOS packages are deferred.

## Why

TCalc has never had a release. The version in `pyproject.toml` is `0.6.3`, last raised on 2026-03-06 (`bae0545`, which came in with #19); 79 pull requests have merged after #19, nothing reads the number and nothing checks it. There is no tag, no GitHub release, no changelog, no milestone, and the only labels are GitHub's defaults. Progress is tracked by rough percentages in `docs/roadmap.md`, which drifts: the View menu (#64) and the keypad presets (#65) are merged but still unchecked there.

Before TCalc can be packaged and downloaded (phases 2 and 3), a version has to mean something, every version has to say what it brought, work has to have a target, and a release has to be one repeatable procedure. Nothing in that procedure that can be derived is left to a hand: the version, the changelog section, the tag and the release notes are generated, and the person only decides when to release and reviews what was generated.

## Goals

- The version is derived from git tags by setuptools-scm; no file holds the number. The first release is `v0.14.0`.
- Every past version gets a retroactive git tag on the commit that ends it, so each merged pull request's version shows on GitHub and every compare link is between two tags.
- `CHANGELOG.md` covers the whole history, `0.1.0` to `0.14.0`. The past is written by hand once; every release after it is generated from the merged pull request titles.
- A release is two steps for the owner: start the release workflow, merge the release pull request it opens. The version, the changelog section, the tag and the GitHub release follow from that.
- GitHub milestones are concrete roadmap steps; past merged pull requests are put into them, so each milestone shows its real progress.
- `type:`, `area:` and `status:` labels sort issues and pull requests.
- AI rules, hookify rules and contributor docs make all of this the normal way of working, for assistants and people.

## Non-goals

- No GitHub releases for past versions. `v0.1.0` to `v0.13.2` are tags only; `v0.14.0` is the first release.
- No version labels on pull requests. A pull request's version is the first tag that contains its merge commit, which GitHub shows on the commit page.
- No due dates on milestones.
- No version shown in the app; the About dialog has its own spec.
- No packages and no install mode: phases 2 and 3.
- No hand-kept `## [Unreleased]` section. What is unreleased is the list of pull requests merged since the last tag; the release workflow writes it down when it releases.
- No script that checks a hand-written changelog against the tags. It was built and dropped: what it checked (the version against the tag, the bump rule, the link targets) is now generated, so it cannot drift. The measurements are in `docs/superpowers/findings/versioning.md`.

## Version scheme

- Semantic versioning before 1.0. A release with at least one new feature raises the minor (`0.13.0` to `0.14.0`); a release with fixes only raises the patch (`0.13.0` to `0.13.1`).
- A pull request is a feature when its title starts with `feat`. So a release raises the minor when a pull request titled `feat` merged since the last tag, and the patch otherwise; the release workflow computes it from the merge commits (below).
- A change that makes TCalc unable to read what an older version saved (the history file, `QSettings`, a theme or a custom pad file) is a breaking change. It raises the minor even when it is a fix: the release workflow has a `bump` input, `auto` by default, that the owner sets to `minor` for such a release, and in the release pull request its changelog line gets `**Breaking:**` in front and says what the user loses.
- `1.0.0` comes when the v1 roadmap is done; the release workflow's `bump` input takes `1.0.0` for it. Before that, the `Development Status :: 3 - Alpha` classifier stays.
- The version string is always `MAJOR.MINOR.PATCH`, three integers, which is valid both as semver and as PEP 440. No pre-release suffixes on tags.
- A tag is `v` plus the version (`v0.13.0`), annotated, set by the release workflow on the merge commit of the release pull request on `master`. The retroactive tags of past versions are the one exception (below).
- A published version is never moved or deleted. A broken one is marked `[YANKED]` in the changelog and fixed by a patch release. A GitHub tag ruleset on `v*` blocks deleting and moving tags, so the rule holds without anyone remembering it.
- Tags are not GPG-signed. The workflow pushes them and the ruleset guards them; signing can come with a second maintainer.

## Where the number comes from

setuptools-scm computes the version from git when the package is built or installed:

- `pyproject.toml` drops `version = "0.6.3"`, lists `version` in `[project] dynamic`, and adds `setuptools-scm>=10.3,<10.4` to `[build-system] requires`, pinned to the minor like every other dependency (`docs/superpowers/specs/2026-10-28-dependency-pins.md`). The owner approved the dependency on 2026-10-31.
- At a tag the version is exactly the tag (`0.13.0`). Between tags it is a development version that sorts after the last release, `0.13.1.devN+gHASH` with setuptools-scm's default scheme, where `N` is the commit count since the tag. The strings measured on a scratch clone are in `docs/superpowers/findings/versioning.md`.
- Once the retroactive tags are pushed, the code between `v0.13.2` and `v0.14.0` reads as `0.13.3.devN+gHASH`. Without any tag setuptools-scm would give `0.1.devN`, so the retroactive tags go up before this phase's pull request merges.
- Release archives: GitHub's source archives have no `.git`. A `.git_archival.txt` with `export-subst` in `.gitattributes`, the mechanism setuptools-scm documents for this, puts the commit and tag into the archive, so `pip install` from a release tarball gets the right version. Phase 3's Flatpak builds from that archive.
- Editable installs: `pip install -e .` records the version at install time. A development tree shows the version of its last `make install`; that is expected and is written in `docs/dev.md`.
- CI: `actions/checkout` fetches one commit by default, without tags. Jobs that only build and test do not read the version and stay as they are. The release workflows fetch the full history and tags.

## Pull request titles

A pull request's title is its changelog line. GitHub writes the title into the body of the merge commit (`Merge pull request #103 from ...`, then `fix/keypad: round keys as far as they fit, without resize lag`), so the title is in git history, where the release workflow reads it.

- The title keeps the existing commit style: `type/scope: what changed`, lower case, present tense (`feat/ui: switch between light and dark themes`). The scope may be left out (`ci: run each job only for the paths it checks`).
- The types are those of `docs/CONTRIBUTING.md` (`feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `ci`, `chore`, `build`), plus `release` for the release pull request (`release: v0.14.0`).
- `what changed` is written so it reads well to someone who uses TCalc when the change is user-visible: what they can now do, or the symptom that no longer happens. The release pull request is where a line gets its last polish.
- A CI job checks the title on every pull request (opened, edited, synchronized) against `^(feat|fix|perf|refactor|docs|test|ci|chore|build)(/[a-z0-9-]+)?: \S` or `^release: v\d+\.\d+\.\d+$`, and fails otherwise. It is needed: of the 99 merge titles in the history, 57 do not match (`Feat/theme switching`, `bugfix`, `doc`, a branch name instead of a title), and a title that does not match is a line missing from the changelog. It is a regular expression in a `run:` step, not an action: the ready-made title checkers expect `type(scope):`, which TCalc does not use.
- Pull requests are merged on GitHub with a merge commit, as now. A squash or a local merge would not leave the `Merge pull request #N` commit the changelog is built from.

## Changelog

`CHANGELOG.md` at the repository root, in the [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) layout, generated by [git-cliff](https://git-cliff.org) from the merge commits, with the past written by hand once.

### Format

- A short header: what the file is, that it follows Keep a Changelog, and that versions follow the scheme above. git-cliff's `header` setting holds the same text, since `--prepend` only places a new section under the header when the two are equal (measured).
- A version is `## [0.14.0](https://github.com/0x74h51N/TCalc/compare/v0.13.2...v0.14.0) - 2026-11-03`: the version linked to its compare view, then the ISO date. The link sits in the heading instead of a link reference block at the end of the file, so a generated section carries its own link and nothing at the bottom has to be rewritten. `0.1.0` links to the `v0.1.0` tree. A yanked version gets ` [YANKED]` after its date.
- Under a version, only these sections, in this order, and only the ones that have lines: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- Each line is one sentence ending with its pull request number, `(#91)`.

### Generation

`cliff.toml` at the repository root configures git-cliff. The settings that matter, each tried on a scratch clone (`docs/superpowers/findings/versioning.md`):

- `conventional_commits = false`. One commit preprocessor turns a merge commit into `<pull request title> (#N)`. The parsers match only `type/scope: ... (#N)`, so the commits inside a pull request's branch, which also start with `feat/` or `fix/`, never reach the changelog; only the merges do.
- `feat` goes to `Added`, `perf` to `Changed`, `fix` to `Fixed`. `fix` with the scope `ci`, `scripts`, `hooks` or `tests` is skipped, as are `refactor`, `docs`, `test`, `ci`, `chore`, `build` and `release`: they have no user-visible effect. A refactor that changes what the user sees is titled for what the user sees.
- `Deprecated`, `Removed` and `Security` have no title type; the rare line that belongs there is moved in the release pull request.
- The heading template writes the compare link from the previous tag to the new one.

git-cliff is a development tool, so it goes into the `dev` extra of `pyproject.toml`, pinned to its minor like the other tools (`git-cliff>=2.14,<2.15`; it ships as a Python wheel on PyPI). `make install` installs it with the other dev tools, and the release workflow installs the same extra. Nothing is added for users.

### Backfill

The past is written by hand from the commits, the pull requests and their descriptions, once, in the same format. It cannot be generated: 57 of the 99 past merge titles do not follow the title pattern, and the early versions have no pull requests. Each version is dated with its last change.

- `0.1.0` to `0.5.9`: the versions `pyproject.toml` already went through before the first pull request, each from the commits up to the commit that set it: `0.1.0` 2025-12-09 (`106e83e`), `0.2.0` 2025-12-12 (`a7f015b`), `0.5.0` 2025-12-18 (`06e15f8`), `0.5.1` 2025-12-19 (`b599061`), `0.5.9` 2025-12-26 (`b716cf1`). The commit that set `0.5.9` is the last commit of #1, which merged the same day, so #1 belongs to `0.5.9`.
- `0.6.0` to `0.13.2`: the merged pull requests from #2 on, in merge order, cut by the bump rule of Version scheme applied to the past. A minor ends at the last feature pull request of its range. The fixes merged after it become patches of that minor, a new patch wherever the fixes are split by a gap of days or by a change of subject. `0.6.3` keeps the commit that set it (`bae0545`, in #19).
- `0.14.0` is the first generated release: everything merged after `0.13.2`.

Hand-written lines follow the title rules above: written for someone who uses TCalc, one change per line, the pull request number at the end, or several if several pull requests made it (`(#75, #76, #78)`). Commits without a pull request (everything before #1, and the 60 commits made straight on `master` between #1 and #2) are cited by short SHA, `(3529d20)`. A small fix gets its own line, written as the symptom the user saw. A performance change names what got faster, with the measured number from its pull request where it has one. Tests, CI, docs, hooks, refactors and internal moves get no line.

Every merged pull request up to `0.13.2` lands in exactly one version. A version is dated with its last merge.

| Version | Date | Pull requests | Headline |
|---|---|---|---|
| 0.6.0 | 2026-02-21 | #2 to #6 | Native parser, BigComplex, round ops, LaTeX expression editor |
| 0.6.1 | 2026-02-27 | #7 to #11 | Whitespace and paren fixes, faster expression utilities, error logs only in debug mode |
| 0.6.2 | 2026-03-02 | #12 to #14 | Paren open, close and backspace rendering |
| 0.6.3 | 2026-03-06 | #15 to #19 | Paren dissolve and cursor focus |
| 0.7.0 | 2026-03-30 | #20 to #30 | History math renderer, dock layout, keypad panels and the custom pad |
| 0.7.1 | 2026-03-31 | #31 | Navigation and editing inside an expression |
| 0.7.2 | 2026-04-03 | #32 to #33 | Math expression alignment, rendering and cursor stability |
| 0.8.0 | 2026-04-10 | #34 to #37 | Exact rational arithmetic |
| 0.9.0 | 2026-05-12 | #38 to #47 | Paint renderer, native render tree, collapsible toolbar |
| 0.9.1 | 2026-05-20 | #48 to #49 | Paren margins, a crash on a deleted scroll target |
| 0.10.0 | 2026-06-19 | #50 to #58 | Collections, statistics functions, multi-argument function calls |
| 0.10.1 | 2026-06-19 | #59 | A freeze when a huge exponent result is edited again |
| 0.11.0 | 2026-07-11 | #60 to #70 | Variables, constants, View menu, keypad presets, subscripts |
| 0.12.0 | 2026-08-20 | #71 to #81 | Native evaluator, Σ and Π with closed forms, exact and periodic trigonometry |
| 0.12.1 | 2026-08-25 | #82 to #83 | BigReal integer reads, collection item formatting |
| 0.12.2 | 2026-08-28 | #84 to #85 | `exp` as its own primitive, exact log inverses |
| 0.13.0 | 2026-09-05 | #86 | Based log |
| 0.13.1 | 2026-09-07 | #87 | A flat script keeps its braces |
| 0.13.2 | 2026-10-29 | #88 to #90, #92 to #94 | App palette follows the theme, bundled icons, Ubuntu install |
| 0.14.0 | release day | #91, #99 onward | Theme switching, versioning, the first release |

The ranges go by merge order, not by number: #43 merged before #42, #77 before #76, and #91 (theme switching, 2026-10-30) after #88 to #94, which is why it opens `0.14.0`. `0.8.0` has no patch: #36 and #37 merged on the feature's own day.

`0.14.0` is generated, but #91's title (`Feat/theme switching`) does not match the pattern, so the generated section misses it, and this phase's own pull requests and #99 to #103 are mostly tooling. The release pull request of `0.14.0` adds the theme switching line by hand, which is what the release pull request is for.

Completeness is checked, not trusted: the backfill pull request lists every merged pull request from #1 to #94, each either with the version and section its line went into or as "no user-visible change" with the reason. A reviewer can see that nothing was dropped.

### Retroactive tags

- Each past version gets an annotated tag, `v0.1.0` to `v0.13.2`, 24 in all, on the commit that ends it: for `0.1.0` to `0.5.1` the commit that set the version in `pyproject.toml` (the SHAs above), for the others the merge commit of the last pull request of its range on `master`: `0.5.9` is the merge of #1 (`d636b92`), since `b716cf1` sits on #1's branch, and `0.6.3` the merge of #19 (`85c3394`), since `bae0545` sits on #19's branch. Every tag is on a first-parent commit of `master`; git-cliff picked the wrong previous version when a tag sat on a commit outside HEAD's history (measured).
- The tag message is `TCalc 0.7.0 (tagged retroactively)`, and the tag date is the version's date (`GIT_COMMITTER_DATE`), so the tag list reads in time order.
- The tags are pushed one by one by name, never with `--tags`. They go up before this phase's pull request merges, so setuptools-scm and git-cliff read `v0.13.2` as the latest tag from the first commit on.
- The boundary commits and the tag dates are in the plan as a table, approved with the other GitHub changes.

## Milestones and labels

GitHub milestones are a flat list; they cannot nest. Large projects use them for something that can be finished and use labels for lasting categories (Kubernetes `area/` and `sig/` labels, Rust `A-` labels). TCalc does the same.

### Milestones

- A milestone is one roadmap step that can be finished: "CSV collection load", "Line-based calculation", "Iterated ops (Σ, Π)". Never a whole roadmap section like "Statistic".
- Its title is the step's name as the roadmap writes it. Its description is two or three lines: what is done when it closes, and the roadmap section it belongs to.
- No due date.
- The first set is every roadmap step that is partly done, plus the steps not started that the v1 roadmap needs. The plan proposes the list with each step's progress measured from the merged pull requests and open issues, the owner picks, and the assistant creates them (see GitHub changes).
- Past merged pull requests that worked on a step are added to its milestone (`gh pr edit N --milestone ...`; the plan confirms on one pull request that GitHub accepts this for a merged one), so the milestone's progress bar counts real work from the start. Open issues that belong to a step go in too.
- A milestone's progress bar counts closed over all of its issues and pull requests, so the work left has to exist as open issues or the bar shows 100%. Each remaining roadmap item of a milestone gets one open issue, `feat: <item>`, with a body of two or three general sentences and its roadmap section. The detailed issue is written in the spec step of that work, not now.
- A pull request belongs to one milestone only, so a past pull request goes where its main work went; one that finished a fully done roadmap step gets none. The proposed table is in the plan.
- A pull request or issue that serves no milestone has none. A fix that comes up on the way goes into the milestone it was found in, if any.
- A milestone closes when its last issue or pull request closes. A closed milestone is what a release reports.

### Labels

A label answers one question at a glance, and every label belongs to one of three groups, each with its own prefix and one color family, so the list of labels on an issue reads as "what kind, about what, how far along".

- `type:`, exactly one on every issue and pull request: `type: feature`, `type: bug`, `type: perf`, `type: refactor`, `type: docs`, `type: test`, `type: ci`, `type: chore` (build, dependencies, tooling, scripts, hooks). The words follow the branch and commit types of `docs/CONTRIBUTING.md`. The type is what the work does: a `fix/` branch that adds a capability is a feature, and its title starts with `feat`.
- `area:`, at most one: one per top-level item of the v1 roadmap in `README.md`, which names the sections of `docs/roadmap.md` with Calculus split into Scientific and Statistic and Tests as its own item: `area: parser`, `area: errors`, `area: scientific`, `area: statistic`, `area: menubar`, `area: history`, `area: shortcuts`, `area: ui`, `area: packaging`, `area: tests`. A new top-level roadmap item gets its label in the same change. Work that fits no section (CI, AI rules) has none.
- `status:`, only on open issues: `status: needs spec` (no design yet; every roadmap issue starts here), `status: ready` (concrete enough to implement), `status: blocked` (waits for another issue, named in its body). The spec step of a work moves its issue from `needs spec` to `ready`.
- GitHub's defaults are folded in: `bug` becomes `type: bug`, `enhancement` becomes `type: feature`, `documentation` becomes `type: docs` (renamed in place, so the issues that carry them keep them). `good first issue` and `help wanted` stay, since GitHub shows them to new contributors. `duplicate`, `invalid`, `question` and `wontfix` are deleted: no issue or pull request uses them (checked on 2026-10-31), and GitHub's close reasons ("completed", "not planned", "duplicate") already say it.
- The issue templates set the type: the bug report `type: bug`, the feature request `type: feature`; the "Other" template sets none, since its type varies.
- Every open issue and every merged pull request gets its labels, the past ones included, so a filter shows a section's history and the open work of one kind.
- Labels do not drive the changelog or the version; the title does. The labels are for finding work.

### Roadmap

`docs/roadmap.md` stays the user-facing plan. Its rough percentages are not maintained by this phase. Where the analysis finds the roadmap out of date (a merged step still unchecked), the plan lists it and the owner decides on the edit.

## Release procedure

TCalc is trunk-based: every pull request merges into `master` as soon as it is done, and `master` stays green. There is no `dev` branch; nothing is deployed from `master`, and users get only what a tag releases. A release is a tag on `master`, not a separate line of code.

A release happens only when the owner says so, usually after a milestone closes. The owner does two things: starts the release workflow and merges the pull request it opens.

### Release pull request workflow

`.github/workflows/release-pr.yml`, started by hand (`workflow_dispatch`) with one input, `bump`: `auto` (default), `minor`, or an exact version such as `1.0.0`.

1. Check out the full history and tags, install git-cliff at the pin of the `dev` extra.
2. Compute the version. The last tag is `git describe --tags --abbrev=0 --match 'v[0-9]*'`. With `bump: auto`, the release is a minor when a merge since that tag has a title starting with `feat` (`git log --merges --first-parent --format=%b <tag>..HEAD | grep -q '^feat[/:]'`, measured: minor at the #86 merge, patch on its parent), and a patch otherwise. `minor` forces a minor; an exact version is taken as it is, after checking it is greater than the last tag.
3. Fail when no pull request with a changelog line merged since the last tag: there is nothing to release.
4. Run `git-cliff --unreleased --tag vX.Y.Z --prepend CHANGELOG.md`.
5. Commit `release: vX.Y.Z` on a branch `release/vX.Y.Z` and open a pull request with that title. Its description lists the merged pull requests the section came from and the milestones that will close.

The owner reviews the generated section in that pull request like any other change, polishes a line, adds `**Breaking:**`, moves a line to `Removed`, and merges it.

The Actions bot opening a pull request needs the repository setting "Allow GitHub Actions to create and approve pull requests". Its `ci.yml` run on that pull request waits as `action_required` until the owner approves it with one click; then the checks attach, and with only `CHANGELOG.md` changed the change filter skips the build jobs and `CI OK` passes (measured on the scratch repository). No token and no bypass actor is added.

### Release workflow

`.github/workflows/release.yml`, on a push to `master` that changes `CHANGELOG.md`, with only the permissions it uses (`contents: write` for the tag and the release, `issues: write` for the milestones):

1. Read the top version heading of `CHANGELOG.md`. If its tag already exists, stop: the push was a fix to the file, not a release (a `[YANKED]` mark, a typo).
2. Fail unless the head commit is the merge of a `release/vX.Y.Z` pull request for that version, so editing the file by hand cannot publish.
3. Tag the commit, `vX.Y.Z`, annotated, `TCalc X.Y.Z`, and push the tag. Tagging and publishing happen in this one workflow, because a tag pushed with `GITHUB_TOKEN` would not start a second one.
4. Build the package with `pip install .` and confirm the installed version equals the tag, which proves setuptools-scm sees the same number.
5. Take the top section of `CHANGELOG.md`, the reviewed one, as the release notes, end them with the compare link (`**Full changes**: https://github.com/0x74h51N/TCalc/compare/v0.13.2...v0.14.0`), and run `gh release create vX.Y.Z --title "TCalc X.Y.Z" --notes-file ...`. It is a normal release, not marked pre-release; the alpha status is the `0.x` number and the classifier.
6. Close every open milestone whose issues and pull requests are all closed: the work it tracked has shipped in this release.

Phase 3 adds a job that builds the Flatpak and attaches it to this release.

## AI rules and contributor docs

- A new `docs/rules/ai/release.md`, imported in `CLAUDE.md` with the other rule files. It holds, briefly: the version scheme and the bump rule; that no file holds the version; the pull request title rules, since the title is the changelog line, with a pointer to the CI job that holds the pattern; that an assistant never edits a released section of `CHANGELOG.md` except to mark `[YANKED]` or fix a factual error, never tags, never runs `gh release` or the release workflows, and never creates, closes or deletes a milestone or label unless the owner asked for it in that conversation; a pointer to `docs/release.md` for the procedure, which it does not repeat; and the milestone rules below.
- Milestones in design: before writing a spec, an assistant lists the open milestones (`gh api repos/0x74h51N/TCalc/milestones`), and the spec says which milestone it serves and what part of it the work completes. If the work fits none, the spec proposes a new milestone (title and description), and the assistant creates it once the owner approves the spec.
- Pull requests: opened with a title that matches the pattern, with `--milestone` when the work serves one, and with its `type:` and `area:` labels. The PR description says what part of the milestone it closes.
- Hookify rules in `.claude/`, matching the existing ones:
  - `warn-release-action`: a bash command that runs `git tag`, pushes a tag, runs `gh release` or `gh workflow run release-pr`, or creates, edits or deletes a milestone or label through `gh api` or `gh label`. The message: only when the owner asked for it in this conversation; see `release.md`.
  - `warn-pr-create`: `gh pr create` without `--milestone` or `--label`. The message: the title is the changelog line and CI checks its pattern; check the open milestones and set the labels; leave the milestone out only if the work serves none. The pattern itself lives only in the CI job, so the hook does not keep a second copy of it.
- `docs/rules/ai/git.md`: `release` joins the commit types (`release: v0.14.0`), and `release/` the branch prefixes; pull requests are merged on GitHub with a merge commit.
- `docs/CONTRIBUTING.md`: the title pattern and that the title is the changelog line; milestones and labels; the release procedure in two lines, pointing to `release.md`.
- `.github/pull_request_template.md`: a reminder that the title is the changelog line, and the milestone the pull request serves.
- `docs/dev.md`: setuptools-scm, that an editable install shows the version of its last install, and git-cliff in the dev tools.
- `docs/release.md`: the one place the release procedure is written, from this spec's procedure section once it is implemented. `release.md`, `CONTRIBUTING.md` and the PR template point to it instead of repeating it.

## GitHub changes

The assistant makes the GitHub changes of this phase with `gh`: it creates the labels, the milestones and the `v*` tag ruleset, labels the open issues and the merged pull requests, adds the past pull requests to their milestones, and pushes the retroactive tags `v0.1.0` to `v0.13.2`. Each is outward and visible to everyone, so it runs only after the owner has approved its list: the plan shows the labels, the milestones with their descriptions, and the pull request and issue assignments as tables, and nothing is sent before the owner says yes to that table. A script in the scratch directory runs the approved table, so what is sent is exactly what was approved, and the assistant reports what GitHub returned. `v0.14.0` is not pushed by the assistant: the release workflow tags it when the owner merges the first release pull request.

## Testing

- `cliff.toml` is tried on a scratch clone before it is committed: a minor at a `feat` merge, a patch at a fix-only range, the commits inside a branch kept out, a skipped scope, the prepend under the header. The results go into `docs/superpowers/findings/versioning.md`.
- The pull request title check gets its regular expression tried against the 99 past merge titles; the matching and the failing counts are recorded.
- Both release workflows run once on a scratch repository before `v0.14.0`, the whole way: start, release pull request, merge, tag, release. The first real release is not their first run. The plan names where.
- setuptools-scm is checked on a scratch clone: the version before the first tag, at a tag, after a tag, and from a `git archive` tarball. The strings are recorded in `docs/superpowers/findings/versioning.md`.
- The suite stays green; the version change touches packaging, so the plan runs the whole suite once at the end.

## Alternatives not taken

All tried on 2026-10-31; the measurements are in `docs/superpowers/findings/versioning.md`.

- A hand-kept changelog with a check script against the tags and the bump rule: built, then dropped. It checks what can be generated instead.
- `python-kacl`: it renames `## [Unreleased]` and writes the links, but does not choose the bump, wrote broken links from the SSH remote, and its `verify` passed an impossible date and wrong link targets.
- Release Drafter: it drafts the GitHub release from labels, but does not write `CHANGELOG.md`, and it makes the labels the source of the changelog, a second place to keep right.
- Conventional Commits titles (`feat(ui): ...`) with release-please or git-cliff's own bump: the owner keeps `type/scope:`. git-cliff's bump by type did not work with it (`v0.12.3` instead of `v0.13.0` at a feature), and a preprocessor that rewrote the titles into the conventional form also pulled in the commits inside each branch; the first-parent `grep` does the bump in one line.
- towncrier or changelog fragments: each pull request adds a small file. The title already carries the line, so a fragment would be a second copy of it.
- A `dev` branch with release merges into `master` (git-flow): it protects a deployed `master`, and nothing is deployed from TCalc's `master`.
- A version literal in `pyproject.toml`: one more file to bump by hand at every release, and `master` would claim the last release's number for unreleased code.

## Calls made without the owner

Settled by the assistant, open to change: the changelog at the repository root in the Keep a Changelog layout; the compare link in the heading instead of a link block; the title-to-section mapping and the skipped scopes; the `bump` input for breaking changes and `1.0.0`; the tag set by the release workflow instead of by hand; the release workflow's checks and permissions; releases not marked pre-release; the milestone closing step; retroactive tags dated to their version's date; annotated, unsigned tags guarded by a tag ruleset; the `**Breaking:**` marker; the `area:` label names; the two hookify rules; a separate `docs/release.md`; `.git_archival.txt` for source archives.

## Left to the builder

The wording of every backfilled changelog line, which section a past change goes in, the exact commit SHAs that bound each backfilled version, and the `cliff.toml` template details.
