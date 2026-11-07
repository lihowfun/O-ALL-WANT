# Screen by Claude (Opus 5.5), written before seeing Codex's

Picks (at most 3):
1. **Fast yes/no judge for grading and review** (Jev idea + owner question). Gap: every yes/no in grading
   (fact present or absent) and review (is this finding supported by its cited lines) is paid at Opus/Codex price
   (`records/.../validation/xgrade.py`, `egm-selftest/taste_grade.py`). Tier B. Test: on the V3 gold set
   (`digestion-2026-11-07/validation/v3`, known labels) a small model (Haiku 5.5, low effort) labels facts; pass if
   label accuracy >= 0.90 and planted-error detection >= 0.75 (the V3 thresholds) at <= 20% of the Opus grader's
   tokens. Second use, after X2: per-finding "supported?" filter, pass if it removes >= half of the unsupported
   claims both graders found while dropping no planted-defect detection.
2. **Agent bug bash from a written plan, run by the other family** (Codex + browser idea). Gap: OAW's merge gate
   asks for an end-to-end run but has no step that executes a written scenario list exhaustively and reports
   evidence (`CLAUDE.md` merge gate, `scripts/oaw_mode.py` steps). Tier B (skill text) or C (browser runtime).
   Test: seeded-bug small apps (CLI first, no browser), executor agent with the plan vs native "test this change";
   pass if detection is better on both graders (D32), no more false alarms.
3. **Re-taste defaults when the model changes** (pruning as models improve). Gap: catalog verdicts carry model and
   date but nothing flags a verdict as stale when the default model changes (`catalog/verdicts.json`,
   `scripts/catalog_core.py`). Tier A. Test: mechanical: list verdicts whose model differs from the current
   default; pass if every default skill has a verdict on the current Opus and Codex models, or is flagged.

Not picked:
- who owns this (people): OAW has no org data; code ownership via git history could join the code map later,
  after X1 shows whether agents use the map at all.
- what's up: needs Slack/project data OAW does not have; for a repo it overlaps `docs/knowledge/CURRENT_STATE.md`
  and `.agents/memory.md`. Would change if owners ask for a session-start digest of open decisions.
- start-of-session version check: OAW has `oaw.py doctor`; a per-session network hook is tier C for small value.
- parent/child repo: OAW install already keeps the template in `.oaw/` and user changes in `.oaw/user-skills.json`.
- spec skill that walks the codebase: covered by EGM draft plus the code map; measure through X1 and X2.
- build artifact, FigJam, coach: product-specific, not a framework gap.
- no telemetry: supports keeping the X5 trigger log local and opt-in; a policy note, not a unit.
- AutoXP single checkpoint: OAW already runs this way (D28: owner only at entry and release).
- terminal -> web front end: covered by the digest pane mod and artifacts.
