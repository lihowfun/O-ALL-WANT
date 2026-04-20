# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased / v1.1.0-preview]

This release bundles two parallel investments completed on 2026-04-20:

1. **Taiwan.md-inspired wiki governance layer** — a shipped LLM-wiki
   contribution pipeline + public prompts + quality lint extensions.
2. **Pre-work for harness quality hardening** — `harness_check` one-command
   gate, skill frontmatter lint, and decision documents for the two research
   items from the 2026-04-20 Harness Engineering audit.

Both ship as a single v1.1.0 because the audit itself is what scoped A-2 and
A-3. Audit findings that did **not** become shippable work (evaluator skill,
recovery pattern, task-state CLI, lane audit log, JSON CLI output) are
explicitly triaged in
[`docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md`](docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md).

### Added
- **Taiwan.md wiki governance packet** (8 artifacts):
  - `docs/wiki/CONTRIBUTING_WIKI.md` — wiki contribution guide
  - `docs/wiki/WIKI_PIPELINE.md` — staged gather → compile → verify → connect → promote pipeline
  - `docs/wiki/TOPIC_BOARD.md` — topic tracking board
  - `docs/prompts/WIKI_TOPIC_PROMPT.md` — public prompt to propose/create a wiki topic
  - `docs/prompts/WIKI_REFRESH_PROMPT.md` — public prompt to refresh
  - `docs/prompts/WIKI_SKILL_PROMOTION_PROMPT.md` — public prompt to promote a repeatable procedure to a skill
  - `.github/ISSUE_TEMPLATE/wiki_topic_proposal.yml` + `wiki_fact_correction.yml`
  - `scripts/wiki_sync.py` lint extensions: required-metadata enforcement, invalid-date detection, stale-page warnings, thin-topic warnings, hollow-prose warnings
- **`scripts/harness_check.py`** — one-command local health gate covering
  pycompile, CLI surface, install-refusal, fresh-install file set,
  fresh-install lint, repo lint, strict placeholder detection, and
  `example/minimal-project` drift. CI now calls it as a single step.
- **Skill frontmatter lint** in `wiki_sync.py lint` — skills under
  `templates/.agents/skills/*.md` must have `triggers` or `outputs` plus an
  execution-structure heading (Steps / Rules / Workflow / Procedure). Warn
  by default, `--strict` promotes to error. Existing 6 skills all pass.
- **Star-growth positioning pass**: clearer README first screen, comparison
  guide, and CI coverage for `example/minimal-project/` fixture drift.
- **Adapter files auto-created by installer** for Codex (`AGENTS.md`),
  Cursor (`.cursorrules`), Windsurf (`.windsurfrules`), Gemini (`GEMINI.md`).

### Changed
- `example/minimal-project/` now tracks a fresh `install.sh` run, including
  `wiki_sync.py`, `docs/raw/`, and wiki meta pages; CI enforces drift.
- Public-facing wording now uses "OAW" as the product name; older "Agent
  Memory Framework" references are kept only as history.
- New-project agent prompt in `install.sh` and README now reads "Use OAW's
  architecture as the harness, map this project's real state into
  `AI_CONTEXT.md`" instead of merely "fill in the scaffold" — explicit per
  the 2026-04-20 harness audit recommendation.
- `ROADMAP.md` Active Work table reorganized to reflect the accept/research/
  reject decisions from `Future_Optimization_Plan_Confirmed_2026-04-20.md`.

### Research decisions (no code shipped from these, but documented)
- [R-1 `Evaluator_Design_Decision_2026-04-20.md`](docs/archive/Evaluator_Design_Decision_2026-04-20.md)
  — subagent-based evaluator is empirically feasible; spec ready for Week 4
  implementation.
- [R-3 `Skill_Failure_Modes_2026-04-20.md`](docs/archive/Skill_Failure_Modes_2026-04-20.md)
  — 9 historical failures analyzed; 0 of 9 fit the Recovery/retry/rollback
  framing. No skill-template change ships; revisit in 3 months.

### Explicitly rejected or deferred
- Task-state CLI (over `VERSION.json.task_state`): `memory.md` + `ROADMAP.md`
  already cover the need; ROI too low.
- Recovery skeleton in skill template: no matching failure cases (see R-3).
- Worktree collaboration skill: maintains contingent status — rebuild only
  when ≥3 people on a branch ≥2 weeks hits a real merge pain point.
- `--json` CLI output, lane audit log: both contingent on the R-1 evaluator
  skill actually needing structured input / loaded-file provenance; defer
  until demand emerges.

## [1.0.0] — 2026-04-17

First public release. Bundles the pre-launch hardening pass into a single
tagged release.

The short-lived internal `v1.0.1` label used during pre-launch hardening was
never shipped as a public release; those changes were consolidated back into
`v1.0.0` before tagging.

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
