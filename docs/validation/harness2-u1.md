# Harness2 U1 implementation validation

Date: 2026-11-13. Branch: `codex/harness2-evaluation-u1`, based on release-polish
`5af21f61d1d30d844ead3169081532842d3fe375`. The owner explicitly authorized this
method-engineering work before release (D46). It ships with the version after 2.0.1 (D50); see
"Merged with the 2.0.1 line" at the end.

Implemented: optional stdlib evaluation accounting, JSON/Markdown reports,
read-only historical FIXCHECK import, and a bridge to existing `eval_stats`.
[Usage and contract](../EVAL_LEDGER.md), [reviewed design](../plans/harness2-u1.md).
No startup/installed payload changes, new scorer, catalog adoption or model task
execution. This is not a measured harness quality/token-saving improvement.

## Executed validation

- Linux, Python 3.10.20; focused synthetic suite: **29 tests, 0 failures**.
- `sync_examples.py --write`: completed; no generated payload differences.
- Full offline gate: **9/9 checks, 714 tests, 0 skips**, after review fixes.
- [Machine-readable gate evidence](harness2-u1-gate.json) binds tested sources.
- Existing `eval_stats` output is checked for exact equality on paired fixture
  score/cost arrays. Fixtures cover missing planned tasks, failed/retried costs,
  quota zero, unknown cost versus zero, unscored versus zero score, duplicate
  IDs/attempts/parent-child charges, source/manifest/path/snapshot conflicts,
  output/selection/grading linkage, incompatible graders and metrics, pilot and
  stream exclusion, repeat coverage, single-repeat floor and malformed input.
- These are offline behavior tests, not model benchmarks or cross-platform CI.

## Independent review

Design: one native fresh-context reviewer, initially 3/4 criteria passed. The
missing metric/rubric/judge/source contract was added; original finding closed,
4/4 design approval before implementation. Subsequent clarifications retained
that approval (plan SHA-256
`07da502f67584971b5ce7ca9efd62443a29a4e43cd1e849a47e93c74c61656ad`).

Code: one fresh-context review round found two actionable defects even though
all original 27 tests and the first 712-test full gate passed:

| Finding | Repair and regression |
|---|---|
| P1: scored outcome plus grading N/A could report complete with zero grading cost | Reject contradictory N/A scoring; require complete matching grading evidence for report completion. CLI tests verify invalid exit 1 and incomplete exit 2 for failed/unmeasured grading. |
| P2: whole-bank verification did not bind each manifest unit to its actual bank entry | Recompute each unit SHA with historical H1 JSON spacing/UTF-8; reject a manifest/ledger identity changed consistently while the actual bank stays unchanged. |

The original reviewer confirmed **2/2 findings closed**, independently reran all
29 focused tests and checked the actual read-only import. Closure was limited to
the original findings; it is not an extra independent review round.

## Existing FIXCHECK import

[Saved accounting report](harness2-u1-fixcheck.json), SHA-256
`d06dd78f559beccfef2a80ac93b96823681f92813b1469ff296ec7e8aebf2275`.
The report contains source IDs/hashes and summaries, not private source paths or
native transcripts; its supplied identifiers/reasons were checked for publication.

| Observation | Result |
|---|---:|
| Planned runs | 24 |
| Started / completed / scored | 13 / 12 / 12 |
| Missing outcomes | 12 |
| Quota not-run attempts | 1 |
| Observed logical tokens | 6,802,657 |
| Complete whole-study logical total | unknown (`null`) |
| Outstanding Claude reservation | 0 |
| Recovered answer logical tokens | 428,278 |
| Recovered answer elapsed time | unknown (`null`) |

JSON and Markdown each ran twice: byte-identical outputs, exit 2, no stderr.
Hashes/existence of all 19 explicitly read input paths were unchanged before and
after. The manifest remains
`d1bec84b95004f7d27f9adf6a1acc07ae53be41f45fcbb50943c334f1ea5b80e`, candidate
`c2d9852bf8cabf13fd86a4340ab89f69044cae5a`. The importer preserves the recovered
serialized total, rather than selecting the truncated 397,636-token observation.
It does not run the historical grader or thresholds, recover files, or replay
native streams. All historical usage completeness remains unverified. Engineering,
review and other missing stages remain unknown; 6,802,657 is an observed subtotal.

## Remaining work and limits

Use this contract when preparing a new evaluation, with real per-stage metering,
artifact identities and predeclared grading/analysis. A hash proves identity,
not truthful coverage, independence or absence of omitted work. The comparison
is one metric/judge and execution-token scope, not the D32 cross-family verdict.

No U2/U3 behavior change, Harness2 runtime trial, new capability evaluation,
release merge or tag was performed. Existing FIXCHECK continues on its original
candidate. Gate results here do not replace its disposition, final integration
checks or actual Linux/macOS/Windows CI. Controller/design/code-review model
costs were not independently metered; zero new experimental task calls is not
zero engineering/review cost.

## Cross-family review follow-up (2026-11-13)

U1 was built and first reviewed within one model family, so a Claude review followed. Fourteen
adversarial synthetic bundles (missing outcome, unscored outcome given a zero, self-reported usage,
self-reported grader, symlink escape, unmatched repeats, a grade bound to another run's output, stream
analysis unit, and others) were all refused or reported incomplete as the contract requires; a failed
attempt's cost stayed in the arm's total. No input was found that reports more than its evidence.

Three design gaps were found and changed, then reviewed once by Codex (no blocker; two disclosure
findings in the Markdown output, both fixed with a test):

- `required_metrics`: completeness was judged on all four metrics, so a subscription-billed study with
  no dollar cost could never be complete and exit 2 lost its meaning. The frozen manifest may now name
  the metrics that decide completeness (default: all four; `logical_tokens` is mandatory). Other metrics
  are still reported with their unknown entries, in JSON and Markdown.
- Test-only comparison: any pilot or development run of the compared arms made `compare` refuse, which
  kept pilot cost out of the study ledger that holds the test comparison. `compare` now uses the test
  runs only and reports the runs it left out.
- Identical harness: two arms with the same harness hash were compared as if they differed; this is
  now refused.

Measured on Linux x86_64, `/usr/bin/python3` 3.10.12: the two ledger test files, 33 tests, pass. The
full gate result for the commit that carries this change is recorded in its commit message. These are
synthetic fixtures; they are not model measurements and establish no benefit.

## Merged with the 2.0.1 line — 2026-11-14

The ledger ships with the version after 2.0.1 (D49, D50). The 2.0.1 release line (`036a3e6`) was
merged into this branch; the only conflict was a ROADMAP heading. No ledger
source or test changed in the merge.

Measured by the lead on Linux x86_64, `/usr/bin/python3` 3.10.12, at the merge: the full offline
gate passed **9/9 checks, 751 tests, 0 skipped** (718 tests of the release line plus the 33 ledger
tests). The ledger had not run on macOS or Windows before this merge; the six-job CI runs on the
pull request that carries this branch. The earlier gate snapshot
[harness2-u1-gate.json](harness2-u1-gate.json) binds the sources of the pre-merge branch and is
kept as history.
