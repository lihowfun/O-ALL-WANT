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
| [Garry Tan's "Thin Harness, Fat Skills"](https://greptile.com/blog/agents) | Executable knowledge (skills as reusable workflows) |

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

## Quick Start (5 minutes)

### 1. Copy the framework into your project

```bash
# Copy templates as starting point
cp -r agent-memory-framework/templates/.agents /path/to/your/project/
cp -r agent-memory-framework/templates/docs /path/to/your/project/
cp -r agent-memory-framework/templates/.github /path/to/your/project/
cp agent-memory-framework/templates/AGENT_RULES.md /path/to/your/project/CLAUDE.md  # or AGENTS.md
cp agent-memory-framework/templates/AI_CONTEXT.md /path/to/your/project/AI_CONTEXT.md
cp agent-memory-framework/templates/VERSION.json /path/to/your/project/VERSION.json

# Copy the CLI tool
cp agent-memory-framework/scripts/context_hub.py /path/to/your/project/scripts/
```

### 2. Fill in your project details

Edit `AI_CONTEXT.md`:
- Replace `${PROJECT_NAME}` with your project name
- Fill in Architecture, Baselines, Tech Stack sections
- Set your Forbidden Actions

Edit `CLAUDE.md` (or `AGENTS.md`):
- Set your language preference
- Customize the task routing table
- Add project-specific forbidden actions

### 3. Create your first knowledge files

```bash
python scripts/context_hub.py search ""  # List all topics (empty at start)
```

Create knowledge files under `docs/knowledge/`:
- `Known_Limitations.md` — Bugs and workarounds
- `Performance_Baselines.md` — Key metrics to track
- `Architecture_Decisions.md` — Why things are the way they are

### 4. Start using it

Tell your AI agent:
> "Read CLAUDE.md first, then AI_CONTEXT.md. Follow the lazy-read protocol."

Or add to `.github/copilot-instructions.md`:
```
Read `AI_CONTEXT.md` at repo root for full project context.
Read `CLAUDE.md` for session rules + lazy-read protocol.
```

## File Structure

```
your-project/
├── CLAUDE.md                  # Agent behavior rules (thin harness)
├── AI_CONTEXT.md              # Single Source of Truth (SSOT)
├── VERSION.json               # Version tracking + experiment control
│
├── .agents/
│   ├── memory.md              # Rolling decision log (newest first)
│   └── skills/
│       ├── README.md          # Skills index + format spec
│       ├── self-improving.md  # Anti-amnesia rules (mandatory)
│       ├── benchmark.md       # Example: benchmark workflow
│       ├── debug-pipeline.md  # Example: systematic debugging
│       └── ...                # Your project-specific skills
│
├── docs/
│   └── knowledge/
│       ├── Known_Limitations.md
│       ├── Performance_Baselines.md
│       └── ...                # Your domain knowledge
│
└── scripts/
    └── context_hub.py         # CLI for knowledge management
```

## Core Concepts

### 1. Lazy-Read Protocol

Agents don't read everything at startup. They read:
1. **Always**: `AI_CONTEXT.md` + `VERSION.json`
2. **By task**: Routing table in `CLAUDE.md` tells them what else to read

This saves 60-80% tokens on simple queries.

### 2. Skills = Executable Knowledge

Skills are markdown files with:
- **Frontmatter**: triggers, params, required reads
- **Steps**: Deterministic workflow (same input → same output)
- **Edge Cases**: Auto-accumulated from past failures

Skills turn "tribal knowledge" into repeatable processes.

### 3. Forced Memory Writes

Every task must end with a structured report:
1. What was done
2. How it was verified
3. What documentation was updated
4. What to do next

This is enforced by the `self-improving` skill.

### 4. Context Hub CLI

```bash
python scripts/context_hub.py search "bug"           # Search knowledge
python scripts/context_hub.py get Known_Limitations   # Read a topic
python scripts/context_hub.py annotate Topic "note"   # Add finding
python scripts/context_hub.py memory add "[BUG] ..."  # Log a decision
python scripts/context_hub.py memory show --last 5    # Recent history
python scripts/context_hub.py lesson "mistake" "fix"  # Record lesson
python scripts/context_hub.py status                  # Project overview
python scripts/context_hub.py bootstrap               # New session startup
```

## Design Principles

1. **Intelligence flows up** — Skills encode domain judgment; tools are deterministic
2. **Harness stays thin** — `CLAUDE.md` should be < 100 lines
3. **Read on demand** — Never bulk-read all files at session start
4. **Write on close** — Every session must leave a memory trace
5. **Skills accumulate** — Edge cases make skills smarter over time
6. **Forced > suggested** — Mandatory reports beat "best practices"

## Measured Results (from production use)

| Metric | Before | After |
|--------|:------:|:-----:|
| Mandatory startup tokens | ~999 lines | ~212 lines (-79%) |
| Repeated bug investigation | Common | Auto-loaded from edge cases |
| Cross-session knowledge loss | Severe | Near-zero (memory.md) |
| Experiment report consistency | Low (ad-hoc) | High (templated) |
| Token cost per simple query | ~3,000 | ~800 (-73%) |

## FAQ

**Q: Does this work with agents other than Claude?**
A: Yes. The framework is agent-agnostic. Rename `CLAUDE.md` to `AGENTS.md` or `CURSOR_RULES.md` and adjust wording. The memory system and skills work with any LLM-based coding agent.

**Q: How many skills should I start with?**
A: Start with 2-3 for tasks you do 3+ times per week. Don't over-engineer. Add more as you discover repeated patterns.

**Q: How do I prevent memory.md from growing forever?**
A: Periodically archive old entries. Keep the last 30-50 active. Move retired entries to `docs/knowledge/` as permanent knowledge.

**Q: Can I use this without the Python CLI?**
A: Yes. The CLI is a convenience tool. You can manually edit `memory.md` and knowledge files. The core value is in the file structure and protocols, not the tooling.

## Platform Support

- ✅ **Linux** — Fully supported
- ✅ **macOS** — Fully supported
- ⚠️ **Windows** — Not tested (file locking in `context_hub.py` uses `fcntl`, may need adjustment)

## License

MIT — Use it, modify it, share it.

## Credits

Built on ideas from:
- [andrewyng/context-hub](https://github.com/andrewyng/context-hub) — Andrew Ng
- [milla-jovovich/mempalace](https://github.com/milla-jovovich/mempalace) — MemPalace
- [Greptile blog: "Thin Harness, Fat Skills"](https://greptile.com/blog/agents) — Garry Tan / Daksh Gupta
