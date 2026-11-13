# OAW 2.0.1 release review, round 2 (Claude, cross-family)

Scope: `b898e4d..73fb8f7` (b4ca559 + 73fb8f7) in `OAW-review-r2`, left unmodified.
All experiments ran on clones in a scratch directory: `73fb8f7`, `b898e4d` (round-1 state) and `359e6e3`
(pre-D45 baseline). Interpreter: `/usr/bin/python3` 3.10.12 with `PYTHONDONTWRITEBYTECODE=1`, on Linux x86_64.
Some stdlib behaviour was also checked with local 3.11.14, 3.12.12 and 3.14.0 interpreters. Windows and macOS
were not available. Windows statements say whether they are emulated (real stdlib code, `sys.platform` patched)
or traced by reading.

Gate on the `73fb8f7` clone (Linux, 3.10.12): 9/9 checks, 716 tests, 0 skipped. The affected test modules
(context_hub, wiki_sync, cli_resolve, doctor_probe, user_install, gate) also pass on 3.14.0 (205 tests).

## 1. Closure

"Reverted" means that I undid that fix in the clone, re-ran its new tests, saw them fail, and restored the fix.

| id | verdict | evidence | reverted and confirmed |
|---|---|---|---|
| R1-01 | closed | The new test is the reported scenario: a shared `common.py` that already had project bytes, `--consent hooks` and then `--consent all`. Receipt and backup keep the original bytes and `remove` restores them. Five extra scenarios also pass: a second addition that fails while writing the record rolls back to an identical tree; a first addition that fails rolls back and a clean retry works; removing the parts in either order restores the original; add, remove, add again works; a partial remove followed by `--force` restores the original and a re-add is not blocked. | yes: `user_install.py` set back to b898e4d makes all 3 new tests fail |
| R1-02 | closed | `test_restore_aborts_when_migration_keeps_new_custom_policy_before_lock` runs `migrate --apply --keep-custom AGENTS.md` between capture and lock, which is the reported interleaving. Restore aborts and the tree is byte-identical. Absorb and absorbed-skill removal are covered the same way. Normal restore, absorb and remove flows in the gate still pass, and `check_path` accepts absent paths, so a write that creates a file does not abort by mistake. | yes: with `check_captured_files` disabled, 4 tests fail (7 failures counting subtests) |
| R1-03 | closed | The obsolete paragraph is replaced by a link to `#optional-checkout-locator`, a section that exists and is correct. No live doc still says "init records the checkout" or mentions the temp-folder exemption. | n/a (doc) |
| R1-04 | closed | Both READMEs now say "no unexpected skips", linked to `CLI_Reference.md#repository-validation`, which lists the platform exceptions. The remaining "zero skips" lines are dated historical validation records. | n/a (doc) |
| R1-05 | closed | README.zh now gives the H1 result: 12 tasks, inconclusive; Codex met the benefit criteria and Claude did not; 2.58× and 1.92× tokens. These match the table in `268429d:records/.../H1/RESULT.md`. The FIXCHECK paragraph (24 rows, `fail`, `codex/t01` and `claude/t12`, both memory thresholds missed) matches `e05c4d5:.../FIXCHECK/RESULT.md`. The linked files exist. | n/a (doc) |
| C1-01 | closed | Re-ran the CLI scenario with and without the `---` separator. `memory-check` now finds 2 entries and attributes `scripts/missing_new.py` to the new entry (line 5, date 2026-11-13). b898e4d finds 1 entry, and without the separator it attributes the path to 2026-10-01. `promote-candidates` lists both entries. | yes: the old regex makes the new test fail (2 subtests) |
| C1-02 | partly closed | The reported single-file scenario is fixed: memory show, recall (both modes), status and bootstrap list the ARC entry first. A file with one source keeps exactly its written order. For a v1-style memory file (date-only headers, newest first), show, recall, status and bootstrap output is identical to the 359e6e3 baseline. **Left:** the same inversion still happens when the newer note goes to `.oaw/memory-pending.md` (C2-02). The `oaw-evidence` skill sentence that C1-02 flagged is unchanged. | yes: `_memory_entries` set back to b898e4d makes both new tests fail |
| C1-03 | closed | On Linux, with `chmod 444` on the main file, `memory add` writes to pending, leaves the main file byte-identical, creates no `*.tmp` and does not retry. b898e4d rewrote the main file. On Windows the read-only attribute makes `os.access(W_OK)` return False, so the same direct path is taken and no temp copy is made (traced by reading). | yes: without the `os.access` pre-check the new test fails |
| C1-04 | closed | Compared old and new comparison logic with `ntpath` on 3.10 and 3.14 over 19 inputs. `\\?\C:\proj\..\outside\x` and `\\?\UNC\server\share\proj\..\outside` are now refused. No ordinary inside path changed verdict. | yes: without `normpath` the new test fails (2 subtests) |
| C1-05 | closed, but the fix causes C2-01 | The probe no longer resolves from the current directory or from relative PATH entries. However, the lookup now breaks on Windows with Python 3.10 and 3.11 (C2-01). | yes: `oaw.py` set back to b898e4d makes 2 new tests fail |
| C1-06 | closed | Re-ran the CLI with a symlinked `AGENT_MEMORY_BASE_DIR`. It now prints `.agents/memory.md`; b898e4d printed `../real/.agents/memory.md`. | yes: the old `relpath` makes the new test fail |

## 2. New findings (most severe first)

### C2-01 — blocker — `doctor --probe` cannot find Claude Code on Windows with Python 3.10/3.11; the windows × 3.10 CI job fails

- Where: `scripts/oaw.py:848-858` (73fb8f7, the C1-05 fix). For an extensionless command, each PATH directory is
  now looked up as `shutil.which(os.path.join(directory, "claude"))`.
- Cause: on Python 3.10 and 3.11, `shutil.which` with a directory part returns the path only if that exact file
  exists, and it does not apply PATHEXT. I read this in the local 3.10.12 and 3.11.14 stdlib. PATHEXT is applied
  to directory-qualified commands only from 3.12 on (checked in the 3.14 source).
- Scenario (emulated: the real stdlib `which` of each version, `sys.platform` patched to `win32`, `Popen`
  captured; `scripts_mine/probe_win.py` in the scratch directory):

  | PATH directory holds | b898e4d, 3.10/3.11 | 73fb8f7, 3.10/3.11 | 73fb8f7, 3.12/3.14 |
  |---|---|---|---|
  | `claude.cmd` | starts `…\claude.cmd` | "not found in absolute PATH directories" | starts `…\claude.cmd` |
  | `claude` + `claude.cmd` (npm shims) | starts `…\claude.cmd` | starts the extensionless `…\claude` sh shim; CreateProcess fails with WinError 193 (suspected, not run on Windows) | starts `…\claude.cmd` |
  | `claude.exe` (native installer) | starts `…\claude.exe` | "not found" | starts `…\claude.exe` |

  This brings back the defect that 651d468 fixed. `test_probe_resolves_host_from_path` already exercises it
  without mocks: on Windows, `fake()` creates `fake-claude-N.cmd`, and the test passes its stem with PATH set to
  that directory. That test should therefore fail on the windows-latest × Python 3.10 job (suspected by reading
  plus the emulation above; CI has not run). The new tests cannot catch this, because both Windows tests mock
  `shutil.which`, and the "legacy" mock returns None for every directory-qualified command.
- Not reproduced on real Windows. Reproduced by emulation.
- Smallest fix: in the no-directory branch, try `command + ext` explicitly in each absolute PATH directory. On
  `os.name == "nt"`, `ext` comes from PATHEXT (default `.COM;.EXE;.BAT;.CMD`) and the bare name is left out. On
  POSIX, `ext` is `""`. For example, `shutil.which(os.path.join(directory, command + ext))`. A directory-qualified
  name with an extension resolves on every version, and the current directory is still never searched. The
  existing unmocked `test_probe_resolves_host_from_path` then covers it on windows × 3.10.

### C2-02 — issue — a superseded legacy entry still ranks first when the newer note goes to pending (rest of C1-02)

- Where: `scripts/context_hub.py:331-344`. A date-only header is read as 00:00 UTC of that date. 2.0.0 wrote
  *local* dates (`datetime.now().strftime("%Y-%m-%d")`), and the merge compares the heads of the two files.
- Scenario (reproduced, CLI plus a patched clock): owner in UTC+8. `.agents/memory.md` holds the 2.0.0 entry
  `## [2026-11-14] [DECISION] cache needle: use LRU`. The main file is not writable (`chmod 444`; this is also the
  Codex-sandbox case that pending memory exists for). At 07:30 local, `memory add "[DECISION] cache needle: LRU
  superseded, use ARC"` writes `## [2026-11-13T23:30:00.000000+00:00]` to pending. Then `memory show --last 1`,
  status "Recent" and `recall --index` all put the superseded LRU entry first.
- This can only happen on the day of the newest legacy entry, before UTC midnight, in UTC+ zones, and only when a
  note goes to pending. Nothing is lost. CLI_Reference describes the rule. The `oaw-evidence` skill line "new
  matching entries precede older ones" (`templates/.agents/skills/oaw-evidence/SKILL.md:26`) is false in this case.
- Smallest fix: qualify the skill sentence the way CLI_Reference does, or compare a date-only head with a
  timestamp by the timestamp's local date (the timestamp wins ties).

### C2-03 — issue — one header the merge cannot parse at the top of a file pushes that whole file below every pending entry

- Where: `scripts/context_hub.py:336-344`. An unknown format becomes `datetime.min`. Each file now keeps its own
  order, so such an entry at the head of the main file blocks every main entry behind it until pending is used up.
  b898e4d's full sort moved only that one entry down.
- Scenario (reproduced): main holds `## [2026-11-14 09:00] [DECISION] …` (a hand-written time, which the new
  wiki_sync regex accepts as dated), followed by two `memory add` entries from 11-13 and 11-14. Pending holds two
  entries from October. `status` lists "Recent" as the two October pending entries, then the hand-written one;
  today's main entries drop out of the top 3. Nothing is lost. CLI_Reference describes the rule; the skill
  sentence above is false here too.
- Smallest fix: give an unparsed header the order key of the nearest dated entry in the same file, so it no
  longer holds the rest of its file back. Or parse the `YYYY-MM-DD[ T]HH:MM[:SS]` forms that wiki_sync now
  accepts.

## Checked with no new finding

- `_memory_entries` consumers: recall cursors bind the content of both sources, and the order is derived from
  that content, so a cursor stays valid exactly while the content is unchanged. `memory show N`, status,
  bootstrap, search and context only take the order, the first three or the count. An empty or missing pending
  file and files without `---` keep their written order, and that order is the 359e6e3 order. Compact and week
  dates no longer parse differently on 3.10 and 3.13.
- `memory_add` pre-check:
  - Root: `access` is True, so the main file is written as before.
  - Missing `.agents`: no pre-check; the normal path runs.
  - A directory at the memory path: EISDIR is still not rerouted.
  - A file the user does not own, or a 0444 file, goes to pending. CLI_Reference describes this.
- `check_captured_files`: no false abort on normal restore, absorb or remove (gate). The message says to rerun
  and that nothing was changed. The restore point is now recorded only after the check, so that is true.
  Unchanged files that restore skips are not rechecked, but restore does not write them.
- `confined_path`: `\\?\Volume{…}\..` is still accepted on 3.10, as before (`normpath` leaves the prefix alone).
  This is outside C1-04.
- wiki_sync regex: it additionally accepts `## [YYYY-MM-DD<T or space>…]` headers as dated entries. This only
  makes parsing more accurate. No check passes that should fail.
- Docs, CHANGELOG, example copies: no false statement found. The examples are regenerated, and the gate's
  example-content check passes.

Outside the diff, not a finding: `test_wiki_sync.MemoryCheckTests.test_c16_links_are_never_followed` fails on
Python 3.12.12 at both 73fb8f7 and b898e4d, and passes on 3.10 and 3.14. 3.12 is not in the CI matrix.

RELEASE: blocked (C2-01)
