# Research Pipeline Demo

This is a public, sanitized example of the hybrid wiki router applied to a
small research-pipeline style repo.

It demonstrates:

- **Operational lane**: `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, recent memory
- **Wiki lane**: compiled topic pages in `docs/knowledge/`
- **Execution lane**: reusable workflows in `.agents/skills/`
- **Raw source fallback**: source notes in `docs/raw/`

## Quick Validation

Run these from `example/research-pipeline-demo/`:

```bash
python3 scripts/wiki_sync.py build
python3 scripts/wiki_sync.py lint
python3 scripts/context_hub.py status
python3 scripts/context_hub.py search "router"
python3 scripts/context_hub.py get Experiment_Findings
```

## What To Inspect

- `AI_CONTEXT.md`: lane routing and project rules
- `docs/raw/`: sanitized source notes that feed the wiki
- `docs/knowledge/`: compiled durable pages plus `index.md` and `log.md`
- `BRANCH.md` / `BRANCH_STATUS.md`: branch-style operating docs kept in the example, not the default starter
- `experiments/`: a compact experiment ledger similar to a research repo

## Why This Example Exists

The default starter stays simple. This demo shows the more opinionated operating
style once a project has:

- active experiments
- recurring knowledge refreshes
- branch-level merge criteria
- a need for both raw notes and compact durable docs
