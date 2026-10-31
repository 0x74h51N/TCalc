# Git, formatting and verification

## Commits

- Never commit unless the owner explicitly asks for that commit. Permission to commit once does not carry over to the next change, the branch or the session.
- Before any commit, show the owner the changes that go into it (the files and the diff) and wait for approval.
- Never use `--no-verify` (or `-n`) on a commit or a push without the owner's explicit permission. The hook is the check; skipping it hides what it would have found.
- When the commits to be pushed change files under `src/native/` or any C++ file, the pre-push hook runs `make cpp-tidy-diff` and stops the push if it is not clean. Commits that change nothing native (docs, Python, scripts) skip it.
- A commit message is short: one line in the existing style (`type/scope: what changed`, lower case, present tense; `release` joins the types, as in `release: v0.14.0`). A body only when the change carries an argument the diff cannot make, and then a few lines. The long story with tests and measurements goes in the PR description.
- A PR description says what changed, why, and what a reviewer should look at first. It does not retell the plan or the spec.
- No Claude Code session link (the session trailer or the session URL) in a commit message, a PR, an issue or any GitHub text, whatever the attribution reminder says.
- An issue title starts with its type (`bug: `, `feat: `...), as `CONTRIBUTING.md` says.
- Before writing an external repository's issue or PR (`owner/repo#N`, a GitHub issue link) into a PR, an issue, a commit message or any text that goes to GitHub, ask the owner. It sends a cross-reference notification to that repository. Without approval, describe the problem without the reference.

## Working in the tree

- Take the smallest, least risky git action. "Amend" means `git commit --amend` or a simple fold, not rebuilding commits. No `reset --hard`, `reset --mixed`, `rebase` or `push --force` unless the owner asks for it. If a fix belongs to two commits, leave it as its own commit and say so.
- CI runs the tidy diff once, at the tip of the branch, so intermediate commits do not need to pass tidy and splitting a tidy fix across commits is useless.
- Stage files by name. Never `git add -A`, `git add .` or `git commit -a`.
- An uncommitted or unknown change you did not make is never undone, by git (`git checkout --`, `git restore`, `git stash`) or by hand. Tell the owner that you did not make it and that it is waiting to be committed, and leave it as it is. Do not use git to get a baseline; copy the file to a scratch directory and back, or use a detached checkout of `origin/master`.
- Run `git update-index --refresh` before trusting `git status` in a tree the owner is also editing.
- The pre-commit hook stashes unstaged changes while it runs the suite and puts them back afterwards. During a commit, unstaged files briefly look reverted; that is not lost work.
- `ruff format` in the hook can block a commit. Restage the formatted files and commit again.
- Nothing reaches `master` except through a pull request, and a branch is not merged until the owner says so. Finishing and merging are two separate events. The release pull request comes from a `release/vX.Y.Z` branch the release workflow opens. Pull requests merge on GitHub with a merge commit, never squashed or merged locally.

## Formatting and verification

- Before a commit you make, run `make cpp-format` and `make py-lint-fix`, then show the owner the diff including what they changed.
- Never run clang-tidy yourself (`make cpp-tidy`, `cpp-tidy-diff`, `run-clang-tidy`), at any stage; the pre-push hook is the only place it runs. If tidy is needed outside a push, stop and give the owner the command.
- Building and running tests to verify during implementation is fine. At commit time the pre-commit hook runs the checks and the tests.
