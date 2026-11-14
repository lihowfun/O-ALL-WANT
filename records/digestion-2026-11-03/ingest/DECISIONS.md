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

## D28. The digestion system runs itself (2026-11-05, owner in chat: "你是一個自動自發的消化系統 不是每樣都要等我 盡可能找到SOP自動消化與吸收 盡量降低人類審查 不然這超級沒效率", and on court-skill: "court-skill 這次沒有真的跑 以後不准再測skills 連安裝起來跑都沒跑 就給我下結論"; applies D21, D25, D26)
1. The default actor at every stop is the agent. The owner is waited on only for: entry (a link, or scout
   ticks), release (merging the PR), a tier-C question (D21), and an owner-only prerequisite (a login, a
   token, sudo). Everything else moves without asking; the digestion view says "自動（Claude 接手）" for it,
   never "等你".
2. Static flags inform; they do not park a food. Scanning, flags, per-component holds and owner triage stay as
   safety checks, and copying a flagged component still needs triage. Because D21 rebuilds picked units as
   OAW code with tests and D25 runs food code only in the tasting area, the next step after static is the
   agent's tasting, not an owner triage.
3. No verdict without the food arm installed and run. A tasting whose food arm did not run ends in "no
   verdict" with what blocks it; a "ceiling" argument does not replace the run. This binds relaying another
   session's result too. The catalog engine refuses a recorded verdict whose food arm has no graded run.
4. Tastings are recorded in the ledger (`catalog.py record-tasting`), so the view shows real progress.
5. The loop, per food, in order of expected value: free static screen -> claim and tasting plan from the food's
   own docs -> questions by a fresh agent, frozen in records -> official install in the tasting area (project
   scope when offered) -> all arms run (native, food, OAW version when one exists) -> blind grading ->
   pre-registered rules -> record-tasting -> absorb (tier A/B rebuild on `claude/oaw-2` with tests and one
   goldfish round), plug in, or decline -> release page. D13 caps hold; over a cap the loop stops and asks.
6. Running food code inside the tasting area is the standing permission of D25. If the host's safety layer
   blocks it, the agent records "blocked" and asks the owner once for a standing rule scoped to the tasting
   area, never per food.

## D29. Verdicts: default, optional or excrete (2026-11-06, owner in chat: "照建議改成 D29", on recommendation 1 of `records/digestion-2026-11-06/SOP_AUDIT.md`; refines D21 tier B and D28 item 5)
The SOP audit and the EGM self-test showed the tasting rules both excreted cheap small gains (thresholds far
above run-to-run noise, native at the ceiling, "not shown better" filed as declined) and absorbed costly small
gains (cost ignored once "better"), and that verdict edges sat inside AI-grader noise.
1. Every tasting compares the food with native on two axes, fixed in its PREREG before any run:
   - quality: better, same or worse. An AI-graded difference counts only if it holds in two independent
     gradings of the same answers; mechanical grading (hidden tests, executable checks) needs no second pass.
     Anything inside the band is "same", including "the instrument cannot tell".
   - cost: the food's token median over native's (per question, then median), with the PREREG's "cheaper" rule.
2. Outcomes (with several model conditions, the lowest condition decides):
   - default (進預設): better and cost <= 1.5x native; or same and cheaper by the PREREG rule.
   - optional (可選用): same and cost <= 1.5x; or better but cost > 1.5x. Available, not default; called
     explicitly (as EGM already is in V2).
   - excrete (排掉): worse; or same and cost > 1.5x.
3. Ledger verdicts: default -> `absorb` (rebuild, D21 A/B) or `plug-in` (official version); optional ->
   `optional`; excrete -> `decline`. `not-shown-better` stays readable for old records and is not used for
   new ones. D21 tiers still apply: anything tier C (food code at runtime, new runtime dependency) waits on the
   owner before it is installed, whether default or optional. External plugins OAW does not install are
   documented as optional; the owner installs them through the host.
4. A recorded verdict must match its quality, cost and cheaper fields; the catalog engine checks this.
5. Earlier foods are judged again on the same data and recorded as D29 re-judgments.

## D30. Mechanical limits never stop a food; plain answers on request (2026-11-06, owner in chat: "停止試吃千萬別是甚麼snap 50MB之類的 不要因為這個卡", "snapshot exceeds 50 MB 限制沒有任何意義", "消化吸收盡量最大程度減少我需要審核或人工校閱的步驟 但我如果有問 要能夠直白找出來")
1. Archive size and file-count caps only bound what is stored and scanned; past them files are skipped and
   flagged F-PARTIAL and the food is tasted (claude/oaw-2 27a5312).
2. `catalog.py why [food]` answers the owner plainly: verdict, reason, whether the food's own arm ran, numbers,
   evidence commit, who it waits on (claude/oaw-2 13dcbb1).
3. A grader or runner call that spends zero tokens or is cut by a usage limit is "not run", never a score.

## D31. Light, standard and deep modes; heavy review only on triggers (2026-11-06, owner in chat: "需要深入思考的session時候就用某版 需要light時候就用XXX 怎樣能夠讓這之間切換更絲滑順暢 而不是都要EGM審半天", then "該補補 幫我往下 減少我操作")
1. Three modes, default light:
   - light: a plain session with OAW's minimal policy and no review.
   - standard: effort high plus one fresh-context reviewer of the diff and tests. The D21 goldfish round is this level.
   - deep: plan mode first, the highest effort, then the EGM review when EGM is installed.
2. The agent picks the mode with a deterministic check of the change; the owner does not. Deep triggers:
   - harness or infrastructure code that runs every session (the Merge Gate category);
   - irreversible-looking changes;
   - a new design document.
   A large code change is standard. Everything else is light. The triggers live in code with tests and are themselves to be checked against outcomes later (D29 methods).
3. EGM never runs by default. Its skills are already explicit-invocation only; the full EGM review is reserved for deep.
4. When fairness or consistency between foods conflicts with saving tokens, keep one yardstick for every food. The owner chose to finish codegraph's Haiku repeats although the verdict could not change.
5. Implemented on `claude/oaw-2` (2026-11-06):
   - Commits 08dbe3c, 4225749 and 8e607f0. `scripts/oaw_mode.py suggest|show` is installed with every recipe, and AGENTS.md carries one rule: light by default; run `suggest` before any review; deep always uses `--effort max`.
   - The change is deep by its own triggers, so it got cross-family fresh-context reviews (`codex review --commit`):
     - round 1 found 5 P2;
     - round 2 found 1 P1 (Windows test) and 2 P2;
     - round 3 found none.
   - harness_check passed 9/9 (508 tests, Linux).
   - Adherence smoke test of the AGENTS.md rule: Sonnet 5.5, one run each on a CI-workflow change and a docs change. Both ran `suggest`, then `show deep` or `show light`, matching the change. This shows the rule is followed, not that it helps.
   - Windows is not verified on a Windows host yet; CI runs only for PRs into main.

## D32. Tasting yardstick (2026-11-07, owner in chat: "全部照建議開工", approving Q1 of `docs/plans/v2.0.1-execution.md` §8 on `claude/oaw-2` db27874; refines D29)
Source: `records/digestion-2026-11-07/validation/RESULT.md`. Implemented by plan item W0.
1. The second grading always comes from a different model family (Codex). Grading twice with the same family is not independent: Opus vs Opus kappa 0.97, Opus vs Codex 0.46–0.62 (V4).
2. Wrong-claim counts decide a verdict only when both families agree (V3, V4).
3. The default sample is 12 questions × 1 run. Questions are treated as a random sample, and questions at the ceiling are replaced.
4. Zero-spread floor: the interval never collapses to a point. With one run per question, the floor is the pooled within-question SD from earlier repeated runs of the same question bank and model.
5. Before excreting a food, test at least one condition on the food's home turf (V8).
6. Cost: "too expensive" only when the CI's lower bound exceeds 1.5×. A CI straddling 1.5× is "cost undetermined".

## D33. One review switch; EGM in deep (2026-11-07, owner in chat: "全部照建議開工" on Q2, then "EGM 貴的有道理的話那很棒啊 但後續要想一個按鈕開關 需要品質好審查時候開 不需要可以關 預設先調整最好版本"; refines D31 item 3 and V2's "EGM keeps its explicit invocation policy")
1. Each project has one EGM switch with three positions:
   - on: every deep task gets the full EGM design review.
   - off: EGM never runs.
   - auto, the default: deep runs whichever design review the current evidence ranks best.
     - Today that is EGM, the only design review with a measured gain (V5: 3/3 vs native 1/6).
     - X2's pre-registered rule can move auto to a readiness checklist, a single cross-family review, or no extra design review.
     - The owner's later words ("預設先調整最好版本") take auto to EGM before X2 reports, instead of the plan's "only after X2 selects E".
2. The agent starts the review itself; the owner types nothing.
   - Before each EGM run the agent prints an estimate of tokens and minutes.
   - Over the project's cap (default 25M logical tokens) it asks first.
   - If a usage limit cuts the run, implementation waits until the review finishes.
3. The switch lives in one project setting with three faces:
   - the CLI (`scripts/oaw_mode.py egm on|auto|off`);
   - the chat (the `oaw-review` skill);
   - later, a button in the digestion pane.

## D34. User install route (2026-11-07, owner in chat: "全部照建議開工" on Q3)
- `oaw.py add/list/remove` installs into the user's own project.
- With explicit consent given in the single install question, it may install untasted skills, scripts, hooks and MCP servers.
- Every component keeps a change record, so removal restores exactly what it changed, including its entries in shared settings files.
- OAW's own absorb into its defaults keeps its blocks: no hooks or MCP, executable skills held, and runtime code is tier C under D21.

## D35. Higher caps while building 2.0.1 (2026-11-07, owner in chat: "D13 10M上限先放寬 我們還在建立中 多點機會試", then "甚至你放寬到20M 或更高 只要合理使用 我都覺得還好"; refines D13)
- The owner set no number. The agent chose 30M as "higher, used reasonably".
- Until 2.0.1 is released:
  - 30M logical tokens (input + output + cache) per food or experiment;
  - 30M digestion overhead per round.
  - Above 30M the agent still stops and asks.
- Subscription billing only and `apiKeySource: none` are unchanged.
- Records report both logical tokens and tokens without cache reads.
- The 2026-11-07 plan review (EGM 18.5M) is within this cap; its deviation note stays as history.
- Applied to the 2.0.1 plan: X1 adds the fourth cell (VS Code × Haiku 5.5), and X2 grows to 12 cases (10 new).

## D36. X2 ceiling 60M (2026-11-09, owner in chat: "給60M"; refines D35 for X2)
- Asked after the escalation review (`records/escalation-2026-11-08-x2/`): Fable 5.1 and gpt-6-astra both found that the
  25M design cannot decide, and asked for 16 unseen defect cases + 4 unseen clean cases (33-48M Claude).
- X2 may spend up to 60M Claude logical tokens (input + output + cache). Other items keep D35's 30M.
- With the ceiling above both reviewers' estimates, the agent drops Fable's futility stop (astra: adaptive rules add
  method risk) and keeps Fable's calibration step (measured floors instead of borrowed ones). All 20 cases run in
  every arm; expected spend about 42M.

## D37. auto means one fresh-context review until X2 decides (2026-11-09, owner in chat: "改"; amends D33)
- Until X2 reports, the EGM switch's default `auto` runs one fresh-context design review of the plan, not EGM.
- `on` still runs full EGM for every deep task; a finished EGM review also satisfies `auto`.
- Why: EGM's measured gain rests on one selected case (V5's `events`), at about 28x native cost; the Codex audit
  flagged "EGM as deep default" as the verdict most at risk, and both escalation reviewers advised native until X2.
- Replaces D33's line that auto takes EGM before X2 reports ("預設先調整最好版本").
- Where catalog or docs describe EGM's default status, it is "not tested", not "declined".
- Outcome (2026-11-09, X2 RESULT): both cells keep N; the Codex judge applied the frozen rule and the sensitivity
  run agrees. Per the X2 PREREG this interim rule becomes the standing rule. Native review already found 47 of 48
  planted defects (ceiling), every alternative had a clean-case false alarm both graders found, and E cost 27-29x
  native tokens. This is not a finding about large design documents. EGM stays available through `on`.

## D38. Two purposes of intake; capability foods get their own track (2026-11-10, owner in chat: "至今 skill 吸收 有兩種目的 1. 對整體 OWA harness or 使用者 repo 有所幫助 2. 整體使用者的repo 可以新增一些過往沒有得能力，我們整理後打造起來，譬如可以是影片剪輯，可以是遊戲製作的相關skills"; refines D4)
- Purpose 1, benefit: the food makes work the agent already does better or cheaper (memory, review, code map,
  token saving). Judged against native, as before (D29, D32).
- Purpose 2, capability: the food gives the user's repository an ability it did not have (the owner's examples:
  video editing, game making).
- D4 item 1 changes: the scout's relevance filter no longer drops foods unrelated to coding-agent skills. They go on
  a separate capability list. Entry is unchanged: nothing is tasted until the owner picks it.
- The owner stated the two purposes only. The capability track's judging rules are the agent's draft in
  `docs/plans/v2.0.1-value-check.md` section 4 on `claude/oaw-2`, open to the owner's change:
  - compared against native with the same underlying tools installed, on finished-artifact tasks with mechanical checks;
  - outcome is optional or excrete, never default;
  - an idle condition: installed but unused, it must not raise startup tokens by more than 2% or make ordinary tasks worse.
- Same message, the owner's question that starts H1: "所以我們至今 OWA 2.0.1 有調整到最好嗎? 還是這harness 讓opus5.5跟codex 6.1 sol
  有比沒有更慘? 效果依樣 記憶沒變 但token變多的話 也許會變蠻雞肋" and the go-ahead "先整合相關內容寫 md 然後就開始執行".
  OAW itself is held to the gate external foods pass: installed against not installed, on real work
  (`records/v2.0.1-experiments/H1/`). Budget is D35's 30M.

## D39. I16 ceiling 65M (2026-11-10, owner in chat: "請你從 30M 加到 65M dk3u3" (dk3u3 is 可以 typed on the Zhuyin layout), then "可以65M"; refines D35 for I16)
- Asked after I16 calibration (records dff4be0): the frozen design needs about 63M Claude in total; the alternatives
  offered were 45M (Claude cell N and F only) or 30M (no Claude verdict).
- I16 may spend up to 65M Claude logical tokens (input + output + cache). The full frozen design runs unchanged.
- Claude-cell runs go one process at a time across experiments (two parallel Claude processes hit the subscription
  session limit in X2). Order: H1's Claude cell, then I16's.

## D40. The agent decides at release whether H1 trims the 2.0.1 defaults (2026-11-10, owner in chat: "依 H1 結論決定 2.0.1 的預設要不要再減：發佈時由你決定 你決定 你不能決定的話讓我開fable5.2"; amends `docs/plans/v2.0.1-value-check.md` section 6 on `claude/oaw-2`, which left this to the owner)
- At release the agent applies the uses fixed before H1 ran (value-check section 6, "H1 的結果會怎麼用") and decides
  whether any part leaves the defaults.
- When those uses do not point to one action, the agent does not pick a side: it says so and the owner opens a
  Fable 5.2 session to decide. Cases named in advance: the two cells point in opposite directions; a worse class
  cannot be traced to one part; H1 ends without a verdict for a cell.
- This covers the defaults decision only. Other release steps stay with the owner (D21).

## D41. Capability entry: the harness first, then PPT or video (2026-11-10, owner in chat: "能力型候選要試哪幾個 先擬自行測試 首選harness 再來PPT Skill or 影片製作能力的新增都可以測"; applies D38)
- The agent reads 首選harness as D38's purpose 1, work on the OAW harness itself: H1, then I16's Claude cell, keep
  the Claude subscription first.
- Picked for the capability track: PPT skills (not on the 2026-11-10 list, so a scout runs first) and video making.
  Game making is not picked.
- 先擬自行測試: the agent drafts its own tests first (finished-artifact tasks, mechanical checks, against native with
  the same underlying tools installed), per D38's draft rules, then tastes without further sign-off (D28).
- The agent reads 都可以測 as consent to the user-directory installs the tests need (ffmpeg, asked in
  `records/v2.0.1-experiments/capability/CANDIDATES.md`). Nothing is installed system-wide.
- Budget: D35's 30M per food.

## D42. H1 class C is filled with ceiling units after the last supplement (2026-11-11, owner in chat: "1 補滿天花板題"; amends PREREG 驗題 6 of `records/v2.0.1-experiments/H1`)
- After three class C authors only two units were below ceiling in the codex-cell calibration (one large, one design).
  The agent offered three options with the cost of each: fill with ceiling units (named in advance: large-2-c1,
  design-3-c1), run with the two, or rewrite the brief for new authors. The owner chose the first.
- Rule: once the supplements are used up, a type with fewer than two units below ceiling is filled to two with its
  units at ceiling, in authoring order. Units that failed verification or the audit never fill; too few usable
  units still stops for the owner. Class B is unchanged.
- Cost, stated before the runs: N already scored these two units 1.0 once in calibration, so in the codex cell they
  may be weaker at showing "better"; only where N1 and N2 both score 1.0 in the main runs can they show just equal
  or worse. Results list the filled units.
- Records made before the freeze by the previous runner stay valid (PREREG 凍結前的修正 2); nothing is re-drawn.

## D43. Tracking: GitHub Issues and milestones on D22's four branches (2026-11-11, owner in chat: "就用推薦的git flow"; settles the 2026-11-05 request "後續工作要用 git flow 之類方法好好記錄與追蹤")
- The agent's recommendation of 2026-11-05, now adopted. Branches stay as D22: main, codex/oaw-2-native-upgrade,
  claude/oaw-2, records. No per-feature or per-round branches.
- Work items are GitHub Issues, one milestone per stage (v2.0.1; capability tasting; after 2.0.1). Each issue states
  its done condition. Commits and records refer to it as `Refs #N`; it is closed with the commit or record that
  shows the condition met.
- Commits follow Conventional Commits, `type(scope): subject` (feat, fix, docs, test, refactor, chore; `!` for a
  breaking change). Records commits use `docs(<experiment or area>): ...`.
- Releases are SemVer tags on main (`vMAJOR.MINOR.PATCH`) with a GitHub release. 2.0.0 was never released, so the
  next tag is v2.0.1 (W6).
- Integration shows as pull requests: claude/oaw-2 gets a draft PR (base codex/oaw-2-native-upgrade until PR #4
  merges, then main).
- A Project board needs the `project` token scope, which the current GitHub logins lack. The owner adds it
  (`gh auth refresh -s project`) if a board is wanted; milestones show progress meanwhile.

## D44. I16 ceiling 85M (2026-11-11, owner in chat: "加到 85M 跑完"; refines D39)
- Asked after the I16 Claude cell was paused between runs at 3 of 48 main runs (spent about 27.4M): runs cost
  0.82–1.71M each against the calibration estimate of 0.8M, so the full cell plus grading projected to 68–80M,
  over D39's 65M. An incomplete cell gets no verdict (I16 PREREG, 「資料不完整」), so running into the guard would
  have spent the tokens without a Claude result.
- Options put to the owner: raise to 85M and run the frozen design unchanged (chosen); stop at 65M with a Codex-only
  result; run only N and F in the Claude cell as a deviation (about 50M).
- I16 may spend up to 85M Claude logical tokens. The runner's guard is set at 83M so about 2M stays for grading.
  Nothing in the frozen design changes; the run resumes from its ledger.

## D45. D40 settled: nothing leaves the default, five traced defects are fixed first, release is the only open line (2026-11-12, owner in chat after switching this session to Fable 5.2: "很棒 請統整一下 制定接下來的 執行計畫與調整 roadmap 讓發散的問題收斂 最佳化調整"; settles D40, proposes a change to D43's PR base)
- How the request was read: D40 leaves H1's case (one cell without a verdict, cells opposite on memory) to the
  owner's Fable 5.2. On 2026-11-10 the owner had said the agent may reopen on Fable 5.2 itself when needed
  ("需要的話 你這邊重開就好"); on 2026-11-12 the owner switched this session's model and asked for a converged plan.
  The agent took that as the D40 hand-over and decided. The owner did not pick an option and can overturn any item.
- Evidence added before deciding: `records/v2.0.1-experiments/H1/AUDIT-D40.md` (command-level audit of the O runs).
- Defaults:
  1. No part leaves the default recipe. The merged word is undetermined, not worse and not 雞肋; the Codex cell is
     helpful. The post-hoc audit supports fixing rules and two Codex-side defects first; it is descriptive, not a
     registered test, so keeping the default is this decision's call and the package's effect stays undetermined.
  2. Fixed before release (each traced in the audit):
     - M1: the save rule becomes unconditional (decisions and facts later work needs are saved before the session
       ends), after the L arm's two-line rule. The `oaw-evidence` skill's "explicitly requested" limit changes
       with it. It still asks for no note after unrelated tasks.
     - M2: an empty project recall says so and the agent continues with the host's own memory and history.
     - M3: `memory add` succeeds under Codex's `workspace-write` sandbox, which keeps `.agents/` read-only. Existing
       files are not moved in 2.0.1. The design (ordering across the two sources, superseded entries, the cursor;
       fallback only on an explicit read-only or permission error; confinement, credential refusal and the locked
       atomic update kept) gets one fresh-context review before coding.
     - R1: on Codex the review step is a fresh subagent, not `codex review --uncommitted` (it cannot start inside a
       sandboxed Codex session; 4 of 4 failed).
     - R2: deep's code review is one round by default. "Until a round finds nothing new (at most 3)" was a plan
       choice with no measurement; H1 measured whole-unit cost (design units 3.3–8.7x native) and X2 supports one
       fresh-context review of a design, not a number of code-review rounds. One round is therefore a cost-saving
       hypothesis for the fix check. Its risk: defects introduced while fixing round-one findings get no
       independent review.
  3. One fix check, written down and reviewed once before it runs: the O arm only, on H1's frozen units, both
     cells, same runner and mechanical grader.
     - It has its own manifest (the fixed OAW commit, digests of H1's unit bank and grader, digests of H1's O and
       N rows). H1's freeze, ledger and verdict stay untouched. It produces no new owner verdict word.
     - It has its own ledger as a new experiment under D35, not H1's remaining 5.94M. H1's O arm cost 12.76M in
       the Claude cell; with R2 working the estimate is about 8M; the stop is 17M (12.76M × 1.3, stop rule 2).
     - Each fix needs its own observed event. A mechanism that was not triggered is recorded as not observed, not
       as passed.
     - Its conclusion is limited to "these runs met the preset regression thresholds". One run per unit, and the
       same units were used to find the defects, so it is neither proof of no regression nor new evidence of
       benefit. The README headline stays H1's frozen result.
     - If it fails: memory thresholds → M1 and M2 are reverted; a design-unit score drop → R2 is reverted; M3 or
       R1 still failing → release blocker, fixed against their model-free reproduction, not another full check;
       incomplete data → no pass is declared (a usage interruption resumes from the ledger; the budget stop goes
       to the owner). Any revert means the final commit passes the gate and CI again. No second iteration.
  4. Not taken: brief option B as written (the fresh-context review stays; R2 trims only the extra rounds) and
     option D (no enlarged retest before release).
- Convergence:
  - The v2.0.1 release is the only open line until it ships. No new experiment starts before that.
  - Proposed, waiting for the owner: PR #16's base moves to `main` now instead of D43's "after PR #4 merges".
    CI runs only for pull requests into `main`; PR #4's last run (2026-10-30) failed on Windows and macOS;
    `claude/oaw-2`, which contains PR #4's head, had never been run by CI. The agent's own attempt to change the
    base was stopped by the session's permission check and was not worked around, so D43's base stands until the
    owner approves the change or makes it on the pull request page. With the new base the owner would merge one
    pull request (#16, merge commit) and PR #4 would then show as merged.
  - After the release: PPT tasting (#13), with the tasting kit (#9) built as its runner. G5 (#15) starts as an
    independent re-application of the yardstick to the existing data by Codex; new runs only for a food someone
    wants to use (D31 item 4 still holds for those).
  - Parked with written restart conditions: video (#14, needs ffmpeg), G6, G7, X5, and moving the memory store
    out of `.agents/`. X5's per-commit log, which the 2.0.1 plan asked for from the start of work, was never
    kept. Path-based triggers can be recomputed from git history at analysis time; the context-based one
    (plan-given) cannot and is out of X5's scope.
- Stop rules for the agent's own work (the owner can lift any of them per case):
  1. A "better" claim is tested only where calibration shows room. If fewer than half the units are below ceiling,
     the run is cut to a no-worse-and-cost check or not run, and recorded as "not measured: ceiling". Intake of
     outside foods is the exception: a comparison already used for comparable foods is not cut by arm or cell to
     save tokens (D31 item 4).
  2. A budget request uses the pilot's real cost per run × runs × 1.3 (I16: 0.8M guessed, 0.82–1.71M measured).
  3. A fix gets one check. Failing it means revert, not another iteration. A product defect with a model-free
     reproduction is the exception: it is fixed until that reproduction passes.
  4. Reviews stop at 3 rounds (unchanged).
- Review: one independent Codex (gpt-6.1-sol) round on the plan and this entry said "先改再做": 2 blocking, 5
  should-fix, 1 note. All eight were accepted and are in the text above
  (`records/v2.0.1-experiments/H1/D45-review.md`). The fix check's own write-up gets its review before it runs.
- The plan is `docs/plans/v2.0.1-release-path.md` on `claude/oaw-2`; `ROADMAP.md` points to it.
- Addendum (2026-11-12, same day): the PPT tasting (#13) was already running in its own session, started by the
  owner, when this entry was committed. It continues there, does not gate the release, and is the one existing
  exception to "no new experiment before the release". Its model runs and the fix check do not overlap (D39).


## D46. Start the Harness2 evaluation-method implementation now (2026-11-13)

Owner in chat: 「那評估這塊 我們可以吸收阿 你開始動工」, after receiving the
source-review conclusion and CC handoff. This authorizes implementing the
evaluation-method absorption now; U1 no longer waits for the release.

- First deliverable: an opt-in, stdlib evaluation accounting/report tool and
  fixtures, plus a read-only adapter over existing FIXCHECK evidence. Preserve
  existing eval_stats/improvement semantics; no third scorer or startup rules.
- Work on `codex/harness2-evaluation-u1` from release-polish `5af21f6`; do not
  change frozen FIXCHECK candidate `c2d9852`, its state/manifest/thresholds, or H1.
- This is owner-directed method engineering, not an official Harness2 tasting
  verdict or proof of quality/token gains. U2/U3 model-readable policies still
  require their planned validation before promotion.
- No new model experiment, increased quota/budget, pending CI routing change,
  rejected cache relocation, merge, tag or release is authorized by this entry.
  Claude FIXCHECK still waits for 18:00 and continues independently in CC.

## D47. Carry the release on and move the absorption lines forward beside it, by delegation (2026-11-13)

Owner in chat, to the Claude Code session that took over from the Codex handoff: 「目前 fable 跟 codex
針對 OAW repo branch 有很多大更新 請你確認一下進度 並且follow 下去 尤其是 harness2 的專業評估harness
好壞的地方直的我們吸收 另外EGM 或其他的skill 最佳化吸收也要推進下去 你這邊也可以隨時指派codex 研究或是
讓其他opus 5.5 往下」.

- Reading (Claude's): finish the release line, and beside it move the absorption work that D45 had placed
  after the release: the Harness2 method (after U1), EGM, and the earlier skill verdicts. Work may be
  handed to Codex and to Opus 5.5 agents. This relaxes D45's "one line at a time" for offline work only.
- Done under it the same day, with no experiment model answers beyond the FIXCHECK already authorized:
  a cross-family review and fix of U1; the U2 card candidate with a draft preregistration; a plan (not a
  run) for tasting the official Harness2 runtime; G5, the re-judgement of three intake verdicts on
  existing data (#15); an EGM cost anatomy from existing traces with a study design for large documents.
- Not authorized by this entry: any new model experiment, a budget above D35's 30M per experiment, API or
  Vertex billing, a pull-request base change, merge, tag or release. Three questions were put to the
  owner and are open: whether to deviate from FIXCHECK's preregistered disposition, the base of PR #16,
  and whether to fund the Harness2 runtime tasting.
- Operations, same day: the local system disk was full. Owner: 「請你用正確的 /mnt/drugs」, 「如果我們的
  一些內容可以清 或超過兩個月都沒動 也可以清」, 「已經沒再用或達成目的的也可以刪」, 「不要你去做這件事
  請你指派opus 5.5 去做」. Project data goes to the shared storage; only an experiment's state root stays
  local while it runs; cleanup is delegated to an Opus 5.5 agent.

## D48. Follow the preregistered FIXCHECK disposition; start the release steps and the two follow-up lines (2026-11-14)

Owner in chat, answering the 2026-11-13 report (three open questions, then next steps listed as P0, P1,
P2 with a recommendation on each): 「P0 -P2都照妳建議直接動工」.

- FIXCHECK disposition: the preregistered one stands. M1, M2 and R2 are reverted; M3, R1 and the #18
  path fix ship. No deviation, so the README carries no owner-override note.
- PR #16: base changed from `codex/oaw-2-native-upgrade` to `main` (done 2026-11-14 through the API),
  so the six-job CI runs on every push. `claude/oaw-2` was fast-forwarded to the final integration
  `5c4e53b`; no new remote branch.
- Release steps authorized to proceed without further questions: version 2.0.1, six-job CI, one
  cross-family release review of at most three rounds. Merge, tag and release stay with the owner.
- P1, authorized inside D35's 30M per experiment, one Claude experiment process at a time:
  the EGM native-only calibration on real large documents (#20; estimate Claude 2.7–3.6M, Codex
  3.7–4.6M), and the preparation and A/B of the U2 minimal-change card (estimate 27.7M, unit price not
  yet piloted). The full EGM comparison (about 27M) is asked again only if calibration shows room.
  This lifts the "no new experiment before the release" rule of D45 for these two lines.
- P2: the finished H1 and FIXCHECK state roots on the local disk (about 19 GB) move to the shared
  storage, byte-identical with a hash manifest, by an Opus 5.5 agent.
- Not covered by this answer, so unchanged: the official Harness2 runtime is not tasted (the
  recommendation was not to); closing #15 and the branch that should hold the U2 candidate were asked
  separately and are still open.

## D49. Release as recommended; EGM stops at "no conclusion"; the U2 pilot runs to its 18 runs; confirm the evaluation methods in this version (2026-11-14)

Owner in chat, answering the 2026-11-14 report's three open decisions (the owner numbers them P0, P1,
P2 in the order release, EGM, U2):
「P0照你建議 p1不用繼續 但我們至今不管harness2還怎樣 應該找到最公正的幾種方式評估harness好壞 請確認有這版 p2 請照預設跑到18次別停」.

- Release (P0): as recommended, 2.0.1 is released. Merge, tag and release stay with the owner (the
  recommendation named the owner as the one who does them); PR #16 was still an open draft when this
  was recorded.
- EGM (P1): not continued. Stage one of #20 closes with the formal outcome "no conclusion"; no EGM
  arm is run; EGM stays an explicit opt-in. This is not a verdict on EGM.
- Evaluation methods: the owner expects that, whatever happens to the Harness2 lines, the project
  has by now settled the fairest ways to judge whether a harness is good, and asks to confirm that
  this version has them. Lead reading: "this version" is the 2.0.1 release. The check and its result
  are recorded in `records/release-fixes-2026-11-13/PROGRESS.md`.
- U2 (P2): the pilot continues to its planned 18 runs with the default settings and does not stop.
  Lead reading: the 600,000 observed ceiling stays; a run stopped at the ceiling is kept, flagged and
  not redrawn, and no longer ends the stage. This departs from the frozen pilot text (a metering
  error stops the stage) on the owner's instruction, given after seven attempts existed. It is
  implemented by a lead wrapper outside the frozen files and recorded in the state before the first
  continued launch. The stops for a severe violation or a broken checker stay. No test split is
  authorized by this.
