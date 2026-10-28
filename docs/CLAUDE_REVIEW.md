# Independent Claude Code review of OAW v2.0.0

Review the PR against main without merging, tagging or releasing. The version is proposed, not published. Reproduce important failure cases independently rather than relying on the author's green gate.

## Main questions

1. **Native-first scope.** Do the default AGENTS.md and three native skills add non-obvious OAW value without duplicating native reasoning, memory, compaction or generic task procedure? Are the removed v1 rules truly absent from installed defaults?
2. **Migration preservation.** Review `scripts/oaw.py`: read-only preview, full preflight, recognized ownership, symlink/type conflicts, rollback, backups, `--keep-custom`, and additive profile/host choices. Confirm existing customized policy, memory, raw/wiki content and project VERSION/ROADMAP survive. Check pending-conflict and doctor exit status.
3. **Native layouts.** Confirm `--host codex|claude|both` routes native packages correctly from one source and doctor does not equate supported features with enabled host settings. Actual native discovery is a separate check.
4. **Concurrent writes and boundaries.** Review `scripts/oaw_common.py`, Context Hub and wiki mutations. Check complete read-modify-write locking, stable sidecars, atomic replacement, topic confinement and symlink handling. Stable lock files must not be deleted/enumerated as content.
5. **Recall and wiki correctness.** Challenge JSON/text budgets with escaped prefixes, huge records and adjacent matches; preserve the actual match and meaningful continuation. Check source/query changes invalidate cursors. Challenge annotation delimiter examples, unfinished code fences, rebuild idempotency, per-page freshness and relocated links.
6. **Self-improvement gates.** Review `scripts/improvement.py`: concrete scoped diff, fixed cases/repeats/assertions, matched metadata, patch identity, per-assertion regressions, resource limits, changed/missing evidence and acceptance revalidation. No path may automatically apply a patch or silently rewrite policy. Operator-supplied metrics are not certified model measurements.
7. **Gate strength.** Inspect `tests/`, `scripts/harness_check.py` and `sync_examples.py`. Verify a broken skill, stale router/helper, arbitrary process failure or installer conflict cannot produce a false pass. Compare generated example contents rather than only file names.
8. **Documentation honesty.** Match README, CHANGELOG, UPGRADING and SELF_IMPROVEMENT to actual CLI behavior. No native-model quality gain, live skill discovery, or remote matrix success should be implied by local fixtures.

## Run

```bash
python3 scripts/harness_check.py --verbose
python3 scripts/sync_examples.py
```

The author ran 82 behavioral tests and 8/8 gate groups on Windows/Python 3.12.14. Actual source-package installs for both hosts and the Bash wrapper were exercised. Skill-creator schema checks passed for three packages. CI is configured for Ubuntu/macOS/Windows with Python 3.10/3.13; inspect PR checks for current results.

Historical v1 wiki reports intentionally retain example placeholders and produce 22 soft lint warnings. Native schema failures and substantive broken metadata/link/freshness issues are hard errors. Native Opus 5.5/Sol 6.1 A/B tasks and real host skill listing remain unverified; the optional comparison workflow is tested with explicitly synthetic fixtures.

Report actionable findings with severity, exact file/line, reproduction, expected behavior and proposed smallest fix. Preserve uncertainty where an environment-dependent claim cannot be verified.
