# EGM verification status — 2026-10-29

**No quality/parity claim and no authorization to merge from this record.**
The user requires real experimental non-regression, not synthetic test passes.
Claude CLI model calls remain paused; its free auth-status check reports logged
out. Preparation and offline checks made no experimental model calls. The user
subsequently authorized Codex independent subagents; collection is now in
progress, with no accepted quality result yet.

## Completed offline work

- Windows / CPython 3.12.14: full OAW gate, **125 tests, zero skips, 8/8 groups**.
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
  hashes / 30 converted scenarios and the official Claude runtime's 64-file tree
  match the pinned source. Runtime is not vendored or installed by OAW.

## Real experiment prepared, not executed

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

Codex trial collection is **in progress** after explicit user authorization.
No arm has an accepted aggregate result. Main stays unchanged until real
evidence and the functional/CI checks meet the user's acceptance condition.

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
No history is rewritten. On a later accepted merge, preserve an annotated
pre-upgrade version point and use a normal merge commit; rollback should revert
that merge, rather than force-reset shared history. User project data remains
subject to the installer's backup/receipt/ownership rules.
