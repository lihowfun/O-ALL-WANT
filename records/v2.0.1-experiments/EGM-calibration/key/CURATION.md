# Frozen-packet curation

The key contains **30 items: 16 primary and 14 secondary**. All 33 historical findings are retained verbatim in the private ledger. Eighteen findings are verified as submitted, thirteen are partly verified with narrower claims, one is not verified, and one is not adjudicable. Thus 31 findings contribute at least one retained defect; “partly” does not mean half credit.

## Scope and evidence discipline

The target is the 2026-11-07 draft in the supplied packet, not the later revised plan. I opened the packet lines cited in KEY.json and LEDGER.json, inspected the relevant code branches, and used no network. I did not run or import packet code, run its tests, inspect the prohibited sibling workspace, modify inputs, or commit anything. A small curator-owned Python script assembled and structurally checked the artifacts; executing that script is not executing the software under review.

Appendix B supplies author dispositions only. Its blanket statement that 30 findings were changed is recorded as “accepted,” EGM 13 as “partly,” and EGM 16/native 15 as “declined.” It does not provide an individual acceptance rationale for all 30, and none is invented. A search locating Appendix B also displayed excerpts of the later plan; no later edits, experiments, decisions or costs were used as defect evidence. No historical stage-report-only observation or question was promoted into the key.

The supplied packet SHA-256 is copied exactly into KEY.json. Its directory serialization algorithm was not supplied, so I do not claim to have independently reproduced that aggregate hash. LEDGER.json records SHA-256 digests of both input reports, the author-appendix excerpt and every cited packet file for an independent check. No retained item depends on hindsight. `needs-context` flags survive for limited historical subclaims even where a narrower packet-supported claim is retained.

Finished KEY.json SHA-256 (curated 2026-11-14, before any rerun in this task): `c5e672866b97d29d23d83b286ec8bcef577b635f973ff8474d3ad77b4e087f93`. This fingerprints the key bytes, separately from the user-supplied packet identifier.

## Counts and source balance

| Source | Findings | Verified | Partly | Not verified | Not adjudicable | Findings retained | Primary items | Secondary items |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EGM | 18 | 4 | 13 | 1 | 0 | 17 | 9 | 12 |
| Native historical review | 15 | 14 | 0 | 0 | 1 | 14 | 12 | 3 |
| Union | 33 | 18 | 13 | 1 | 1 | 31 | 16 | 14 |

Item counts are unique within each source; they must not be added across sources. There are 6 shared clusters, 15 EGM-only clusters, and 9 native-only clusters. These are provenance counts, not a newly graded historical contest. EGM 18's review-budget label observation is related context, not by itself detection of the primary omitted-cost mechanism; EGM 5/6/8 independently establish that primary item.

Both sources contribute exclusive primary defects. The native report contains more direct code-to-promise incompatibilities; its claims are usually narrower and straightforward to verify. The EGM report more often bundles several mechanisms, broad policy interpretations, cost projections and suggested experimental improvements. Its exclusive observations therefore required more narrowing and tier judgment. This is an asymmetry in these reports' claim formulation and available evidence, not evidence that one method is intrinsically more or less valid. Report severity and author acceptance did not determine tier: the map-number finding is primary despite native “minor,” while the TS-engine scope finding is secondary despite EGM “blocker.”

Shared items:

- K02: Map efficiency evidence overstatement (primary).
- K04: Inaccurate current footprint counts (secondary).
- K05: Review invoked after its prerequisite implementation (primary).
- K15: User installation reuses an incompatible absorption engine (primary).
- K18: Restore snapshots exclude promised runtime configuration (primary).
- K24: X2 standard arm has the wrong input contract (primary).

EGM-only items:

- K01: Grader agreement extrapolated to code review (secondary).
- K03: Misstated resolution rationale (secondary).
- K06: Automatic EGM conflicts with retained manual contracts (primary).
- K07: New agent violates exact generated inventory (primary).
- K08: Undefined review-plan command contract (secondary).
- K11: Automatic deep lacks a per-task budget contract (secondary).
- K13: TS parsing understates call-graph scope (secondary).
- K20: Policy-cut validation scheduled after the cut (secondary).
- K21: New default skills do not enter explicit recipes (primary).
- K22: Release checklist omits existing upgrade and metadata contracts (secondary).
- K23: X1 quality decision table is underspecified (secondary).
- K26: Known ceiling case retained in the detection panel (secondary).
- K27: X3 cannot establish improvement over current routing (secondary).
- K28: Context gate precedes the shipping configuration (secondary).
- K29: Approval budget omits required work and overstates fallback certainty (primary).

Native-only items:

- K09: Within-question inference without repeated observations (primary).
- K10: New-plan trigger narrower than promised (primary).
- K12: Completeness confused with resolution certainty (secondary).
- K14: Management commands absent from project payload (primary).
- K16: No policy-free management installation (primary).
- K17: Free installation overpromises semantic conflict detection (primary).
- K19: Tasting prompt violates one-question flow (secondary).
- K25: S replacement bypasses review-quality eligibility (primary).
- K30: New verdict semantics cannot be enforced by the reused ledger (primary).

## Clustering and judging conventions

An item represents a root cause, not a report row, reviewer severity or proposed fix. For example, untasted text, executable payloads and bundled-name rejection are witnesses of one incompatible absorption contract (K15). They do not earn three scores. Restore exclusion (K18) remains separate: widening installation eligibility does not make excluded configuration restorable. Review timing (K05) and mandatory manual workflow gates (K06) are independently failing contracts. Defining X2's S treatment (K24) does not fix the unsafe selection rule (K25).

Some historical rows bundled independent defects and therefore map to several items: notably EGM 2/5/8/11 and native 10. This is decomposition of multi-claim findings, not splitting one defect into several scores. Conversely, omitted second-X3 cost, omitted live E2E cost, grading overhead and the unguaranteed X2 fallback are one budget-reconciliation item (K29). The two present-size counts are one small baseline-footprint audit (K04); this secondary grouping cannot affect primary recall.

IDs follow the principal substantive location in the draft, not the earliest summary allusion and not source-report order. The anchor table below makes that ordering auditable. A primary item needs an executable-contract failure, consequential unsupported promise, invalid inference method, or a materially contradicted decision premise. Missing implementation detail alone is secondary. A future feature's absence from current code does not automatically make its plan defective. Where Q1/Q2 are pending, evaluate the recommended approved branch; approval changes permission, not existing engine or upstream contracts.

For a new report, apply each item's `detected_if` by mechanism. Exact wording, file-line citation, a historical severity label and a proposed fix are not required if the report identifies the mechanism unambiguously. Count an item at most once even if it appears in several findings. A single finding can detect two items only if it actually states both independent mechanisms. Do not require every example within a cluster: the explicit acceptable alternatives in `detected_if` define the minimum.

Questions and uncertainty sections are not automatically discarded. A question that explicitly asserts the concrete failure mechanism can detect an item (for example, “How can pre-implementation review occur if the only invocation is after edits?”). “Which preset?” or “check migration” is mention-only. Merely naming an area is not detection. Keep a separate mention-only count. Do not let a bare question acquire a mechanism through the grader's own knowledge of this key.

Use `not_adjudicable_if` only when deciding the asserted mechanism requires unavailable facts or the report's referent/assumption cannot be resolved. It is not partial credit, not a substitute for a clear negative, and not a way to ignore a wrong claim refuted by the packet. If an exaggerated finding contains the correct minimal mechanism, credit that mechanism and separately note the unsupported extension. Report detected / mention-only / not detected / not adjudicable separately; do not silently remove ambiguous items from the denominator to inflate recall. Primary recall is over the fixed primary set, with any adjudication uncertainty stated.

The key contains no historical-source attribution. Keep LEDGER.json and this document away from graders if source blinding is intended. Freeze the key and its rubric before collecting any new review. A later independent correction needs a new version and a documented reason, never an adjustment selected to improve a tested model's score.

## Primary items

- **K02 — Map efficiency evidence overstatement.** The draft says all three maps reduced tool calls to 0.23–0.65 of native, although several measured conditions were 0.76–1.04. It also attributes codegraph’s aggregate 0.23 ratio to symbol lookup without a measurement isolating that mechanism.
- **K05 — Review invoked after its prerequisite implementation.** The replacement policy invokes oaw-review after changes are made, but deep review requires a plan and its EGM review before implementation. Classifying only the finished diff cannot supply that prerequisite review.
- **K06 — Automatic EGM conflicts with retained manual contracts.** Q2 proposes authorizing automatic EGM, but the specified implementation still follows the installed upstream/manual workflow without binding the inputs and preset that avoid owner prompts or reconciling the retained invocation policy. As specified, the owner-free deep flow can stop at mandatory human gates.
- **K07 — New agent violates exact generated inventory.** Adding templates/.claude/agents/oaw-goldfish.md as specified violates the exact EGM adapter inventory enforced by the existing harness gate. The plan does not change that ownership/checking contract.
- **K09 — Within-question inference without repeated observations.** The planned within-question paired bootstrap and pooled within-question variance floor have no repeat observations to resample or estimate in X1/X2’s one-run-per-question-per-arm design. The plan must change the resampling unit or explicitly supply a defensible external variance source.
- **K10 — New-plan trigger narrower than promised.** The unchanged classifier does not implement the advertised deep trigger for new design documents generally: it recognizes only added docs/designs/*.md paths or design*.md filenames. A new docs/plans/v2.0.1-execution.md alone falls through as light despite the plan’s stated trigger.
- **K14 — Management commands absent from project payload.** The documented project-relative add/list/remove commands and /oaw-add backend have no delivery path: oaw.py stays in the framework checkout and is not part of the installed project. The draft must provide an installed launcher and dependencies or a checkout-based command with an explicit project target.
- **K15 — User installation reuses an incompatible absorption engine.** W3 promises installation before tasting, script-bearing/runtime components, and bundled-name conflict choices through a wrapper around catalog. Its reused absorption engine instead holds untasted text and executable components, never installs hooks/MCP, and rejects bundled-name collisions; the installation and default-promotion contracts must be separated or changed.
- **K16 — No policy-free management installation.** Option 2 promises only A/B/C, with no OAW skills or policy, but an empty skill recipe still installs OAW policy/helpers and doctor requires them. A management-only manifest/install/health-check mode is needed; --skills none alone cannot deliver this option.
- **K17 — Free installation overpromises semantic conflict detection.** The zero-agent-token add path promises functional-overlap and contradictory-policy detection without specifying a semantic representation, declared metadata, or a bounded rule set. The reused static pattern scanner does not establish that general capability, so the promise needs a narrower deterministic scope or an explicit optional analysis step.
- **K18 — Restore snapshots exclude promised runtime configuration.** W3 reuses catalog builds/restore while permitting hooks and MCP installation and promising byte-identical removal. Those restore points explicitly exclude host settings and MCP files, so they cannot restore configuration written by the promised installer.
- **K21 — New default skills do not enter explicit recipes.** The migration promise that new skills will be added is incompatible with preserving prior explicit skill selections. The plan needs a rule distinguishing default-recipe upgrades from user exclusions; merely adding new templates does not add those skills to existing explicit recipes.
- **K24 — X2 standard arm has the wrong input contract.** X2 tests S on design documents and may use it for deep plan review, but the only defined standard treatment reviews a code diff and tests. The experiment lacks an executable design-review S treatment tied to the behavior that would ship.
- **K25 — S replacement bypasses review-quality eligibility.** The S-for-E replacement rule checks detection equivalence and price but not S’s false-positive safety. The separate E-fails-to-generalize fallback also chooses S without an acceptable S-versus-N result, so the plan can install a treatment that has never met its own review-quality requirements.
- **K29 — Approval budget omits required work and overstates fallback certainty.** The approximately 23M approval budget leaves required work uncosted, including the second X3 pass, live deep E2E, and Claude grading/question preparation; its listed approximately 22.5M subtotal leaves little room for these. The eight-new-case fallback is also not demonstrably within 10M at the observed EGM cost range, and the blanket per-experiment cap is not reconciled with X2’s exception.
- **K30 — New verdict semantics cannot be enforced by the reused ledger.** The new protocol separates equivalence from uncertainty and uses cost intervals, but record-tasting still accepts only better/same/worse and derives outcomes from a point cost ratio. A statistics module alone cannot make the old catalog record and enforce the new decisions without an explicit mapping or validator/schema change.

## Three hardest calls

1. **EGM 3: TS/JS scope, K13 secondary, partly verified.** `code_index.py:1525-1534` and `1594-1596` prove the existing traversal is Python-only. But draft line 139 explicitly schedules TS/JS call-point work. Calling all missing TS functionality an impossible or blocking plan would penalize a plan for proposing new code. The retained defect is the understated resolver/traversal scope needed for recall and call-ranked overview, not an asserted inability to build it. A second checker should reconsider this tier first if using a stricter implementation-readiness definition.
2. **EGM 16: removal complaint, not verified.** The 11-06 self-test reports a real earlier leak, but `oaw.py:310-319`, `430-451` and `catalog.py:2021-2032,2050-2070` already show omission/retirement and delegated migration in the frozen code. Custom edited files deliberately remain conflicts. This rejection is based on packet code, not the author's later assertion of a fix. No hindsight is needed.
3. **Native 15: alleged NFS incident, not adjudicable.** The packet has NFS indexing slowness and TokenEconomizer ceiling results, not the claimed clock-skew incident. The later author's pointer names an earlier source outside the packet, but neither acceptance nor rejection can be proven from that pointer. Lack of packet support is not proof that the incident was fabricated. No key item is created and the outside record is not opened.

## Other important decisions and exclusions

- **Budget, K29: primary, but not a false arithmetic objection.** The displayed costs are approximately 7 + 11 + 1.5 + 0.3 + 0.3 + 2.4 = 22.5M, which can reasonably round to 23M. The blocking issue is required work outside those entries: another X3, deep E2E and Claude grading/question creation. Nine E runs span 9.63–12.87M at the supplied range; eight span 8.56–11.44M before N/S and overhead. The report's 10.2M lower bound is not repeated. The eight-case fallback is not guaranteed to fit; an exact future total is not claimed. No later actual cost of reviewing this document is used.
- **Singleton statistics, K09: primary without external source code.** One value per question/arm cannot estimate repeated-run variance within that cell. More questions can support a different estimator; this is not a claim that 12 × 1 is intrinsically bad. The defect is the stated resampling/floor contract. Historical variances could be a repair, but no selected external floor is specified.
- **Catalog verdict integration, K30: primary and distinct from the statistical estimator.** Even valid intervals do not change `record-tasting`'s three-state point-ratio validation. Mapping uncertainty to same can contradict line 77. Do not require a new schema if an explicit faithful compatible mapping can work.
- **Automatic workflow, K06: primary but conditional.** Q2 does ask permission to change manual invocation. That resolves the authorization proposal in principle, not upstream `Step`, context or split prompts. The installed skill requires preserving checkpoints. Upstream already has an uninterrupted preset and report names (`vendor/egm/skills/egm-review/SKILL.md:261-293`), so missing report location alone is not a defect. Unverified host limitations are excluded.
- **X1, K23: secondary.** The experiment table is underspecified, but line 77 explicitly forbids promoting undetermined quality. A consistent reader can honor that prohibition. Do not elevate ambiguous local wording into an unequivocal permission to violate the global rule.
- **X2 arms, K24 and K25: primary; ceiling case, K26: secondary.** S has no design-document treatment and can replace E without its own safety eligibility. Those affect execution/selection. A saturated orders case weakens or conflicts with the stated panel design but could legitimately be a control; its inclusion does not alone invalidate nine new cases. The desired nonleaking readiness-checklist arm is a useful alternative, not required by a demonstrated rule. The observed P leaked defect information and cannot prove a real cheap substitute works.
- **X3, K27 and K20: secondary.** Missing status quo means the test cannot establish the value of the upgrade; it can still answer A-versus-B. Missing pre-cut placement is a schedule gap that can be fixed by splitting W4, not an unavoidable dependency cycle. Its omitted second-pass cost is counted once under K29.
- **Cross-family review, K01: secondary.** Grader agreement is not a reviewer-family experiment. No packet evidence proves cross-family review ineffective, or establishes the authorization state of every installing user. A universal extra vendor-consent question is not imported as a primary item.
- **D32 approval allegation: not retained.** W0 says “according to Q1,” and Q1 asks approval and supplies a fallback. Calling the proposal D32 before it appears in the log is not itself an unauthorized decision. The contradicted resolution rationale survives separately as K03.
- **Policy/doctor allegation: narrowed.** Existing tests do bind old policy text (`tests/test_oaw_mode.py:374-380`), and the retained manual policy needs adaptation. But doctor also recognizes the helper through manifest ownership (`oaw.py:766-773`), so replacing its policy mention does not automatically break doctor. Test updates are consequences of that policy transition, not an extra score.
- **Release, K21 primary and K22 secondary.** Explicit recipes really preserve their skill list, contradicting automatic addition. v1 migration already exists, and VERSION can be shorthand; the omitted v1 validation/version-ledger checklist is not proof v1 is broken.
- **Semantic conflict promise, K17: primary with a bounded claim.** The defect is an advertised semantic capability without a mechanism, metadata contract or declared scope in a zero-token static path. It is not a theorem that semantic checking always requires an LLM. Structural conflicts and declared overlap could be a valid repair.
- **EGM 18's approximate numbers: narrowed.** The current CLI count is directly checkable. A not-yet-built skill's approximately 180 tokens is not disproved by court's matching measurement; no plagiarism inference is made. The reuse fraction depends on treatment and grading costs, so neither one-third nor one-half can be established from the packet. The EGM/code-review budget label inconsistency is retained as related accounting context, not a separate primary detection threshold.
- **Runtime-install owner decision allegation: narrowed.** The catalog incompatibility is direct evidence. Whether every user-requested install needs a new toolkit-owner decision is not established simply by applying maintainer tier-C rules to a new user route that already includes consent.
- **No expansion from unnumbered questions/uncertainties.** Host discovery probes, in-session effort behavior, missing outside statistical code, style preferences and EGM unfounded-claim totals were not among the 33 findings or lack enough evidence. The V4 EGM unfounded-claim total is not broken down by arm, so it cannot refute the draft's E-only zero claim by itself.

## Complete finding inventory

E = EGM report; N = native historical report. Indices are one-based. Full original objects, evidence and narrower adjudications are in LEDGER.json.

| Finding | Historical severity | Curator status | Item(s) | Author disposition |
|---|---|---|---|---|
| E01 | blocker | partly | K15, K18 | accepted |
| E02 | blocker | partly | K05, K06 | accepted |
| E03 | blocker | partly | K13 | accepted |
| E04 | major | verified | K02 | accepted |
| E05 | major | partly | K24, K26, K29 | accepted |
| E06 | major | partly | K29 | accepted |
| E07 | major | partly | K23 | accepted |
| E08 | major | verified | K27, K20, K29 | accepted |
| E09 | major | partly | K06, K04 | accepted |
| E10 | major | partly | K07 | accepted |
| E11 | major | partly | K21, K22 | accepted |
| E12 | major | partly | K11 | accepted |
| E13 | major | partly | K01 | partly |
| E14 | major | partly | K03 | accepted |
| E15 | major | verified | K08 | accepted |
| E16 | major | not verified | Excluded | declined |
| E17 | minor | verified | K28 | accepted |
| E18 | minor | partly | K04, K29 | accepted |
| N01 | major | verified | K09 | accepted |
| N02 | major | verified | K30 | accepted |
| N03 | major | verified | K05 | accepted |
| N04 | major | verified | K10 | accepted |
| N05 | major | verified | K14 | accepted |
| N06 | major | verified | K16 | accepted |
| N07 | major | verified | K15 | accepted |
| N08 | major | verified | K18 | accepted |
| N09 | major | verified | K17 | accepted |
| N10 | major | verified | K24, K25 | accepted |
| N11 | minor | verified | K19 | accepted |
| N12 | minor | verified | K12 | accepted |
| N13 | minor | verified | K02 | accepted |
| N14 | minor | verified | K04 | accepted |
| N15 | minor | not adjudicable | Excluded | declined |

## Principal draft anchors

| Item | Main draft line | Tier | Cluster |
|---|---:|---|---|
| K01 | 36 | secondary | Grader agreement extrapolated to code review |
| K02 | 37 | primary | Map efficiency evidence overstatement |
| K03 | 44 | secondary | Misstated resolution rationale |
| K04 | 45 | secondary | Inaccurate current footprint counts |
| K05 | 83 | primary | Review invoked after its prerequisite implementation |
| K06 | 83 | primary | Automatic EGM conflicts with retained manual contracts |
| K07 | 87 | primary | New agent violates exact generated inventory |
| K08 | 88 | secondary | Undefined review-plan command contract |
| K09 | 96 | primary | Within-question inference without repeated observations |
| K10 | 108 | primary | New-plan trigger narrower than promised |
| K11 | 108 | secondary | Automatic deep lacks a per-task budget contract |
| K12 | 138 | secondary | Completeness confused with resolution certainty |
| K13 | 139 | secondary | TS parsing understates call-graph scope |
| K14 | 157 | primary | Management commands absent from project payload |
| K15 | 164 | primary | User installation reuses an incompatible absorption engine |
| K16 | 170 | primary | No policy-free management installation |
| K17 | 173 | primary | Free installation overpromises semantic conflict detection |
| K18 | 175 | primary | Restore snapshots exclude promised runtime configuration |
| K19 | 176 | secondary | Tasting prompt violates one-question flow |
| K20 | 198 | secondary | Policy-cut validation scheduled after the cut |
| K21 | 217 | primary | New default skills do not enter explicit recipes |
| K22 | 218 | secondary | Release checklist omits existing upgrade and metadata contracts |
| K23 | 233 | secondary | X1 quality decision table is underspecified |
| K24 | 234 | primary | X2 standard arm has the wrong input contract |
| K25 | 234 | primary | S replacement bypasses review-quality eligibility |
| K26 | 234 | secondary | Known ceiling case retained in the detection panel |
| K27 | 235 | secondary | X3 cannot establish improvement over current routing |
| K28 | 236 | secondary | Context gate precedes the shipping configuration |
| K29 | 239 | primary | Approval budget omits required work and overstates fallback certainty |
| K30 | 305 | primary | New verdict semantics cannot be enforced by the reused ledger |

## Curator-found appendix

**No additional independently verified blocking defect was identified outside the 33 findings.** This is not a completeness claim about the draft. New witnesses of an existing reported mechanism (for example upstream intake prompts supporting the reported unattended-flow defect) stay within that cluster; they do not create curator-only items. No appendix candidate enters the key or the primary denominator.

## Calibration suitability and second-check priorities

This is a useful but narrow calibration target: there are 16 primary items, not merely one or two. Their supporting evidence is in the packet; no primary requires a later incident record or live host experiment. The statistical item requires understanding what a resampling unit is, but does not require an unavailable statistical implementation. The stronger code-contract items can be checked by reading a handful of explicit branches.

The main limitations are one Chinese-language plan, a large code/evidence packet, conditional owner proposals, and correlated items within the same review/install/evaluation workstreams. Several findings concern missing contracts rather than a concrete line of faulty new code, so grading can drift if reviewers are rewarded for generic “needs detail.” Secondary items must not be mixed into blocking-defect recall. The historical union is an ascertainment-limited reference set: perfect primary recall means all verified historical blockers were detected, not that the plan has no other defects. The curator-found appendix is empty, not a guarantee of exhaustive discovery. Historical source models and the plan author can contaminate future grading; hide provenance and preserve the same packet, instructions, output limits and grading rules across reruns.

A second independent checker should first examine (1) the primary/secondary boundary for K13, K17, K06 and K14; (2) packet-code precedence for the rejected removal finding; (3) the singleton inference and catalog mapping independently; (4) the budget omissions without later review costs; and (5) whether both X2 failures are independently described rather than double-counting one undefined arm. Recheck the narrower X1 and orders-ceiling tiers if interpreting every unresolved acceptance-table ambiguity as blocking. Source-specific retained counts should be reviewed only after claim-level judgments, to avoid optimizing for either historical report.

Structural checks confirm valid JSON, all 33 original finding objects/indices, consecutive ordered IDs, complete historical provenance, valid packet citation paths/ranges and consistent counts. They do not substitute for the independent semantic check requested above. No packet test suite was executed.
