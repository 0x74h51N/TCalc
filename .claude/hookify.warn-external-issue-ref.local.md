---
name: warn-external-issue-ref
enabled: true
event: bash
pattern: \b(gh\s+(pr|issue|api|release)|git\s+commit)\b[\s\S]*([\w.-]+/[\w.-]+#\d+|github\.com/[\w.-]+/[\w.-]+/(issues|pull)/\d+)
---

**External issue or PR reference.** An `owner/repo#N` or a GitHub issue link sends a cross-reference notification to that repository. Ask the owner before writing it; without approval, describe the problem without the reference. See `docs/rules/ai/git.md`.
