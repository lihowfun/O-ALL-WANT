# Design Principles — Thin Harness, Fat Skills

> How to structure AI agent context for maximum efficiency and minimum token waste.
> Based on production experience + three architectural influences.

---

## Core Architecture

```
┌─────────────────────────────────────────────┐
│  Fat Skills      (90% of the value)         │
│  Markdown workflows encoding judgment +     │
│  domain knowledge                           │
├─────────────────────────────────────────────┤
│  Thin Harness    (~100 lines)               │
│  Agent rules / context routing / safety     │
├─────────────────────────────────────────────┤
│  Deterministic   (tools & scripts)          │
│  CLI, tests, benchmarks, data pipelines     │
└─────────────────────────────────────────────┘

Principle: Push intelligence UP (skills), push execution DOWN (deterministic tools),
keep the harness THIN.
```

## Five Key Concepts

| # | Concept | One Sentence |
|---|---------|-------------|
| 1 | **Skill Files** | Reusable markdown workflows — like function calls with parameters |
| 2 | **Harness** | The wrapper around the LLM — only does: loop / read-write / context / safety |
| 3 | **Resolvers** | Context routing tables — task type X auto-loads documents Y |
| 4 | **Latent vs Deterministic** | LLM judgment needed vs same-input-same-output. Don't mix them. |
| 5 | **Learning Loop** | Skills accumulate edge cases → get smarter over time |

---

## Anti-Patterns to Avoid

### ❌ Bulk-reading at startup
**Problem**: Agent reads 1,000+ lines of docs before understanding what the user wants.
**Fix**: Lazy-read protocol — read `AI_CONTEXT.md` only, then route by task type.

### ❌ Ad-hoc workflows
**Problem**: Agent invents a new process every time for recurring tasks.
**Fix**: Skill files — write the workflow once, reuse forever.

### ❌ Knowledge in git history only
**Problem**: Important decisions live in commit messages, unreachable by agents.
**Fix**: Rolling memory (`memory.md`) + annotatable knowledge files.

### ❌ "Best practice" suggestions
**Problem**: Voluntary reporting means agents skip it when under token pressure.
**Fix**: Mandatory rules — enforced in agent rules file, embedded in every skill.

### ❌ Monolithic context file
**Problem**: One 500-line file covers everything, most of it irrelevant to the current task.
**Fix**: Separate into SSOT (`AI_CONTEXT.md`) + topic-indexed knowledge + skills.

---

## Skill Design Guidelines

### When to create a skill
- You've done the same task **3+ times**
- Each time you re-explain the workflow to the agent
- There are **known edge cases** the agent keeps forgetting

### When NOT to create a skill
- One-off task (just do it ad-hoc)
- The workflow is still evolving rapidly (wait until it stabilizes)
- It's purely deterministic (make it a script instead)

### Skill anatomy

```yaml
---
name: skill-name
triggers: ["keyword1", "keyword2"]  # How the resolver finds this skill
params: { PARAM1: "desc", PARAM2: "desc" }
requires: [AI_CONTEXT.md, VERSION.json]  # Must-read before execution
outputs: [memory.md entry, knowledge annotation]  # What gets produced
---
```

```markdown
# Steps
1. Pre-checks (deterministic)
2. Execute core action (may involve LLM judgment — mark clearly)
3. Verify results (deterministic)
4. Record results (deterministic — write to memory/knowledge)

# Edge Cases (Learning Block)
- [date] What happened + resolution
```

### The learning loop

```
Session N:   Agent uses /benchmark → anomalous result → records edge case
Session N+1: Agent uses /benchmark → Step 1 reads edge cases → avoids the trap
Session N+5: 5+ edge cases → agent proposes skill rewrite
```

---

## ROI Estimates

| Benefit | Mechanism | Savings |
|---------|-----------|---------|
| Skip irrelevant reads | Lazy-read routing | ~60-80% startup tokens |
| Reuse workflows | Skills | ~2,500 tokens/skill use |
| Avoid re-investigation | Edge cases in skills | ~1,800 tokens/debug session |
| Consistent reports | Forced templates | ~1,200 tokens/report |
| Prevent re-runs | `do_not_rerun` in VERSION.json | Hours of compute |

**Total estimated savings**: ~5,000-8,000 tokens per session for high-frequency tasks.

---

## Implementation Roadmap

### Phase 1: Foundation (1 hour)
- Copy templates into your project
- Fill in `AI_CONTEXT.md` and agent rules
- Create 1-2 knowledge files

### Phase 2: First Skills (2-3 hours)
- Identify your top 3 recurring tasks
- Write skills using `_TEMPLATE.md`
- Test with your AI agent

### Phase 3: Optimization (ongoing)
- Accumulate edge cases in skills
- Periodically archive old memory entries
- Add knowledge frontmatter for auto-resolution (future)
- Automate the learning loop (future)
