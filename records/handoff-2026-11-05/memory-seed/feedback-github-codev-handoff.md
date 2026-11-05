---
name: feedback-github-codev-handoff
description: "OAW work is co-development through GitHub; the owner does auth-gated steps on a logged-in machine and pushes, I fetch and continue; GitHub is the record of truth"
metadata:
  type: feedback
---

OAW work stays on the main work computer, but treat it as co-development managed through GitHub (`lihowfun/O-ALL-WANT`). Steps that need the owner's authorization (CLI login, OAuth, tokens, accounts) are done by the owner on whichever machine they are logged in to; they push the results to GitHub, and I fetch the branch and continue from there. All records are GitHub-first: push decisions, handoff notes and results to a branch rather than leaving them only in local scratch files.

**Why:** the owner is often remote and cannot type into this machine's terminal, and I may not enter credentials for them (2026-11-03).

**How to apply:** write any auth-gated step as a self-contained kit on a branch (commands, expected output, where to push results); make its output safe for the public repo (redact local paths, account names, emails); when the owner says it is done, `git fetch` and read the pushed results before acting. Related: [[oaw-catalog-intake-rules]], [[feedback-egm-full-combo]].
