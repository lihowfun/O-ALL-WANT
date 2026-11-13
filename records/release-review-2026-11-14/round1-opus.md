# OAW 2.0.1 release review, round 1 (Claude, cross-family)

Scope: `359e6e3..b898e4d` in `OAW-review-r1` (8 commits).
Experiments ran on a clone of `b898e4d` in a scratch directory with `/usr/bin/python3` 3.10.12,
git 2.34.1 on Linux x86_64. Nothing in the checkout was modified. Windows and macOS were not
available, so every Windows/macOS statement below is `suspected` (traced by reading).

Gate on that clone (`scripts/harness_check.py`, Linux, Python 3.10.12): 9/9 checks, 698 tests,
0 skipped. The findings below are cases the gate does not cover.

## Findings (most severe first)

### C1-01 — blocker — `wiki_sync.py` cannot parse the entries 2.0.1 `memory add` writes

- Where: `scripts/context_hub.py:350` now writes `## [2026-11-13T20:20:11.180566+00:00] [TAG] ...`
  (c2d9852). `scripts/wiki_sync.py:1351-1355` `MEMORY_ENTRY_HEADER = ^## \[(\d{4}-\d{2}-\d{2})\] `
  only accepts a bare date, and is used by `_parse_memory_entries` (`:1400`), therefore by
  `promote-candidates` (`:1494`) and `memory-check` (`:1801`). Same copy in
  `example/public-hybrid-demo/scripts/wiki_sync.py` (installed by the knowledge profile).
- Scenario (verified):
  1. memory.md with one legacy `## [2026-10-01] [DECISION] [T4] old ... scripts/old.py` entry, then
     `context_hub.py memory add "[DECISION] [T4] new decision cites scripts/missing_new.py"`.
     `wiki_sync.py promote-candidates --json` lists only the 2026-10-01 entry; `memory-check --json`
     says "Checked 1 entry ... 0 cited paths not found". The new T4 entry and its missing path are
     invisible (entries above the first parsable header are dropped).
  2. memory.md without a `---` separator (memory add appends at the end): the new entry's lines are
     folded into the previous entry's body. `memory-check` reports
     `entry_line 3, date 2026-10-01, title "old note ..."` for `scripts/gone_new.py`, a path that only
     the new entry cites: the finding is attributed to the wrong entry and date.
  Expected: every entry `memory add` writes is one parsed entry. In 2.0.0 the header was
  `## [YYYY-MM-DD]`, so this is a regression introduced by the timestamp change.
- Smallest fix: accept an optional time part, e.g.
  `^## \[(\d{4}-\d{2}-\d{2})(?:[T ][^\]\n]*)?\] `, keep `date` as the date part, and add a test that
  parses the output of `context_hub.memory_add` with `wiki_sync._parse_memory_entries`. Either also
  read `.oaw/memory-pending.md` in these two commands or say in CLI_Reference that they read only the
  primary file.

### C1-02 — should-fix — date-only entries are reordered against UTC timestamps; a superseded entry ranks first

- Where: `scripts/context_hub.py:313-334` (`_memory_entries`): every entry is sorted by its parsed
  header; a date-only header becomes `00:00 UTC` of that date. Before c2d9852, show/status/recall used
  file order, and `memory add` inserts at the separator, so file order was write order.
- Scenario (verified): timezone UTC+8 (the owner's). memory.md holds the legacy entry
  `## [2026-11-14] [DECISION] cache needle: use LRU` (written by 2.0.0 at 07:00 local, 11-14).
  At 07:30 local the upgraded `memory add "[DECISION] cache needle: LRU superseded, use ARC"` writes
  `## [2026-11-13T23:30:00+00:00] ...` at the top of the file. Result: `memory recall "cache needle" --index`
  lists the superseded LRU entry first; `memory show 1` (and the `status`/`bootstrap` "Recent" lines,
  which take the first three) show only the superseded entry. 2.0.0 showed the new one first.
  The same inversion occurs in every timezone whenever a hand-written `## [YYYY-MM-DD]` entry and a
  `memory add` entry share a UTC day: the date-only one always sorts as the oldest of that day,
  whatever its real order.
- Contradicted text: `templates/.agents/skills/oaw-evidence/SKILL.md:26-27` (and the two example
  copies): "Recall reads both; new matching entries precede older ones". CLI_Reference (line 136)
  does disclose "sort as the start of that UTC day ... Ties are deterministic, not proof of
  chronology", so the reference is accurate but the skill an agent reads is not.
- Related (verified, note-level): `datetime.fromisoformat` accepts `20261114` and `2026-W46` on
  Python 3.11+ but raises on 3.10, so such headers sort as dated on 3.13 and as undated
  (`datetime.min`, bottom) on 3.10. CI runs both versions.
- Smallest fix: keep each source in file order (its write order) and only interleave the two sources
  by timestamp (a merge, not a global sort); or, when comparing a date-only header with a timestamp
  of the same date, fall back to file position within one source. At minimum, change the skill
  sentence to match CLI_Reference.

### C1-03 — should-fix — a read-only `.agents/memory.md` behaves differently per OS, and on Windows leaks a temp copy on every add

- Where: `scripts/context_hub.py:356-366` (fallback) relies on `oaw_common.locked_update` →
  `_replace` (`scripts/oaw_common.py:256-275`) → `_commit` (`:278-289`).
- Linux/macOS (verified on Linux): `chmod 444 .agents/memory.md` in a writable `.agents/`:
  `memory add` succeeds into the primary file (mkstemp + `os.replace` ignore the file mode; the 0444
  mode is copied to the new file). No fallback happens; the "read-only notes file" is rewritten.
- Windows (suspected): `_replace` copies the read-only mode to the temp file (`os.chmod(temporary, ...)`),
  `os.replace` onto a read-only target fails with WinError 5, `_commit` retries for 3 s, then the
  `finally: os.unlink(temporary)` fails too because the temp is read-only. That PermissionError
  (errno EACCES) triggers the pending fallback, so the note is saved, but each `memory add` waits
  3 s and leaves a read-only `.agents/.memory.md.<random>.tmp` holding a full copy of memory.md.
  The Windows branch of `test_primary_lock_permission_failure_uses_pending_and_later_recall` mocks
  `locked_update`, so this path is not exercised in CI.
- Also on Windows (suspected): any PermissionError reaches the fallback, including a sharing
  violation (WinError 32) held over 3 s by a reader or antivirus, or `.agents/memory.md` being a
  directory (Windows reports EACCES, POSIX EISDIR). CLI_Reference line 134 says "Only a
  read-only/permission error". Nothing is lost (recall reads both files), but the routing is wider
  than documented.
- Smallest fix: in `_replace`, before `mkstemp`, raise `PermissionError(errno.EACCES, ...)` when the
  existing target is not writable (`os.access(path, os.W_OK)` is False); and in the `finally`, clear
  the read-only bit (`os.chmod(temporary, stat.S_IWRITE)`) before `os.unlink`. Add one unmocked test
  with a 0444 primary on every OS.

### C1-04 — note — `confined_path` accepts a `\\?\` candidate that still contains `..` (Windows, Python 3.10/3.11)

- Where: `scripts/oaw_common.py:107-142` (b898e4d).
- Scenario (comparison verified with `ntpath` on Linux; the Windows resolution step is suspected):
  boundary `C:\proj`, candidate `\\?\C:\proj\..\outside\x`. Old code: rejected (different drive).
  New code: `plain_windows_path` strips the prefix to `C:\proj\..\outside\x`, `ntpath.commonpath`
  does not collapse `..` and returns `c:\proj`, so the path is accepted and returned. On Python
  3.10/3.11 `ntpath.normpath`, and hence `realpath`, leaves `\\?\` paths unnormalized (3.12+ collapses
  `..`, verified), so an absolute argument such as `oaw_mode.py reviewed "\\?\C:\proj\..\outside\x"`
  would reach this comparison unchanged. Practical impact is likely nil, because NT does not
  interpret `..` after `\\?\` and the later open fails, but the boundary function now returns a path
  it should refuse.
- Smallest fix: `os.path.normpath(plain_windows_path(...))` before `normcase`/`commonpath`, or refuse
  any candidate that still has a `.` or `..` component.

### C1-05 — note — Windows `shutil.which` on Python < 3.12 searches the current directory first

- Where: `scripts/oaw.py:848` (651d468).
- Scenario (suspected): `oaw.py doctor --probe` run from inside a project (default `--target .`) on
  Windows with Python 3.10 resolves `claude` from the current directory before PATH, now also as
  `claude.cmd`/`claude.bat` (before the change CreateProcess only tried `claude.exe` there). The
  probe already starts Claude Code inside the project, so this widens an existing trust assumption
  only slightly.
- Smallest fix: scan `PATH` × `PATHEXT` without the current directory, or document that `--probe`
  trusts the project directory.

### C1-06 — note — the printed destination can be a `../` path

- Where: `scripts/context_hub.py:367`: `os.path.relpath(target, BASE_DIR)` mixes a resolved target
  with an unresolved `BASE_DIR`.
- Scenario (verified): `AGENT_MEMORY_BASE_DIR=<dir>/link` (symlink to `real`) prints
  `Memory entry added to ../real/.agents/memory.md`. On macOS, projects under `/tmp` or `/var` have
  the same symlink shape. Cosmetic; the write goes to the right file.
- Smallest fix: `os.path.relpath(target, Path(BASE_DIR).resolve())`.

## Areas with no finding

- Pending fallback, other cases: secret refusal runs before either write; `.oaw` or `.agents` symlinked
  outside the project is refused; a pending file symlinked outside makes every memory command stop
  with "Path is outside the project boundary" (fails closed); EIO/ENOSPC/ENOENT are not rerouted;
  no route writes one note to both files; concurrent primary/pending writers keep all entries
  (test passes); cursor digest covers presence and content of both sources.
- `matches_revision`: paths with spaces and a leading dash, a file missing at the revision, a symlinked
  working file (returns False, fails closed), a clean filter (agrees with `git status`), and filter
  failures, all verified. No finding.
- `probe_claude`/`stop_probe`: no finding beyond C1-05 (the POSIX branch still ends only the direct
  child, which was already the case).
- Gate skip allow-list (`scripts/harness_check.py:25-33, 109-126`): exact id+reason pairs; subTest,
  class-level and changed-reason skips do not match and fail; no unexpected skip passes without
  `OAW_ALLOW_SKIPS=1`. No finding.
- Locator consent: default `init` writes nothing to the config home; `migrate --remember-checkout`
  without `--apply` reports `planned` and writes nothing (verified). No finding.
- Leftovers of M1/M2/R2: none in code, templates or examples (`templates/AGENTS.md` has no net diff;
  deep rounds are 3, standard 1). Only guard tests asserting the absence of `next_action` remain.
- Version 2.0.1 / 2.0.0 compatibility: constants, ledger rename and example manifests agree; example
  copies are byte-identical to `scripts/` and `templates/`. No finding.
- CHANGELOG/README FIXCHECK numbers (196,707 > 174,382; 211,064 > 209,564; memory 1/4 and 2/4;
  remembered 2 → 1 and 1 → 3; H1 2.58× and 1.92×) match `records/v2.0.1-experiments/FIXCHECK/RESULT.md`
  at the cited commit `e05c4d5`. Documents say six-job CI has not run; no false readiness claim found.
- `evals/skill-value` literal-path audit: no finding (evaluation helper, not shipped).

RELEASE: blocked (C1-01 only; one regex line plus a test)
