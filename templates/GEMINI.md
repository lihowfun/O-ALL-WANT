# OAW Adapter

Read `CLAUDE.md` first. It is the source of project rules, lazy-read routing,
skills-first behavior, and session-end reporting.

Then read `AI_CONTEXT.md` for project facts.

`.agents/skills/*.md` holds the reusable workflows (classify-evidence,
read-discipline, harness-evaluator, inheritance-check, …). Match the current
task against skill `triggers` before going ad-hoc.
