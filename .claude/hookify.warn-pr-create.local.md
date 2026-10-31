---
name: warn-pr-create
enabled: true
event: bash
pattern: \bgh\s+pr\s+create\b(?!(?=[^|;&\n]*--milestone)(?=[^|;&\n]*--label))
---

**The title is the changelog line, and CI checks its pattern.** Check the open milestones and pass `--milestone` and `--label` (`type:` and `area:`); leave the milestone out only if the work serves none. See `docs/rules/ai/release.md`.
