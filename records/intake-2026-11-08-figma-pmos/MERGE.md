# Merged screen (2026-11-08)

Codex's screen (`SCREEN_codex.md`, gpt-6.1-sol, reasoning high, read-only, written without seeing Claude's) and
Claude's (`SCREEN_claude.md`, frozen first). Per `CRITERIA.md`, Codex's pick stands where they disagree.

## Units to build: two

| Unit | Codex | Claude | Merged |
|---|---|---|---|
| I18 cheap judge | Offline judge-calibration adapter first, tier A, zero model calls; a candidate model is admitted later only past accuracy bars | Test a small model on the V3 gold set directly, tier B | **Codex**: offline adapter first |
| I16 bug bash from a written plan | Bounded recipe, tier B; CLI journeys first, browser later | Same idea, tier B/C | **Both**: Codex's frozen BASH test |
| Re-taste defaults on model change | Not picked: native ablation is already policy; run the existing work first | Picked, tier A | **Dropped** (Codex) |

Frozen tests are the JUDGE and BASH tests in `SCREEN_codex.md` section 3. First steps: JUDGE fixtures from existing
JSON with zero model calls; BASH starts by mapping existing regression cases to user journeys.

## Answer to the owner's question: where a fast yes/no judge fits

- Output is a typed label with an evidence pointer and "unknown", not a bare yes/no.
- Candidate uses: fact present/absent/contradicted in grading (bar F: 100% on V3 known labels, then 98% macro-F1 on an
  adjudicated holdout); advisory review flags (bar S: precision and recall 95%).
- Never: merge clearance, consent, license or safety clearance, isolation checks, statistics, adopt/decline
  verdicts, or suppressing findings. Those stay deterministic or with the owner.
- Under D32, a calibrated cheap judge could take at most one family's grading slot.
- V3 has only 4 underlying questions (24 answers, 116 labeled cells); the existing graders scored 100% on simple
  labels but 50-100% on injected-pair detection, so V3 alone cannot admit a judge.

## Where Codex says OAW is worse (findings, not yet acted on)

1. Review outran its stopping rule: the 2.0.1 plan records 18 review rounds against a stated maximum of 3.
2. Evaluation preparation can consume the experiment: X1 spent about 22M tokens on question authoring.
3. The EGM default outruns its evidence (X2 is the redo).
4. The development workspace still feeds placeholder template text at startup (root `CLAUDE.md`, `AI_CONTEXT.md`).
