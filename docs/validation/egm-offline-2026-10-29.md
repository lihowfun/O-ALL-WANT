# EGM verification status — 2026-10-29

> Historical version-specific record. Current V2 includes EGM; current product acceptance uses
> `docs/SHARED_ACCEPTANCE_PROTOCOL.md`. Original arm names, source pins and results below remain unchanged.

**Real Codex study completed; the strict overall quality gate failed. Keep Draft.**
The user requires real experimental non-regression, not synthetic test passes.
Claude CLI model calls remain paused; its free auth-status check reports logged
out. Preparation and offline checks made no experimental model calls. The user
subsequently authorized Codex independent subagents. All 27 primary reviews and
the complete-source grading round are finished. See the
[full result and preserved corrections](egm-codex-2026-10-29.md).

## Completed offline work

- Windows / CPython 3.12.14: full OAW gate, **135 tests, zero skips, 8/8 groups**.
  This includes both-host installation, external-skill coexistence, original
  migration/recall/wiki/improvement regressions and the pilot/local tests.
- Failed reviews cannot win on lower cost; missing per-invocation init/model
  metadata, mismatching native capabilities and prohibited tools fail closed.
- Outcome regexes are screening-only; no quality verdict or official outcome
  improvement artifact is exported. Demonstrated D3/D4/D5 matching counterexamples
  are covered, without pretending regexes establish semantic correctness.
- Frozen inputs include runner/converter/scorer and OAW scripts/templates.
  Resume preserves the original identity. Authentication preflight refuses before
  model calls. Failed attempts do not become free calibration samples.
- Claude Code **2.1.309**: official EGM manifest validated, and its skill/agent
  component directories passed native `plugin validate --strict`. This validates
  schemas/components, not discovery, execution or quality.
- Source: EGM manifest **0.1.0** at full commit
  `f0ba151b252c9abf1318d9fe857a43265d06de89`, Apache-2.0. Seven upstream YAML
  hashes / 30 converted scenarios match the pinned source. A collection-time
  recheck corrected the earlier runtime-tree claim: 63 of its 64 files match
  that commit after CRLF normalization, including all assigned workflow inputs.
  Its README has one older command-prefix sentence, exactly matching upstream
  `e45f640cc3799cf2a19c1dfb88aa850c021231ac`. The README is not an assigned review
  input. Preserve this as-used deviation and both raw/normalized hashes; do not
  silently replace the runtime during collection or call the tree byte-identical.
  Runtime is not vendored or installed by OAW.

## Real experiment completed; promotion condition not met

[Local experiment](../../evals/egm-local/README.md): three independent cases,
three repeats, A native / B EGM / C EGM+OAW, **27 primary reviews**. Fresh contexts,
the same task/source access and allowed reviewer budget; fixed seeded balanced
dispatch order. All initial workspace files are hash-checked after each trial.
Review prompts, grading prompts, rubric, sources and preparation are frozen.

Two fresh graders independently assess anonymous reports against source and
rubric. Missing/invalid runs or grading disagreements block acceptance. Both
B vs A and C vs B must have no per-defect detection-count regression and no
increase in unsupported concrete claims. A win attributed to OAW indexing
requires a plain-index control and memory-removal ablation.

Native plugin discovery and OS-enforced isolation are separate from reading
official workflow files through Codex agents. Any result is scoped to this fixed
suite/model configuration, not statistical equivalence or general superiority.
Unavailable token/cost metadata will not be fabricated.

All three arms detected 24/24 planted defects. A had 0 unsupported concrete
claims, B had 1, C had 0. C matched native and did not regress against B in this
suite. B versus A failed the fixed zero-increase false-claim rule. No general
superiority, indexing causality or efficiency claim follows. Main remains
unchanged; passing functional checks cannot override this quality gate.

The initial grading packet omitted the actual EGM method standards. All of its
grades/adjudication and provisional regression aggregate were excluded after
source verification exposed false unsupported-standard attributions. Full
as-used method evidence was added, and six fresh contexts regraded every
unchanged report with the same rubric/prompt. One genuine factual-assertion
disagreement was explicitly adjudicated in the corrected round. Both grading
rounds and the correction chronology are preserved in the full result.

The first calibration registration (`675703e17644…`) was stopped after five
primary trials started (four completed, one interrupted). Its instruction to
avoid other reviewers' reports was ambiguous: it also blocked required
within-trial Stage 8 input. No quality grades were read or used. Raw calibration
artifacts remain preserved and excluded from acceptance. A new registration
(`d108b3a9e599…`) permits the official same-trial artifacts while prohibiting
cross-trial access. Cases, rubric, grading rules and resource limits are unchanged;
all 27 reviews restart in fresh workspaces and contexts.

## Version preservation

Candidate remains OAW **2.0.0 proposed**. Existing main
`5df531372330f6b0e1c9a81aee0c1c45f2f283ff` and existing `v1.0.0` are retained.
Annotated recovery tag `backup/oaw-v1.1.0-20261029` has been pushed at that exact
main commit. It is a recovery point, not a new GitHub release. No history is
rewritten. On a later accepted merge, use a normal merge commit; rollback should revert
that merge, rather than force-reset shared history. User project data remains
subject to the installer's backup/receipt/ownership rules.
