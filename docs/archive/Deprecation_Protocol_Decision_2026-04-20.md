# R-6: Deprecation Protocol — Skill vs Convention Decision

Date: 2026-04-20
Status: **Decided — ship as convention only. No skill.**
Source of question: [Future_Optimization_Plan_Amendment_v2_2026-04-20.md](Future_Optimization_Plan_Amendment_v2_2026-04-20.md) R-6

## The Research Question

GNN_explainer §3.4 proposed a `[DEPRECATED YYYY-MM-DD]` marker pattern for
entries that have been superseded. Two design options:

- **Skill** (`.agents/skills/deprecate-finding.md`): invoked via trigger, runs
  a multi-step workflow.
- **Convention** (section in `CONTRIBUTING_WIKI.md`): documented template
  users type by hand.

## Decision Criteria (from the Amendment)

> Skill if: deprecation has a repeatable multi-step workflow (find entry,
> move it, write replacement pointer, update cross-links)
>
> Convention if: it's one markdown section people type by hand

## Workflow Analysis

What does deprecating an entry actually require?

1. Locate the original entry (memory or knowledge page)
2. Add a `[DEPRECATED YYYY-MM-DD]` prefix
3. Add a structured "Why / Replaced by / Lesson" block
4. **Optional**: update cross-references in other pages
5. **Optional**: append an annotation to `EXPERIMENT_LOG.md`

Steps 1–3 are **straight markdown editing, 30 seconds of typing**. No
multi-tool dispatch needed.

Step 4 is the step that makes "skill" appealing — the claim is "an agent
might forget to update cross-references." But:

- In practice, cross-references to specific memory/knowledge entries are
  **rare** in OAW projects I've seen. Memory entries are mostly standalone.
- Knowledge pages that reference specific EXPERIMENT_LOG rows would need
  `ssot_mirrors`-style machine-readable links to be automatable. Manual
  cross-references can't be traced deterministically without an LLM pass.
- An LLM pass for every deprecation would be overkill; a subagent review
  via `harness-evaluator.md` (R-1) handles this if needed, on demand.

Step 5 is one additional markdown edit, no workflow needed.

## Decision

**Ship as convention only.** Add a "Deprecating an entry" section to
`docs/wiki/CONTRIBUTING_WIKI.md` with the template and rules.

**Do not ship a skill.** Reasons:

1. The workflow is 3 lines of markdown, not a multi-tool dispatch.
2. The "forgot cross-refs" risk is better solved by the existing
   `harness-evaluator` skill (R-1) if a reviewer asks for it — don't
   build an automation for a risk we haven't measured.
3. The minimalism budget is better spent elsewhere (B-1–B-5 all actually
   shipped code).
4. If users report "I keep forgetting step N," revisit and convert to a
   skill at that point. Not before.

## What Ships

### `docs/wiki/CONTRIBUTING_WIKI.md` — add a new section

```markdown
## Deprecating an entry

When a past finding, baseline, or decision is superseded (benchmark corrected,
model retrained, paper retracted), mark the original entry instead of
deleting it. The audit trail is itself valuable.

### Template

Prepend the deprecation marker to the original entry's heading, then append
the three-line block:

```text
### [DEPRECATED 2026-04-17] Phase X — Finding Y

**Why**: <one-line reason — corrected benchmark, retracted source, new evidence, etc.>
**Replaced by**: <pointer to the replacement, e.g. "Phase Z" or "EXPERIMENT_LOG 2026-04-19">
**Lesson**: <one sentence — what future work should do differently>

<keep the original body below, unchanged>
```

### Rules

- **Do not delete** the original entry. The point of deprecation is preserving the
  audit trail.
- **Date the deprecation**, not the original entry. `[DEPRECATED YYYY-MM-DD]` is the
  date you deprecated it.
- **Point to the replacement** with a concrete locator (filename, section, EXPERIMENT_LOG row).
- **Note the lesson** in one sentence. If there's no lesson, you probably
  don't need to deprecate — just annotate.

### When NOT to deprecate

- Trivial updates (typo, stale date) → just edit.
- Entries nobody references → delete, don't deprecate.
- Failed experiments that were valuable as "we tried X, it didn't work" →
  keep as-is with `[FAILURE]` tag; don't deprecate.

### Cross-reference updates

If you reference the deprecated entry from other pages, update those
references to the replacement at the same time. If you're not sure whether
you hit all cross-references, ask `/harness-evaluator` to confirm.
```

## Acceptance

- Section above added to `docs/wiki/CONTRIBUTING_WIKI.md`
- No new skill file
- Mention in CHANGELOG under Changed (not Added) — "formalized existing
  behavior" rather than "new capability"
- `/harness-evaluator` skill references the deprecation convention as a
  check it can run

## North-Star Check

- **Simple**: yes — 3 lines of markdown, no tooling.
- **Smart**: yes — preserves audit trail, points to replacement.
- **Self-evolving**: yes — the convention itself is the evolution pattern.
- **Not over-engineered**: yes — rejected the skill option explicitly.

Pass on all four.

## When To Revisit

Promote to a skill if **both** conditions appear:
1. ≥ 3 users independently ask "I keep forgetting to update cross-references"
2. The `harness-evaluator` skill reports "missed cross-reference" in ≥ 5 reviews

Until then: convention-only.

---

*Decided 2026-04-20. Supersedes the "R-6 research" placeholder in Amendment v2.*
