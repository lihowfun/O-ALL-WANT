# Lead commands — whole stage in order

Use `/usr/bin/python3`, stdlib only. Preparation makes no model calls and never
opens the key. The commands below are for the lead after offline preparation.
All raw state/maps/grades/credentials remain private on local HOME storage.
No external shared Claude work may race with these commands. Stop on nonzero;
never substitute a new grader or redraw a terminal attempt.

Export EGMCAL_RUNTIME_ROOTS (os.pathsep-separated) with each CLI's own self-contained runtime folder, holding CLI files only;
exactly one folder must contain the CLI in use and must not be HOME, an ancestor of HOME, or a system root. Escaping symlinks are refused. The folder is mounted read-only at /opt/egmcal-runtime; it is never guessed.

Set these inputs in a clean shell (unexpected nonempty API/provider credentials
are refused, not silently removed). CLI resolved bytes/versions must remain
Claude 2.1.322 and Codex 0.167.2. Set KEY to the already corrected frozen key.
STAGE_SPENT and EXPERIMENT_SPENT cover Claude spending OUTSIDE PRIVATE only;
exclude imported/internal charges and keep experiment >= stage. Record Codex
curator work separately through --add-shared. The script computes grading
reserves; there is no --reserve input. Per-request allowance is 150,000 logical
tokens before any Claude-family grader request is observed in PRIVATE, then
max(150,000, ceil(1.3 × largest observed Claude-family grading/reconciliation
request in PRIVATE)). Remaining reserve = remaining design requests × allowance.
N2 always reserves five batch-2 requests: four reports plus one reconciliation.
Preflight and pre-batch-1 native launches reserve nine slots (3+1, then 4+1).
Grader/reconciliation launches reserve the unsettled design slots, excluding
the current Claude request and retaining the five conditional batch-2 slots
while in batch 1. A completed round closes its unused reconciliation slot;
C1 or terminal NC5 closes the conditional batch-2 slots. Reserve is never spending.

```bash
export PYTHONDONTWRITEBYTECODE=1
: "${PACKET:?}" "${CLAUDE_CLI:?}" "${CODEX_CLI:?}" "${CLAUDE_AUTH_FILE:?}" "${CODEX_AUTH_FILE:?}"
: "${KEY:?}" "${STAGE_SPENT:?}" "${EXPERIMENT_SPENT:?}"
PRIVATE="$HOME/oaw-egmcal/issue20"
GATE="$PRIVATE/gate.json"
KEY_SHA256=6d7497e90b9baf7f872bfd04c4750fee77a523e69169fd840d48df02d8e1f99e
ELIGIBLE_PRIMARY_COUNT=9
FREEZE_SHA256=$(/usr/bin/python3 freeze_tools.py --check)
umask 077
mkdir -p "$PRIVATE"
/usr/bin/python3 -c 'import secrets; print(secrets.token_hex(32))' > "$PRIVATE/outside-probe.txt"
OUTSIDE_PROBE="$PRIVATE/outside-probe.txt"
```

The lead supplies ELIGIBILITY_COST: a private JSON record with schema_version 1,
id/charge_ids unique, freeze_sha256 equal to FREEZE_SHA256, provider claude,
stage curation, logical_tokens 3398755, noncache_tokens 359512, measured seconds,
metering_complete true, subagents_included true (none omitted), subagents "none",
metering_source "session transcript", evidence_sha256 containing the complete
session-transcript evidence hash. The checker has ALREADY spent this usage;
import once, do not launch it again. Do not invent wall time or evidence hashes.
The lead also supplies CURATOR_COST separately for Codex curator usage.

Define these helpers once. They are ordinary explicit commands, not automatic
branch execution. `grade_paths` computes names from the anonymous index hash;
no private map is opened. `grade_batch` launches both graders, Codex once and
Claude once per report. `reconcile_batch` launches the single round (zero calls
if no primary differences), freezes even an empty overlay, and never unblinds.
`score_batch` is the first command allowed to open that batch's PRIVATE-MAP.

```bash
native() {
  cell="$1"; arm="$2"
  if [ "$cell" = codex ]; then cli="$CODEX_CLI"; auth="$CODEX_AUTH_FILE"
  else cli="$CLAUDE_CLI"; auth="$CLAUDE_AUTH_FILE"; fi
  /usr/bin/python3 cal_run.py native --cell "$cell" --only "$arm" \
    --packet "$PACKET" --out "$PRIVATE" --cli "$cli" --auth-file "$auth" --gate "$GATE" \
    --budget 15000000 --spent "$STAGE_SPENT" --experiment-spent "$EXPERIMENT_SPENT"
}
grade_paths() {
  BLIND="$PRIVATE/blind$1"
  BIND=$(/usr/bin/python3 -c 'import sys; from cal_common import load,sha,canonical; print(sha(canonical(load(sys.argv[1])))[:12])' "$BLIND/index.json")
  GRADE_A="$PRIVATE/grade-$BIND-codex.json"
  GRADE_B="$PRIVATE/grade-$BIND-claude.json"
  RESOLUTION="$PRIVATE/resolution-batch$1.json"
}
grade_batch() {
  grade_paths "$1"
  /usr/bin/python3 cal_grade.py run-grader --family codex --state "$PRIVATE" --blind "$BLIND" \
    --packet "$PACKET" --key "$KEY" --gate "$GATE" --cli "$CODEX_CLI" --auth-file "$CODEX_AUTH_FILE" \
    --budget 15000000 --spent "$STAGE_SPENT" --experiment-spent "$EXPERIMENT_SPENT" || return
  /usr/bin/python3 cal_grade.py run-grader --family claude --state "$PRIVATE" --blind "$BLIND" \
    --key "$KEY" --gate "$GATE" --cli "$CLAUDE_CLI" --auth-file "$CLAUDE_AUTH_FILE" \
    --budget 15000000 --spent "$STAGE_SPENT" --experiment-spent "$EXPERIMENT_SPENT"
}
reconcile_batch() {
  grade_paths "$1"
  /usr/bin/python3 cal_requests.py --state "$PRIVATE" --blind "$BLIND" --packet "$PACKET" --key "$KEY" \
    --grade-a "$GRADE_A" --grade-b "$GRADE_B" --gate "$GATE" \
    --codex-cli "$CODEX_CLI" --claude-cli "$CLAUDE_CLI" \
    --codex-auth-file "$CODEX_AUTH_FILE" --claude-auth-file "$CLAUDE_AUTH_FILE" \
    --budget 15000000 --spent "$STAGE_SPENT" --experiment-spent "$EXPERIMENT_SPENT" \
    --out "$RESOLUTION"
}
score_batch() {
  batch="$1"; grade_paths "$batch"
  if [ "$batch" = 2 ]; then set -- --previous "$PRIVATE/decision-batch1.json"
  else set --; fi
  /usr/bin/python3 cal_grade.py score --key "$KEY" --grade-a "$GRADE_A" --grade-b "$GRADE_B" \
    --index "$BLIND/index.json" --private-map "$BLIND-PRIVATE-MAP.json" --state "$PRIVATE" \
    --resolution "$RESOLUTION" --accounting "$ACCOUNTING" --out "$PRIVATE/decision-batch$batch.json" "$@"
}
```

One ordered command list for the whole stage:

1. Import already-spent checker and curator costs, then preflight both cells.
   No packet/key goes to preflight probes. Check each private proof; fail or
   could-not-determine keeps the gate closed. Dry preflight never authorizes it.

   ```bash
   /usr/bin/python3 cal_ledger.py --state "$PRIVATE" --add-shared "$ELIGIBILITY_COST" --eligibility-check
   /usr/bin/python3 cal_ledger.py --state "$PRIVATE" --add-shared "$CURATOR_COST"
   /usr/bin/python3 cal_run.py preflight --cell codex --out "$PRIVATE" --cli "$CODEX_CLI" --auth-file "$CODEX_AUTH_FILE" --outside-probe "$OUTSIDE_PROBE" --spent "$STAGE_SPENT" --experiment-spent "$EXPERIMENT_SPENT"
   /usr/bin/python3 cal_run.py preflight --cell claude --out "$PRIVATE" --cli "$CLAUDE_CLI" --auth-file "$CLAUDE_AUTH_FILE" --outside-probe "$OUTSIDE_PROBE" --spent "$STAGE_SPENT" --experiment-spent "$EXPERIMENT_SPENT"
   ```

2. Lead freezes the settled key/eligibility record and preparation bytes, then
   builds the gate from measured preflight evidence. Gate helper never reads key.

   ```bash
   /usr/bin/python3 cal_run.py gate --out "$PRIVATE" --gate "$GATE" --claude-cli "$CLAUDE_CLI" --codex-cli "$CODEX_CLI" --key-sha256 "$KEY_SHA256" --eligible-primary-count "$ELIGIBLE_PRIMARY_COUNT" --freeze-sha256 "$FREEZE_SHA256"
   ```

3. Complete Codex N1 and N2, in order. No merge.

   ```bash
   native codex N1
   native codex N2
   ```

4. Run Claude N1 only. The runner refuses it before Codex N1/N2 complete.

   ```bash
   native claude N1
   ```

5. Pack exactly three reports as batch 1; withhold the separate private map.
   Packing recursively rewrites the attempt workspace, fresh HOME and state-root
   prefixes to packet-relative paths in all findings/uncertainties strings before
   hashing. Original reports remain untouched; the private map records each
   rewrite count. Packing and grader input checks reject the state root, attempt
   IDs, or codex/claude/N1/N2 path components in the blind folder.

   ```bash
   /usr/bin/python3 cal_grade.py pack --batch 1 --state "$PRIVATE" --out "$PRIVATE/blind1"
   ```

6. Grade all three with both graders. Claude receives no packet argument.

   ```bash
   grade_batch 1
   ```

7. Complete the one blind reconciliation round and freeze resolution before
   opening batch 1's map. Keep raw initial grades unchanged.

   ```bash
   reconcile_batch 1
   ```

8. Update a private accounting.template.json copy from usage evidence covering
   all work so far (including imported checker/curator). Set ACCOUNTING to it;
   do not claim conditional future work already happened. Score batch 1. Codex
   is decided; Claude is C1 on N1 or awaits the funded N2 branch.

   ```bash
   score_batch 1
   ```

9. Invoke the runner's conditional Claude N2 command. It reads the audited,
   reconciled decision-batch1.json, skips N2 on C1, otherwise applies exactly
   stage spent + 1.3×N1 actual + remaining Claude grading reserve <=15M (and
   the 30M cap). The remaining reserve is computed as five times the allowance
   above; the lead cannot choose it after seeing batch-1 results. NC5 writes claude-sequential.json, starts no attempt, and
   instructs the lead to report measured unit cost to the owner. On C1 or NC5,
   skip steps 10–13 and go to ledger. For NC5, also run the offline command below
   to record the final NC5 outcome without overwriting the runner-bound batch-1
   score. Only proceed to batch 2 if a completed Claude N2 row exists.

   ```bash
   native claude N2
   # On NC5 only (no new model work):
   grade_paths 1
   /usr/bin/python3 cal_grade.py score --key "$KEY" --grade-a "$GRADE_A" --grade-b "$GRADE_B" --index "$BLIND/index.json" --private-map "$BLIND-PRIVATE-MAP.json" --state "$PRIVATE" --resolution "$RESOLUTION" --accounting "$ACCOUNTING" --out "$PRIVATE/decision-final.json"
   ```

10. If Claude N2 completed, pack it and the exact three batch-1 reports under new
    anonymous IDs and new fixed seed. New graders must not receive batch-1 data
    other than those anonymised repeated reports.

    ```bash
    /usr/bin/python3 cal_grade.py pack --batch 2 --state "$PRIVATE" --out "$PRIVATE/blind2"
    ```

11. Fresh grader sessions label all four reports.

    ```bash
    grade_batch 2
    ```

12. One reconciliation round for batch 2, before opening its map.

    ```bash
    reconcile_batch 2
    ```

13. Refresh ACCOUNTING from all usage evidence. Score with immutable batch-1
    result: Codex validity, completeness and decision remain final; later accounting
    failure can invalidate them. Claude N1 validity and labels are carried from
    batch 1. Only new Claude N2 labels enter its decision; repeated reports give
    independent-label test–retest figures. If N2 failed, do not pack a missing
    report: re-score batch 1 to decision-final.json as in step 9; it emits NC1
    because N2 was launched and is incomplete. Preserve failed costs.

    ```bash
    score_batch 2
    ```

14. Produce ledger including preflight, failed attempts, all per-request grading,
    reconciliation, checker, curator and external shared work. An unsettled
    native/grader/reconciliation intent counts as launched with unknown final
    cost; retain its observed usage lower bound. A Claude N2 intent means N2 was
    launched. Scoring gives NC1 until usage is recovered and an audited row is
    appended; an existing accounting audit cannot override this. Report measured
    native unit cost beside the single historical 18,480,203-token full-EGM run
    (2026-11-07) and plain ratio, explicitly not a quality comparison. No EGM
    command follows.

    ```bash
    /usr/bin/python3 cal_ledger.py --state "$PRIVATE"
    ```

Offline verification only (may be run during preparation):

```bash
export PYTHONDONTWRITEBYTECODE=1
/usr/bin/python3 build_packet.py "$PACKET"
/usr/bin/python3 freeze_tools.py --check
/usr/bin/python3 -m unittest -v
/usr/bin/python3 cal_run.py native --cell codex --packet "$PACKET" --out .dry-hostwrite --dry-run
/usr/bin/python3 cal_run.py native --cell claude --only N1 --packet "$PACKET" --out .dry-hostwrite --dry-run
/usr/bin/python3 cal_run.py native --cell claude --only N2 --packet "$PACKET" --out .dry-hostwrite --dry-run
```

Repeat native dry commands: exactly two immutable rows per cell. Dry N2 creates
only synthetic wiring, bypasses the real scored funding gate, never calls a CLI,
and cannot enter grading. Unit tests use invented keys/hosts to exercise both
batch branches, grader/reconciliation plans, complete usage and failure handling.
Final usage on both hosts requires every token counter to be present and an
integer, with nonzero usage in at least one bucket for output-producing runs.
Missing/empty/invalid buckets retain observed lower bounds and mark native,
grader and reconciliation metering incomplete. Offline tests do not certify real
CLI flags, authentication, sandbox or metering.


## Host launch flags after real preflight fixes (2026-11-14)

Every inference path uses the following external-feature restrictions, including
study/native runs, merge (where retained), graders, reconciliation (where present)
and built-in preflight. No existing user or project settings are loaded. Fresh
HOME contains only the explicit subscription credential and fresh runtime state;
no plugin directories or MCP configs are mounted/copied. Runtime must be a
lead-supplied dedicated folder holding CLI files only. The outer namespace keeps
model transport networking; model shell commands use the CLI network-off sandbox.
No real CLI was exercised offline for this revision; the next preflight must
confirm CLI flag acceptance, nested command sandbox, report writes, billing,
metering and tool-surface removal. Old runner-bound proofs are invalidated.

Codex common base (MODEL is pinned per launch kind), plus every restriction below:

```text
exec --json --model MODEL -c 'model_reasoning_effort="high"'
-c sandbox_workspace_write.network_access=false
-c sandbox_workspace_write.exclude_slash_tmp=true
-c sandbox_workspace_write.exclude_tmpdir_env_var=true
--sandbox workspace-write --skip-git-repo-check --ignore-user-config
--cd /home/dev/proj -
-c features.apps=false
-c features.plugins=false
-c features.remote_plugin=false
-c features.plugin_discovery_prefetch=false
-c features.browser_use=false
-c features.browser_use_external=false
-c features.browser_use_full_cdp_access=false
-c features.in_app_browser=false
-c features.computer_use=false
-c features.skill_mcp_dependency_install=false
-c 'mcp_servers={}'
-c 'web_search="disabled"'
```

Codex native/merge/preflight use MODEL=gpt-6.1-sol; grader and reconciliation
use MODEL=gpt-6-astra. Shell/skill discovery is left enabled for all these Codex
paths because the grader/reconciler writes the requested JSON using packet
files. No shell/multi-agent feature is globally disabled.

Claude common flags:

```text
-p --output-format stream-json --verbose --model MODEL --effort high
--permission-mode acceptEdits --setting-sources ''
--strict-mcp-config --mcp-config '{"mcpServers":{}}'
--settings /home/dev/settings.json --no-session-persistence
```

Claude native/merge add the prompt argument and
`--tools Read,Write,Glob,Grep,Agent,Skill`, MODEL=claude-opus-5-5. Claude per-report
grading/reconciliation use MODEL=claude-fable-5-2, `--tools ''`, with the inline
prompt on stdin. Settings set `enabledPlugins={}`, `disableAllHooks=true` and
permissions deny WebSearch, WebFetch, Edit and reads of fresh HOME auth/config
paths. The per-attempt workspace copy is writable so the CLI can create its
protected-path mount points; native source integrity is enforced by the unchanged
instruction plus before/after inventory and packet digest checks. The launcher does not pass
`--plugin-dir`; with fresh HOME, empty settings sources and empty enabledPlugins,
there are no plugins to load. It leaves Skill available for native review.

`cal_launch.py` is the real shared launcher for both hosts. The obsolete
`cal_sandbox.py` is removed, including from the freeze list; offline tests now
exercise bubblewrap. Shell commands and patch writes must work under the CLI's nested sandbox;
the source overwrite must succeed and be detected; outside reads must be refused.
The probe names `cat`/Read for
the outside path, curl with a five-second timeout, and a web-tool attempt.
Claude preflight alone adds Bash to make the concrete curl attempt observable:
`--tools Read,Write,Glob,Grep,Bash,Agent,Skill`, MODEL=claude-opus-5-5. Its settings
enable the Bash sandbox, autoAllowBashIfSandboxed=true,
allowUnsandboxedCommands=false and network.allowedDomains=[]. Native/merge still
deny Bash and retain the original listed tools. The harmless probe intentionally
modifies source.py to exercise the post-run integrity checker. Web tools remain
excluded in every launch. Missing attempts still keep the gate closed.

Web checks inspect native shell, MCP and hosted search/browse results. Any
successful remote call/content fails even when another record is ambiguous.
An observed DNS/refusal/unavailable error passes both no-success and attempt
checks. Missing attempts or unresolved results are could-not-determine. The real
egmcal-3 hosted call is now a failing fixture. Trimming is documented in
fixtures/host-preflight/README.md. Each failed/undetermined preflight check prints
its name, status and reason on one line; inspect private traces for details.

After the fifth pre-data host fix, rerun both real preflights in new private state;
carry forward all previous failed-preflight usage. Confirm shell commands and
apply_patch actually execute, report.json is valid, `source_change_detected` and
`other_sources_unchanged` both pass, outside reads remain denied, and curl returns
a conclusive refusal/DNS failure with `no_web_tool_succeeded: pass`. A refused
source overwrite now fails: it does not exercise detection. The intentional probe
mutation is recorded in usage as `isolation_complete=false`, with source.py in
`source_changed_paths`; gate authorization uses the explicit preflight checks.
Native packet mutations instead produce terminal `status="isolation incomplete"`
and `retryable=false`, listing all changed paths and recording
`packet_sha256_before`/`packet_sha256_after`. Never repair and redraw that attempt.
Only new empty top-level `.git`, `.agents`, `.codex`, `.aws` directories, including
empty directory mount stubs, may accompany review_out; inspect the per-attempt
`sandbox_placeholders` list. Contents, regular-file stubs, links, other new
directories and changes to existing packet entries are violations. These names
come from U2's listing and the installed pinned CLI's protected-path builder;
see fixtures/host-preflight/README.md. Grader input inventories remain strict.
Old proofs/gates bind earlier runner bytes and cannot authorize this revision.
Offline verification for this revision: 81 tests pass (six new regressions in
`tests/test_hostwrite.py`); native dry runs in `.dry-hostwrite` produce two rows
per cell and repeating all four commands adds none. Both dry preflights in
`.dry-preflight-hostwrite` retain undetermined checks and zero-token usage.
The dry verification forbids subprocess creation and confirms all six plans have
`calls_model=false`. Use new dry state roots for another verification. No real
preflight, model call or gate authorization was performed for this revision.

CLI identity discovery runs only `CLI --version`, in a separate fresh bubblewrap
namespace with no subscription credential and fresh HOME. It
cannot load operator config. The command is only `--version`, with no tools or prompt. Dry commands skip even this
identity launch. Version discovery is not an inference launch.
