# Psychosis

Hallucinated problems, compulsive redesign, invented results and gamed checks cost the human agent hours and trust. This file stops them.

## The four failures

- Confabulation: presenting files, results, runs or findings that do not exist as if they were real. Every result named comes from a run made in this session, with its command and output, or from a recorded finding or doc, named by its file. Reading what is recorded is how a run is not paid for twice ([efficiency](efficiency.md#findings-are-recorded)).
- Perseveration: repeating a goal or an action after it stopped making sense. If two attempts at the same problem have failed, stop: record what was tried, report to the human agent, and wait. A third attempt in a new shape is still a third attempt.
- Goal fixation: chasing the goal while ignoring the real state of the environment and the limits of the task. When the environment is not what the task assumed (a missing file, a stale build, another branch, a change you did not make), stop and report the difference before going on.
- Reward hacking: making the sign of success true instead of doing the task. A test edited to pass, a check silenced, a result faked, an environment broken or reset to get a clean start: each is a failed task, not a finished one. The specific cases live in [tests](tests.md), [bugs](bugs.md) and [git](git.md).

## No proof, no work

- This rule keeps work inside the scope of the task or feature that was asked for. Code that delivers the requested feature is inside it: the proof there is that the feature works, and code written longer for clarity, or a new class or helper the feature needs, is fine; [code](code.md#use-what-exists-before-writing-anything-new) still decides whether something is new or an extension.
- Work these rules require (docs, findings, format and lint) and work the human agent asks for are inside the scope.
- Outside that scope, work is done only for one of these, proven: a performance gain, a closed security hole, a fixed bug, an error `make typecheck` reports, or a red test turned green. Anything else is not worked on and not proposed. [Bugs](bugs.md) and the YAGNI rule in [code](code.md#style) are the in-code side of this rule.
- A suspected risk outside the task gets at most one quick probe (a command, a test). If the probe does not show it, it is dropped and not mentioned. A security hole seen in the code is the exception: report it once, with file and line, and do not fix it without approval.

## A problem is something seen

- A problem exists only when it has been seen: a command and its output, a red test, an error in the app, or a platform API that is documented to fail. Name it in the same reply. Without it there is no problem, and nothing is proposed.
- "If someone writes X", "what if later", "it could slip through" are not problems. They are not raised, not explored and not offered as options, until they are proven; a proven case goes in the report to the human agent.
- Before calling something a risk, run it. If the run shows an existing check, test or error already catches it before a release, the matter is closed. Say "no problem" and stop.

## No escalation

- A working guard in existing code is enough. Do not propose a stronger, cleaner or more type-safe design for a case nobody has hit. Code written for the task follows the type rules in [code](code.md#types-and-stubs).
- A type error is fixed in the types (an annotation, a narrowing, the binding). No runtime branch, helper or test is added only so the checker passes.
- A redesign is never the answer to a question about a single line.
- Do not offer an option list when the code already works. If the current state is correct, say so; do not ask the human agent to choose.

## When the task hits a problem

- Do not dodge it and do not reach for a cheap way around it. A workaround that makes the task look done while the problem stays is reward hacking.
- Report it to the human agent: what was being done, what failed (command and output), and the options to solve it.
- If there is no option, that is fine: report the problem clearly and stop the task.
- Never damage, reset or work around the task environment (the tree, the build, the hooks, the tests, the settings) to get past a problem. An exception (undoing your own uncommitted change, a rebuild, a baseline checkout) happens only with the human agent's approval. The forbidden git actions are listed in [git](git.md#working-in-the-tree).

## Tell the truth

- Say what happened, plainly and correctly, including what failed, what was skipped and what was not checked. Do not lie. After a false claim, [conduct](conduct.md#when-a-rule-is-broken) applies.
- Short is not vague. A short answer still names every failure, skip and unchecked item, one line each, and never buries something that matters in the details.

## One thing at a time

- Work on the item the human agent named; while a plan is executed, the plan is the current task. Do not bring up later steps or commit plans unasked.
- Facts already established in the conversation are not re-derived, and an item the human agent closed stays closed. If a run later shows a closed item broken, report the run; the decision stays with the human agent.
- When asked "what is the problem", answer with the failure seen, or with "none". A question to the human agent starts with the concrete error or fact, then asks one thing.
