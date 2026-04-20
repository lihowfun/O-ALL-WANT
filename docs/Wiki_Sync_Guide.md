# Wiki Sync Guide

`wiki_sync.py` is the deterministic helper for the hybrid wiki layer. It keeps
`docs/raw/` as the detailed source-of-truth layer and `docs/knowledge/` as the
compact retrieval layer.

For multi-person wiki maintenance, start with
[`docs/wiki/CONTRIBUTING_WIKI.md`](wiki/CONTRIBUTING_WIKI.md) and the staged
pipeline in [`docs/wiki/WIKI_PIPELINE.md`](wiki/WIKI_PIPELINE.md).

## When To Use It

Use `wiki_sync.py` when:

- you added or updated a note in `docs/raw/`
- a wiki topic is missing or stale
- you want to regenerate `docs/knowledge/index.md` and `log.md`
- you want a deterministic lint check over source refs, topic metadata, and links

Skip it when:

- you only need rolling memory in `.agents/memory.md`
- a one-off note belongs in a manual topic page, not a compiled wiki topic

## Commands

```bash
python3 scripts/wiki_sync.py build
python3 scripts/wiki_sync.py refresh Topic_Name
python3 scripts/wiki_sync.py refresh all
python3 scripts/wiki_sync.py lint
```

## Raw Source Format

Start from `docs/raw/_SOURCE_TEMPLATE.md`.

Required metadata:

- `source_id`: stable source identifier
- `title`: human-readable source title
- `topic_id`: target wiki topic filename
- `summary`: one-sentence reason this source matters
- `last_updated`: `YYYY-MM-DD`

Recommended metadata:

- `related_topics`: list of wiki topics linked to this source

## Generated Wiki Contract

Compiled topic pages carry minimal frontmatter:

- `id`
- `title`
- `page_type`
- `build_origin`
- `source_refs`
- `last_updated`
- `related_topics`

`index.md` and `log.md` are meta pages. `context_hub.py search ""` ignores them
so the visible topic list stays clean.

## Lint Checks

`python3 scripts/wiki_sync.py lint` checks for:

- missing required raw/source metadata
- invalid `last_updated` dates
- missing source refs
- broken markdown links
- duplicate topic IDs
- broken `related_topics`
- stale compiled pages
- orphan topic pages with no source refs and no topic links
- thin or generic topic pages as soft quality warnings

## Operating Rule

If a wiki page is generated from `docs/raw/`, edit the raw source first and
refresh the topic. Do not treat the compiled page as the primary authoring
surface.
