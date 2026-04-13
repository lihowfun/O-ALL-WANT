# Changelog

All notable changes to this project will be documented in this file.

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
- [MemPalace](https://github.com/milla-jovovich/mempalace) — anti-amnesia discipline
- [Garry Tan "Thin Harness, Fat Skills"](https://greptile.com/blog/agents) — executable knowledge
