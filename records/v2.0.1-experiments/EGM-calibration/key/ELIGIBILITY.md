# Eligibility check of KEY.json (second, independent check)

Key sha256 `41efe96a84ada8b87321fbbf70474e39c5f98273f6d522ae2141dea093429ca4`. Judged from the packet alone (plan, `evidence/`, code as of 2026-11-07). I did not open `CURATION.md`, `LEDGER.json`, `KEY.curator-original.json`, `egmcal/`, `OAW-records/` or any later plan, and ran no packet code. Per-item detail is in `ELIGIBILITY.json`.

## Result

Every one of the 16 primary claims describes something that is really in the draft; none is wrong and none needs excluding. Seven of them are not blocking by the tier definitions I was given.

| Verdict | Count | Items |
|---|---|---|
| keep_primary | 7 | K05, K07, K09, K14, K15, K18, K30 |
| keep_primary_with_edit | 2 | K02, K29 |
| demote_to_secondary | 7 | K06, K10, K16, K17, K21, K24, K25 |
| exclude | 0 | — |

All cited line references are correct; I found no off-by-a-few errors.

**The bar I used.** Blocking means a named statement in the draft is false or unworkable against the packet (code, a documented rule, the evidence, or another statement in the draft), and fixing it needs a decision the draft does not raise. Where the draft is only silent, keeps a known heuristic limit on purpose, or has a weak acceptance rule, I called it secondary. Under a looser bar ("any verifiable plan-versus-code gap that must be flagged before implementation"), K16 and K24 go back to primary and K06 becomes a toss-up. K10, K17, K21 and K25 stay demoted under either bar.

## Items I would not keep as primary

| Item | Why | Confidence |
|---|---|---|
| K06 | Narrower than claimed. The real gap is that the automatic path does not bind the upstream inputs (`Step`, context). Upstream has an ungated `uninterrupted` preset, and the self-test in the packet ran EGM unattended six times. The "retained explicit-invocation policy" half is raised with the owner in Q2 (plan:275). | 0.65 |
| K10 | The matcher is as narrow as stated, but the draft keeps the D31 triggers on purpose and re-checks them in X5. No step fails. | 0.75 |
| K16 | The code facts are right, but the draft never says option 2 is done with `--skills none`. It is an unlisted work item, and no rule is contradicted. | 0.55 (closest call) |
| K17 | Zero-token detection of functional overlap and contradictory policy is promised without a mechanism. That is an overpromise, not a contradiction. | 0.65 |
| K21 | Affects only installs with an explicit recipe, where keeping the selection is documented behavior. Default installs pick up new skills, and 2.0.0 was never released. | 0.85 |
| K24 | The S arm is undefined for design documents. The arms are fixed in a PREREG before any run, and the natural reading is coherent. | 0.60 |
| K25 | An incomplete decision rule, which the tier definitions name as secondary ("weaker acceptance rule"). K23 is the same kind of gap and is already secondary. | 0.70 |

## Edits I propose

- **K02** (primary status 0.6, need for the edit 0.8). Its second route credits "0.23 is an aggregate, not isolated to symbol lookup", which a generic caveat satisfies.
  - Require a packet counterexample for the range (graphify 0.76–1.04, or OAW 1.04 on Opus 4.8).
  - Or require packet evidence of another cause: `codemap-comparison:52-53`, the prompt hook. Add that line to the evidence.
  - Move the bare "aggregate" remark to `mention_only_if`.
- **K29** (primary status 0.7, need for the edit 0.8). One sub-claim does not hold: "the per-experiment cap is not reconciled with X2's exception". The draft states that X2 exceeds the cap and takes it to the owner (plan:244, 276).
  - Delete that clause from the claim.
  - Delete the matching "Also sufficient" sentence from `detected_if`, and add it to `mention_only_if`.
- **K06**, if kept at any tier: narrow the claim to the unbound inputs and drop the "unchanged explicit-invocation policy" route.
- **K15**, optional wording: the draft wraps the catalog and names `add`, `taste`, `builds` and `restore`; it never says it reuses `absorb`. "The only install path of the catalog it wraps" is accurate.
- **K05, K18**, optional: their `not_adjudicable_if` clauses describe a vague report; score that case as not detected. K02 has the same problem, covered by its edit above.

## Secondary pass

- **K03 → same tier as K02.** Both are rationale statements that the cited evidence contradicts (plan:44 and :300 against validation:16 and :41-42). K03 is also the stated reason for owner decision Q1. Either promote K03 or demote K02.
- No secondary item looks wrong. I spot-checked K04 (25 rendered policy lines, 23 top-level commands) and K13 (callers and affected are Python-only); both hold.

## Overlaps among primaries

- **K24 and K25** (partial). Both concern X2's S arm and both cite plan:264. One sentence about "deep falls back to an unvalidated S" can satisfy both.
- **K15 and K18** (partial). Same root: the catalog's managed layer is text-only. K15 sees it at install, K18 at restore. K18 has a guard against the install-side remark; K15 has no guard in the other direction.

## Things about the key as a whole

1. **Concentration.** Five of the 16 primaries (K14–K18) are about W3 and are found only by reading `catalog.py`, `catalog_core.py` and `oaw.py`; three of the nine I would keep. Report recall per cluster as well as overall.
2. **`not_adjudicable_if` used for vague reports** (K02, K05, K10, K18). If "not adjudicable" removes the item from a report's denominator, a vague report scores better than a wrong one.
3. **`mention_only_if` is easy to satisfy** with generic remarks in K09, K15, K18 and K29 ("twelve cases are small", "the budget is optimistic"). Keep it out of the primary recall figure.
4. **Tier consistency.** K02 with K03, and K25 with K23, are same-class pairs at different tiers.
5. **Outside knowledge.** No primary needs it. K06's strongest objection would rest on live host behavior, which its rule correctly excludes.
6. **What the key can measure.** It is the union of two historical reviews, so it measures recall against those findings and cannot measure precision.

## Appendix: noticed in passing, not covered by any item

- plan:34 says unfounded accusations were 0 with both graders agreeing. validation:71 gives totals of 1 (Opus) against 7 (Codex) on the EGM data, with no per-arm split in the packet, so this cannot be settled from the packet.
- plan:234 decides "S equals E within ±0.10" from 12 cases run once each. One case is 0.083 of the scale, and validation:41-43 puts the detectable difference near 0.09–0.10. Adjacent to K09, not covered by it.
