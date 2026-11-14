# Upgrade to OAW v2.0.1

v2.0.1 is the first release of the V2 line and a breaking upgrade from v1. It also supports existing 2.0.0-proposal installs through the normal migration preview and `--apply` path, preserving project records and customized policy. 2.0.0 was a proposal that was never released.

## What changes

| v1 default | v2 behavior |
|---|---|
| CLAUDE.md master router, mandatory startup files and lanes | Short AGENTS.md plus a thin Claude compatibility import; task-relevant reads |
| Flat `.agents/skills/*.md`, custom triggers | Native `<name>/SKILL.md` packages |
| Broad template collection and manually maintained state mirrors | Short policy plus complete pinned EGM and evidence; wiki and improvement are explicit additions |
| Mandatory memory/report/self-review instructions | Selective project evidence; native personal memory stays with the host |
| Installer overwrite confirmation | Non-overwriting init; migration preview, backups and conflict proposals |
| Framework metadata in project VERSION.json | Framework ownership lives in `.oaw/install.json`; project version stays yours |
| Frozen evidence tiers/do-not-rerun rules | Scope, source and reproducible validation; no permanent runtime freeze |

Python 3.10+ is now required. The runtime still has no pip dependencies. Current host capabilities must be checked separately from whether they are enabled. Framework init/migrate do not configure host runtimes or guarantee native discovery just because files pass schema checks. User-selected packages may add project hooks/MCP settings only through the separate add consent flow.

## FIXCHECK disposition (2026-11-13)

M1 (session-end saving), M2 (empty-recall host guidance) and R2 (one deep
code-review round) were implemented, failed the preregistered regression
thresholds in the one FIXCHECK check, and were reverted. M3 (permission-only
pending memory), R1 (native same-family Codex review with explicit cross-family
commands) and the #18 literal-path audit fix ship.

FIXCHECK uses frozen H1 diagnostic tasks, the O arm and one counted answer per
task. All 24 rows are counted and the frozen calculator reports `fail`: two
small-change token limits (`codex/t01`, `claude/t12`) and both cells' memory
thresholds. With one answer per task, neither these failures nor the
differences measured in the other direction can be separated from run-to-run
variation; this is a regression gate, not an effectiveness verdict.
[Result record](https://github.com/lihowfun/O-ALL-WANT/blob/e05c4d5a9238fe3ef4529552a27ce9095ead6a3b/records/v2.0.1-experiments/FIXCHECK/RESULT.md) ·
[Disposition and validation](validation/v2.0.1-final.md).

The save policy again says to save when requested or when a decision would be
difficult to reconstruct; the evidence skill appends only the requested durable
finding. Empty recall prints `No matches found.` and adds no host-memory guidance
or JSON `message`/`next_action`. Deep code review repeats until no new findings,
at most three rounds; standard remains one round. M3 pending notes are retained
and read alongside primary memory; no records are migrated or deleted. Existing
custom policy remains protected by the migration conflict rules below.

## Checkout locator and doctor output

Default init, migrate and add leave the optional user-level locator unchanged. Use `--remember-checkout` only if you want OAW to record its checkout outside this project; the [CLI reference](CLI_Reference.md#optional-checkout-locator) lists exact destinations and preview/apply behavior. The add terminal includes this choice in its existing question. An existing locator is not deleted when you decline. Doctor now summarizes checks by default while showing every warning/failure and native discovery state; `--verbose` and `--json` retain full details.

## Preview and apply

Run from the new framework checkout:

```bash
python3 scripts/oaw.py migrate --target /path/to/project --json
python3 scripts/oaw.py migrate --target /path/to/project --apply --json
python3 scripts/oaw.py doctor --target /path/to/project --json
```

Use `--profile knowledge` to add wiki tools/stubs and `--with-improve` to add the optional improvement workflow. `--host codex` is the default; choose `--host claude` or `--host both` for the corresponding native skill folders. Profile and host additions persist on later operations; a default command does not remove them.

The preview makes no changes. Applied migration recognizes committed v1 template/script hashes in LF or CRLF form, or unchanged files from the previous v2 manifest. Only those known framework files can be replaced automatically. Unchanged legacy flat skills and old adapters can be retired to backup. Unknown/custom files remain in place. Your edits to a managed file are kept while the framework copy is unchanged; doctor warns, and a later framework change to that file becomes a conflict proposal.

Existing `.agents/memory.md`, raw/knowledge pages, AI_CONTEXT.md, ROADMAP.md and root VERSION.json are preserved. Wiki stubs are seed-only, never replacement-managed. An existing custom CLAUDE.md may still contain v1 rules. If it does not import `@AGENTS.md`, migration also keeps the v1 AGENTS.md pointer and stages both as paired conflicts, so Claude and Codex keep following the same policy until you resolve them.

## Resolve a custom policy conflict

Conflicts return exit 3 after safe changes/proposals are recorded; doctor stays unhealthy until resolved. Inspect `.oaw/proposals/OPERATION/` and the receipt before choosing either path:

- Adopt the proposed framework file after reviewing it, then rerun migration.
- Merge the useful changes into your custom file, then explicitly keep it project-owned:

```bash
python3 scripts/oaw.py migrate --target /path/to/project --apply --keep-custom CLAUDE.md
```

Repeat `--keep-custom` for additional reviewed conflict paths. It does not edit those files or claim they match framework policy; future migration preserves them. It is only valid with `--apply` and for relevant package conflicts, edited managed files or custom paths. Keeping a CLAUDE.md without an `@AGENTS.md` import also requires a decision on its paired AGENTS.md (adopt the proposal or `--keep-custom AGENTS.md`); doctor then warns that Claude and Codex may follow different policy. Keep the file type and any native skill schema valid.

## Backups and recovery

Each applied migration keeps replacement/retirement bytes and a migration.json receipt under `.oaw/backups/OPERATION/`. Existing file modes are retained; failed writes roll back already applied payload changes while keeping recoverable backups. Unresolved custom proposals are separate from the backup.

Before manual recovery, stop installation/writers, inspect the receipt and preserve any work performed since migration. Restore only the intended files from that operation's backup; do not blindly copy a whole directory over a project. Init has no force-overwrite option. A stale install.lock after a killed operation requires inspection before removal.

## Native skills

V2 includes EGM 0.1.0 at commit
`f0ba151b252c9abf1318d9fe857a43265d06de89`, installed under
`.oaw/integrations/egm/` whenever the recipe selects an EGM skill. Seven EGM entrypoints plus `oaw-add`, `oaw-codemap`, `oaw-evidence` and `oaw-review` are the default
recipe. Upstream manual invocation is preserved; inclusion does not force a
nine-stage review after ordinary tasks. Claude installs also receive the nine
upstream native agent adapters with their original tool/context restrictions.

Inspect available choices with `python3 scripts/oaw.py skills --target PROJECT`.
For a custom recipe, preview
`python3 scripts/oaw.py migrate --target PROJECT --skills egm-review,oaw-evidence`;
apply with `--apply`. Unmodified owned entrypoints are backed up before removal.
Edited entrypoints remain conflicts; they are never silently discarded. `none`
selects no bundled native skills; `default` restores the profile defaults. An
omitted flag preserves a prior custom recipe. Project memory remains installed.
A recipe without any EGM skill also retires the pinned runtime, the Claude
native agents and the EGM sentences of an unedited `AGENTS.md`, with the same
backups; an edited policy or runtime file stays a conflict. Selecting an EGM
skill again reinstalls them. This recipe selection manages bundled skills. Use `oaw.py add / list / remove`
for external packages; their receipt, consent and removal behavior are described in the
[CLI reference](CLI_Reference.md#your-own-skills-add-list-remove).

Codex's project path is `.agents/skills`; Claude Code's native project skills path is `.claude/skills`. The Claude policy import does not register skills. Use `--host` to generate the selected native packages, then verify the actual listing in each host. See [Skill Guide](Skill_Guide.md).

Customized v1 flat workflows are preserved as files, but their format is not native registration. Migrate worthwhile workflows deliberately; do not bring back always-active logging or generic rules that the host already handles.

## Stricter lint after the unreleased citation check

`wiki_sync.py lint` now warns about backticked `path::Symbol` code citations in raw notes and manual pages that do not resolve (OAW-21). Like every soft warning, these are errors under `lint --strict`, so a project that runs `--strict` in CI can start failing after the upgrade. Fix or remove the citation, or move an example into a fenced code block; default `lint` still exits 0. See [code citations](Wiki_Sync_Guide.md#code-citations).

## What was taken from the Hermes branch

The complete read-modify-write locking fix was adapted into a shared, stable-sidecar/atomic-write helper and tested. The branch was not merged wholesale. Mandatory nudges, manually reported usage counters and step-count skill review are not part of v2. Bounded recall is implemented independently with source positions and continuation.

Historical experiment results remain available in Git history/docs/archive. v2 has no verified native-model quality or cost improvement claim until representative matched A/B runs are captured.

## EGM upstream guides

The source checkout bundles [getting started](../vendor/egm/docs/getting_started.md), [Codex](../vendor/egm/docs/codex.md), [Claude](../vendor/egm/docs/claude.md) and [supported environments](../vendor/egm/docs/harnesses.md) at the EGM revision recorded above. After installation, use the corresponding files in `.oaw/integrations/egm/docs/`. Native entrypoints resolve to the bundled runtime; upstream relative references resolve from their own document directory.
