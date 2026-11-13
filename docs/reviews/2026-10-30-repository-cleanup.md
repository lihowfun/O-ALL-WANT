# Repository cleanup — 2026-10-30

The user requested removing completed branches and PRs while retaining recovery
points. GitHub PR history is retained; obsolete open PRs are closed rather than
erased. Main and the active upgrade PR were not merged or rewritten.

| Item | Action | Recovery / reason |
|---|---|---|
| PR #1 / #2 | Already merged and closed; corresponding remote branches already absent | Existing main history retained |
| PR #3, Hermes-inspired memory loop | Closed as superseded by the v2 scope decisions | `archive/hermes-memory-loop-20261030` → `a048cc86d3c48fc6f229b9cb0a204c1a4de8afb8` |
| Remote `feat/hermes-inspired-memory-loop` | Deleted with an exact-head lease after archive tag was pushed | Full proposal history retained in tag |
| Remote `feat/skill-catalog` | Deleted after verifying it is an ancestor of active PR #4 | `archive/skill-catalog-20261030` → `42d348fd736e56e7d5a52fe5d2d6b36b6c4b30f9` |
| Old `OAW-pr4-review` / `OAW-catalog-review` worktrees | Removed with normal Git worktree removal, without force | Clean tracked/untracked status; ignored files were Python bytecode caches only |
| Local `codex/pr4-egm-review`, old local PR branch, `feat/skill-catalog` | Redundant refs deleted after ancestor checks | Commits reachable from PR #4 and archive tags |
| Working branch `codex/egm-pilot-measurement-fixes` | Renamed to `codex/oaw-2-native-upgrade`, tracking the same remote branch | Same commit; no content rewrite |

Retained:

- Main checkout `O-ALL-WANT` on `main`, at `5df531372330f6b0e1c9a81aee0c1c45f2f283ff`.
- Active checkout `OAW-egm-test` on `codex/oaw-2-native-upgrade`; PR #4 remains open Draft.
- Existing `v1.0.0`, `backup/oaw-v1.1.0-20261029`, both new archive tags and full Git history.
- Original ignored `.oaw/progress.json` remained byte-identical and was also backed up locally before switching the main checkout.
- Local raw experiment evidence, source clone and review notes; these support independent review and are not disposable worktree caches.

No main merge, v2 release, history rewrite, or deletion of experiment evidence
was performed. The new requested study is documented as
[OAW v1 versus OAW v2](../plans/oaw-v1-v2-evaluation.md); prior host-only
comparison data is not relabeled as an OAW v1 result.
