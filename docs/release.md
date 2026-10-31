# Releasing TCalc

TCalc is trunk-based: every pull request merges into `master` as soon as it is done and `master` stays green, with no `dev` branch. A release is a tag on `master`, made only when the owner says so, usually after a milestone closes.

## Version

- The version is derived from git tags by setuptools-scm; no file holds the number. A tag is `v` plus `MAJOR.MINOR.PATCH` (`v0.14.0`), annotated, with no pre-release suffix.
- Before 1.0 a release with at least one pull request titled `feat` raises the minor, and a release with fixes only raises the patch.
- A change that makes TCalc unable to read what an older version saved (the history file, `QSettings`, a theme or a custom pad file) is breaking and raises the minor even when it is a fix: start the workflow with `bump` set to `minor`, and write `**Breaking:**` in front of its line in the release pull request.
- `1.0.0` comes when the v1 roadmap is done: start the workflow with `bump` set to `1.0.0`.
- A published version is never moved or deleted. A broken one is marked `[YANKED]` in `CHANGELOG.md` and fixed by a patch release.

## Pull request titles

The title of a pull request is its changelog line: GitHub writes it into the body of the merge commit, and the release reads it from there. Pull requests are merged on GitHub with a merge commit, never squashed or merged locally. The title is `type/scope: what changed`, lower case, present tense, written for someone who uses TCalc when the change is user-visible. The pattern is checked by `.github/workflows/pr-title.yml`, the only place it is written.

In the changelog `feat` goes under Added, `perf` under Changed and `fix` under Fixed; the other types, and `fix` with the scope `ci`, `scripts`, `hooks` or `tests`, are in the history but not in the changelog (`cliff.toml`).

## Procedure

1. Start the `Release PR` workflow (`.github/workflows/release-pr.yml`) from the Actions tab with the `bump` input: `auto` (default), `minor`, or an exact version greater than the last tag.
2. The workflow takes the last `v*` tag, computes the version, fails when no pull request with a changelog line merged since that tag, writes the section with git-cliff, and opens a pull request titled `release: vX.Y.Z` from the branch `release/vX.Y.Z`. Its description lists the section and the milestones that will close.
3. The Actions bot opened the pull request, so its `ci.yml` run waits as `action_required`. Approve the run with one click; with only `CHANGELOG.md` changed the build jobs are skipped and `CI OK` passes. The repository needs the setting "Allow GitHub Actions to create and approve pull requests".
4. Review the generated section like any other change: polish a line, add `**Breaking:**`, move a line to `Removed`.
5. Merge the pull request.

The merge starts `.github/workflows/release.yml`, on a push to `master` that changes `CHANGELOG.md`:

- It reads the top version of `CHANGELOG.md` and stops if that tag already exists: the push was a fix to the file, not a release.
- It fails unless the head commit is the merge of the `release/vX.Y.Z` pull request for that version, so editing the file by hand cannot publish.
- It tags the merge commit `vX.Y.Z` (annotated, `TCalc X.Y.Z`), builds the package with `pip install --no-deps .` and checks that the installed version equals the tag.
- It creates the GitHub release with the top section of `CHANGELOG.md` as the notes, ending with the compare link, then closes every open milestone whose issues and pull requests are all closed.

## Milestones and labels

A milestone is one roadmap step that can be finished, with no due date; it closes with its last issue or pull request, and a release reports the closed ones. Every issue and pull request carries labels from three groups, each with its own prefix:

- `type:` (exactly one): `feature`, `bug`, `perf`, `refactor`, `docs`, `test`, `ci`, `chore`.
- `area:` (at most one): one per top-level item of the v1 roadmap (`parser`, `errors`, `scientific`, `statistic`, `menubar`, `history`, `shortcuts`, `ui`, `packaging`, `tests`).
- `status:` (open issues only): `needs spec`, `ready`, `blocked`, `needs repro`.

Labels are for finding work; they do not drive the changelog or the version, the title does.
