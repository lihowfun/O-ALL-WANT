---
name: oaw-intake-flow-v1
description: "D21 lean intake flow (2026-11-04): owner only at entry and release; quick screen ≤3 units/food, build with tests, one goldfish round on the diff, automatic A/B/C tiers"
metadata:
  type: project
---

The owner rejected the 2026-11-03 digestion flow as far too slow with too many human reviews (about 20 owner touchpoints, 3 revisions, 3 goldfish rounds, 2.9 MB of records, 0 absorbed). On 2026-11-04 they approved D21 (recorded in `records` branch, `records/digestion-2026-11-03/ingest/DECISIONS.md`):

1. Entry (owner: repo URL or scout ticks).
2. Quick screen, automatic: at most 3 units per food; the rest return to the pool with a one-line verdict, no more analysis or paid plans.
3. Build as code plus tests on `claude/oaw-2`; gate must pass; code and tests are the record (no parallel proposal documents).
4. One zero-context goldfish round on the code diff; the Elephant resolves; only a blocker the Elephant rejects reaches the owner.
5. Tiers: A (mechanism only, no model-facing text, no food code run, restorable) absorbed automatically; B (model-facing text) A/B inside the D13 budget; C (runs food code, new dependency, uncovered license/CLI choice, removes a skill, over budget) asks the owner.
6. Release: one version page; the owner merges the PR.

**Why:** minimize owner review; D14's standing choices (license route Apache-2.0 attribution, CLI contract, release target) count as policy.

**How to apply:** never send the owner per-batch approvals or document-consistency findings; turn real defects into tests. This refines [[feedback-egm-full-combo]] (owner decides via policy and release, not per item) and [[oaw-catalog-intake-rules]]. Related: [[feedback-github-tidy-branches]].
