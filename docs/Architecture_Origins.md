# Agent Memory Architecture — Design Origins

> This document explains the architectural influences behind the Agent Memory
> Framework and how they integrate into the hybrid wiki router.

---

## Design Origins

### 1. Andrew Ng's Context Hub

**Source**: [github.com/andrewyng/context-hub](https://github.com/andrewyng/context-hub)

**Core concepts**:

- Versioned documents preserve context across sessions
- Knowledge files can be annotated as new findings arrive
- A dedicated context layer reduces re-explanation and hallucination

**What we adopted**:

- `context_hub.py` for search, get, annotate, memory, lesson, status, bootstrap
- Topic-indexed knowledge under `docs/knowledge/`
- Rolling memory in `.agents/memory.md`
- `VERSION.json` as a lightweight experiment-control file

---

### 2. MemPalace

**Source**: [github.com/MemPalace/mempalace](https://github.com/MemPalace/mempalace)

**Core concepts**:

- Anti-amnesia rules only work when they are enforced
- Task reports should be structured, not optional free text
- Cross-session continuity needs explicit logs

**What we adopted**:

- Mandatory 4-section wrap-up format
- Structured tags such as `[BUG]`, `[DECISION]`, `[EXPERIMENT]`, `[INSIGHT]`
- Self-improving rules that force memory writes and failure capture

---

### 3. Garry Tan's "Thin Harness, Fat Skills"

**Source**: [x.com/garrytan/status/2042925773300908103](https://x.com/garrytan/status/2042925773300908103)

**Core concepts**:

- Skills encode reusable workflows and domain judgment
- The harness should stay thin and mostly handle routing and safety
- Repeated edge cases belong in workflows, not in ad hoc prompts

**What we adopted**:

- `.agents/skills/` as the execution lane
- A routing-first `CLAUDE.md` / agent-rules file
- Skill templates with explicit inputs, verification, and outputs

---

### 4. Karpathy-style LLM Wiki

**Source**: Conceptual pattern — raw notes compiled into durable markdown wiki pages

**Core concepts**:

- Keep raw notes detailed, local, and immutable in spirit
- Keep retrieval pages concise and curated
- Use markdown as the durable knowledge format instead of defaulting to vector DB

**What we adopted**:

- `docs/raw/` as the fallback-only source layer
- `scripts/wiki_sync.py` as the deterministic raw-to-wiki compiler
- `docs/knowledge/index.md` and `docs/knowledge/log.md` as generated meta pages
- Topic frontmatter with `id`, `source_refs`, `last_updated`, `related_topics`

---

### 5. Operational Documentation Discipline

**Source**: Common practice in long-running software and research repositories

**Core concepts**:

- Keep the main project context obvious instead of scattering it across many docs
- Keep version and release metadata explicit
- Keep experiment conclusions shorter than the raw notebook trail

**What we adopted**:

- `AI_CONTEXT.md` as the main project context file
- `ROADMAP.md` + richer `VERSION.json` metadata
- `docs/knowledge/Experiment_Findings.md` as a compact conclusions ledger

---

## Integrated Architecture

### Hybrid Router

```text
                               CLAUDE.md
                             startup router
                                   |
             -------------------------------------------------
             |                       |                       |
             v                       v                       v
   operational lane             wiki lane              execution lane
AI_CONTEXT / ROADMAP /        docs/knowledge/          .agents/skills/
VERSION / memory             + index.md + log.md

Rolling memory remains append-only across all lanes.
docs/raw/ remains fallback-only and feeds the wiki via `wiki_sync.py`.
```

### Agent Session Flow

```text
Agent starts
    ↓
Read CLAUDE.md
    ↓
Router opens AI_CONTEXT.md + VERSION.json
    ↓
Choose lane: operational / wiki / execution
    ↓
If wiki topic exists: read docs/knowledge topic
    ↓
If wiki topic missing or stale: read docs/raw source + refresh with wiki_sync.py
    ↓
Execute task, verify, and write memory/report output
```

---

## How The Influences Complement Each Other

| Concern | Context Hub | MemPalace | Fat Skills | LLM Wiki | Operational docs |
|---------|-------------|-----------|------------|----------|----------------|
| Structure | ✅ | — | ✅ | ✅ | ✅ |
| Discipline | — | ✅ | — | — | ✅ |
| Execution | — | — | ✅ | — | — |
| Retention | ✅ | ✅ | ✅ | ✅ | ✅ |
| Routing | — | — | ✅ | ✅ | ✅ |

Combined effect:

- Context Hub gives the framework searchable files and CLI operations
- MemPalace forces continuity instead of hoping agents remember
- Fat Skills turn repeated work into reusable SOPs
- The LLM Wiki pattern keeps raw knowledge and retrieval pages separate
- Operational docs keep current priorities and release metadata easy to find

Together they form a public, markdown-first, vector-DB-free long-term memory
system that stays readable by both humans and agents.

---

## Lessons Learned

1. These patterns do not conflict. They solve different failure modes.
2. Raw notes should not be the default retrieval surface.
3. Recent memory and durable wiki serve different jobs and should both remain.
4. Operational docs deserve their own lane instead of being mixed into knowledge topics.
5. A deterministic compiler is the easiest way to keep markdown knowledge fresh without adding heavy infrastructure.
