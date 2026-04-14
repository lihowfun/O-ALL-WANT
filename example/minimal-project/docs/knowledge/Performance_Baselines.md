# Performance Baselines

> Track key performance metrics. Agents read this when comparing benchmark results.

---

## Current Baselines

| Metric | Value | Model/Config | Date | Notes |
|--------|-------|-------------|------|-------|
| Clone + install + first status | 3.55s | macOS local fixture | 2026-04-13 | Remote clone, installer run, first `status` command |
| Install only | 0.04s | macOS local fixture | 2026-04-13 | Local framework copy |

## Baseline History

| Date | Metric | Old → New | Cause |
|------|--------|-----------|-------|
| 2026-04-13 | Operator command examples | `python` → `python3` | Validation host did not expose a `python` alias |
| 2026-04-13 | Overwrite prompt coverage | partial → full managed file list | P0 install audit identified silent overwrite risk |

---

## AI Annotations

<!-- Auto-appended by agents via: python3 scripts/context_hub.py annotate Performance_Baselines "note" -->
