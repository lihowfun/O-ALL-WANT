# Skills Index

> Skills are reusable markdown workflows — like function calls that accept parameters.
> Reference: Garry Tan "Thin Harness, Fat Skills" architecture
>
> Placeholder convention:
> - `${PARAM}` = a value defined in the skill's `params` block
> - `${RUNTIME_VALUE}` = a value the agent fills in while executing the skill
> - Setup-time placeholders are documented in `docs/Skill_Guide.md`

---

## 📚 Skills List

| Skill | Purpose | Status |
|-------|---------|--------|
| `self-improving.md` | Anti-amnesia rules: forced reports, failure logging, user correction capture | ✅ Core (never remove) |
| `benchmark.md` | Run benchmarks + auto-generate structured report + compare baselines | ✅ Example |
| `experiment-report.md` | Structured experiment report → memory + knowledge annotation | ✅ Example |
| `debug-pipeline.md` | Systematic pipeline debug checklist (layered diagnosis) | ✅ Example |
| `wiki-refresh.md` | Refresh a compiled wiki topic from `docs/raw/` and run lint | ✅ Example |
| `version-release.md` | Pre-release verification checklist + execution | ✅ Example |

---

## 🛠️ Skill Format Spec

Every skill must contain:

### 1. Frontmatter (YAML)

```yaml
---
name: skill-name
description: "One sentence: what does this skill do"
triggers: ["keyword1", "keyword2", "..."]
params:
  PARAM1: "description | allowed values"
  PARAM2: "description"
requires:
  - AI_CONTEXT.md
  - VERSION.json
optional_reads:
  - docs/knowledge/relevant_topic.md
  - docs/raw/relevant_source.md
outputs:
  - memory.md entry
  - knowledge annotation
---
```

### 2. Skill Body

```markdown
# /skill-name — Short Title

## Parameters
- **PARAM1**: ${PARAM1}
- **PARAM2**: ${PARAM2}

## Steps

### Step 1: Pre-checks
- [ ] Checklist item 1
- [ ] Checklist item 2

### Step 2: Execute core action
Concrete instructions or commands

### Step 3: Verify results
How to confirm success

### Step 4: Record results
Write to memory.md or knowledge

## Edge Cases (Learning Block)

> Auto-appended when anomalies occur during execution.

- [YYYY-MM-DD] Description of edge case and resolution
```

---

## 📖 Usage

### For AI Agents

When receiving a task:
1. Scan the task description, match skill `triggers`
2. If matched, **follow the skill workflow first** (per `CLAUDE.md` Skills-First Principle)
3. Read the skill's `requires` files
4. Read any `docs/raw/` note only if the skill explicitly needs source material
5. Execute steps in order
6. Record results per the skill's `outputs` spec

### For Humans

Skills are **executable Standard Operating Procedures (SOPs)**:
- Need to run a benchmark? Read `benchmark.md` → follow steps
- Need to debug? Read `debug-pipeline.md` → systematic diagnosis
- Preparing a release? Read `version-release.md` → checklist guarantees nothing is missed

---

## 🔄 Learning Loop (Future)

1. Skill execution records results
2. If results are anomalous (Δ > threshold), auto-append to skill's Edge Cases block
3. Next execution of the same skill checks edge cases first
4. When edge cases accumulate → propose skill rewrite

---

## 🔄 Self-Improving Principles (ALL Skills Must Follow)

**All skills must obey `.agents/skills/self-improving.md` mandatory rules**:

1. **Every execution must record to `memory.md`**
   - Format: `python3 scripts/context_hub.py memory add "[TAG] content"`
   - TAG choices: `[EXPERIMENT]`, `[BUG]`, `[DECISION]`, `[WORKAROUND]`, `[INSIGHT]`

2. **Failures must be auto-recorded**
   - Any error, unexpected result, anomaly → log immediately
   - Format: `[BUG] symptom — Root cause: X — Fix: Y`

3. **User corrections must be captured immediately**
   - Update `memory.md`: `[DECISION] User instruction: X`
   - If it involves forbidden actions, update `CLAUDE.md`

4. **Edge Cases accumulate**
   - Every skill has an "Edge Cases (Learning Block)" section
   - Append anomalies when encountered; check before next execution

**Purpose**: Prevent AI amnesia. Every experience becomes a permanent system upgrade.

---

## ⚠️ Skill Design Principles

1. **Only skill-ify high-frequency tasks** (3+ times) — avoid over-engineering
2. **Steps should be deterministic** (same input → same output) — clearly label steps requiring LLM judgment
3. **Frontmatter must be accurate** (triggers, requires) — this is how the resolver auto-matches
4. **Outputs must be structured** (memory entry format, knowledge annotation) — maintain consistency
5. **Obey lazy-read protocol** (don't bulk-read unnecessary files inside skills) — token efficiency
6. **Use `docs/raw/` sparingly** — only when a wiki topic is missing or needs refresh
