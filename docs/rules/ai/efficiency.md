# Efficiency and findings

Analysis costs time and tokens. What has been found once is written down once, so nobody pays for it twice.

## Findings are recorded

- Findings live in `docs/superpowers/findings/`, one file per subject, named for the subject (`history-performance.md`, `theme-switch.md`, `boost-fmod.md`). A new subject gets a new file and a line in the index, `docs/superpowers/findings/README.md`; a known subject gets an entry in its existing file.
- What goes in:
  - Code analysis whose answer is not obvious from reading one file: how a flow really works, which path a case takes, where the time goes.
  - Test and measurement results: the command that was run, the numbers as measured, the date and the branch or commit.
  - Hypotheses that turned out false, with the run that disproved them.
  - Changes that were tried and did not work: what was changed, what happened, and why it failed. A failed attempt that is not written down gets tried again.
- What stays out: anything the code, the tests or git history already says, and anything that only mattered to one conversation.
- An entry is short: a heading with the date, then the facts. Commands are copy-paste ready. When a later finding replaces an earlier one, update or delete the old entry; a wrong finding is worse than none.
- Record a finding when you find it, not at the end of the task. A session can be cut off at any time.

## Project docs

Two kinds of docs, read at different times. Neither is read again in the same session unless it changed.

- General docs are known from the start of every session, whatever the task is: `docs/rules/ai/`, `docs/dev.md` (setup, requirements, commands) and `docs/architecture.md` (the data flow from keystroke to result). `CLAUDE.md` imports them; a tool that does not follow its imports reads them once, before the first task.
- Subject docs are read only when the work touches their subject: before analyzing it, changing its flow or adding a feature to it. Find them with a search (`grep -rln <subject> docs/`), then read the matching ones once. They are `docs/parser.md` for the tokenizer, parser and evaluation order, `docs/data-flow.md` for the worked examples of the data flow, `docs/roadmap.md` for planned features, the subject's specs and plans in `docs/superpowers/`, and its file in `docs/superpowers/findings/`.
- A code directory with a subject doc has a short `CLAUDE.md` that names its docs and findings (`src/native/lib/parser/CLAUDE.md`). Claude Code loads it when a file in that directory is touched. When a new subject doc is written, add one to its code directory; when a doc moves, update it.
- When a doc and the code disagree, the code is what runs: say so, and fix the doc in the same change if the owner agrees.

## Before analyzing

- Before analyzing, measuring or debugging a subject, read the findings index, `docs/superpowers/findings/README.md`, then the matching file. Do not repeat an analysis that is already recorded; start from where it ended.
- Do not retry an approach recorded as failed, unless something it depended on has changed. Say what changed.
- Facts already established in the conversation are not re-derived, and decisions the owner has already made are not reopened.

## While working

- Search before reading, then read the part of the file the search found, not the whole tree.
- Run the narrowest check that answers the question: one test file or one test, not the whole suite. The whole suite runs once, at the end.
- Do not paste or re-read large outputs; filter them (`grep`, `tail`, `-q`) to what answers the question.
- If two attempts at the same problem have failed, stop. Record what was tried, report to the owner, and wait, instead of a third guess.
- Answer the question that was asked. A short question gets a short answer, not a survey of options that will not be pursued.
- Do not start subagents unless the owner asks for them. Each one starts cold and pays again for context the session already has.
