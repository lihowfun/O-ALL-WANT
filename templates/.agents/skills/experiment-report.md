---
name: experiment-report
description: "Structured experiment report: write to memory + optional knowledge annotation"
triggers: ["experiment conclusion", "archive results", "log experiment", "write report"]
params:
  EXPERIMENT_NAME: "short name (e.g., ablation_dropout_0.3)"
  HYPOTHESIS: "what we expected"
  METHOD: "what we changed"
  RESULTS: "key metrics with Δ%"
  CONCLUSION: "accepted/rejected hypothesis + next steps"
requires:
  - .agents/memory.md (check recent entries to avoid duplication)
optional_reads:
  - docs/knowledge/Performance_Baselines.md
outputs:
  - .agents/memory.md entry ([EXPERIMENT] tag)
  - knowledge annotation (if significant finding)
  - docs/knowledge/EXPERIMENT_LOG.md row (always, via wiki_sync add-experiment)
  - docs/knowledge/CURRENT_STATE.md annotation (if phase status moved)
---

# /experiment-report — Structured Experiment Report

## Parameters
- **EXPERIMENT_NAME**: ${EXPERIMENT_NAME}
- **HYPOTHESIS**: ${HYPOTHESIS}
- **METHOD**: ${METHOD}
- **RESULTS**: ${RESULTS}
- **CONCLUSION**: ${CONCLUSION}

## Steps

### Step 1: Check for Duplicates

```bash
# Confirm this experiment isn't already recorded
head -100 .agents/memory.md | grep "${EXPERIMENT_NAME}"
```

If already recorded → **STOP**, inform user.

### Step 2: Choose Memory Entry Tag

| Experiment Type | Tag |
|----------------|-----|
| Benchmark comparison, ablation study | `[EXPERIMENT]` |
| Bug tracking, workaround | `[BUG]` |
| Methodology decision (chose A over B) | `[DECISION]` |
| Unexpected discovery, pattern observation | `[INSIGHT]` |
| Architecture change | `[ARCHITECTURE]` |

### Step 3: Write to Memory (Structured Format)

```bash
python3 scripts/context_hub.py memory add "[TAG] ${EXPERIMENT_NAME} — ${one_line_summary}

Hypothesis: ${HYPOTHESIS}
Method: ${METHOD}
Results: ${RESULTS}
Conclusion: ${CONCLUSION}"
```

### Step 4: Decide Whether to Annotate Knowledge

**Annotate if any of these apply**:
- Discovered a new limitation or edge case
- Found a new performance pattern (something unexpectedly good/bad)
- Overturned a previous assumption
- Confirmed an important conclusion

**Action**:

```bash
# Performance-related
python3 scripts/context_hub.py annotate Performance_Baselines "[EXPERIMENT] ${summary}"

# Limitation / edge case
python3 scripts/context_hub.py annotate Known_Limitations "[INSIGHT] ${summary}"
```

### Step 5: Auto-Update Wiki (AI responsibility, do not skip)

> The user will not remind you. Any tool that depends on user memory goes stale.
> Run these non-interactive commands yourself before finishing the session.

**5a. Always: append to EXPERIMENT_LOG**

```bash
python3 scripts/wiki_sync.py add-experiment \
  --name "${EXPERIMENT_NAME}" \
  --status "${accepted|rejected|running|blocked|inconclusive}" \
  --result "${RESULTS}" \
  --conclusion "${CONCLUSION}"
```

**5b. If phase status moved: update CURRENT_STATE**

```bash
python3 scripts/wiki_sync.py update-state \
  --phase "${phase_id}" \
  --status "${✅ done|🔄 in progress|⏳ queued}" \
  --note "${EXPERIMENT_NAME}: ${one-line impact}"
```

**5c. Final lint**

```bash
python3 scripts/wiki_sync.py lint
```

### Step 6: Check if ROADMAP Needs Updating

**Update ROADMAP if any of these apply**:
- Experiment conclusion changes phase priority
- Discovered a blocker (must solve X before Y)
- Completed a milestone (phase can be closed)

**Action**: Flag for user review. Don't auto-modify ROADMAP.

---

## Edge Cases (Learning Block)

> Auto-appended when anomalies occur during report writing.

<!-- Example:
- [2026-02-01] Forgot to check do_not_rerun before starting experiment.
  Resolution: Added VERSION.json check to Step 1.
-->
