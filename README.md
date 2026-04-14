# Agent Memory Framework

> **Thin Harness, Fat Skills** — A practical framework for giving AI coding agents long-term memory and executable knowledge.

## The Problem

AI coding agents (Claude Code, GitHub Copilot, Cursor, etc.) forget everything between sessions.
Every new session starts from zero — same bugs rediscovered, same decisions re-debated, same workflows re-explained.

## The Solution

A hybrid router built from durable wiki patterns plus operational markdown
discipline:

| Source | What it provides |
|--------|-----------------|
| [Andrew Ng's Context Hub](https://github.com/andrewyng/context-hub) | Knowledge management infrastructure |
| Karpathy-style LLM Wiki pattern | Raw source layer + compiled durable wiki |
| [MemPalace](https://github.com/MemPalace/mempalace) | Anti-amnesia discipline (forced reports, structured tags) |
| [Garry Tan's "Thin Harness, Fat Skills"](https://x.com/garrytan/status/2042925773300908103) | Executable knowledge (skills as reusable workflows) |
| SEAL-inspired operating style | Strong SSOT, roadmap/version/experiment state |

## Architecture

```
                                ┌───────────────────────────────┐
                                │ Operational Lane             │
                                │ AI_CONTEXT / ROADMAP /       │
                                │ VERSION / recent memory      │
                                └──────────────┬────────────────┘
                                               │
                                               ▼
┌─────────────────────────────┐      ┌───────────────────────────────┐      ┌────────────────────────────┐
│ docs/raw/                   │─────▶│ Compiled Wiki Lane            │◀────▶│ .agents/skills/            │
│ immutable source notes      │      │ docs/knowledge/*.md           │      │ execution lane             │
│ fallback only               │      │ + index.md + log.md           │      │ reusable workflows         │
└─────────────────────────────┘      └───────────────────────────────┘      └────────────────────────────┘

Append-only recent decisions still live in `.agents/memory.md`.
```

## Quick Start (< 1 minute)

Measured in P0 validation on 2026-04-13: clone + install + first successful
`python3 scripts/context_hub.py status` completed in 3.55s on macOS.

```bash
# 1. Clone into your project
cd /path/to/your/project
git clone https://github.com/lihowfun/agent-memory-framework.git .agent-framework

# 2. Run one-command setup
bash .agent-framework/install.sh
```

That's it! The installer:
- ✅ Copies all templates to your project root
- ✅ Creates necessary directories
- ✅ Installs the CLI script
- ✅ Installs the optional wiki compiler
- ✅ Shows you what to edit next

### Next Steps

1. **Edit `AI_CONTEXT.md`** — Fill in your project details (name, architecture, tech stack)
2. **Edit `CLAUDE.md`** — Set language preference + forbidden actions
3. **Tell your AI agent**: "Read `CLAUDE.md` first, then `AI_CONTEXT.md`. Follow the lazy-read protocol."

**That's it.** Your agent now has long-term memory.

---

## Usage Examples

### Use the Context Hub CLI

```bash
# Search knowledge base
python3 scripts/context_hub.py search "bug"

# Add a decision to memory
python3 scripts/context_hub.py memory add "[DECISION] Switched to approach X because Y"

# Annotate a knowledge topic
python3 scripts/context_hub.py annotate Known_Limitations "[BUG] Found edge case with Z"

# Get project status
python3 scripts/context_hub.py status
```

See `docs/CLI_Reference.md` for all commands.

### Build Or Refresh The Wiki Layer

```bash
# Rebuild compiled wiki pages from docs/raw/
python3 scripts/wiki_sync.py build

# Refresh just one topic
python3 scripts/wiki_sync.py refresh Experiment_Findings

# Validate metadata, links, and stale pages
python3 scripts/wiki_sync.py lint
```

### Create a New Skill

Copy `_TEMPLATE.md` from `.agents/skills/`:

```bash
cp .agents/skills/_TEMPLATE.md .agents/skills/my-workflow.md
# Edit frontmatter (triggers, params)
# Fill in steps
```

See `docs/Skill_Guide.md` for a full walkthrough and `docs/Design_Principles.md`
for the architectural rationale.

---

## Documentation

- **[Architecture Origins](docs/Architecture_Origins.md)** — The architectural influences behind the hybrid router
- **[Design Principles](docs/Design_Principles.md)** — How hybrid routing stays thin
- **[CLI Reference](docs/CLI_Reference.md)** — All `context_hub.py` commands with `python3` examples
- **[Skill Guide](docs/Skill_Guide.md)** — How to customize templates and write reusable skills
- **[Wiki Sync Guide](docs/Wiki_Sync_Guide.md)** — Raw source format, build/refresh/lint, and generated wiki rules
- **[Hybrid Router Report](docs/Hybrid_Wiki_Router_Experiment.md)** — Experimental branch recommendation and merge criteria
- **[Release Checklist](docs/Release_Checklist.md)** — P0 findings grouped by release risk
- **[Research Pipeline Demo](example/research-pipeline-demo/README.md)** — Public sanitized hybrid example
- **[Minimal Install Fixture](example/minimal-project/README.md)** — P0 smoke-test snapshot

---

## Why This Works

| Problem | Solution | Impact |
|---------|----------|--------|
| Agent forgets everything between sessions | Rolling memory (`.agents/memory.md`) | Near-zero knowledge loss |
| Durable knowledge gets rewritten ad hoc | `docs/raw/` -> compiled wiki | Stable updates without vector DB |
| Same bugs investigated repeatedly | Edge cases in skills | Auto-loaded on next occurrence |
| Workflows re-explained every time | Fat skills (reusable markdown) | ~2,500 tokens saved per use |
| Startup reads 1000+ irrelevant lines | Lazy-read routing | -79% startup tokens |

**Measured results** (from production use): Startup tokens reduced from ~999 to ~212 lines. Simple query cost from ~3,000 to ~800 tokens (-73%).

---

## FAQ

**Q: Does this work with agents other than Claude?**  
A: Yes. Agent-agnostic. Works with Claude, Cursor, GitHub Copilot, or any LLM coding assistant.

**Q: How many skills should I create?**  
A: Start with 2-3 for tasks you do 3+ times per week. Add more as you discover patterns.

**Q: Can I use this without Python?**  
A: Yes. The core value is in the file structure and protocols. Python is only
needed for the optional helpers (`context_hub.py` and `wiki_sync.py`).

**Q: Do I have to use the wiki compiler on day one?**  
A: No. The default install still works with operational docs + memory + skills.
Add `docs/raw/` and `wiki_sync.py` when your knowledge base grows large enough
that manual topic maintenance becomes annoying.

**Q: What if memory.md grows too large?**  
A: Archive old entries periodically. Keep last 30-50 active.

---

## Platform Support

- ✅ **Linux** — Fully supported
- ✅ **macOS** — Fully supported
- ⚠️ **Windows** — CLI now includes a cross-platform file-lock backend; run a native
  smoke test before public release

## License

MIT — Use it, modify it, share it.

## Credits

Built on ideas from:
- [Andrew Ng's Context Hub](https://github.com/andrewyng/context-hub)
- [MemPalace](https://github.com/MemPalace/mempalace)
- [Garry Tan's "Thin Harness, Fat Skills"](https://x.com/garrytan/status/2042925773300908103)
