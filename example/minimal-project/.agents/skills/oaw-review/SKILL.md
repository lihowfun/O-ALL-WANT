---
name: oaw-review
description: Decide how much review a change needs and run it. Use before starting a code change (with the paths you plan to touch) and again after finishing it, and when the user asks to turn the EGM review on, off or auto.
---

# OAW review

Run from the project root with Python 3.10+ (`py -3` on Windows if needed).

1. Before editing: `python3 scripts/oaw_mode.py suggest --paths <files you plan to change> --json`.
   After editing: `python3 scripts/oaw_mode.py suggest --json` (add `--range BASE..HEAD` for committed work).
   If `dry_run` is true, run no review and record nothing, but still follow the order: plan first when a step
   says so, and stop before changing code where a design review would come.
2. Do the `steps` in order. Finish every step marked `"before_code": true` before you change any code.
   Skip a step whose `done` is true.
   - `plan`: plan first, save the plan as `docs/plans/<name>.md`, then run
     `suggest --paths <files you plan to change> --plan docs/plans/<name>.md --json` for its design-review step.
   - `design-review`, `how: egm`: pick the context files the plan names, then run
     `python3 scripts/oaw_mode.py egm estimate <plan> <context files> --json`. State the estimate in one line;
     if `ask_first` is true, ask the user before running. Read the installed `egm-review` skill file (`.claude/skills/egm-review/SKILL.md` or
     `.agents/skills/egm-review/SKILL.md`) and follow the upstream entry it names with `Step: uninterrupted`,
     `TargetFile:` the plan and `GoldfishContext:` only the files the plan names. Review one plan at a time and
     write its reports to its own `report_dir` in `reviews`.
     Resolve each finding yourself: fix the plan, or reject it with a reason. Show the user only blockers you reject.
     Then run `python3 scripts/oaw_mode.py reviewed <plan> --how egm --report <its report_dir>`.
     If a usage limit or an error stops EGM early, record it with `--status cut`, tell the user, and write no code.
   - `design-review`, `how: fresh-context`: one reviewer with no conversation context reads the plan and the
     files it names; resolve the findings; record it with `--how fresh-context`.
   - `recheck`: after the change, run `python3 scripts/oaw_mode.py suggest --json` on the diff and follow it.
   - `code-review`: after the change, follow the instruction for this host and its selected reviewer family.
     For a same-family Codex review, start a native fresh-context subagent; for an explicitly selected
     cross-family review, use the command the step gives. Wait for the review and resolve its findings.
     Standard and deep each use one code-review round; run affected tests after fixes. Further independent
     review is explicit.
3. Light needs no review.
4. Switches, when the user asks:
   - EGM: `python3 scripts/oaw_mode.py egm on|auto|off` (no argument shows it). One EGM run without changing
     the switch: the user types `/egm-review`.
   - Code review by the other model family sends the diff there, so it needs the user's consent:
     `python3 scripts/oaw_mode.py second-opinion same|codex|claude`.
