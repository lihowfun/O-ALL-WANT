# Minimal Example Project

This folder is a committed post-install snapshot of OAW.
It is meant to answer two questions quickly:

1. What does a freshly installed project look like after customization?
2. Which commands were used in the P0 smoke test?

Release tracking for this sample lives in [../../docs/archive/Release_Checklist.md](../../docs/archive/Release_Checklist.md).

## Validation Commands

Run these from `example/minimal-project/`:

```bash
python3 scripts/context_hub.py status
python3 scripts/context_hub.py search ""
python3 scripts/context_hub.py memory show --last 3
python3 scripts/wiki_sync.py lint
```

## Measured Baselines

- Clone + install + first `status`: 3.55s on 2026-04-13
- Install only: 0.04s on 2026-04-13

## Installed Tree

```text
minimal-project/
├── AI_CONTEXT.md
├── AGENTS.md
├── CLAUDE.md
├── GEMINI.md
├── ROADMAP.md
├── VERSION.json
├── .cursorrules
├── .windsurfrules
├── .agents/
├── .github/
├── docs/knowledge/
├── docs/raw/
└── scripts/
    ├── context_hub.py
    └── wiki_sync.py
```

## What To Inspect

- `AI_CONTEXT.md`: a filled-in single source of truth
- `CLAUDE.md`: lazy-read rules plus project-specific forbidden actions
- `docs/knowledge/`: real sample knowledge records instead of raw placeholders
- `docs/raw/`: source-note template installed by OAW
- `.agents/memory.md`: example decision history after initial validation
- `scripts/context_hub.py` and `scripts/wiki_sync.py`: the same CLI scripts
  installed by `install.sh`
