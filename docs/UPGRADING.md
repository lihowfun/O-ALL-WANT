# Upgrade to OAW v2.0.0

v2.0.0 is a proposed breaking upgrade. Review and merge happen separately; no tag or release is implied by the version field.

## What changes

| v1 default | v2 behavior |
|---|---|
| CLAUDE.md master router, mandatory startup files and lanes | Short AGENTS.md plus a thin Claude compatibility import; task-relevant reads |
| Flat `.agents/skills/*.md`, custom triggers | Native `<name>/SKILL.md` packages |
| Broad template collection and manually maintained state mirrors | Minimal five-file framework; knowledge and improvement are explicit additions |
| Mandatory memory/report/self-review instructions | Selective project evidence; native personal memory stays with the host |
| Installer overwrite confirmation | Non-overwriting init; migration preview, backups and conflict proposals |
| Framework metadata in project VERSION.json | Framework ownership lives in `.oaw/install.json`; project version stays yours |
| Frozen evidence tiers/do-not-rerun rules | Scope, source and reproducible validation; no permanent runtime freeze |

Python 3.10+ is now required. The runtime still has no pip dependencies. Current host capabilities must be checked separately from whether they are enabled. OAW does not modify host settings, run another agent loop, or guarantee native skill discovery just because files pass schema checks.

## Preview and apply

Run from the new framework checkout:

```bash
python3 scripts/oaw.py migrate --target /path/to/project --json
python3 scripts/oaw.py migrate --target /path/to/project --apply --json
python3 scripts/oaw.py doctor --target /path/to/project --json
```

Use `--profile knowledge` to add wiki tools/stubs and `--with-improve` to add the optional improvement workflow. `--host codex` is the default; choose `--host claude` or `--host both` for the corresponding native skill folders. Profile and host additions persist on later operations; a default command does not remove them.

The preview makes no changes. Applied migration recognizes committed v1 template/script hashes in LF or CRLF form, or unchanged files from the previous v2 manifest. Only those known framework files can be replaced automatically. Unchanged legacy flat skills and old adapters can be retired to backup. Unknown/custom files remain in place.

Existing `.agents/memory.md`, raw/knowledge pages, AI_CONTEXT.md, ROADMAP.md and root VERSION.json are preserved. Wiki stubs are seed-only, never replacement-managed. An existing custom CLAUDE.md may still contain v1 rules; review its proposal before assuming the old behavior is gone.

## Resolve a custom policy conflict

Conflicts return exit 3 after safe changes/proposals are recorded; doctor stays unhealthy until resolved. Inspect `.oaw/proposals/OPERATION/` and the receipt before choosing either path:

- Adopt the proposed framework file after reviewing it, then rerun migration.
- Merge the useful changes into your custom file, then explicitly keep it project-owned:

```bash
python3 scripts/oaw.py migrate --target /path/to/project --apply --keep-custom CLAUDE.md
```

Repeat `--keep-custom` for additional reviewed conflict paths. It does not edit those files or claim they match framework policy; future migration preserves them. It is only valid with `--apply` and for relevant package conflicts/custom paths. Keep the file type and any native skill schema valid.

## Backups and recovery

Each applied migration keeps replacement/retirement bytes and a migration.json receipt under `.oaw/backups/OPERATION/`. Existing file modes are retained; failed writes roll back already applied payload changes while keeping recoverable backups. Unresolved custom proposals are separate from the backup.

Before manual recovery, stop installation/writers, inspect the receipt and preserve any work performed since migration. Restore only the intended files from that operation's backup; do not blindly copy a whole directory over a project. Init has no force-overwrite option. A stale install.lock after a killed operation requires inspection before removal.

## Native skills

Codex's project path is `.agents/skills`; Claude Code's native project skills path is `.claude/skills`. The Claude policy import does not register skills. Use `--host` to generate the selected native packages, then verify the actual listing in each host. See [Skill Guide](Skill_Guide.md).

Customized v1 flat workflows are preserved as files, but their format is not native registration. Migrate worthwhile workflows deliberately; do not bring back always-active logging or generic rules that the host already handles.

## What was taken from the Hermes branch

The complete read-modify-write locking fix was adapted into a shared, stable-sidecar/atomic-write helper and tested. The branch was not merged wholesale. Mandatory nudges, manually reported usage counters and step-count skill review are not part of v2. Bounded recall is implemented independently with source positions and continuation.

Historical experiment results remain available in Git history/docs/archive. v2 has no verified native-model quality or cost improvement claim until representative matched A/B runs are captured.
