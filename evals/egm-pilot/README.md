# EGM pilot tooling (revised offline contract)

No successful live result exists. The earlier F1 runner attempt at spec
`27d99f9160d974dd26360e07013ab3a574423d479e910e22cbb3894fae6c2bde`
failed authentication before model calls and reported $0. It is not a quality
result or valid cost calibration. Claude CLI runs remain paused.

The revision addresses [the static review](../../docs/reviews/2026-10-29-pr4-egm.md)
and the later pilot findings. For the separately registered Codex workflow
experiment, see [egm-local](../egm-local/README.md). Never treat a synthetic
fixture result, package validator or dry run as an EGM benefit.

## Free checks

```sh
python3 evals/egm-pilot/run_pilot.py --dry-run --phase all
python3 evals/egm-pilot/run_pilot.py --verify
python3 -m unittest tests.test_egm_pilot
```

Dry-run is the default and starts no subprocess. Verify checks the frozen
contract, case data, runner/converter/scorer and OAW scripts/templates.
`--freeze` records intentional pre-experiment changes; preserve the old identity
in Git and obtain separate user authorization before any model invocation.

## What was fixed

- Every invocation needs complete init metadata. Models, native skills/commands,
  tools and non-treatment plugins must match. Missing metadata fails closed.
- Every baseline run must complete successfully; failed reviews cannot win
  through lower costs. Failed/zero-token/zero-cost attempts are not calibration.
- Resume preserves the original manifest and refuses changed identities. Raw
  artifacts must remain outside the repository.
- Restricted mode, explicit tool selection and denied command/network tools
  replace the mistaken assumption that `permission-prompts none` disables Bash.
  The complete official plugin is inside the workspace under `.egm-runtime`,
  with edits denied. Actual host enforcement/discovery is still unverified.
- Both baseline and candidate get the same explicit current ADR reading list.
  A memory-index difference cannot be called a superior memory engine without
  a plain-index control and a memory-removal ablation.
- Regex output is **triage only**. Outcome comparisons cannot emit evolution,
  parity, or official improvement artifacts. Independent blinded grading of
  concrete findings, unsupported claims and costs is required.

## Protocol and outcome have different purposes

The 30 EGM scenarios / 53 assertions are protocol conformance probes, not design
quality measurements. Their original file/conversation preconditions are not
fully instantiated here. F2 live is blocked until those fixtures exist. An
otherwise valid protocol comparison additionally requires baseline passes of
at least 4/5 per assertion; equal failures never prove non-interference.

Outcome has one design fixture with known defects and a decoy. Its regexes now
reject several demonstrated false positives, but remain an incomplete semantic
grader. Broader, separately frozen cases and hard negatives are in egm-local.

## Retained optional Claude runner

The program retains explicit `--live` with a matching phase/spec authorization
token, pinned runtime tree, exact host version and a free auth-status preflight.
**This does not authorize a run. No paid execution is requested by the current
workflow.** F1 is now only three outcome smoke calls (one per A/B/C), capped at
$1.50 each, $4.50 total; this would calibrate setup, not establish quality.
F3 is 15 calls, at most $22.50 at that cap. F2 remains blocked. Dry-run derives
counts and ceilings from spec.json; these are caps, not expected spend.

Claude Code 2.1.309 also exposes native `plugin eval` with a no-plugin baseline.
Prefer evaluating that native facility before growing a second general live
runner. Nothing here changes user login/configuration or installs a plugin.
The Codex experiment uses the current host's independently authorized agents,
not Claude CLI. Bundled native skills belong in the baseline, with the same
capability set across arms.

## Upstream identity and licensing

EGM manifest **0.1.0**, commit
`f0ba151b252c9abf1318d9fe857a43265d06de89`, Apache-2.0. The source commit
is the immutable identity; manifest version alone is not a published-release
or compatibility claim. `distributions/claude` is the complete official runtime,
not seven copied skill files. The source package is never bundled with OAW.
Converted scenario JSON is redistributed with [NOTICE](NOTICE.md) and
[LICENSE.egm](LICENSE.egm), including source-file hashes and modification notes.

`score.py --emit-gate` remains available only for valid protocol comparisons.
Exports are synthetic/observational artifact checks and not statistical proof.
There are no exported outcome-quality gates from regex matches.
