# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] — 2026-04-16

### Added
- Cross-agent/IDE compatibility table — pointer files for Codex (`AGENTS.md`), Cursor (`.cursorrules`), Windsurf (`.windsurfrules`), Gemini (`GEMINI.md`)
- Self-hosting: OAW repo now uses its own harness to manage itself (eating our own dog food)
- `.github/copilot-instructions.md` auto-created by installer for GitHub Copilot support
- `docs/knowledge/Release_Learnings.md` — durable knowledge page capturing release review patterns
- Public memory policy clarified in Self-Hosting section

### Changed
- **README rewrite (zh + en)**: agentic-first UX — dispatch table, precise AI prompts for Plan A/B, file tree with agent-behavior annotations
- Section reorder: "Why won't this become a mess" now follows architecture diagram for narrative flow
- Integrated LLM Wiki section into architecture explanation (no more standalone section)
- Softened absolute claims ("Agent 自動做" → "Agent 通常會做") for cross-agent accuracy
- GitHub repo URL updated to `lihowfun/O-ALL-WANT`
- Design Sources updated with honest "Borrowed / Not Yet Implemented" ledger

### Fixed
- `templates/VERSION.json` was still `0.2.0-dev` — new users saw stale version after install
- Root `AI_CONTEXT.md` and `VERSION.json` still referenced old repo name `agent-memory-framework`

### Verified
- Fresh install test (macOS): clone + install.sh + context_hub.py status — version now shows correctly
- Cross-agent review: harness structure validated against a real downstream project
- All scripts functional: context_hub.py (8 commands), wiki_sync.py (3 commands)

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
