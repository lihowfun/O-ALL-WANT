# EGM / OAW v1 / OAW v2 acceptance

Read the [registered scope](../../docs/plans/egm-oaw-three-way-acceptance.md) and
[Claude independent rerun handoff](../../docs/CLAUDE_ACCEPTANCE.md).
This is a controlled design-review and persisted-file handoff pilot. It does not
certify native plugin discovery, calendar-time memory or production coding.

`protocol.json`, `rubric.json`, `grade-prompt.md` and the initial `bench.py` were
committed before task-model execution. The OAW product inputs are pinned to
earlier source commits, independently of the evaluator's commit.

```sh
# Free preparation; requires git and Bash for the actual historical v1 installer.
python3 evals/three-way/bench.py prepare --repo /path/to/O-ALL-WANT \
  --egm-repo /path/to/EGM-source --out /private/fresh/cohort

# Consumes the user's signed-in Codex quota. Read the protocol/budget first.
python3 evals/three-way/bench.py run --out /private/fresh/cohort --codex /path/to/codex

# Offline only; no model requests.
python3 evals/three-way/summarize.py --out /private/fresh/cohort --write /private/fresh/cohort/summary.json
python3 evals/three-way/make_packet.py --out /private/fresh/cohort --packet /private/fresh/packet
python3 -m unittest discover -s evals/three-way -p 'test_bench.py' -v
```

The first, now **invalid environment cohort** hit its original 2.5m cap. See the historical
[budget-only amendment](budget-amendment.md): total cohort cap 12m, same 100k
output cap and original 3000-second origin, no changed tasks/prompts/grades or
failed-call retries. `continue_budget.py` preserves/reuses completed calls,
verifies their exact prompts and hashes, and dispatches only never-started calls.
Independent graders then found that reads had been blocked; the whole cohort is
excluded. See [invalidation](invalid-environment-v1.md). The current v2 protocol
starts fresh with `--approve-for-me`, a successful real read/write preflight,
per-call unknown-nonce IO proof and prospective 20m/250k input-output/output caps.
The old continuation script is historical; do not resume invalid evidence.

The runner never uses a key-based paid API or invokes Claude. Its `run` adapter
accepts only Codex workspaces. `prepare --host claude` installs the v2 adapter for
a separately registered Claude controller; it does not run Claude automatically.

Summary counters measure exact answer fields and observed usage. Citation path
existence is not semantic grounding; review claims require independent blinded
grades and source support must be checked against each stage's saved snapshot.
Do not turn incomplete usage or missing grades into a quality/efficiency pass.
Raw prompts/events, per-stage files, full local paths and private state stay
outside the public repository.
