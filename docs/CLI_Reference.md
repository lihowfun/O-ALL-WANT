# OAW CLI reference

Requires Python 3.10+. All runtime tools use the Python standard library. Replace `python3` with your Python executable when appropriate.

## Framework lifecycle

Run these from the OAW source checkout; `oaw.py` is not copied into target projects.

```bash
python3 scripts/oaw.py init --target PROJECT [--profile minimal|knowledge] [--host codex|claude|both] [--with-improve] [--skills LIST|none|default] [--json]
python3 scripts/oaw.py migrate --target PROJECT [--profile minimal|knowledge] [--host codex|claude|both] [--with-improve] [--skills LIST|none|default] [--apply] [--keep-custom PATH] [--json]
python3 scripts/oaw.py doctor --target PROJECT [--json]
python3 scripts/oaw.py skills [--target PROJECT] [--json]
```

Init protects different existing content; edits to a managed file are kept while its framework copy is unchanged. Profile/host additions are cumulative; codex is the default host. Migrate without `--apply` only previews. Applied migration backs up known changes and stages custom conflicts under `.oaw/proposals/`; unresolved conflicts return exit 3. Use repeatable `--keep-custom PATH` with `--apply` only after reviewing a relevant conflict to retain it as project-owned. Preflight errors/init conflicts return 2. Doctor returns 1 for an unhealthy install and 2 for invalid paths/manifests; WARN checks (edited managed files, a CLAUDE.md without `@AGENTS.md`) keep exit 0. Support does not imply host features are enabled.

The Bash wrapper invokes init on the current directory. Set `OAW_PYTHON` to select an explicit Python executable.

V2 includes the pinned EGM runtime. The default active recipe is seven EGM
entrypoints plus `oaw-evidence`; EGM keeps upstream explicit invocation.
`--skills egm-review,oaw-evidence,oaw-wiki` selects exactly those native skills.
`none` disables all bundled skill entrypoints; `default` resets to the installed
profile's defaults. Omit the flag to preserve an explicit recipe. Selecting wiki
or improve also installs its helper. Profile/helper and host additions persist.

Use `migrate` to preview a recipe that removes entrypoints, then `--apply` to
back up and retire only owned, unchanged packages. Edited SKILL.md blocks the
whole package's removal; an edited Claude agent also remains a pending conflict.
Doctor fails until conflicts are resolved. Foreign skills and project evidence
remain project-owned. Full EGM source stays installed even if its entrypoints
are disabled; this is selection, not a new product named after a combination.
`skills` lists installed files, not proven host discovery or successful activation.

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

`--index` returns one short row per hit instead of an excerpt: `source:line` of the matching line, the memory entry's date, tag and title (for a knowledge page: its frontmatter title, first `# ` heading or file name), the entry's size in characters, and a `match` window from the matching line of at most max(120, query length + 40) characters that always holds the complete match. Text output prints two lines per hit; JSON rows also carry `entry_line` and `kind`, and the packet adds `"mode": "index"`. `--limit`, `--max-chars` and continuation work as in the default mode. A cursor is bound to its mode, so the other mode refuses it. Read the cited line in the source for the full entry.

`memory add`, `lesson` and `annotate` refuse a note that contains a credential: a vendor-prefixed token (GitHub, GitLab, Slack, OpenAI, Anthropic, AWS access key ID, Google, Stripe, Hugging Face, npm, Docker Hub, SendGrid, DigitalOcean, Shopify, PyPI, JWT), a PEM private-key header, a Slack or Discord webhook URL, a password in a URL's userinfo, or an AWS secret access key or session token next to its key name. The check is on by default and has no override flag. A refused write exits 1, names the matched pattern ids without printing the value, and writes nothing; use a placeholder such as `<GITHUB_PAT>` or `scheme://user:${DB_PASS}@host`. A URL password passes only when it is wholly a placeholder (`${DB_PASS}`, `$DB_PASS`, `{db_pass}`, `{{db_pass}}`, `%s`, `%(pw)s`, `***` or `<...>`); a literal `user:pass@host` is refused. An OpenAI key is recognized by its `sk-proj-`, `sk-svcacct-`, `sk-admin-` or `sk-None-` kind, or as a legacy `sk-` plus one alphanumeric run with a digit, so kebab-case names such as `sk-learn-compatible-api` pass; an AWS access key ID must stand alone, not inside a longer alphanumeric run. Generic `password=`/`TOKEN=` assignments are not checked. Only these CLI writes are guarded: a direct edit of `.agents/memory.md` bypasses the check, and a refused value is already in the command line and the host transcript. Called from Python, `memory_add` and `annotate` raise `ValueError` instead.

Topic identifiers cannot contain path separators/traversal or reserved output names. Missing topics and invalid operations return nonzero. Source and state paths are confined to the project, including symlink boundaries. Writer locks cover the complete read-modify-write transaction. Stable `.NAME.oaw.lock` sidecars are synchronization state; do not delete them while writers are running.

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

`cites` is the reverse lookup: it lists the raw notes and manual pages whose `path::Symbol` citations name PATH, or PATH::Symbol and its members, with line and topic. It is read-only and advisory and exits 0 with an empty list when nothing cites the target; an absolute, drive or `..` target exits 1. `--json` returns `schema_version: 1` with `target` and `results` (`source`, `line`, `citation`, `topic_id`).

`memory-check` is a manual, read-only report of `.agents/memory.md` entries whose cited project paths are missing. It exits 0 whenever the check completes (advisory, also when the file is absent), 1 on a handled error such as non-UTF-8 input, and 2 on a usage error. `--limit` (1–500, default 50) truncates findings, never counts. See [memory citation check](Wiki_Sync_Guide.md#memory-citation-check-prototype).

Raw source notes are rendered deterministically into topic pages. Manual pages are not overwritten. Generated source content and annotations use separate boundaries. Local Markdown links are relocated to the output directory. Metadata freshness checks run per page. Unchanged source inputs produce stable generated content.

Existing experiment/state convenience commands remain in `--help` for older projects; they are not required state mirrors. Native skills use name/description and do not require custom triggers or heading conventions. The validator deliberately supports a documented subset of YAML, not every native extension field. Installed doctor/wiki lint check OAW's declared packages, including project-owned custom versions of those packages; unrelated host/plugin skills need their own host/upstream validation. This is not a certification of external packages.

## Optional improvement workflow

```bash
python3 scripts/improvement.py --base-dir PROJECT propose --title TITLE --hypothesis TEXT --target PATH --patch DIFF --evaluation SPEC.json --snapshot BASE_REV
python3 scripts/improvement.py --base-dir PROJECT compare ID --baseline BASELINE.json --candidate CANDIDATE.json
python3 scripts/improvement.py --base-dir PROJECT decide ID --decision accept|reject --reason TEXT
```

Paths are project-relative. A proposal stores its concrete git text diff and fixed evaluation contract. Comparison returns eligible (exit 0), rejected (1) or inconclusive (3); malformed/mismatched inputs return 2. Eligible means ready for explicit review, not automatic approval, deployment, statistical proof, or patch application. See [SELF_IMPROVEMENT](SELF_IMPROVEMENT.md).

An evaluation spec may declare an optional `trigger` block (cases plus `minimum_rate`, default 2/3); candidate case records then need a boolean `triggered`, and a candidate whose mechanism fired below the rate on any designated case compares as inconclusive (`vacuous: mechanism did not trigger`). Only the `improvement.py` from the unreleased OAW-03 change (after the 2.0.0 proposal) enforces it; older copies ignore the block silently.

A spec may also declare `"usage_coverage": "required"` (optional `overhead_fields`). Case records then need `usage_coverage` (`complete`/`incomplete`) and may carry `overhead_tokens` (added to the arm's tokens) and `grading_tokens` (reported, never cost); an efficiency gain counts only when coverage is complete in both arms. Enforced from the unreleased OAW-04 change; older copies ignore it silently.

## Skill catalog (prototype v0)

Run from the OAW source checkout, like `oaw.py`. Every command accepts `--target PROJECT` and `--json`. The official process for adding skills, and how to operate it (Traditional Chinese): [SKILL_INTAKE](SKILL_INTAKE.md).

```bash
python3 scripts/catalog.py add URL [URL ...] [--ref REF] [--no-taste]
python3 scripts/catalog.py list
python3 scripts/catalog.py show FOOD
python3 scripts/catalog.py taste FOOD [--ref REF]
python3 scripts/catalog.py triage FOOD FLAG --benign|--allergen|--confirm-toxic --reason TEXT
python3 scripts/catalog.py import-report FOOD DIR
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
python3 scripts/oaw_status.py [--project PROJECT] [--json]
```

`add` merges duplicate repositories (case, `.git`, trailing slash, SSH and tree URLs). Naming a repository with `add`, or picking a scout candidate with `scout pick`, is the owner's confirmation (D4): each new food is tasted at once (free T0), and `--no-taste` only registers it; a batch in which a taste fails exits 2. `scout` searches GitHub for repositories pushed in the last 7 days, newest first (up to 3 pages of 100 per query; the rest is counted as not fetched), drops unrelated ones without review, and uses stars only to order the candidates. It has no schedule: run it once a week, since a skipped week is not searched again. `taste` pins a snapshot with a hardened git fetch (no hooks, no checkout, https or local file URLs only) and seals it as a read-only tar in `LAB_HOME`, outside the project: `%LOCALAPPDATA%\oaw\lab`, `~/Library/Application Support/oaw/lab` or `$XDG_DATA_HOME/oaw/lab`, overridable with `OAW_LAB_HOME`. Without git it falls back to a codeload tarball marked `unverified-against-commit`. The free T0 checks read the tar in memory; nothing is extracted, executed or imported. Static rules only raise flags: a high-severity flag makes the food `risky`, and only an owner `triage --confirm-toxic` makes it `toxic`. Each food is split into components (skills, hook sets, MCP servers, scripts, manifests, instruction files, docs) proposed as absorb, excrete or hold; executable or flagged parts never default to absorb, a part with an untriaged high-severity flag is held until triage, and rule excretes (package manifests, a second instruction file, binaries) are final. Model-facing skill text is held behind a behavior A/B (D17): a skill becomes absorbable only with consented live evidence (a gain with a parity floor) that names that component, so v0, which has no A/B runner, absorbs no food skill.

Verdicts come from `catalog_core.derive()`, which reads evidence and owner decisions only; stars, authors and requests are not inputs. `import-report` stores an Elephant/Goldfish digestion directory as `historical-prior` evidence that is shown separately and never counted. `plan` is the system's test plan, cheapest first, with token estimates (about 0.6-0.9M logical tokens per tool-using agent run); each step names its D13 stage (0 free, 1 screening, 2 always asks the owner, or digestion overhead) and sandbox level, and only Stage 0/1 is compared with the per-food cap. v0 never runs paid tests, and `policy set` does not yet encode PRE-01: it stores a per-food cap, a weekly cap and free sandbox conditions, with no per-round overhead cap or sandbox levels. `policy set` and `triage --benign|--allergen` need an interactive terminal (stdin and stderr are TTYs): they print a one-time code there and read it back in the same process; without one they refuse, and no code is written anywhere. `ui` and `menu` keep their codes in memory, show them on their own terminal, and stop accepting codes after three wrong ones. The code is a speed bump against an agent acting through the CLI, not authentication: `policy.json` and `decisions.jsonl` are unauthenticated project files that anything with write access can edit, so records say `confirmed_via: code typed back on an interactive terminal (unauthenticated)`. A SKILL.md (or a text file the skill ships) that asks the agent to run a command, in a fence, an inline code span or a "run `…`" instruction, or that matches any flag rule, is `X1-inline` and held for a sandbox trial even after its flags are triaged; records from older scan rules must be tasted again before anything is absorbed.

`absorb`, `remove`, `readd`, `restore` and `forget` only preview without `--apply`; `remove` and `readd` need `--reason` with `--apply`. Applying first snapshots the OAW-managed layer (install manifest, managed files OAW can produce from its templates or allowlisted absorbed skill text, the EGM runtime, absorb receipts) into `LAB_HOME`, indexes it there, evaluates it against the default, then names the result `2.0.0+build.N.<hash7>`. Only text-only skills proposed for absorption are installed, and only after the same skill lint doctor runs passes on a staged copy in `LAB_HOME`; the text is copied unchanged (not re-implemented yet) together with the food's root `LICENSE`/`NOTICE`/`COPYING` files and an `OAW-UPSTREAM.md` note (source, pinned commit, tree hash, files, license, "Modifications: none"). A removed part is not absorbed again from its old taste: it needs a taste recorded after the removal (D6); a selection of historical proposals only is recorded as backlog decisions, changes no file and makes no build. A `remove` name means one thing: `egm`, a bundled skill, or one absorbed skill; `--food` removes every installed part of a food. Receipt paths are deleted only when they sit in one absorbed skill folder and match the install manifest's hashes. Bundled skills and `egm` are removed and re-added through `oaw.py migrate` (backup first); a removal never adds and a re-add never retires. `restore` accepts only restore points this `LAB_HOME` created for this project (the location is derived, not read from `builds.json`), refuses any snapshot path outside the layer (never `.git/`, host settings, `.mcp.json` or project records), keeps declared custom files custom, refuses to overwrite any other file the current install does not manage, then runs doctor. `effect` compares the install with a fresh default recipe: every line is `static-measured`, and quality stays `not measured` without consented live evidence for a food whose parts the layer holds. `view` writes `.oaw/catalog/view.json` for every renderer; `status.json` keeps schema 1. A generated `.oaw/catalog/.gitignore` keeps only `builds.json` and `absorbed/*.json` committable. Exit codes follow the D14 CLI contract: 0 done, 2 refused or failed, 3 a choice is needed (the page or menu waits for the owner's code).

`ui` serves the intake pipeline page (`scripts/catalog_ui/`) on `127.0.0.1` at a free port and opens the browser with a per-session token in the URL fragment. Every `/api/` call needs that token in the `X-OAW-Token` header and a `Host` naming the bound address; no CORS headers are sent, actions are JSON `POST`s only, and cross-site `Origin`/`Sec-Fetch-Site` requests are refused. One action runs at a time in a background thread; the page polls its progress and `view.json`. JSON responses escape `<`, `>` and `&`, the page sets text with `textContent` only, a Content-Security-Policy allows only its own files, and food-supplied HTML, SVG or images are never rendered. Confirmation codes are printed on the terminal that runs `ui`, never in an API response. The main screen is the official intake process of [SKILL_INTAKE](SKILL_INTAKE.md): two inlets (weekly scout → relevance filter → owner confirms, and owner-named repositories) merge into the nine stages of `catalog_core.PIPELINE_STAGES` (入口, 封存, 靜態, 計畫, 盲審, 實測, 分流, 核准, 版本), each marked automated, owner, mixed or planned. Each food is a token on its current stage with one coloured pip per component; when its stage changes between refreshes the token glides there with a CSS transition (instant under `prefers-reduced-motion`). The current stage's actions are buttons under the token and call the same engine actions as the CLI; owner-code steps are shown as a copyable `menu` command for this project, and planned stages (zero-context Goldfish review, paid tests) are drawn without any button. The food card (components as 🟢 吸收 / 🔴 排掉 / 🟡 暫留 with reasons and evidence levels, flags, the system plan, 🐘/🐟 records labelled 歷史證據) opens from the token; 我的 OAW (current build, skills with remove and re-add, effect versus the default with an evidence level per line, the build timeline with 還原到這版, standing policy) opens from the 版本 stage. `menu` prints the same stage table as one ASCII line per food (`● done ◐ partly done ◉ current ⊗ blocked ⊖ removed ○ not reached ┄ planned – not needed`; a passed stage with planned steps is partly done), lists every food's current-stage actions by letter and keeps the numbered screens, without curses, for Codex or terminals without a browser. `oaw_status.py` prints the same pipeline lines when `.oaw/catalog/view.json` exists, with the same display rules: quality is 未量測 without measured evidence, stars appear only as queue order, and unknown verdict words or stage states show as unknown. `view.json` uses schema `oaw-catalog-view/2`: it carries the stage table under `pipeline` and each food's `pipeline` (stage, per-stage states, note, actions, parity label).

## Repository validation

```bash
python3 scripts/harness_check.py [--json] [--verbose]
python3 scripts/validate_skills.py [PROJECT] [--all-packages]
python3 scripts/sync_examples.py [--write]
python3 scripts/sync_egm.py --check-bundled
```

The regression group fails when a required `tests/test_*.py` module is missing, fewer tests run than the recorded minimum, or any test is skipped. Set `OAW_ALLOW_SKIPS=1` only on a platform that cannot run a skipped case, such as a Windows host without symlink privilege.
