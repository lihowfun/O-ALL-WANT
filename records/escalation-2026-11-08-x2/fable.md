Reviewing the inlined material and answering the three questions directly.

## 1. Design: a two-stage sequential confirmatory run

Pick option c. Option a spends most of 25M and by construction decides nothing, and the owner still needs a second bank later. Option b commits 40M with uncalibrated floors and no way to stop paying for E when E is clearly not winning. A sequential design turns the pilot into stage 1 and keeps the decision confirmatory.

**Bank.** 16 unseen defect cases, 8 authored by Opus and 8 by Codex, 3 defects each, plus 4 unseen clean cases. Keep `events` and the old clean case as descriptive replication only, outside the primary analysis.

**Calibration before scoring.** Run N three times on 3 extra defect cases per host, excluded from the primary analysis. Use the resulting per-host within-case SD as the floor for every arm, and prereg the assumption that E's floor is no larger than N's. Make defect-level clustered standard errors the primary interval, so the floor is only a lower bound.

**Stages.**
- Stage 1: 10 defect plus 2 clean cases, all arms. X costs nothing extra.
- Stage 2: 6 defect plus 2 clean. Cheap arms always run stage 2. E runs stage 2 only if it passes a prereg'd futility rule after stage 1: its point-estimate gap over the better of N and R is at least +0.05 with both graders. Otherwise E stops and is recorded as "did not reach the gate".
- Keep the 0.10 equivalence margin. With 16 cases the floor half-width is about 0.054, so equivalence can actually be established.

| Item | Claude logical tokens |
|---|---|
| Authoring and dual verification | ~1.5M |
| Calibration, 9 N runs | ~1.8M |
| Stage 1: 12 E runs, 24 N/R runs, 72 grades | ~24M |
| Stage 2 cheap arms and grades | ~4M |
| Stage 2 E, 8 runs, only if not futile | ~12M |
| `events` replication, 1 E run | ~1.5M |
| Total | ~33M if E stops early, ~45M if it continues |

Ask the owner for a 45M ceiling now with this range stated. The worst case matches option b, and the design is cheaper exactly when E is not winning. Before freezing: fix every bug Codex listed, have Codex re-review the revised prereg, and have Codex rather than Claude run the judge script on the final data, as the audit's rule 5 requires.

## 2. Decision rule and the interim default

The current rule is wrong in one place. It applies one superiority bar to arms whose costs differ by 28x, so a free checklist that ties native loses, and a cheap tie leaves the user with nothing. Use cost-tiered gates:
- **Free tier, R versus N.** Adopt R if it is established non-inferior on detection within 0.10 with both graders, established non-inferior on unsupported claims within 0.5, and has zero dual-confirmed false alarms. Otherwise N.
- **Costly tier, E and X.** Adopt only if superior to the best free arm, not merely to N, with both graders, plus the same two safety gates. X also requires the second host to be configured on the user's machine.
- "Undetermined" never passes a gate. Any incomplete arm makes the cell unresolved, never a decision.

Keep the "cheapest among arms equivalent to the best" selection. It becomes meaningful once 16 cases make equivalence establishable.

While X2 is unresolved, auto should be native, with EGM available through "on", and the ledger should say "not tested" per the audit's category 6, not "declined". A 28x default cannot rest on one selected case. R is also untested and may add unsupported claims, so do not preempt X2 with it.

## 3. Next week, ranked

1. **X2 fixes, revised prereg, calibration, freeze, start stage 1.** It is the audit's highest-risk judgment, the design is already reviewed, and the fixes are cheap.
2. **Merge X1 with the codegraph/graphify/OAW-map rejudge into one ERPNext map experiment.** Arms: no map, OAW map, codegraph, graphify. Codex authors tasks blind to the implementations, Claude operates a frozen runner, Codex applies the rule. Design and freeze this week, run after X2 or in parallel on the Codex plan.
3. **X1 alone** only if the merge is refused. Running it separately duplicates the bank and leaves the audit's override finding on codegraph unresolved.
4. **Drawn-map feature.** Do not ship it as a default. Smoke-test it and register it as a fifth arm of item 2. New code with no measured use case is exactly what the audit warned about.
5. **Figma PM OS interview.** One hour to write the intake note. The cheap yes/no judge idea gets a free test inside X2: add a Haiku grader as a descriptive third grade and report its agreement with Opus and Codex. Bug bash from a plan and skill pruning go to the backlog with reversal conditions.

Bottom line: run X2 as a prereg'd two-stage design under a 45M ceiling, switch the rule to cost-tiered gates, ship native as the interim auto, and fold X1, the rejudge and the drawn map into one independent map experiment.
