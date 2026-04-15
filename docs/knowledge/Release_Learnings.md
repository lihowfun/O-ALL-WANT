---
topic: release-learnings
page_type: knowledge
last_updated: 2026-04-16
confidence: high
source: v1.0.0 release reviews
related_topics:
  - Architecture_Decisions
---

# Release Learnings

Distilled patterns from OAW release reviews. Agent should read this before any version-release task.

## Pattern 1: Version Drift

**Problem**: `templates/VERSION.json` is the file users actually get after install. If you update root `VERSION.json` but forget `templates/`, every new user sees a stale version.

**Rule**: When bumping version, always update BOTH:
- `VERSION.json` (self-hosting)
- `templates/VERSION.json` (what users install)

## Pattern 2: Repo Rename Drift

**Problem**: After renaming a repo, metadata files (`AI_CONTEXT.md`, `VERSION.json`) may still reference the old name. Agents reading these files learn the wrong project identity.

**Rule**: After any repo rename, grep for the old name across all `.md` and `.json` files.

## Pattern 3: README Promise vs. Reality Gap

**Problem**: README describes features aspirationally ("Agent automatically does X"), but the actual harness may not enforce it.

**Rule**: Every README claim should be testable. If a feature is planned but not implemented, say "planned" explicitly.

## Pattern 4: Design Source Honesty

**Problem**: Citing inspiration sources without clarifying what was actually borrowed vs. what remains aspirational creates false expectations.

**Rule**: Use a "Borrowed / Not Yet Implemented" ledger for each design source.

## Pattern 5: Public Memory Policy

Public repos should NOT commit rolling `.agents/memory.md` (it contains session-specific noise). Instead:

| Surface | Committed? | Contains |
|---------|-----------|----------|
| `.agents/memory.md` | ❌ gitignored | Local development diary |
| `docs/knowledge/` | ✅ committed | Distilled, durable conclusions |
| `docs/archive/` | ✅ committed | One-time audit evidence |

The flow: memory entries accumulate locally → when patterns emerge → distill into knowledge pages → commit the knowledge page.
