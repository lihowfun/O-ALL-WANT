# Independence audit of past intake verdicts (2026-11-08)

- Owner asked whether past review and intake verdicts were self-review and self-judgment (自審自裁), and named
  Codex as the independent unit.
- `CODEX_AUDIT.md`: Codex CLI 0.167.0, gpt-6.1-sol, reasoning high, read-only sandbox, user config ignored,
  ephemeral. Brief written by Claude; the report is Codex's text with local paths replaced by relative links.
- Verdict: yes, substantial parts were self-judged. Claude designed, ran, interpreted and applied most verdicts;
  cross-family grading (V4, V5, V8) was real but did not cover design or decisions.
- Claude checked two claims against the records before accepting them:
  - codegraph: the registered rule gave "equally good and cheaper" (`digestion-2026-11-06/taste-codegraph/RESULT.md`
    line 76-92), yet the ledger said decline because "OAW's own tools do the same" (line 85). Confirmed: the builder
    of the competing component overrode a passing rule.
  - V5: `v5_judge.py` pools the original self-test runs of `events` (where the gain was first seen) with the new
    runs in one Fisher p. Confirmed: p = 0.048 is exploratory, not an independent confirmation.
- Most at risk (Codex): EGM as preferred deep review (X2 is the redo); codegraph rejection vs OAW map retention;
  TokenEconomizer's early conclusion; graphify's broad rejection; memory-check usefulness.
- Rules proposed for future intake are in the last section of `CODEX_AUDIT.md`.
