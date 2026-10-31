# Release

The procedure is in [release.md](../../release.md); it is not repeated here.

- No file holds the version. It comes from git tags; never write a version number into a file to "bump" it.
- The pull request title is the changelog line. Write it for users when the change is user-visible. Its pattern is in `.github/workflows/pr-title.yml`, the only copy.
- The released sections of `CHANGELOG.md` are not edited, except to mark `[YANKED]` or to fix a factual error.
- Never tag, run `gh release` or `gh workflow run release-pr`, or create, close or delete a milestone, label or ruleset, unless the owner asked for it in this conversation.
- Before writing a spec, list the open milestones (`gh api repos/0x74h51N/TCalc/milestones`) and name the one the spec serves, or propose a new one.
- Open pull requests with `--milestone` (when the work serves one), a `type:` label and an `area:` label.
- An issue opened by an assistant gets its `type:`, `area:` and `status:` labels. The spec step of a work moves its issue from `status: needs spec` to `status: ready`.
