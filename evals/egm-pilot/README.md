# EGM fast-track pilot

Phase F0 of the EGM fast track in
[docs/plans/skill-catalog-execution.md](../../docs/plans/skill-catalog-execution.md):
a pre-registered evaluation contract, fixtures, and offline tooling for comparing
three arms on Claude Code 2.1.309. **F0 made no model calls.** F1 and later
phases spend model quota and need the user's approval.

| Arm | Contents |
|---|---|
| A native | Claude Code only |
| B EGM | Claude Code plus EGM's packaged plugin (`f0ba151`) via `--plugin-dir` |
| C OAW + EGM | B plus `scripts/oaw.py init --host claude` in the fixture (and, in the outcome suite, the OAW evidence entry) |

## Files

| Path | Purpose |
|---|---|
| `spec.json`, `spec.sha256` | Pre-registered contract: arms, suites, repeats, tolerances, budget cap, isolation flags, verdict rules, and hashes of every input. |
| `scenarios.json` | EGM's 30 scenarios converted from YAML, with provenance. See [NOTICE.md](NOTICE.md) and [LICENSE.egm](LICENSE.egm). |
| `convert_scenarios.py` | The converter; rejects any YAML construct or key it does not understand. |
| `protocol/project/` | Near-empty workspace for the protocol suite. |
| `outcome/project/` | Fixture project with `docs/design_draft.md` (planted defects) and decision record `docs/decisions/0007-postgresql-only.md`. |
| `outcome/overlay-oaw/` | Arm C only: `.agents/memory.md`, the OAW evidence entry for decision 0007. |
| `outcome/defects.json` | Defect IDs, case-insensitive detection regexes, false-positive guards, and examples. |
| `run_pilot.py` | Dry-run planner (default) and the approval-gated live runner. |
| `score.py` | Pass counts per (case × assertion), verdicts, and `improvement.py` artifacts. |
| `pilot_common.py` | Shared parsing and matching; its hash is pinned with `score.py`. |

## What each suite proves, and what it does not

**Protocol suite (EGM's 30 scenarios).** It checks whether arm C stays at parity
with arm B, which would mean OAW does not interfere with EGM's flow (for example
through trigger confusion or context growth). The scenarios check whether a run
follows EGM's protocol, such as its modal wording and its refusal to choose for
the owner. They do not measure design quality, so B beating A is expected and
**is not a quality claim**. Arm A runs once per scenario only as a sanity
baseline. Most scenarios name files that do not exist in any arm, because the
upstream suite ships no fixtures for them.

**Outcome suite (planted defects).** It counts how many known defects each arm
reports in `docs/design_draft.md`:

| ID | Defect |
|---|---|
| D1 | No latency, availability or throughput targets for a multi-region design |
| D2 | Undefined jargon (`Kestrel shim`, `BRV pass`) |
| D3 | Non-actionable implementation steps |
| D4 | Contradiction: records deleted after 7 days, but looked up over 30 days |
| D5 | MongoDB contradicts accepted decision 0007 (PostgreSQL only; MongoDB retired) |
| N1 | Decoy: `fan-out worker` is defined; calling it undefined is a false alarm |

B vs A asks whether EGM finds more than native, and C vs B whether OAW + EGM
finds more than EGM alone. D5 is the place the plan registered in advance where
OAW might win, because EGM's reviewers work without project context on purpose.
The decision record is in `docs/decisions/` in **every** arm and is not linked
from the draft. Arm C also has the OAW memory entry with source and revision.
This keeps the test fair. Removing the fact from A and B would only measure an
information gap, not OAW. Linking it from the draft would let every arm find it
without any recall. A single fixture with one defect of each kind is a small
sample. A win on it is evidence for this fixture, not a general benchmark.

**Not proven anywhere here:** Codex behavior. This machine has no Codex CLI, so
Codex stays `untested`, and Claude or fixture results never stand in for it
(decision 2). Every metric is **operator-reported**: it comes from the host's
result event and the runner's clock, not from a model-certified measurement.

## Headless isolation and its trade-offs

Every invocation uses `claude -p --output-format stream-json --verbose
--max-budget-usd <cap> --model <spec model> --setting-sources project,local
--settings <run>/config/settings.json --permission-mode acceptEdits
--permission-prompts none --strict-mcp-config --mcp-config <empty>`. Arms B and C
add `--plugin-dir <run>/plugin/egm` and start turn 1 with `/egm:<skill>`. All seven
EGM skills are manual-only, and EGM's `docs/claude.md` documents the
`/egm:egm-review` form.

- **No `--bare`.** It never reads OAuth or the keychain (only `ANTHROPIC_API_KEY`
  or an `apiKeyHelper`), so it would break this machine's OAuth login. It also
  skips CLAUDE.md discovery, which would remove arm C's treatment. `--safe-mode`
  and `--restricted` were rejected for the same kind of reason (see `spec.json`
  `invocation.rejected_options`).
- **`--setting-sources project,local`** keeps `~/.claude/settings.json`
  (hooks, enabled plugins, permissions) out of every arm without editing it.
  Project files still load, so arm C's `CLAUDE.md` and `.claude/skills` apply.
  The cost of this choice is that arm A is "native minus the user's personal
  settings", and nothing here proves that user-level memory or skills stay out.
  On this machine `~/.claude` has no `CLAUDE.md`, skills, agents or plugins.
- **`--settings`** turns hooks off and allows reads only of the copied plugin's
  `agents/`, `docs/`, `resources/` and `skills/` folders, as EGM's Claude guide
  asks for headless runs. Bash and other prompting tools are denied in every arm
  (`--permission-prompts none`); edits are accepted inside the workspace only.
- **`--strict-mcp-config` with an empty config** loads no MCP servers in any arm.
- **The plugin comes from `distributions/claude`**: EGM's packaged runtime, the
  same skills, agents and resources but without `test_scenarios.yaml`, so a run
  cannot read the expected answers. It is copied per run; nothing is installed.
- **Sessions:** single-turn runs use `--no-session-persistence`. The one
  two-turn scenario needs `--session-id` and then `--resume`, so it leaves a
  transcript under `~/.claude/projects/` (not settings).
- **Output:** stream-json ends with the same result object that
  `--output-format json` prints, and adds the `system/init` event (the per-run
  isolation evidence) and parent `Agent` calls (sub-agent counts).
  `score.py` accepts either format.
- `DISABLE_AUTOUPDATER=1` keeps the host version fixed during a run set.
  The manifest records whether `ANTHROPIC_API_KEY` was set, but never its value.

## Running

```sh
# dry-run (default): planned commands and run counts; calls nothing
python evals/egm-pilot/run_pilot.py
python evals/egm-pilot/run_pilot.py --phase F2 --show-all
python evals/egm-pilot/run_pilot.py --json

# contract integrity (add --egm-src <checkout> to check the plugin tree hash too)
python evals/egm-pilot/run_pilot.py --verify

# regenerate scenarios.json/LICENSE.egm from an EGM checkout (read as data only)
python -I -X utf8 evals/egm-pilot/convert_scenarios.py --source <egm-checkout> --check
```

Planned runs: F1 has 9 runs (12 invocations), F2 has 330 runs (A 30, B 150,
C 150; 341 invocations), and F3 has 15 runs (5 per arm).

`--live` refuses unless all of the following hold:

- `--i-have-approval <phase>-<first 12 hex of spec.sha256>` is given for that
  phase.
- `spec.json` matches `spec.sha256`, and every pinned input hash matches
  (scenarios, defects, fixtures, scorer code, EGM plugin tree).
- `model` is set.
- `claude --version` reports 2.1.309.

At F1, fill `model`/`effort` (and, if needed, the cap), then run
`run_pilot.py --freeze --egm-src <checkout>`. The new hash produces a new token.
Raw runs go to `<temp>/oaw-egm-pilot/<phase>/` by default, outside the
repository. Do not commit them.

```sh
python evals/egm-pilot/score.py --runs <out>/F2 --runs <out>/F3 --emit-gate <dir>
```

`--emit-gate` writes `evaluation.json`, `baseline.json`, `candidate.json`,
`arm.diff` and `snapshot.txt` for each verdict comparison. Then
`scripts/improvement.py --base-dir <dir>/<comparison> propose --target arm.txt
--patch arm.diff --evaluation evaluation.json --snapshot "$(cat snapshot.txt)" ...`
followed by `compare` reruns the official gate. Rows are passes-first within each
(case × assertion), so `improvement.py` judges with tolerance 0: a strict
cross-check until P4 adds tolerance. The pilot verdict applies the
pre-registered live tolerance (1 of 5).

## Cost estimate once F1 calibrates

With `c̄(suite, arm)` = mean `total_cost_usd` per invocation in F1 and `S = 30`
scenarios (31 turns):

- `E[F2] ≈ 31 × (1·c̄(protocol,A) + 5·c̄(protocol,B) + 5·c̄(protocol,C))`
- `E[F3] ≈ 5 × (c̄(outcome,A) + c̄(outcome,B) + c̄(outcome,C))`
- Hard ceiling = invocations × cap: F2 341 × $2 = $682, F3 15 × $2 = $30.

`run_pilot.py --estimate-from <out>/F1` prints the expected cost and a high
estimate (worst F1 sample × invocations) per phase, suite and arm. F1 has only
one or two samples per cell, so prefer the high estimate.

## Open until F1 (needs a live call)

- The init event's field names (`plugins`, `slash_commands`, `skills`,
  `mcp_servers`). The isolation check depends on them, and arm C must show
  `oaw-evidence` under `--setting-sources project,local`.
- Whether `/egm:<skill>` expands in `-p` mode with `--plugin-dir`, and how EGM's
  modals render headless (`AskUserQuestion` inputs or plain text). Protocol
  assertions read both.
- Whether reviewer reads of the copied plugin pass the `Read(//c/...)` rules, and
  whether `Agent` needs approval under `--permission-prompts none`.
- Whether `usage` includes sub-agents (the tokens metric prefers `modelUsage`).
  Also the result subtype when the budget cap is hit (scored as a failed run).
- Whether $2 covers an uninterrupted EGM review: it spawns many reviewers. If it
  does not, raise the cap at F1 and re-freeze before F3.
