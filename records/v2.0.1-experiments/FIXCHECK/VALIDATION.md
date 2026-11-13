# FIXCHECK preparation validation

2026-11-13. Linux; no FIXCHECK model answers started.

## Frozen candidate and inputs

- Product candidate: `c2d9852bf8cabf13fd86a4340ab89f69044cae5a`.
- Installed corpus O commit: `54563feddf5fd7c2b89b9e2e1c1f0c50fd5666c9`.
- Installed O tree: `f901ef192813418c69a7dec6d28b04240eac6ca6`.
- Final preregistration manifest SHA-256: `d1bec84b95004f7d27f9adf6a1acc07ae53be41f45fcbb50943c334f1ea5b80e`.
- Original H1 runner, grader, source rows, task files, N/L trees, tool snapshots, system executables and launch configuration match the original freeze. Only the explicitly allowed candidate O/product mode/budget fields differ.
- Snapshots are independent copies (no hardlinks). Local state contains its own 17M D45 budget, BINDING and empty event audit. H1 records and state were not rewritten.

## Independent review

Fresh-context Codex review, no inherited parent reasoning. Initial criteria 1 and 3 failed, 2 and 4 passed. Three findings:

1. A false hidden function could leave its corresponding requirement item true.
2. Forged `recall=true` could hide failed recall functions and evade the memory regression threshold.
3. Negative session tokens could cancel against another session while preserving a positive row total.

All three were fixed. The manifest now includes the frozen functions→items mapping, and the calculator verifies functions→items→counts/score plus recall functions/suite status. Session totals must each be positive integers and sum to the row total. The reviewer independently replayed the three original counterexamples; all now raise ValueError.

Final **4/4 PASS**: provenance, launch/accounting/resume guards, D45 decisions, privacy/evidence limits. The reviewer checked the final manifest digest, all 12 grader mappings, source hashes, state binding and event template. This closure was limited to the original findings and final binding, not another broad review loop. Machine-readable summary: [REVIEW.json](REVIEW.json).

## Model-free validation

| Check | Result |
|---|---|
| `python3 -m unittest discover -s records/v2.0.1-experiments/FIXCHECK -p 'test_*.py'` | 28/28 pass |
| Empty-state thresholds command | exit 2, incomplete, 0/24 counted rows; claim=null |
| Independent old-row comparison | all 72 public O/N1/N2 summaries match original rows field-for-field |
| Independent malformed-input probes | inconsistent function/item, forged recall, negative session cost all rejected |
| Independent launch stubs | bad review, stale/active-other/wrong-manifest preflight, missing earlier class and premature Claude rejected |
| Independent accounting/recovery probes | ended cost 700 + interrupted reserve 450 = 1150; repeated recover writes completed attempt only once |
| Records repository gate | 9/9, 167 behavior tests, 0 skips; 22 pre-existing wiki soft warnings |
| Public manifest/baseline/template scan | no known local account paths, raw transcript paths or credential field literals |
| Original H1 freeze and source row digests | unchanged |
| Experiment starts | 0 |

The records gate checks its existing toolkit; the 28 FIXCHECK tests separately exercise the new experiment code. The candidate product's earlier **677-test** gate remains recorded in [the repair progress](../../release-fixes-2026-11-13/PROGRESS.md); these are different checkouts, not conflicting test counts.

## Remaining release requirements

This is preparation evidence, not a model result. CI routing for the new product branch still awaits owner choice under D45; six actual jobs have not yet been verified. Before any run, push these exact preregistration bytes to records, verify the independent state, recheck live PPT/other experiment processes and refresh the local preflight. No merge, version bump, tag or release has been performed.

Next: resolve the PR/CI arrangement, then the once-only FIXCHECK in the approved sequence. Claude estimate ~8M, independent hard cap 17M; Codex usage reported separately. Harness² U1/U2/U3 stay after the release gates.
