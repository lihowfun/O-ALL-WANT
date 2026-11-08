**1. Choose (b): one independently governed confirmatory run, targeting 40M Claude tokens.** A 25M pilot spends most of the necessary budget while deliberately leaving the default unresolved. EGM’s roughly 28× cost warrants testing for a substantial benefit; elaborate adaptive selection would add avoidable methodological risk.

- Use **20 unseen cases: 16 defect + 4 clean**, balanced by author family and declared defect categories. Keep `events` and the old clean case outside the primary analysis.
- Run N/R/E once per case on each host: **60 runs per host, 120 unique reports**. X reuses the other host’s N. Two graders mean **240 grading calls**, including 120 Opus calls.
- Expected Claude spend: **29.8M E + 4.0M N/R + 2.4M grading + 1.5M existing pilot + approximately 2M preparation = 39.7M**. This assumes N/R average 100k each.
- Request **40M expected, with an explicitly approved ceiling of 48M**: N/R averaging 300k would bring that estimate to 47.7M. Reconcile actual sunk costs before approval; a budget stop leaves the decision unresolved.
- Sixteen defect cases offer approximately **13-point optimistic single-comparison MDE**, not assured power for the full selection procedure. Multiple comparisons, grader agreement and safety gates make the effective requirement harder. Accept that small benefits may remain unresolved.
- Analyze **paired case-level outcomes**. Forty-eight planted defects are not 48 independent observations. Freeze multiplicity control across candidate comparisons and the rule for comparing eligible candidates.
- Require an independent statistical reviewer to approve host-appropriate uncertainty before launch. The borrowed Opus floor is a sensitivity assumption, not validated Codex calibration; do not lower it through a few favorable repeats or widen equivalence merely to obtain a winner.
- Fix the documented execution defects, freeze the complete protocol, and have an evaluator uninvolved in the competing implementations apply it. Another model family alone does not establish independence.

This buys a credible opportunity to decide, not a guaranteed winner. Do not spend another tranche automatically if the result is inconclusive.

**2. Keep the adoption gates; change the fallback and interpretation.**

Requiring detection superiority with both graders is defensible for adding recurring cost. Require **affirmative noninferiority** on unsupported claims from both graders; “not significantly worse” is insufficient. Freeze a tolerance justified by product consequences, including how severe false accusations are handled.

Zero dual-confirmed false alarms on four clean cases is a useful veto, **not evidence that false alarms are rare**. Even zero events leaves a roughly 53% one-sided 95% upper bound on a case-level event probability under an independent-case model. Report that limitation.

The fallback should be **native review**, not a conclusion that design review has no value. N is itself an explicitly requested review; this experiment does not compare it with skipping review or measure downstream implementation outcomes.

While X2 is unresolved, **`auto` should use one bounded native design-review pass**, described as provisional. Keep full EGM explicitly selectable. If “adds no design review” already preserves that native pass, the behavior is acceptable; make the wording precise.

After X2, choose the cheapest candidate whose benefit and safety are established and whose detection is demonstrably equivalent to the best eligible candidate. Incomplete data or unresolved equivalence must remain unresolved; arm order must never settle a tie. Cross-provider logical tokens also need provider-specific cost reporting before claiming one option is economically cheaper.

**3. Next week’s priority order:**

1. **Rejudge codegraph, graphify and OAW’s map under one independent protocol.** Correct the documented asymmetric treatment first; separate code-navigation, document/semantic and visualization claims, and preserve valid scoped adverse evidence.
2. **Finish X1 under that common governance.** It answers a concrete ERPNext workflow question for both priority hosts; align its cases and outcomes before further scoring, and retain earlier exposed results as exploratory.
3. **Repair, independently freeze and fund X2.** Then run the confirmatory comparison; native review is a workable provisional default, so an expensive rushed verdict has little value.
4. **Hold the new drawn-map feature as experimental.** Validate basic correctness, but defer expansion and automatic activation until the map comparison establishes what users gain.
5. **Defer the Figma PM OS intake.** Record the three hypotheses in the backlog; cheap judges require validation, bug bashes require outcome measurement, and skill pruning should follow evidence rather than become another self-judged absorption.