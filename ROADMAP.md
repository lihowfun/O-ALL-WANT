# ROADMAP — Agent Memory Framework

## Current Focus

- Phase: **v1.1 shipped — iterate on community feedback**
- Goal: Harden the auto-update story introduced in v1.1, absorb PRIVATE_PROJECT feedback
- Definition of done:
  - Self-hosting harness merged to main ✅
  - README improvements (post-install, decision table, self-hosting) ✅
  - Skills alignment between templates/ and example/ ✅ (v1.1.0)
  - PRIVATE_PROJECT feedback P0/P1 items implemented ✅ (v1.1.0)
  - Placeholder-aware lint + CURRENT_STATE regression tests (P1, queued)

## Active Work

| Priority | Workstream | Status | Notes |
|----------|------------|--------|-------|
| P0 | Self-harness on main | ✅ Done | v1.0.0 |
| P0 | README improvements | ✅ Done | v1.0.0, zh + en |
| P0 | PRIVATE_PROJECT feedback P0/P1 | ✅ Done | v1.1.0 — CURRENT_STATE, non-interactive wiki_sync, AI-responsibility Session End |
| P0 | Skills alignment | ✅ Done | v1.1.0 — example/minimal-project/ synced with templates/ |
| P1 | Placeholder-aware lint | Queued | `wiki_sync.py lint` should catch `${...}` / `YYYY-MM-DD` leftovers in knowledge pages |
| P1 | CURRENT_STATE regression test | Queued | Automated test: install → add-experiment → update-state → lint |
| P1 | README — CURRENT_STATE entry-point doc | Queued | Explain the "read one file" pattern so new users actually use it |
| P1 | Design docs update | Queued | Add naming evolution note ("Fat Skills" → "Hybrid Router") |
| P2 | Skill dispatch mechanism | Deferred | `context_hub.py skill-match "task"` — let AI auto-pick matching skill |
| P2 | Multi-worktree memory sync protocol | Deferred | Append-only memory + file lock, or per-worktree notes merged back to main |
| P2 | `wiki_sync.py build-world-model` | Deferred | Auto-compile CURRENT_STATE from topic pages |
| P2 | Community feedback | Ongoing | Monitor issues and PRs |

## Future Plan (P1 detail)

### P1-1. Placeholder-aware lint (1–2h)

**Problem**: After `install.sh`, users often forget to replace `${PROJECT_NAME}`,
`YYYY-MM-DD`, `${LANGUAGE}` in installed files. The current `wiki_sync.py lint`
only checks metadata and links.

**Approach**:
- Add a regex pass in `lint()` that scans every knowledge page body + frontmatter
  for `\$\{[^}]+\}` and literal `YYYY-MM-DD`.
- Report as **warnings** by default (exit 0) + **errors** when `--strict` is set.
- Skip the `_TEMPLATE.md` / `_SOURCE_TEMPLATE.md` fixtures.

**Acceptance**: a fresh `install.sh` immediately followed by `lint --strict`
fails with a list of placeholders still to fill.

### P1-2. CURRENT_STATE regression test (2–3h)

**Problem**: No automated guarantee that the post-install file set produces a
working `add-experiment` / `update-state` flow.

**Approach**:
- Add `tests/test_install_flow.sh` that:
  1. `mktemp -d` + `./install.sh` with `y` piped
  2. Run `wiki_sync.py add-experiment --name smoke ...`
  3. Run `wiki_sync.py update-state --phase ... --status ... --note ...`
  4. Assert the file diffs match expected patterns (row count, frontmatter bump)
- Wire into CI (`.github/workflows/test.yml`) — runs on every push.

**Acceptance**: PRs touching `templates/` or `scripts/` must pass this test.

### P1-3. README — CURRENT_STATE entry-point doc (30min)

**Problem**: v1.1.0 ships CURRENT_STATE.md but README does not explain the
"read one file" pattern. Users may ignore it.

**Approach**: Add a dedicated sub-section to both README.md (zh) and README.en.md
showing: (a) what goes in CURRENT_STATE.md, (b) when to update it,
(c) the `update-state` CLI as the preferred update mechanism.

### P1-4. Design docs update (1h)

Add a "Naming Evolution" note to `docs/Design_Principles.md`: "Fat Skills"
was an earlier name; the current "Hybrid Router" concept evolved from it.
Context for anyone reading old design docs.

## Future Plan (P2 detail — deferred, not committed)

### P2-1. Skill dispatch mechanism

AI currently needs to know which skill matches a task. `context_hub.py
skill-match "refresh the wiki for Performance_Baselines"` would scan all
`.agents/skills/*.md` `triggers:` frontmatter and return best match.

### P2-2. Multi-worktree memory sync

When 6+ worktrees run in parallel, `memory.md` merges conflict. Two options:
- Append-only file + file lock (conservative)
- Per-worktree `worktree_notes.md` that `wiki_sync.py merge-worktrees` consolidates

### P2-3. `wiki_sync.py build-world-model`

Today CURRENT_STATE.md is hand-maintained (via `update-state`). A
`build-world-model` command would walk topic pages, extract their
`last_updated` + first paragraph, and regenerate CURRENT_STATE sections
1–6 deterministically. §9 Common Commands stays hand-written.

## Completed

- ✅ 2026-04-17: **v1.1.0** — PRIVATE_PROJECT feedback P0/P1 implemented
  - CURRENT_STATE template + EXPERIMENT_LOG + non-interactive wiki_sync
    subcommands + AGENT_RULES Session End rewrite + example/minimal-project/
    sync
- ✅ 2026-04-16: v1.0.0 tagged — cross-agent table, CHANGELOG, review validation
- ✅ 2026-04-15: Harness testing (17/17 passed)
- ✅ 2026-04-15: Repo health review & sanitization
- ✅ 2026-04-14: P0 release validation
- ✅ 2026-04-14: README refresh (zh + en)
- ✅ 2026-04-13: Initial public release
