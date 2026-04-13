# ${PROJECT_NAME} — Agent Rules

## Response Language

- **${LANGUAGE}** is the primary response language
- Professional terms keep English (branch, commit, deployment, etc.)

## Session Startup (Read On Demand — NOT Everything)

**Always read (every session)**:
1. ✅ `AI_CONTEXT.md` — architecture, rules, baselines, tech stack
2. ✅ `VERSION.json` → only check `version` + `do_not_rerun` fields

**Read on demand (based on current task)**:

| Task Type | Also Read | Skip |
|-----------|-----------|------|
| Change code / run experiments | `ROADMAP.md` first 60 lines | knowledge/, docs/ |
| Check past decisions | `.agents/memory.md` last 5 entries | ROADMAP |
| Write docs / compare | `docs/knowledge/` relevant file | memory.md |
| Plan direction | `ROADMAP.md` + latest `docs/ACTION_PLAN_*.md` | knowledge/ |
| Debug / fix bugs | `docs/knowledge/Known_Limitations.md` | ROADMAP |

**Skills-First Principle**:
- If `.agents/skills/` has a matching skill (e.g., `/benchmark`, `/debug-pipeline`), **follow the skill workflow first**
- Skills still obey this file's lazy-read protocol
- Only go ad-hoc when no matching skill exists

> ⚠️ **FORBIDDEN**: Reading all .md files at session start. Understand the task first, then read on demand.
> ⚠️ **FORBIDDEN**: Re-running experiments listed in `VERSION.json` `do_not_rerun`.

## File Architecture — What Lives Where

```
📁 root/
├── CLAUDE.md              ← You are reading this (agent rules)
├── AI_CONTEXT.md          ← Architecture + baselines + rules (SSOT)
├── VERSION.json           ← Version number + do_not_rerun
├── ROADMAP.md             ← Phase plan + progress
├── README.md              ← User quick-start
│
├── .agents/
│   ├── memory.md          ← Decision/bug/finding log (newest first)
│   └── skills/            ← Executable workflows (read by task type)
│
├── docs/
│   ├── knowledge/         ← Topic-indexed knowledge (read on demand)
│   │   ├── Known_Limitations.md      Known issues & workarounds
│   │   ├── Performance_Baselines.md  Score benchmarks
│   │   └── ...
│   └── archive/           ← Stale docs, do not read
│
└── scripts/
    └── context_hub.py     ← CLI for knowledge management
```

## Session End — Mandatory Report (4 sections)

> **Source**: Follows `.agents/skills/self-improving.md` rules — prevents AI amnesia.

### 1. What Was Done
- Bullet list of modified files + behavior changes
- Include `[file.py:line]` references
- Distinguish **new** / **modified** / **deleted**

### 2. How It Was Verified
- Which tests were run + results
- If no tests: write **"Not verified"**

### 3. Were Docs Updated?
- [ ] `ROADMAP.md` → updated if phase status changed
- [ ] `README.md` → updated if CLI flags / defaults changed
- [ ] `VERSION.json` → bumped version / added do_not_rerun
- [ ] `.agents/memory.md` → added `[BUG]`/`[DECISION]`/`[FINDING]` entry

### 4. What Comes Next
- P0/P1/P2 action items + estimated cost + dependencies

## Forbidden Actions

<!-- Customize these for your project -->
1. Do not remove safety checks without explicit approval
2. Do not re-run experiments in the `do_not_rerun` list
3. Do not hardcode credentials in source code (use env vars + `.env.example`)
4. ${CUSTOM_FORBIDDEN_ACTION_1}
5. ${CUSTOM_FORBIDDEN_ACTION_2}
