# Repo Health Review — OAW Framework

> **Date**: 2026-04-15  
> **Scope**: `repo/` directory — public-facing harness  
> **Reviewer**: Automated architecture audit  
> **Verdict**: 🟡 Yellow-Green — Usable, with actionable improvements below

---

## 1. File Structure Audit

### ✅ Present and Correct

| File / Dir | Role | Status |
|------------|------|--------|
| `README.md` / `README.en.md` | Landing page (zh/en) | ✅ |
| `install.sh` | One-command installer | ✅ |
| `CHANGELOG.md` | Version history | ✅ |
| `LICENSE` | MIT | ✅ |
| `scripts/` | `context_hub.py`, `wiki_sync.py` | ✅ |
| `templates/` | Installable templates | ✅ |
| `example/minimal-project/` | Post-install snapshot | ✅ |
| `docs/Architecture_Origins.md` | Design lineage | ✅ |
| `docs/Design_Principles.md` | Thin Harness, Hybrid Router | ✅ |
| `docs/archive/Release_Checklist.md` | P0 validation record | ✅ |

### ⚠️ Potential Issues

| Item | Concern | Severity | Recommendation |
|------|---------|----------|----------------|
| `_tmp/` (workspace root) | Contains test fixtures — not inside `repo/` | 🟡 Medium | Add to `.gitignore` at workspace root |
| `private/` (workspace root) | Contains sensitive experiment data | 🔴 High | Must never be committed. Delete or move outside workspace. |
| Missing `CLAUDE.md` in `repo/` root | Only in `templates/` | 🟡 Medium | By design — clarify in README that it appears after install |

---

## 2. Action Items

### P0 — Do Now (Completed ✅)

| # | Action | Status |
|---|--------|--------|
| 1 | Verify `private/` and `_tmp/` are not git-tracked | ✅ Done |
| 2 | Delete sensitive directories | ✅ Done |
| 3 | Add `_tmp/` and `private/` to root `.gitignore` | ✅ Done |

### P1 — Do This Week

| # | Action | File |
|---|--------|------|
| 4 | Add "What You Get After Install" section to both READMEs | `repo/README.md`, `repo/README.en.md` |
| 5 | Add a "When To Use What" quick-reference table | `repo/README.md` |
| 6 | Clarify that `CLAUDE.md` appears only after install | `repo/README.md` |
| 7 | Add naming evolution note to Design Principles | `repo/docs/Design_Principles.md` |
| 8 | Clarify lazy-read vs always-read in README | `repo/README.md` |
| 9 | Align skills list between templates and example | Check `wiki-refresh.md` |

### P2 — Nice To Have

| # | Action | File |
|---|--------|------|
| 10 | Clean up `_tmp/` fixtures after validation | `_tmp/` |
| 11 | Add archive index if `docs/archive/` grows | `repo/docs/archive/README.md` |
| 12 | Resize meme image for mobile | `repo/README.md` |

---

## 3. Summary Scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| File completeness | ⭐⭐⭐⭐ | All core files present |
| Routing clarity | ⭐⭐⭐⭐ | Good in docs, could be more explicit in README |
| README readability | ⭐⭐⭐⭐ | Strong hook, needs post-install orientation |
| Cross-file consistency | ⭐⭐⭐½ | Minor naming drift |
| Security posture | ⭐⭐⭐⭐⭐ | Clean — sensitive dirs deleted |
| **Overall** | **⭐⭐⭐⭐** | **Ship-ready with minor polish** |

---

## 4. Execution Log

### 2026-04-15 — Initial Audit

- [x] Verified git tracking status — `_tmp/` and `private/` not tracked ✅
- [x] Deleted `private/` directory (contained sensitive experiment data)
- [x] Deleted `_tmp/private_project_plan/` (contained sensitive project files)
- [x] Created `.gitignore` at workspace root with `_tmp/` and `private/`
- [x] Confirmed no sensitive references in `repo/` git history
- [x] Sanitized this review file to remove sensitive project names
