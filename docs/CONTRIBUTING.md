# Contributing to TCalc

Bug reports, feature requests and pull requests are welcome. By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Issues

- The title starts with its type, as branches do: `bug: ...`, `feat: ...`, `docs: ...`, `chore: ...`, `perf: ...`, `refactor: ...`. The issue templates fill it in.
- A bug report says what you typed, what you expected and what you got, plus your OS and how you installed TCalc. A screenshot helps for anything visual.
- Every issue gets labels from three groups: `type:` (what kind of work), `area:` (which part of TCalc, at most one) and `status:` (how far along: `needs spec`, `ready`, `blocked`, `needs repro`). The templates set the type.
- Search the existing issues first; a duplicate is closed in favor of the older one.

## Setting up

Requirements and the build steps are in [dev.md](dev.md). In short: `make install`, then `make native-build`. `make hooks` installs the pre-commit hook, which runs the format check, lint and typecheck before every commit, and the pre-push hook, which runs the tests the pushed files need (by the rules CI uses) and `make cpp-tidy-diff` when they change native files.

## AI-Assisted Contributions

AI coding assistants are tools, not substitutes for engineering knowledge, judgment, or responsibility.

**AI-generated contributions are accepted only when the contributor is capable of independently reviewing, understanding, verifying, and maintaining every part of the submitted changes.**

If you cannot confidently evaluate the code an AI produces, identify architectural flaws, recognize unnecessary complexity, assess test quality, and distinguish a proper solution from a workaround, **please do not use AI to produce contributions to this project.**

The contributor is fully responsible for all submitted code, regardless of who or what generated it.

### Autonomous AI agents are prohibited

**Contributions from AI agents that are not supervised by a human agent are completely prohibited.** This covers pull requests, issues, reviews, and comments.

- A human directs the work, reviews the complete result, and decides to submit it. An agent that picks its own work, or that runs on a schedule or a trigger and posts on its own, is not supervised, whoever owns it.
- A pull request or issue comes from the personal account of the human responsible for it, who stays reachable and answers for it. Accounts operated by an agent are not accepted.
- Do not point an agent at this repository's open issues to harvest work. Claim the problem yourself, and understand it yourself.

Such contributions are closed without review, and the account may be blocked from the project.

### Strict requirements

AI-assisted contributions must follow these principles:

- **Understand before changing.** Understand the existing architecture, code paths, and intended behavior before asking an AI to modify them.
- **Reproduce before fixing.** See the failure yourself by running it. A bug an AI inferred from reading the code is a guess, not a bug report and not a reason for a fix.
- **Fix root causes.** Investigate and address the actual source of a problem. Do not stack patches, fallbacks, compatibility layers, or workarounds on top of broken implementations.
- **No unnecessary complexity.** Do not introduce speculative abstractions, redundant helpers, duplicated logic, wrappers, or additional layers without a clear architectural justification.
- **No speculative defenses.** Every guard, fallback, and validation must name the concrete input that reaches it and what breaks without it. If you cannot name one, it does not go in.
- **Respect existing architecture.** Do not work around established design boundaries simply because an AI finds it easier to implement a local workaround.
- **Stay in scope.** Do not submit unrelated refactors, renames, reformatting, or drive-by improvements an AI added along the way.
- **Tests must be meaningful.** Tests must verify actual behavior and intended contracts, not merely reproduce implementation details or make the current implementation appear correct.
- **Test quality matters.** Do not introduce brittle snapshots, arbitrary hash comparisons, unnecessary production-data dependencies, or tightly coupled tests without a sound justification.
- **Do not game the test suite.** Never weaken, remove, or modify tests simply to make an implementation pass. Investigate whether the implementation or the test itself is incorrect.
- **Review every change.** Inspect the complete diff, including generated code, test changes, imports, dependencies, and unrelated modifications.
- **Claim only what you ran.** "Tested", "works", and "measured" mean you ran it and saw the result. An AI's report of its own success is not evidence.
- **Answer for it yourself.** You must be able to explain any line of your change when asked. Do not relay review questions to an AI and paste its answers back.
- **Hold your assistant to the project's rules.** An assistant working on this repository must load [AGENTS.md](../AGENTS.md) and the rules it points to. Those rules are not an excuse: you remain responsible for what comes out.

A passing test suite does not automatically mean the implementation or the tests are correct.

**If you cannot independently verify the correctness and quality of AI-generated code, do not submit it.** Submissions that demonstrate these problems may be rejected without further review.

### Disclosure

If AI tools materially contributed to your implementation or tests, disclose their use in your pull request and explain how you verified the resulting changes. The pull request template has a field for it. Undisclosed use is itself a reason to close a pull request.

## Contribution Workflow

All code contributions must be developed in a local Git clone and submitted through a Pull Request.

Contributions made directly through GitHub's web editor are not accepted for code changes.

### Fork and clone

1. Fork this repository on GitHub.
2. Clone your fork to your local machine:

   ```bash
   git clone https://github.com/<your-username>/TCalc.git
   cd TCalc
   ```

3. Add the original repository as the upstream remote:

   ```bash
   git remote add upstream https://github.com/0x74h51N/TCalc.git
   git fetch upstream
   ```

4. Create a dedicated branch from upstream `master`:

   ```bash
   git switch -c <branch-name> upstream/master
   ```

5. Make your changes, review the complete diff, run `make native-test` and `make py-test`, and commit your work.
6. Push your branch to your fork:

   ```bash
   git push -u origin <branch-name>
   ```

7. Open a Pull Request from your fork to `master` of the original repository.

Every Pull Request must have a clear scope, explain the problem being solved, describe the implementation, and document the tests performed. On your first Pull Request, CLA Assistant asks you to sign the contributor license agreement: you submit your work under the project's license (GPL-3.0-or-later), you have the right to, and you work as this document says. Every line you sign is a claim you answer for. CI checks the signature and then the title before anything else, and until they pass no other check runs. When you sign, CI starts again by itself.

## Pull requests

- Name the branch for what it does: `feat/...`, `fix/...`, `docs/...`, `chore/...`, `perf/...`, `refactor/...`.
- One change per pull request. A refactor and a behavior change are two pull requests.
- Commit messages are one short line in the log's style: `type/scope: what changed`, lower case, present tense (`fix/ui: bundle every icon under assets/icons`).
- The title is the changelog line: `type/scope: what changed`, written for people who use TCalc when the change is user-visible. CI checks it. Pull requests are merged on GitHub with a merge commit.
- A maintainer sets the milestone the work serves (if any) and the `type:` and `area:` labels. Releases and their procedure are in [release.md](release.md).
- The description follows the template: what changed and why, what a reviewer should look at first, how it was tested, and whether the change is breaking (the template says `**Breaking:** no`; change it to yes if [release.md](release.md#version) says so).
- A bug fix comes with a test that fails without the fix. Where tests go and how they are written is in [tests.md](rules/ai/tests.md); it applies to people as much as to AI assistants.
- CI also runs the clang-tidy diff at the tip of the branch.
- Everything written into the repository (code, comments, docs, commit messages) is in English.

The other files in [rules/ai/](rules/ai/) are written for AI assistants, but most of them (code style, git, versions) describe how this project is worked on by anyone.
