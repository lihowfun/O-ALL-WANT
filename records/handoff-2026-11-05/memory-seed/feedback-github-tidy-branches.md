---
name: feedback-github-tidy-branches
description: "Keep the OAW GitHub repo to four branches: main, Codex's PR branch, one claude/oaw-2 V2 branch, one records branch"
metadata:
  type: feedback
---

Keep `lihowfun/O-ALL-WANT` tidy; the owner does not want a pile of disorganized branches (2026-11-04: "github 都弄好要保持整潔 我不希望看到一堆雜亂無章的branch"). Claude's side ships only one V2 branch, and when its PR concludes it is merged into main if it should be ("最終我們這邊只會出去一個V2相關branch ＰＲ節數後 該merge main就merge"). Layout since 2026-11-04: `main`, `codex/oaw-2-native-upgrade` (PR #4, Codex), `claude/oaw-2` (all Claude V2 work), `records` (all records, review kits, auth-gated kits and their results).

**Why:** GitHub is the record of truth for co-development ([[feedback-github-codev-handoff]]), so the owner reads the branch list directly; per-feature, per-round and per-kit branches made it noisy.

**How to apply:** add V2 code to `claude/oaw-2`, never a new feature branch; put each digestion round, review kit and auth-gated kit in a folder on `records`; delete a branch once its PR is merged; before creating any branch, ask whether an existing one should hold the work. Deleting or renaming GitHub branches still needs the owner's OK (auto mode blocked it until the owner said "可以刪").
