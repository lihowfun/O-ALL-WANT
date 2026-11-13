# FIXCHECK execution status

2026-11-13. This file is a progress snapshot, not a verdict.

- Preregistration and independent review pushed in records commit `4033f52`.
- Manifest SHA-256: `d1bec84b95004f7d27f9adf6a1acc07ae53be41f45fcbb50943c334f1ea5b80e`.
- Candidate remains `c2d9852bf8cabf13fd86a4340ab89f69044cae5a`.
- Live-process D39 check found no other experiment runners; stale PID files were ignored.
- Codex O / class A started through the guarded adapter. At this snapshot: **1 counted task of 24 total**, second task running; 196,707 logical Codex tokens in counted rows. This is partial usage, not final all-attempt spend.
- Claude has not started. Its independent D45 budget is still 17M; no H1 allowance is reused.
- Continue the same state and resume completed attempts. Do not rebuild, alter the manifest, re-draw counted answers or start PPT concurrently.
- Mechanism audit is pending. No new H1 effectiveness verdict, no regression-pass claim, no release decision.

CI PR routing still awaits owner choice. The authorized FIXCHECK uses its already-pushed preregistration and D45 budget independently of that PR choice. Final release still requires both the regression disposition and actual six-job CI.

Release polish is separate: `codex/v2.0.1-release-polish@5af21f6`, Linux gate 9/9, 685 tests. It has not been folded into the fixed study candidate. Integrate it after FIXCHECK's keep/revert disposition, then validate the final release commit.
