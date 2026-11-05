# OAW project decisions for skill digestion (owner decisions, with provenance)

Purpose: give any fresh agent the full project context to act as the EGM "Elephant",
without relying on a chat transcript. Each entry: decision, date, source, scope.
Status: draft evidence record; to be moved into the OAW repo's decision records.

## D1. V2 definition (2026-10-30, owner in chat; scope: all OAW docs and code)
V2 = the OAW v1 upgrade (old flat skills retired) + bundled EGM
(google/elephant-goldfish-model, pinned f0ba151, Apache-2.0). Never write "V2+EGM"
or "OAW+EGM" in new material; historical/frozen records keep their wording.
Implemented by Codex in 341b450 (EGM under .oaw/integrations/egm, bridge skills,
selectable EGM skills). Bundling EGM is a product decision, not a measured gain:
the 2026-10-29 Codex study found no detection gain over native and one extra
unsupported claim for standalone EGM.

## D2. Parity floor and evolution claims (2026-10-29, owner; scope: every food)
After eating a food, OAW must be at least as good as using that food alone
(parity floor; iterative updates may ship at parity). Only a measured win over the
food may be called "evolution". Without matched evidence, write "parity, no
improvement claimed" or "not yet proven".

## D3. Citations per version (2026-10-29, owner; scope: releases)
Each version cites only upstream material it actually uses, with where it is used;
anything removed or not adopted is listed with the reason.

## D4. Intake: two entry paths (2026-11-03, owner; scope: catalog)
1. Weekly active scouting: only detect and accumulate; a relevance filter drops
   anything unrelated to coding-agent skills/harnesses (e.g. video tools) without
   review; stars only order the list. Each week the owner picks which candidates to
   try; nothing enters quarantine or digestion without that confirmation.
2. Manual entry: the owner names repos (e.g. graphify) and they enter directly.
   Batches are allowed; duplicates are merged (the same repo named twice is reviewed once).

## D5. Every food is tested; verdicts are per component (2026-11-03, owner)
Some foods are toxic, some nutritious, but every food is tested before any verdict.
"Diarrhea" is rarely total: split each food into components and mark each absorb
(re-implemented into a named OAW part), excrete (reason + evidence) or hold (which
paid test is missing). Excrete only the harmful part.

## D6. Owner control over existing skills (2026-11-03, owner)
The owner may remove any absorbed skill per project, including the bundled EGM:
preview, back up, then remove; record why. Re-adding requires testing again.

## D7. Consent and cost (2026-10-29/30, owner)
No automatic install or apply. Paid model tests (behavior A/B, integration runs)
need the owner's explicit consent and a budget, shown with an estimate first.
Untrusted repos are quarantined at a pinned SHA and never executed during digestion.

## D8. Cross-host counterpart (2026-10-29, owner)
OAW is shared by Claude Code and Codex. Any single-host feature (e.g. a Claude mod)
needs a counterpart usable from Codex (terminal CLI / skill). Same data, same
display rules.

## D9. Usable, simple, game-like (2026-11-03, owner)
The digestion experience must be simple to understand and actually usable (e.g.
press to actively digest), "like a video game", and the owner will test it personally.

## D10. Use the full EGM combination (2026-11-03, owner)
Digestion uses Elephant (full project context, from these records) drafting the
absorption proposals, Goldfish (zero context) blind-reviewing those drafts, the
Elephant resolving findings, and the owner deciding. A goldfish review of the food
alone is not a substitute for goldfish review of our own drafts.

## D11. The digestion system decides how to eat each food (2026-11-03, owner)
The system, not the owner, decides each food's test plan: the Elephant drafts the
plan from evidence, goldfish blind-review it, and the system picks the cheapest
test that can still tell nutritious from no-gain or toxic. The owner sets a
standing policy once (per-food paid budget cap; sandbox conditions for trial runs,
e.g. isolated venv, copy of the project, no API keys). Within that policy the
system runs free and paid tests without asking per food and reports results;
it asks only when a test would exceed the policy. The owner still approves which
components are absorbed. This refines D7: consent is given once as a policy,
not per test.

## D12. Versioned absorption with one-click restore (2026-11-03, owner)
Every absorption or removal produces a named project build with a restore point,
and the owner can restore any earlier build in one step (preview, restore, then
doctor). Names must be professional: SemVer 2.0, release `2.0.0` as the default,
project compositions as build metadata `2.0.0+build.N` (plus a short content hash),
each with a human label of what was added or removed. Restoring switches only the
OAW-installed layer, never project records. Each build shows which skills and
components it has and its effect versus the default release, with an evidence
level per line (measured / static-measured / not measured); the digestion system
performs this simple evaluation at absorption time. Without measured evidence the
view says "not measured", never "enhanced".

## Evidence index (for this digestion round)
- Pinned foods and static digests: ingest/<food>/scout.json, digest.json, verify.json
- graphify vs LLM wiki duel: ingest/graphify/wiki-duel.json (judge: complement)
- Goldfish-on-food, component ledgers, integration checks, first proposals:
  ingest/<food>/goldfish-*.json, components.json, integration.json, proposals.md
  (components.json ledger_revision 2 carries the integration-resolved after_integration
  records; goldfish-*.json are marked "context unverified")
- Cross-food absorption backlog (revision 2: items, dependencies, test order, owner
  decisions, budget estimates): ingest/backlog.json
- Round summary for owner approval, with the 修訂紀錄 of revision 2: ingest/SUMMARY.md
- OAW V2 reference: oaw-ref/ (origin/codex/oaw-2-native-upgrade)

## D13. Standing policy PRE-01 (2026-11-03, owner in chat: "全部都照你的建議推進", approving Claude's recommendations; scope: all digestion runs)
- Per-food screening cap: 10M logical tokens per food for Stage 0/1. Stage 2, a
  second host, or anything over the cap asks the owner first. Reason: on 2026-11-03
  about 7M subagent logical tokens across three workflows reached the owner's
  usage limit, so the drafted 120M/250M/300M caps would span many limit windows.
- Digestion-system overhead cap (goldfish reviews, probes, fixtures): 10M per round.
- Sandbox level 1: a copy of the project on this machine with the host config
  directory redirected; only for runs that do not execute food code.
- Sandbox level 2: a disposable Linux container or VM, destroyed after each trial;
  required for any run that executes food code, installs anything, or could read OS
  credential stores (HOME redirection does not isolate USERPROFILE or Credential
  Manager on Windows). Not available on this machine yet: such runs stay hold.
- API keys: trials get none by default; a dedicated, capped, revoked-after key only
  if the owner creates one. Goldfish runs use a disposable config directory.
- Network: model provider API only; level 2 may open PyPI/GitHub briefly to fetch
  dependencies.
- Codex CLI (PRE-03): install on this machine (D8), pending the owner's own login;
  until then every Codex half is recorded "untested".
- Shared A/B cost: a shared baseline is split evenly across the foods that use it;
  candidate arms are charged to the food they test.

## D14. Owner choices for the 2026-11-03 round (same source)
- Target release: all batches go into the untagged 2.0.0; if 2.0.0 is tagged
  first, additive items go to 2.x and incompatible ones (OAW-19, OAW-12/13, OAW-25)
  wait for 3.0.0.
- Removal granularity: removal builds only, no per-item switches; restore is linear.
- CLI contract (OAW-19): exit 3 = a choice is needed, 4 = no match; `memory recall`
  with no hit stays 0; `get` gives a unique case-insensitive match on every OS with a
  stderr note; an empty knowledge base always exits 0.
- License route (OAW-07/12/30): Apache-2.0 attribution with modification notices,
  LICENSE/NOTICE shipped, as for EGM.
- The excrete list in ingest/OWNER_SHEET.md section 3 is accepted whole.
- Batches 1-9 are NOT approved yet: approval follows the zero-context PRE-02
  review of revision 3 (D10, D15).
- Paper arXiv 2606.03979: the T0 field check may read only O-ALL-WANT's own
  .agents/memory.md.
- Digestion animation: superseded by D19 the same day.

## D19. Not a game: the official skill-intake process plus an operable animated view (2026-11-03, owner in chat: "這不是遊戲 而是之後要開始增加skills時候最佳流程定出來 消化系統動畫讓使用者容易懂也能幫忙操作"; refines D9)
The prototype is not a game. Its purpose is (1) to fix the best process OAW uses
whenever skills are added from now on (intake, relevance filter, quarantine, tests,
per-component verdicts, absorb, versioned build, restore, removal), written down as
the official process, and (2) a digestion-system animation that makes that process
easy to understand AND lets the user operate it: each food is shown moving through
the stages, and the actions for the current stage are on the animation itself.
"Like a video game" (D9) means simple to use, not a game. Do not name commands,
pages or docs "game" or "play".

## D15-D18. Process rules P1-P4 confirmed (same source; refine D10, D2, D5/D7, D12)
- D15 (P1, refines D10). Zero context is verified, not assumed: each goldfish is
  launched with a recipe whose argv and init event show no tools, skills, plugins,
  MCP servers or inherited settings, and each goldfish record states its launch
  method, host version, inherited context and init-event check. The backlog
  synthesis and every merge-derived item are Elephant drafts and get goldfish review.
- D16 (P2, refines D2). The parity floor is a designed gate for every tested food:
  the plan includes "OAW after eating" against "the food alone" (C >= B). Until it
  runs, the food is labelled "parity vs food alone: not tested". Scope: the whole food.
- D17 (P3, refines D5/D7). A step that executes the food is automatically a hold
  under D11. A model-facing line (skill, template or startup text) is always split
  from its mechanism and held behind an A/B; the mechanism may ship at static
  evidence. Every hold starts with a free Stage 0.
- D18 (P4, refines D12). An item that is not built carries evidence "not measured
  (planned: <level>)"; the planned level is kept in a separate field and never shown
  as the current level.

## D20. PRE-02 goldfish label (2026-11-04, owner in chat, choosing "標成零專案上下文")
The four PRE-02 goldfish runs (macOS, CLI 2.1.160, subscription) passed every init
check (no tools, MCP servers, slash commands, skills or auto-memory; built-in
plugins only; fresh temp folder) but the canary did not answer "none": `claude -p`
always carries the CLI's default system prompt and an account reminder (email,
date). The round is labelled "zero project context"; the result files keep
`zero_context_verified: false` unchanged. Findings that rest on the goldfish's own
claims about its tools are disregarded where the init event contradicts them.

## D21. Lean intake flow v1 (2026-11-04, owner in chat: "我覺得目前的流程要再討論 超級沒效率 人類審查的步驟也太多 先找出最佳流程 降低我審查的必要性", then "改用，這輪開始"; refines D4, D5, D10, D11, D16, D19; replaces the per-batch approval of D14 and PRE-08)
Diagnosis: the 2026-11-03 round needed about 20 owner touchpoints, three revisions
and three goldfish rounds, produced 2.9 MB of records and absorbed nothing; most of
the 25 PRE-02 findings were drift between five documents holding the same content,
or cited lines missing from review packets, not defects.
1. Entry (owner): a repo URL, or ticks on the weekly scout list.
2. Quick screen (automatic): at most 3 units per food, by expected value. Units
   not picked go back to the candidate pool with a one-line verdict; no further
   analysis and no paid plan is spent on them.
3. Build (automatic): each picked unit is built as code plus tests on the single
   Claude V2 branch `claude/oaw-2`; the gate must pass. Code and tests are the
   record; one ledger per food, summaries generated from it.
4. Blind review (automatic): one zero-context goldfish round (D15 recipe) on the
   code diff and tests, not on documents. The Elephant resolves the findings; only a
   blocker the Elephant rejects goes to the owner.
5. Tiers (automatic):
   - A: mechanism only, no model-facing text, does not execute food code,
     restorable -> absorbed (D17 allows static evidence).
   - B: model-facing text -> A/B inside the standing D13 budget; ships only at
     parity or better; queued when the budget is short.
   - C: executes food code, adds a runtime dependency, needs a license or CLI
     contract choice not covered by a standing decision, removes an existing skill,
     or exceeds the budget -> owner.
6. Release (owner): one page per version (what was added, comparison against the
   default, how to restore); the owner merges the PR.
- D14's standing choices (license route, CLI contract, release target, excrete
  list) count as policy; items they cover are not asked again.
- D16: the label "parity vs food alone: not tested" stays; a floor arm is no longer
  designed at screening.
- Findings on documents from the old flow are not resolved as document edits; real
  defects among them become tests during the build.
- Owner routine touchpoints: entry and release.

## D22. GitHub branch layout (2026-11-04, owner in chat: "github 都弄好要保持整潔 我不希望看到一堆雜亂無章的branch", "最終我們這邊只會出去一個V2相關branch ＰＲ節數後 該merge main就merge", "可以刪")
Four branches: `main`, `codex/oaw-2-native-upgrade` (PR #4), `claude/oaw-2` (all
Claude V2 work; merged into main when its PR concludes, then deleted) and `records`
(every round, review kit, auth-gated kit and result, as folders). No new branch per
feature, round or kit.

## D23. Digestion view and packaging (2026-11-04, owner in chat: "照這個方向改" on the digestive-tract mockup; "請多加審核機制或是提問機制"; "要把他做成 skill or mod")
- The local digestion page (`catalog.py ui`) and a desktop mod show foods as boluses on a digestive tract at
  their real stop, with the selected food's travelled path, a per-food progress bar and the absorbed / held /
  excreted split.
- Every food shows a blocker explanation (where it is stuck, which decision causes it, what happens if the
  owner does nothing). Decisions show options with consequences and a recommendation; optional decisions are
  marked optional and never block. The owner can ask about a blocker; on the local page the question is
  recorded and answered by Claude in the conversation.
- The D21 procedure is packaged as the owner-level skill `oaw-digest`; the goldfish kit becomes
  `scripts/goldfish_review.py`.

## D24. Code map and screening rules after the CLI review (2026-11-04, owner in chat: "全部照建議" on Q1-Q5 of REVIEW_2026-11-04.md; refines D13, D17, D21 and the v2 graph-memory exclusion)
1. A code index generated from source is not "graph memory" under docs/plans/v2.0.0-execution.md:78 when
   agents do not write to it, it can be rebuilt at any time, querying it is never mandatory, and it has a
   staleness check. A stdlib index may be a core candidate; any line telling agents to use it is still
   model-facing and needs an A/B (D17).
2. Quick screening follows D21 as written: pick by expected value, tier after picking; tier-C picks go to the
   owner as at most 3 questions per round. The "tier A only" filter of round 1 is withdrawn.
3. Level 2 sandbox: not required to start. Stage 0-alpha compares native search (R) with a stdlib index (S)
   without running graphify; a local Docker recipe for graphify (G) is prepared and needs one owner sudo setup.
4. No D13 exception: Stage 0-alpha (0 model tokens) and, only if it passes, a minimal Claude-only Stage 1 of
   12 runs (6 questions x 2 arms x 1, at most 10M).
5. Pre-registered "step change" threshold for the code map: on file-location questions the median number of
   tool calls drops by at least 30% and the number of correct answers is not lower than the native arm.
   Stage 0-alpha passes only if S (or G) beats R by at least 0.15 top-5 file hit rate in some question class
   without producing more output bytes than R. Thresholds are fixed before any result is seen.

## D25. Taste before judging (2026-11-04, owner in chat: "你從來就沒有graphify 執行過 那你怎麼判斷該不該吸收的….. 我們流程有問題"; "試吃就是在安全環境吃看看啊"; "為啥要斷網 就OAW 2 拉一個worktree or brance"; refines D17)
- No food is judged on reading alone. Every food is first run as it is in a tasting area: a local worktree of
  OAW 2 (detached, no new branch, never pushed), the food installed in its own environment (for example a
  separate WSL conda env), no API keys in its environment, and its installer, hooks or always-on rules run only
  when tasting them is the point. Network cut-off is not required.
- D17 changes from "food code is never executed without level 2" to "food code is executed only in the
  tasting area". Level 2 (Docker) stays optional.
- Tasting compares three arms on the same questions: native, the food as it is, and the OAW version. Zero-token
  checks run first; only a gap worth measuring goes to a paid agent run (D13 caps unchanged).
- Each food ends in one of three verdicts: absorb (rebuilt in the standard library), plug in (the original is
  better; the user installs it and OAW connects to it), or decline.
- First tasting: graphify 0.9.101 (records/digestion-2026-11-03/taste-graphify/).
- Proposed in the same review but not decided by the owner: no gate without a tool to pass it; calibrate cost
  estimates from measured runs; a unit with no real caller is not absorbed; batch process changes.

## D26. Fair tasting of popular foods (2026-11-04, owner in chat: "Graphify 幾千幾萬顆星啊 你認真跑出來 我們18顆星的比較好？我不是妄自菲薄 而是要建立最佳流程 ... 一定程度上算是可信 我們可以參照 順便建立好最佳skill吸收效率流程"; "3 個skills 用公正方式好好審"; "儘量減少我登入什麼有的沒的操作 你就直接現有環境跑"; refines D25)
- Stars, authorship and activity are a prior, not proof: a popular food is assumed useful, and tasting finds
  where. When OAW beats a popular food, suspect the test first: rerun on a repo that is not ours and check
  the food was configured as its authors recommend before concluding.
- Taste the food the way its authors intend: official install (project scope when it offers one), its
  recommended configuration (for example ignore files), its own workflow; test its own claim at the agent level,
  not a tool-output proxy.
- Questions are written by a fresh agent that knows the food's claim but not OAW's implementation, frozen in
  records before any run; same model, prompt and limits in every arm; answers graded blind.
- Verdicts: plug in (default for a popular food that works; OAW connects to it, as with vendored EGM), absorb
  the mechanism (stdlib rebuild of the part that carries the value), or decline.
- Runs use the existing WSL Claude Code login on the subscription; no extra owner login. User-level installs
  are backed up and restored; project-scope installs are preferred. D13 caps per food stay.
- Proposed by Claude, not objected to: the owner acts at entry (link) and release (merge) only; the steps
  become a reusable tasting kit (install recipe plus questions per food).

## D27. claude-mem is tasted in local subscription mode (2026-11-05, owner in chat: "本機訂閱模式"; applies D26)
- claude-mem's default install asks for an email sign-in to its hosted service (a trial in which memory
  compression runs on the vendor's servers). For tasting, it is installed with an explicit `--provider` that
  compresses on the owner's own Claude plan: no new account, observations stay on the machine, and the
  compression calls count toward the food's D13 cap.
- This departs from D26's "recommended configuration" only in which model compresses memory; hooks, worker and
  retrieval are the food's own. The tasting report states the departure.
- One local setup by the owner, so later runs over Remote Control need no password or login: the corporate root
  CA trusted inside WSL (the corporate network inspects TLS for some sites, so official installers that fetch
  from them fail there), build packages, a one-year `claude setup-token` token in a mode-600 file (each tasting
  arm then runs with its own config folder instead of the user-level one), and the GitHub CLI login on Windows.
