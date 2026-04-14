# Agent Memory Framework

> A simple file-based framework for giving coding agents memory, durable notes,
> and reusable workflows across sessions.

## Quick Start (< 1 minute)

Measured on 2026-04-13: clone + install + first successful
`python3 scripts/context_hub.py status` completed in 3.55s on macOS.

```bash
cd /path/to/your/project
git clone https://github.com/lihowfun/agent-memory-framework.git .agent-framework
bash .agent-framework/install.sh
```

After install:

1. Edit `AI_CONTEXT.md`
2. Edit `CLAUDE.md`
3. Tell your agent: "Read `CLAUDE.md` first, then `AI_CONTEXT.md`."

## What You Get

- `AI_CONTEXT.md`: the main project context file
- `.agents/memory.md`: rolling recent decisions and findings
- `docs/knowledge/`: durable topic pages
- `.agents/skills/`: reusable markdown workflows
- `scripts/context_hub.py`: optional CLI helper
- `docs/raw/` + `scripts/wiki_sync.py`: optional raw-note and wiki-sync layer

## Common Commands

```bash
python3 scripts/context_hub.py status
python3 scripts/context_hub.py search "bug"
python3 scripts/context_hub.py memory add "[DECISION] Switched to approach X"
python3 scripts/context_hub.py annotate Known_Limitations "[BUG] Reproduced on Windows"
```

## Optional Wiki Sync

Use this only when you want `docs/raw/` notes to compile into durable wiki pages.

```bash
python3 scripts/wiki_sync.py build
python3 scripts/wiki_sync.py refresh Experiment_Findings
python3 scripts/wiki_sync.py lint
```

## Examples

- [Minimal Install Fixture](example/minimal-project/README.md) — a committed post-install snapshot
- [Public Hybrid Demo](example/public-hybrid-demo/README.md) — a sanitized example with raw notes, compiled wiki pages, and reusable skills

## Docs

- [CLI Reference](docs/CLI_Reference.md)
- [Skill Guide](docs/Skill_Guide.md)
- [Wiki Sync Guide](docs/Wiki_Sync_Guide.md)
- [Architecture Origins](docs/Architecture_Origins.md)
- [Design Principles](docs/Design_Principles.md)

## FAQ

**Do I need Python?**  
No. The file structure still works without Python. Python is only needed for
the optional helpers.

**Do I need the wiki compiler on day one?**  
No. Start with `AI_CONTEXT.md`, `memory.md`, knowledge topics, and skills. Add
`docs/raw/` and `wiki_sync.py` later if manual knowledge maintenance gets noisy.

## Platform Support

- Linux: supported
- macOS: supported
- Windows: supported by the CLI lock fallback, but a native smoke test is still recommended

## License

MIT
