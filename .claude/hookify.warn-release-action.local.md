---
name: warn-release-action
enabled: true
event: bash
pattern: \bgit\s+(-C\s+\S+\s+)?tag\s+(-a|-s|-d|-f|v\d)|\bgit\s+push\b[^|;&\n]*(refs/tags/|\sv\d+\.\d+\.\d+|--tags)|\bgh\s+(release|label)\s+(create|edit|delete)|\bgh\s+workflow\s+run\s+release|\bgh\s+api\b[^|;&\n]*(milestones|labels|rulesets)[^|;&\n]*(-X\s*(POST|PATCH|DELETE)|-f\s|--field)
---

**Release actions are the maintainer's.** Tag, release, start the release workflow, or create, edit or delete a milestone, label or ruleset only when the human agent asked for it in this conversation. See `docs/rules/ai/release.md`.
