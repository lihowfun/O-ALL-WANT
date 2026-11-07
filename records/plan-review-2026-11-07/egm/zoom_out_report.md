# Stage 5: Initial Zoom Out Report

**Target:** `docs/plans/v2.0.1-execution.md` (full file, lines 1-325)
**Standard:** `zoom-out-standard.md`

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed |

**Context sufficiency:** passes. The plan covers all three owner requests: a smoother harness with fewer rules, built-in EGM and a code map (G1-G5); an absorption SOP and a path to faster absorption (Appendix A, W5); and a user-facing `add A B C` with three options (W3).
**Verdict:** Revise. 1 Blocker, 6 Major, 6 Nits.

## Prioritized Findings

### ZO-1. W3 says it "wraps the existing catalog", but the catalog cannot install or restore hooks, MCP servers, agents or scripts. Severity: Blocker
* **Affected Scope:** Lines 89, 164, 174-175, 180-184, 192, 252
* **Discrepancy:** The plan describes `add/list/remove` as a wrapper around the existing catalog (line 89). It says install and rollback reuse catalog `builds`/`restore` (line 175) and puts W3 in segment 1 at "nearly 0 tokens, 2-3 days" (line 252). Steps 4-5 install hooks, MCP servers and background programs after a consent checkbox. The completion test requires that `remove` of a hook-carrying fixture leave managed files byte-identical (line 192). The catalog was built to exclude exactly these things:
  * `scripts/catalog.py:1374-1375` denies `.codex/`, `.mcp.json` and `.claude.json`.
  * `scripts/catalog.py:1391-1404` requires absorbed files to sit inside a skill folder and rejects anything under `hooks`, `.claude` or `.agents`.
  * `scripts/catalog_core.py:78` allows only `.md` and `.txt` files.
  * The docstring at `scripts/catalog.py:1407-1413` says host settings and MCP files are never part of a build.
  * `evidence/egm-selftest-2026-11-06-RESULT.md:58-63` records that `catalog.py remove egm` did not remove cleanly.
* **Rationale & Recommendation:** Options ① and ② need a new installer that writes host settings, MCP config and executable files. That installer would cross a security boundary the code enforces on purpose. Either limit 2.0.1 installs to skill text and agent definitions, and list hooks and MCP servers as "not installed by OAW" (the same rule D29.3 applies to external plugins, `evidence/DECISIONS-D21-D31.md:148-150`), or scope hook/MCP install as its own designed workstream with its own restore mechanism and its own estimate.

### ZO-2. `oaw-review` copies EGM's orchestration instead of referencing it. Severity: Major
* **Affected Scope:** Lines 86, 108, 114-116, 275
* **Discrepancy:** In deep mode the skill "follows the upstream `egm-review` flow" (line 115). The upstream skill is explicit-only (`templates/.agents/skills/egm-review/SKILL.md:5`, `disable-model-invocation: true`), and `scripts/sync_egm.py:68-70` copies that flag from upstream. The per-project off switch (line 275) has no named location.
* **Rationale & Recommendation:** If the skill carries its own copy of the flow, every EGM pin update has to be mirrored by hand. D21 named this kind of copy drift as the main source of waste (`DECISIONS-D21-D31.md:2-5`). Say that `oaw-review` only points to the installed `egm-review/SKILL.md`, or that the change is made as an install-time override of the flag. Name where the off switch lives.

### ZO-3. The new zero-context reviewer ignores the existing `goldfish_review.py`. Severity: Major
* **Affected Scope:** Lines 87, 107, 112, 118
* **Discrepancy:** `scripts/goldfish_review.py:1-15, 34-35` already runs a `claude -p` diff review with tools, MCP and settings turned off, plus canary, billing and leak checks (D23). `scripts/oaw_mode.py:314-317` already holds the reviewer instructions for both hosts.
* **Rationale & Recommendation:** Name `goldfish_review.py` as the basis for the `claude -p` path. Then either justify the new `oaw-goldfish` agent by saying what it does that the script does not, or drop it.

### ZO-4. `overview` and the TS/JS parser upgrade are added before any evidence supports them. Severity: Major
* **Affected Scope:** Lines 132, 137, 139, 141-142
* **Discrepancy:** The evidence supports only `callers`/`affected` (`codemap-comparison-2026-11-06.md:56-57`). No map improved accuracy (`:6`). graphify, the source of the "architecture overview" idea, won on neither axis and was rejected (`:6, 80-82`). `code_index.py` already handles `.ts/.tsx` (`code_index.py:6, 48-49`). X1 does not test `overview` separately, yet the skill text adds "look at the overview first in an unfamiliar repo".
* **Rationale & Recommendation:** Run Stage 0 (b) on VS Code with the current parser first, and upgrade TS parsing only if recall falls below 0.95. Defer `overview`, or ship it as a CLI command with no skill text until it is measured.

### ZO-5. Two motivating claims in §1 do not match the evidence. Severity: Major
* **Affected Scope:** Lines 34, 37
* **Discrepancy:**
  * Line 37 says all three maps cut tool calls to 0.23-0.65× native. That is false:
    * OAW on Opus 4.8 is at 104% (`codemap-comparison-2026-11-06.md:36`).
    * graphify is at 76-104% (`:28, 32, 36, 40`).
    * The 0.23 figure is codegraph's, from V8.
  * Line 34 claims "0 unfounded claims". The V4 table lists unfounded claims for EGM detection as Opus 1 / Codex 7 (`validation-2026-11-07-RESULT.md:71`).
* **Rationale & Recommendation:** The overstatement on line 37 is the basis for treating maps as "efficiency tools". Report each map separately, and state which grader and which arm the "0 unfounded" claim refers to.

### ZO-6. The absorption list rebuilds data that `catalog effect` and `oaw.py skills` already produce. Severity: Major
* **Affected Scope:** Lines 89, 158, 173, 180-189, 306
* **Discrepancy:** `catalog_core.effect_vs_default` already reports startup bytes, hooks, non-stdlib dependencies and settings writes (`catalog_core.py:1485-1513`; CLI at `catalog.py:2585`). `oaw.py skills` already lists installed skills (`oaw.py:826-845`), and `catalog.py list` is a third listing (`catalog.py:2523`). `catalog/verdicts.json` would be a second copy of the ledger.
* **Rationale & Recommendation:** Build `oaw.py list` from `effect` plus the ledger, replacing `oaw.py skills`. Generate `verdicts.json` from the ledger and check it in `harness_check`.

### ZO-7. The plan assumes the agent can put itself into plan mode, but nothing tests this. Severity: Major (conditional)
* **Affected Scope:** Lines 43, 55, 108, 121
* **Discrepancy:** The spike only asks about raising effort. `oaw_mode.py:343, 357` says plan mode is started from the command line and that "the agent cannot start it".
* **Rationale & Recommendation:** Add plan-mode self-entry on Claude and on Codex to the spike, with a fallback. If self-entry fails, G1 ("no owner action") does not hold.

### Nits
* **ZO-N1:** `oaw_mode.py plan` (lines 88, 113) overlaps `show --json` (`oaw_mode.py:337-372, 404-408`).
* **ZO-N2:** The "contradictory policy text" check (line 173) cannot be done statically. That conflicts with "agent spends no tokens" (line 163).
* **ZO-N3:** The eval tooling is split between W0 (lines 94-100) and W5 (lines 202-213). Merge it into one workstream.
* **ZO-N4:** Mirroring the list in `catalog.py ui` and the digestion panel (line 188) is extra scope.
* **ZO-N5 (conditional):** The release could ship with conservative defaults and leave the ~18M of X1/X2 for a follow-up, if the owner does not need defaults decided before release.
* **ZO-N6:** Line 45 says `SKILL_INTAKE.md` has "400 lines". The reviewer counted 321 non-empty lines. Say which count is meant.
