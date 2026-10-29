# Subagents

- Never start many subagents at the same time. Run one agent at a time; if two must run at once, each brief names the files, ids and directories that belong to it and to nothing else.
- A commit step planned for a task is followed, but no commit is made without the owner's approval: the subagent stops at the commit step, and the commit is made after the owner has seen its diff and approved it.
- `kill -9` does not stop a subagent; it only kills its shell, and the agent keeps editing files. Stop agents with `TaskStop`. To see whether one is still alive, check the time of the last event in its transcript, not the process list.
- The red phase of TDD can hang the suite. A test that expects a closed form over a huge range runs the brute force loop forever while the closed form does not exist yet. Take the red proof from a small range and keep the large range case for green.
- `timeout` cannot interrupt a long C++ bignum computation; the signal reaches Python, but the work never returns to the interpreter. Run long computations detached and kill them by PID.
- Snapshot the files before every fix round, so a scoped re-review gets only that round's diff.
- Do not trust a report; verify it independently: the test count, the values, the behavior. Read the diff against `HEAD`, not only the test count. A stale build from a branch switch can report the wrong number of tests. When a session limit cuts an agent off, read the tree yourself to see where it really stopped before handing the task on.
- Check a brief against the code before sending it. A wrong "revert these" list makes an agent break committed code while obeying the brief.
- Do not write a guessed number into a brief as a requirement. Ask the agent to measure it and report it.
