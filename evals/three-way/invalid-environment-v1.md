# Invalid environment cohort — 2026-10-30

The first CLI task cohort (`cohort-v4`, protocol v1) is excluded from every
quality, efficiency and memory-effect comparison. Its JSONL processes completed,
but ordinary filesystem reads were rejected by CLI execution policy. Reports
explicitly said they were blocked and performed no review. Both independent
blinded graders confirmed all 12 final reviews contained no planted detection
because they were incomplete. Empty findings are not a clean review or parity.

The initial runner incorrectly accepted process exit + valid JSON as completed
work. A no-tool usage probe was insufficient operational preflight. The controller
noticed the setup failure through independent grading, stopped the runner and
its specifically identified subprocesses, and retained all raw files, costs,
the budget amendment and both grades. Some memory calls had already started;
they are excluded too. No outputs were selectively salvaged.

A separate real IO probe with the documented `--approve-for-me` mode successfully
read an unknown canary, wrote it to disk and verified its actual content. It uses
normal sandbox/automatic approval review; no sandbox bypass or ignored rules.

The v2 registration starts all arms and cases from fresh installs. Same product
sources, tasks, gold, repeats, model and effort. It records the changed approval
configuration and prospective budget. Every call now requires a nonce read from
disk, a matching persisted copy, the returned nonce and a successful command
event. Failure stops new dispatch. This checks actual IO, not task correctness;
independent grading and source-integrity checks remain necessary.

The invalid cohort's usage is setup overhead, never a successful workflow's
cost or evidence of a harness regression. Retain original Git commits to
reproduce its old runner; the corrected runner must not resume invalid data.
