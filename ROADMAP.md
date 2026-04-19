# ROADMAP — OAW

## Current Focus

- Phase: **star-growth polish**
- Goal: 強化 GitHub 首屏轉換、修補 example 漂移、讓 adapter 支援與 README 敘事一致
- Definition of done:
  - ✅ 所有 root operational files 指向已發布的 v1.0.0 狀態
  - ✅ CHANGELOG 明確標示 pre-launch hardening 已併回 v1.0.0
  - ✅ example/minimal-project 與 fresh install 必要檔案對齊
  - ✅ README 首屏 outcome-first 化
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
| P1 | Star-growth polish | In progress | README 首屏、comparison doc、minimal-project drift CI |
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

## Completed

- ✅ 2026-04-18: tag v1.0.0 正式發布
- ✅ 2026-04-18: 短暫出現的 v1.0.1 內部標記已明確併回 v1.0.0 敘事
- ✅ 2026-04-18: README 英文主頁化，Harness Engineering 三大支柱、wiki_sync 工作流說明、readme-i18n 多語言
- ✅ 2026-04-16: Pre-release build — cross-agent table, CHANGELOG, review validation
- ✅ 2026-04-15: Harness testing (17/17 passed)
- ✅ 2026-04-15: Repo health review & sanitization
- ✅ 2026-04-14: P0 release validation
- ✅ 2026-04-14: README refresh (zh + en)
- ✅ 2026-04-13: Initial public release
