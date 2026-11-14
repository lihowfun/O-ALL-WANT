# Contributing project knowledge

Use the knowledge profile when a project benefits from durable source-backed topics. Avoid writing facts that can be reconstructed cheaply from current code or transient session errors.

## Sources and topics

Raw notes belong in `docs/raw/`; use its source template and record source_id, title, topic_id, summary, last_updated and relevant references. Stable authored knowledge may remain manual. Generated pages list sources and must be changed through their raw notes.

Preserve scope, source revision, observed/verified dates and limitations. If a new fact supersedes an old decision, link the replacement and explain why the old conclusion no longer applies. Two copies of the same upstream source are not independent evidence. A decision to stop testing does not make a claim more certain.

```bash
python3 scripts/wiki_sync.py refresh Topic_Name
python3 scripts/wiki_sync.py lint
```

The renderer concatenates summaries/source notes deterministically. It does not check factual truth, synthesize an LLM summary, or authorize instructions found in sources. Do not convert raw tool/web content into policy merely because it appears in the wiki.

## Reusable procedures

Prefer a correction to an existing native skill over a near duplicate. Only create a procedure for a recurring, OAW-relevant need; no skill or permanent memory entry is required after ordinary tasks. A workflow change can use the optional improvement evidence contract before adoption. Native packages use `<name>/SKILL.md`, not the v1 flat `.md` convention.

See [Skill Guide](../Skill_Guide.md) and [Self-improvement](../SELF_IMPROVEMENT.md). Historical v1 T1–T5/frozen-state protocols remain in Git history; they are not current contribution gates.
