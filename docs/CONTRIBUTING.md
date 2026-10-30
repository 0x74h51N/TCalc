# Contributing to TCalc

Bug reports, feature requests and pull requests are welcome. By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Issues

- The title starts with its type, as branches do: `bug: ...`, `feat: ...`, `docs: ...`, `chore: ...`, `perf: ...`, `refactor: ...`. The issue templates fill it in.
- A bug report says what you typed, what you expected and what you got, plus your OS and how you installed TCalc. A screenshot helps for anything visual.
- Search the existing issues first; a duplicate is closed in favor of the older one.

## Setting up

Requirements and the build steps are in [dev.md](dev.md). In short: `make install`, then `make native-build`. `make hooks` installs the pre-commit hook, which runs the format check, lint, typecheck and both test suites before every commit, and the pre-push hook, which runs `make cpp-tidy-diff` before a push that changes native files.

## Pull requests

- Branch from `master` and open the pull request against `master`. Name the branch for what it does: `feat/...`, `fix/...`, `docs/...`, `chore/...`, `perf/...`, `refactor/...`.
- One change per pull request. A refactor and a behavior change are two pull requests.
- Commit messages are one short line in the log's style: `type/scope: what changed`, lower case, present tense (`fix/ui: bundle every icon under assets/icons`).
- The description says what changed, why, and what a reviewer should look at first.
- A bug fix comes with a test that fails without the fix. Where tests go and how they are written is in [tests.md](rules/ai/tests.md); it applies to people as much as to AI assistants.
- Run `make native-test` and `make py-test` before pushing. CI also runs the clang-tidy diff at the tip of the branch.
- Everything written into the repository (code, comments, docs, commit messages) is in English.

The other files in [rules/ai/](rules/ai/) are written for AI assistants, but most of them (code style, git, versions) describe how this project is worked on by anyone.
