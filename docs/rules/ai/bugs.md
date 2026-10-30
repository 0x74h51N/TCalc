# Bugs

- No bug, no fix. Code that works is not changed under the name of a fix; a fix needs a bug that has been seen.
- No bug is fixed on a hallucinated assumption. Reproduce it first: run it, test it or measure it, and see the failure with your own eyes. Reading the code and guessing is not seeing the bug; type probes, overflow edges, underflow and precision loss are found by running the code.
- Find the root cause, then explain the cause and the planned fix to the owner before you touch a file. Read-only probes are fine; edits wait for approval.
- A bug gets its test before it gets its fix. The test fails without the fix and passes with it. If the test already passes before the fix, it proves nothing.
- Do not add extra checks "just in case". Every `if`, guard, fallback or validation must answer one question: which concrete input takes this branch, and what breaks without it? Name the input from this repository (a value a user can type, a test that went red, an error that was actually seen). If there is no answer, it does not go in.
- What counts as a case that happened: it happened (a bug, a red check), the input produces it (a real expression reaches it), or the platform does it (an API that is documented to fail does fail).
- Defensive code hides the bug it was written for. A fallback that quietly returns a default turns a broken path into a wrong answer every check passes. When something unexpected arrives, fail loudly and name it; do not branch around it.
- A case you believe is possible but have not seen goes in the report to the owner, not in the code.
- Never work around a failing test or benchmark with a patch on top of a library. Fix the structure, or report that it cannot be fixed yet.
