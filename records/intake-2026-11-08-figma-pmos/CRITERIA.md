# Screen criteria (frozen 2026-11-08, before either screen is written)

Two blind screens: Claude (SCREEN_claude.md, pushed first) and Codex gpt-6.1-sol (SCREEN_codex.md, written without
seeing Claude's). Where they disagree, Codex's pick stands (owner 2026-11-08: Codex is the independent unit).

For every idea in SOURCE.md:
1. Gap: which OAW gap it fills, citing an OAW file (or "none: OAW already has X at <file>").
2. Native check: would Opus 5.5 or Codex gpt-6.1-sol without OAW already do it? Unknown means it must be measured.
3. Cost: tokens or seconds it adds per session or per use; who pays (Claude or ChatGPT plan).
4. Tier (D21): A mechanism only; B text the model reads; C runs food code, new runtime dependency, network,
   hooks on every session, or needs an owner decision.
5. Scale: does its value grow with repository size, session length or team size?
6. Test: one measurable test with a pass rule written now, cheapest first (mechanical before paid).
Pick at most 3 units to build (D21). Every idea not picked gets one line: why, and what would change that.
