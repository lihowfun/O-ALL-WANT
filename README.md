# Agent Memory Framework

> **Thin Harness, Fat Skills** — A practical framework for giving AI coding agents long-term memory and executable knowledge.

## The Problem

AI coding agents (Claude Code, GitHub Copilot, Cursor, etc.) forget everything between sessions.
Every new session starts from zero — same bugs rediscovered, same decisions re-debated, same workflows re-explained.

## The Solution

A three-layer memory system built from three proven architectures:

| Source | What it provides |
|--------|-----------------|
| [Andrew Ng's Context Hub](https://github.com/andrewyng/context-hub) | Knowledge management infrastructure |
| [MemPalace](https://github.com/milla-jovovich/mempalace) | Anti-amnesia discipline (forced reports, structured tags) |
| [Garry Tan's "Thin Harness, Fat Skills"](https://x.com/garrytan/status/2042925773300908103) | Executable knowledge (skills as reusable workflows) |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Session Memory (Built-in)                     │
│  Claude /memory, Cursor rules, etc.                     │
│  Scope: same session only                               │
└─────────────────────────┬───────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Rolling Memory (.agents/memory.md)            │
│  Last 20-50 important decisions/findings                │
│  Scope: cross-session, most recent context              │
└─────────────────────────┬───────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Knowledge Base (docs/knowledge/*.md)          │
│  Permanent topic-indexed knowledge                      │
│  Scope: project lifetime                                │
└─────────────────────────────────────────────────────────┘
```

## Quick Start (< 1 minute)

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
- ✅ Sets up the CLI tool
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
python scripts/context_hub.py search "bug"

# Add a decision to memory
python scripts/context_hub.py memory add "[DECISION] Switched to approach X because Y"

# Annotate a knowledge topic
python scripts/context_hub.py annotate Known_Limitations "Found edge case with Z"

# Get project status
python scripts/context_hub.py status
```

See `docs/CLI_Reference.md` for all commands.

### Create a New Skill

Copy `_TEMPLATE.md` from `.agents/skills/`:

```bash
cp .agents/skills/_TEMPLATE.md .agents/skills/my-workflow.md
# Edit frontmatter (triggers, params)
# Fill in steps
```

See `docs/Design_Principles.md` for skill design guidelines.

---

## Documentation

- **[Architecture Origins](docs/Architecture_Origins.md)** — The three frameworks this is built on
- **[Design Principles](docs/Design_Principles.md)** — "Thin Harness, Fat Skills" explained
- **[CLI Reference](docs/CLI_Reference.md)** — All context_hub.py commands (TODO)
- **[Skill Guide](docs/Skill_Guide.md)** — How to create custom skills (TODO)

---

## Why This Works

| Problem | Solution | Impact |
|---------|----------|--------|
| Agent forgets everything between sessions | Rolling memory (`.agents/memory.md`) | Near-zero knowledge loss |
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
A: Yes. The CLI is optional. Core value is in the file structure and protocols.

**Q: What if memory.md grows too large?**  
A: Archive old entries periodically. Keep last 30-50 active.

---

## Platform Support

- ✅ **Linux** — Fully supported
- ✅ **macOS** — Fully supported
- ⚠️ **Windows** — Not tested (file locking in `context_hub.py` uses `fcntl`, may need adjustment)

## License

MIT — Use it, modify it, share it.

## Credits

Built on ideas from:
- [Andrew Ng's Context Hub](https://github.com/andrewyng/context-hub)
- [MemPalace](https://github.com/milla-jovovich/mempalace)
- [Garry Tan's "Thin Harness, Fat Skills"](https://x.com/garrytan/status/2042925773300908103)
