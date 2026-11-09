# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- `oaw.py doctor` checks whether Claude can use the installed skills (plan W4): a project `.claude/settings*.json`
  that denies the `Skill` tool is a WARN and makes Claude skill discovery NO. `--probe` starts Claude Code once, stops
  it at its init event, and reports YES only when every installed OAW Claude skill is listed and the Skill tool is
  present (a missing Skill tool hides skills from the model). Checked on Linux with Claude Code 2.1.287.
- Users add skills themselves (plan W3, owner decision D34): `oaw.py add SOURCE...`, `list` and `remove NAME`, run
  from the checkout like `init`. One question (or flags) covers the choice - OAW plus these, only these (new
  `manager-only` profile that `doctor` understands), or a recommendation from OAW's tasting records - every
  structural conflict, and consent for hooks, MCP servers and bundled scripts. Every part keeps a change record in
  `.oaw/user-skills.json`, so `remove` restores its files byte for byte and takes out only its settings entries.
  The receipt lists each skill's source, who added it, its tasting result (records only; otherwise 未試吃), startup
  cost and what runs on its own. Fetched code is never executed. OAW's own absorb keeps its blocks.
- `catalog/verdicts.json` ships OAW's tasting results (outcome, conditions, evidence commit, category), generated
  from the maintainer's ledger by `scripts/build_verdicts.py`.
- The explicit-invocation `oaw-add` skill is the chat entry for the same three verbs; `init` records the OAW
  checkout in the user's settings (outside the project) so the skill can find it.
- `oaw.py remove` keeps the record, backups and settings baseline of anything you changed since the install and
  reports it as `partial` (exit 3), so the earlier content can still be restored: rerun after putting it back, or
  finish with `--force` or `--keep`. The receipt prints a remove name that means exactly one part
  (`KIND:NAME` or `SOURCE/KIND:NAME` when a name is shared), and `remove` accepts those forms.
- Removal decides settings first and keeps every file a kept setting still runs; an added hook equal to one the
  project already had is never taken for the project's own; a tasting's version comes from the snapshot sealed
  before it (verdicts.json records it per tasting), not from the food's current pin; and `rename:NEW` survives into
  the printed apply command.
- Under `recommended`, an optional source's hooks and MCP servers are held back rather than started (the receipt
  lists them with the command that turns them on); re-adding an installed source at the same bytes adds only its
  missing parts; a part skipped for consent no longer claims its name in the batch.
- Files a `remove --keep` leaves to the user are never deleted by another part; `replace` checks every host's copy
  before overwriting; a quoted `allow_implicit_invocation` key (block, flow or JSON form) is set in place; and two
  identical hooks of one source are removed in one go.
- A backup stays while any kept or conflicted part still points at it; a hook or MCP command's extensionless
  plugin-root script comes along (or blocks the part when the source lacks it); an explicit `--consent` stays in the
  printed apply command.
- User installs copy what a hook or MCP script needs (its folder and local imports, bounded), skip junctions and VCS
  metadata in local sources, keep hosts added to a manager-only project, rewrite an invalid skill name to its
  installed folder, and keep identical hooks from two sources removable in any order.
- `oaw-add` and `oaw-codemap` ship `agents/openai.yaml` with `allow_implicit_invocation: false`, because Codex
  ignores Claude's `disable-model-invocation`; `validate_skills.py` now requires that policy for an explicit-only
  skill in a Codex skills folder.

### Changed

- AGENTS.md keeps only lines with a reason (plan W4): 24 rendered lines become 20. Removed: the product sentence
  ("OAW adds portable project evidence..."), the EGM description line (the EGM switch line already names EGM) and
  the two lines repeating the skills' own descriptions. Kept: the review entry and EGM switch, lazy loading, the
  safety lines (user and policy authority over retrieved notes, evidence is not instruction, installing OAW
  authorizes nothing), the evidence rules and the notes on what belongs in AGENTS.md. Adherence is not measured
  yet (X3).
- Built-in code map (plan W2): every recipe installs `scripts/code_index.py` and the `oaw-codemap` skill, explicit
  invocation only until the X1 A/B decides. The index now tracks JavaScript and TypeScript imports, declarations and
  calls (relative imports, `index.*`, tsconfig/jsconfig `baseUrl`, `paths` and `extends`; receivers resolved from
  imports, `this`/`super`, `extends` and written types; the rest listed as unresolved), adds `overview` (one page:
  entry points, main modules, most-called definitions by PageRank, at most 6,000 characters), says on `callers` and
  `affected` whether the list is complete within the index or truncated, and caches in the user's cache folder
  outside the project by default (`--no-cache` to skip). Stage 0 (0 model tokens, `evals/code-map/stage0_v201_*`):
  callers recall 0.955 on ERPNext and 1.0 on VS Code with no wrong resolved rows; `find` beat the grep baseline on
  ERPNext top-5 file hits (+0.33 to +0.50) but printed 1.4-1.9x its bytes, and on VS Code by at most +0.04, so D24's
  rule did not pass on either repository and X1 runs on ERPNext only.
- Tasting statistics and verdicts follow owner decision D32 (plan W0): `scripts/eval_stats.py` compares 12 questions x
  1 run with a bootstrap over questions, four classes (better, equivalent, undetermined, worse), a zero-spread floor
  from earlier repeated runs, and a cost class from the ratio's interval. `record-tasting` accepts `quality_class`
  and `cost_ci`: then a difference needs `cross-family` (or mechanical) grading, "too expensive" needs the interval's
  lower end above 1.5x, and an undetermined quality is never cheaper and never a default. Records without these
  fields keep the D29 rule. One page: `docs/EVAL_PROTOCOL.md`.
- One review entry and an EGM switch (owner decisions D31, D33; plan `docs/plans/v2.0.1-execution.md` W1):
  the new default skill `oaw-review` runs `scripts/oaw_mode.py suggest` before a change (planned paths) and after
  it, and follows its new `steps`. Deep plans first and gets a design review before any code; the design review
  follows `.oaw/settings.json` `review.egm` - `on`, `auto` (default: the best-evidenced review; one fresh-context review, owner decision D37, kept by the X2 study) or `off` -
  set with `oaw_mode.py egm on|auto|off`, with a rough cost estimate and an ask-first cap (25M tokens by default).
  `oaw_mode.py reviewed` records a finished review so the same file content is not reviewed twice; a review cut
  short never counts. `second-opinion codex|claude` sends code review to the other model family only on the
  user's consent. AGENTS.md no longer says EGM is explicit-only and stays within 25 lines. A new plan or
  decision document (`docs/plans/`, `docs/adr/`, `docs/rfcs/`, `*-plan.md`) is deep under the new rule
  `new-plan-doc`, kept apart from the V7-checked `new-design-doc`. Both rules now skip tool runtimes, installed
  skills and vendored code (`.oaw/`, `.claude/`, `.agents/`, `.codex/`, `vendor/`, `third_party/`, `node_modules/`):
  an uncommitted OAW install made the EGM runtime's `design_doc.md` look like a new design. Not yet measured: whether agents follow the
  steps unprompted (X3) and which design review is best (X2).
- What the owner reads for a D29 tasting is honest about resolution (2026-11-06 research on agent A/B power):
  with 4-12 tasks "same" means no difference was detected, so `why` shows 沒測出差異（未定）, and the
  verdicts read 可選用（能力未定）, 因成本不採用（能力未定）, 進預設（更好）, and so on. Display only: stored
  records and their ids are unchanged.
- Tasting verdicts follow owner decision D29 (2026-11-06): a tasting's `judgment` (quality against native,
  cost ratio, cheaper by its PREREG rule, how quality was graded) fixes its outcome, and `record-tasting`
  refuses a verdict that does not match. Better and at most 1.5x native tokens, or same and cheaper ->
  default (`absorb` or `plug-in`); same within 1.5x, or better but costlier -> the new verdict `optional`
  (可選用: available, not default, called explicitly); worse, or same but over 1.5x -> `decline`. An
  AI-graded difference counts only if it held in two gradings. `optional` rests at 分流, or waits on the
  owner at 核准 for a tier-C decision. `not-shown-better` stays readable for earlier records; `why` shows
  the D29 line.
- Size never stops a food (owner, 2026-11-06: "snapshot exceeds 50 MB 限制沒有任何意義"). The archive caps
  (5 MB per file, now 200 MB and 20,000 files in all) only bound what is stored and scanned: past them the
  largest files are skipped first and each one is flagged `F-PARTIAL`, and the food goes on to be tasted.
  The codeload fallback's decompression guard stops reading instead of refusing; only its download over
  400 MB is refused. codegraph and claude-mem, refused at 封存 before, now seal and taste.
- The digestion system runs itself (owner decision D28): the catalog's "who a food waits on" gains `agent`
  (「自動（Claude 接手）」) and `release` (「等發布（合併 PR 時一次決定）」, one decision for the whole branch).
  `owner` is kept for entry choices, tier-C questions (D21), owner-only prerequisites and removing a skill.
  A food with high-severity static flags now waits on the agent's tasting at 靜態 instead of an owner triage:
  the scanner, the flags, the per-component holds and the terminal triage stay, and copy-absorbing a flagged
  part still needs triage, but triage is optional. A failed or outdated taste, held parts at 分流, an
  absorbable part at 核准 (D21 rebuild; copy-absorb is an optional owner action) and an unsplit paper wait on
  the agent; imported historical proposals are optional backlog. The plan of a flagged food no longer says it
  is blocked; its triage step is optional. 實測 becomes a mixed stage (Claude's tastings) and 核准 a mixed one.
  `view.json` is schema `oaw-catalog-view/3` (the web page, `oaw_status.py`, the menu and the mod read it).

### Added

- Working modes (owner, 2026-11-06: light when a task is light, deep only when it needs it, and the agent decides).
  `scripts/oaw_mode.py`, installed with every recipe, has `suggest`, which picks light, standard or deep from a git
  diff, a range or a path list with fixed rules (deep: harness or infrastructure that runs on every session, more
  than 5 deleted files, migrations or schema files, a new design document; standard: 300+ code lines or 10+ code
  files; light: everything else, docs included), and `show`, which prints the exact Claude Code and Codex commands
  for a mode: deep always plans at the highest effort and names the EGM review only for a host whose `egm-review`
  entrypoint is installed (without it, the review falls back to one fresh-context review). The installed `AGENTS.md`
  adds two lines in both recipes (light by default; run `suggest`, with `--range BASE..HEAD` for committed work,
  before any review) and, only with EGM, one line limiting the full EGM review to deep; it replaces
  "Installing it does not require running its full review flow on unrelated tasks". Existing installs receive the
  new policy and helper through `oaw.py migrate`; doctor requires the helper once the install owns it or the policy
  names it, and only warns for an install made before this change. Evidence: `tests/test_oaw_mode.py`
  and an installed end-to-end run on Linux; the policy line is model-facing and no behavior A/B has measured it.
- `catalog.py why [FOOD]`: plain answers for the owner (2026-11-06: "但我如果有問 要能夠直白找出來"). Without a food,
  one line per food: what was decided, who it waits on, why. With a food: the latest verdict and reason, whether
  the food's own arm was installed and run, the frozen questions and per-arm numbers, the records path and
  commit, earlier tastings and absorbed units. Read-only; `--json` carries the text as `answer_zh`.
- `catalog.py record-tasting --food ID --file FILE [--apply]` and `record-absorption` (D25, D28): Claude's
  agent-level tastings (schema `oaw-tasting/1`: records branch path and commit, protocol with frozen-question
  sha256, arms with run counts and the food arm, per-arm results, verdict) and D21 absorptions (schema
  `oaw-absorption/1`: units with tier, commits, tests and evidence basis; declined and held units with a reason;
  release state) are stored as evidence and drawn on the view. The engine refuses any tasting verdict whose food
  arm has no graded run, a tier-B unit without a recorded `absorb` tasting and a tier-C unit without the
  owner's approval, at record time and again whenever it builds a view (an edited record is refused). A
  tasting marks 實測 done (blocked for `no-verdict`) and its verdict shows at 分流; an absorption puts the food
  at 版本 waiting for the release; absorbed units count in the funnel's absorbed parts.
- The digestion views draw the new waiting values: an orange `»` (agent) and a teal `↑` (release) next to the
  owner's blue `!` on the web page and in the `oaw-digest-monitor` mod (0.2.0), a waiting tally line in
  `oaw_status.py` and the menu, and each food's tasting and absorption notes at their stops.

- Claude Code mod `oaw-digest-monitor` (`mods/oaw-digest-monitor/`, listed in `.claude-plugin/marketplace.json`;
  optional, D19/D23): the intake pipeline as a pane beside the chat. Desktop, VS Code and mobile draw an SVG
  digestive tract (nine stops, one bolus per food coloured by verdict, owner badges, the selected food's travelled
  path, a peristalsis wave and a pulsing bolus while a taste runs, honouring reduced motion); the terminal draws
  one line per stop. The selected food shows its blocker explanation and its stop's actions, which run
  `catalog.py` preview-first (`--apply` only after 確認套用; removal needs a reason; triage only copies the
  terminal command because the confirmation code stays with the owner). A status line and toasts report a
  running, finished or stopped taste. Fourteen `claude plugin test` scenarios; `tests/test_digest_mod.py`
  keeps the mod's view schema, view sources, action handlers and read keys in step with the engine.
- Code-map Stage 0-alpha evaluation harness (`evals/code-map/`, owner decision D24): a pre-registered,
  zero-model-token question set (39 questions in four classes) on a pinned corpus of this repository,
  a simulated native-search baseline (`native_search.py`) and a scorer (`score.py`) that runs each arm
  as a subprocess. No results yet.
- Skill catalog prototype v0 (`scripts/catalog.py`, pure `scripts/catalog_core.py`):
  batch intake with duplicate merging, weekly scout with a relevance filter,
  sealed tasting in `LAB_HOME` with free static checks and component split,
  historical-prior report import, system test plans with token estimates, an
  owner-confirmed standing policy, preview-first absorb/remove, named
  `2.0.0+build.N.<hash7>` builds with restore, static effect versus the default
  recipe, and `view.json`. Paid tests are planned, not run.
- `catalog.py ui`: a local page on `127.0.0.1` (per-session token, Host check, no CORS, JSON POST
  actions in a background thread, text-only rendering) whose main screen is the animated intake
  pipeline: two inlets merge into nine stages, each food is a token on its current stage with
  one pip per component, it glides to its next stage (instant with reduced motion), and the
  current stage's actions sit under it; planned stages are drawn without buttons. The food card
  and 我的 OAW open from the token and the 版本 stage. `catalog.py menu` prints the same stage table
  as one ASCII line per food and runs each food's stage actions by letter; `oaw_status.py` prints
  the same lines from `view.json`.
- The intake pipeline stage table (`catalog_core.PIPELINE_STAGES`) and per-food stage mapping in
  `view.json` (schema `oaw-catalog-view/2`), defined once for every renderer.
- `docs/SKILL_INTAKE.md`: the official process for adding skills from now on (owner decisions
  D1-D19), with what is automated today, planned, or needs the owner, and how to operate it from
  the web page, the terminal menu and the CLI; linked from both READMEs.
- Research papers as a second kind of food in the skill catalog: `catalog.py add` accepts
  `arXiv:ID[vN]`, `arxiv.org/abs/ID[vN]` and `arxiv.org/pdf/ID[vN][.pdf]` (new- and old-style
  ids; every version of a paper is one food, the requested version is kept) and local
  `file:///…/x.pdf`. Tasting fetches the arXiv OAI-PMH `arXivRaw` record and the PDF of the
  pinned version (the latest when none is named) over https only, with a timeout and size caps;
  the PDF is only checked for `%PDF-` and hashed, then sealed with a `metadata.json` in
  `LAB_HOME` like a repository snapshot. The T0 record keeps title, authors, version, date,
  abstract length and the license rule (CC BY, CC BY-SA, CC0: quote with attribution; anything
  else: info flag `P-LIC`, ideas only). Components are not invented: the card says they need
  the Elephant (planned) or an imported digestion record. `import-report` reads paper records
  (it can add the food from the record's arXiv id), counting their units as historical-prior
  evidence, and `absorb` refuses to copy a paper (its ideas are re-implemented, D5/D21). The
  page, `menu` and `oaw_status.py` show a paper's pinned arXiv version + sha256, title, authors
  and license. Tests are offline: the arXiv calls are replaced and the 2606.03979 record is a
  fixture.
- `catalog.py ui` is now one digestive tract (D23): an SVG tube (serpentine on wide screens,
  one wavy column on phones) with a stop per stage captioned with its organ (`organ_zh` in the
  stage table), the two inlets running into the mouth, and side exits counting excreted, held
  and built components. Each food is a coloured bolus at its real stage with a blue `!` when it
  waits on the owner, a grey `?` when only optional decisions are left, a still ring when it
  waits for a planned step and a spinning ring only while a taste runs on it; selecting one
  highlights the tube it has travelled and shows its source, a progress bar, 現在, the blocker
  explanation (卡在哪 / 依據 / 你不處理會怎樣, and what the records cannot say), the current
  stage's actions, the absorb/hold/excrete split and the food card. Every earlier capability
  (both inlets, food cards, imports, builds, restore, remove, effect, policy) is kept;
  `prefers-reduced-motion` stops every animation. `food_pipeline` adds `waiting_on` and
  `blocker` to each food in `view.json`; `catalog.py menu`'s food card prints the same blocker.
- Asking about a blocker on the page: the page has no model, so a preset or typed question is
  recorded through a token-guarded `POST /api/question` (8 KB body cap, 500 characters,
  sanitized) into `.oaw/catalog/questions.jsonl` (local, at most 200 records, oldest answered
  dropped first) and offered with the food's facts to copy into a Claude conversation.
  `catalog.py questions [--all] [--answered ID ...]` lists and closes them; `oaw_status.py`
  counts the open ones.
- OAW-15 (food: claude-mem, index-then-fetch recall): `context_hub.py memory recall --index` returns
  one row per hit (`source:line` of the match, date, tag or page title, entry size, and a `match`
  window of at most max(120, query length + 40) characters that holds the complete match) under the
  same `--limit`, `--max-chars` and cursor rules; the mode is bound into the cursor hash, so a cursor
  from one mode is refused by the other. CLI only: documented in `--help` and
  `docs/CLI_Reference.md`; no skill text changed. Default recall output is unchanged and pinned by a
  byte-golden test (verified against the 790177e recall code). `--index` refuses a query with a line
  break, and a row's date and tag are cut to 40 characters like the 120-character title (EV-06). Evidence: static fixture output sizes (30 entries of about 1.5 KB: 3,350 vs
  31,079 bytes of text), not a model benchmark; no improvement is claimed.
- `oaw_common.normalize_cited_path` and `exact_case_path` (OAW-02, only the part OAW-21 needs;
  merge-derived from the graphify integration checks): cited paths are made project-relative
  POSIX paths (backslashes folded, drives, absolute paths and `..` rejected on every OS) and
  resolved segment by segment against directory listings, so a citation whose case differs
  from the file is unresolved on Windows and macOS as on Linux. `oaw_common.lf_sha256` with
  `HASH_BASIS` (CRLF folded to LF, the `evals/egm-pilot` file-digest basis) is the one hash
  for new evidence; `resolver_sha256` uses it. Not built: the LF byte count, and making an
  absolute path under the workspace root relative, so such a citation is reported as outside
  the project (goldfish CT-09).
- `wiki_sync.py lint` checks backticked `path::Symbol` code citations (OAW-21; food:
  graphify@8e6a6d2, method re-implemented with the standard library, no code copied). Only
  whole single-backtick spans with a project-root-relative path and a file extension count,
  only in raw notes and manual pages; paths resolve with exact case (OAW-02); `.py` names are
  read with `ast` (functions, classes, `Class::method` or `Class.method`, module-level names)
  with an indentation-scoped regex fallback, other files get a whole-word text check; a bad or
  unreadable cited file gives a warning, never a traceback. Warnings are grouped per note.
  After the goldfish diff review: a symlink loop is one citation's `unreadable` verdict on
  Python 3.10-3.12 too (CT-01); `ast` and the fallback both read annotation-only names,
  unpacking and chained targets, `match` case bodies and `type X = ...` aliases (CT-02, CT-03);
  the fallback skips lines inside brackets, strings and backslash continuations (CT-05); a
  UTF-8 BOM is dropped before parsing (CT-06); a dotted token counts only with a directory
  part or a known file extension, so `os.path::join` and `node.js::fs` are not citations
  (CT-04). Only fenced code is skipped (CT-12).
  Static evidence only: fixture tests; agent effect not measured.
- `wiki_sync.py cites PATH[::Symbol] [--json]` (OAW-22; food: graphify@8e6a6d2 `affected`
  reverse lookup, re-implemented as a stdlib index over the OAW-21 citation parser, no graph):
  lists the raw notes and manual pages that cite a file, a symbol or its members, with line
  and topic. Read-only and advisory; a renamed or deleted file still lists its citing notes;
  exit 0 with an empty list when nothing cites it. No skill text points to it yet (held for
  HOLD-12). Static evidence only: modify/rename/delete fixture tests.
- OAW-01 (from microsoft/TokenEconomizer, Apache-2.0): `oaw_common.resolve_cli()` returns the
  argv that starts a CLI with `shell=False`. It searches only absolute `PATH` entries, never the
  current directory. On Windows it reads an npm `.cmd`/`.ps1` shim (at most 8 KB) and starts its
  `node.exe` + script or native `.exe` inside the shim's `node_modules`, and refuses any other
  batch file, so cmd.exe never parses the arguments again. `resolver_sha256()` hashes the
  resolver block (`lf_sha256`; record `hash_basis` and the Python version beside it, since
  imports and the runtime are not hashed). Confinement to `node_modules` is lexical: it checks
  the shim's text, and a link inside `node_modules` (`npm link`, a junction) is trusted like the
  package code it holds, since a realpath check would refuse every linked package. No runner
  uses it yet; frozen eval contracts are unchanged. Wiring it into the new registrations of
  `evals/three-way/bench.py`, `evals/skill-value/experiment.py` and the next egm-pilot contract,
  with `cli_argv`, `resolver_sha256` and `hash_basis` in their manifests, is deferred to those
  registrations. Evidence: static fixtures only.
- OAW-03 (from thedotmack/claude-mem, Apache-2.0): an evaluation spec may declare an optional
  `trigger` block (`cases`, `minimum_rate`, default 2/3) outside `assertions`. Candidate case
  records then carry a boolean `triggered`; if the rate falls short on any designated case, a
  candidate that is not rejected compares as `inconclusive` with `vacuous: mechanism did not
  trigger`, and `decide` revalidation fails closed the same way. Specs without the block keep
  their verdicts. The catalog comparison rules add a no-model trigger preflight before any paid
  run. Evidence: static fixtures only.
- OAW-04 (from microsoft/TokenEconomizer, Apache-2.0): an evaluation spec may declare
  `"usage_coverage": "required"` (and `overhead_fields` for the report). Case records then carry
  `usage_coverage` and may carry `overhead_tokens`, added to that arm's tokens, and
  `grading_tokens`, reported but never counted as cost. The comparison reports each arm's
  tokens, overhead, `overhead_frac`, grading tokens and coverage; an efficiency gain counts only
  when coverage is complete in both arms (`efficiency_blocked` otherwise), while resource
  regressions use the observed lower bounds: certain (rejected) over a complete baseline, and
  `uncertain_resource_regressions` with an inconclusive verdict over an incomplete baseline,
  whose total is an undercount (goldfish MS-01). Spec-declared, so schema-1 specs and stored
  proposals keep their verdicts; no schema bump. Evidence: static fixtures only.
- `scripts/goldfish_review.py build|run|check`: the D21 zero-context Goldfish round on a code
  diff as a reusable tool, from the hand-built 2026-11-03 records kit. `build` writes one packet
  per spec group holding only that group's diff for its listed paths plus its design (shared
  files are no longer added implicitly) and refuses a group whose diff is empty. `run` keeps the
  kit's `claude -p` recipe (fresh empty temp folder, init-event checks, recorded canary, strict
  `zero_context_verified` per D20, redaction of temp/home paths in Windows, Git Bash, WSL, macOS
  `/private` and dash-encoded forms, emails and the account name) and fails closed on billing:
  an API key in the environment is refused, each result records `billing_source`, and a packet
  whose init event reports an `apiKeySource` other than `none` (or none at all) is written and
  stops the run with exit 1 unless `--allow-api-key`. New init check: no `CLAUDE.md`,
  `CLAUDE.local.md` or `AGENTS.md` above the temp folder. The review is read from the last
  `json` fence that opens a line, and a timeout is recorded instead of aborting. `check`
  summarises results and fails on a leak or a billing problem. Evidence: static fixtures with a
  fake CLI (16 tests, run on Windows 11 with Python 3.13 and WSL Ubuntu with Python 3.10); no
  model call, review quality not measured.
- `scripts/code_index.py` (D24 core candidate): a regenerable, read-only code index with `find`
  (IDF-weighted word overlap over split identifiers, paths, docstrings and comments, with the
  best symbol and line per file), `callers` (resolved through imports, aliases, `self` and local
  base classes), `path` (shortest import chain), `affected` (importers and callers, one or two
  hops) and `stats`, each with `--json` (`schema_version: 1`). Standard library only: Python via
  `ast` with a regex fallback, light name passes for Markdown, shell, JSON/TOML/YAML and
  JavaScript. Built on the fly, or cached under a directory the user names with size, mtime and
  sha256 per file so stale files are re-indexed (`--frozen` reports them). Example copies that
  `sync_examples.py` marks as generated are skipped. Evidence: static fixture tests only. No
  effect on agents has been measured, and no skill text points to it yet (a skill line is
  model-facing and waits for an A/B).

### Changed

- OAW-12 (food: claude-mem, prefixed credential patterns): default behavior change. `context_hub.py
  memory add`, `lesson` and `annotate` now refuse a note that contains a vendor-prefixed token, a PEM
  private-key header, a Slack/Discord webhook URL, a password in URL userinfo, or a key-anchored AWS
  secret access key or session token (`oaw_common.SECRET_PATTERNS`, `evidence_write_refusal`). A
  refused write exits 1, names the pattern ids without printing the value and writes nothing. No
  override flag; use a placeholder. Generic `password=`/`TOKEN=` assignments are not checked, and
  only the CLI write path is guarded. After the goldfish diff review: a URL password is exempt only
  when it is wholly a placeholder (`${DB_PASS}`, `$DB_PASS`, `{db_pass}`, `%s`, `***`), so `$ecret`
  is refused (EV-02); `openai_key` needs a `sk-proj-`/`sk-svcacct-`/`sk-admin-`/`sk-None-` kind or a
  legacy alphanumeric run with a digit, so `sk-learn-compatible-api` prose passes (EV-01);
  `aws_access_key` must stand alone, not inside a longer base64 run (EV-04); the URL scheme and
  the JWT start are bounded, so a 120,000-character note scans in linear time (EV-03). Evidence:
  positive and negative fixtures per pattern, negatives also pass the whole guard (static).
- Strict-mode change (OAW-21): an unresolved `path::Symbol` code citation is a new soft lint
  warning, so `wiki_sync.py lint --strict` now fails on it, like on every other soft warning.
  Default `lint` still exits 0 for it. Also noted in `docs/UPGRADING.md`.
- The unreleased catalog prototype is named for what it is (D19): the web command is
  `catalog.py ui` (server `catalog_ui_server.py`), the guide is `docs/SKILL_INTAKE.md`, and the
  four-step food track gives way to the nine-stage intake pipeline.

### Fixed

- Working modes after a cross-family fresh-context review of the first commit (`codex review --commit 08dbe3c`, five
  P2 findings, each reproduced): the policy and a clean-tree `suggest` now point at `--range BASE..HEAD`, since a
  clean tree alone said light for committed work; a `--root` inside a larger repository sees only its own files with
  root-relative paths (`git diff --relative`), and the default root is the project that holds the script; the
  entrypoint hint includes `--target <project>`, so it no longer installs into the OAW checkout; hook-command files
  are compared as whole project-relative paths, so a root `check.sh` no longer matches `tools/check.sh`; installer
  names such as `setupEnv.sh` and `installDeps.py` now match. Owner decision: deep always uses `--effort max`, with or
  without EGM; only the review step falls back. Evidence: regression tests in `tests/test_oaw_mode.py`.
- Working modes after a second codex review (`codex review --commit 4225749`, three findings): the entrypoint hint
  quotes the target with `shlex.quote` on POSIX, so a path with `$`, a backtick or a quote is not expanded by the
  shell, and on Windows prints forward slashes, double quotes when needed and a warning for `%`, `$` or a backtick
  (the test now formats both platforms explicitly, so it no longer expects POSIX output on Windows CI, P1); a hook
  wrapped in one `bash -c '...'` or `sh -lc "..."` shell now names its inner script, so editing that script is deep.
  Evidence: regression tests in `tests/test_oaw_mode.py`; Windows behavior checked through the explicit-platform
  test only, not on a Windows host.
- Removing EGM now removes it (D6; found by the 2026-11-06 EGM self-test). A recipe without any EGM
  skill, from `oaw.py init`/`migrate --skills` or `catalog.py remove egm --apply`, no longer writes or
  keeps the pinned runtime under `.oaw/integrations/egm/`: migrate previews its 66 files as `retire`,
  backs them up and removes them (emptied folders included), and an edited runtime file stays a
  conflict. The manifest records the EGM integration only while its runtime is installed. The installed
  `AGENTS.md` names EGM only when EGM is installed: `templates/AGENTS.md` stays the one authored
  source, with an `<!-- oaw:if egm -->` block that the installer renders per recipe (the EGM rendering
  is byte-identical to the previous policy, so EGM installs and the examples are unchanged). An unedited
  policy is replaced with backup; a customized one is never rewritten (a proposal is staged, and
  `catalog.py remove egm` asks to resolve it through `oaw.py migrate` first). `readd egm` or a restore
  point brings the same layer back. `oaw.py doctor` no longer fails a project without EGM; it still
  verifies the runtime for a selected or retained EGM entrypoint, and warns (never fails) when an
  EGM-free project still holds the runtime or the EGM policy text, as installs made before this fix
  do. Re-running `init` on such an install now asks for `migrate`, like any other retirement.
  Evidence: offline installer and catalog regression tests (`tests/test_egm_integration.py`,
  `tests/test_catalog.py`, `tests/test_skills.py`); no host discovery or model run.
- `wiki_sync.py memory-check` (prototype) after the goldfish diff review: line numbers count only
  line breaks, not U+2028 or form feeds (SL-01); calls such as `res.json()` and prose such as
  `A:B` are skipped (SL-02, SL-05); a top-level symlink or junction is never followed and bare
  names are judged by the walk only, by exact NFC name on every OS (SL-03, SL-04); a fence that
  closes later hides heading-shaped examples (SL-08); autolinks `<path>` are unwrapped and the
  placeholder characters are documented (SL-11); text output escapes every control, format and
  line-separator character, including U+061C and U+FEFF (SL-12); a memory file over 4 MB exits 1
  unread (SL-13).
- `oaw_status.py` shows a catalog headline, reports unknown verdict words as
  unknown instead of in progress, and strips control/bidi characters.
- `catalog.py restore --apply` re-evaluates the effect versus the default, so no view keeps
  showing the skills of the layer that was replaced.
- Catalog owner codes never touch disk: the CLI reads the code back on its own interactive
  terminal (no `--confirm`, no pending file, no hidden-console fallback), `ui`/`menu` keep codes
  in memory and lock after three wrong ones, and records say the confirmation is unauthenticated.
- `catalog.py restore` accepts only restore points its `LAB_HOME` indexed for the project, never
  writes paths OAW does not install (`.git/`, host settings, `.mcp.json`, project records),
  keeps custom files custom and refuses to overwrite other unmanaged files.
- `catalog.py remove` deletes only receipt paths inside one absorbed skill folder that match the
  install manifest, never adds skills to an explicit empty recipe, requires `--reason` with
  `--apply`, and names one thing (`--food` for a whole food); `readd` re-adds `egm` or a bundled
  skill through `oaw.py migrate` and keeps later changes.
- Static checks hold a SKILL.md that tells the agent to run commands (inline code spans,
  imperative commands, any flag rule) as `X1-inline`, even after triage; scanner rules version 2.
- `absorb` stages a skill in `LAB_HOME` and runs doctor's own skill lint before installing;
  backlog-only selections make no build and are no longer shown as in the current build.
- The tarball fallback caps unpacked bytes while streaming and runs only after git transport errors.
- Imported reports count list items of any type (missing lists show `—`, not 0) and use the
  ledger's canonical `after_integration` dispositions, including split parts.
- The official process follows binding D17: a static-only `X0` skill is held for a behavior A/B
  (`x0-text-ab`, amber), never shown as a green absorb; only consented live evidence naming the
  component makes it absorbable. The effect counts measured evidence only for foods in the layer.
- `absorb` ships the food's root license/notice files and an `OAW-UPSTREAM.md` attribution note
  with the copied text, and refuses a removed part until it is tasted again (D6).
- `add` and `scout pick` taste at once (`--no-taste` only registers); the scout searches by
  recency, never by stars; a pending owner code is exit 3 (D14 CLI contract).
- Stage table: 靜態, 計畫 and 版本 are mixed, the scout is owner-started (no schedule), T4 and the
  parity floor run under 實測, D18, the D3 citation list and the D14 release target are planned
  steps, and a passed stage with planned steps shows ◐ 部分完成; a removed food shows ⊖ 已移除 and
  offers a new taste. Plans tag D13 stages and compare only Stage 0/1 with the per-food cap.
- High-severity flags hold their parts until triage; rule excretes are final. The page and the
  menu use one absorb rule, show Chinese reasons, flag meanings and plan costs, call the forget
  action 忘掉這樣食物, title imported Goldfish records 零脈絡未驗證 with unrecorded launch fields,
  keep a tasting token from gliding back to 入口, show the stages on narrow screens with no food,
  and show a copyable `menu` command for owner-code steps; the menu checks for a terminal before
  asking for a triage reason.
- The web page: passed stages are neutral and only the food token takes the verdict colour; builds
  expand to their skills, components and effect lines; flags, verdict reasons, failed-taste
  reasons and one-host skills are shown; engine reasons, plans, build labels and known errors
  are in Traditional Chinese; phone layout starts at the feeding area; dark-mode contrast tokens.

## [2.0.0] — Proposed, updated 2026-10-30

V2 includes the complete current OAW toolkit and pinned EGM, with selectable native skills. Breaking upgrade prepared for independent review. No tag or release
is published by this PR. See [migration](docs/UPGRADING.md) and the
[execution plan](docs/plans/v2.0.0-execution.md).

### Added

- Historical 2026-10-29 frozen EGM evaluation fixtures and a separate three-arm Codex workflow
  experiment: three cases, three repeats, blinded independent grading and
  explicit non-regression criteria. Completed 27 real reviews: all arms detect
  24/24 defects, unsupported claims A=0/B=1/C=0. C matches native on this suite;
  standalone EGM fails the fixed gate, so the PR remains Draft. Full source
  evidence, independent grades, adjudication and invalid grading corrections
  are preserved. See [result](docs/validation/egm-codex-2026-10-29.md).
- Safe Python 3.10+ `init`, preview-first `migrate`, and read-only `doctor`.
  Manifest ownership, recognized v1 hashes, recoverable backups, conflict
  proposals and rollback protect existing project content.
- Native `oaw-evidence`, `oaw-wiki` and optional `oaw-improve` SKILL.md packages.
  V2 now includes the complete pinned EGM runtime and seven native EGM skill bridges; knowledge/improvement are additive.
- `skills` inventory and exact `--skills LIST|none|default` recipes. Disabling
  owned entrypoints previews and backs up removals; edited entrypoints remain
  protected conflicts. The EGM source remains available for reactivation.
- Nine Claude native agent adapters preserve upstream tools, inherited model and
  fresh-context policy. EGM retains upstream manual invocation on both hosts.
- Explicit `--host codex|claude|both` routes native skill folders from a single
  source; reviewed migration conflicts can remain project-owned with `--keep-custom`.
- Bounded record-oriented recall with complete JSON/text budgets, source positions,
  truncation and continuation that detects changed query/source state.
- Optional improvement proposals with concrete diffs, fixed matched-run contracts,
  regression/resource gates, evidence hashes and explicit immutable decisions.
  Acceptance records a decision; it never applies a patch.
- Focused behavioral regression tests, deterministic example regeneration and one
  local/CI entry point. CI covers Ubuntu/macOS/Windows and Python 3.10/3.13.

### Changed

- AGENTS.md is the short canonical project policy; CLAUDE.md is a compatibility import.
  The host owns execution, sessions, compaction, personal memory and permissions.
- Installer defaults no longer create memory or placeholder architecture/state files.
  Project VERSION.json, roadmap, custom policies and accumulated notes stay project-owned.
- Python 3.10+ is required. Runtime dependencies remain standard-library-only.
- Examples are generated from actual installer payloads rather than manually copied scripts.

### Removed from defaults

- Flat trigger-scanned skills, always-active self-improving rules, mandatory memory
  writes/reports, step-count skill creation, frozen evidence tiers and permanent
  do-not-rerun instructions. Customized legacy files remain recoverable/preserved.
- No mandatory Hermes nudge or hand-reported skill usage loop is introduced.

### Fixed

- Blind grading exports now require actual reviewer workflow/persona/standard
  coverage and matching content hashes. Omitted method sources cannot silently
  turn legitimate style/standard observations into unsupported factual claims.
- Pilot false-positive evolution on failed reviews, incomplete isolation
  metadata, unfrozen execution/OAW source and mutable resume identities.
  Outcome regex matches are triage-only; failed auth attempts cannot calibrate
  spend. Windows subprocess mocking no longer intercepts OS version discovery.
- Topic traversal/symlink escapes; complete locked read-modify-write with atomic commits.
- Per-page freshness checks; annotation marker collisions and rebuild growth;
  relative source-link relocation; meaningful nonzero errors.
- False-positive gates for malformed skills, stale example content and arbitrary
  expected-failure exits; installer type conflicts and write-failure rollback.
- Recall truncation retains the actual match, including escaped/long-prefix content.
- Legitimate macOS system ancestor aliases are canonicalized without allowing
  symlinks inside project-managed paths; redirected Windows gate diagnostics use UTF-8.
- CI Actions are pinned to verified Node 24 releases instead of deprecated Node 20 actions.
- Installed doctor/wiki lint no longer impose OAW's portable YAML subset on
  unrelated host/plugin skills. OAW-managed/custom packages remain checked;
  `validate_skills.py --all-packages` opts into a broader portable-subset audit.
- `oaw-evidence` now describes its actual bounded recall/write CLI instead of
  generic evidence-handling advice.
- [Versioned source ledger](docs/releases/2.0.0-sources.md) and
  [EGM review](docs/reviews/2026-10-29-pr4-egm.md): EGM manifest 0.1.0 at full
  commit `f0ba151b252c9abf1318d9fe857a43265d06de89` is now bundled in V2.
  All 65 runtime files, host manifests, personas, standards, icons and license
  retain exact upstream bytes; generated native adapters are separately marked.
  Automatic external-skill scouting/digestion remains an unimplemented plan.

### Validation limits

- Local fixtures and package/skill validation are not a model benchmark or proof of
  live native skill discovery. The 2026-10-30 Codex pilot requested Sol 6.1;
  provider revision was not exposed, and its V2 source predates this installer.
  Do not use the historical scores to certify the newly bundled runtime.
- The v1 86–87% estimate remains a historical selected-vs-all-Markdown illustration.

## [1.1.0] — 2026-04-21

This release bundles three parallel investments completed on 2026-04-20
and finalized on 2026-04-21:

1. **LLM-wiki governance layer** — a shipped LLM-wiki
   contribution pipeline + public prompts + quality lint extensions.
2. **Harness quality hardening** — `harness_check` one-command gate, skill
   frontmatter lint, and decision documents for the two research items
   from the 2026-04-20 Harness Engineering audit.
3. **Amendment v2 follow-through** — Merge Gate rule, evidence-tier
   vocabulary, deprecation protocol, and two review skills
   (`classify-evidence`, `harness-evaluator`).

Audit findings that did **not** become shippable work (recovery pattern,
task-state CLI, lane audit log, JSON CLI output) are explicitly triaged in
[`docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md`](docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md).

### Added
- **LLM-wiki governance packet** (8 artifacts):
  - `docs/wiki/CONTRIBUTING_WIKI.md` — wiki contribution guide
  - `docs/wiki/WIKI_PIPELINE.md` — staged gather → compile → verify → connect → promote pipeline
  - `docs/wiki/TOPIC_BOARD.md` — topic tracking board
  - `docs/prompts/WIKI_TOPIC_PROMPT.md` — public prompt to propose/create a wiki topic
  - `docs/prompts/WIKI_REFRESH_PROMPT.md` — public prompt to refresh
  - `docs/prompts/WIKI_SKILL_PROMOTION_PROMPT.md` — public prompt to promote a repeatable procedure to a skill
  - `.github/ISSUE_TEMPLATE/wiki_topic_proposal.yml` + `wiki_fact_correction.yml`
  - `scripts/wiki_sync.py` lint extensions: required-metadata enforcement, invalid-date detection, stale-page warnings, thin-topic warnings, hollow-prose warnings
- **`scripts/harness_check.py`** — one-command local health gate covering
  pycompile, CLI surface, install-refusal, fresh-install file set,
  fresh-install lint, repo lint, strict placeholder detection, and
  `example/minimal-project` drift. CI now calls it as a single step.
- **Skill frontmatter lint** in `wiki_sync.py lint` — skills under
  `templates/.agents/skills/*.md` must have `triggers` or `outputs` plus an
  execution-structure heading (Steps / Rules / Workflow / Procedure). Warn
  by default, `--strict` promotes to error. All 8 shipped skills pass.
- **Merge Gate rule** in `CLAUDE.md` + `templates/AGENT_RULES.md` — three
  conditions (e2e test + skill acceptance / quantified improvement /
  explicit experimental authorization) gate any infra change reaching
  `main`. "Smoke test passed" is necessary, not sufficient.
- **`classify-evidence` skill** (`templates/.agents/skills/classify-evidence.md`)
  — 30-second vocabulary gate for evidence tiers T1–T5 before writing to
  memory or wiki; prevents single-run observations from being promoted to
  "confirmed."
- **`harness-evaluator` skill** (`templates/.agents/skills/harness-evaluator.md`)
  — fresh-context subagent review against explicit acceptance criteria.
  Records `[REVIEW]` verdict to `.agents/memory.md`.
- **Deprecation protocol** in `docs/wiki/CONTRIBUTING_WIKI.md` —
  `[DEPRECATED YYYY-MM-DD]` marker + Why / Replaced by / Lesson block,
  with rules for when NOT to deprecate.
- **Evidence-tier vocabulary** in `templates/.agents/memory.md` TAG list —
  optional `[T1]`–`[T5]` tiers + `[CAVEAT: ...]` qualifier.
- **`wiki_sync.py` non-interactive subcommands**:
  - `add-experiment --name ... --status ... --result ... --conclusion ...`
    appends a row to `docs/knowledge/EXPERIMENT_LOG.md`.
  - `update-state --phase ... --status ... --note ...` updates a phase row
    in `docs/knowledge/CURRENT_STATE.md` + appends a dated AI annotation.
- **`templates/docs/knowledge/CURRENT_STATE.md`** — single compiled
  cold-start entry point template; optional but recommended over
  per-lane scatter reads.
- **First dogfood audit trail** in `docs/archive/Dogfood_Session_2026-04-21.md`
  — committed evidence that the new skills were invoked on this branch
  per Merge Gate §1.
- **Star-growth positioning pass**: clearer README first screen, comparison
  guide, and CI coverage for `example/minimal-project/` fixture drift.
- **Adapter files auto-created by installer** for Codex (`AGENTS.md`),
  Cursor (`.cursorrules`), Windsurf (`.windsurfrules`), Gemini (`GEMINI.md`).

### Changed
- `example/minimal-project/` now tracks a fresh `install.sh` run, including
  `wiki_sync.py`, `docs/raw/`, and wiki meta pages; CI enforces drift.
- Public-facing wording now uses "OAW" as the product name; older "Agent
  Memory Framework" references are kept only as history.
- New-project agent prompt in `install.sh` and README now reads "Use OAW's
  architecture as the harness, map this project's real state into
  `AI_CONTEXT.md`" instead of merely "fill in the scaffold" — explicit per
  the 2026-04-20 harness audit recommendation.
- `ROADMAP.md` Active Work table reorganized to reflect the accept/research/
  reject decisions from `Future_Optimization_Plan_Confirmed_2026-04-20.md`.

### Research decisions (no code shipped from these, but documented)
- [R-1 `Evaluator_Design_Decision_2026-04-20.md`](docs/archive/Evaluator_Design_Decision_2026-04-20.md)
  — subagent-based evaluator is empirically feasible; spec ready for Week 4
  implementation.
- [R-3 `Skill_Failure_Modes_2026-04-20.md`](docs/archive/Skill_Failure_Modes_2026-04-20.md)
  — 9 historical failures analyzed; 0 of 9 fit the Recovery/retry/rollback
  framing. No skill-template change ships; revisit in 3 months.

### Explicitly rejected or deferred
- Task-state CLI (over `VERSION.json.task_state`): `memory.md` + `ROADMAP.md`
  already cover the need; ROI too low.
- Recovery skeleton in skill template: no matching failure cases (see R-3).
- Worktree collaboration skill: maintains contingent status — rebuild only
  when ≥3 people on a branch ≥2 weeks hits a real merge pain point.
- `--json` CLI output, lane audit log: both contingent on the R-1 evaluator
  skill actually needing structured input / loaded-file provenance; defer
  until demand emerges.

## [1.0.0] — 2026-04-17

First public release. Bundles the pre-launch hardening pass into a single
tagged release.

The short-lived internal `v1.0.1` label used during pre-launch hardening was
never shipped as a public release; those changes were consolidated back into
`v1.0.0` before tagging.

### Added
- **Cross-agent/IDE compatibility table** — pointer files for Codex
  (`AGENTS.md`), Cursor (`.cursorrules`), Windsurf (`.windsurfrules`),
  Gemini (`GEMINI.md`), plus `.github/copilot-instructions.md` auto-created
  by the installer.
- **Self-hosting**: OAW repo uses its own harness to manage itself (eating
  our own dog food). Public memory policy documented in README.
- **`CONTRIBUTING.md`** — quick-start for external contributors: what's
  useful, what to skip, how to run CI locally, commit/PR style, release
  cadence rules.
- **`example/README.md`** — labels `minimal-project/` as Start Here and
  explains when to reach for `public-hybrid-demo/` instead.
- **`docs/Design_Principles.md` Naming Evolution table** — documents the
  path from "Fat Skills / Thin Harness" to "Hybrid Router" and from
  "Three-layer memory" to "Hybrid Router + Compiled Wiki" so older
  discussions stay legible.
- **`docs/knowledge/Release_Learnings.md`** — durable knowledge page
  capturing release review patterns.
- **`scripts/wiki_sync.py lint --strict`** — opt-in flag that flags
  unfilled `${...}` placeholders and literal `YYYY-MM-DD` dates as errors.
  Default lint behavior unchanged (still warn-only).
- **`.github/workflows/test.yml`** — CI smoke tests: Python syntax,
  `wiki_sync.py` CLI surface, install.sh self-install refusal, fresh-tempdir
  install file set, lint on fresh install, lint on the OAW repo itself,
  `--strict` correctly failing on a fresh install that still has
  placeholders.

### Changed
- **README (zh + en) rewrite**: agentic-first UX — intro moved above
  30-second try-it, "why you're here" merges the inventory bullets so nothing
  is said twice, Plan A and Plan B consolidated, duplicate "core principle"
  notes collapsed. Net -217 lines across both languages without losing the
  humor.
- **`install.sh`** refuses to install into the OAW framework repo itself
  (previously `$(pwd)` silently overwrote root CLAUDE.md / AI_CONTEXT.md /
  ROADMAP.md when users ran `./install.sh` from the clone). Override with
  `--force-self-install`.
- **`scripts/wiki_sync.py`** — orphan-page detection softened from error
  to warning. A repo with one curated knowledge note is a valid pattern.
- **`docs/knowledge/Release_Learnings.md`** frontmatter cleaned up
  (`page_type: topic`, stable `id`/`title`, no broken `related_topics`).
  Used to cause a spurious lint failure on the OAW repo itself.
- **`templates/VERSION.json`** refreshed for the release (previously
  `0.2.0-dev` left new users staring at a stale version after install).
- Root `AI_CONTEXT.md` + `VERSION.json` now reference `lihowfun/O-ALL-WANT`
  (was the older `agent-memory-framework` name).
- **Design Sources** ledger in README is explicit about "Borrowed" vs
  "Not Yet Implemented" — no overclaiming.

### Fixed
- Running `./install.sh` from the repo root no longer corrupts the
  framework's own root files.
- `wiki_sync.py lint` passes on the OAW repo itself (previously failed on a
  pre-existing Release_Learnings frontmatter issue).

### Verified
- Full CI matrix locally: `py_compile` on both scripts; `--help` surfaces
  build/refresh/lint; `install.sh` refuses self-install; fresh-tempdir
  install drops the expected file set; `wiki_sync.py lint` passes on both
  the OAW repo and a fresh install; `--strict` correctly fails on a fresh
  install.
- Cross-agent review: harness structure validated against a real downstream
  project.
- All scripts functional: `context_hub.py` (8 commands), `wiki_sync.py`
  (3 commands).

### Holding pattern
- Branch `v1.1-preview` carries a speculative feature set (CURRENT_STATE
  template, non-interactive `wiki_sync` subcommands, Session-End
  AI-responsibility rewrite) driven by a single integrator's feedback. It
  stays parked there until ≥1 more user confirms the pattern is useful.

## [0.2.0-dev] — 2026-04-13

### Added
- `scripts/wiki_sync.py` with `build`, `refresh`, and `lint` commands
- `docs/raw/` starter templates for raw source notes
- Compiled wiki metadata pattern (`index.md`, `log.md`, topic frontmatter)
- `docs/knowledge/Experiment_Findings.md` template
- `wiki-refresh.md` skill for refreshing compiled wiki topics
- `docs/Wiki_Sync_Guide.md` and `docs/Hybrid_Wiki_Router_Experiment.md`
- `example/public-hybrid-demo/` sanitized public demo for the hybrid router

### Changed
- Upgraded the framework from a simple three-layer memory description to a hybrid router:
  operational lane + compiled wiki lane + execution lane
- `install.sh` now installs `scripts/wiki_sync.py` and `docs/raw/`
- `context_hub.py` now skips wiki meta pages in search/status and reports raw-source counts
- `AI_CONTEXT.md`, `CLAUDE.md`, `VERSION.json`, and skill templates now describe raw→wiki workflows

## [0.1.1] — 2026-04-13

### Added
- **`install.sh`** — One-command installer with safety checks and overwrite warnings
- Cleaner README structure focusing on quick onboarding

### Changed
- **BREAKING**: Simplified Quick Start from 5-minute multi-step to <1 minute one-command
- Moved detailed concepts (File Structure, Design Principles) to separate docs
- Fixed Garry Tan credit link (X/Twitter post instead of Greptile blog)
- Condensed "Measured Results" into concise "Why This Works" table
- Streamlined FAQ answers for better readability

### Removed
- Verbose "File Structure" section from README (users see it after install anyway)
- Redundant "Core Concepts" details (moved to `docs/Design_Principles.md`)

## [0.1.0] — 2026-04-13

### Added
- Initial framework release
- Three-layer memory architecture (session → rolling → knowledge base)
- `context_hub.py` CLI with 8 commands (search, get, annotate, memory, lesson, status, bootstrap)
- 5 template skills (self-improving, benchmark, experiment-report, debug-pipeline, version-release)
- Skill template (`_TEMPLATE.md`) for creating new skills
- Template files for agent rules, AI context, VERSION.json, memory.md
- Knowledge file templates (Known_Limitations, Performance_Baselines, Architecture_Decisions)
- Copilot instructions template
- Documentation: Architecture Origins, Design Principles
- MIT License

### Design Sources — What OAW Actually Borrowed
- [Andrew Ng's Context Hub](https://github.com/andrewyng/context-hub) — **Borrowed**: knowledge file structure (`docs/knowledge/`), CLI-based context management (`context_hub.py`), search/annotate/status pattern. **OAW adds**: skills dispatch layer, wiki compilation pipeline, hybrid 4-lane routing.
- [MemPalace](https://github.com/MemPalace/mempalace) — **Borrowed**: rolling `memory.md` with append-only discipline, "read last N entries" pattern, session-end 4-part summary format. **Not yet implemented**: hierarchical compression, memory→topic consolidation, archival rotation.
- [Garry Tan "Thin Harness, Fat Skills"](https://x.com/garrytan/status/1917325461256498517) — **Borrowed**: philosophy of keeping the harness thin (`CLAUDE.md` < 120 lines) while putting executable knowledge in skill files. **OAW adds**: trigger-based dispatch, `_TEMPLATE.md` standardization.
