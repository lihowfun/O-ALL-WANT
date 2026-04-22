# OAW Future Optimization Plan

Date: 2026-04-20
Author: synthesis of two grounding documents —
- `docs/archive/Taiwan_MD_Collaboration_Study.md` (wiki governance, 2026-04-19)
- `docs/archive/Harness_Engineering_Quality_Audit_2026-04-20.md` (6.7 / 10 audit)

Scope: merge decisions + prioritized roadmap for the next 6–8 weeks. Written
so the maintainer can pick up Monday morning and act without re-deriving.

## 0. North Star (the one sentence that decides everything below)

> **"Move OAW from well-routed agent instructions to an observable harness
> with evaluator and repair loops."** — Harness Engineering audit, §Final Judgment.

Every prioritization decision below ladders up to that one line. If an item
does not observably improve routing, evaluation, or repair, it drops in priority.

## 1. State of Play

| Surface | Current strength | Weakest point | Biggest unlock |
|---------|------------------|---------------|----------------|
| Information boundary | 8.0 | Lane compliance is honor-system | Lane audit log |
| Tool system | 6.5 | No structured output, no unified tool wrapper | `harness_check` + optional `--json` |
| Execution orchestration | 6.0 | Planner/generator/evaluator not separated | `harness-evaluator` skill |
| Memory + state | 8.0 | `task_state` has no CLI | Task-state CLI or skill |
| Evaluation + observability | 5.5 | No independent evaluator, no lane telemetry | Skill-frontmatter lint + quality scorecard |
| Constraints + recovery | 5.5 | Static guardrails only, no retry/rollback | Recovery pattern in skill template |
| Wiki governance | New in worktree | Not yet on main | Merge decision this week |

Strengths to protect: routing architecture, memory/state separation, deterministic
scripts, session-continuity evidence (86–87% context reduction), CI smoke tests.

## 2. Merge Decision — `llm-wiki-study` worktree

The worktree delivered all 8 artifacts listed in the LLM-wiki study:

| Artifact | Purpose | Risk of merging |
|----------|---------|-----------------|
| `docs/wiki/CONTRIBUTING_WIKI.md` | Explains `raw/` vs `knowledge/` vs `AI_CONTEXT` vs `memory` as distinct surfaces | Docs only; low |
| `docs/wiki/WIKI_PIPELINE.md` | Staged: gather → compile → verify → connect → promote | Docs only; low |
| `docs/wiki/TOPIC_BOARD.md` | Track topics in flight | Docs only; low |
| `docs/prompts/WIKI_TOPIC_PROMPT.md` | Public prompt to create a topic | Docs only; low |
| `docs/prompts/WIKI_REFRESH_PROMPT.md` | Public prompt to refresh | Docs only; low |
| `docs/prompts/WIKI_SKILL_PROMOTION_PROMPT.md` | Public prompt to promote repeatable procedure to skill | Docs only; low |
| `scripts/wiki_sync.py` lint extensions | Invalid dates, stale pages, thin topics, generic prose | Behavioral change — existing `lint` call stays green? Verify |
| Issue templates + PR checklist additions | `wiki_topic_proposal.yml`, `wiki_fact_correction.yml`, PR wiki rows | Low; purely GitHub UI |

### Recommended merge flow

1. **Pre-merge verification** (30 min):
   - Run `python3 scripts/wiki_sync.py lint` on the worktree — must be exit 0.
   - Run `python3 scripts/wiki_sync.py lint --strict` — should match the strict behavior already on `main`; the new checks (stale/thin/generic) should be `--strict`-only *or* emit warnings, not break default lint.
   - Sanity-check `example/minimal-project/scripts/wiki_sync.py` is byte-identical to `scripts/wiki_sync.py` (CI already guards this, but confirm locally).
2. **Single PR** titled `feat(wiki): LLM-wiki governance layer`.
   - Short summary + link to `Taiwan_MD_Collaboration_Study.md`.
   - Checklist in the PR description: "lint green", "`--strict` green", "example drift green", "preview the rendered `docs/wiki/` pages on GitHub".
3. **Explicit non-goals in the PR description** (so future reviewers know):
   - No website generation.
   - No i18n/translation dashboards.
   - No editorial scoring engine.
4. **Version bump**: `1.0.0 → 1.1.0` (minor — new public surface: `docs/wiki/`, `docs/prompts/`, new `wiki_sync.py lint` signals).
   - Previous "single user's feedback = don't bump to 1.1" concern does **not** apply here: this is a self-driven architectural investment, not a reactive feature for one integrator.

**Cost estimate**: 2–3 hours end-to-end, half of which is careful CHANGELOG wording.

## 3. Harness Engineering Gap Closure — Prioritized Roadmap

### P1 — High leverage, small scope (target: week 1–3 after wiki merge)

#### P1-1. `harness_check` one-command local gate (2–3h)

**Problem**: pre-PR verification today is "remember to run five things".

**Deliverable**: `scripts/harness_check.py` (or `context_hub.py health`) that runs in order:

1. `python3 -m py_compile scripts/context_hub.py scripts/wiki_sync.py`
2. `python3 scripts/wiki_sync.py lint`
3. Self-install refusal probe (`./install.sh`, expect non-zero + "Refusing")
4. Fresh-tempdir install, assert file set
5. Drift check: `example/minimal-project/scripts/*.py` must equal `scripts/*.py`

**Acceptance**:
- `./scripts/harness_check.py` exits 0 on a clean repo, prints a green summary.
- Any one step failing exits non-zero with which step failed.
- CONTRIBUTING.md links to it in the "before you open a PR" section.

**Why this first**: closes the audit's tool-layer gap (§2) with the cheapest ROI.
External contributors stop asking "did I run everything".

#### P1-2. `harness-evaluator` skill — planner/generator/evaluator split (3–4h)

**Problem**: same agent plans, executes, and evaluates its own work (§3 gap).

**Deliverable**: `templates/.agents/skills/harness-evaluator.md` with:
- `triggers`: "review this change", "evaluate PR", "is this ready to merge"
- Required reads: changed files + relevant lane + acceptance criteria block from the source skill
- Steps: restate goal → enumerate objective checks → run each → emit pass/fail per criterion → final verdict
- Outputs: verdict section in `.agents/memory.md` as `[REVIEW]` tag

**Acceptance**:
- Skill works against any other skill's "outputs" block as criteria.
- When invoked on a completed skill run, produces a concrete pass/fail/uncertain answer.
- Added to README's "You speak naturally" table: "Review this change" → `/harness-evaluator`.

**Why second**: single biggest qualitative lift, per audit §3 recommendation.

#### P1-3. Lane audit log (2h)

**Problem**: lane compliance is honor-system (§1 gap).

**Deliverable**: `context_hub.py audit` that appends a line to `.agents/lane_audit.log` whenever a lane is requested. Log line: timestamp + lane + files emitted. `.agents/lane_audit.log` is gitignored (same policy as `memory.md`).

**Acceptance**:
- Running `context_hub.py context --lane operational` appends a `[lane=operational files=...]` line.
- `context_hub.py audit --summary` shows lane frequency counts.
- Does not break any existing `context --lane` behavior.

**Why third**: enables future telemetry work, zero cost to users who ignore it.

#### P1-4. Skill frontmatter lint (1.5h)

**Problem**: skills rely on `triggers / requires / outputs` convention, but nothing enforces it (§5 gap).

**Deliverable**: extend `scripts/wiki_sync.py lint` (or new `scripts/skill_lint.py`) to check every `.agents/skills/*.md`:
- Has frontmatter with `triggers` + `outputs` fields
- Has a "Steps" section
- Has a "Verification" or "Acceptance" subsection (unless `_TEMPLATE.md` / README.md)

**Acceptance**:
- `wiki_sync.py lint` (or new subcommand) reports skills missing required fields.
- CI fails when a new skill lacks required structure.

**Why fourth**: cheap, prevents skill-quality regressions as the library grows.

### P2 — Bigger lifts (target: week 4–7)

#### P2-1. Recovery / retry / rollback conventions (1 day)

**Problem**: no retry/backoff, no rollback beyond "don't do destructive things" (§6 gap).

**Deliverable**: add a **"Recovery" section template** to `_TEMPLATE.md`:

```markdown
## Recovery

- **Retry conditions**: what triggers a retry (network flake? transient auth?)
- **Retry budget**: max attempts + backoff pattern
- **Unsafe to retry**: operations that must NOT retry (side-effectful writes, pushes)
- **Root cause record**: on final failure, write `[FAILURE]` entry to memory with what was tried
```

Plus a reference implementation: update `debug-pipeline.md` skill to use it.

**Acceptance**:
- `_TEMPLATE.md` includes the Recovery section.
- `debug-pipeline.md` demonstrates a working example.
- Skill frontmatter lint (P1-4) optionally requires a `Recovery` section for any skill that invokes `scripts/*` or external commands.

#### P2-2. Task-state CLI (3–4h)

**Problem**: `VERSION.json.task_state.in_progress` / `blocked` exist but have no CLI manipulation (§4 gap).

**Deliverable**: `context_hub.py task start <id>` / `task block <id> --reason "..."` / `task close <id>`.

**Acceptance**:
- Starts/blocks/closes a task id in `VERSION.json.task_state`.
- `context_hub.py status` surfaces current in-progress + blocked tasks.
- Skill templates (especially `experiment-report`, `version-release`) link to it.

#### P2-3. Optional `--json` on status/lint/search (3h)

**Problem**: tool output is human-prose, hard for machine evaluators (§2 gap).

**Deliverable**: accept `--json` on `context_hub.py status`, `context_hub.py search`, `wiki_sync.py lint`. Emit a stable schema.

**Acceptance**:
- `--json` output passes `jq .` for all three.
- Schema documented in `docs/CLI_Reference.md`.
- Existing non-JSON output unchanged.

**Why this tier**: enables a future evaluator agent to run locally, but not load-bearing yet.

#### P2-4. Worktree collaboration skill (1 day, contingent)

**Trigger**: only build this when multi-agent usage becomes frequent enough (≥3 people on a branch).

**Deliverable**: `templates/.agents/skills/worktree-coordinate.md` that codifies:
- When to fork a worktree (branch > 2 days of work, more than one agent)
- How to name worktree branches (`feat/<topic>`, `study/<topic>`, `audit/<topic>`)
- How to merge back (single clean commit? keep history? — your call, but decide once)
- Cleanup policy

### P3 — Research / deferred (target: beyond week 8)

| Item | Why deferred | Revisit trigger |
|------|-------------|-----------------|
| Runtime observability (telemetry, lane usage dashboards) | Needs real usage volume to be meaningful | ≥50 external installs |
| Independent evaluator **agent** (separate model/process) | Requires infra we don't have; skill-based evaluator (P1-2) covers 80% | Evaluator skill hits recognizable quality ceiling |
| Hard system-level rule interception (e.g. file-write policy gates) | Would require leaving markdown-first design | Real incident that markdown rules failed to prevent |
| Full quality scorecard with regression tracking | Premature before skill-frontmatter lint exists | After P1-4 ships |

## 4. Sequencing — Concrete 6-Week Calendar

Assuming 4–6 hours of OAW work per week (evenings / weekend).

| Week | Target | Definition of done |
|------|--------|-------------------|
| 1 | Merge `llm-wiki-study` as `v1.1.0` | Tag cut, CHANGELOG, release notes, README link to COMPARISON stays accurate |
| 2 | P1-1 `harness_check` + P1-4 skill frontmatter lint | One command green, CI uses it, CONTRIBUTING.md updated |
| 3 | P1-2 `harness-evaluator` skill | New skill file, README table updated, one real PR reviewed by the skill |
| 4 | P1-3 lane audit log | Command works, example in docs/CLI_Reference.md |
| 5 | P2-1 Recovery pattern in skill template | `_TEMPLATE.md` updated, `debug-pipeline.md` demonstrates it |
| 6 | P2-2 task-state CLI **or** P2-3 `--json` output — pick one | Whichever has higher near-term demand at that point |

## 5. Decisions Still Open (your call, not mine)

1. **Evaluator location**: separate skill (cheap, recommended above), separate *agent* (needs infra), or CI step (least agentic)?
2. **JSON schema stability**: if P2-3 ships, is `1.0` the stable contract, or `0.x` experimental until adoption?
3. **Wiki governance ownership**: after merge, do maintainers of `docs/wiki/*` need a separate `CODEOWNERS` entry?
4. **Audit log location**: gitignored local only (proposed), or opt-in commit for public repos to demonstrate routing discipline?

## 6. Anti-Patterns to Avoid (from recent history)

Recent lessons that should constrain the roadmap:

- **Do not ship a minor version bump based on a single integrator's feedback.**
  The wiki merge is an exception because the investment is self-driven and
  delivers its own internal justification (audit §7 roadmap impact).
- **Do not let the "six layers" list become a check-every-box obligation.**
  Audit scores below 6.0 in Evaluation (§5) and Constraints (§6) are the only
  layers where P1 work is *unambiguously* justified. Memory (8.0) and Information
  Boundary (8.0) do not need more engineering; they need more telemetry.
- **Do not rebuild routing before evaluator exists.** Router quality is already
  the strongest layer. Diminishing returns.

## 7. Success Criteria at End of Week 6

If this plan executes, at week 6 OAW should be able to honestly claim:

1. **Observability**: every lane request leaves a trail; you can answer "which
   lanes did this PR touch?" from a log.
2. **Independent evaluation**: any completed skill run can be reviewed by a
   second-pass skill that produces objective pass/fail per declared criterion.
3. **Single-command health**: external contributor can run one command to
   verify they didn't break the harness.
4. **Structured recovery**: every skill that calls external commands has an
   explicit retry/rollback/root-cause protocol documented in its frontmatter.
5. **Wiki governance**: raw → knowledge → skill promotion is a shipped pipeline,
   not a tribal convention.

The **6.7 / 10** audit score should move to roughly **7.8 / 10** — same
strengths, with Evaluation and Constraints layers both crossing 7.0.

## 8. What NOT in This Plan (deliberate exclusions)

- Public marketing / more README polish. The README was already rewritten for
  star-growth on 2026-04-19. Further copy tweaks are now below product work.
- New lanes. Four is enough. The audit's top gap is not "more lanes" but
  "prove agents actually use the four we have".
- A second memory layer. `task_state` + `memory.md` + `knowledge/` is the right
  shape; automation around them (§P2-2) beats invention.
- Cross-agent validation in CI. Worth doing eventually, but requires real
  Codex/Cursor/Windsurf test environments — not week 1–6 scope.

---

## Appendix A — Acceptance Test Templates

For each P1/P2 item, this is what "done" looks like when you show it to yourself.

### P1-1 `harness_check`

```bash
./scripts/harness_check.py
# Expected green output, exit 0

# Break something
echo "syntax error" >> scripts/wiki_sync.py
./scripts/harness_check.py
# Expected: FAIL on py_compile step, exit non-zero
git checkout scripts/wiki_sync.py
```

### P1-2 `harness-evaluator`

```text
You (to agent): Run /harness-evaluator against .agents/skills/benchmark.md
                using the last experiment from .agents/memory.md.
Expected:       Per-criterion pass/fail table + overall verdict written to
                .agents/memory.md as [REVIEW] tag.
```

### P1-3 Lane audit

```bash
python3 scripts/context_hub.py context --lane operational > /dev/null
python3 scripts/context_hub.py context --lane wiki > /dev/null
python3 scripts/context_hub.py audit --summary
# Expected output like:
#   lane=operational count=1
#   lane=wiki count=1
```

### P1-4 Skill frontmatter lint

```bash
echo "# Broken skill" > templates/.agents/skills/broken.md
python3 scripts/wiki_sync.py lint --strict
# Expected: non-zero exit, reports broken.md missing triggers/outputs
rm templates/.agents/skills/broken.md
```

### P2-1 Recovery pattern

Any skill frontmatter-linted after P1-4 that calls `scripts/*` commands
must have a non-empty `## Recovery` section; otherwise strict lint fails.

---

## Appendix B — Cross-References

- LLM-wiki study (source of §2): [Taiwan_MD_Collaboration_Study.md](Taiwan_MD_Collaboration_Study.md)
- Harness Engineering audit (source of §§3–5): [Harness_Engineering_Quality_Audit_2026-04-20.md](Harness_Engineering_Quality_Audit_2026-04-20.md)
- Current roadmap (will need update when §2 merges): `ROADMAP.md` on main
- Release cadence policy: `CONTRIBUTING.md` — especially the "don't bump minor on single-user feedback" rule

---

*Not pushed. Lives in the worktree until you approve + choose a merge strategy.*
