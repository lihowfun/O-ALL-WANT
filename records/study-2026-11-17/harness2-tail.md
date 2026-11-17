**1. Pipeline, records, budgets, and resume**

The order is: `k` shared base executions → invariant/domain proposals → candidate probes → compositions and their executions → blind selection → reflection/library update → separate judging → reporting. Parallel mode draws `k` candidates per scope, then `k` compositions; sequential mode carries the composed harness and accumulated evidence through `k` steps. Selection uses exactly the `k` composed finals; at `k=1` it needs no selector session. (`docs/EXPERIMENTS.md:8–19`; `harness2/core/schedule.py:543–588,634–639`)

A task summary keeps task/domain, budget, seed, input digest, base-run locations, mode records, selections, and errors. A `RunView` keeps label, run ID/directory, execution/delivery status, cost/wall-time fields, and error—“Never carries a score.” Candidate-stage records retain dimension, fallback/base-retention flags, execution failure, attempts, USD, cache status, notes, and error; harness trees and evidence are materialized separately. (`harness2/core/schedule.py:240–264`; `harness2/core/spec.py:176–187`; `harness2/core/recursion.py:84–110,282–287`)

The context contains task/source material, trajectories, deliverables, current harness, earlier library entries, decision notes, and candidate harness diffs. Whole trajectories remain available; individual observations default to 50,000 characters. (`harness2/core/context.py:105–187,290–330`; `harness2/core/spec.py:148`)

The ledger enforces **R=4k**: `k` bases + `2k` candidate probes + `k` finals; **P=3k** improvement stages. It rejects duplicate labels, records cached flags and invocation attempts, and separates rollout/session USD. Selection/reflection sit outside it. Thus rejected candidates still consume rollout/stage counts. (`harness2/core/ledger.py:15–33,40–64,89–132`)

Invalid proposals receive one repair attempt with rejection feedback and retain previous edits; exhausted validation inherits the current harness. Transport failures have two attempts and mark execution failure. Costs accumulate across rejected attempts and outages. Defaults: phase width two, proposer concurrency two, one concurrent domain; judging uses eight workers. (`harness2/core/recursion.py:36–38,187–261`; `harness2/config.py:175–179`; `harness2/cli/run_sweep.py:56`; `harness2/core/judge.py:103–110`)

**Accounting limitation:** rollout ledger calls omit USD, leaving zero defaults. The report adds every stage’s USD plus selection/reflection USD, including unsuccessful edits; it labels this **improver spend**, not total benchmark expenditure. LAB separately records rollout tokens, cost, duration, tools, and document coverage. Cached proposer replies report zero incremental cost. (`harness2/core/recursion.py:310,349`; `harness2/core/ledger.py:58`; `harness2/cli/report.py:37–55,104–109`; `third_party/lab_runner/opencode/run_opencode.py:315–334`; `harness2/core/proposer.py:344–352`)

Stage-call caching fingerprints mission, system text, evidence bytes, and context path. Rollout completion markers record version, run ID, timestamp, harness digest, and optional task-input digest; legacy markers without input identity remain reusable. Summary resume also checks requested modes, selected output, harness, and available artifact fingerprints. (`harness2/core/proposer.py:500–527`; `harness2/core/runmark.py:93–159`; `harness2/core/schedule.py:408–463`)

Reports contain graded/ungraded counts, mean score, LAB all-pass, pick provenance, and fallback counts. They warn about mixed scoring units and call the parallel/sequential `k=1` gap a “NOISE FLOOR.” Judge failure is missing data, excluded from the denominator, rather than zero. (`harness2/core/report.py:80–110,122–163`; `harness2/core/judge.py:15–18,32–34`)

**2. Tasks, partitions, judging, and isolation**

Tasks are discovered locally: LAB practice-area/task JSONs; JobBench occupation/task instruction folders; WorkBuddy office/web/code task directories, grouped by category or code role. The guide states LAB has 1,143 tasks. (`harness2/benchmarks/tasks.py:26–51`; `docs/EXPERIMENTS.md:46–48`)

The optional splitter defaults to seed 42 and 50% train, shuffles independently per domain, floors each domain’s train count, and refuses overwrite. Selection validates duplicates, overlap, benchmark identity, and unknown IDs. Default execution uses all installed tasks. **Inference:** “test” is a task filter, not a frozen held-out evaluation: the same improvement sweep receives whichever split is selected. (`scripts/split_tasks.py:33–60`; `harness2/benchmarks/tasks.py:62–88`; `harness2/cli/run_sweep.py:159–172`)

Execution seeds shuffle sorted domains and each domain’s sorted tasks independently; they do **not** control model sampling. Anonymous candidate ordering uses a separate deterministic task/budget/mode hash. (`harness2/core/schedule.py:135–161`; `docs/EXPERIMENTS.md:28`; `harness2/core/selection.py:71–76`)

LAB uses upstream criterion judging and reports partial/all-pass; JobBench uses weighted rubric points, with an explicitly labelled unweighted fallback. WorkBuddy declares rule scoring for code, LLM judging for web, rubrics for office, then reads verifier `score.json`. Judge IDs are user-configured; WorkBuddy setup requires Gemini routes. (`docs/BENCHMARKS.md:34–38,64–68,103–110`; `harness2/benchmarks/jobbench.py:597–624`; `harness2/benchmarks/workbuddy.py:84–108,986–1003`)

Shipped patches add JobBench reasoning-effort control and reject empty completions; LAB adds Vertex Anthropic support, four judge attempts, conflicting-verdict rejection, and nested deliverable paths. WorkBuddy patches refresh credentials and preserve Gemini thought signatures. (`third_party/patches/job-bench-eval-judge.diff:9–39`; `third_party/patches/harvey-labs-judge-vertex-anthropic.diff:28–35,49–55,181–187,235–240`; `third_party/patches/workbuddy-bench-runtime.diff:33–40,143–149`)

Scoring material is filtered: LAB removes `criteria`; JobBench excludes rubric/reference paths; WorkBuddy excludes tests/solutions/environment and admits only specified agent-artifact locations. Context checks reject answer-key paths and grader-verdict content. WorkBuddy code gives proposers filenames only. (`harness2/benchmarks/lab.py:569–600`; `harness2/benchmarks/jobbench.py:518`; `harness2/benchmarks/workbuddy.py:91–108,666`; `harness2/benchmarks/wb_render.py:33–85`; `harness2/core/context.py:167–169`)

JobBench isolates workspaces, npm/Python user installs, and temporary files, resetting them before retries; WorkBuddy uses fresh containers. **Network isolation is absent:** “The release does not restrict network access.” The guide reports a Codex rollout independently downloading its rubric and instructs users to apply external host restrictions; Codex’s sandbox is disabled. (`harness2/benchmarks/jb_opencode_runner.py:147–175,295–325`; `docs/BENCHMARKS.md:119–122`; `docs/EXPERIMENTS.md:95–109`)

**3. Editable harness and baselines**

The JobBench manifest distinguishes editable harness files from frozen CLI/tool/provider infrastructure; context assembly/compaction is not injectable. (`third_party/jb_runner/harness_baseline_oc/harness.yaml:1–18`)

OpenCode permits four always-on prose files—system prompt, guardrails, memory, tool guidance—plus skills and skill scripts, Python helpers, sub-agent definitions, and TypeScript plugins; always-on content caps at 24,000 characters. Codex permits `AGENTS.md` (8,000 characters), `.agents/skills`, helpers, and `.codex/hooks.json`. Path escapes/off-surface files are rejected; validation checks skill triggers/frontmatter, scripts, references, hooks, and deployment-specific sub-agent availability. (`harness2/substrate/opencode.py:42–63`; `harness2/substrate/codex.py:39–74`; `harness2/core/tree.py:64–110,301–389`)

Sub-agents are enabled only for OpenCode JobBench/WorkBuddy, disabled for LAB. (`harness2/benchmarks/jobbench.py:519`; `harness2/benchmarks/workbuddy.py:664`; `harness2/benchmarks/lab.py:508`)

JobBench OpenCode’s baseline prose is comment-only, with no defined helpers/sub-agents/plugins; Codex’s baseline simply follows instructions and writes deliverables. WorkBuddy similarly starts with empty OpenCode additions or minimal Codex instructions; its runner installs components into runtime locations and commits Codex harness installation before agent work. (`third_party/jb_runner/harness_baseline_oc/systemprompt.md:1–4`; `guardrails.md:1`; `LongTermMEMORY.md:1`; `tool_descriptions/tool_guidance.md:1`; `scripts/README.md:7`; `sub_agents/README.md:4`; `plugin/README.md:26`; `third_party/jb_runner/codex_base_harness/AGENTS.md:1–2`; `harness2/benchmarks/workbuddy.py:892–921`; `third_party/wb_runner/agents/codex_harness_agent.py:55–75`)

LAB instead includes upstream prompt/manuals, document helpers, output-path instructions, and a base tool gate; its runtime document reader overrides harness copies. (`third_party/lab_runner/opencode/render.py:35–78`; `third_party/lab_runner/opencode/run_opencode.py:60–78`; `third_party/lab_runner/adapt_runs_cx/run_codex_lab.py:104–132`)

**4. Tests: failures guarded against**

These are source assertions, not executed results:

- `tests/test_baseline_judge.py:97–139`: missing numerator/invalid denominator becoming valid baseline or selected scores.
- `tests/test_env_example.py:68–93`: broken example configuration or lost shell precedence.
- `tests/test_jobbench_killed_rollout.py:99–153`: missing timeout/crash/signal evidence, including preserved partial outputs.
- `tests/test_jobbench_rollout_isolation.py:123–161`: shared installation/temp state, dirty retries, broken PATH or workspace fences.
- `tests/test_jobbench_worker_failure.py:171–205`: worker/transport failures becoming zero or partial grades.
- `tests/test_lab_judge_patch.py:166–202`: conflicting verdicts producing cached scores.
- `tests/test_lab_nested_deliverables.py:189–208`: losing nested paths or conflating identical basenames.
- `tests/test_proposer_failures.py:67–119,163–225`: outages appearing successful, invalid fallbacks becoming unresumable, lost retry costs.
- `tests/test_proposer_session_errors.py:30–92`: accepting partial answers after session errors or losing spend.
- `tests/test_requested_mode_resume.py:29–64`: unrelated failed modes blocking valid requested-mode resume.
- `tests/test_runner_seed.py:121–149`: seeds failing to reach judging/reporting.
- `tests/test_stage_retry.py:71–84`: repair retries discarding earlier valid edits.
- `tests/test_subprocess_env.py:35–95,186–233,251–297`: credential leakage or removal of required provider credentials.
- `tests/test_task_input_identity.py:58–112,159–188,267–294`: stale reuse after changed instructions/source files, with legacy compatibility.
- `tests/test_workflow.py:50–185,208–311`: budget/evidence/library-prefix violations, failed selection judging, stale selections/grades.

**5. Running and paying**

Documented installation uses `uv`, editable installation with rendering extras, then optional credential-free deterministic demo. Benchmark workflow is setup → check → refinement → judge → report. Linux/Python 3.12 is recommended; package support is `>=3.12,<3.14`; Node 20+, Google CLI, LAB document tools, and WorkBuddy Docker are required as applicable. (`README.md:83–103`; `docs/BENCHMARKS.md:18–23`; `pyproject.toml:11`; `docs/SETUP.md:9–25`)

Configure solver/judge IDs, optional improver, Vertex project/region and ADC; alternate JobBench endpoints use separate URL/key settings. Calls incur API costs. Controls include `k`, domain/task caps, workers, dry-run, channel step/time limits; preflight checks installation/configuration, not model availability. (`.env.example:7–30`; `docs/SETUP.md:30–59,103–110`; `docs/EXPERIMENTS.md:44–52`; `harness2/core/spec.py:40–44`)

Supported solver substrates are **OpenCode and Codex**, not Claude Code. `claude_cli` exists separately as a proposer/selector channel. Codex needs a Responses endpoint, optionally supplied by the included Vertex/LiteLLM bridge. (`harness2/cli/_common.py:32,103–107`; `harness2/core/spec.py:17–19,33`; `docs/SETUP.md:114–145`)

**6. Reported results**

README claims one-step maximum gains across GLM-5/Gemini 3.5 Flash and four model–harness configurations: WorkBuddy **11.5 points**, JobBench **4.5 points**, LAB partial pass **11.8 percentage points**. It does not map each maximum to a specific model/substrate. (`README.md:41–48`)

A LAB patch comment reports ~9% unparseable judge calls and ~32% failure for ~50-criterion runs at two attempts; model/sample details are unstated there. (`third_party/patches/harvey-labs-judge-vertex-anthropic.diff:49–55`)

## What a careful adopter would miss by taking only the ledger

- Behavioral contrasts before composition and finals-only selection (`docs/EXPERIMENTS.md:8–14`; `harness2/core/schedule.py:637–639`).
- Evidence-backed reflection carried only to later same-domain tasks (`docs/EXPERIMENTS.md:16–19`).
- Validated editable surfaces and repair feedback (`harness2/core/tree.py:336–389`; `harness2/core/recursion.py:187–239`).
- Content-sensitive resume, artifact checks, and independent mode recovery (`harness2/core/schedule.py:408–463`).
- Grading boundaries, explicit missing-data treatment, and external network restrictions (`harness2/core/context.py:167–169`; `harness2/core/judge.py:15–18`; `docs/EXPERIMENTS.md:100–109`).