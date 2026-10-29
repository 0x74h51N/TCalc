# Docs

- AI process documents live in the repository under `docs/superpowers/`: specs in `docs/superpowers/specs/`, plans in `docs/superpowers/plans/`, together with status notes and the day's change notes. They are written in English.
- Markdown is not hard-wrapped. A paragraph is one line; a new line starts only a new paragraph, a list item, a table row or a heading.
- No horizontal rules in Markdown. Headings separate sections.
- Math in Markdown is always LaTeX: `$...$` inline, `$$...$$` for blocks, including fractions, powers, sums, roots, inequalities, scientific notation and $O(\cdot)$. GitHub renders it natively. Raw values (`Rational(0)`, `1.1102230246251565e-16`) stay in backticks. Terminal answers do not render LaTeX, so use plain notation there.
- `docs/roadmap.md` is for users: it informs and makes them curious. Only user-facing feature items go there. Maintenance and infrastructure (dependency pins, CI, Boost limits, tidy) and a branch's remaining work go into the status and plan documents under `docs/superpowers/`.
- A roadmap item that has no design yet is one high-level line, with no mechanism or implementation detail. Detail belongs only to items that are done or designed.
- A spec does not describe behavior for a case that has not happened, and a plan does not carry a task for one. A requirement that starts with "in case", "if later", "for safety" or "should it ever" is cut before the spec is approved.
- A plan names the existing code each task builds on. A task that adds a new file, class or layer says so out loud, with its argument, where the owner can refuse it.
