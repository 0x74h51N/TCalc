# Versioning

## 2026-10-31: setuptools-scm version strings, measured

Setup: a clone of the working tree in a scratch directory with the edited `pyproject.toml`, `.git_archival.txt` and `.gitattributes` committed on top, a fresh venv (Python 3.14), and in each state `pip install -e . -q && python -c 'import importlib.metadata as m; print(m.version("TCalc"))'`.

1. No tags: `0.1.dev655+gba2d97e65`
2. `git tag -a v0.13.2 -m x HEAD~1` (HEAD is one commit after it): `0.13.3.dev1+gba2d97e65`
3. `git tag -a v0.14.0 -m x HEAD`: `0.14.0`
4. One more commit after it (`git commit --allow-empty -m next`): `0.14.1.dev1+g23a0a8c87`
5. Before the archive, the tag was moved so the archived commit is the one holding the scm files: `git tag -d v0.14.0 && git tag -a v0.14.0 -m x HEAD~1` (after step 4, HEAD~1 is the commit that added the three files; the empty commit from step 4 is HEAD). Then `git archive --format=tar.gz -o a.tgz v0.14.0`, unpacked into an empty directory, `pip install .` there: `0.14.0` (the unpacked `.git_archival.txt` carried `describe-name: v0.14.0`)
6. `git clone --depth 1 file://<scratch>/scm shallow`, `pip install -e .` there: installs (exit code 0) and prints `0.1.dev1+g23a0a8c87`, so a depth-1 checkout reports `0.1.devN` (`git tag` in the clone listed no tags). Conclusion, not measured: a CI job that needs the real version would have to fetch tags.

Reproduction order: 1, 2, 3, 4, then the tag move from step 5, then 5, then 6 (step 6 cloned after the move).

## 2026-10-31: ready tools for the changelog and the version (feat/versioning, base c1811dc)

Tried in a scratch venv, nothing added to the project.

- `python-kacl` 0.7.7 (`kacl-cli verify`, with `default_content: []` so the intro sentence is not required): catches an unknown section, a duplicate section, versions not decreasing, `## [v0.2.0]`, a missing link. It passes an impossible date (`2026-02-30`), sections out of order, an empty section, dates out of order, a link with the wrong target, a duplicated link. It has no tag check and no bump rule.
- `kacl-cli release minor --modify --auto-link` renames `## [Unreleased]` to `## [X.Y.Z] - <today>`, adds an empty Unreleased and rewrites the link block (templates set to `v{version}`). It does not choose the level: `release patch` on an Unreleased with an `Added` line gave `0.2.1`. It reads the host from the git remote; with the SSH remote the links came out as `git@github.com:0x74h51n/TCalc/compare/...`, and a `host` key in `.kacl.yml` was not read. The code reads `CI_PROJECT_URL` first (seen in `kacl/document.py`, not run).
- Release Drafter (README read, not run): it drafts a GitHub release from merged pull requests, can read `$BODY`, resolves the version from labels (`resolved_version` output), and does not write `CHANGELOG.md`.
- `git-cliff` 2.14.2 with a custom parser on merge commits (the merge body is the pull request title): `git-cliff -c cliff.toml c1811dc~12..c1811dc --unreleased` produced a correct Fixed section with the pull request numbers. On the real history the titles drift: of 99 merge titles, 57 do not match `^(feat|fix|perf|refactor|docs|test|ci|chore|build|style)(/[a-z0-9-]+)?: ` (for example `Feat/theme switching` for #91, the branch name `fix/exact-log-inverse` for #85, `bugfix`, `doc`). Generating the past from commits needs the hand backfill; generating the future needs a pull request title check.
- Without a scope filter, dev-only fixes land in the user changelog: the run above listed `fix/ci: format check uses the pinned ruff` (#92) and `fix/scripts: install deps by package name` (#88) next to user-visible fixes.
- `git-cliff --bumped-version` with `conventional_commits = false` and `[bump] custom_minor_increment_regex` matching `feat` merges does not raise the minor: in a scratch clone with the last tag `v0.12.2` and HEAD on the `feat/calc: based log` merge (#86) it printed `v0.12.3`, not `v0.13.0`. With only fixes after `v0.13.2` it printed `v0.13.3`, as expected. The bump by type seems to need Conventional Commits (`feat(scope): ...`), which our `type/scope:` titles are not (not tested with conventional titles). `--bumped-version` counts from the latest tag in the repository, not from the start of a given range.
- `git-cliff --unreleased --bump --prepend CHANGELOG.md` added only the new section above a hand-written one and left the old one as it was.
- Correction to the bump entry above: the range after `c1811dc~6` holds #91 (theme switching, a feature titled `Feat/theme switching`), so `v0.13.3` there was wrong because the parser missed #91, and `v0.14.0` is the right answer.
- `commit_preprocessors` turning `type/scope: ` into `type(scope): ` with `conventional_commits = true` (scratch `cliff2.toml`) did not work: it also converts the commits inside each pull request branch (50 commits for one range instead of the merges), and with HEAD on the #86 merge and the last tag on its first parent it found 0 commits and printed `v0.12.2`. Cause not found; stopped after this attempt.
- Working setup (2026-10-31, scratch clone of c1811dc with `v0.12.2` tagged on the parent of the #86 merge): `conventional_commits = false`, one preprocessor that turns a merge into `<pull request title> (#N)` (`(?s)^Merge pull request #(\d+) from \S+\s*\n\s*([^\n]+).*` to `${2} (#${1})`), parsers that only match `^type/scope: .* \(#\d+\)$`, so the commits inside a pull request branch never match. `git-cliff --unreleased --tag v0.13.0` at the #86 merge gave `## [0.13.0](.../compare/v0.12.2...v0.13.0) - <date>` with `### Added` and `- Based log (#86)`. A compare link inside the heading replaces the link block, so a prepended section carries its own link.
- The bump without git-cliff: `git log --merges --first-parent --format=%b <last tag>..HEAD | grep -q '^feat/'` printed minor at the #86 merge and patch on its parent.
- `--prepend CHANGELOG.md` writes the new section under the config's `header` only when `header` matches the file's opening text; without `header` it put the section above `# Changelog`. `--latest --strip all` after tagging printed the release notes of that version.
- A stray tag on a commit that is not an ancestor of HEAD made `previous.version` wrong and the section empty; with tags only on first-parent ancestors (the retroactive tags) it was right.
