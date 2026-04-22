# R-1: Evaluator Design Decision

Date: 2026-04-20
Status: **Decided — proceed with Option A (subagent evaluator skill).**
Research budget: target 5 days in original plan; collapsed to 1 session after empirical spike confirmed the core assumption.

Source of the research question:
- [Harness_Engineering_Quality_Audit_2026-04-20.md](Harness_Engineering_Quality_Audit_2026-04-20.md) §3 — "planner / generator / evaluator split is weak; same agent usually owns all three roles"
- [Future_Optimization_Plan_Confirmed_2026-04-20.md](Future_Optimization_Plan_Confirmed_2026-04-20.md) R-1

## The Question We Had To Answer

> Can OAW get **genuinely independent evaluation** of a completed change,
> cheaply enough to run per PR, without requiring infra we don't have?

The risk, stated plainly: a "harness-evaluator" skill that runs in the **same
Claude session** as the work it's evaluating is **theater, not evaluation**.
Same agent, same context → same biases → rubber-stamp reviews that feel
rigorous but aren't.

## Three Candidate Options

### Option A — Claude Code Agent subagent

The parent session invokes the `Agent` tool with a narrow evaluation prompt.
The subagent gets **its own context window**: system prompt, parent's invocation
prompt, tools. Nothing else.

### Option B — Fresh `claude` CLI session

User manually starts a separate `claude` CLI in another terminal, loads the
diff, asks for review. Completely separate process.

### Option C — Static check script (no LLM)

Plain Python script. Checks structural properties (skill frontmatter valid?
CHANGELOG updated? CI green?). Deterministic, deterministically limited.

## The Empirical Spike (2026-04-20)

Spawned one `general-purpose` subagent with a probe prompt asking it to:
1. Self-describe what context it has
2. Read one file (`scripts/harness_check.py`) and critique it
3. Distinguish "inferred from what I read" vs "known from prior context"

**Result:**

> **1. Self-description (memory):** I have no prior conversation history with
> you. My context window contains only: the system prompt defining me as a
> Claude Code subagent, the environment note (cwd is the
> `future-plan-confirmed` worktree under OAW), your current message, and the
> file I just read (`harness_check.py`). I have seen no other files in this
> repo, have no memory of your parent session, and the only repo-specific
> knowledge I have is what `harness_check.py` reveals.

> **2. File read critique:** The eight checks are run strictly sequentially
> with `install.sh` re-executed three times into fresh tempdirs — factoring
> out a shared "install into tempdir" fixture (and running independent checks
> concurrently) would cut runtime meaningfully without changing semantics.

> **3. Reasoning check:** *Inferred from the file I just read:* OAW ships a
> reusable AI-context harness — an `install.sh` that drops CLAUDE.md /
> AI_CONTEXT.md / AGENTS.md / GEMINI.md / `.cursorrules` / `.windsurfrules` /
> `.agents/memory.md` / `docs/knowledge/index.md` and two CLI tools into a
> target project. *Known from prior session context:* nothing — I have no
> parent-session inheritance.

### Two signals this result proved

1. **Independence is real, not theoretical**: The subagent explicitly confirmed
   zero parent-context bleed. If I had pushed a biased framing ("OAW is great,
   just validate it"), the subagent wouldn't have inherited that; it had to
   derive understanding from one file and its own reasoning.
2. **Independence produces findings, not just signatures**: The critique about
   running `install.sh` three times and parallelizing independent checks was a
   **concrete issue I had not raised and had not seen** when I wrote the file.
   This is the exact behavior a good PR review produces — second-pair-of-eyes
   catches what the author was too close to see.

### Spike cost

- Tokens: ~19k
- Wall time: ~13 seconds
- Tool calls inside subagent: 1 (one Read)

Per-review cost is dominated by context-loading, not LLM reasoning. Cheap enough to run on every non-trivial PR.

## Decision

**Option A. Proceed with a subagent-based evaluator skill.**

Options B and C are **complements, not replacements**:
- **C (static checks)** already ships as [`scripts/harness_check.py`](../../scripts/harness_check.py) — it catches structural breakage without LLM cost. Every PR runs it via CI. Cheap safety net.
- **A (subagent evaluator)** handles semantic review — did the change actually solve the problem it claims to solve? Did it break an implicit invariant?
- **B (manual fresh `claude`)** stays in the toolbox for **high-stakes releases** where ambient confidence is insufficient — e.g., breaking changes, installer rewrites, anything touching `install.sh`.

The three layers answer different questions. Use all three, proportional to risk.

## Implementation Spec (for Week 4)

### New file: `templates/.agents/skills/harness-evaluator.md`

Frontmatter (must pass A-3 skill lint, so `triggers` + `outputs` present):

```yaml
---
name: harness-evaluator
description: "Independent subagent review of a completed change against explicit acceptance criteria"
triggers: ["review this change", "evaluate PR", "is this ready to merge", "second pair of eyes"]
requires:
  - .agents/memory.md (to find the change being evaluated)
optional_reads:
  - docs/archive/*.md (if the change references a plan doc)
outputs:
  - .agents/memory.md entry with [REVIEW] tag and per-criterion verdict
---
```

Body structure (must pass A-3 skill lint — needs Steps / Rules):

```markdown
## Steps

### Step 1: Identify the change and its acceptance criteria
Read last 5 entries of .agents/memory.md. Find the [DECISION] / [EXPERIMENT]
this review targets. If the source skill had `outputs:` listed, those become
the acceptance criteria.

### Step 2: Spawn subagent with structured review prompt
Use the Agent tool with subagent_type="general-purpose". Prompt template:
  - "Evaluate this change: <file list + diff excerpt>"
  - "Against these criteria: <from source skill outputs or explicit
     Verify/Acceptance section>"
  - "Return: per-criterion pass/fail + concrete evidence (file:line). Max 200 words."

### Step 3: Write subagent verdict to memory
Append to .agents/memory.md:
  [REVIEW] <change name> — <pass_count>/<total_count> criteria passed
  Subagent verdict: <one-line summary>
  Failed criteria: <list, or "none">

### Step 4: Flag next action
If any critical criterion failed → raise in conversation, do not silently land.
```

### How the parent agent uses it

User says "review this change" → parent agent matches the trigger → reads skill → invokes Agent tool with the prompt template → writes result to memory.

### Testing strategy

- First real test target: the LLM-wiki merge PR (Week 1 deliverable). Run evaluator against it before merging. Document subagent's verdict in the PR body.
- Success criterion: subagent flags at least one thing the author didn't notice. If subagent only rubber-stamps, revisit the prompt template.

## Answers To The Original Research Questions

From the confirmed plan R-1 §"需要回答的三個問題":

| Question | Answer |
|----------|--------|
| 在 Claude Code / Codex 現有能力內,最便宜的「真獨立 context」是什麼? | **Subagent spawn (Option A)**. Verified empirically: zero parent-context bleed. Cost ~19k tokens per invocation. |
| 若只能做到 "同 session + 結構化 prompt + 獨立 checklist",值得做嗎? | Moot — we don't need to settle for that. Option A gives real independence. |
| Evaluator output 寫到哪? | `.agents/memory.md` with `[REVIEW]` tag, per-criterion pass/fail. |

## Roll-up To Confirmed Plan Calendar

| Week | Original (confirmed plan) | After R-1 decision |
|:---:|---------------------------|--------------------|
| 3 | Evaluator design research (R-1) | **R-1 done (this doc)**; can start skill draft early |
| 4 | R-1 結論執行 | **Implement `harness-evaluator.md` skill; first run against LLM-wiki merge** |
| — | R-2 (lane audit) was contingent on R-1 | **R-2 still contingent — deferred pending evaluator's actual usage pattern** |

**R-2 (lane audit log) revisit note**: now that we've committed to Option A,
the audit log would be useful input for the subagent (so it knows what was
loaded). But start the evaluator *without* the audit log first; only add it
if the subagent reviews keep asking "what files did the parent agent actually
read?" If that question never comes up, skip R-2.

## Open Questions For Future (Not Blocking Week 4)

1. **Model choice**: should the evaluator subagent use the same model as the parent, or always pin to a specific model for review consistency? — revisit after 3 real reviews.
2. **Batch vs sequential review**: if a PR has 5 changes, is it 5 subagent invocations or 1 with a multi-part prompt? — probably 1 for token efficiency, but verify on a real PR.
3. **Publishing evaluator verdicts**: for public PRs, should the subagent's verdict go in the PR body automatically? Useful for visitors, but commits the review to public record. — decide when first public PR lands.

## Anti-Pattern To Avoid

> **Don't let the evaluator become a rubber stamp.** If the subagent approves
> every PR, either (a) the criteria are too loose, (b) the prompt template is
> priming for validation not review, or (c) the reviews are catching real
> issues but the author is cherry-picking when to run them. Audit monthly by
> sampling 5 random reviews and asking "would a human reviewer catch more?"

---

*Decided 2026-04-20. Supersedes the "R-1 research" placeholder in the confirmed plan.*
