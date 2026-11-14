# Fast decision, first real example: the minimal-change card (written before any judge call)

2026-11-15. Purpose: show the fast decision end to end on real answers. The answers already exist
(U2 development and pilot runs, Codex CLI 0.167.2 / gpt-6.1-sol / high); nothing is rerun. What is run
now: the judge (Claude Haiku 5.5, low effort, tool-free, one request per answer and checklist) through
`fast_screen.py prompt` and `labels`, and `fast_screen.py verdict`.

Choices fixed here, before the first judge call:

- Food: the card (arm B, OAW 2.0.1 with the card). Without the food: arm A (OAW 2.0.1 without it).
- Tasks: P1, P2 and D2, the three tasks whose expected answer is a change with a patch. D1 is left
  out: its expected answer is "no change, no patch", so most of its items are about the absence of
  something, which a judge that must quote a passage cannot show.
- Runs: one per task and arm, as the rule says. Pilot tasks have three repeats; repeat 1 is used.
- The answer shown to the judge: `review_out/decision.md` followed by `review_out/proposed.patch`.
- Counted checklist (the rule asks for concrete items an answer should contain): the items the
  mechanical checker decides from the content of the answer. P1 and P2: a to h. D2: a, b, c, d, i.
  21 items. Left out: items about what the run did to the workspace (P1/P2 i, j, k; D2 e, f, g, h),
  which the answer text cannot show.
- Reader items (P1/P2 l to o; D2 j, k, l): the judge labels them too, in a separate checklist. They
  are reported and not counted, because they are judgements about the whole answer, not concrete items.
- Order, as the rule says: the arm without the food first. The food arm is judged only if step B
  leaves room.
- Token and time figures for the runs come from the recorded attempt rows; family `codex`.
- Known before running: the mechanical checker found every counted item met in these six answers.
  Not known: any judge label.
