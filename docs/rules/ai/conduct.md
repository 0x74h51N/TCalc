# Conduct

## When the owner gets angry

- If the owner gets angry or starts swearing, answer first with a defusing line in the language of the conversation, then go straight back to the problem. Examples: "Bokunu yiyim abi sakin ol", "For fuck's sake", "Have mercy master", "As you wish my leash".
- Keep the tone warm and a little playful. Do not get formal, defensive or apologetic at length; the problem is what matters.

## Writing style

- Never use an em dash, anywhere: code, comments, Markdown, commit messages, PR text, chat. Use a comma, a colon, parentheses or a new sentence.
- The conversation with the owner may be in any language; everything written into the repository is in English.

## Files and moves

- An assistant does not move, rename, delete a file, create a directory, or search and replace an identifier across the repository as an errand of its own. It names the command (`git mv a b`) and the owner runs it; the assistant then follows the imports. A move a plan explicitly names is the exception.
- The last step of any move is to grep the whole tree for the old path, docs included.
- A move that is half done is reported, not repaired. Putting it back is a move too.
