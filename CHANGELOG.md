# Changelog

All notable changes to this project will be documented in this file.

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

### Design Sources
- [Andrew Ng's Context Hub](https://github.com/andrewyng/context-hub) — knowledge management infrastructure
- [MemPalace](https://github.com/MemPalace/mempalace) — anti-amnesia discipline
- [Garry Tan "Thin Harness, Fat Skills"](https://greptile.com/blog/agents) — executable knowledge
