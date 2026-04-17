# Design Principles — Thin Harness, Hybrid Router

> How to structure AI agent context for maximum efficiency and minimum token
> waste while keeping durable knowledge easy to update.

---

## Naming Evolution (for anyone reading older discussions)

OAW's vocabulary has shifted once already — keep this in mind when reading
archived design notes:

| Earlier name | Current name | Why the shift |
|--------------|--------------|---------------|
| **Fat Skills / Thin Harness** (Garry Tan, inspiration) | **Hybrid Router** (current) | "Fat Skills" captures only the execution lane. OAW's real contribution is the **4-lane routing** (Operational / Wiki / Execution / Debug). |
| **Three-layer memory** (early `agent-memory-framework` era) | **Hybrid Router + Compiled Wiki** | Three layers described storage; the current phrasing describes *read-time decisions*, which is what actually saves tokens. |
| **Agent Memory Framework** (repo name through v0.2) | **O-ALL-WANT (OAW)** | The framework grew opinionated enough to deserve its own brand; the memory layer is one ingredient, not the product. |

If a doc still uses an older term, that is historical context, not a new concept.

---

## Core Architecture

```text
┌─────────────────────────────────────────────┐
│ Fat Skills                                  │
│ Reusable workflows with verification        │
├─────────────────────────────────────────────┤
│ Thin Harness                                │
│ Agent rules, lane routing, safety           │
├─────────────────────────────────────────────┤
│ Deterministic Tools                         │
│ context_hub.py, wiki_sync.py, tests, CLI    │
└─────────────────────────────────────────────┘

Principle: push judgment up into skills, push repeatable maintenance down into
scripts, keep the harness thin.
```

## Six Key Concepts

| # | Concept | One Sentence |
|---|---------|--------------|
| 1 | Skill Files | Reusable markdown workflows for repeated tasks |
| 2 | Harness | A small router that decides what to read next |
| 3 | Lanes | Operational, wiki, and execution context should not be mixed blindly |
| 4 | Wiki Compilation | Raw notes stay detailed; compiled topic pages stay readable |
| 5 | Latent vs Deterministic | If the step should be identical every time, script it |
| 6 | Learning Loop | Skills and memory should capture edge cases as they appear |

---

## Anti-Patterns To Avoid

### Bulk-reading at startup

Problem: the agent reads hundreds of irrelevant lines before it even knows the task.

Fix: always start with `CLAUDE.md`, then let it route into `AI_CONTEXT.md`,
`VERSION.json`, and the right lane.

### Ad-hoc repeated workflows

Problem: the agent reinvents the same benchmark, release, or refresh process.

Fix: encode high-frequency tasks as skills.

### Raw-note retrieval by default

Problem: detailed notebooks are great for authorship but terrible for everyday retrieval.

Fix: use compiled wiki pages for retrieval and `docs/raw/` only as fallback.

### Knowledge hidden in git history only

Problem: important conclusions are technically preserved but practically invisible.

Fix: keep rolling memory and durable knowledge pages in repo-visible markdown.

### Monolithic context

Problem: one giant context file makes every task pay the same token cost.

Fix: split the system into operational docs, compiled wiki, and execution skills.

---

## Lane Design

### Operational Lane

Use:

- `AI_CONTEXT.md`
- `ROADMAP.md`
- `VERSION.json`
- recent `.agents/memory.md`

Best for:

- branch status
- release decisions
- active experiment constraints
- current priorities

### Wiki Lane

Use:

- `docs/knowledge/index.md`
- relevant topic pages
- `Experiment_Findings.md`

Best for:

- durable background knowledge
- reusable architecture explanations
- condensed prior findings

### Execution Lane

Use:

- `.agents/skills/*.md`

Best for:

- benchmarks
- release checklists
- wiki refreshes
- repeated debugging flows

### Raw Source Fallback

Use:

- `docs/raw/*.md`

Only when:

- a topic is missing
- a topic looks stale
- you are authoring or refreshing the compiled wiki

---

## The Wiki Loop

```text
New source note lands in docs/raw/
    ↓
python3 scripts/wiki_sync.py refresh Topic_Name
    ↓
docs/knowledge/Topic_Name.md stays concise and searchable
    ↓
index.md + log.md update deterministically
    ↓
future agents read the compiled topic instead of the raw note
```

## The Learning Loop

```text
Task runs
    ↓
Decision / failure / experiment result gets written to memory
    ↓
Reusable conclusions get promoted into docs/knowledge/
    ↓
If maintenance becomes repetitive, move the flow into a skill
```

---

## ROI

| Benefit | Mechanism | Savings |
|---------|-----------|---------|
| Fewer irrelevant reads | lane routing | ~60-80% startup tokens |
| Reuse workflows | skills | ~2,500 tokens per repeated task |
| Stable knowledge maintenance | raw→wiki compilation | lower doc drift |
| Consistent reports | forced report structure | fewer lost conclusions |
| Fewer accidental reruns | `do_not_rerun` in `VERSION.json` | hours of compute |

---

## Rollout Order

### Phase 1: Foundation

- Install the framework
- Fill in `AI_CONTEXT.md` and `CLAUDE.md`
- Start writing memory entries

### Phase 2: Skills

- Identify 2-3 repeated tasks
- Turn them into skills
- Verify each skill produces memory output

### Phase 3: Wiki

- Add raw source notes under `docs/raw/`
- Compile durable topics with `wiki_sync.py`
- Keep `index.md` and `log.md` passing lint

### Phase 4: Optimization

- Archive stale memory
- tighten related-topic links
- refine branch and experiment ledgers
