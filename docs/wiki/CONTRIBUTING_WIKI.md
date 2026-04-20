# Contributing To The LLM Wiki

The OAW wiki is not a folder of random markdown. It is the durable knowledge
layer that lets a future agent resume work without replaying the whole project.

## What Goes Where

| Surface | Purpose | Edit Directly? |
|---------|---------|----------------|
| `AI_CONTEXT.md` | Current project facts, commands, architecture, safety notes | Yes |
| `.agents/memory.md` | Rolling session diary and recent decisions | Yes, local-first |
| `docs/raw/` | Source notes, evidence, meeting notes, experiment material | Yes |
| `docs/knowledge/` | Compact topic pages used by the Wiki lane | Usually via `wiki_sync.py` |
| `.agents/skills/` | Repeatable workflows that agents should execute consistently | Yes, after the pattern is proven |

## Contribution Types

- **Topic proposal**: identify a missing project concept, workflow, or decision
  history that future agents need.
- **Raw source note**: add evidence to `docs/raw/` using `_SOURCE_TEMPLATE.md`.
- **Topic refresh**: run `python3 scripts/wiki_sync.py refresh <topic>` after raw
  source notes change.
- **Fact correction**: update stale dates, broken links, wrong assumptions, or
  missing context in raw notes and refresh the compiled topic.
- **Skill promotion**: when a wiki topic describes a repeated procedure, propose
  a `.agents/skills/` workflow.

## Quality Bar

A useful OAW wiki page is:

- **Concrete**: names files, commands, decisions, dates, measurements, or failure
  modes.
- **Source-backed**: links to `docs/raw/`, issues, PRs, reports, or another
  stable source of truth.
- **Small enough to route**: gives the agent the durable facts, not every chat
  transcript.
- **Cross-linked**: uses `related_topics` so agents can follow nearby knowledge
  without loading everything.
- **Actionable**: tells the next agent what to preserve, verify, or avoid.

Avoid generic summaries like "improve performance", "enhance reliability", or
"optimize the workflow" unless the page also says exactly what changed and how
to verify it.

## Standard Workflow

1. Pick a topic from `docs/wiki/TOPIC_BOARD.md` or open a topic proposal issue.
2. Add or update a source note in `docs/raw/`.
3. Refresh the compiled topic:

   ```bash
   python3 scripts/wiki_sync.py refresh <topic>
   ```

4. Verify the wiki:

   ```bash
   python3 scripts/wiki_sync.py lint
   python3 scripts/context_hub.py search "<topic keyword>"
   ```

5. If the refreshed topic describes a repeated process, suggest a skill
   promotion in the PR.

## PR Checklist

- [ ] The change keeps `docs/raw/` as the source layer and
      `docs/knowledge/` as the compact retrieval layer.
- [ ] New or changed topic pages have `id`, `title`, `page_type`,
      `last_updated`, and `related_topics`.
- [ ] Claims that may drift over time include a source ref or stable link.
- [ ] `python3 scripts/wiki_sync.py lint` passes.
- [ ] Repeated procedures are either linked to an existing skill or proposed as
      future skill candidates.
