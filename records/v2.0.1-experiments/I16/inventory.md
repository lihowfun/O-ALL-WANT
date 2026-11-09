# OAW tested terminal journeys

Source: the supplied `claude/oaw-2` snapshot at `80bb3fa`. Runtime: `/usr/bin/python3` (Python 3.10.12); Linux-6.8.0-136-generic-x86_64-with-glibc2.35. Verification time: 2026-11-09T01:39:32.325457+00:00.

`inventory.json` is a list of 28 journeys. Each `setup` is an ordered list of Bash commands, to run together in a fresh folder containing a complete source copy at `./oaw`. Run `commands` in order in that same shell. Commands that start with `(cd project ...)` use the installed helpers; lifecycle, user-skill, catalog and status commands use the source checkout. All setup fixtures are created explicitly, without importing test fixtures.

`can_host` describes natural variation opportunities, not a claim that every variation is asserted by the cited tests. B1: non-ASCII input; B2: input size and form; B3: partial operation and continuation; B4: state across commands; B5: repeated runs; B6: CLI reporting; B7: paths; B8: ownership of existing user files. These are coverage categories only.

| id | commands | can_host | oracle count |
|---|---|---|---:|
| install-minimal | `oaw.py init`; `oaw.py doctor`; `oaw.py skills` | B4, B5, B6, B7, B8 | 1 |
| install-knowledge | `oaw.py init`; `oaw.py doctor` | B1, B4, B5, B7, B8 | 1 |
| install-claude | `oaw.py init`; `oaw.py skills`; `oaw.py doctor` | B4, B5, B6, B7 | 1 |
| install-both-hosts | `oaw.py init`; `oaw.py skills`; `oaw.py doctor` | B4, B5, B6, B7, B8 | 1 |
| add-project-host | `oaw.py migrate`; `oaw.py init`; `oaw.py skills`; `oaw.py doctor` | B3, B4, B5, B7, B8 | 1 |
| choose-skill-recipe | `oaw.py migrate`; `oaw.py init`; `oaw.py skills`; `oaw.py doctor` | B3, B4, B5, B7, B8 | 2 |
| plan-review-effort | `oaw_mode.py suggest`; `oaw_mode.py show light`; `oaw_mode.py show standard` | B1, B2, B4, B5, B6, B7 | 3 |
| set-design-review | `oaw_mode.py egm`; `oaw_mode.py suggest`; `oaw_mode.py egm on`; `oaw_mode.py egm off`; `oaw_mode.py egm auto` | B3, B4, B5, B6, B7, B8 | 2 |
| estimate-review-budget | `oaw_mode.py egm estimate`; `oaw_mode.py egm on` | B1, B2, B4, B5, B6, B7 | 2 |
| record-plan-review | `oaw_mode.py reviewed`; `oaw_mode.py suggest` | B1, B3, B4, B5, B6, B7, B8 | 1 |
| review-saved-plan | `oaw_mode.py suggest` | B1, B2, B4, B5, B6, B7 | 1 |
| choose-code-reviewer | `oaw_mode.py second-opinion codex`; `oaw_mode.py show standard`; `oaw_mode.py egm off`; `oaw_mode.py show deep`; `oaw_mode.py egm auto`; `oaw_mode.py second-opinion claude`; `oaw_mode.py second-opinion same` | B4, B5, B6, B7, B8 | 1 |
| annotate-project-topic | `context_hub.py get`; `context_hub.py annotate` | B1, B2, B4, B5, B6, B7, B8 | 1 |
| page-memory-recall | `context_hub.py memory recall` | B1, B2, B4, B5, B6, B7 | 2 |
| locate-memory-evidence | `context_hub.py memory recall --index` | B1, B2, B4, B5, B6, B7 | 2 |
| find-project-code | `code_index.py find` | B1, B2, B4, B5, B6, B7 | 2 |
| trace-symbol-callers | `code_index.py callers` | B1, B2, B4, B5, B6, B7 | 2 |
| follow-import-chain | `code_index.py path` | B1, B2, B4, B5, B6, B7 | 1 |
| inspect-change-reach | `code_index.py affected` | B1, B2, B4, B5, B6, B7 | 1 |
| refresh-code-cache | `code_index.py stats`; `code_index.py find` | B3, B4, B5, B6, B7, B8 | 1 |
| orient-in-typescript | `code_index.py overview` | B1, B2, B4, B5, B6, B7 | 1 |
| export-dependency-map | `code_index.py graph` | B1, B2, B4, B5, B6, B7, B8 | 2 |
| preview-local-skills | `oaw.py add`; `oaw.py list` | B1, B2, B4, B5, B6, B7, B8 | 1 |
| add-and-remove-skills | `oaw.py add`; `oaw.py list`; `oaw.py remove`; `oaw.py doctor` | B1, B2, B3, B4, B5, B6, B7, B8 | 1 |
| manage-only-own-skills | `oaw.py add`; `oaw.py list`; `oaw.py doctor`; `oaw.py remove` | B1, B2, B3, B4, B5, B6, B7, B8 | 1 |
| remove-bundled-skill | `oaw.py remove`; `oaw.py list`; `oaw.py doctor` | B3, B4, B5, B6, B7, B8 | 1 |
| catalog-local-paper | `catalog.py add`; `catalog.py list`; `catalog.py show sleep-notes`; `catalog.py plan` | B1, B2, B4, B5, B6, B7 | 1 |
| read-project-progress | `oaw_status.py` | B1, B2, B4, B5, B6, B7 | 1 |

## Measured results

- Setups: **28/28 passed**.
- Complete terminal command sequences: **28/28 passed**.
- Longest setup plus command sequence: **1.578s**; every journey was below 60 seconds.
- Unique individual oracle methods: **38/38 passed** (38 journey-to-oracle links).
- Each oracle was invoked separately with `unittest`; a pass requires exit 0, exactly one test run, `OK`, and no skip. All oracle processes ran from a source copy.
- No network or model calls are part of these journeys. Only local paths are supplied to intake commands, Git is restricted to the file transport, and no host CLI or `doctor --probe` is run.
- `TMPDIR`, OAW configuration and lab paths, and XDG cache/data paths point within this folder. Tests' `tempfile` allocations inherit that `TMPDIR`. Shell setup exports appear below.
- Original source content SHA-256 before: `dd26b9297abe74c0884051d7be2d8cb187ba44b3ce6daee7181b00789e7ee3d9`.
- Original source content SHA-256 after: `dd26b9297abe74c0884051d7be2d8cb187ba44b3ce6daee7181b00789e7ee3d9`.
- Setup and command output logs, individual oracle logs, and machine-readable results are in [.verification/](.verification/). Reading and assertion coverage for every cited method was checked against the test source; some oracles exercise more scenarios than the corresponding journey.

## Exact verification invocations

The inventory was generated and verified with:

```bash
/usr/bin/python3 build_inventory.py
/usr/bin/python3 verify_inventory.py --source ../oaw-src
/usr/bin/python3 verify_inventory.py --source ../oaw-src --only-journey estimate-review-budget
```

The verifier uses `shutil.copytree` for each temporary source copy. A setup's working directory is a fresh `mkdtemp` folder under `.verification/work/`, populated with `./oaw`; it executes `bash --noprofile --norc ./verify.sh` with a 60-second limit. The exact scripts appear below and are saved under `.verification/scripts/`. The verifier records a setup-completion marker before running the journey commands. Temporary source and project folders are removed after each run; scripts and logs are retained.

Oracle working directory: `.verification/oracle-oaw`. Exact inherited environment overrides:

```bash
export TMPDIR="$PWD/.verification/tmp"
export OAW_CONFIG_HOME="$PWD/.verification/state/config"
export OAW_LAB_HOME="$PWD/.verification/state/lab"
export XDG_CACHE_HOME="$PWD/.verification/state/cache"
export XDG_DATA_HOME="$PWD/.verification/state/data"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
```

### Individual oracle commands and results

Each command below was run separately from `.verification/oracle-oaw`:

```bash
/usr/bin/python3 -m unittest tests.test_catalog.CatalogCliTests.test_a_local_pdf_is_sealed_with_metadata_from_the_file_only
# PASS; exit 0; 0.966s; Ran 1 test in 0.773s; OK
/usr/bin/python3 -m unittest tests.test_code_index.CodeIndexTests.test_affected_lists_importers_and_callers_with_two_hops
# PASS; exit 0; 0.143s; Ran 1 test in 0.007s; OK
/usr/bin/python3 -m unittest tests.test_code_index.CodeIndexTests.test_cache_records_hashes_and_reindexes_stale_files
# PASS; exit 0; 0.151s; Ran 1 test in 0.017s; OK
/usr/bin/python3 -m unittest tests.test_code_index.CodeIndexTests.test_callers_resolve_aliases_methods_and_instances
# PASS; exit 0; 0.142s; Ran 1 test in 0.006s; OK
/usr/bin/python3 -m unittest tests.test_code_index.CodeIndexTests.test_cli_json_shapes_and_exit_codes
# PASS; exit 0; 1.231s; Ran 1 test in 1.096s; OK
/usr/bin/python3 -m unittest tests.test_code_index.CodeIndexTests.test_find_ranks_definitions_methods_and_lines
# PASS; exit 0; 0.142s; Ran 1 test in 0.007s; OK
/usr/bin/python3 -m unittest tests.test_code_index.CodeIndexTests.test_identifiers_split_into_stemmed_words_and_rare_words_weigh_more
# PASS; exit 0; 0.143s; Ran 1 test in 0.007s; OK
/usr/bin/python3 -m unittest tests.test_code_index.CodeIndexTests.test_relative_imports_resolve_and_import_path_is_shortest
# PASS; exit 0; 0.141s; Ran 1 test in 0.007s; OK
/usr/bin/python3 -m unittest tests.test_code_index.DrawnGraphTests.test_cli_formats_stdout_files_errors_and_windows_output
# PASS; exit 0; 1.329s; Ran 1 test in 1.188s; OK
/usr/bin/python3 -m unittest tests.test_code_index.DrawnGraphTests.test_exact_file_graph_reuses_index_and_keeps_tests_and_isolates
# PASS; exit 0; 0.140s; Ran 1 test in 0.004s; OK
/usr/bin/python3 -m unittest tests.test_code_index.JavaScriptIndexTests.test_overview_is_one_capped_page_of_pointers
# PASS; exit 0; 0.244s; Ran 1 test in 0.112s; OK
/usr/bin/python3 -m unittest tests.test_context_hub.ContextHubTests.test_annotation_migrates_legacy_notes_and_refuses_meta
# PASS; exit 0; 0.153s; Ran 1 test in 0.061s; OK
/usr/bin/python3 -m unittest tests.test_context_hub.ContextHubTests.test_recall_budgets_json_and_pages_independent_entries
# PASS; exit 0; 0.093s; Ran 1 test in 0.003s; OK
/usr/bin/python3 -m unittest tests.test_context_hub.ContextHubTests.test_recall_default_output_is_byte_identical
# PASS; exit 0; 0.094s; Ran 1 test in 0.003s; OK
/usr/bin/python3 -m unittest tests.test_context_hub.ContextHubTests.test_recall_index_knowledge_page_row_uses_title_and_matched_line
# PASS; exit 0; 0.096s; Ran 1 test in 0.003s; OK
/usr/bin/python3 -m unittest tests.test_context_hub.ContextHubTests.test_recall_index_rows_cite_match_line_and_fit_max_chars
# PASS; exit 0; 0.150s; Ran 1 test in 0.058s; OK
/usr/bin/python3 -m unittest tests.test_egm_integration.EgmIntegrationTests.test_reinit_without_selection_preserves_previous_explicit_selection
# PASS; exit 0; 0.377s; Ran 1 test in 0.282s; OK
/usr/bin/python3 -m unittest tests.test_egm_integration.EgmIntegrationTests.test_subset_migration_previews_without_writes_then_backs_up_owned_bridge_removal
# PASS; exit 0; 0.818s; Ran 1 test in 0.727s; OK
/usr/bin/python3 -m unittest tests.test_install.InstallTests.test_additive_profiles_preserve_domain_content
# PASS; exit 0; 0.518s; Ran 1 test in 0.428s; OK
/usr/bin/python3 -m unittest tests.test_install.InstallTests.test_both_hosts_receive_identical_native_skill_packages
# PASS; exit 0; 0.703s; Ran 1 test in 0.612s; OK
/usr/bin/python3 -m unittest tests.test_install.InstallTests.test_claude_host_uses_native_claude_skill_folder_only
# PASS; exit 0; 0.507s; Ran 1 test in 0.417s; OK
/usr/bin/python3 -m unittest tests.test_install.InstallTests.test_fresh_minimal_install_and_idempotence
# PASS; exit 0; 0.619s; Ran 1 test in 0.529s; OK
/usr/bin/python3 -m unittest tests.test_install.InstallTests.test_host_selection_is_additive_and_default_source_api_stays_codex
# PASS; exit 0; 0.963s; Ran 1 test in 0.866s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.GitDiffTests.test_path_list_counts_missing_paths_as_new
# PASS; exit 0; 0.128s; Ran 1 test in 0.051s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.GitDiffTests.test_planned_folders_trigger_like_files_in_them
# PASS; exit 0; 0.145s; Ran 1 test in 0.057s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.ShowTests.test_light_and_standard_are_fixed
# PASS; exit 0; 0.097s; Ran 1 test in 0.013s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.SwitchAndStepTests.test_a_named_plan_is_reviewed_with_or_without_git
# PASS; exit 0; 0.119s; Ran 1 test in 0.038s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.SwitchAndStepTests.test_a_recorded_review_counts_only_for_the_same_file_content
# PASS; exit 0; 0.213s; Ran 1 test in 0.130s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.SwitchAndStepTests.test_cap_and_estimate
# PASS; exit 0; 0.179s; Ran 1 test in 0.069s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.SwitchAndStepTests.test_default_switch_is_auto_and_auto_means_fresh_context_until_x2
# PASS; exit 0; 0.093s; Ran 1 test in 0.015s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.SwitchAndStepTests.test_estimate_with_context_applies_the_cap
# PASS; exit 0; 0.103s; Ran 1 test in 0.020s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.SwitchAndStepTests.test_show_follows_the_second_opinion_setting
# PASS; exit 0; 0.112s; Ran 1 test in 0.029s; OK
/usr/bin/python3 -m unittest tests.test_oaw_mode.SwitchAndStepTests.test_switch_positions_change_the_deep_design_review
# PASS; exit 0; 0.191s; Ran 1 test in 0.113s; OK
/usr/bin/python3 -m unittest tests.test_status.StatusTests.test_progress_counts_and_unknown_percent
# PASS; exit 0; 0.057s; Ran 1 test in 0.002s; OK
/usr/bin/python3 -m unittest tests.test_user_install.UserInstallTests.test_builtin_skill_removal_previews_then_applies
# PASS; exit 0; 0.798s; Ran 1 test in 0.632s; OK
/usr/bin/python3 -m unittest tests.test_user_install.UserInstallTests.test_choice_oaw_on_clean_project_then_remove_one_restores_exactly
# PASS; exit 0; 0.775s; Ran 1 test in 0.607s; OK
/usr/bin/python3 -m unittest tests.test_user_install.UserInstallTests.test_choice_only_on_clean_project_is_manager_only
# PASS; exit 0; 0.225s; Ran 1 test in 0.056s; OK
/usr/bin/python3 -m unittest tests.test_user_install.UserInstallTests.test_preview_writes_nothing_on_clean_and_installed_projects
# PASS; exit 0; 0.536s; Ran 1 test in 0.365s; OK
```

### Setup and journey scripts

The `# setup` and `# commands` sections below reproduce the JSON arrays in order. The completion-marker line is verification bookkeeping and does not form part of the user journey.

#### install-minimal

You are a developer starting a small project that has no OAW files yet. Use oaw.py init to add the default tools, repeat init, and inspect the installation with doctor and skills.

Result: setup PASS; commands PASS; exit 0; 0.779s for setup and commands together. [stdout](.verification/logs/setups/install-minimal.stdout.log) · [stderr](.verification/logs/setups/install-minimal.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
mkdir project

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py skills --target ./project --json
```

Oracles: `tests/test_install.py::InstallTests::test_fresh_minimal_install_and_idempotence`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### install-knowledge

You maintain a project with an existing knowledge index and want OAW's knowledge and improvement tools. Install them with oaw.py init --profile knowledge --with-improve, then inspect the project with doctor.

Result: setup PASS; commands PASS; exit 0; 0.730s for setup and commands together. [stdout](.verification/logs/setups/install-knowledge.stdout.log) · [stderr](.verification/logs/setups/install-knowledge.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/docs/knowledge/index.md': '# Team knowledge\n\nRelease notes live here.\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --profile knowledge --with-improve --json
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_install.py::InstallTests::test_additive_profiles_preserve_domain_content`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### install-claude

You use Claude Code and have a new project ready for OAW. Use oaw.py init --host claude, then list the installed skills and inspect the installation with doctor.

Result: setup PASS; commands PASS; exit 0; 0.679s for setup and commands together. [stdout](.verification/logs/setups/install-claude.stdout.log) · [stderr](.verification/logs/setups/install-claude.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
mkdir project

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --host claude --json
/usr/bin/python3 ./oaw/scripts/oaw.py skills --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_install.py::InstallTests::test_claude_host_uses_native_claude_skill_folder_only`.

Notes: Checks installed files offline. doctor is used without --probe; Claude Code is neither required nor started.

#### install-both-hosts

You share a project between Codex and Claude Code and want the knowledge and improvement tools available to both. Start with an empty project, run oaw.py init --host both --profile knowledge --with-improve, and inspect skills and doctor.

Result: setup PASS; commands PASS; exit 0; 0.804s for setup and commands together. [stdout](.verification/logs/setups/install-both-hosts.stdout.log) · [stderr](.verification/logs/setups/install-both-hosts.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
mkdir project

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --host both --profile knowledge --with-improve --json
/usr/bin/python3 ./oaw/scripts/oaw.py skills --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_install.py::InstallTests::test_both_hosts_receive_identical_native_skill_packages`.

Notes: Inspects native skill packages on disk. Neither Codex nor Claude Code is started; host discovery is outside this journey.

#### add-project-host

Your project already has OAW installed for Claude Code and you now also use Codex. Preview and apply oaw.py migrate --host codex, then run init, skills and doctor to inspect the resulting project.

Result: setup PASS; commands PASS; exit 0; 1.486s for setup and commands together. [stdout](.verification/logs/setups/add-project-host.stdout.log) · [stderr](.verification/logs/setups/add-project-host.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --host claude --json

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py migrate --target ./project --host codex --json
/usr/bin/python3 ./oaw/scripts/oaw.py migrate --target ./project --host codex --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py skills --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_install.py::InstallTests::test_host_selection_is_additive_and_default_source_api_stays_codex`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### choose-skill-recipe

You maintain a project with the default OAW skills installed for both hosts and want a smaller selection. Preview and apply oaw.py migrate --skills egm-review, then use init, skills and doctor to inspect that selection.

Result: setup PASS; commands PASS; exit 0; 1.453s for setup and commands together. [stdout](.verification/logs/setups/choose-skill-recipe.stdout.log) · [stderr](.verification/logs/setups/choose-skill-recipe.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --host both --json

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py migrate --target ./project --skills egm-review --json
/usr/bin/python3 ./oaw/scripts/oaw.py migrate --target ./project --skills egm-review --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py skills --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_egm_integration.py::EgmIntegrationTests::test_subset_migration_previews_without_writes_then_backs_up_owned_bridge_removal`, `tests/test_egm_integration.py::EgmIntegrationTests::test_reinit_without_selection_preserves_previous_explicit_selection`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### plan-review-effort

You are planning a project change and want to see which review steps OAW recommends before you start. In a project with OAW installed and a committed baseline, use oaw_mode.py suggest --paths for a new design document and a workflow folder, then read show light and show standard.

Result: setup PASS; commands PASS; exit 0; 0.636s for setup and commands together. [stdout](.verification/logs/setups/plan-review-effort.stdout.log) · [stderr](.verification/logs/setups/plan-review-effort.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
git -C project init -q
git -C project add .
git -C project -c user.name=Tester -c user.email=tester@example.invalid -c core.hooksPath=/dev/null commit -qm baseline

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --paths docs/designs/cache.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --paths .github/workflows --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py show light)
(cd project && /usr/bin/python3 scripts/oaw_mode.py show standard)
```

Oracles: `tests/test_oaw_mode.py::GitDiffTests::test_path_list_counts_missing_paths_as_new`, `tests/test_oaw_mode.py::GitDiffTests::test_planned_folders_trigger_like_files_in_them`, `tests/test_oaw_mode.py::ShowTests::test_light_and_standard_are_fixed`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### set-design-review

You are a project maintainer choosing how design reviews should be described for a saved plan. With OAW and its EGM entry point installed, use oaw_mode.py egm to inspect and select auto, on and off, and use suggest --plan to read the steps for each setting.

Result: setup PASS; commands PASS; exit 0; 0.791s for setup and commands together. [stdout](.verification/logs/setups/set-design-review.stdout.log) · [stderr](.verification/logs/setups/set-design-review.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/docs/plans/cache.md': '# Cache plan\n\nUse a small local cache for reports.\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --plan docs/plans/cache.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm on --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --plan docs/plans/cache.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm off --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --plan docs/plans/cache.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm auto --json)
```

Oracles: `tests/test_oaw_mode.py::SwitchAndStepTests::test_default_switch_is_auto_and_auto_means_fresh_context_until_x2`, `tests/test_oaw_mode.py::SwitchAndStepTests::test_switch_positions_change_the_deep_design_review`.

Notes: Only settings and review instructions are produced. No review, model session or EGM runtime is executed.

#### estimate-review-budget

You have a saved design plan and a context document and want a rough review budget. Use oaw_mode.py egm estimate first for the plan alone and then with context, set a project token cap with egm --max-tokens, and read the estimate again.

Result: setup PASS; commands PASS; exit 0; 0.638s for setup and commands together. [stdout](.verification/logs/setups/estimate-review-budget.stdout.log) · [stderr](.verification/logs/setups/estimate-review-budget.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/docs/plans/small.md': 'x' * 2300, 'project/docs/context.md': 'y' * 105000}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm estimate docs/plans/small.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm estimate docs/plans/small.md docs/context.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm on --max-tokens 900000000 --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm estimate docs/plans/small.md docs/context.md --json)
```

Oracles: `tests/test_oaw_mode.py::SwitchAndStepTests::test_cap_and_estimate`, `tests/test_oaw_mode.py::SwitchAndStepTests::test_estimate_with_context_applies_the_cap`.

Notes: Estimates are computed locally from file sizes. They are rough estimates; this journey does not perform a review or consume model tokens.

#### record-plan-review

You are maintaining review records for a saved project plan and want to track a review session's status. With OAW installed and EGM selected for design review, use oaw_mode.py reviewed to record the session as cut and then done, and inspect suggest --plan after each record.

Result: setup PASS; commands PASS; exit 0; 0.664s for setup and commands together. [stdout](.verification/logs/setups/record-plan-review.stdout.log) · [stderr](.verification/logs/setups/record-plan-review.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/docs/plans/cache.md': '# Cache plan\n\nUse a small local cache for reports.\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm on --json)

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/oaw_mode.py reviewed docs/plans/cache.md --how egm --status cut)
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --plan docs/plans/cache.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py reviewed ./docs/plans/cache.md --how egm --report .oaw/reviews/r1/ --tokens 1200000)
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --plan docs/plans/cache.md --json)
```

Oracles: `tests/test_oaw_mode.py::SwitchAndStepTests::test_a_recorded_review_counts_only_for_the_same_file_content`.

Notes: Records synthetic review metadata only; no reviewer is started and no report directory contents are required. Record dates and report suggestions use the local date.

#### review-saved-plan

You are drafting a plan in a project folder that does not use Git yet. OAW is already installed and the plan is saved under docs/plans; use oaw_mode.py suggest --plan on its own and alongside a planned workflow path to read the recommended steps.

Result: setup PASS; commands PASS; exit 0; 0.492s for setup and commands together. [stdout](.verification/logs/setups/review-saved-plan.stdout.log) · [stderr](.verification/logs/setups/review-saved-plan.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/docs/plans/cache.md': '# Cache plan\n\nUse a small local cache for reports.\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --plan docs/plans/cache.md --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py suggest --paths .github/workflows/ci.yml --plan docs/plans/cache.md --json)
```

Oracles: `tests/test_oaw_mode.py::SwitchAndStepTests::test_a_named_plan_is_reviewed_with_or_without_git`.

Notes: Intentionally uses a project without a Git repository. --plan supplies the saved document; no agent is started.

#### choose-code-reviewer

You maintain an OAW project and want to choose the reviewer family named in its code review instructions. Start with an installed project, use oaw_mode.py second-opinion to select codex and claude in turn, inspect show standard and show deep, then select same.

Result: setup PASS; commands PASS; exit 0; 0.791s for setup and commands together. [stdout](.verification/logs/setups/choose-code-reviewer.stdout.log) · [stderr](.verification/logs/setups/choose-code-reviewer.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/oaw_mode.py second-opinion codex --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py show standard --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm off --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py show deep --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py egm auto --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py second-opinion claude --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py show deep --json)
(cd project && /usr/bin/python3 scripts/oaw_mode.py second-opinion same --json)
```

Oracles: `tests/test_oaw_mode.py::SwitchAndStepTests::test_show_follows_the_second_opinion_setting`.

Notes: Saves preferences and prints instructions only. It never executes the printed Codex or Claude commands.

#### annotate-project-topic

You are a developer adding a note to an existing project knowledge page. The page already contains a team note; use context_hub.py get, annotate and get again to read the page and add your observation.

Result: setup PASS; commands PASS; exit 0; 0.540s for setup and commands together. [stdout](.verification/logs/setups/annotate-project-topic.stdout.log) · [stderr](.verification/logs/setups/annotate-project-topic.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --profile knowledge --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/docs/knowledge/Topic.md': '# Topic\n\nProject cache notes.\n\n## AI Annotations\n\nTeam note about report caching.\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/context_hub.py get Topic)
(cd project && /usr/bin/python3 scripts/context_hub.py annotate Topic 'Cache reports after each release.')
(cd project && /usr/bin/python3 scripts/context_hub.py get Topic)
```

Oracles: `tests/test_context_hub.py::ContextHubTests::test_annotation_migrates_legacy_notes_and_refuses_meta`.

Notes: The installed helper creates an annotation timestamp and a writer-lock sidecar. Page text and commands are fixed; timestamps vary with the local date.

#### page-memory-recall

You are returning to a project and want to read its saved observations in small portions. The project has OAW and three dated memory entries; use context_hub.py memory recall with a limit and continue with the returned cursor, then read the text form.

Result: setup PASS; commands PASS; exit 0; 0.548s for setup and commands together. [stdout](.verification/logs/setups/page-memory-recall.stdout.log) · [stderr](.verification/logs/setups/page-memory-recall.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/.agents/memory.md': '# Memory\n\n---\n\n## [2026-10-28] [NOTE] needle first\nFirst project observation.\n\n## [2026-10-27] [NOTE] needle second\nSecond project observation.\n\n## [2026-10-26] [NOTE] needle third\nThird project observation.\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/context_hub.py memory recall needle --limit 1 --max-chars 900 --json) > recall-first.json
cursor="$(/usr/bin/python3 -c 'import json; print(json.load(open("recall-first.json"))["continuation"])')"
(cd project && /usr/bin/python3 scripts/context_hub.py memory recall needle --limit 1 --max-chars 900 --cursor "$cursor" --json)
(cd project && /usr/bin/python3 scripts/context_hub.py memory recall needle --max-chars 900)
```

Oracles: `tests/test_context_hub.py::ContextHubTests::test_recall_budgets_json_and_pages_independent_entries`, `tests/test_context_hub.py::ContextHubTests::test_recall_default_output_is_byte_identical`.

Notes: Continuation is obtained from the preceding JSON result, never hard-coded. Keep the memory files and recall options unchanged between these commands.

#### locate-memory-evidence

You are researching a project decision and want short pointers into memory and knowledge pages. OAW is installed, memory contains dated observations, and three knowledge pages mention the same topic; use context_hub.py memory recall --index in JSON and text forms.

Result: setup PASS; commands PASS; exit 0; 0.472s for setup and commands together. [stdout](.verification/logs/setups/locate-memory-evidence.stdout.log) · [stderr](.verification/logs/setups/locate-memory-evidence.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --profile knowledge --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/.agents/memory.md': '# Memory\n\n---\n\n## [2026-10-28] [NOTE] needle first\nFirst project observation.\n\n## [2026-10-27] [NOTE] needle second\nSecond project observation.\n\n## [2026-10-26] [NOTE] needle third\nThird project observation.\n', 'project/docs/knowledge/Titled.md': '---\ntitle: Cache Decisions\n---\n# Report cache\n\nA needle in the project notes.\n', 'project/docs/knowledge/Headed.md': '# Cache Notes\n\nA needle in another page.\n', 'project/docs/knowledge/Plain_Page.md': 'Project context\nneedle\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/context_hub.py memory recall needle --index --limit 5 --max-chars 2000 --json)
(cd project && /usr/bin/python3 scripts/context_hub.py memory recall needle --index --max-chars 900)
```

Oracles: `tests/test_context_hub.py::ContextHubTests::test_recall_index_rows_cite_match_line_and_fit_max_chars`, `tests/test_context_hub.py::ContextHubTests::test_recall_index_knowledge_page_row_uses_title_and_matched_line`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### find-project-code

You are new to a Python project and want to locate the code that joins path parts and starts an engine. OAW is installed alongside a small package and application; use code_index.py find with ordinary descriptions and identifiers, and inspect the JSON form.

Result: setup PASS; commands PASS; exit 0; 1.266s for setup and commands together. [stdout](.verification/logs/setups/find-project-code.stdout.log) · [stderr](.verification/logs/setups/find-project-code.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/pkg/__init__.py': 'from .core import Engine\n', 'project/pkg/util.py': 'RETRY_LIMIT = 3  # attempts before giving up\n\n\ndef helper_func(parts):\n    """Join path parts safely without escaping the root."""\n    return "/".join(parts)\n', 'project/pkg/core.py': 'class Engine:\n    """Drives the rotation of session keys."""\n    def start(self):\n        # kick off the first rotation\n        return self.helper()\n    def helper(self):\n        return 1\n\ndef make_engine():\n    return Engine()\n', 'project/pkg/sub/__init__.py': '', 'project/pkg/sub/deep.py': 'from ..util import helper_func as hf\nfrom .. import core\n\ndef go():\n    hf(["a"])\n    engine = core.Engine()\n    engine.start()\n', 'project/app/main.py': 'import pkg.util as u\nfrom pkg.core import Engine\n\ndef run():\n    u.helper_func(["b"])\n    Engine().start()\n    return u.RETRY_LIMIT\n', 'project/tools/runner.py': 'from app.main import run\n\ndef cli():\n    run()\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/code_index.py find 'join path parts safely' --no-cache)
(cd project && /usr/bin/python3 scripts/code_index.py find 'engine rotation' --limit 2 --no-cache --json)
(cd project && /usr/bin/python3 scripts/code_index.py find makeEngine --no-cache --json)
```

Oracles: `tests/test_code_index.py::CodeIndexTests::test_find_ranks_definitions_methods_and_lines`, `tests/test_code_index.py::CodeIndexTests::test_identifiers_split_into_stemmed_words_and_rare_words_weigh_more`.

Notes: Indexes text without running the sample application. --no-cache keeps each query independent of host cache state.

#### trace-symbol-callers

You are preparing to change a shared helper and an engine method and want to find their callers. The Python project and OAW are already present; use code_index.py callers with a dotted helper name and a method name, then inspect the JSON results.

Result: setup PASS; commands PASS; exit 0; 1.254s for setup and commands together. [stdout](.verification/logs/setups/trace-symbol-callers.stdout.log) · [stderr](.verification/logs/setups/trace-symbol-callers.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/pkg/__init__.py': 'from .core import Engine\n', 'project/pkg/util.py': 'RETRY_LIMIT = 3  # attempts before giving up\n\n\ndef helper_func(parts):\n    """Join path parts safely without escaping the root."""\n    return "/".join(parts)\n', 'project/pkg/core.py': 'class Engine:\n    """Drives the rotation of session keys."""\n    def start(self):\n        # kick off the first rotation\n        return self.helper()\n    def helper(self):\n        return 1\n\ndef make_engine():\n    return Engine()\n', 'project/pkg/sub/__init__.py': '', 'project/pkg/sub/deep.py': 'from ..util import helper_func as hf\nfrom .. import core\n\ndef go():\n    hf(["a"])\n    engine = core.Engine()\n    engine.start()\n', 'project/app/main.py': 'import pkg.util as u\nfrom pkg.core import Engine\n\ndef run():\n    u.helper_func(["b"])\n    Engine().start()\n    return u.RETRY_LIMIT\n', 'project/tools/runner.py': 'from app.main import run\n\ndef cli():\n    run()\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/code_index.py callers pkg.util.helper_func --no-cache --json)
(cd project && /usr/bin/python3 scripts/code_index.py callers Engine.start --no-cache)
(cd project && /usr/bin/python3 scripts/code_index.py callers 'pkg/core.py::Engine::helper' --no-cache --json)
```

Oracles: `tests/test_code_index.py::CodeIndexTests::test_callers_resolve_aliases_methods_and_instances`, `tests/test_code_index.py::CodeIndexTests::test_cli_json_shapes_and_exit_codes`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### follow-import-chain

You are learning how a Python command runner reaches the project's core package. The project contains an application, a runner and relative package imports; use code_index.py path with file paths and dotted module names to follow those connections.

Result: setup PASS; commands PASS; exit 0; 1.343s for setup and commands together. [stdout](.verification/logs/setups/follow-import-chain.stdout.log) · [stderr](.verification/logs/setups/follow-import-chain.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/pkg/__init__.py': 'from .core import Engine\n', 'project/pkg/util.py': 'RETRY_LIMIT = 3  # attempts before giving up\n\n\ndef helper_func(parts):\n    """Join path parts safely without escaping the root."""\n    return "/".join(parts)\n', 'project/pkg/core.py': 'class Engine:\n    """Drives the rotation of session keys."""\n    def start(self):\n        # kick off the first rotation\n        return self.helper()\n    def helper(self):\n        return 1\n\ndef make_engine():\n    return Engine()\n', 'project/pkg/sub/__init__.py': '', 'project/pkg/sub/deep.py': 'from ..util import helper_func as hf\nfrom .. import core\n\ndef go():\n    hf(["a"])\n    engine = core.Engine()\n    engine.start()\n', 'project/app/main.py': 'import pkg.util as u\nfrom pkg.core import Engine\n\ndef run():\n    u.helper_func(["b"])\n    Engine().start()\n    return u.RETRY_LIMIT\n', 'project/tools/runner.py': 'from app.main import run\n\ndef cli():\n    run()\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/code_index.py path tools/runner.py pkg/core.py --no-cache --json)
(cd project && /usr/bin/python3 scripts/code_index.py path pkg.sub.deep pkg.util --no-cache)
(cd project && /usr/bin/python3 scripts/code_index.py path pkg/util.py pkg/sub/deep.py --no-cache --json)
```

Oracles: `tests/test_code_index.py::CodeIndexTests::test_relative_imports_resolve_and_import_path_is_shortest`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### inspect-change-reach

You are planning a change to a shared Python module and want a list of nearby files to read. Start with OAW installed in the sample application and use code_index.py affected for the module and for its helper, including a two-hop view.

Result: setup PASS; commands PASS; exit 0; 1.282s for setup and commands together. [stdout](.verification/logs/setups/inspect-change-reach.stdout.log) · [stderr](.verification/logs/setups/inspect-change-reach.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/pkg/__init__.py': 'from .core import Engine\n', 'project/pkg/util.py': 'RETRY_LIMIT = 3  # attempts before giving up\n\n\ndef helper_func(parts):\n    """Join path parts safely without escaping the root."""\n    return "/".join(parts)\n', 'project/pkg/core.py': 'class Engine:\n    """Drives the rotation of session keys."""\n    def start(self):\n        # kick off the first rotation\n        return self.helper()\n    def helper(self):\n        return 1\n\ndef make_engine():\n    return Engine()\n', 'project/pkg/sub/__init__.py': '', 'project/pkg/sub/deep.py': 'from ..util import helper_func as hf\nfrom .. import core\n\ndef go():\n    hf(["a"])\n    engine = core.Engine()\n    engine.start()\n', 'project/app/main.py': 'import pkg.util as u\nfrom pkg.core import Engine\n\ndef run():\n    u.helper_func(["b"])\n    Engine().start()\n    return u.RETRY_LIMIT\n', 'project/tools/runner.py': 'from app.main import run\n\ndef cli():\n    run()\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/code_index.py affected pkg/util.py --no-cache --json)
(cd project && /usr/bin/python3 scripts/code_index.py affected 'pkg/util.py::helper_func' --hops 2 --no-cache --json)
(cd project && /usr/bin/python3 scripts/code_index.py affected 'pkg/util.py::RETRY_LIMIT' --no-cache)
```

Oracles: `tests/test_code_index.py::CodeIndexTests::test_affected_lists_importers_and_callers_with_two_hops`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### refresh-code-cache

You have been using a cached code index and have just added another function to a project module. Use code_index.py stats and find --frozen to inspect the saved index, then run find and stats normally and repeat the query.

Result: setup PASS; commands PASS; exit 0; 1.317s for setup and commands together. [stdout](.verification/logs/setups/refresh-code-cache.stdout.log) · [stderr](.verification/logs/setups/refresh-code-cache.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/pkg/__init__.py': 'from .core import Engine\n', 'project/pkg/util.py': 'RETRY_LIMIT = 3  # attempts before giving up\n\n\ndef helper_func(parts):\n    """Join path parts safely without escaping the root."""\n    return "/".join(parts)\n', 'project/pkg/core.py': 'class Engine:\n    """Drives the rotation of session keys."""\n    def start(self):\n        # kick off the first rotation\n        return self.helper()\n    def helper(self):\n        return 1\n\ndef make_engine():\n    return Engine()\n', 'project/pkg/sub/__init__.py': '', 'project/pkg/sub/deep.py': 'from ..util import helper_func as hf\nfrom .. import core\n\ndef go():\n    hf(["a"])\n    engine = core.Engine()\n    engine.start()\n', 'project/app/main.py': 'import pkg.util as u\nfrom pkg.core import Engine\n\ndef run():\n    u.helper_func(["b"])\n    Engine().start()\n    return u.RETRY_LIMIT\n', 'project/tools/runner.py': 'from app.main import run\n\ndef cli():\n    run()\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY
(cd project && /usr/bin/python3 scripts/code_index.py stats --cache ../.state/code-cache --json)
/usr/bin/python3 - <<'PY'
from pathlib import Path
p = Path('project/pkg/util.py')
p.write_text(p.read_text(encoding='utf-8') + '\n\ndef freshly_added_wombat():\n    pass\n', encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/code_index.py stats --cache ../.state/code-cache --frozen --json)
(cd project && /usr/bin/python3 scripts/code_index.py find 'freshly added wombat' --cache ../.state/code-cache --frozen --json)
(cd project && /usr/bin/python3 scripts/code_index.py find 'freshly added wombat' --cache ../.state/code-cache --json)
(cd project && /usr/bin/python3 scripts/code_index.py stats --cache ../.state/code-cache --json)
(cd project && /usr/bin/python3 scripts/code_index.py find 'freshly added wombat' --cache ../.state/code-cache --json)
```

Oracles: `tests/test_code_index.py::CodeIndexTests::test_cache_records_hashes_and_reindexes_stale_files`.

Notes: Setup intentionally creates a cache before adding a function. Frozen commands may print cache-state information on stderr while returning 0. The explicit cache directory stays inside the working folder.

#### orient-in-typescript

You are joining a TypeScript project and want a compact starting map before reading individual files. OAW is installed and the project has a package entry point and a command runner; use code_index.py overview in text and JSON forms.

Result: setup PASS; commands PASS; exit 0; 0.967s for setup and commands together. [stdout](.verification/logs/setups/orient-in-typescript.stdout.log) · [stderr](.verification/logs/setups/orient-in-typescript.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/package.json': '{\n  "name": "sample-app",\n  "main": "src/main.js",\n  "bin": {"sample": "bin/cli.js"}\n}\n', 'project/src/lib.ts': 'export class Emitter {\n    fire(value: number): void {\n        console.log(value);\n    }\n}\n', 'project/src/main.ts': 'import {Emitter} from "./lib";\nexport function run() {\n    const emitter = new Emitter();\n    emitter.fire(1);\n}\nrun();\n', 'project/bin/cli.js': '#!/usr/bin/env node\nimport {run} from "../src/main";\nrun();\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/code_index.py overview --no-cache)
(cd project && /usr/bin/python3 scripts/code_index.py overview --no-cache --json)
```

Oracles: `tests/test_code_index.py::JavaScriptIndexTests::test_overview_is_one_capped_page_of_pointers`.

Notes: Python scans the TypeScript and JavaScript as text. Node, npm and installed dependencies are not needed.

#### export-dependency-map

You want to share a local dependency map of a project containing Python and TypeScript. OAW and the sample source files are present, and an export folder is ready; use code_index.py graph to create HTML, Mermaid and JSON files and inspect a scoped map.

Result: setup PASS; commands PASS; exit 0; 1.578s for setup and commands together. [stdout](.verification/logs/setups/export-dependency-map.stdout.log) · [stderr](.verification/logs/setups/export-dependency-map.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/pkg/lib.py': 'def ping():\n    return 1\n\ndef loop():\n    return ping()\n', 'project/app/main.py': 'from pkg.lib import ping, loop\ndef run():\n    ping()\n    ping()\n    loop()\n', 'project/tests/test_main.py': 'from app.main import run\ndef test_run():\n    run()\n', 'project/src/lib.ts': 'export function ping() { return 1; }\n', 'project/src/main.ts': 'import {ping as p} from "./lib";\np(); p();\n', 'project/src/nested/orphan.ts': 'export const lone = 1;\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY
mkdir project/exports

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
(cd project && /usr/bin/python3 scripts/code_index.py graph --no-cache --format html --out exports/map.html)
(cd project && /usr/bin/python3 scripts/code_index.py graph --no-cache --format mermaid --out exports/map.mmd)
(cd project && /usr/bin/python3 scripts/code_index.py graph --no-cache --format json --out exports/map.json)
(cd project && /usr/bin/python3 scripts/code_index.py graph --no-cache --format json --scope src)
```

Oracles: `tests/test_code_index.py::DrawnGraphTests::test_exact_file_graph_reuses_index_and_keeps_tests_and_isolates`, `tests/test_code_index.py::DrawnGraphTests::test_cli_formats_stdout_files_errors_and_windows_output`.

Notes: Exports are generated locally and include an offline HTML drawing. A browser is not opened. Exported files live under project/exports.

#### preview-local-skills

You have a local folder of skills and want to see what adding them to your OAW project would involve. Start with OAW installed and the local skill files beside the project, then use oaw.py add without --apply and inspect the existing list.

Result: setup PASS; commands PASS; exit 0; 0.652s for setup and commands together. [stdout](.verification/logs/setups/preview-local-skills.stdout.log) · [stderr](.verification/logs/setups/preview-local-skills.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'local-skills/notes/SKILL.md': '---\nname: notes\ndescription: Organize project notes into a short reading list.\n---\n\nRead the notes and group them by topic.\n', 'local-skills/scripty/tool/SKILL.md': '---\nname: scripty\ndescription: Summarize a local log file.\n---\n\nRun `python3 scripts/run.py LOG`.\n', 'local-skills/scripty/tool/scripts/run.py': "print('Local log summary')\n"}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py add ./local-skills/notes ./local-skills/scripty --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py list --target ./project --json
```

Oracles: `tests/test_user_install.py::UserInstallTests::test_preview_writes_nothing_on_clean_and_installed_projects`.

Notes: The preview is noninteractive and omits --apply. It returns a question in JSON with status preview and exit 0; no skill or bundled script is run.

#### add-and-remove-skills

You are adding two locally stored skills to an OAW project, including one with a bundled script. Use oaw.py add --choice oaw --consent scripts --apply, inspect list, then remove each addition and inspect the installation with doctor.

Result: setup PASS; commands PASS; exit 0; 1.284s for setup and commands together. [stdout](.verification/logs/setups/add-and-remove-skills.stdout.log) · [stderr](.verification/logs/setups/add-and-remove-skills.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'local-skills/notes/SKILL.md': '---\nname: notes\ndescription: Organize project notes into a short reading list.\n---\n\nRead the notes and group them by topic.\n', 'local-skills/scripty/tool/SKILL.md': '---\nname: scripty\ndescription: Summarize a local log file.\n---\n\nRun `python3 scripts/run.py LOG`.\n', 'local-skills/scripty/tool/scripts/run.py': "print('Local log summary')\n"}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py add ./local-skills/notes ./local-skills/scripty --target ./project --choice oaw --consent scripts --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py list --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py remove notes --target ./project --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py remove scripty --target ./project --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py list --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_user_install.py::UserInstallTests::test_choice_oaw_on_clean_project_then_remove_one_restores_exactly`.

Notes: All additions come from local folders. Consent permits copying the bundled script; the journey never runs it. The cited oracle also exercises a broader mix of skill parts.

#### manage-only-own-skills

You want to use OAW as a manager for your own skills in a project that has no OAW installation. Add the two local skills with oaw.py add --choice only --consent scripts --apply, inspect list and doctor, then remove the additions.

Result: setup PASS; commands PASS; exit 0; 0.784s for setup and commands together. [stdout](.verification/logs/setups/manage-only-own-skills.stdout.log) · [stderr](.verification/logs/setups/manage-only-own-skills.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
mkdir project
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'local-skills/notes/SKILL.md': '---\nname: notes\ndescription: Organize project notes into a short reading list.\n---\n\nRead the notes and group them by topic.\n', 'local-skills/scripty/tool/SKILL.md': '---\nname: scripty\ndescription: Summarize a local log file.\n---\n\nRun `python3 scripts/run.py LOG`.\n', 'local-skills/scripty/tool/scripts/run.py': "print('Local log summary')\n"}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py add ./local-skills/notes ./local-skills/scripty --target ./project --choice only --consent scripts --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py list --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py remove notes --target ./project --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py remove scripty --target ./project --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_user_install.py::UserInstallTests::test_choice_only_on_clean_project_is_manager_only`.

Notes: The resulting profile manages local additions. Commands use the source checkout's oaw.py; the project does not need installed helper scripts.

#### remove-bundled-skill

You maintain an OAW project and want to remove its bundled code map skill from the installed selection. Preview oaw.py remove oaw-codemap, apply it, then inspect list and doctor.

Result: setup PASS; commands PASS; exit 0; 1.145s for setup and commands together. [stdout](.verification/logs/setups/remove-bundled-skill.stdout.log) · [stderr](.verification/logs/setups/remove-bundled-skill.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw.py remove oaw-codemap --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py remove oaw-codemap --target ./project --apply --json
/usr/bin/python3 ./oaw/scripts/oaw.py list --target ./project --json
/usr/bin/python3 ./oaw/scripts/oaw.py doctor --target ./project --json
```

Oracles: `tests/test_user_install.py::UserInstallTests::test_builtin_skill_removal_previews_then_applies`.

Notes: Offline standard-library commands. Uses only this folder for configuration, cache and temporary files; no host agent is launched.

#### catalog-local-paper

You have a locally saved PDF that you want to register in your project's OAW catalog. The project already has OAW installed; use catalog.py add with the local file URL, then read list, show and plan for the paper.

Result: setup PASS; commands PASS; exit 0; 1.398s for setup and commands together. [stdout](.verification/logs/setups/catalog-local-paper.stdout.log) · [stderr](.verification/logs/setups/catalog-local-paper.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'papers/sleep-notes.pdf': '%PDF-1.4\n% Offline sample paper\n%%EOF\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY
paper_url="$(/usr/bin/python3 -c 'from pathlib import Path; print(Path("papers/sleep-notes.pdf").resolve().as_uri())')"

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/catalog.py add "$paper_url" --target ./project --json
/usr/bin/python3 ./oaw/scripts/catalog.py list --target ./project --json
/usr/bin/python3 ./oaw/scripts/catalog.py show sleep-notes --target ./project --json
/usr/bin/python3 ./oaw/scripts/catalog.py plan sleep-notes --target ./project --json
```

Oracles: `tests/test_catalog.py::CatalogCliTests::test_a_local_pdf_is_sealed_with_metadata_from_the_file_only`.

Notes: Uses a minimal PDF-header fixture, sufficient for catalog's byte-level intake; it is never parsed or rendered. OAW_LAB_HOME is a sibling of project inside this folder. No remote source is used.

#### read-project-progress

You are checking the work recorded for an OAW project from the terminal. A progress file lists completed and waiting work, plus a task without a measured percentage; use oaw_status.py in text and JSON forms to read the summary.

Result: setup PASS; commands PASS; exit 0; 0.430s for setup and commands together. [stdout](.verification/logs/setups/read-project-progress.stdout.log) · [stderr](.verification/logs/setups/read-project-progress.stderr.log).

```bash
set -euo pipefail

# setup
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 ./oaw/scripts/oaw.py init --target ./project --json
/usr/bin/python3 - <<'PY'
from pathlib import Path
files = {'project/.oaw/progress.json': '{\n  "schema_version": 1,\n  "items": [\n    {\n      "id": "docs",\n      "title": "Review project notes",\n      "status": "done",\n      "percent": 100,\n      "basis": "Reviewed three pages"\n    },\n    {\n      "id": "release",\n      "title": "Publish release",\n      "status": "waiting",\n      "percent": 0,\n      "basis": "Awaiting maintainer"\n    },\n    {\n      "id": "research",\n      "title": "Read design options",\n      "status": "in_progress",\n      "percent": 40,\n      "basis": ""\n    }\n  ]\n}\n'}
for name, content in files.items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
PY

# setup completion marker
/usr/bin/python3 -c 'from pathlib import Path; Path(".setup-complete").touch()'

# commands
/usr/bin/python3 ./oaw/scripts/oaw_status.py --project ./project
/usr/bin/python3 ./oaw/scripts/oaw_status.py --project ./project --json
```

Oracles: `tests/test_status.py::StatusTests::test_progress_counts_and_unknown_percent`.

Notes: Reads a fixed local progress record. No running task, scheduler or model is needed; status is advisory project data.

## Unverified scope

No listed setup, terminal command sequence or cited oracle remains unverified when all counts above pass. Only the cited regression methods were run; this inventory does not claim a full-suite run. Native host discovery, live reviews, model quality and network intake are outside these offline journeys. The source snapshot has no Git metadata, so its revision label is the supplied provenance; the content digest above records the files actually read.
