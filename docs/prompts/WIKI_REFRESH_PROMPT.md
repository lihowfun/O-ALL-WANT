# Prompt: Refresh An Existing Wiki Topic

Use this when a topic exists but may be stale, thin, or missing sources.

```text
Read CLAUDE.md first, then AI_CONTEXT.md.

Refresh the wiki topic: [topic id].

Do this as an OAW LLM-wiki maintenance pass:

1. Read docs/knowledge/index.md and the current topic page.
2. Read related docs/raw/ source notes before changing the compiled page.
3. Check whether the topic has stale dates, missing source refs, broken links,
   generic prose, or missing related_topics.
4. Update docs/raw/ first when the source evidence needs to change.
5. Run python3 scripts/wiki_sync.py refresh [topic id].
6. Run python3 scripts/wiki_sync.py lint.
7. Summarize what changed, what evidence supports it, and whether the topic
   should become or update a .agents/skills/ workflow.
```

## Quality Signals

- The page names concrete files, commands, decisions, dates, or measurements.
- Claims that can drift over time point back to raw source notes or stable
  links.
- Related topics help the next agent discover adjacent context without reading
  every markdown file.
