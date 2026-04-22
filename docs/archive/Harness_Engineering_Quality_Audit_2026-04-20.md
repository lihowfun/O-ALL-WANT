# Harness Engineering Quality Audit

Date: 2026-04-20

Scope: Objective review of OAW against the supplied Harness Engineering article.
This audit checks the current `taiwanmd-llm-wiki-study` worktree, including the
Taiwan.md-inspired LLM-wiki collaboration changes.

## Executive Summary

OAW is already a strong **context-routing and continuity harness**. It clearly
implements information boundaries, on-demand context exposure, rolling memory,
compiled wiki knowledge, and repeatable skill workflows.

OAW is not yet a full commercial-grade **self-healing execution harness**. The
weakest areas are independent evaluator roles, runtime observability, lane audit
trails, structured rule interception beyond wiki/docs checks, and automatic
recovery loops.

Overall score: **6.7 / 10**

| Layer | Score | Verdict |
|-------|-------|---------|
| Information boundary | 8.0 | Strong |
| Tool system | 6.5 | Good foundation, limited tool-result governance |
| Execution orchestration | 6.0 | Skills exist, but planner/evaluator separation is thin |
| Memory and state | 8.0 | Strong, especially for markdown-first workflows |
| Evaluation and observability | 5.5 | CI exists, but independent evaluation is limited |
| Constraints and recovery | 5.5 | Good static guardrails, weak automatic recovery |

## Article Claim: Prompt, Context, Harness

### Prompt Engineering

OAW does not position itself as prompt engineering, which is correct. The project
avoids one giant prompt blob and instead uses a router plus file-based context.

Evidence:

- `CLAUDE.md` defines router behavior and forbidden actions.
- `templates/AGENT_RULES.md` installs the same router pattern into user repos.
- README emphasizes session continuity, not prompt cleverness.

Assessment: **Implemented well.** OAW's product identity is correctly above the
prompt layer.

### Context Engineering

OAW's strongest layer is context engineering:

- `CLAUDE.md` routes by Operational / Wiki / Execution / Debug lanes.
- `AI_CONTEXT.md` stores project facts instead of behavioral instructions.
- `context_hub.py context --lane ...` exposes lane-specific context on demand.
- `docs/raw/` and `docs/knowledge/` separate raw evidence from retrieval pages.

Assessment: **Strong.** This is the clearest part of OAW.

### Harness Engineering

OAW partly reaches harness engineering:

- Skills define execution tracks.
- `VERSION.json` and `do_not_rerun` reduce repeated work.
- CI validates install and wiki integrity.
- `wiki_sync.py` prevents manual-page overwrite and catches wiki metadata drift.

The missing pieces are runtime control and recovery:

- No independent evaluator agent or evaluator skill is required.
- No audit trail records which lane/files an agent actually loaded.
- No generic retry/backoff/rollback mechanism exists for failed tool steps.
- Most harness rules are markdown instructions, not hard system intercepts.

Assessment: **Promising but incomplete.** OAW is a real harness, but currently
more deterministic context harness than self-healing execution harness.

## Six-Layer Harness Review

## 1. Information Boundary Layer

Article expectation: define role/goal, trim information, avoid context pollution.

OAW evidence:

- `CLAUDE.md` says `CLAUDE.md` is the only startup router and `AI_CONTEXT.md` is
  project facts, not a second rulebook.
- Startup forbids reading all markdown files.
- Lanes separate operational state, wiki knowledge, execution skills, and debug
  context.
- `docs/raw/` is explicitly fallback-only.
- `context_hub.py context --lane ...` can output a lane-specific file set.

Score: **8.0 / 10**

What is good:

- Clear boundaries are documented.
- The startup protocol is concise.
- The lane model directly addresses token pollution.
- New-project prompt now tells the agent to map real project state into
  `AI_CONTEXT.md`, not merely fill a template.

Gaps:

- Lane compliance is still mostly honor-system. There is no session-level
  record proving the agent only loaded lane-appropriate files.
- The root repo and installed template use slightly different canonical paths
  (`templates/docs/knowledge/` for self-hosting vs `docs/knowledge/` for users),
  which is correct but cognitively expensive.

Recommended next step:

- Add a lightweight lane audit log or `context_hub.py audit` command that records
  which lane was requested and which files were emitted.

## 2. Tool System Layer

Article expectation: manage tool timing and distill raw tool output before
feeding it back to the model.

OAW evidence:

- `context_hub.py` provides deterministic search, get, annotate, memory, status,
  bootstrap, setup, and lane context commands.
- `wiki_sync.py` deterministically compiles raw notes into knowledge pages.
- `--compact` exists for token-friendly status/search/bootstrap output.
- `wiki_sync.py lint` now checks required metadata, invalid dates, stale pages,
  broken links, missing refs, thin topics, and generic prose signals.

Score: **6.5 / 10**

What is good:

- The tools are standard-library Python and easy to run anywhere.
- `--compact` is a real token-efficiency feature.
- `wiki_sync.py` converts raw source notes into a smaller retrieval layer.

Gaps:

- Tool outputs are mostly human-readable text, not structured machine-readable
  JSON. That is fine for users, weaker for automated evaluators.
- There is no common wrapper for tool timeout, retry, or failure classification.
- There is no command that runs the full local harness health check in one step.

Recommended next step:

- Add `scripts/harness_check.py` or `context_hub.py health` that runs pycompile,
  wiki lint, install self-refusal, fresh install smoke, and example drift checks.
- Consider optional `--json` for status/lint results before building evaluator
  automation on top.

## 3. Execution Orchestration Layer

Article expectation: give the model tracks for understanding, analysis,
execution, and self-check instead of letting it improvise.

OAW evidence:

- `.agents/skills/*.md` define workflows such as benchmark, debug-pipeline,
  experiment-report, version-release, and wiki-refresh.
- Skill frontmatter defines triggers, required reads, optional reads, outputs,
  and steps.
- `CLAUDE.md` has a Skills-First Principle.
- Session end requires a four-section report.

Score: **6.0 / 10**

What is good:

- Skills are a good "thin harness / fat skills" implementation.
- Each skill has expected outputs and verification sections.
- Debug and release workflows reduce ad-hoc execution.

Gaps:

- Planner / generator / evaluator roles are not separated in the shipped
  harness. The same agent usually plans, executes, and evaluates.
- Skills are invoked by instruction, not by a hard dispatcher.
- The skill learning loop is documented as future behavior, but not automated.

Recommended next step:

- Add a `harness-evaluator` or `qa-review` skill that independently reviews a
  completed change against objective acceptance criteria.
- Add a simple "Plan → Execute → Verify → Record" skeleton to the skill template
  so every future skill follows the same lifecycle.

## 4. Memory And State Layer

Article expectation: separate current task state, intermediate results, and
long-term memory.

OAW evidence:

- `AI_CONTEXT.md` stores stable project facts.
- `.agents/memory.md` stores rolling decisions and findings.
- `docs/raw/` stores detailed source evidence.
- `docs/knowledge/` stores compiled durable knowledge.
- `VERSION.json` stores version, phase, task_state, benchmark snapshot, and
  `do_not_rerun`.
- File locking in `context_hub.py` reduces multi-agent memory write races.

Score: **8.0 / 10**

What is good:

- The memory/state surfaces are explicitly separated.
- `do_not_rerun` is a strong deterministic state-control primitive.
- Memory can be searched with `--include-memory`.
- The Taiwan.md-inspired wiki packet improves raw → knowledge → skill promotion.

Gaps:

- `task_state.in_progress` and `blocked` exist in `VERSION.json`, but there is
  no CLI workflow that manages them.
- The distinction between local `.agents/memory.md` and committed
  `docs/knowledge/` is good, but users may need clearer examples of when to
  promote memory into wiki.

Recommended next step:

- Add a state command or skill for starting, blocking, and closing tasks in
  `VERSION.json`.
- Add examples for "memory entry becomes raw source becomes knowledge topic".

## 5. Evaluation And Observability Layer

Article expectation: independent acceptance mechanisms and logs/monitoring so
the system knows whether it actually succeeded.

OAW evidence:

- GitHub Actions runs pycompile, CLI surface checks, wiki lint, self-install
  refusal, fresh install smoke, minimal-project drift, and strict placeholder
  detection.
- `docs/knowledge/OAW_Session_Continuity_Test.md` records measured 86-87%
  startup context savings.
- `wiki_sync.py lint` has objective pass/fail behavior.
- Release checklist and CI smoke tests exist.

Score: **5.5 / 10**

What is good:

- CI is practical and catches real regressions.
- The project has an actual session-continuity test report.
- `example/minimal-project` drift is now guarded.

Gaps:

- No independent evaluator role is required before landing changes.
- No lane usage telemetry exists.
- No "harness quality score" or regression trend exists.
- Most evaluation is repo/docs focused; execution skills do not have automated
  acceptance tests.

Recommended next step:

- Create a harness quality scorecard and run it in CI or as a local command.
- Add evaluator checks for skill files: required frontmatter, required verify
  section, required outputs, and required edge-case block.

## 6. Constraints And Recovery Layer

Article expectation: define what cannot happen, then provide automatic retry,
rollback, or corrective loops when failure occurs.

OAW evidence:

- `CLAUDE.md` and template router define forbidden actions.
- `install.sh` refuses self-install unless explicitly forced.
- `wiki_sync.py` refuses to overwrite manual pages with generated topics.
- `wiki_sync.py lint` blocks missing metadata and broken refs.
- CI blocks PRs that fail smoke checks.
- `VERSION.json do_not_rerun` stops repeated experiments.

Score: **5.5 / 10**

What is good:

- Static guardrails are clear.
- The installer has a real safety check.
- Wiki generation has overwrite protection.

Gaps:

- No generic retry/backoff rule for flaky commands or API failures.
- No rollback workflow exists beyond "do not use destructive commands".
- No structured "error reason + correction path" is automatically fed back into
  the next repair loop.
- Worktree isolation is used in practice, but not yet a first-class shipped
  skill or policy for multi-agent execution.

Recommended next step:

- Add a recovery pattern to the skill template: classify failure, retry only if
  safe, record root cause, and stop with a repair path when unsafe.
- Promote multi-agent worktree handling into a dedicated skill once the current
  branch settles.

## Practical Techniques From The Article

| Technique | OAW Status | Evidence | Recommendation |
|-----------|------------|----------|----------------|
| Context Reflect | Partial | `bootstrap`, memory, wiki, reports | Add handoff/reflect command that summarizes current task into memory + wiki candidate |
| On-demand Exposure | Strong | lanes, `context --lane`, skills, compact outputs | Add lane audit trail |
| Planner / Generator / Evaluator split | Weak | skill steps exist, but same agent usually owns all roles | Add evaluator skill and PR gate |
| Environment Validation | Medium | CI fresh install, lint, pycompile | Add one local `harness_check` command |
| Structured Rule Interception | Partial | wiki lint, self-install refusal, manual-page overwrite refusal | Extend to skills/frontmatter and architecture constraints |
| Automatic Recovery | Weak | debug skill documents diagnosis | Add retry/rollback/repair-loop conventions |

## Roadmap Impact

The roadmap should change. Star growth is still valid, but the next quality
investment should be **Harness Quality Hardening**, not more public-facing copy.

Recommended additions:

1. **P1 Evaluator and observability**
   - Add a `harness-evaluator` skill.
   - Add lane audit logging.
   - Add skill frontmatter/verification lint.

2. **P1 Local harness health command**
   - One command should run pycompile, wiki lint, install smoke, fresh install
     lint, and example drift checks.

3. **P2 Recovery loops**
   - Add retry/backoff/rollback guidance to the skill template.
   - Add a structured failure record format that includes root cause and next
     repair path.

4. **P2 Worktree collaboration skill**
   - Promote the current manual worktree practice into a reusable skill when
     multi-agent usage becomes frequent enough.

## Final Judgment

OAW has genuinely implemented the parts of Harness Engineering that matter for
context efficiency and session continuity. The 86-87% context reduction claim is
supported by the session-continuity report, and the architecture is coherent:
router, memory, wiki, skills, deterministic scripts, and CI all reinforce each
other.

The honest limitation is that OAW still relies on the agent's cooperation for
many rules. It tells the model what to do very well; it does not yet fully
observe, evaluate, intercept, and recover from bad execution. The next maturity
step is to move from "well-routed agent instructions" to "observable harness
with evaluator and repair loops."
