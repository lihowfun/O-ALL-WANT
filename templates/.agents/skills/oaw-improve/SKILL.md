---
name: oaw-improve
description: Evaluate a requested improvement to project agent guidance or skills using a candidate diff and matched baseline-versus-candidate evidence.
---

# Evidence-driven improvements

Start with the recurring failure or measurable cost the user wants to address.
Check the native host's current capabilities and try deleting redundant guidance
before adding another rule or workflow.

Propose a reviewable candidate diff and a falsifiable improvement hypothesis.
Use `python scripts/improvement.py --help` for proposal, comparison, and decision
commands. Keep the proposal separate from active policy.

Compare baseline and candidate on matched tasks with the same model, effort,
host version, environment, repository state, and permissions. Retain outputs and
checks supporting quality, token, and time results; a single successful execution
does not establish an improvement. Identify missing or inconclusive evidence.

Ask for an explicit accept or reject decision on the candidate and its evidence.
A recorded acceptance does not apply the patch or authorize external actions.
Do not automatically rewrite skills, project policy, or native memory.
