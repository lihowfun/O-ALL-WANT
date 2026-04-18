---
id: OAW_Session_Continuity_Test
title: OAW Session Continuity — Test Report
page_type: topic
build_origin: manual
last_updated: 2026-04-18
related_topics:
  - Harness_Engineering_Context_Fragmentation
  - Harness_Engineering_Deterministic_State
  - Harness_Engineering_Knowledge_Synthesis
---

# OAW Session Continuity — Test Report

> Tested: 2026-04-18 | Environment: macOS Darwin 24.6.0, fresh git repo, OAW install.sh
> Test project: `/tmp/oaw-test-project` | OAW source: `/Users/akuo/Documents/agent_memory/repo`

## Summary

| Session | Difficulty | Result | Key Finding |
|---------|-----------|--------|-------------|
| 0 | Cold start | ⚠️ Partially | CLAUDE.md routing table is clear, but all project-identity fields are `${...}` placeholders — agent cannot orient to *this* project |
| 1 | Memory continuity | ✅ Yes | All 3 entries persisted; `status` shows last 3; `memory show` shows all; gap: `search` does not scan memory.md |
| 2 | Wiki persistence | ✅ Yes | `wiki_sync.py refresh` compiled raw → wiki in one command; `search "session cookies"` found the topic; `status` listed it |
| 3 | Lane routing efficiency | ✅ Yes | Each lane uses ~3,000 tokens vs 22,583 for loading everything — 86-87% savings; but lane boundaries exist only in CLAUDE.md prose, with no CLI enforcement |

---

## Session 0 — Cold Start Baseline

**Test**: Simulate what a brand-new AI agent sees on first open.

### CLI Output — `context_hub.py status`

```
======================================================================
  PROJECT STATUS
======================================================================

  VERSION: ${VERSION}
  DO NOT RERUN: 0 experiments locked
  CURRENT PHASE: ${CURRENT_PHASE}

  RECENT DECISIONS (last 3)
  ----------------------------------------
    ## [2026-01-15] [DECISION] Initialized agent memory system

  KNOWLEDGE TOPICS
  ----------------------------------------
    Architecture_Decisions
    Experiment_Findings
    Known_Limitations
    Performance_Baselines
```

### CLAUDE.md — First 30 Lines

```
# ${PROJECT_NAME} — Master Router

> Replace `${PROJECT_NAME}`, `${LANGUAGE}`, and the custom forbidden-action
> placeholders before first use. Keep the rest of the structure intact unless
> your workflow truly needs a different policy.

## Router Contract ...
## Response Language ...
## Session Startup (Read On Demand — NOT Everything)
...
| Lane | Use When | Read First | Fallback |
|------|----------|------------|----------|
| Operational | Current state, ...   | ROADMAP.md first 60 lines + .agents/memory.md last 5 entries | ... |
| Wiki | Stable concepts, ...  | docs/knowledge/index.md + relevant topic page(s) | ... |
| Execution | Repeating workflows  | Matching file in .agents/skills/ | ... |
| Debug | Reproducing failures  | docs/knowledge/Known_Limitations.md | ... |
```

### AI_CONTEXT.md — First 20 Lines

All project-identity fields are `${...}` placeholders:
- `${PROJECT_NAME}`, `${ONE_LINE_DESCRIPTION}`, `${VERSION}`, `${REPO_URL}`, `${PIPELINE_SUMMARY}`
- `${LANGUAGE}`, `${SAFETY_CRITICAL_FILE}`, `${IMPORTANT_WORKAROUND}`
- Metric table: `${METRIC_1}`, `${VALUE_1}`, `${DATE}`, `${NOTES}`
- Test commands: `${SMOKE_TEST_CMD}`, `${REGRESSION_TEST_CMD}`, `${INTEGRATION_TEST_CMD}`
- Stack: `${LANGUAGE_AND_FRAMEWORKS}`, `${RUNTIME_ENVIRONMENT}`, `${EXTERNAL_SERVICES}`

### VERSION.json

```json
{
  "version": "${VERSION}",
  "project": "${PROJECT_NAME}",
  "last_updated": "${DATE}",
  "current_phase": "${CURRENT_PHASE}",
  "next_phase": "${NEXT_PHASE}",
  "do_not_rerun": [],
  ...
}
```

### Analysis

**Grade: ⚠️ Partially**

- **What works**: The routing table in CLAUDE.md is immediately legible. Lane routing (Operational / Wiki / Execution / Debug) is well-structured. The `do_not_rerun` field is present and empty, correctly signaling no locked experiments. `context_hub.py status` runs cleanly and outputs a parseable summary in under 2 seconds.
- **What fails**: A fresh agent cannot answer "what project is this?" or "what phase are we in?" All identity fields are `${...}`. The `status` output shows `VERSION: ${VERSION}` and `CURRENT PHASE: ${CURRENT_PHASE}`. A real agent forced to read this would either hallucinate project identity or ask the user — a friction point that could have been avoided with a post-install setup step.
- **60-second orientation**: The harness structure is discoverable in 60 seconds. The *project context* is not, because placeholders were never filled.
- **Minor positive**: `context_hub.py bootstrap` outputs a structured one-shot dump that would give a new agent all routing context, memory, and knowledge topics in a single command — an excellent session-start primitive.

---

## Session 1 — Memory Continuity (Easy)

**Test**: After one day of work, verify a new session agent can pick up where the previous session left off.

### Commands Run

```bash
python3 scripts/context_hub.py memory add "[DECISION] 2026-04-18 Switch auth from JWT to session cookies — JWT refresh complexity too high"
python3 scripts/context_hub.py memory add "[BUG] 2026-04-18 N+1 query in UserList endpoint — added select_related, fixed"
python3 scripts/context_hub.py memory add "[FINDING] 2026-04-18 Redis cache hit rate 94% after adding 5min TTL to product queries"
```

### CLI Output — `status` (after entries added)

```
  RECENT DECISIONS (last 3)
  ----------------------------------------
    ## [2026-04-18] [FINDING] 2026-04-18 Redis cache hit rate 94% after adding 5min TTL to product queries
    ## [2026-04-18] [BUG] 2026-04-18 N+1 query in UserList endpoint — added select_related, fixed
    ## [2026-04-18] [DECISION] 2026-04-18 Switch auth from JWT to session cookies — JWT refresh complexity too high
```

### CLI Output — `search "auth"`

```
Searching for 'auth' in /private/tmp/oaw-test-project/docs/knowledge...
No matches found. Try broadening the search.
```

*(Search only scans `docs/knowledge/`, not `.agents/memory.md`.)*

### `memory show --last 5` — Full Output

All 4 entries returned correctly, including the original "Initialized agent memory system" entry with full body text. The rolling log format is intact and parseable.

### Analysis

**Grade: ✅ Yes — with a notable gap**

- **What works**: All entries persist to `.agents/memory.md` correctly. The `status` command shows the last 3 entries so a new session agent immediately sees recent decisions. `memory show --last 5` retrieves the full rolling log. `bootstrap` combines memory + knowledge + AI_CONTEXT.md in one command.
- **Gap — search does not scan memory.md**: `search "auth"` returns nothing because `context_hub.py search` only scans `docs/knowledge/*.md`. A user who saved `[DECISION] Switch auth from JWT...` in memory cannot retrieve it via the search CLI without knowing to use `memory show` separately. This is a discoverability gap: two separate stores with no unified search.
- **Minor UX issue — date redundancy**: The `memory add "[DECISION] 2026-04-18 Switch auth..."` command auto-prepends a timestamp to the heading (`## [2026-04-18] [DECISION] 2026-04-18 Switch auth...`), leaving the date duplicated in the stored entry title. Harmless but noisy.
- **Positive**: The `bootstrap` command is the strongest session-continuity primitive. It outputs AI_CONTEXT.md + last 5 memory entries + knowledge topic index in one shot — a new session agent using `python3 scripts/context_hub.py bootstrap` gets ~80% of project context in one command.

---

## Session 2 — Wiki Persistence (Medium)

**Test**: Create a raw note, compile it to wiki, and verify a subsequent session can find it.

### Raw Note Created

`docs/raw/auth_strategy.md` — frontmatter with `id: auth_strategy`, `title: Auth Strategy Decisions`, `related_topics: [security, session_management]`

### Commands Run

```bash
python3 scripts/wiki_sync.py refresh auth_strategy
# Output: ✅ Refreshed topic 'auth_strategy'.
```

### CLI Output — `search "session cookies"`

```
Searching for 'session cookies' in /private/tmp/oaw-test-project/docs/knowledge...

MATCHING KNOWLEDGE TOPICS (1 found)
  Topic ID                       | Annotations | Description
  auth_strategy                  |             | auth strategy
```

### CLI Output — `status` (after wiki refresh)

```
  KNOWLEDGE TOPICS
  ----------------------------------------
    Architecture_Decisions
    Experiment_Findings
    Known_Limitations
    Performance_Baselines
    auth_strategy

  RAW SOURCES: 1 file(s) in docs/raw/
```

### Compiled Wiki Output

`docs/knowledge/auth_strategy.md` was created with correct frontmatter (`build_origin: wiki_sync`, `source_refs`, `related_topics`). Content preserved the raw note body and added a `## Summary` section with a one-line extract.

### Additional Finding — `wiki_sync lint` Output

Running `wiki_sync.py lint` revealed:
- **30 soft warnings**: Unfilled `${...}` placeholders in all 4 pre-installed knowledge templates (`Architecture_Decisions.md`, `Experiment_Findings.md`, `Known_Limitations.md`, `Performance_Baselines.md`) — every template ships with literal placeholder text that lint flags as unresolved.
- **2 hard errors**: `broken related topic in auth_strategy.md: security` and `broken related topic in auth_strategy.md: session_management` — the lint tool validates that `related_topics` references must correspond to actual knowledge topic files, but `security` and `session_management` don't exist as compiled wiki pages. This is a false positive for a fresh install: the raw note's related topics are free-form strings, not OAW topic IDs.

### Analysis

**Grade: ✅ Yes — with lint friction**

- **What works**: Raw → wiki compilation is a single command. The compiled file is immediately searchable via `search`. The `status` output counts raw sources and lists knowledge topics, so a next-session agent can see the topic without reading the directory. Full-text search within the compiled page works correctly (both `"session cookies"` and `"JWT"` found the `auth_strategy` topic).
- **Gap — lint false positives at install**: `wiki_sync lint` exits 1 on a fresh install due to 30 unfilled template placeholders. This means agents using lint as a "green means ready" signal will always see red on a stock install — undermining lint's value as a health check. The pre-installed knowledge template files should either ship without placeholder content or the lint tool should have a `--strict` flag that skips template detection.
- **Gap — related_topics validation too strict**: The `broken related topic` error treats all `related_topics` values as OAW topic IDs. Raw notes may reference concepts (`security`, `session_management`) that don't correspond to knowledge files. Lint should either warn (not error) on this, or the wiki_sync template should document that `related_topics` must be valid topic IDs.

---

## Session 3 — Lane Routing Efficiency (Hard)

**Test**: Quantify how much context each lane loads vs loading everything.

### File Counts Per Lane

| Lane | Files Loaded | File List |
|------|-------------|-----------|
| Operational | 4 | `CLAUDE.md` + `AI_CONTEXT.md` + `ROADMAP.md` (first 60L) + `.agents/memory.md` (last 5 entries) |
| Wiki | 4 | `CLAUDE.md` + `AI_CONTEXT.md` + `docs/knowledge/index.md` + 1 relevant topic page |
| Execution | 3 | `CLAUDE.md` + `AI_CONTEXT.md` + 1 matching skill file |
| Everything | 25 | All `.md`, `.json`, `.py` files across the project |

### Skill Files Available (Execution Lane)

8 files in `.agents/skills/`: `README.md`, `_TEMPLATE.md`, `benchmark.md`, `debug-pipeline.md`, `experiment-report.md`, `self-improving.md`, `version-release.md`, `wiki-refresh.md`

### Token Estimates (chars ÷ 4)

| Lane | Chars Loaded | Approx Tokens | Savings vs Everything |
|------|-------------|--------------|----------------------|
| Operational | 11,909 | ~2,977 | 78,423 chars (86%) |
| Wiki | 11,568 | ~2,892 | 78,764 chars (87%) |
| Execution | 12,551 | ~3,137 | 77,781 chars (86%) |
| Everything | 90,332 | ~22,583 | — |

> Note: `CLAUDE.md` (4,790 chars) + `AI_CONTEXT.md` (4,588 chars) = 9,378 chars baseline always loaded. The routing-specific files add only 1,500–3,200 chars per lane. As the project grows with more raw notes, wiki pages, and skills, the savings percentage will increase further.

### Analysis

**Grade: ✅ Yes — routing is structurally sound, but enforcement is implicit**

- **What works**: The lane routing math is compelling. Each lane uses ~3,000 tokens compared to 22,583 for loading everything — an 86-87% reduction. As the project accumulates more wiki pages and raw notes, the "load everything" cost grows while each lane's cost stays near-constant (it reads a subset by design). This is the correct architecture for AI cost management.
- **Gap — routing is prose-only in CLAUDE.md**: There is no CLI command like `context_hub.py context --lane operational` that auto-outputs only the Operational lane's files. The lane routing is purely a CLAUDE.md instruction that the AI agent must interpret and follow. Different AI models or inattentive agents may load more than needed. A CLI shortcut for lane-based context loading would make the savings automatic rather than aspirational.
- **Gap — no lane enforcement metrics**: There's no way to verify after the fact which files an agent actually loaded in a session. The harness can specify routing policy but cannot audit compliance.
- **Positive**: `context_hub.py bootstrap --compact` provides a minimal token-efficient session starter that approximates the Operational lane's output without requiring the agent to know about lane routing at all.

---

## OAW Improvement Suggestions

Based on test findings, prioritized list of improvements. **Items marked ✅ were shipped in the 2026-04-18 follow-up commit.**

| Priority | Issue | Fix | Status |
|----------|-------|-----|--------|
| P0 | Fresh install: every file shows `${VERSION}` / `${CURRENT_PHASE}` placeholders — agent cannot orient | `context_hub.py setup` — audits every unfilled `${...}` in CLAUDE.md, AI_CONTEXT.md, VERSION.json, ROADMAP.md with line numbers, prompts the agent to fill them | ✅ Shipped |
| P0 | `search` only scans `docs/knowledge/` — decisions in `.agents/memory.md` invisible | `search --include-memory` flag scans memory entries alongside the wiki | ✅ Shipped |
| P1 | `wiki_sync lint` exits 1 on fresh install due to 30 unfilled template placeholders | Shipped template pages now tagged `build_origin: template`; lint's placeholder scanner skips them | ✅ Shipped |
| P1 | `related_topics` in raw notes treated as OAW topic IDs — fails with "broken related topic" for free-form concepts | Downgraded from error to warning (`unresolved related topic`) | ✅ Shipped |
| P1 | No CLI shortcut for lane-based context loading — routing is prose-only | `context_hub.py context --lane [operational\|wiki\|execution\|debug]` outputs the correct file set for each lane | ✅ Shipped |
| P2 | Date redundancy: `memory add "[DECISION] 2026-04-18 ..."` produced `## [2026-04-18] [DECISION] 2026-04-18 ...` with date duplicated | `memory_add` now strips leading `YYYY-MM-DD` from the note body | ✅ Shipped |
| P2 | `wiki_sync refresh` lowercased the compiled title (`auth strategy` instead of `Auth Strategy Decisions`) | `_render_topic_page` now prefers the raw source's `title` field | ✅ Shipped |
| P2 | No lane audit trail — cannot verify which files an agent actually loaded | Add optional `context_hub.py audit log [lane]` command | Open |

---

## Conclusion

OAW's session continuity architecture is structurally sound. The three-lane routing model delivers measurable token savings (86-87% reduction vs loading everything), the raw→wiki compilation pipeline works reliably in one command, and the rolling memory log persists correctly between sessions. The `bootstrap` command is particularly effective as a session-start primitive, giving a new agent project context, recent decisions, and knowledge topic index in a single output.

The two most significant gaps are both P0: first, a fresh install leaves all project identity fields as `${...}` placeholders, making it impossible for an agent to orient to the specific project without human setup intervention; second, the `search` command only scans the compiled wiki and misses decisions stored in `.agents/memory.md`, creating two separate stores with no unified retrieval. Closing these two gaps would make OAW genuinely self-orienting out of the box.

The P1 lint false positives are a credibility risk: if agents use lint as a health signal and always see 30 warnings + 2 errors on a fresh install, they will learn to ignore lint output — which defeats the tool's purpose. Shipping cleaner templates or adding a `--strict` mode would restore lint's signal value.
