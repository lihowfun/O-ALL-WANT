# Minimal Example Project

This folder is a committed post-install snapshot of the Agent Memory Framework.
It is meant to answer two questions quickly:

1. What does a freshly installed project look like after customization?
2. Which commands were used in the P0 smoke test?

Release tracking for this sample lives in [../../docs/Release_Checklist.md](../../docs/Release_Checklist.md).

## Validation Commands

Run these from `example/minimal-project/`:

```bash
python3 scripts/context_hub.py status
python3 scripts/context_hub.py search ""
python3 scripts/context_hub.py memory show --last 3
python3 scripts/context_hub.py annotate Known_Limitations "[BUG] Example validation note"
```

## Measured Baselines

- Clone + install + first `status`: 3.55s on 2026-04-13
- Install only: 0.04s on 2026-04-13

## Installed Tree

```text
minimal-project/
├── AI_CONTEXT.md
├── CLAUDE.md
├── ROADMAP.md
├── VERSION.json
├── .agents/
├── .github/
├── docs/knowledge/
└── scripts/context_hub.py
```

## What To Inspect

- `AI_CONTEXT.md`: a filled-in single source of truth
- `CLAUDE.md`: lazy-read rules plus project-specific forbidden actions
- `docs/knowledge/`: real sample knowledge records instead of raw placeholders
- `.agents/memory.md`: example decision history after initial validation
- `scripts/context_hub.py`: the same cross-platform CLI script installed by
  `install.sh`
