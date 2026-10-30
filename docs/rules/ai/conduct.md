# Conduct

## When a rule is broken

- Stop. Do not continue the task on top of the violation.
- Name it: which rule, in which file, and what exactly was done.
- Undo your own part if it is not committed yet. If undoing it needs git history work, say so and wait.
- After a false claim, no claim counts on its own word for the rest of the session: every "passes", "works" or "measured" comes with the command and its output in the same reply.
- If the same rule is broken twice, propose a hookify rule that would have caught it.

## Writing style

- Never use an em dash, anywhere: code, comments, Markdown, commit messages, PR text, chat. Use a comma, a colon, parentheses or a new sentence.
- The conversation with the owner may be in any language; everything written into the repository is in English.

## Files and moves

- An assistant does not move, rename, delete a file, create a directory, or search and replace an identifier across the repository as an errand of its own. It names the command (`git mv a b`) and the owner runs it; the assistant then follows the imports. A move a plan explicitly names is the exception.
- The last step of any move is to grep the whole tree for the old path, docs included.
- A move that is half done is reported, not repaired. Putting it back is a move too.
