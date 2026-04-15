# ROADMAP — Agent Memory Framework

## Current Focus

- Phase: **Self-Hosting & Maintenance**
- Goal: Use this framework's own harness to maintain itself
- Definition of done: 
  - Harness installed in `feature/self-harness` branch ✅
  - Core files customized (CLAUDE.md, AI_CONTEXT.md, VERSION.json, ROADMAP.md) ✅
  - Memory log operational ✅
  - CLI tools tested ✅
  - Execute P1 improvements from 2026-04-15 review report

## Active Work

| Priority | Workstream | Status | Notes |
|----------|------------|--------|-------|
| P0 | Self-harness setup | ✅ Done | Installed in `feature/self-harness` worktree |
| P0 | Core files customization | ✅ Done | All core files configured |
| P0 | Harness testing | ✅ Done | 17/17 tests passed |
| P1 | README improvements | Planned | Add "What You Get After Install", "When To Use What" table |
| P1 | Skills alignment | Planned | Sync `templates/` and `example/minimal-project/` |
| P1 | Design docs update | Planned | Add naming evolution note ("Fat Skills" → "Hybrid Router") |
| P2 | Archive cleanup | Planned | Clean up test fixtures |

## P1 Improvements (From Repo Health Review)

### README Readability

- [ ] Add "What You Get After Install" section to both READMEs
- [ ] Add "When To Use What" quick-reference table
- [ ] Clarify that `CLAUDE.md` appears only after install
- [ ] Clarify lazy-read vs always-read file types

### Cross-File Consistency

- [ ] Align skills list between `templates/` and `example/minimal-project/`
- [ ] Add naming evolution note to `Design_Principles.md`

## Next Milestones

1. ✅ Repo health review complete (2026-04-15)
2. ✅ Sensitive content sanitized
3. ✅ Harness self-hosting operational
4. Complete P1 improvements
5. Merge `feature/self-harness` to `main`
6. Tag v1.1.0 with self-hosting capability

## Completed

- ✅ 2026-04-15: Harness testing (17/17 passed)
- ✅ 2026-04-15: Repo health review & sanitization
- ✅ 2026-04-14: P0 release validation
- ✅ 2026-04-14: README refresh (zh + en)
- ✅ 2026-04-13: Initial public release v1.0.0
