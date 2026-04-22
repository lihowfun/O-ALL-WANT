---
name: inheritance-check
description: "Spawn a fresh-context subagent to test whether a next session's agent can actually extract project state from the SOURCES lane files. Catches silently-stale AI_CONTEXT.md, memory entries too terse to reconstruct from, and gaps a current-context agent can't see."
triggers: ["does the next session know enough", "inheritance check", "onboarding test", "cold-start readiness", "is memory self-sufficient", "can a fresh agent pick this up"]
requires:
  - The SOURCES list (default: AI_CONTEXT.md, VERSION.json, last 5 memory entries, ROADMAP.md first 60 lines)
  - 3–5 project-specific questions the current agent believes should be answerable from SOURCES
optional_reads:
  - docs/archive/Inheritance_And_Promotion_Experiment_2026-04-21.md (origin of this skill)
outputs:
  - .agents/memory.md entry with [INHERITANCE-CHECK] tag + subagent pass/fail record
  - Optional: proposed SOURCES additions when coverage gaps surface
---

# /inheritance-check — Cold-Start Readiness Test

> **Why this skill exists**: OAW's memory + wiki system is designed so that
> a fresh session's agent can orient from a handful of files. But it only
> works if those files *actually* carry the current state. A current-context
> agent cannot self-audit this — too much is in their head.
> This skill spawns a **fresh-context subagent** to try, and scores what happens.
>
> Related: `harness-evaluator` (reviews a completed change); `read-discipline`
> (rules for what counts as "extractable").

## Three rules

### Rule 1: Questions must have extractable answers

Every question you ask must be literally answerable from SOURCES by a cold reader. "What's our next priority?" is not extractable; "What's in `task_state.in_progress` in `VERSION.json`?" is.

### Rule 2: Draft reference answers BEFORE spawning

Write down what the subagent *should* answer before you hand over the prompt. Post-hoc agreement with subagent output is confirmation bias.

### Rule 3: Score three failure modes distinctly

- **Exact** — answer matches reference.
- **Hallucination** — answer does not match reference AND is not supported by SOURCES.
- **Over-refuse** — answer is "INSUFFICIENT EVIDENCE" but the reference is in SOURCES. (See `read-discipline.md`.)

Don't collapse the last two. Hallucination says the rules failed on the *write* side; over-refuse says they failed on the *read* side. They need different fixes.

## Steps

### Step 1: Fix SOURCES

Default SOURCES for OAW-harness-using projects:
- `AI_CONTEXT.md` — architecture + commands
- `VERSION.json` — version + `do_not_rerun` + `task_state`
- `.agents/memory.md` — **last 5 entries only**, not whole file
- `ROADMAP.md` — **first 60 lines**
- `docs/knowledge/CURRENT_STATE.md` — **if it exists** (optional compiled single-entry-point)

Adjust per project. More is worse; the test is whether the **compiled cold-start set** is sufficient, not whether the whole repo is.

### Step 2: Draft 3–5 questions + reference answers

Questions should span:
- Operational state (what phase are we in? what's the version?)
- Recent decisions (last [DECISION] entry's gist)
- Guard rails (what's in `do_not_rerun`?)
- One *intentionally hard* extractable question — something the current agent knows is buried but should still be findable

Write reference answers in ≤15 words each.

### Step 3: Spawn fresh-context subagent

Use the Agent tool with `subagent_type="general-purpose"`. Prompt template:

```
You are a fresh-context agent with ZERO prior session history. Your ONLY task is
to answer the questions below using ONLY the files listed. Do not read other
files, do not run scripts, do not use git log.

ALLOWED FILES:
<list from Step 1>

FORBIDDEN: guessing. If the answer is not in the allowed files, answer with
"INSUFFICIENT EVIDENCE: <what's missing>". If the answer IS in the files,
extract it verbatim and cite the line.

QUESTIONS (answer each in ≤15 words, cite file:line):
1. <q1>
2. <q2>
3. <q3>
4. <q4>
5. <q5>

OUTPUT FORMAT: `Q<n>: <answer> — source: <file>:<line>`
Do not add preamble. Do not explain reasoning.
```

### Step 4: Score

For each question, classify the subagent's answer:

| Class | Criterion |
|-------|-----------|
| ✅ EXACT | Matches reference; cite is accurate. |
| ❌ HALLUCINATION | Answers confidently but wrong / not in SOURCES. |
| ⚠️ OVER-REFUSE | "INSUFFICIENT EVIDENCE" but reference is extractable from SOURCES. |
| 🟡 PARTIAL | Right direction, incomplete or imprecise. |

### Step 5: Record verdict to memory

Append to `.agents/memory.md`:

```
## [YYYY-MM-DD] [INHERITANCE-CHECK] <project state summary>

Score: <E>/<total> exact, <H> hallucination, <OR> over-refuse, <P> partial.

Failed questions:
- Q<n>: <class> — reference was "<ref>", subagent said "<actual>"

Proposed SOURCES additions (if any):
- <file/section> — would have answered Q<n>

Or: "SOURCES sufficient; no additions needed."
```

If any hallucination: **immediately** fix whichever SOURCE let it happen. Hallucinations in cold-start means current state is silently broken.

If any over-refuse: likely a `read-discipline.md` or question-phrasing issue. Raise in conversation; don't silently accept.

### Step 6: Decide whether to rerun later

- Score ≥ 4/5 exact, 0 hallucinations, 0 over-refuse → **green**, file is cold-start-ready.
- Score 2–3/5 exact → **yellow**, add flagged SOURCES and rerun.
- Score ≤ 1/5 exact or ≥ 1 hallucination → **red**, stop and fix before trusting the memory as hand-off material.

## When NOT to use

- Before any serious work has been done on the project — nothing meaningful to inherit yet.
- When you know the SOURCES are being edited right now — wait for stable state.
- For exploratory sessions — this skill is about *durable* state, not in-progress work.

## Example invocation

*(Dogfooded against OAW itself on 2026-04-21 — see
`docs/archive/Inheritance_Check_Dogfood_2026-04-21.md` for the verdict and
scoring.)*

## Reference

- `docs/archive/Inheritance_And_Promotion_Experiment_2026-04-21.md` — the
  experiment that validated the subagent-spawn approach for read-side
  testing.
- `templates/.agents/skills/read-discipline.md` — the write-side
  discipline this skill tests adherence to.
- `templates/.agents/skills/harness-evaluator.md` — sibling skill for
  change review (write-side equivalent of this skill).
