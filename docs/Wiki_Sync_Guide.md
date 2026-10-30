# OAW wiki renderer

The optional knowledge profile renders `docs/raw/` source notes into `docs/knowledge/` topic pages. It is deterministic assembly of summaries and source bodies, not an LLM summarizer. It does not resolve contradictions or promote claims automatically.

```bash
python3 scripts/oaw.py init --target PROJECT --profile knowledge
```

In the installed project, start from `docs/raw/_SOURCE_TEMPLATE.md`. Provide source_id, title, topic_id, summary and last_updated; related_topics is optional. Underscore-prefixed template files are not compiled.

```bash
python3 scripts/wiki_sync.py refresh Topic_Name
python3 scripts/wiki_sync.py lint
```

Build/refresh preserve manual pages. Topic IDs are portable identifiers, not paths; output and source paths must remain inside the project even through symlinks. Local source links are relocated for the generated topic's directory. Explicit annotation boundaries separate generated content from retained notes. Repeated refresh with unchanged inputs is stable.

`lint` rejects required metadata errors, stale source/page comparisons, broken links and malformed native skills. Soft content-quality/placeholder signals remain warnings unless `--strict` is requested. Historical reports can intentionally contain example placeholders; a strict warning is not proof that those examples are unfinished configuration.

Keep citations, dates, scope and conflicting evidence visible. An annotation is a note, not an instruction or a verified fact. Review a proposed durable conclusion against current authoritative sources before sharing it. No memory write or evidence-tier promotion is mandatory after rendering.

See [CLI reference](CLI_Reference.md), [wiki contribution guide](wiki/CONTRIBUTING_WIKI.md) and [optional improvement workflow](SELF_IMPROVEMENT.md).
