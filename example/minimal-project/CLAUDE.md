# Minimal Example App — Agent Rules

## Router Contract

- `CLAUDE.md` is the startup router
- `AI_CONTEXT.md` stores project facts, not a second rulebook
- If the two overlap, use `CLAUDE.md` for behavior and `AI_CONTEXT.md` for
  project-specific facts and commands

## Response Language

- **English** is the primary response language
- Professional terms keep English (branch, commit, deployment, etc.)

## Session Startup (Read On Demand — NOT Everything)

**After opening this file, always read**:
1. ✅ `AI_CONTEXT.md` — architecture, baselines, commands, tech stack
2. ✅ `VERSION.json` → only check `version` + `do_not_rerun` fields

**Route by lane (based on the current task)**:

| Lane | Use When | Read First | Fallback |
|------|----------|------------|----------|
| Operational | Current state, release status, branch scope, experiment execution | `ROADMAP.md` first 60 lines + `.agents/memory.md` last 5 entries | `docs/knowledge/Experiment_Findings.md` |
| Wiki | Stable concepts, background knowledge, reusable domain facts | `docs/knowledge/index.md` + relevant topic page(s) | `docs/raw/` relevant sources, then `python3 scripts/wiki_sync.py refresh <topic>` |
| Execution | Repeating workflows and SOPs | Matching file in `.agents/skills/` | Operational lane docs only if the skill asks for them |
| Debug | Reproducing failures and workarounds | `docs/knowledge/Known_Limitations.md` | `.agents/memory.md` last 5 entries |

**Skills-First Principle**:
- If `.agents/skills/` has a matching skill (e.g., `/benchmark`, `/debug-pipeline`, `/wiki-refresh`), **follow the skill workflow first**
- Skills still obey this file's lazy-read protocol
- Only go ad-hoc when no matching skill exists
- If a maintenance step can be done by `context_hub.py` or `wiki_sync.py`,
  prefer the script over repeated prose instructions

> ⚠️ **FORBIDDEN**: Reading all .md files at session start. Understand the task first, then read on demand.
> ⚠️ **FORBIDDEN**: Re-running experiments listed in `VERSION.json` `do_not_rerun`.
> ⚠️ **FORBIDDEN**: Treating `docs/raw/` as startup-default context. Raw notes are fallback-only.

## File Architecture — What Lives Where

```
📁 root/
├── CLAUDE.md              ← You are reading this (agent rules)
├── AI_CONTEXT.md          ← Project facts, baselines, commands
├── VERSION.json           ← Version number + do_not_rerun
├── ROADMAP.md             ← Phase plan + progress
├── README.md              ← User quick-start
│
├── .agents/
│   ├── memory.md          ← Decision/bug/finding log (newest first)
│   └── skills/            ← Executable workflows (read by task type)
│
├── docs/
│   ├── raw/               ← Source notes (fallback-only)
│   ├── knowledge/         ← Compiled durable wiki (read on demand)
│   │   ├── index.md                 Knowledge map (meta)
│   │   ├── log.md                   Sync ledger (meta)
│   │   ├── Known_Limitations.md     Known issues & workarounds
│   │   ├── Performance_Baselines.md Score benchmarks
│   │   └── ...
│   └── archive/           ← Stale docs, do not read
│
└── scripts/
    ├── context_hub.py     ← CLI for knowledge management
    └── wiki_sync.py       ← Deterministic raw→wiki compiler
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

1. Do not remove safety checks without explicit approval
2. Do not re-run experiments in the `do_not_rerun` list
3. Do not hardcode credentials in source code (use env vars + `.env.example`)
4. Do not rewrite the example baseline timings without rerunning the fixture
5. Do not delete the release checklist link from the example README
