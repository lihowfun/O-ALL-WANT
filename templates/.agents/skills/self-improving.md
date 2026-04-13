---
name: self-improving
description: "Mandatory rules for agent self-improvement — auto-report, failure logging, user correction capture"
triggers: ["always active — not triggered by keywords, enforced by protocol"]
params: {}
requires:
  - AI_CONTEXT.md
outputs:
  - memory.md entry (every session)
  - CLAUDE.md update (when forbidden actions change)
---

# Self-Improving Skill

> **Core principle**: Every agentic interaction must leave a traceable record.
> Success or failure, experience must accumulate — never evaporate.

## 🚨 Mandatory Rules

### Rule 1: Every task must end with a report

Before ending any non-trivial task, you **must**:

1. Produce a concise **Task Report** containing at minimum:
   - **What was done** (1-3 line summary)
   - **Result** (success/failure/partial + key metrics)
   - **Next steps** (if any)

2. Write important findings to `memory.md`:
   ```bash
   python scripts/context_hub.py memory add "[TAG] Finding/decision summary"
   ```

3. If the work was **experimental** (running evaluations, changing algorithms, etc.), additionally record:
   - Hypothesis
   - Method
   - Result + data
   - Lesson learned

### Rule 2: Failures must be auto-recorded

**Any failure** (errors, unexpected results, crashes) must be immediately written to memory.md:

```bash
python scripts/context_hub.py memory add "[BUG] Failure description — Root cause — Fix/workaround"
```

Templates:
```
[BUG] {symptom} — Root cause: {cause} — Fix: {solution}
[EXPERIMENT] {name} — Hypothesis: {H} — Result: ❌ {why it failed} — Lesson: {takeaway}
```

### Rule 3: User corrections → Immediate memory

When the user says "don't do that" or "always use X from now on", immediately:

1. **Record to agent built-in memory** (e.g., Claude Code `/memory`)
2. **Record to memory.md**:
   ```bash
   python scripts/context_hub.py memory add "[DECISION] User instruction: {specific instruction} — Reason: {if known}"
   ```
3. If it involves forbidden actions, update `CLAUDE.md` Forbidden Actions section

> **Note**: Both built-in memory AND memory.md must be updated.
> Built-in memory works within the same session; memory.md persists across sessions.

---

## 📋 Report Templates

### Quick Report (standard tasks)
```markdown
## Task Report: {task_name}
- **Date**: {YYYY-MM-DD}
- **What was done**: {1-3 line summary}
- **Result**: {success/failure + key data}
- **Next steps**: {recommendations}
```

### Experiment Report (experimental tasks)
```markdown
## Experiment Report: {experiment_name}
- **Date**: {YYYY-MM-DD}
- **Hypothesis**: {why this experiment was run}
- **Method**: {specific steps}
- **Result**: {✅/❌ + data table}
- **Lesson**: {the single most important takeaway}
- **Next steps**: {recommendations based on result}
```

---

## 🎯 Why This Matters

Without these rules:
- ❌ Agent forgets decisions across sessions
- ❌ Same bugs are investigated repeatedly
- ❌ Experiments are rerun unnecessarily
- ❌ Knowledge lives only in git history (unsearchable)

With these rules:
- ✅ Every decision has a memory entry
- ✅ Every failure becomes a permanent lesson
- ✅ User preferences are captured instantly
- ✅ Skills accumulate edge cases over time
