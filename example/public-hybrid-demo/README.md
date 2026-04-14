# Public Hybrid Demo

This is a public, sanitized example of the hybrid wiki router applied to a
small generic project.

It demonstrates:

- **Operational lane**: `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, recent memory
- **Wiki lane**: compiled topic pages in `docs/knowledge/`
- **Execution lane**: reusable workflows in `.agents/skills/`
- **Raw source fallback**: source notes in `docs/raw/`

## Quick Validation

Run these from `example/public-hybrid-demo/`:

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
- `experiments/`: a compact experiment ledger for a generic public project

## Why This Example Exists

The default starter stays simple. This demo shows a fuller setup once a project has:

- active experiments
- recurring knowledge refreshes
- a need for both raw notes and compact durable docs
