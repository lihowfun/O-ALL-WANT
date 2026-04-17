# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] — 2026-04-17

First public release. Bundles the pre-launch hardening pass into a single
tagged release.

### Added
- **Cross-agent/IDE compatibility table** — pointer files for Codex
  (`AGENTS.md`), Cursor (`.cursorrules`), Windsurf (`.windsurfrules`),
  Gemini (`GEMINI.md`), plus `.github/copilot-instructions.md` auto-created
  by the installer.
- **Self-hosting**: OAW repo uses its own harness to manage itself (eating
  our own dog food). Public memory policy documented in README.
- **`CONTRIBUTING.md`** — quick-start for external contributors: what's
  useful, what to skip, how to run CI locally, commit/PR style, release
  cadence rules.
- **`example/README.md`** — labels `minimal-project/` as Start Here and
  explains when to reach for `public-hybrid-demo/` instead.
- **`docs/Design_Principles.md` Naming Evolution table** — documents the
  path from "Fat Skills / Thin Harness" to "Hybrid Router" and from
  "Three-layer memory" to "Hybrid Router + Compiled Wiki" so older
  discussions stay legible.
- **`docs/knowledge/Release_Learnings.md`** — durable knowledge page
  capturing release review patterns.
- **`scripts/wiki_sync.py lint --strict`** — opt-in flag that flags
  unfilled `${...}` placeholders and literal `YYYY-MM-DD` dates as errors.
  Default lint behavior unchanged (still warn-only).
- **`.github/workflows/test.yml`** — CI smoke tests: Python syntax,
  `wiki_sync.py` CLI surface, install.sh self-install refusal, fresh-tempdir
  install file set, lint on fresh install, lint on the OAW repo itself,
  `--strict` correctly failing on a fresh install that still has
  placeholders.

### Changed
- **README (zh + en) rewrite**: agentic-first UX — intro moved above
  30-second try-it, "why you're here" merges the inventory bullets so nothing
  is said twice, Plan A and Plan B consolidated, duplicate "core principle"
  notes collapsed. Net -217 lines across both languages without losing the
  humor.
- **`install.sh`** refuses to install into the OAW framework repo itself
  (previously `$(pwd)` silently overwrote root CLAUDE.md / AI_CONTEXT.md /
  ROADMAP.md when users ran `./install.sh` from the clone). Override with
  `--force-self-install`.
- **`scripts/wiki_sync.py`** — orphan-page detection softened from error
  to warning. A repo with one curated knowledge note is a valid pattern.
- **`docs/knowledge/Release_Learnings.md`** frontmatter cleaned up
  (`page_type: topic`, stable `id`/`title`, no broken `related_topics`).
  Used to cause a spurious lint failure on the OAW repo itself.
- **`templates/VERSION.json`** refreshed for the release (previously
  `0.2.0-dev` left new users staring at a stale version after install).
- Root `AI_CONTEXT.md` + `VERSION.json` now reference `lihowfun/O-ALL-WANT`
  (was the older `agent-memory-framework` name).
- **Design Sources** ledger in README is explicit about "Borrowed" vs
  "Not Yet Implemented" — no overclaiming.

### Fixed
- Running `./install.sh` from the repo root no longer corrupts the
  framework's own root files.
- `wiki_sync.py lint` passes on the OAW repo itself (previously failed on a
  pre-existing Release_Learnings frontmatter issue).

### Verified
- Full CI matrix locally: `py_compile` on both scripts; `--help` surfaces
  build/refresh/lint; `install.sh` refuses self-install; fresh-tempdir
  install drops the expected file set; `wiki_sync.py lint` passes on both
  the OAW repo and a fresh install; `--strict` correctly fails on a fresh
  install.
- Cross-agent review: harness structure validated against a real downstream
  project.
- All scripts functional: `context_hub.py` (8 commands), `wiki_sync.py`
  (3 commands).

### Holding pattern
- Branch `v1.1-preview` carries a speculative feature set (CURRENT_STATE
  template, non-interactive `wiki_sync` subcommands, Session-End
  AI-responsibility rewrite) driven by a single integrator's feedback. It
  stays parked there until ≥1 more user confirms the pattern is useful.

## [0.2.0-dev] — 2026-04-13

### Added
- `scripts/wiki_sync.py` with `build`, `refresh`, and `lint` commands
- `docs/raw/` starter templates for raw source notes
- Compiled wiki metadata pattern (`index.md`, `log.md`, topic frontmatter)
- `docs/knowledge/Experiment_Findings.md` template
- `wiki-refresh.md` skill for refreshing compiled wiki topics
- `docs/Wiki_Sync_Guide.md` and `docs/Hybrid_Wiki_Router_Experiment.md`
- `example/public-hybrid-demo/` sanitized public demo for the hybrid router

### Changed
- Upgraded the framework from a simple three-layer memory description to a hybrid router:
  operational lane + compiled wiki lane + execution lane
- `install.sh` now installs `scripts/wiki_sync.py` and `docs/raw/`
- `context_hub.py` now skips wiki meta pages in search/status and reports raw-source counts
- `AI_CONTEXT.md`, `CLAUDE.md`, `VERSION.json`, and skill templates now describe raw→wiki workflows

## [0.1.1] — 2026-04-13

### Added
- **`install.sh`** — One-command installer with safety checks and overwrite warnings
- Cleaner README structure focusing on quick onboarding

### Changed
- **BREAKING**: Simplified Quick Start from 5-minute multi-step to <1 minute one-command
- Moved detailed concepts (File Structure, Design Principles) to separate docs
- Fixed Garry Tan credit link (X/Twitter post instead of Greptile blog)
- Condensed "Measured Results" into concise "Why This Works" table
- Streamlined FAQ answers for better readability

### Removed
- Verbose "File Structure" section from README (users see it after install anyway)
- Redundant "Core Concepts" details (moved to `docs/Design_Principles.md`)

## [0.1.0] — 2026-04-13

### Added
- Initial framework release
- Three-layer memory architecture (session → rolling → knowledge base)
- `context_hub.py` CLI with 8 commands (search, get, annotate, memory, lesson, status, bootstrap)
- 5 template skills (self-improving, benchmark, experiment-report, debug-pipeline, version-release)
- Skill template (`_TEMPLATE.md`) for creating new skills
- Template files for agent rules, AI context, VERSION.json, memory.md
- Knowledge file templates (Known_Limitations, Performance_Baselines, Architecture_Decisions)
- Copilot instructions template
- Documentation: Architecture Origins, Design Principles
- MIT License

### Design Sources — What OAW Actually Borrowed
- [Andrew Ng's Context Hub](https://github.com/andrewyng/context-hub) — **Borrowed**: knowledge file structure (`docs/knowledge/`), CLI-based context management (`context_hub.py`), search/annotate/status pattern. **OAW adds**: skills dispatch layer, wiki compilation pipeline, hybrid 4-lane routing.
- [MemPalace](https://github.com/MemPalace/mempalace) — **Borrowed**: rolling `memory.md` with append-only discipline, "read last N entries" pattern, session-end 4-part summary format. **Not yet implemented**: hierarchical compression, memory→topic consolidation, archival rotation.
- [Garry Tan "Thin Harness, Fat Skills"](https://x.com/garrytan/status/1917325461256498517) — **Borrowed**: philosophy of keeping the harness thin (`CLAUDE.md` < 120 lines) while putting executable knowledge in skill files. **OAW adds**: trigger-based dispatch, `_TEMPLATE.md` standardization.
