# Prompt: Create Or Refresh A Wiki Topic

Paste this into your agent when you want to build an OAW-style wiki topic for a
new project or a new area of an existing project.

```text
Read CLAUDE.md first, then AI_CONTEXT.md.

I am building: [describe the project in one or two sentences].

Use OAW's architecture as the harness, then map this project's real state into
AI_CONTEXT.md and the wiki:

1. Identify the project facts that belong in AI_CONTEXT.md.
2. Identify durable topics that belong in docs/knowledge/.
3. For each topic, identify the raw evidence that should live in docs/raw/.
4. Create or update the smallest useful raw source note and compiled wiki topic.
5. Run python3 scripts/wiki_sync.py lint.
6. Tell me which repeated workflows are strong candidates for .agents/skills/.

Keep operational instructions in CLAUDE.md, project facts in AI_CONTEXT.md,
source evidence in docs/raw/, durable summaries in docs/knowledge/, and
repeatable execution procedures in .agents/skills/.
```

## Expected Output

- Edited `AI_CONTEXT.md` if project facts were missing.
- One or more `docs/raw/*.md` source notes.
- Refreshed `docs/knowledge/*.md` topic pages.
- A short list of skill candidates with triggers and verification commands.
