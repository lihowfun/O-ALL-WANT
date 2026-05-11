---
name: skill-review
description: "After a non-trivial task, decide whether a skill should be added, updated, or patched — never invent skills for one-off tickets."
triggers: ["end of a multi-step task", "after solving something that felt repeatable", "/skill-review"]
params:
  task_summary: "1-3 line description of what was just done"
requires:
  - .agents/skills/
outputs:
  - 0 or 1 new/updated skill file
  - context_hub.py skills use/patch invocation
---

# Skill Review

> Inspired by Hermes Agent's autonomous skill creation
> (tools/skill_manager_tool.py + agent/curator.py). OAW's version is
> agent-invoked rather than backgrounded — you decide whether to run this
> at the end of a task. Honest non-action is fine.

## When to invoke

- A non-trivial task just finished (≥3 distinct steps, or new tooling, or new workflow discovered).
- Self-improving Rule 5 fires (see `.agents/skills/self-improving.md`).
- User explicitly types `/skill-review`.

## Hard rules

1. **Class-level, not ticket-level.** A skill captures a pattern that will
   be useful again. `python-debugging` ✓ — `fix-PR-123` ✗.
2. **Update existing before adding new.** If an existing skill is close,
   patch it. Adding a near-duplicate skill is the most common mistake.
3. **No environment-failure logs.** "AWS CLI wasn't installed today" is
   not a skill. Real skills survive a fresh checkout.
4. **No negative tool claims.** "Don't use sed for X" by itself is not a
   skill — turn it into a positive workflow ("for X, use Y because Z").

## Decision tree (run in order — stop at first match)

1. **Already loaded a skill this task?** → if you patched its behavior or
   refined a step, run `skills patch` and rewrite the affected section.
2. **An existing skill is the umbrella but missing a sub-step?**
   → add a section (or supporting file under a sub-dir) to it; `skills patch`.
3. **A new pattern of work emerged that doesn't fit any current skill?**
   → only then create a new `.agents/skills/<name>.md` using `_TEMPLATE.md`.
4. **None of the above?** → exit without action. Honest non-action beats
   noise. Optionally drop a `[INSIGHT]` line in `memory.md` instead.

## What goes in a new/updated skill

```
---
name: <slug>
description: "<one line — what the skill does, when to fire it>"
triggers: ["<phrase that should auto-fire>", "/<name>"]
params:
  <key>: "<what the caller should provide>"
requires: [<file or skill dependencies>]
outputs: [<observable side-effects>]
---

# <Title>

## When to invoke
<2-4 bullets, concrete situations>

## Hard rules
<the 1-4 invariants the workflow must keep>

## Step-by-step
<numbered list — each step actionable in one shell command or one prompt>

## Verification
<how to know it succeeded — link to the test or quantified metric>
```

## After making changes

```bash
# Increment usage / patch counters so `skills audit` reflects reality.
python3 scripts/context_hub.py skills patch <name>     # if updated
python3 scripts/context_hub.py skills use <name>       # if you applied an existing one

# Memory note (optional but recommended for non-obvious decisions):
python3 scripts/context_hub.py memory add "[DECISION] Patched <skill> — reason: <one line>"
```

## Counter-examples (do NOT do this)

- ❌ `fix-cors-bug-on-acme-staging` — ticket-specific
- ❌ `dont-use-sed` — negative, no replacement workflow
- ❌ `pytest-failed-today` — environment artefact
- ❌ Copy of an existing skill with one renamed step

## Output

End the review with one of:

- `PATCH <skill-name>: <one-line reason>` — and the patch
- `ADD <new-skill-name>: <one-line reason>` — and the new file
- `NOACTION: <one-line reason>` — and exit
