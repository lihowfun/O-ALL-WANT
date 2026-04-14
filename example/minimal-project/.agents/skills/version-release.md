---
name: version-release
description: "Pre-release verification checklist — quality, docs, reproducibility, safety"
triggers: ["release", "bump version", "tag", "prepare release", "ship it"]
params:
  NEW_VERSION: "new version number (e.g., 1.2.0)"
  RELEASE_BRANCH: "branch to release from (e.g., main)"
requires:
  - VERSION.json
  - AI_CONTEXT.md
optional_reads:
  - docs/knowledge/Performance_Baselines.md
outputs:
  - VERSION.json (version field updated)
  - .agents/memory.md entry ([DECISION] Release vX.X.X)
  - git tag (vX.X.X)
---

# /version-release — Release Verification & Execution

## Parameters
- **NEW_VERSION**: ${NEW_VERSION}
- **RELEASE_BRANCH**: ${RELEASE_BRANCH}

## ⚠️ Important

**This skill is semi-automated**:
- ✅ Automatable: run tests, check syntax, grep for credentials
- ⚠️ Requires human judgment: baselines current?, docs complete?, performance acceptable?

---

## Steps

### Step 1: Pre-Flight Check

```bash
# 1. Confirm on correct branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH (expected: ${RELEASE_BRANCH})"

# 2. Confirm git is clean
git status --short
# Should be empty. If not, commit or stash first.

# 3. Check sync with main (optional)
git fetch origin main
git log --oneline HEAD..origin/main | head -5
```

### Step 2: Run Automated Tests

```bash
# Smoke tests (MUST pass)
${SMOKE_TEST_CMD}

# Regression tests (MUST pass)
${REGRESSION_TEST_CMD}

# Integration tests (if available)
# ${INTEGRATION_TEST_CMD}
```

If any test fails → **STOP release, fix first**.

### Step 3: Check Safety-Critical Code

```bash
# Verify safety checks are present (customize for your project)
# Example: grep for safety functions/flags that must exist
# grep -q "safety_check" src/core.py || echo "❌ CRITICAL: safety check missing!"
```

### Step 4: Check for Hardcoded Credentials

```bash
# Scan for common credential patterns
grep -rn "sk-\|AKIA\|password\s*=\s*['\"]" src/ scripts/ 2>/dev/null
# Should return nothing. If found → STOP, remove credentials.
```

### Step 5: Verify Documentation Consistency (Human Judgment)

- [ ] `VERSION.json` → `version` field matches `${NEW_VERSION}`
- [ ] `AI_CONTEXT.md` Current Baselines → numbers are from latest production model
- [ ] `ROADMAP.md` → completed phases marked ✅, active phases marked clearly
- [ ] `README.md` → quick-start example actually works

If inconsistent → fix before continuing.

### Step 6: Run Benchmark (Confirm No Regression)

```bash
${BENCHMARK_CMD}
```

Compare output with baselines in `AI_CONTEXT.md`:
- If primary metric regresses > 10% → **STOP release, investigate**
- If within ±5% → ✅ Continue

### Step 7: Bump VERSION.json

```bash
# Edit VERSION.json: set "version" to "${NEW_VERSION}"
# Verify JSON syntax
python3 -c "import json; json.load(open('VERSION.json'))" && echo "✅ Valid JSON"

git add VERSION.json
git commit -m "chore: bump version to v${NEW_VERSION}"
```

### Step 8: Create Git Tag

```bash
git tag -a v${NEW_VERSION} -m "Release v${NEW_VERSION}"
git push origin v${NEW_VERSION}
```

### Step 9: Record in Memory

```bash
python3 scripts/context_hub.py memory add "[DECISION] Released v${NEW_VERSION} — Branch: ${RELEASE_BRANCH}. Tests: pass. Baselines: verified. Tag: v${NEW_VERSION}"
```

---

## Edge Cases (Learning Block)

> Auto-appended when release issues are discovered.

<!-- Example:
- [2026-02-15] Forgot to update README quick-start after changing CLI defaults.
  Resolution: Added README check to Step 5 checklist.
-->
