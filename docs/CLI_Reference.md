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
python3 scripts/context_hub.py memory recall QUERY [--limit N] [--cursor TOKEN] [--max-chars N] [--json]
```

Recall bounds the complete rendered output and returns continuation when records or excerpts remain. Keep the same query/options for continuation. Source positions and revisions identify evidence, not verified truth. The legacy `bootstrap`, `setup`, `context --lane ...`, and `lesson` conveniences remain available through `--help`; v2 policy does not require them.

Topic identifiers cannot contain path separators/traversal or reserved output names. Missing topics and invalid operations return nonzero. Source and state paths are confined to the project, including symlink boundaries. Writer locks cover the complete read-modify-write transaction. Stable `.NAME.oaw.lock` sidecars are synchronization state; do not delete them while writers are running.

## Knowledge profile

```bash
python3 scripts/wiki_sync.py refresh TOPIC
python3 scripts/wiki_sync.py build
python3 scripts/wiki_sync.py lint [--strict]
python3 scripts/wiki_sync.py stale [--threshold DAYS]
python3 scripts/wiki_sync.py cross-check
```

Raw source notes are rendered deterministically into topic pages. Manual pages are not overwritten. Generated source content and annotations use separate boundaries. Local Markdown links are relocated to the output directory. Metadata freshness checks run per page. Unchanged source inputs produce stable generated content.

Existing experiment/state convenience commands remain in `--help` for older projects; they are not required state mirrors. Native skills use name/description and do not require custom triggers or heading conventions. The validator deliberately supports a documented subset of YAML, not every native extension field. Installed doctor/wiki lint check OAW's declared packages, including project-owned custom versions of those packages; unrelated host/plugin skills need their own host/upstream validation. This is not a certification of external packages.

## Optional improvement workflow

```bash
python3 scripts/improvement.py --base-dir PROJECT propose --title TITLE --hypothesis TEXT --target PATH --patch DIFF --evaluation SPEC.json --snapshot BASE_REV
python3 scripts/improvement.py --base-dir PROJECT compare ID --baseline BASELINE.json --candidate CANDIDATE.json
python3 scripts/improvement.py --base-dir PROJECT decide ID --decision accept|reject --reason TEXT
```

Paths are project-relative. A proposal stores its concrete git text diff and fixed evaluation contract. Comparison returns eligible (exit 0), rejected (1) or inconclusive (3); malformed/mismatched inputs return 2. Eligible means ready for explicit review, not automatic approval, deployment, statistical proof, or patch application. See [SELF_IMPROVEMENT](SELF_IMPROVEMENT.md).

## Skill catalog (prototype v0)

Run from the OAW source checkout, like `oaw.py`. Every command accepts `--target PROJECT` and `--json`. Player guide (Traditional Chinese): [CATALOG_PLAY](CATALOG_PLAY.md).

```bash
python3 scripts/catalog.py add URL [URL ...] [--ref REF]
python3 scripts/catalog.py list
python3 scripts/catalog.py show FOOD
python3 scripts/catalog.py taste FOOD [--ref REF]
python3 scripts/catalog.py triage FOOD FLAG --benign|--allergen|--confirm-toxic --reason TEXT [--confirm CODE]
python3 scripts/catalog.py import-report FOOD DIR
python3 scripts/catalog.py plan FOOD
python3 scripts/catalog.py policy show
python3 scripts/catalog.py policy set --per-food-tokens N --weekly-tokens N --sandbox isolated-venv,project-copy,no-api-keys [--confirm CODE]
python3 scripts/catalog.py absorb FOOD --components ID[,ID ...] [--reason TEXT] [--apply]
python3 scripts/catalog.py remove SKILL|egm|FOOD [--reason TEXT] [--apply]
python3 scripts/catalog.py builds
python3 scripts/catalog.py restore BUILD [--apply]
python3 scripts/catalog.py effect
python3 scripts/catalog.py view
python3 scripts/catalog.py scout [list | pick N [N ...]]
python3 scripts/catalog.py play [--no-browser] [--port N]
python3 scripts/catalog.py menu
python3 scripts/oaw_status.py [--project PROJECT] [--json]
```

`add` merges duplicate repositories (case, `.git`, trailing slash, SSH and tree URLs). `taste` pins a snapshot with a hardened git fetch (no hooks, no checkout, https or local file URLs only) and seals it as a read-only tar in `LAB_HOME`, outside the project: `%LOCALAPPDATA%\oaw\lab`, `~/Library/Application Support/oaw/lab` or `$XDG_DATA_HOME/oaw/lab`, overridable with `OAW_LAB_HOME`. Without git it falls back to a codeload tarball marked `unverified-against-commit`. The free T0 checks read the tar in memory; nothing is extracted, executed or imported. Static rules only raise flags: a high-severity flag makes the food `risky`, and only an owner `triage --confirm-toxic` makes it `toxic`. Each food is split into components (skills, hook sets, MCP servers, scripts, manifests, instruction files, docs) proposed as absorb, excrete or hold; executable or flagged parts never default to absorb.

Verdicts come from `catalog_core.derive()`, which reads evidence and owner decisions only; stars, authors and requests are not inputs. `import-report` stores an Elephant/Goldfish digestion directory as `historical-prior` evidence that is shown separately and never counted. `plan` is the system's test plan, cheapest first, with token estimates (about 0.6-0.9M logical tokens per tool-using agent run); v0 never runs paid tests. `policy set` and `triage --benign|--allergen` print a one-time code on the interactive terminal and exit 4 until the same command is repeated with `--confirm CODE`; a wrong code is burned.

`absorb`, `remove` and `restore` only preview without `--apply`. Applying first snapshots the OAW-managed layer (install manifest, managed files, `.oaw/integrations/`, absorb receipts) into `LAB_HOME`, then names the result `2.0.0+build.N.<hash7>`. Only text-only skills proposed for absorption are installed; other parts are recorded as backlog items. Bundled skills and `egm` are removed through `oaw.py migrate`. `restore` writes or deletes only OAW-managed paths, never project records, then runs doctor. `effect` compares the install with a fresh default recipe: every line is `static-measured`, and quality stays `not measured` without consented live evidence. `view` writes `.oaw/catalog/view.json` for every renderer; `status.json` keeps schema 1. A generated `.oaw/catalog/.gitignore` keeps only `builds.json` and `absorbed/*.json` committable. Exit codes: 0 done, 2 refused or failed, 4 waiting for the owner's code.

`play` serves the game page (`scripts/catalog_ui/`) on `127.0.0.1` at a free port and opens the browser with a per-session token in the URL fragment. Every `/api/` call needs that token in the `X-OAW-Token` header and a `Host` naming the bound address; no CORS headers are sent, actions are JSON `POST`s only, and cross-site `Origin`/`Sec-Fetch-Site` requests are refused. One action runs at a time in a background thread; the page polls its progress and `view.json`. JSON responses escape `<`, `>` and `&`, the page sets text with `textContent` only, a Content-Security-Policy allows only its own files, and food-supplied HTML, SVG or images are never rendered. Confirmation codes are printed on the terminal that runs `play`, never in an API response. The page shows three areas: 我的 OAW (current build and label, skills, effect versus the default with an evidence-level chip per line, build timeline with 還原到這版 preview then confirm, standing policy), 投食區 (GitHub URLs with duplicate merges reported, the weekly scout list with checkboxes, and an import of existing Elephant/Goldfish records), and one 食物卡 per food (① 找到 → ② 試吃 → ③ 實測 → ④ 結果, components as 🟢 吸收 / 🔴 排掉 / 🟡 暫留 with reasons, 🐘/🐟 reports labelled 歷史證據, the system plan and estimate behind 實測…, absorb and remove). `menu` offers the same actions as a numbered terminal menu without curses, for Codex or terminals without a browser. `oaw_status.py` prints the same catalog view when `.oaw/catalog/view.json` exists, with the same display rules: quality is 未量測 without measured evidence, stars appear only as queue order, and unknown verdict words show as unknown.

## Repository validation

```bash
python3 scripts/harness_check.py [--json] [--verbose]
python3 scripts/validate_skills.py [PROJECT] [--all-packages]
python3 scripts/sync_examples.py [--write]
python3 scripts/sync_egm.py --check-bundled
```

The regression group fails when a required `tests/test_*.py` module is missing, fewer tests run than the recorded minimum, or any test is skipped. Set `OAW_ALLOW_SKIPS=1` only on a platform that cannot run a skipped case, such as a Windows host without symlink privilege.
