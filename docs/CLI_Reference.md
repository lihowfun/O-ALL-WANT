# OAW CLI reference

Requires Python 3.10+. All runtime tools use the Python standard library. Replace `python3` with your Python executable when appropriate.

## Framework lifecycle

Run these from the OAW source checkout; `oaw.py` is not copied into target projects.

```bash
python3 scripts/oaw.py init --target PROJECT [--profile minimal|knowledge] [--host codex|claude|both] [--with-improve] [--json]
python3 scripts/oaw.py migrate --target PROJECT [--profile minimal|knowledge] [--host codex|claude|both] [--with-improve] [--apply] [--keep-custom PATH] [--json]
python3 scripts/oaw.py doctor --target PROJECT [--json]
```

Init protects different existing content; edits to a managed file are kept while its framework copy is unchanged. Profile/host additions are cumulative; codex is the default host. Migrate without `--apply` only previews. Applied migration backs up known changes and stages custom conflicts under `.oaw/proposals/`; unresolved conflicts return exit 3. Use repeatable `--keep-custom PATH` with `--apply` only after reviewing a relevant conflict to retain it as project-owned. Preflight errors/init conflicts return 2. Doctor returns 1 for an unhealthy install and 2 for invalid paths/manifests; WARN checks (edited managed files, a CLAUDE.md without `@AGENTS.md`) keep exit 0. Support does not imply host features are enabled.

The Bash wrapper invokes init on the current directory. Set `OAW_PYTHON` to select an explicit Python executable.

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

Existing experiment/state convenience commands remain in `--help` for older projects; they are not required state mirrors. Native skills use name/description and do not require custom triggers or heading conventions. The validator deliberately supports a documented subset of YAML, not every native extension field.

## Optional improvement workflow

```bash
python3 scripts/improvement.py --base-dir PROJECT propose --title TITLE --hypothesis TEXT --target PATH --patch DIFF --evaluation SPEC.json --snapshot BASE_REV
python3 scripts/improvement.py --base-dir PROJECT compare ID --baseline BASELINE.json --candidate CANDIDATE.json
python3 scripts/improvement.py --base-dir PROJECT decide ID --decision accept|reject --reason TEXT
```

Paths are project-relative. A proposal stores its concrete git text diff and fixed evaluation contract. Comparison returns eligible (exit 0), rejected (1) or inconclusive (3); malformed/mismatched inputs return 2. Eligible means ready for explicit review, not automatic approval, deployment, statistical proof, or patch application. See [SELF_IMPROVEMENT](SELF_IMPROVEMENT.md).

## Repository validation

```bash
python3 scripts/harness_check.py [--json] [--verbose]
python3 scripts/validate_skills.py [--help]
python3 scripts/sync_examples.py [--write]
```

The regression group fails when a required `tests/test_*.py` module is missing, fewer tests run than the recorded minimum, or any test is skipped. Set `OAW_ALLOW_SKIPS=1` only on a platform that cannot run a skipped case, such as a Windows host without symlink privilege.
