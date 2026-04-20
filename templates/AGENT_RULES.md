# ${PROJECT_NAME} — Master Router

> Replace `${PROJECT_NAME}`, `${LANGUAGE}`, and the custom forbidden-action
> placeholders before first use. Keep the rest of the structure intact unless
> your workflow truly needs a different policy.

## Router Contract

- `CLAUDE.md` is the only startup router
- `AI_CONTEXT.md` stores project facts, not a second rulebook
- If the two overlap, use `CLAUDE.md` for behavior and `AI_CONTEXT.md` for
  project-specific facts and commands

## Response Language

- **${LANGUAGE}** is the primary response language
- Professional terms keep English (branch, commit, deployment, etc.)

## Session Startup (Read On Demand — NOT Everything)

**After opening this file, always read**:
1. ✅ `AI_CONTEXT.md` — architecture, baselines, commands, tech stack
2. ✅ `VERSION.json` → only check `version` + `do_not_rerun` fields
3. ✅ **If `docs/knowledge/CURRENT_STATE.md` exists**, read it too — it's the
      compiled entry point and replaces most of the per-lane first-read work.

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
│   ├── raw/               ← Immutable source notes (fallback-only)
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

## Merge Gate — Do Not Merge Untested Infrastructure

> Infrastructure code (install scripts, CI, build tooling, scripts the harness
> calls, anything that runs on every session) merges to `main` only if one of:

1. **End-to-end test passes in the worktree** (not just `import ok` or `py_compile`)
2. **Quantified improvement vs current `main` baseline** (measured, not asserted)
3. **Explicit user authorization for experimental scaffold** (clearly marked as such)

"Smoke test passed" proves no crash, not benefit. A passing `harness_check` or
`py_compile` is necessary, not sufficient. If none of the three conditions
hold, the change stays on a `study/*` branch until one of them does.

## Project-Specific Forbidden Actions

> The global prohibitions above already cover startup bulk-reads, `do_not_rerun`,
> and raw-vs-compiled wiki behavior. Keep this list for project-specific bans.

1. Do not remove safety checks without explicit approval
2. Do not hardcode credentials in source code (use env vars + `.env.example`)
3. ${CUSTOM_FORBIDDEN_ACTION_1}
4. ${CUSTOM_FORBIDDEN_ACTION_2}
