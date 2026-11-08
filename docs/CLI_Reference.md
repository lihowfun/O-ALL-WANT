# OAW CLI reference

Requires Python 3.10+. All runtime tools use the Python standard library. Replace `python3` with your Python executable when appropriate.

## Framework lifecycle

Run these from the OAW source checkout; `oaw.py` is not copied into target projects.

```bash
python3 scripts/oaw.py init --target PROJECT [--profile minimal|knowledge|manager-only] [--host codex|claude|both] [--with-improve] [--skills LIST|none|default] [--json]
python3 scripts/oaw.py migrate --target PROJECT [--profile minimal|knowledge|manager-only] [--host codex|claude|both] [--with-improve] [--skills LIST|none|default] [--apply] [--keep-custom PATH] [--json]
python3 scripts/oaw.py doctor --target PROJECT [--probe] [--json]
python3 scripts/oaw.py skills [--target PROJECT] [--json]
```

Init protects different existing content; edits to a managed file are kept while its framework copy is unchanged. Profile/host additions are cumulative; codex is the default host. Migrate without `--apply` only previews. Applied migration backs up known changes and stages custom conflicts under `.oaw/proposals/`; unresolved conflicts return exit 3. Use repeatable `--keep-custom PATH` with `--apply` only after reviewing a relevant conflict to retain it as project-owned. Preflight errors/init conflicts return 2. Doctor returns 1 for an unhealthy install and 2 for invalid paths/manifests; WARN checks (edited managed files, a CLAUDE.md without `@AGENTS.md`, a project `.claude/settings*.json` whose `permissions.deny` blocks the `Skill` tool) keep exit 0. Support does not imply host features are enabled: without `--probe` Claude skill discovery is UNKNOWN (NO when the Skill tool is denied). `--probe` starts Claude Code once in the project and stops it as soon as it reports its init event (tools and skills), without waiting for an answer; YES means every installed OAW Claude skill was listed and the Skill tool was present, NO names what was missing, and a probe that cannot start or sees no init stays UNKNOWN. Whether the stopped request spends any model tokens was not measured. Codex discovery is not probed.

The Bash wrapper invokes init on the current directory. Set `OAW_PYTHON` to select an explicit Python executable.

V2 includes the pinned EGM runtime. The default active recipe is seven EGM
entrypoints plus `oaw-evidence`, `oaw-review`, `oaw-codemap` and `oaw-add`. The EGM
skills stay explicit-invocation entrypoints; deep work reaches EGM through
`oaw-review` as the project's EGM switch allows (`scripts/oaw_mode.py egm`).
`--skills egm-review,oaw-evidence,oaw-wiki` selects exactly those native skills.
`none` disables all bundled skill entrypoints; `default` resets to the installed
profile's defaults. Omit the flag to preserve an explicit recipe. Selecting wiki
or improve also installs its helper. Profile/helper and host additions persist.

Use `migrate` to preview a recipe that removes entrypoints, then `--apply` to
back up and retire only owned, unchanged packages. Edited SKILL.md blocks the
whole package's removal; an edited Claude agent also remains a pending conflict.
Doctor fails until conflicts are resolved. Foreign skills and project evidence
remain project-owned. A recipe without any EGM entrypoint also retires the
pinned EGM runtime and the policy's EGM line; this is selection, not a new
product named after a combination.
`skills` lists installed files, not proven host discovery or successful activation.

## Your own skills: add, list, remove

Run these from the OAW checkout, like `init`. A SOURCE is a GitHub repository (optionally `URL@REF`, where REF
may contain slashes; no query string or fragment), a local folder, or a food name from OAW's shipped tasting results (`catalog/verdicts.json`; that installs the commit OAW
tasted).

```bash
python3 scripts/oaw.py add SOURCE [SOURCE ...] --target PROJECT [--choice oaw|only|recommended] [--consent hooks,mcp,scripts|all|none] [--on-conflict NAME=ACTION ...] [--host codex|claude|both] [--apply] [--json]
python3 scripts/oaw.py list --target PROJECT [--json]
python3 scripts/oaw.py remove NAME --target PROJECT [--dry-run] [--apply] [--force|--keep] [--json]
```

- `add` previews and writes nothing. In a terminal without `--choice` it asks one question and then installs: the
  choice (`oaw` = OAW plus these, the default; `only` = only these, OAW just keeps the receipt and can remove and
  restore; `recommended` = from OAW's tasting records), every conflict, and consent for what runs on its own.
  Elsewhere pass the answer as flags with `--apply`; a missing answer returns exit 3 with the question
  (`question`, `apply_command` and `apply_argv` in `--json`; a `--consent` you gave, even `none`, stays in them). The command repeats the preview's sources, target
  and hosts with every value quoted for the shell; on Windows a value with shell characters gets no
  `apply_command`, so use `apply_argv`.
- Adding a source that is already installed, with the same bytes, installs only its missing parts (consent given
  later, or parts held back by `recommended`); a changed source must be removed first.
- Conflicts are structural and free: a same-named skill, agent or MCP server (`rename[:NEW]`, `skip`, `replace`;
  `replace` only when no host's copy belongs to another of your additions) and
  a declared category overlap with an OAW skill, such as a second code map (`keep-both`, `use-theirs` retires OAW's
  skill until you remove theirs, `use-oaw` skips theirs). Several hooks on one event and several MCP servers are
  reported. Semantic overlap is left to the `oaw-add` skill (choice 3 or on request).
- Consent (owner decision D34): hooks merge into `.claude/settings.json`, MCP servers into `.mcp.json`, and the files
  they run go to `.claude/oaw-user/<source>/` with `${CLAUDE_PLUGIN_ROOT}` and relative paths pointed there
  (every string under `command`, `args`, `cwd` and `env`; a hook command keeps each path one quoted shell word).
  Each hook set or server carries the files its own commands name (any source file after
  `${CLAUDE_PLUGIN_ROOT}/`, whatever its extension, or a path-shaped word; a plugin-root path the source lacks
  blocks the part), the folder of each such file when it has one
  (modules and data next to it), and their local Python, JavaScript/TypeScript and shell imports; a script at the
  source root brings only its imports. Past 300 files or 10 MB the part is not installed rather than installed
  without what it needs. A file two parts need stays until the last one is removed. A skill's bundled scripts stay in its folder (`scripts`). Without consent those parts are not installed. Fetched
  code is never executed, imported or built; dependencies are listed, not installed.
- `recommended`: a tasting outcome of default installs as is, optional installs as explicit-only
  (`disable-model-invocation: true` for Claude and `agents/openai.yaml` `policy.allow_implicit_invocation: false`
  for Codex, keeping the rest of a shipped file) while its hooks and MCP servers, which would start on their own,
  are held back and listed with the `add` command that turns them on; excrete is not installed (with the condition it was tasted under), and no
  record installs it marked 未試吃. Consent is still yours.
- A local folder is read without following symlinks or Windows junctions, and version-control metadata (`.git` as a
  file or folder, `.hg`, `.svn` and the like) never comes along. A skill installs under its folder name, and its
  SKILL.md `name` is rewritten to match; one without a description is not installed. Hosts added with `--host`
  are kept in the manifest, manager-only projects included.
- Skills go to `.agents/skills/` and/or `.claude/skills/` by the project's hosts, agents and commands to
  `.claude/agents/` and `.claude/commands/`. `.oaw/user-skills.json` records, per part, every file written (with the
  earlier content's hash and a backup under `.oaw/user-skills/`) and every settings entry added.
- `remove NAME` (a whole source, every part of that name, `KIND:NAME`, or `SOURCE/KIND:NAME`; the receipt prints the
  shortest form that means exactly one part) restores those files byte for byte and removes only its entries.
  When nothing of yours is left in a settings file, its original bytes come back. A file or entry you changed since
  stays, and so do its record, backup and settings baseline, and every file a kept setting still runs: the result
  is `partial` (exit 3). An added hook equal to one the project already had is recorded with that count, so remove
  never takes the project's own copy for it; when it cannot tell them apart it reports a conflict. Put it back and run
  `remove` again, or finish with `--force` (back to before the install, over your edit) or `--keep` (your version
  stays and is no longer tracked; the files it runs become yours, so removing another part never deletes them). A built-in OAW skill is removed through migrate: preview, then `--apply`.
- A tasting result counts as the same version only when the tasted commit is established: the one snapshot sealed
  before the tasting was recorded, never the food's current pin; otherwise the receipt says the version is unknown.
- `list` and the end of `add` print the receipt: skill, source, added by, tasting result (from records only; 未試吃
  points at `catalog.py taste`), startup cost (description estimate), what runs on its own, how to remove.
- `--choice only` on an OAW project retires OAW's unchanged files with backups and keeps edited ones as yours
  (profile `manager-only`; also `migrate --profile manager-only`). `init` or `migrate --profile minimal` switches back.
- `init` records the checkout in the user's OAW settings (`checkout.json` under `$OAW_CONFIG_HOME`, else
  `~/.config/oaw/`, `~/Library/Application Support/oaw/` or `%APPDATA%\oaw\`), never in the project, so the
  explicit `oaw-add` skill can find it (skipped for a project under the system temp folder unless `OAW_CONFIG_HOME` is set). `OAW_VERDICTS` points at another verdicts file (maintainers and tests).
- Maintainers regenerate the shipped results with `python3 scripts/build_verdicts.py --ledger LEDGER --write`
  (`--check` compares); it refuses local foods and anything that looks like a private path.

## Installed Context Hub

```bash
python3 scripts/context_hub.py status [--compact]
python3 scripts/context_hub.py search QUERY [--compact] [--include-memory]
python3 scripts/context_hub.py get TOPIC
python3 scripts/context_hub.py annotate TOPIC NOTE
python3 scripts/context_hub.py memory add NOTE
python3 scripts/context_hub.py memory show [--last N]
python3 scripts/context_hub.py memory recall QUERY [--limit N] [--cursor TOKEN] [--max-chars N] [--json] [--index]
```

Recall bounds the complete rendered output and returns continuation when records or excerpts remain. Keep the same query/options for continuation. Source positions and revisions identify evidence, not verified truth. The legacy `bootstrap`, `setup`, `context --lane ...`, and `lesson` conveniences remain available through `--help`; v2 policy does not require them.

`--index` returns one short row per hit instead of an excerpt: `source:line` of the matching line, the memory entry's date, tag and title (for a knowledge page: its frontmatter title, first `# ` heading or file name), the entry's size in characters, and a `match` window from the matching line of at most max(120, query length + 40) characters that always holds the complete match. Text output prints two lines per hit; JSON rows also carry `entry_line` and `kind`, and the packet adds `"mode": "index"`. Date and tag are cut to 40 characters and the title to 120, so a row has a bounded length, and `--index` refuses a query that contains a line break. `--limit`, `--max-chars` and continuation work as in the default mode. A cursor is bound to its mode, so the other mode refuses it. Read the cited line in the source for the full entry.

`memory add`, `lesson` and `annotate` refuse a note that contains a credential: a vendor-prefixed token (GitHub, GitLab, Slack, OpenAI, Anthropic, AWS access key ID, Google, Stripe, Hugging Face, npm, Docker Hub, SendGrid, DigitalOcean, Shopify, PyPI, JWT), a PEM private-key header, a Slack or Discord webhook URL, a password in a URL's userinfo, or an AWS secret access key or session token next to its key name. The check is on by default and has no override flag. A refused write exits 1, names the matched pattern ids without printing the value, and writes nothing; use a placeholder such as `<GITHUB_PAT>` or `scheme://user:${DB_PASS}@host`. A URL password passes only when it is wholly a placeholder (`${DB_PASS}`, `$DB_PASS`, `{db_pass}`, `{{db_pass}}`, `%s`, `%(pw)s`, `***` or `<...>`); a literal `user:pass@host` is refused. An OpenAI key is recognized by its `sk-proj-`, `sk-svcacct-`, `sk-admin-` or `sk-None-` kind, or as a legacy `sk-` plus one alphanumeric run with a digit, so kebab-case names such as `sk-learn-compatible-api` pass; an AWS access key ID must stand alone, not inside a longer alphanumeric run. Generic `password=`/`TOKEN=` assignments are not checked. Only these CLI writes are guarded: a direct edit of `.agents/memory.md` bypasses the check, and a refused value is already in the command line and the host transcript. Called from Python, `memory_add` and `annotate` raise `ValueError` instead.

Topic identifiers cannot contain path separators/traversal or reserved output names. Missing topics and invalid operations return nonzero. Source and state paths are confined to the project, including symlink boundaries. Writer locks cover the complete read-modify-write transaction. Stable `.NAME.oaw.lock` sidecars are synchronization state; do not delete them while writers are running.

## Working modes

Installed with every recipe. The policy makes light the default and has the agent use the `oaw-review` skill (or run `suggest`) before starting a change and after finishing it, so the heavy EGM review runs only when the change calls for it and before any code is written.

```bash
python3 scripts/oaw_mode.py suggest [--range A..B | --paths PATH ...] [--plan FILE] [--root DIR] [--json]
python3 scripts/oaw_mode.py show light|standard|deep [--root DIR] [--json]
python3 scripts/oaw_mode.py egm [on|auto|off] [--max-tokens N] [--root DIR] [--json]
python3 scripts/oaw_mode.py egm estimate PLAN [CONTEXT ...] [--root DIR] [--json]
python3 scripts/oaw_mode.py second-opinion [same|codex|claude] [--root DIR] [--json]
python3 scripts/oaw_mode.py reviewed PLAN --how egm|fresh-context|checklist|cross-family [--report DIR] [--status done|cut] [--tokens N]
```

**Steps.** `suggest` also returns `steps` (JSON, and a `steps:` block in text): light has none; standard has one code review after the change; deep has `plan` and `design-review` marked `before_code` (finish them before writing code), then up to three code-review rounds. The design review follows the EGM switch and names its targets (the new design or plan documents in the change, or "the plan you save under docs/plans/" for a `--paths` list before the plan exists), one `reviews` entry per document with its own `report_dir` under `.oaw/reviews/` (named by path and content, since EGM writes fixed file names), and for EGM a rough estimate and `ask_first` when the high end exceeds the project's cap. A step is `done` when `reviewed` recorded a finished review of the same file content (sha256); a `--status cut` record (a usage limit, for example) never counts. `--plan FILE` names a saved plan as a design-review target whatever git says (rule `plan-given` makes the result deep), which also works in a project without git. `.oaw/settings.json` `review.dry_run: true` (tests only) reports the steps without running a review.

**EGM switch** (owner decision D33). `.oaw/settings.json` holds `review.egm`: `on` (every deep task gets the full EGM design review), `auto` (the default: the design review with the best evidence, one fresh-context review until the 2.0.1 X2 study decides, owner decision D37; the reason is printed; a finished EGM review also counts) or `off` (EGM never runs; deep gets a plan and code review). `egm` without an argument shows the switch; `--max-tokens N` sets when to ask first (default 25,000,000). `egm estimate` sizes one run from the bytes it would read, fitted to two measured Opus 5.5 runs (about 2.3 KB: 1.1M tokens, 8 minutes; about 105 KB: 18.5M tokens, 31 minutes; mostly cache reads, never below about 1M); it is rough. To run EGM once without changing the switch, type `/egm-review`. Without an EGM entrypoint in the project, deep falls back to one fresh-context review of the plan. Settings writes keep every other key, are atomic, and refuse to overwrite an unreadable file.

**Second opinion.** `second-opinion` sets who reviews code: `same` (default; a fresh session of the same model family), `codex` or `claude` (the other family, under the user's own login; setting it is the user's consent to send the diff there).

`suggest` reads the working tree (staged, unstaged and untracked files) against HEAD, a `--range`, or a plain `--paths` list (planned or changed; a path that does not exist yet counts as new, and line counts are unknown). A clean tree says light, so pass `--range BASE..HEAD` to review committed work or a pull request; the policy says so too. The project is `--root`, by default the folder that holds the script's `scripts/` folder; a root inside a larger repository sees only its own files, with paths relative to it. The rules are fixed in code; the highest mode wins and every matching reason is printed:

- **deep**: harness or infrastructure that runs on every session (`AGENTS.md` or `CLAUDE.md` anywhere, `templates/`, `.github/workflows/`, `.claude/settings*.json`, `.claude/hooks/`, `.codex/`, `.githooks/`, `.husky/`, `.pre-commit-config.yaml`, installers named `install*`, `setup*` or `bootstrap*` with a `.sh`, `.ps1`, `.bat`, `.cmd` or `.py` extension, such as `setup_env.sh` or `installDeps.py`, OAW's own helpers and harness scripts in `scripts/`, and any file a Claude Code hook command in `.claude/settings*.json` names, compared as a whole project-relative path after `$CLAUDE_PROJECT_DIR/`, the project's absolute path or `./` is removed, and including the inner command of one `bash`/`sh`/`zsh`/`dash`/`ksh` `-c` wrapper such as `bash -c '...'` or `sh -lc "..."`); more than 5 deleted files; anything under a `migrations/` or `migration/` folder or `alembic/versions/`, and schema files (`schema.*`, `*.schema.json`, `*.prisma`); a new design document (an added `docs/designs/*.md` or `design*.md`, rule `new-design-doc`, checked against outcomes in V7); a new plan or decision document (an added `.md` under `docs/plans/`, `docs/adr/`, `docs/adrs/`, `docs/rfc/` or `docs/rfcs/`, or named `plan.md`, `*-plan.md` or `*_plan.md`; rule `new-plan-doc`, added in 2.0.1 and marked `since`, not yet checked against outcomes). A rename is checked under its old and new path and is not a deletion.
- **standard**: none of the above, and a code change of 300 or more lines (added plus deleted) or 10 or more files. Documentation (`docs/`, `.md`, `.markdown`, `.rst`, `.txt`, `.adoc`) never counts toward size; binary files count as files only.
- **light**: everything else, including docs-only and small changes.

`show` prints the host commands for a mode (flags checked with Claude Code 2.1.287 and codex-cli 0.167.0): light is a plain `claude` or `codex` session; standard is `claude --effort high` plus one new subagent with no conversation context that reviews the diff and the tests, or for Codex `codex review --uncommitted` (Codex has no mapped effort flag yet); deep is `claude --permission-mode plan --effort max`, then the EGM design review that the agent runs through the `oaw-review` skill when the switch allows it (the user can still type `/egm-review` for one run), or with the switch `off` the code review only; every deep listing ends with the code review of the chosen family and "review again until a round finds nothing new (at most 3 rounds)"; or for Codex a `codex --sandbox read-only` planning pass and the `egm-review` skill from the skill picker (Codex plan-mode and effort flags are not mapped yet). Deep always plans at the highest effort; it names EGM only for a host whose `egm-review/SKILL.md` is installed in the project (`.claude/skills/` or `.agents/skills/`). Without it, only the review step falls back to the one fresh-context review, and when only the other host has EGM, `show` prints the `oaw.py init --target <project> --host ...` command that adds the entrypoint from the OAW checkout, with the path quoted by `shlex.quote` on POSIX; on Windows it uses forward slashes and double quotes when needed and warns when the path holds `%`, `$` or a backtick that a Windows shell may expand. Exit codes: 0 done, 2 a usage, path or git error. `oaw.py doctor` requires the helper once the install owns it or `AGENTS.md` names it; an install made before working modes gets a WARN and `migrate --apply` adds the helper and the policy lines. The rules route review effort; they do not measure review quality, and no behavior A/B has measured the policy line.

## Knowledge profile

```bash
python3 scripts/wiki_sync.py refresh TOPIC
python3 scripts/wiki_sync.py build
python3 scripts/wiki_sync.py lint [--strict]
python3 scripts/wiki_sync.py stale [--threshold DAYS]
python3 scripts/wiki_sync.py cross-check
python3 scripts/wiki_sync.py memory-check [--json] [--limit N]
python3 scripts/wiki_sync.py cites PATH[::Symbol] [--json]
```

`lint` also warns about backticked `path::Symbol` code citations in raw notes and manual pages that do not resolve (path missing or differing in case, symbol not defined, or outside the project), one line per note; `--strict` makes them errors like every other warning. See [code citations](Wiki_Sync_Guide.md#code-citations).

`cites` is the reverse lookup: it lists the raw notes and manual pages whose `path::Symbol` citations name PATH, or PATH::Symbol and its members, with line and topic. It is read-only and advisory and exits 0 with an empty list when nothing cites the target; an absolute, drive or `..` target exits 1. It reads notes with the same loader as `lint`, so a raw note with an invalid `topic_id` or a non-scalar `last_updated` makes it exit 1 with lint's error until the note is fixed. `--json` returns `schema_version: 1` with `target` and `results` (`source`, `line`, `citation`, `topic_id`).

`memory-check` is a manual, read-only report of `.agents/memory.md` entries whose cited project paths are missing. It exits 0 whenever the check completes (advisory, also when the file is absent), 1 on a handled error such as non-UTF-8 input or a memory file over 4 MB, and 2 on a usage error. `--limit` (1–500, default 50) truncates findings, never counts. See [memory citation check](Wiki_Sync_Guide.md#memory-citation-check-prototype).

Raw source notes are rendered deterministically into topic pages. Manual pages are not overwritten. Generated source content and annotations use separate boundaries. Local Markdown links are relocated to the output directory. Metadata freshness checks run per page. Unchanged source inputs produce stable generated content.

Existing experiment/state convenience commands remain in `--help` for older projects; they are not required state mirrors. Native skills use name/description and do not require custom triggers or heading conventions. The validator deliberately supports a documented subset of YAML, not every native extension field. Installed doctor/wiki lint check OAW's declared packages, including project-owned custom versions of those packages; unrelated host/plugin skills need their own host/upstream validation. This is not a certification of external packages.

## Optional improvement workflow

```bash
python3 scripts/improvement.py --base-dir PROJECT propose --title TITLE --hypothesis TEXT --target PATH --patch DIFF --evaluation SPEC.json --snapshot BASE_REV
python3 scripts/improvement.py --base-dir PROJECT compare ID --baseline BASELINE.json --candidate CANDIDATE.json
python3 scripts/improvement.py --base-dir PROJECT decide ID --decision accept|reject --reason TEXT
```

Paths are project-relative. A proposal stores its concrete git text diff and fixed evaluation contract. Comparison returns eligible (exit 0), rejected (1) or inconclusive (3); malformed/mismatched inputs return 2. Eligible means ready for explicit review, not automatic approval, deployment, statistical proof, or patch application. See [SELF_IMPROVEMENT](SELF_IMPROVEMENT.md).

An evaluation spec may declare an optional `trigger` block (cases plus `minimum_rate`, default 2/3; a written `0.667` compares exactly and needs 3 of 3); candidate case records then need a boolean `triggered`, and a candidate whose mechanism fired below the rate on any designated case compares as inconclusive (`vacuous: mechanism did not trigger`). Only the `improvement.py` from the unreleased OAW-03 change (after the 2.0.0 proposal) enforces it; older copies ignore the block silently.

A spec may also declare `"usage_coverage": "required"` (optional `overhead_fields`). Case records then need `usage_coverage` (`complete`/`incomplete`) and may carry `overhead_tokens` (added to the arm's tokens) and `grading_tokens` (reported, never cost); an efficiency gain counts only when coverage is complete in both arms. A resource regression over an incomplete baseline is not certain: it is listed under `uncertain_resource_regressions` and the comparison is inconclusive. Enforced from the unreleased OAW-04 change; older copies ignore it silently.

## Skill catalog (prototype v0)

Run from the OAW source checkout, like `oaw.py`. Every command accepts `--target PROJECT` and `--json`. The official process for adding skills, and how to operate it (Traditional Chinese): [SKILL_INTAKE](SKILL_INTAKE.md).

```bash
python3 scripts/catalog.py add URL [URL ...] [--ref REF] [--no-taste]   # GitHub repositories or arXiv papers
python3 scripts/catalog.py list
python3 scripts/catalog.py show FOOD
python3 scripts/catalog.py why [FOOD]
python3 scripts/catalog.py taste FOOD [--ref REF]
python3 scripts/catalog.py triage FOOD FLAG --benign|--allergen|--confirm-toxic --reason TEXT
python3 scripts/catalog.py import-report FOOD DIR                      # FOOD may be empty: taken from DIR
python3 scripts/catalog.py record-tasting --food FOOD --file TASTING.json [--apply]        # D25, D28
python3 scripts/catalog.py record-absorption --food FOOD --file ABSORPTION.json [--apply]  # D21, D28
python3 scripts/catalog.py plan FOOD
python3 scripts/catalog.py policy show
python3 scripts/catalog.py policy set --per-food-tokens N --weekly-tokens N --sandbox isolated-venv,project-copy,no-api-keys
python3 scripts/catalog.py absorb FOOD --components ID[,ID ...] [--reason TEXT] [--apply]
python3 scripts/catalog.py remove SKILL|egm [--reason TEXT] [--apply]
python3 scripts/catalog.py remove FOOD --food [--reason TEXT] [--apply]
python3 scripts/catalog.py readd SKILL|egm [--reason TEXT] [--apply]
python3 scripts/catalog.py forget FOOD [--reason TEXT] [--apply]
python3 scripts/catalog.py builds
python3 scripts/catalog.py restore BUILD [--apply]
python3 scripts/catalog.py effect
python3 scripts/catalog.py view
python3 scripts/catalog.py scout [list | pick N [N ...] [--no-taste]]
python3 scripts/catalog.py ui [--no-browser] [--port N]
python3 scripts/catalog.py menu
python3 scripts/catalog.py questions [--all] [--answered ID [ID ...]]
python3 scripts/oaw_status.py [--project PROJECT] [--json]
```

`add` merges duplicate repositories (case, `.git`, trailing slash, SSH and tree URLs). Naming a repository with `add`, or picking a scout candidate with `scout pick`, is the owner's confirmation (D4): each new food is tasted at once (free T0), and `--no-taste` only registers it; a batch in which a taste fails exits 2. `scout` searches GitHub for repositories pushed in the last 7 days, newest first (up to 3 pages of 100 per query; the rest is counted as not fetched), drops unrelated ones without review, and uses stars only to order the candidates. It has no schedule: run it once a week, since a skipped week is not searched again. `taste` pins a snapshot with a hardened git fetch (no hooks, no checkout, https or local file URLs only) and seals it as a read-only tar in `LAB_HOME`, outside the project: `%LOCALAPPDATA%\oaw\lab`, `~/Library/Application Support/oaw/lab` or `$XDG_DATA_HOME/oaw/lab`, overridable with `OAW_LAB_HOME`. Without git it falls back to a codeload tarball marked `unverified-against-commit`. Size never refuses a food: the archive caps (5 MB per file, 200 MB and 20,000 files in all) only bound what is stored and scanned; past them the largest files are skipped first and each one is flagged `F-PARTIAL` (not stored, not scanned), and the food goes on to be tasted. Only the tarball fallback refuses a download over 400 MB. The free T0 checks read the tar in memory; nothing is extracted, executed or imported. Static rules only raise flags: a high-severity flag makes the food `risky`, and only an owner `triage --confirm-toxic` makes it `toxic`. Each food is split into components (skills, hook sets, MCP servers, scripts, manifests, instruction files, docs) proposed as absorb, excrete or hold; executable or flagged parts never default to absorb, a part with an untriaged high-severity flag is held until triage, and rule excretes (package manifests, a second instruction file, binaries) are final. Model-facing skill text is held behind a behavior A/B (D17): a skill becomes absorbable only with consented live evidence (a gain with a parity floor) that names that component, so v0, which has no A/B runner, absorbs no food skill.

`why` answers the owner's questions in plain Chinese, read-only: without a food, one line per food (what was decided, who it waits on, the one-line reason); with a food, the latest tasting's verdict and reason, whether the food's own arm was installed and run (graded runs and their evidence), the frozen questions, models and per-arm numbers, the records branch path and commit, earlier tastings, absorbed units and the static summary. `--json` carries the same text as `answer_zh`.

A paper is the second kind of food. `add` accepts `arXiv:ID[vN]`, `https://arxiv.org/abs/ID[vN]`, `https://arxiv.org/pdf/ID[vN][.pdf]` (with or without the scheme) for new-style (`2606.03979`) and old-style (`hep-th/9901001`) ids, and a local `file:///…/x.pdf`; the key has no version, so every version of one paper is one food, and the requested version is kept as the ref (`--ref v2` on `add` or `taste` names it too). `taste` fetches the arXiv OAI-PMH record (`oaipmh.arxiv.org/oai`, `arXivRaw`: title, authors, abstract, license URL, versions) and the PDF of the requested version, or of the latest one when none is named, over https only (redirects included), with a 60-second timeout and size caps (2 MB metadata, 200 MB PDF). The PDF must start with `%PDF-`; it is hashed, never parsed, rendered or executed. The PDF and a deterministic `metadata.json` (with the sha256 of each) are sealed like a repository snapshot, as a read-only tar in `LAB_HOME` pinned to the arXiv version plus the content hash, with integrity `sha256-recorded` (arXiv publishes no hash to verify against); a local PDF is sealed the same way with metadata from the file only. The paper's T0 record keeps title, authors, version and date, abstract length (the abstract itself stays in `LAB_HOME`) and the license rule: CC BY, CC BY-SA and CC0 allow quoting with attribution; anything else, including arXiv's non-exclusive distribution license or an unknown one, adds the info flag `P-LIC` (ideas only: re-implement, do not copy text), which never waits for triage or holds anything. No hook, MCP or script check applies. Without a model v0 does not split a paper into components and invents none: the card and the plan say that component extraction needs the Elephant (planned) or an imported digestion record. `absorb` refuses any part of a paper other than its imported historical proposals (those become backlog decisions only): a paper's ideas are absorbed by re-implementing them in OAW code with tests (D5, D21), never by copying its text.

Verdicts come from `catalog_core.derive()`, which reads evidence and owner decisions only; stars, authors and requests are not inputs. `import-report` stores an Elephant/Goldfish digestion directory as `historical-prior` evidence that is shown separately and never counted. It also reads a paper's digestion record (`components.json` with `food_kind: paper` and units named by `what`, `goldfish-*.json`, `skeptic.json`, and `digest.md`, `elephant-draft.md`, `elephant-final.md`, `extract.md`, which are hashed and their headings listed); with an empty FOOD it adds the food from `scout.json`'s `repo` or, for a paper, from the record's arXiv id pinned to the version it digested, without fetching anything. `plan` is the system's test plan, cheapest first, with token estimates (about 0.6-0.9M logical tokens per tool-using agent run); each step names its D13 stage (0 free, 1 screening, 2 always asks the owner, or digestion overhead) and sandbox level, and only Stage 0/1 is compared with the per-food cap. v0 never runs paid tests, and `policy set` does not yet encode PRE-01: it stores a per-food cap, a weekly cap and free sandbox conditions, with no per-round overhead cap or sandbox levels. `policy set` and `triage --benign|--allergen` need an interactive terminal (stdin and stderr are TTYs): they print a one-time code there and read it back in the same process; without one they refuse, and no code is written anywhere. `ui` and `menu` keep their codes in memory, show them on their own terminal, and stop accepting codes after three wrong ones. The code is a speed bump against an agent acting through the CLI, not authentication: `policy.json` and `decisions.jsonl` are unauthenticated project files that anything with write access can edit, so records say `confirmed_via: code typed back on an interactive terminal (unauthenticated)`. A SKILL.md (or a text file the skill ships) that asks the agent to run a command, in a fence, an inline code span or a "run `…`" instruction, or that matches any flag rule, is `X1-inline` and held for a sandbox trial even after its flags are triaged; records from older scan rules must be tasted again before anything is absorbed.

### Agent tastings and D21 absorptions (D28)

Claude tastes a food in the tasting area (D25: official install, every arm run, blind grading, pre-registered rules; the results are committed on the `records` branch) and, under D21, rebuilds the picked units as OAW code with tests on the working branch. `record-tasting` and `record-absorption` put those results in the ledger so `view.json` shows them. Both preview without `--apply` (the preview prints the stage and who the food will wait on), refuse a record the engine does not accept with exit 2 and write nothing, store an accepted record as `.oaw/catalog/evidence/<food>/tasting-<id>.json` or `absorption-<id>.json` (the id is a hash of the normalized record, so the same file twice is `already-recorded`), and refresh `view.json`. Records are evidence of their own kind: `derive()` never counts them, so the static headline and the copy-absorb holds (flags, D17) do not change. The engine checks every stored record again whenever it builds a view; an edited file (its content no longer hashes to its id) or a verdict the rules refuse is listed on the card under `records_refused` and ignored. `forget` drops them with the rest of the food's evidence; the results stay on the records branch they point to.

A tasting file (schema `oaw-tasting/1`; unknown fields are refused):

| Field | Meaning |
|---|---|
| `schema` | `"oaw-tasting/1"` |
| `food` | optional; must be the `--food` id when given |
| `date` | `YYYY-MM-DD` of the tasting |
| `records` | `{branch` (default `records`), `path` (relative), `commit` (7-40 hex)`}`: where the frozen questions, answers and grades are |
| `protocol` | `{models: [...], corpus, questions: {count, sha256 (64 hex, the frozen questions), file?}, repeats, grading?, host?}` |
| `arms` | `[{id, label?, food_arm: true/false, runs, graded_runs, results?: {coverage (0-1), essential_correct, essential_total, wrong_claims, token_median, tokens_total}}]`; exactly one arm is the food arm (for a paper: the arm that carries its rebuilt idea) |
| `food_arm_ran` | `{graded_runs, evidence?}`; must equal the food arm's `graded_runs` |
| `verdict` | `absorb`, `plug-in`, `optional`, `decline` or `no-verdict`; `not-shown-better` is kept for records made before D29 |
| `verdict_zh` | the verdict in a sentence |
| `blocked_on_owner` | optional: what only the owner can do (allowed with `absorb`, `plug-in`, `optional`, `no-verdict`) |
| `judgment` | D29: `{quality: better/same/worse, cost_ratio (food tokens over native), cheaper (the PREREG's cheaper rule), grading: double-graded/mechanical/single-graded, conditions?, basis?}`; required for `optional`, and when given the verdict must match it |
| `notes` | optional |

D29 rule (2026-11-06), enforced when recording: the judgment fixes the outcome. Quality better and cost at most 1.5x native, or quality same and cheaper by the PREREG rule -> default (`absorb` or `plug-in`); quality same and cost at most 1.5x, or better but over 1.5x -> `optional` (available, not default, called explicitly); worse, or same and over 1.5x -> `decline`. With several model conditions the lowest decides. An AI-graded difference counts only if it held in two gradings, so a `single-graded` judgment can only say `same`. `optional` rests at 分流 with nothing pending, or waits on the owner at 核准 when `blocked_on_owner` names a tier-C decision.

D28 rule, enforced when recording and when building the view: any verdict other than `no-verdict` is refused unless the food arm has at least one graded run ("no verdict without the food arm installed and run"); a `no-verdict` must say what blocks it (`blocked_on_owner` or `notes`). Several tastings of one food accumulate: all are listed on the card (`tastings`), and the latest (by `date`, then the time it was recorded) decides (`tasting`). Example (the ERPNext graphify tasting):

```json
{"schema": "oaw-tasting/1", "food": "graphify", "date": "2026-11-05",
 "records": {"branch": "records", "path": "records/digestion-2026-11-03/taste-graphify/erpnext", "commit": "93e555b"},
 "protocol": {"models": ["claude-opus-5-5"], "corpus": "ERPNext at a pinned commit", "repeats": 1,
              "questions": {"count": 4, "sha256": "b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83"},
              "grading": "blind zero-context grader"},
 "arms": [{"id": "N", "label": "native", "food_arm": false, "runs": 4, "graded_runs": 4,
           "results": {"coverage": 0.933, "essential_correct": 4, "wrong_claims": 2, "token_median": 69438}},
          {"id": "G", "label": "graphify 0.9.102", "food_arm": true, "runs": 4, "graded_runs": 4,
           "results": {"coverage": 0.933, "essential_correct": 4, "wrong_claims": 1, "token_median": 95592}}],
 "food_arm_ran": {"graded_runs": 4, "evidence": "out/grades.jsonl"},
 "verdict": "not-shown-better", "verdict_zh": "覆蓋率相同，每題 token 中位數多 38%：沒證明比原生好"}
```

An absorption file (schema `oaw-absorption/1`) records units already rebuilt on a branch, and the units declined or held; it never needs a food arm (a paper has none):

| Field | Meaning |
|---|---|
| `schema`, `food`, `date` | as above |
| `branch` | the branch that holds the commits, e.g. `claude/oaw-2` |
| `absorbed` | `[{id, name?, tier: A/B/C, commits: [7-40 hex], tests: [names], evidence: {basis, tasting?}, owner_approval?}]` |
| `declined`, `held` | `[{id, name?, reason}]` |
| `release` | `{state: pending/released, pr?, ref?}`, default `pending` |
| `blocked_on_owner`, `records` (`{path, commit, branch?}`), `notes` | optional |

D21 tiers are enforced: tier A (mechanism only) rests on its `evidence.basis` (static evidence is enough, D17); tier B (model-facing text) needs `evidence.tasting` naming a recorded tasting of the same food whose verdict is `absorb`; tier C needs `owner_approval` (record a pending tier-C question as a held unit with `blocked_on_owner` instead). Unit ids may be written as in the digestion record (`sl.wake-sleep-cycle/manual-pass`); they settle the matching imported proposal (`hist:sl.wake-sleep-cycle-manual-pass`). Several absorption records of a food are merged by unit, a later record winning for the same unit.

Who a food waits on (`pipeline.waiting_on`, D28): `owner` (blue `!`) only for an entry choice (a never-tasted food), a tier-C question, an owner-only prerequisite (`blocked_on_owner`) or removing a skill that is in the build with a bad verdict; `agent` (「自動（Claude 接手）」) for every next step Claude takes: tasting a food (including one with high-severity flags, which stays at 靜態 with triage as an optional terminal action), re-tasting after a rule change or a failed taste, re-running a `no-verdict` tasting, splitting a paper into units, rebuilding units after an `absorb` verdict or a consented A/B (copy-absorbing stays an optional owner action), plugging in after `plug-in`; `release` (「等發布（合併 PR 時一次決定）」) for a food whose absorbed units wait on the working branch for the owner's one release (merging the PR), counted once for the branch in `view.json`'s `release_pending`; `optional` when only optional owner decisions are left (imported historical proposals included); `none` at rest (decline, not shown better, nothing absorbable, released). A recorded tasting marks 實測 done (blocked for `no-verdict`) and its verdict shows at 分流 (`pipeline.stage_notes_zh`); `absorb` and `plug-in` move the food to 核准, `decline` and `not-shown-better` rest at 分流; a recorded absorption with absorbed units puts the food at 版本. The funnel counts `absorbed_parts` as installed parts plus rebuilt units (`installed_parts`, `rebuilt_units`), and `agent_tasted` foods.

`absorb`, `remove`, `readd`, `restore` and `forget` only preview without `--apply`; `remove` and `readd` need `--reason` with `--apply`. Applying first snapshots the OAW-managed layer (install manifest, managed files OAW can produce from its templates or allowlisted absorbed skill text, the EGM runtime, absorb receipts) into `LAB_HOME`, indexes it there, evaluates it against the default, then names the result `2.0.0+build.N.<hash7>`. Only text-only skills proposed for absorption are installed, and only after the same skill lint doctor runs passes on a staged copy in `LAB_HOME`; the text is copied unchanged (not re-implemented yet) together with the food's root `LICENSE`/`NOTICE`/`COPYING` files and an `OAW-UPSTREAM.md` note (source, pinned commit, tree hash, files, license, "Modifications: none"). A removed part is not absorbed again from its old taste: it needs a taste recorded after the removal (D6); a selection of historical proposals only is recorded as backlog decisions, changes no file and makes no build. A `remove` name means one thing: `egm`, a bundled skill, or one absorbed skill; `--food` removes every installed part of a food. Receipt paths are deleted only when they sit in one absorbed skill folder and match the install manifest's hashes. Bundled skills and `egm` are removed and re-added through `oaw.py migrate` (backup first); a removal never adds and a re-add never retires. `restore` accepts only restore points this `LAB_HOME` created for this project (the location is derived, not read from `builds.json`), refuses any snapshot path outside the layer (never `.git/`, host settings, `.mcp.json` or project records), keeps declared custom files custom, refuses to overwrite any other file the current install does not manage, then runs doctor. `effect` compares the install with a fresh default recipe: every line is `static-measured`, and quality stays `not measured` without consented live evidence for a food whose parts the layer holds. `view` writes `.oaw/catalog/view.json` for every renderer; `status.json` keeps schema 1. A generated `.oaw/catalog/.gitignore` keeps only `builds.json` and `absorbed/*.json` committable. Exit codes follow the D14 CLI contract: 0 done, 2 refused or failed, 3 a choice is needed (the page or menu waits for the owner's code).

`ui` serves the intake pipeline page (`scripts/catalog_ui/`) on `127.0.0.1` at a free port and opens the browser with a per-session token in the URL fragment. Every `/api/` call needs that token in the `X-OAW-Token` header and a `Host` naming the bound address; no CORS headers are sent, actions are JSON `POST`s only, and cross-site `Origin`/`Sec-Fetch-Site` requests are refused. One action runs at a time in a background thread; the page polls its progress and `view.json`. JSON responses escape `<`, `>` and `&`, the page sets text with `textContent` only, a Content-Security-Policy allows only its own files, and food-supplied HTML, SVG or images are never rendered. Confirmation codes are printed on the terminal that runs `ui`, never in an API response. The main screen is the official intake process of [SKILL_INTAKE](SKILL_INTAKE.md) drawn as one digestive tract (D23): an SVG tube, serpentine on wide screens and one wavy column below 620 px, with a stop for each of the nine stages of `catalog_core.PIPELINE_STAGES` (入口, 封存, 靜態, 計畫, 盲審, 實測, 分流, 核准, 版本), each captioned with its organ (`organ_zh`: 口, 食道, 胃, 十二指腸, 肝, 小腸, 大腸, 門靜脈, 全身) and whether it is automated, done by Claude (agent), owner, mixed or planned. The two inlets (weekly scout → relevance filter → owner confirms, and owner-named repositories or arXiv papers) run into the mouth; side exits at 分流 count the excreted and held components, and one at 版本 the components in the current build. Each food is a coloured bolus at its real stage; several foods at one stop line up along the tube. A bolus carries a blue `!` when the food waits on the owner, an orange `»` when Claude takes the next step (D28), a teal `↑` when it waits for the release (one decision for the whole branch), a grey `?` when only optional decisions are left, a still dotted ring when it waits for a planned step, and a spinning ring only while a taste is running on it (`status.json`); these come from each food's `pipeline.waiting_on`. When its stage changes between refreshes a bolus glides along the tube; the peristalsis wave, rings, bob and glide stop under `prefers-reduced-motion`. Selecting a bolus (click, or Enter on a focused one) highlights the part of the tube the food has travelled and shows, below, its source (repository commit, or arXiv version plus PDF sha256), a nine-segment progress bar, 現在 (stage · who · note), the blocker explanation from `pipeline.blocker` (卡在哪 / 依據 / 你不處理會怎樣, and 紀錄沒寫的 where the records cannot say), the current stage's real actions (the same engine actions as the CLI; owner-code steps are shown as a copyable `menu` command, planned stages carry no button), the absorb/hold/excrete split, and the food card (components with reasons and evidence levels, flags, the system plan, 🐘/🐟 records labelled 歷史證據). The page has no model: 「看不懂？問這個卡點」 records a preset or typed question with `POST /api/question` (same token, Host and origin checks, an 8 KB body cap, at most 500 characters, sanitized like every other input) into `.oaw/catalog/questions.jsonl` in the project (local only, like the rest of the catalog state; at most 200 records, the oldest answered ones dropped first) and offers the question with the food's facts to copy into a Claude conversation. `catalog.py questions` lists the open ones (`--all` includes answered ones) and `--answered ID` marks them answered; `oaw_status.py` counts the open ones. 我的 OAW (current build, skills with remove and re-add, effect versus the default with an evidence level per line, the build timeline with 還原到這版, standing policy) sits below. `menu` prints the same stage table as one ASCII line per food (`● done ◐ partly done ◉ current ⊗ blocked ⊖ removed ○ not reached ┄ planned – not needed`; a passed stage with planned steps is partly done), lists every food's current-stage actions by letter and keeps the numbered screens, without curses, for Codex or terminals without a browser. `oaw_status.py` prints the same pipeline lines when `.oaw/catalog/view.json` exists, with the same display rules: quality is 未量測 without measured evidence, stars appear only as queue order, and unknown verdict words or stage states show as unknown. `view.json` uses schema `oaw-catalog-view/3`: it carries the stage table under `pipeline` (with `waiting_zh`, `tasting_verdicts_zh` and `tiers_zh`), each food's `pipeline` (stage, per-stage states, note, actions, parity label, `waiting_on`, `blocker`, `stage_notes_zh`), each food's `tastings`, `tasting`, `absorption` and `records_refused`, and `release_pending`.

## Tasting statistics (D32)

```bash
python3 scripts/eval_stats.py compare FOOD.json NATIVE.json --margin M [--lower-is-better] [--floor-sd SD]
python3 scripts/eval_stats.py cost FOOD.json NATIVE.json [--cap 1.5]
```

Framework tooling, not installed into projects. Each file maps a question id to its per-run values. `compare` prints the question-paired difference with a bootstrap over questions (10,000 draws, seed 20261107), the 95% and 90% intervals, the standard error (never below `--floor-sd` x sqrt(2 / questions)), the MDE and one of better, equivalent, undetermined or worse. `cost` prints the token ratio, its 95% interval and cheaper, within, undetermined or over (over only when the lower end exceeds the cap). The module's `quality()`, `agree()`, `lowest()` and `judgment()` combine metrics, the two grader families and conditions into the catalog's judgment fields. The rules are on one page: [EVAL_PROTOCOL.md](EVAL_PROTOCOL.md). Exit codes: 0 done, 2 unreadable input.

### Offline judge calibration (I18)

```bash
python3 scripts/judge_calibration.py GOLD.json GRADES.jsonl [GRADES.jsonl ...] [--json]
```

This framework tool scores judge labels offline with zero model calls; it does not install or approve a judge. A separate script keeps label validation apart from `eval_stats.py`'s experimental statistics, without duplicating them. Neither tool is installed into projects.

Gold uses V3 `expected.json`: `arm|question|positive-rep` maps to `labels` (fact ID → `present`, `absent`, or `contradicted`; `null` means unlabeled). Variants share a question's fact IDs. Optional `wrong`/`wrong_at_least` sets an exact count/lower bound; `wrong_over_e` on f sets the injected increase over matching e. Optional `critical: [fact-id, ...]` marks known cells; without marked cells, critical misses are unavailable (`null`).

Candidate JSONL rows require `key` and `verdict: {"facts": {"fact-id": "label"}, "wrong_claims": 0}`. Every answer/fact ID is required, including e/f. Explicit `unknown` means abstention; other unknown values are invalid. Optional `verdict._grader_tokens` must be positive; missing costs remain unavailable/partial. Optional `status` must be `completed` or `ok`. Errors, incomplete statuses, zero tokens, duplicate IDs/JSON fields, missing/extra IDs and malformed schemas reject the whole candidate without metrics. Archived identity/derived fields are accepted but never trusted as scores. Missing execution metadata cannot prove completion; schema validation cannot verify execution.

Reports include gold-row/prediction-column confusion, abstention/coverage, covered accuracy, false credit (`present` against non-present gold), critical errors/abstentions separately, wrong-claim checks, signed f−e deltas and recorded tokens. Archived accuracy is rounded to three decimals: exact matches/all known cells; abstentions reduce it but are separate from label errors. Full injection detection uses the gold threshold; partial means delta ≥1. e/f consistency averages per-pair fact agreement, not gold accuracy. V3 has four questions, 24 answers and 116 known cells; e/f lack gold labels. Exit 0: scored; 2: rejected input (other valid candidates still receive reports).

## Goldfish code review (D21)

Run from the OAW source checkout. It packages the one zero-context Goldfish round on a code diff that D21 intake uses (the D15 recipe); the Elephant still resolves the findings.

```bash
python3 scripts/goldfish_review.py build --spec SPEC.json --repo OAW_CHECKOUT --out PACKETS
python3 scripts/goldfish_review.py run --packets PACKETS --results RESULTS [--only NAME ...] [--claude PATH] [--timeout SECONDS] [--dry-run] [--allow-api-key]
python3 scripts/goldfish_review.py check --results RESULTS
```

`SPEC.json` is `{"groups": [{"name": ..., "id_prefix": ..., "base": ..., "head": ..., "paths": [...], "design": "Markdown"}], "context_lines": 25}` (`context_lines` is optional). `build` writes `PACKETS/<name>.md` per group: the review steps, canary and output schema, the group's design text, and `git diff -U<context_lines> base head` for each listed path only (literal pathspecs, no external diff or textconv, a fence longer than any backtick run in the diff). Shared files are never added implicitly; list a file in a group to review it there. Paths are project-relative; absolute, drive and `..` paths are refused. A listed path without changes is left out and reported. A group whose paths have no change, an unknown revision or a malformed spec is refused (exit 2) before any packet is written. `build` prints each packet's size and names other packets already in `PACKETS`, since `run` sends every `*.md` there.

`run` resolves the CLI with `oaw_common.resolve_cli` and starts `claude -p --tools "" --strict-mcp-config --disable-slash-commands --setting-sources project --output-format stream-json --verbose` once per packet, with the packet bytes on stdin and a fresh empty `oaw-goldfish-*` temp folder as working directory, removed afterwards. It refuses to start when `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` is set, unless `--allow-api-key`. Each result records `billing_source`, the init event's `apiKeySource`. When that is not `none`, or no init event arrived, and `--allow-api-key` was not given, `run` writes that result, sends no further packet and exits 1. The init checks (no tools, MCP servers, slash commands or skills; built-in plugins only; agents unusable without tools; the working folder is the fresh temp folder; no `CLAUDE.md`, `CLAUDE.local.md` or `AGENTS.md` in any folder above it; an empty auto-memory folder) are recorded in `init_checks` and `init_checks_passed`. Per D20 the canary answer is recorded as given, and `zero_context_verified` needs every check plus a canary of exactly `none`; it is normally false because the CLI adds its own system prompt. The review is the last ```` ```json ```` fence that opens a line; without one, the result text is kept in `raw_result_if_unparsed`. A timed-out packet is recorded with `timed_out: true`. Before `RESULTS/<name>.json` is written, temp and home paths (as written, with `/` or doubled `\`, Git Bash `/c/...`, WSL `/mnt/c/...`, macOS `/private/...`, and Claude's dash-encoded project folder names), emails, and the account name inside paths are redacted. `--dry-run` prints the CLI version and what would run, and sends nothing.

`check` prints one summary per result (exit code, model, `apiKeySource`, every init check, `zero_context_verified`, findings by severity and kind) and scans each file, raw and decoded, for this machine's temp and home path forms, emails, and the account name inside paths. Leaks are named by kind, never printed. It exits 1 on a leak, a file that is not a JSON object, or a billing source other than `none` that the run did not allow with `--allow-api-key`. Exit codes for all three commands: 0 done, 1 a failed run or a check problem, 2 refused input. The tests use a fake CLI only; nothing here measures review quality.

## Code index (prototype)

A regenerable index for locating code (owner decision D24; W2 of the 2.0.1 plan). Run it from the source checkout; it parses the tree it is pointed at and never imports or runs indexed files. It writes its cache and, with `graph --out FILE`, the requested export. The `oaw-codemap` skill is explicitly invoked. No effect on agent comprehension has been measured.

```bash
python3 scripts/code_index.py find "free text" [--limit 5] [--json]
python3 scripts/code_index.py callers SYMBOL [--limit N] [--json]
python3 scripts/code_index.py path A B [--json]
python3 scripts/code_index.py affected PATH[::Symbol] [--hops 1|2] [--limit N] [--json]
python3 scripts/code_index.py overview [--json]
python3 scripts/code_index.py stats [--json]
python3 scripts/code_index.py graph [--scope DIR] [--format html|mermaid|json] [--out FILE]
```

Every command also takes `--root DIR` (default: the current directory), `--cache DIR` or `--no-cache`, `--frozen` and `--include-generated`, before or after the command name.

`graph` draws file dependencies using the existing index, with no second parser or runtime dependency.
HTML (default) is a self-contained offline SVG view with inline CSS/JS, directory groups, search,
click/keyboard neighbor selection, top callers/callees, zoom and a legend. Open the exported file locally:

```bash
python3 scripts/code_index.py graph --scope scripts --out map.html
python3 scripts/code_index.py graph --scope scripts --format mermaid
```

Output goes to stdout unless `--out FILE` is supplied (UTF-8, LF, surrogate characters backslash-escaped).
Exports are written to a temporary file beside the destination, then atomically replace it on success.
`--json` also selects JSON;
combining it with an explicit non-JSON format is a usage error. Mermaid is text for small scopes and
needs a separate renderer to draw it. All formats include totals, caps, `complete`, `truncated`
(node/edge counts) and `limits`; JSON also exposes `nodes` (`id`, `group`), `edges`
(`source`, `target`, `imports`, `calls`, `weight`), `scope` and `stale_files`.
Caps default to 200 nodes/500 edges, or 40/80 for Mermaid. `--max-nodes N` and `--max-edges N`
accept 1–1000. Nodes are retained by total incoming plus outgoing edge weight, then the strongest edges
among retained nodes, with relative path tie-breaks. Reduce scope before inferring structure from missing edges.

Nodes are indexed Python/JS/TS files, including tests and isolated files. Arrows point from
importer/caller to dependency; weight is import bindings plus resolved call sites, shown separately.
Scopes containing symlinks, junctions or skipped directories are refused; case mismatches name the indexed spelling.
Only cross-file local edges with both endpoints in `--scope DIR` are included; external, unresolved and
intra-file links are omitted. Top lists describe only displayed edges (up to 10 per direction).
Directory groups are deterministic navigation aids, not semantic architecture. Existing index limits,
skips and frozen-cache warnings apply. Exports contain relative paths/counts, no source snippets or
cache locations, and make no network requests; filenames and structure can still be private.
See the [graphify intake](intake/graphify-map.md) for rationale and the predeclared evaluation contract.

What is indexed:

- Python files with `ast` (modules, classes, functions, methods as `Class.method`, module- and class-level names, imports resolved to local files, call sites, docstrings, comments and string literals); a file this Python cannot parse falls back to an indentation-scoped regex pass and is listed by `stats`.
- JavaScript and TypeScript (`.js .mjs .cjs .jsx .ts .tsx .mts .cts`) with a standard-library scanner: comments, strings, template text and regular expression literals are blanked (line numbers kept), then it reads declarations (functions, classes, methods including async/static/get/set/`#private`, arrow and function expressions bound to names, namespaces, interfaces, enums, type aliases, CommonJS `exports.x =`), imports (ES named, default and namespace imports, `export ... from` re-exports, `require()`, `import x = require()`; dynamic `import()` is an import edge only) and call sites with their receiver chain (`a.b.c(`, `new X(`, `this.x(`, `super.x(`, decorators, `f().g(`). A file the scanner fails on keeps a light name pass and is listed by `stats`.
- Imports resolve relative paths (a `.js` name finds its `.ts` twin, then added extensions and `index.*`, also at the root, in the importing file's language first) and the nearest `tsconfig.json`/`jsconfig.json` `compilerOptions.baseUrl` and `paths` (one `*` wildcard; exact keys before wildcards, then the longest prefix; local `extends`, including arrays and any JSON file, merged option by option as TypeScript does, where an explicit `paths: {}` or `baseUrl: null` replaces the inherited value). A module exports only what it marks `export` (declarations, export lists, `export default`, anonymous defaults included) or assigns to `exports`/`module.exports`; `export *` passes on exported names only. Package names and anything not in the tree are external.
- Markdown headings, shell functions and JSON/TOML/YAML keys get a light name pass; other text files are indexed as words.
- `.git`, virtualenvs (any directory with `pyvenv.cfg`), `__pycache__`, `node_modules`, tool caches, symlinks, junctions, binaries and files over 1 MB are skipped. Example copies are skipped only where `sync_examples.py` marked them: a directory whose `.oaw/install.json` has an `installation_id` starting `generated-example-` loses the files its `managed_files` lists (`--include-generated` keeps them). Files with identical content are grouped in `find` results.

Commands:

- `find` ranks files for a description with IDF-weighted overlap of words from identifiers (snake_case and camelCase split, lightly stemmed; JavaScript keywords left out), paths, docstrings and JSDoc, comments and strings, scored per definition or section, then names the best symbol and line in each file. A small built-in synonym list counts at reduced weight. Tests and prose rank lower unless the query mentions tests or documentation. No model is called.
- `callers` lists call sites with `path:line` and the calling function. SYMBOL may be `path::Name`, `path::Class::method`, `module.func`, `Class.method` or a bare name. Python calls are resolved through imports (aliases, relative imports, namespace packages, `importlib.import_module("name")`, `sys.path` additions whose directory name is a string literal), `self`/`cls`/`super()`, local base classes and simple `x = Class()` or `self.x = Class()` assignments. JavaScript/TypeScript calls (including `super(...)`, which reaches the base class's constructor, or the base class when it writes none) are resolved through imports and re-exports (callers of a definition include calls through re-export aliases such as `export { original as renamed }`), `this`/`super`, `extends`, and the types the source writes (a parameter, including the one of `x => ...` and names bound by destructuring, a `for (const x ...)` or `catch (x)` binding, a callback's parameter (arrow functions, function expressions and object-literal methods have their own scope), or a local variable, including names a destructuring declaration binds, whose type is not written shadows an import of the same name and stays unresolved; `this` inside an ordinary nested `function` is unknown, inside an arrow function it is the class's; inside `const g = function f() {}`, `f` is `g`; `let`/`const` inside a block are visible only in that block, and a `require()` inside a function or block binds its name only there): annotations on variables, fields, parameters and constructor parameter properties, `new X()`, written return types (so `this.getX().y()` and `const x = makeX()` resolve), getters, and module constants such as `export const registry = new Registry()`; a receiver written with a built-in type (`string`, `Map`, `T[]`) is external. Calls on a receiver whose type is unknown but that use the same name follow the resolved ones, those whose receiver is named like the target's class first (`index.resolve()` for `Index.resolve`), and for JS/TS also calls that resolve to the same method on a base class or an implemented interface (they may run the target at run time); they are marked `~` in text and `"resolved": false` in JSON. Check them in the source.
- `path` prints the shortest import chain from A to B (file paths or dotted module names; Python and JS/TS files); when there is none it tries B to A and says so.
- `affected` lists local files that import the module, or that call, import or reference the symbol, one row per file; `--hops 2` adds the files that depend on those (importers, or callers of the calling function).
- `overview` prints one page (at most 6,000 characters, about 1.5k tokens) of pointers: entry points (`package.json` `main`/`module`/`bin`, `__main__.py`, `if __name__ == "__main__"`, `argparse` scripts, `#!` node scripts), the top-level directories and the dominant subtree's directories by code files and definitions, the largest modules, and the 20 most-called definitions ranked by PageRank over the call sites this index resolves (tests left out), each with `path:line`, kind, resolved call count and its source line. It holds no descriptions; sections cut by the size cap are named on a final `truncated:` line.
- `stats` prints files by kind, symbols, imports, calls, what was skipped, parse fallbacks, build time and cache state.

Completeness. `callers` and `affected` report `complete` (every match in the index was returned), `truncated` (how many more there are; raise `--limit`) and `limits`. Text output ends with `complete within the index (...)` or `truncated: N more (raise --limit)`. Complete means complete within the index, which tracks only Python and JavaScript/TypeScript calls and imports, at most two hops, and does not follow dynamic dispatch beyond the cases above, inferred types, `any`, string-named calls (`getattr`, framework hooks, `run_method`), reflection, dependency injection (`createInstance`, `invokeFunction`), callbacks and values passed around, JSX elements or object-literal methods. In Python, a method called on what an external call returned (`doc = frappe.get_doc(...)`, then `doc.save()`) resolves as external and is not listed.

Known limits of the JS/TS index. The JavaScript/TypeScript engine is a scanner with heuristics, not a parser or a type checker. Behavior in the classes below is a documented limit, not a defect; review findings there are judged against this list:

- Tokenizing: regular expressions over masked text. Regex versus division, and JSX versus a comparison, are decided from the previous token (a `)` that closes an `if`/`while`/`for`/`with` condition counts as a statement end). Declarations are read only at a line start (plus `for`/`catch` headers); minified, generated or unusually laid-out code and code that depends on automatic semicolon insertion can be misread.
- JSX: tags, attribute strings and text are blanked only in `.jsx`/`.tsx` files and in `.js` files that import React or Preact or carry an `@jsx` pragma; an element that never closes is left as code. JSX elements are not counted as calls to their components.
- Types: no inference. Only written types are used (annotations, `new X()`, written return types, getters, constructor parameter properties); generics are erased; `any`, unions of several classes, conditional and mapped types, overloads, and declaration merging beyond one value plus one interface are not resolved.
- Dispatch: calls that may reach an override or an interface implementation are listed as unresolved; structural typing, dependency injection (`createInstance`, `invokeFunction`) and decorators' run-time effects, mixins, prototype manipulation, getters defined with `Object.defineProperty`, receivers set by `bind`/`call`/`apply`, an ordinary function's `this`, callbacks and values passed around are not followed.
- Dynamic code: `eval`, `new Function`, `require`/`import()` with computed names, computed members (`obj[name]()`), reflection and framework hooks are not followed; a literal `import()` is an import edge only.
- Scopes: functions, anonymous callbacks, `let`/`const` blocks, `for`/`catch` headers, parameters and destructuring are modelled; `with`, `arguments`, labels, hoisting order and reassigned variables are not; object-literal methods and class static blocks are not definitions. Partly handled: object-literal `get`/`set`/`async` methods and arrows whose return type contains parentheses get no scope of their own, and a named function expression passed as an argument shadows imports with its own name but is not linked to a definition.
- Modules: packages (`node_modules`, package `exports` maps, workspaces), aliases from bundler configs other than tsconfig/jsconfig, and packages' declaration files are not read.
- Generated, vendored and minified files are indexed as written; files over 1 MB are skipped.

Cache. By default the index lives in the user's local cache directory: `$XDG_CACHE_HOME/oaw/code-index` or `~/.cache/oaw/code-index`, `%LOCALAPPDATA%\oaw\code-index` on Windows (`--cache DIR` or `OAW_CODE_INDEX_CACHE` names another directory). It is never written inside the indexed tree unless you name a directory there (which is then excluded from the index); when the default location lies inside the tree, the index is built on the fly instead. `--no-cache` builds it in memory and writes nothing. Each indexed root has two JSON files: the structure (definitions, imports, calls) and the search units that only `find` loads, written with a shared token; a cache written by a different `code_index.py` (by content hash) or `INDEX_VERSION` is rebuilt. Each file's size, mtime, inode change time (POSIX) and sha256 are recorded: a file whose size, mtime or change time differs is hashed again and re-indexed when its content changed, so mtimes copied back or set by a skewed network clock do not hide an edit; new files are added and deleted ones dropped. `--frozen` uses the cache as it is and reports stale, new and deleted files on stderr (and in `stats`) instead. When many files need indexing, up to 8 worker processes are used (one process where the platform has none). Agents read the index; only this command writes it, and it is never required before reading code.

`--json` prints `schema_version: 1`. `find`: `results` of `path`, `score`, `symbol`, `line` (and `duplicates` when identical files were grouped). `callers`/`affected`: `results` of `path`, `line`, `symbol` (the calling scope, `<module>` at top level), plus `resolved` or `hop`; `total`, `complete`, `truncated`, `limits` (and `hops` for `affected`). `path`: `path` as a list of files from first to last, and `direction`. `overview`: `entry_points`, `directories`, `inside`, `inside_directories`, `modules`, `most_called` (`path`, `line`, `symbol`, `kind`, `calls`, `signature`), `chars`, `truncated` and `limits`. `stats`: also `cache.origin` (`default`, `--cache` or the environment variable). Paths are repository-relative POSIX paths whatever the platform; inputs may use either slash, be absolute inside the root or name a module. Exit 0 with empty results when nothing matches, 1 on a handled error (unknown file or module, a path outside the root, an unusable root or cache directory) with one `code_index:` line and no traceback, 2 on a usage error (including `--cache` with `--no-cache`).

## Repository validation

```bash
python3 scripts/harness_check.py [--json] [--verbose]
python3 scripts/validate_skills.py [PROJECT] [--all-packages]
python3 scripts/sync_examples.py [--write]
python3 scripts/sync_egm.py --check-bundled
```

The regression group fails when a required `tests/test_*.py` module is missing, fewer tests run than the recorded minimum, or any test is skipped. Set `OAW_ALLOW_SKIPS=1` only on a platform that cannot run a skipped case, such as a Windows host without symlink privilege.
