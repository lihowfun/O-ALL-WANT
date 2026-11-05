---
name: oaw-catalog-intake-rules
description: "How new skills/harnesses may enter OAW's digestion pipeline (scout cadence, relevance filter, user confirmation, manual entry)"
metadata:
  type: project
---

OAW skill-catalog intake has two entry paths (user decision, 2026-11-03):

1. Active scouting: run weekly. Scout only detects and accumulates candidates; a relevance filter drops anything unrelated to coding-agent skills/harnesses (e.g. video tools) without reviewing it. High stars do not mean review. Each week the user is asked which candidates to try; nothing enters quarantine/digestion without that confirmation.
2. Manual entry: the user names a repo (e.g. Graphify, any GitHub repo) and it enters quarantine/digestion directly. The user may submit many foods in one batch: deduplicate (the same repo named twice is reviewed once), run each food independently, and return one batch summary; paid tests are still listed per food with an estimate and need the user's tick.
Verdicts are per component, not per food: "diarrhea" is rarely total. Split each food into parts and mark each absorb (into which OAW part), excrete (reason + evidence) or hold (which paid test is missing); excrete only the part that harms, and cite absorbed parts per version.
The digestion system decides each food's test plan itself (Elephant drafts, goldfish review, cheapest discriminating test); do not ask the user per food whether to test. The user sets a standing policy once (per-food paid budget cap, sandbox conditions); within it, run free and paid tests and report; ask only beyond the policy. The user still approves which components get absorbed.
Every absorb/remove creates a SemVer-named project build (default release 2.0.0; compositions 2.0.0+build.N + short hash + human label) with a one-click restore (preview, restore, doctor; OAW layer only). Each build lists its skills/components and its effect vs the default with an evidence level (measured / static-measured / not measured); never say "enhanced" without measurement.
Standing policy set 2026-11-03 (D13): 10M logical tokens per food for Stage 0/1, 10M digestion overhead per round; anything that executes food code needs a disposable container/VM (none on this machine yet, so it stays hold); no API keys by default; Codex halves "untested" until the user logs into a Codex CLI.
3. Removal: the user may drop any absorbed skill, including the bundled EGM, per project. Show a preview, back up, then remove; record why. Re-adding means testing again.

**Why:** the user does not want effort or quota spent on irrelevant or merely popular repos, and wants control over what gets digested.

**How to apply:** this supersedes the earlier catalog plan text that auto-queued scout finds and auto-ran static digest. Every food still needs tests before any verdict (toxic / nutritious / no gain). See also [[oaw-v2-definition]].

**Superseded in part (later decisions win):** D21 (2026-11-04): paid tests inside the D13 caps run without per-food owner ticks; the owner acts only at entry and release. D25 (2026-11-04): food code may run in a local tasting area (detached worktree, its own environment); no container or VM is required.
