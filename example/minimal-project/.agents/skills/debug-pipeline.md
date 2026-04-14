---
name: debug-pipeline
description: "Systematic pipeline debug — layered diagnosis from data → model → output → validation"
triggers: ["debug", "error", "bug", "not working", "wrong output", "crash", "OOM", "0 results"]
params:
  ERROR_MSG: "error message or anomalous behavior description"
  FAILING_STEP: "which pipeline step is failing (optional, if known)"
requires:
  - AI_CONTEXT.md (Architecture section)
  - docs/knowledge/Known_Limitations.md
optional_reads:
  - docs/knowledge/ (relevant topic based on error type)
outputs:
  - .agents/memory.md entry ([BUG] or [WORKAROUND])
  - docs/knowledge/Known_Limitations.md annotation (if new limitation)
---

# /debug-pipeline — Systematic Pipeline Debug

## Parameters
- **ERROR_MSG**: ${ERROR_MSG}
- **FAILING_STEP**: ${FAILING_STEP}

## Pipeline Architecture (Layered Diagnosis)

```
Layer A: Data / Input       → Is the input data correct and present?
Layer B: Model / Processing → Is the core logic producing expected output?
Layer C: Post-processing    → Are filters/transforms losing valid results?
Layer D: Validation / Output→ Is the final check rejecting valid results?
```

---

## Steps

### Step 1: Triage (Quick Classification)

Classify `ERROR_MSG`:

| Error Type | Keywords | Jump to |
|-----------|---------|---------|
| Out of memory | "OOM", "CUDA", "killed", "memory" | Step 2.1 |
| Empty results | "0 results", "no output", "empty" | Step 2.2 |
| Wrong results | "wrong", "unexpected", "should be" | Step 2.3 |
| Import / env error | "ModuleNotFoundError", "cannot import" | Step 2.4 |
| Data issues | "not found", "missing", "corrupt" | Step 2.5 |
| External service | "timeout", "API error", "connection" | Step 2.6 |

### Step 2: Layered Diagnosis

#### 2.1 Out of Memory

**Check Known_Limitations.md for previous OOM solutions.**

Standard checklist:
1. Reduce batch size
2. Enable gradient checkpointing (if available)
3. Clear GPU/memory cache before heavy operations
4. Check for memory leaks (objects not freed in loops)
5. Try CPU fallback for non-training operations

If new OOM → record in Known_Limitations.md with GPU model, batch size, operation.

#### 2.2 Empty Results

Diagnosis flow (check in order):
1. **Input exists?** → Verify input files/data are present and non-empty
2. **Input format correct?** → Check schema, encoding, delimiter
3. **Intermediate steps produce output?** → Add logging/print at each pipeline stage
4. **Filter too aggressive?** → Check thresholds, conditions that might exclude everything
5. **Silent failure?** → Check for caught exceptions that swallow errors

#### 2.3 Wrong Results

Diagnosis flow:
1. **Reproducible?** → Run again with same input. If different → randomness issue (seed not set)
2. **Input correct?** → Verify the right data/config was used (not a stale version)
3. **Model correct?** → Confirm the right checkpoint/weights are loaded
4. **Post-processing?** → Check sorting, ranking, filtering logic
5. **Evaluation method?** → Confirm the metric calculation matches expectations

#### 2.4 Import / Environment Error

Standard checklist:
```bash
# 1. Confirm environment is active
command -v python3  # Should point to your venv/conda

# 2. Confirm in project root
pwd

# 3. Check required packages
python3 -c "import ${KEY_PACKAGE_1}; import ${KEY_PACKAGE_2}"

# 4. Reinstall if needed
pip install -r requirements.txt
```

#### 2.5 Data Issues

Diagnosis flow:
1. **File exists?** → `ls -la ${FILE_PATH}`
2. **File non-empty?** → `wc -l ${FILE_PATH}`
3. **Format correct?** → `head -5 ${FILE_PATH}`
4. **Encoding?** → `file ${FILE_PATH}` (should be UTF-8)
5. **IDs match?** → Cross-reference IDs between data files

#### 2.6 External Service Errors

Diagnosis flow:
1. **Service reachable?** → `curl -s ${SERVICE_URL}/health`
2. **Credentials valid?** → Check env vars are set: `test -n "$API_KEY" && echo "API_KEY is set" || echo "API_KEY is missing"`
3. **Rate limited?** → Check response headers for rate limit info
4. **Timeout?** → Increase timeout, retry with exponential backoff

---

## Step 3: Record Results

### If solution found

```bash
python3 scripts/context_hub.py memory add "[WORKAROUND] ${ERROR_MSG} — Cause: ${ROOT_CAUSE}. Fix: ${SOLUTION}"
```

### If new limitation discovered

```bash
python3 scripts/context_hub.py annotate Known_Limitations "[BUG] ${ERROR_MSG} — No fix yet, needs investigation. Symptoms: ${SYMPTOMS}"
```

### If known issue re-encountered

```bash
python3 scripts/context_hub.py memory add "[BUG] Re-encountered Known Limitation: ${BRIEF_DESC}. Suggest prioritizing fix (hit ${N} times now)"
```

---

## Edge Cases (Learning Block)

> Auto-appended when new debug patterns are discovered.

<!-- Example:
- [2026-01-20] "0 results" was caused by a silent exception in data loading.
  Resolution: Added explicit error logging at every pipeline boundary.
-->
