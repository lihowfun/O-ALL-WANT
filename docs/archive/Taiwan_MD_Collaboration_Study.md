# Taiwan.md Collaboration Study

Date: 2026-04-19

This report captures the collaboration patterns OAW should borrow from
[`frank890417/taiwan-md`](https://github.com/frank890417/taiwan-md) for its
LLM-wiki layer.

## What Taiwan.md Does Well

- Treats markdown knowledge as a governed system, not a pile of files.
- Separates source-of-truth content from generated projection layers.
- Documents contribution workflows for research, writing, verification,
  cross-linking, and translation.
- Uses AI prompts as public contribution protocols so non-coders can help
  produce repo-shaped content.
- Adds GitHub issue templates, PR templates, and CI checks to make quality
  review visible and repeatable.
- Scans for AI-shaped weak prose, missing sources, stale facts, and structural
  drift.

## What OAW Should Borrow

- A clear wiki contribution guide that explains `docs/raw/`,
  `docs/knowledge/`, `AI_CONTEXT.md`, `.agents/memory.md`, and
  `.agents/skills/` as distinct surfaces.
- A staged wiki pipeline: gather raw evidence, compile topic, verify, connect,
  and promote repeatable procedures to skills.
- Public prompt files that let users ask an agent to create, refresh, or promote
  wiki knowledge without needing to understand every internal convention.
- Topic proposal and fact/source correction issue templates.
- Lightweight quality lint signals: required metadata, invalid dates, broken
  source refs, stale compiled pages, thin topics, and generic prose warnings.

## What OAW Should Not Borrow Yet

- Full website generation.
- Large i18n and translation dashboards.
- Heavy maintainer automation that assumes dozens of daily content PRs.
- Complex editorial scoring that would make a small coding harness feel like a
  publishing platform.

## Implemented In This Branch

- `docs/wiki/CONTRIBUTING_WIKI.md`
- `docs/wiki/WIKI_PIPELINE.md`
- `docs/wiki/TOPIC_BOARD.md`
- `docs/prompts/WIKI_TOPIC_PROMPT.md`
- `docs/prompts/WIKI_REFRESH_PROMPT.md`
- `docs/prompts/WIKI_SKILL_PROMOTION_PROMPT.md`
- `scripts/wiki_sync.py` quality lint extensions
- wiki-specific GitHub issue templates and PR checklist additions
