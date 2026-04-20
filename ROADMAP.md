# ROADMAP — OAW

## Current Focus

- Phase: **star-growth polish + harness quality hardening**
- Goal: 強化 GitHub 首屏轉換、修補 example 漂移、讓 adapter 支援與 README 敘事一致，並把 OAW 從 context-continuity harness 推進到更可觀測、可驗收的 execution harness
- Definition of done:
  - ✅ 所有 root operational files 指向已發布的 v1.0.0 狀態
  - ✅ CHANGELOG 明確標示 pre-launch hardening 已併回 v1.0.0
  - ✅ example/minimal-project 與 fresh install 必要檔案對齊
  - ✅ README 首屏 outcome-first 化
  - ✅ LLM-wiki collaboration packet reviewed (see Future_Optimization_Plan_Confirmed)
  - ✅ Harness quality audit recommendations triaged (3 Accept / 4 Research / 3 Reject)
  - [ ] LLM-wiki packet merged to main as v1.1.0
  - [ ] `harness_check` + skill frontmatter lint landed in main
  - [ ] GitHub topics / description / Discussions settings 合併後再調整

## Active Work

| Priority | Workstream | Status | Notes |
|----------|------------|--------|-------|
| P0 | README 英文主頁 + 多語言 | ✅ Done | README.md=EN, README.zh.md=ZH, readme-i18n 其他語言 |
| P0 | Harness Engineering 三大支柱 | ✅ Done | README + 3 knowledge 頁 |
| P0 | Git history 清理 | ✅ Done | filter-repo 移除敏感 ref |
| P1 | Skills alignment | ✅ Done | wiki-refresh.md 補入 example/minimal-project/ |
| P1 | Design docs update | ✅ Done | Design_Principles.md 已有 Hybrid Router 命名演進 |
| P1 | 正式 tag v1.0.0 | ✅ Done | 2026-04-18 |
| P1 | 版本敘事一致化 | ✅ Done | 已明確將短暫的 v1.0.1 內部標記併回 v1.0.0 |
| P1 | Star-growth polish | ✅ Done | README 首屏、comparison doc、minimal-project drift CI 已落地 |
| P1 | LLM-wiki collaboration packet (A-1) | In progress | Taiwan.md-inspired 8 artifacts integrated in `study/future-optimization-plan-confirmed`, awaiting merge as v1.1.0 |
| P1 | `harness_check` one-command gate (A-2) | In progress | `scripts/harness_check.py` 8-check harness; CI collapsed to single `harness_check` step |
| P1 | Skill frontmatter lint (A-3) | In progress | `wiki_sync.py lint` extended — warn by default, strict fail; existing 6 skills all green |
| P1 | Harness evaluator skill (from R-1) | Queued — spec ready | Subagent-based evaluator design decided; implement Week 4 per `Evaluator_Design_Decision_2026-04-20.md` |
| P2 | Lane audit log (R-2) | Contingent on R-1 usage | Defer until evaluator skill first asks "what files did parent load?" |
| P2 | Recovery / retry / rollback automation | ❌ Deferred — see R-3 | 0/9 historical failures would benefit; skip skeleton, revisit after ≥3 new runtime-flakiness cases |
| P2 | Worktree collaboration skill | ❌ Deferred | Maintain contingent — rebuild only when ≥3 people on a branch ≥2 weeks |
| P2 | `--json` output on CLI (R-4) | Contingent on R-1 | Build only if evaluator skill needs structured input |
| P2 | Task-state CLI | ❌ Rejected | `memory.md` + `ROADMAP.md` already cover the need |
| P2 | Community feedback | Ongoing | Monitor issues and PRs |

## Next Milestones

1. ✅ Repo health review complete (2026-04-15)
2. ✅ Sensitive content sanitized (2026-04-15)
3. ✅ Harness self-hosting merged to main (2026-04-15)
4. ✅ README improvements shipped (2026-04-15)
5. ✅ Cross-agent compatibility table (2026-04-16)
6. ✅ Pre-release build complete (2026-04-16)
7. ✅ README 大改版：EN 主頁、Harness Engineering、SOP Dispatch (2026-04-18)
8. ✅ Skills alignment + tag v1.0.0 (2026-04-18)
9. ✅ Version narrative cleanup: keep pre-launch hardening under v1.0.0 (2026-04-18)
10. ✅ Taiwan.md wiki packet + Harness Engineering audit triaged — see `docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md` (2026-04-20)
11. ✅ R-1 Evaluator design decision — subagent-based approach, empirically verified — see `docs/archive/Evaluator_Design_Decision_2026-04-20.md` (2026-04-20)
12. ✅ R-3 Skill failure modes analysis — Recovery section deferred (0/9 cases fit) — see `docs/archive/Skill_Failure_Modes_2026-04-20.md` (2026-04-20)
13. [ ] Merge `study/future-optimization-plan-confirmed` worktree → main as v1.1.0 (Week 1 target)
14. [ ] Week 4: ship `harness-evaluator.md` skill per R-1 decision; first use on the v1.1.0 merge PR

## Completed

- ✅ 2026-04-20: Taiwan.md wiki governance packet integrated (8 artifacts) in `study/future-optimization-plan-confirmed` worktree
- ✅ 2026-04-20: `scripts/harness_check.py` one-command health gate (8 checks, all green)
- ✅ 2026-04-20: Skill frontmatter lint added to `wiki_sync.py` (triggers/outputs + execution-structure heading required)
- ✅ 2026-04-20: R-1 evaluator design decision — subagent approach, empirically verified (19k tokens, 13s per review)
- ✅ 2026-04-20: R-3 recovery-pattern research — defer (0/9 failures fit the Recovery framing; existing A-1/A-2/A-3 cover the real clusters)
- ✅ 2026-04-18: tag v1.0.0 正式發布
- ✅ 2026-04-18: 短暫出現的 v1.0.1 內部標記已明確併回 v1.0.0 敘事
- ✅ 2026-04-18: README 英文主頁化，Harness Engineering 三大支柱、wiki_sync 工作流說明、readme-i18n 多語言
- ✅ 2026-04-16: Pre-release build — cross-agent table, CHANGELOG, review validation
- ✅ 2026-04-15: Harness testing (17/17 passed)
- ✅ 2026-04-15: Repo health review & sanitization
- ✅ 2026-04-14: P0 release validation
- ✅ 2026-04-14: README refresh (zh + en)
- ✅ 2026-04-13: Initial public release
