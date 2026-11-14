# Independent Claude Code review of OAW v2.0.0

Review the PR against main without merging, tagging or releasing. The version is proposed, not published. Reproduce important failure cases independently rather than relying on the author's green gate.

**V2 is the whole OAW product, including EGM.** The default recipe provides
seven pinned EGM native skill entrypoints plus evidence; wiki and improve are
optional. Exact recipe selection and safe retirement are implemented. Automatic
external-skill scouting/digestion/absorption remains a plan, not a shipped feature.

Use `docs/SHARED_ACCEPTANCE_PROTOCOL.md` for the single self-contained common
Codex/Claude test protocol. The Codex conclusions, all score tables, actual usage,
source identities and limitations are together in
`docs/validation/egm-oaw-codex-2026-10-30.md`. Claude owns its separate report and
private cohort; do not modify shared code or Git during a performance run.

The historical 9ae4eba pilot used a runner-supplied EGM runtime and does not
certify this new installer or native discovery. Its valid source-loaded results
are 8/8 planted detections in each arm, no unsupported concrete claims, and
exploratory readiness coverage EGM/v1/v2 = 14/14, 2/14, 14/14. The invalid
blocked-IO predecessor is excluded, with failed usage preserved. Do not turn
completion counts into quality, or an old post-hoc endpoint into a prospective one.

Review the complete pinned runtime in `vendor/egm`, the independent provenance
lock, `scripts/sync_egm.py` generation and `scripts/oaw.py` installation together.
Claude adapters preserve upstream tools/model/context restrictions; project-root
and plugin namespace bindings are marked adaptations. The strict gate checks
adapter bytes as well as source completeness. File/schema success does not prove
host discovery, semantic quality or a production token advantage.

## Main questions

1. **Native-first scope.** Do the short AGENTS.md, pinned EGM runtime and ten selectable native skill packages add non-obvious OAW value without duplicating native reasoning, memory, compaction or generic task procedure? Are the removed v1 rules truly absent from installed defaults?
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

The earlier 82-test result describes the initial revision, not the current suite.
See the dated [validation record](validation/v2.0.0-local.md) and current PR
checks. CI is configured for Ubuntu/macOS/Windows with Python 3.10/3.13. Actual
native host discovery and model experiments are separate from artifact installs.

Historical v1 wiki reports intentionally retain example placeholders and produce 22 soft lint warnings. Native schema failures and substantive broken metadata/link/freshness issues are hard errors. The historical Codex pilot requested Sol 6.1; its provider revision was not exposed. New integrated-install performance and real host skill listing remain unverified. The improvement gate tests use explicitly synthetic fixtures.

Report actionable findings with severity, exact file/line, reproduction, expected behavior and proposed smallest fix. Preserve uncertainty where an environment-dependent claim cannot be verified.
