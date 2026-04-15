---
name: benchmark
description: "Run benchmark, auto-generate structured report, compare against baselines"
triggers: ["benchmark", "evaluate", "test scores", "run eval", "compare metrics"]
params:
  MODEL_PATH: "path to model checkpoint or config"
  EVAL_COMMAND: "the benchmark command to run"
  BASELINE_SOURCE: "where current baselines are documented (default: AI_CONTEXT.md)"
requires:
  - AI_CONTEXT.md (Current Baselines section)
  - VERSION.json (do_not_rerun check)
optional_reads:
  - docs/knowledge/Performance_Baselines.md
outputs:
  - .agents/memory.md entry
  - docs/knowledge/Performance_Baselines.md annotation (if Δ > 5%)
  - AI_CONTEXT.md baseline update (if new best)
---

# /benchmark — Run Benchmark + Auto Report

## Parameters
- **MODEL_PATH**: ${MODEL_PATH}
- **EVAL_COMMAND**: ${EVAL_COMMAND}
- **BASELINE_SOURCE**: ${BASELINE_SOURCE}

## Steps

### Step 1: Pre-checks

- [ ] Confirm `MODEL_PATH` exists and contains required files
- [ ] Confirm environment is activated (conda, venv, etc.)
- [ ] Read `VERSION.json` → confirm this experiment is **not** in `do_not_rerun`
- [ ] Read `AI_CONTEXT.md` Current Baselines → note current baseline numbers

### Step 2: Execute Benchmark

```bash
${EVAL_COMMAND}
```

Capture stdout/stderr. Expected output: key metrics (accuracy, AUPRC, F1, loss, etc.)

### Step 3: Extract Results (Deterministic)

From stdout, extract key metrics:
- Primary metric: ${PRIMARY_METRIC}
- Secondary metrics: ${SECONDARY_METRICS}

Record the exact numbers.

### Step 4: Compare Against Baselines (Deterministic)

Calculate delta:
```
Δ% = (new_value - baseline_value) / baseline_value * 100
```

Classification:
- **Δ > +5%** → 🟢 Significant improvement
- **Δ > +10%** → 🔥 Major breakthrough, update AI_CONTEXT.md baselines
- **-5% ≤ Δ ≤ +5%** → 🟡 Within noise range
- **Δ < -5%** → 🔴 Regression, investigate
- **Δ < -10%** → ⚠️ Severe regression, record [BUG]

### Step 5: Write to Memory (Structured)

```bash
python3 scripts/context_hub.py memory add "[EXPERIMENT] Benchmark ${MODEL_PATH} — ${PRIMARY_METRIC}=${VALUE} (Δ=${DELTA}% vs baseline)"
```

### Step 6: Update Knowledge (if Δ > 5%)

```bash
python3 scripts/context_hub.py annotate Performance_Baselines "[EXPERIMENT] New numbers: ${METRIC}=${VALUE}. Model: ${MODEL_PATH}. Δ vs baseline: ${DELTA}%"
```

### Step 7: Update AI_CONTEXT.md Baselines (if new best)

**Conditions** (all must be met):
- Δ > +10% (major improvement)
- Experiment is production-ready (not a debug run)
- Results are stable (multi-run verified, or standard seed)

**Action**:
- Update `AI_CONTEXT.md` Current Baselines section
- Record: `[DECISION] Updated baseline: ${METRIC} → ${NEW_VALUE}`

### Step 8: Learning Loop (if results are anomalous)

If Δ < -10% (severe regression):
1. Annotate `Known_Limitations.md` with the regression details
2. Append to this skill's Edge Cases block below

---

## Edge Cases (Learning Block)

> Auto-appended when benchmark results are anomalous.

<!-- Example:
- [2026-01-20] Single-seed results can be misleading for metric X.
  Resolution: Always run ≥3 seeds before drawing conclusions.
-->
