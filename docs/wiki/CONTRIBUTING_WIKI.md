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
- [ ] If this change supersedes a prior entry, follow the **Deprecating an
      entry** section below.

## Deprecating an entry

When a past finding, baseline, or decision is superseded (benchmark corrected,
model retrained, paper retracted), mark the original entry instead of
deleting it. The audit trail is itself valuable.

### Template

Prepend the deprecation marker to the original entry's heading, then append
the three-line block:

```text
### [DEPRECATED 2026-04-17] Phase X — Finding Y

**Why**: <one-line reason — corrected benchmark, retracted source, new evidence>
**Replaced by**: <concrete pointer — e.g. "Phase Z" or "EXPERIMENT_LOG row 42">
**Lesson**: <one sentence — what future work should do differently>

<keep the original body below, unchanged>
```

### Rules

- **Do not delete** the original entry. Preserving the audit trail is the
  entire point.
- **Date the deprecation**, not the original entry. `[DEPRECATED YYYY-MM-DD]`
  is the date you marked it, not the date the original was written.
- **Point to the replacement** with a concrete locator (file + section, or
  EXPERIMENT_LOG row number).
- **State the lesson** in one sentence. If there's no lesson, you probably
  don't need to deprecate — just annotate.

### When NOT to deprecate

- Trivial updates (typo, stale date) → just edit.
- Entries nobody references → delete, don't deprecate.
- Failed experiments valuable as "we tried X, it didn't work" → keep with
  `[FAILURE]` tag; don't deprecate.

### Cross-reference updates

If you reference the deprecated entry from other pages, update those
references to the replacement at the same time. If you're uncertain whether
you caught them all, ask `/harness-evaluator` to run a subagent review.

## Evidence tiers (optional)

For projects with inherent uncertainty (research, measurements, sourced
claims), classify entries with one of the 5 evidence tiers from
`.agents/skills/classify-evidence.md`:

| Tier | Means | Typical home |
|:----:|-------|--------------|
| T1 | Hypothesis / work-in-progress | `.agents/memory.md` only |
| T2 | Single observation (needs `[CAVEAT]`) | memory / experiment log |
| T3 | Confirmed (≥ 2 independent reproductions/sources) | `docs/knowledge/` |
| T4 | Baseline (measured, with method) | `VERSION.json` + knowledge |
| T5 | Frozen (don't retest) | `VERSION.json.do_not_rerun` |

Tiers are **not enforced**. They are vocabulary that slows writers down
enough to pick the right word. If your project isn't claim-heavy (e.g. a
CLI tool or a docs repo without measurements), skip this section entirely.
