You are an independent reviewer. Review one small code change in this repository (a standard-library Python toolkit). Do not edit any file. Do not run the full gate (your sandbox blocks sockets). You may read files and run `python3 -m unittest tests.test_cli_resolve -v`.

The change is the last commit (`git show HEAD -- scripts/oaw_common.py scripts/harness_check.py tests/test_cli_resolve.py`).

Background, as the author states it:
- Two CI failures on windows-latest with Python 3.10 ended in `PermissionError: [Errno 13]` raised from `handle.flush()` right after `handle.write(b"\0")` in `oaw_common._exclusive_lock`, when several processes wrote the same file at once and the lock file was new.
- The author's reading (not reproduced): the Windows C runtime implements append as seek-to-end then write; a process that saw an empty lock file can write at offset 0 after another process has written that byte and locked it with `msvcrt.locking`, and Windows refuses a write to a locked byte.
- The change: open the lock file unbuffered; on PermissionError from the first-byte write, continue to the lock wait when `msvcrt` is the lock mechanism; re-raise otherwise.

Questions to answer, each with file:line evidence:
1. Is the new code correct on Windows and on POSIX? Look for: behaviour of `open(path, "a+b", buffering=0)` (FileIO) with `seek`, `write`, `fileno`, `msvcrt.locking`; anything that relied on the buffered object; partial writes; whether swallowing the PermissionError can hide a real failure or lead to a state where two writers both believe they hold the lock.
2. Is the author's reading of the cause plausible? If you see a more likely cause of a PermissionError at that line, say so and say whether the change still handles it.
3. Do the three new tests in `tests/test_cli_resolve.py` (class `ExclusiveLockTests`) test what they claim, on Linux, macOS and Windows? Look for path comparisons that break on macOS (/var vs /private/var) or Windows short names, and for anything that would fail on a real Windows runner.
4. Is raising `CHECK_TIMEOUT` from 900 to 1800 in `scripts/harness_check.py` harmless to anything else that uses it?

Output: a verdict line `VERDICT: merge` or `VERDICT: fix first`, then at most 8 findings, each marked BLOCKER or NOTE, each with evidence. Only call something a BLOCKER if it would produce wrong behaviour or a failing test. No style comments.
