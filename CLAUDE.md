# OAW — Master Router

> This repo uses its own harness to manage itself. Meta, but effective.

## Router Contract

- `CLAUDE.md` is the only startup router
- `AI_CONTEXT.md` stores project facts, not a second rulebook
- If the two overlap, use `CLAUDE.md` for behavior and `AI_CONTEXT.md` for
  project-specific facts and commands

## Response Language

- **繁體中文** is the primary response language
- Professional terms keep English (branch, commit, deployment, harness, router, skill, etc.)

## Session Startup (Read On Demand — NOT Everything)

**After opening this file, always read**:
1. ✅ `AI_CONTEXT.md` — architecture, baselines, commands, tech stack
2. ✅ `VERSION.json` → only check `version` + `do_not_rerun` fields

**Route by lane (based on the current task)**:

| Lane | Use When | Read First | Fallback |
|------|----------|------------|----------|
| Operational | Current state, release status, branch scope, experiment execution | `ROADMAP.md` first 60 lines + `.agents/memory.md` last 5 entries | `templates/docs/knowledge/Experiment_Findings.md` |
| Wiki | Stable concepts, background knowledge, reusable domain facts | `templates/docs/knowledge/index.md` + relevant topic page(s) | `templates/docs/raw/` relevant sources |
| Execution | Repeating workflows and SOPs | Matching file in `templates/.agents/skills/` | Operational lane docs only if the skill asks for them |
| Debug | Reproducing failures and workarounds | `templates/docs/knowledge/Known_Limitations.md` | `.agents/memory.md` last 5 entries |

**Skills-First Principle**:
- If `templates/.agents/skills/` has a matching skill (e.g., `/benchmark`, `/debug-pipeline`, `/wiki-refresh`), **follow the skill workflow first**
- Skills still obey this file's lazy-read protocol
- Only go ad-hoc when no matching skill exists
- If a maintenance step can be done by `context_hub.py` or `wiki_sync.py`,
  prefer the script over repeated prose instructions

> ⚠️ **FORBIDDEN**: Reading all .md files at session start. Understand the task first, then read on demand.
> ⚠️ **FORBIDDEN**: Re-running experiments listed in `VERSION.json` `do_not_rerun`.
> ⚠️ **FORBIDDEN**: Treating `docs/raw/` as startup-default context. Raw notes are fallback-only.

## File Architecture — What Lives Where

> This repo uses its own harness for self-hosting. Skills, knowledge, and raw
> notes live in `templates/` and are installed into user projects via
> `install.sh`. The root-level `CLAUDE.md`, `AI_CONTEXT.md`, etc. are the
> **customized** versions for developing this framework itself.

```
📁 root/
├── CLAUDE.md              ← You are reading this (agent rules for OAW dev)
├── AI_CONTEXT.md          ← OAW project facts, baselines, commands
├── VERSION.json           ← Version number + do_not_rerun
├── ROADMAP.md             ← Phase plan + progress
├── README.md              ← User quick-start (public-facing)
│
├── .agents/
│   └── memory.md          ← Decision/bug/finding log (git-ignored)
│
├── templates/             ← Installable templates for users
│   ├── AGENT_RULES.md     ← Becomes CLAUDE.md after install
│   ├── AI_CONTEXT.md      ← Placeholder for user projects
│   ├── .agents/skills/    ← Reusable workflows (also used by this repo)
│   ├── docs/knowledge/    ← Wiki templates
│   └── docs/raw/          ← Raw note templates
│
├── docs/
│   ├── Architecture_Origins.md, Design_Principles.md, etc.
│   └── archive/           ← Audit trails and reports
│
├── scripts/
│   ├── context_hub.py     ← CLI for knowledge management
│   └── wiki_sync.py       ← Deterministic raw→wiki compiler
│
└── example/
    ├── minimal-project/   ← Post-install snapshot
    └── public-hybrid-demo/← Full example with raw + wiki + skills
```

**For OAW development**: Skills are at `templates/.agents/skills/`.
Knowledge pages are at `templates/docs/knowledge/`.
These are the canonical copies — do not duplicate them at root.

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

## Project-Specific Forbidden Actions

> The global prohibitions above already cover startup bulk-reads, `do_not_rerun`,
> and raw-vs-compiled wiki behavior. Keep this list for project-specific bans.

1. Do not remove safety checks without explicit approval
2. Do not hardcode credentials in source code (use env vars + `.env.example`)
3. Do not modify `templates/` without updating `example/minimal-project/` accordingly
4. Do not add PRIVATE_PROJECT or other sensitive project references to this public repo
