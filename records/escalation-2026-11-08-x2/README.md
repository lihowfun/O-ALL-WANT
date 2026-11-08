# Escalation review: X2 size vs budget, the "auto" rule, next-week order (2026-11-08)

- Why: Codex gpt-6.1-sol judged the X2 design "fix first" (8 defect cases cannot establish equivalence). The open
  question was design size vs the D35 cap, so it went to the expensive tier (owner rule 2026-11-08).
- Same brief (`brief.md`, data inlined, no file access needed) to both, run in parallel, blind to each other:
  - Claude Fable 5.1 (`claude -p`, subscription, no API key): 14,409 input + 10,247 output tokens
    (24,656 logical, 147 s). Answer: `fable.md`.
  - Codex gpt-6-astra (Codex CLI 0.167.0, reasoning high, read-only, user config ignored, ChatGPT plan):
    22,711 input (12,160 cached) + 2,511 output. Answer: `astra.md`.
- Paths in all three files are made relative. The answers are verbatim otherwise.

## Where they agree

1. Do not run the 25M pilot design: it spends most of the budget and by construction decides nothing.
2. The confirmatory bank is 16 unseen defect cases + 4 unseen clean cases, balanced by author family.
   `events` and the old clean case are descriptive only.
3. That costs more than the 30M D35 cap. Fable: about 33M if E stops early, 45M ceiling. Astra: about 40M
   expected, 48M ceiling. Owner approval is needed either way.
4. While X2 is unresolved, `auto` should mean one native design review; full EGM stays available through `on`.
   The ledger should say EGM's default status is "not tested", not "declined".
5. The unsupported-claims gate needs affirmative non-inferiority from both graders (already in `x2_judge.py`).
6. The verdict is applied by an evaluator who did not build the competing parts (Codex runs the judge script on
   the final data, or an independent statistical reviewer signs off).
7. The drawn code map stays experimental (explicit use only) until a map comparison shows what users gain.

## Where they disagree

| Question | Fable 5.1 | gpt-6-astra |
|---|---|---|
| Design | Two stages: 10+2 cases all arms, then 6+2; E continues only if stage 1 shows a gap of at least +0.05 over the best cheap arm with both graders | One run of all 20 cases; adaptive rules add method risk |
| Gate for the checklist arm R | Cost-tiered: R adopted on non-inferiority to N | Keep the current superiority gates |
| First priority next week | X2 | Unified re-judgment of codegraph / graphify / OAW map |
| Figma intake | Free test inside X2: a cheap grader as a descriptive third grade | Defer; record hypotheses |

## Claude's recommendation to the owner (not a decision)

- Fable's two-stage design under a 45M ceiling. The futility stop can only err toward not adopting the 28x-cost
  option, which is the safe direction for a default; cheap arms always run all 20 cases.
- Keep the current gates (astra): changing them is a verdict-rule change that the owner has not approved.
- Add gpt-6-luna (ChatGPT plan, outside the Claude cap) as a descriptive third grader, which tests the Figma
  cheap-judge idea at no Claude cost.
- `auto` → native until X2 decides. This changes the D33 default, so it waits for the owner.

Status: waiting for the owner on the X2 ceiling and the interim `auto` default.
