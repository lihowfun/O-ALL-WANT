# Code-map Stage 0-alpha: pre-registration (D24)

First frozen on 2026-11-04 (commit 4b46d4c). Amendment A1 on the same day resolves
a zero-context goldfish review of that freeze (QS-01..QS-10, log below). A1 was
written before any arm-S output on these questions existed. Before the full
evaluation, the only runs on the real questions are the 3-question harness checks
of arm R recorded at the end; they are not scores.

## Question

Does a code index (arm S) locate code better than an agent's first native
keyword search (arm R)? Zero model tokens, no graphify (arm G waits for the
level 2 sandbox, D24.3). Owner decision: D24 in the OAW records
(`ingest/DECISIONS.md`), from review C3 of 2026-11-04.

## Corpus

- OAW repository at commit `6481437f14705dacf18f5b7d713003598e2f0bfe`, the tip of
  `claude/oaw-2` before this work.
- Produced outside the repository with
  `git -c core.autocrlf=false -c core.eol=lf archive --format=tar 6481437 | tar -x -C EMPTY_DIR`,
  so files keep their LF blob bytes on every OS.
- 536 files. File-list hash (sha256 of the sorted relative POSIX paths, each
  followed by LF; equal to `git ls-tree -r --name-only 6481437 | LC_ALL=C sort | sha256sum`):
  `23999a79b547fb751cd6126249a5d628e32530650d78a3fee5b90d2bed276702`.
  Content hash (sha256 of `sha256(bytes)  path` lines in the same order):
  `7201f25c139032966f6d06b803b7eb1c55835e0dd8924af8cc40a608f2c75580`.
- `score.py run` refuses a corpus whose file list differs; `score.py corpus-hash DIR`
  prints both hashes.

## Frozen files (amendment A1)

- questions.json sha256: `9fae80bdfb16f7acd28dfa6785decd4b6a1a1a246d9af4b7e7988e3091885970`
- native_search.py (arm R) sha256: `208b410291dce79ebed58f99e6476d014ae8324b4cf8fb4c88add19900814d95`
- score.py sha256: `7596ad70d7a2d924ba625d2eb41a8d6c1caeccc3c50ce04a99afd282115fbf6e`

From A1 on, none of these three files changes before the results. A later change
is a recorded deviation: it is listed here with its reason, and the results are
reported both ways (frozen files and changed files). `score.py run` enforces part
of this:

- It refuses questions whose sha256 is not the one on the `questions.json sha256:`
  line above.
- It lists as a deviation in `results.json` any harness file whose sha256 is not in
  this file.
- It refuses a full run of an arm whose template names a `.py` file whose sha256 is
  not in this file (`--allow-unfrozen-arm` runs it anyway, as a deviation).
- It records the sha256 of this PREREG.md in `results.json`.

Superseded hashes from the first freeze are shortened to 12 characters in the log
below, so the old files fail these checks.

## Arm S freeze (QS-03)

Recorded on 2026-11-04 before the full run. S was not run on the questions by
the Elephant, and its source was not read.

- Branch `wip/code-index`, commit `6f2d36509cbdb6d34dd21575fe69e9e342ab8ee9`
  (2026-11-04 11:07:15 +0800).
- One file: `scripts/code_index.py` sha256 `67e2d48dfdc6d58e7971df9d59b4a5edd90c3b8499aea8d926616a97206bcd5a`.
  The Elephant checked this with `git show 6f2d365:scripts/code_index.py | sha256sum`.
- The S branch is cut from `6481437`, its merge base with `claude/oaw-2`. Neither
  the question commit `4b46d4c` nor the merge `237ada0` is an ancestor of S
  (`git merge-base --is-ancestor`), so the question set is not in S's history.
- S needs no setup step (it builds its index on the fly, in about 1 s). It accepts
  `--json` and `--limit N`, and its `callers` takes a bare or module-qualified
  name. Template: `py -3 FROZEN_PATH/code_index.py {sub} {args}`, with cwd = the
  corpus copy and FROZEN_PATH = any directory holding the file with the hash above.

Residual risk, stated plainly: S's author was told not to read the questions, and
that cannot be proven. The S commit (11:07:15) is 19 s older than the question
commit (11:07:34). However, the uncommitted question file sat on the same machine
from about 10:40, so blindness rests on the instruction, not on git history. The
hash above rules out any change to S after this record.

## Questions (39)

| class | task | subcommand | n | gold |
|---|---|---|---|---|
| a | concept -> definition: behaviour in plain words | `find "<question text>"` | 12 | the defining file (symbol and line span recorded) |
| b | callers of a named public function | `callers <symbol>` | 9 | every file with a direct call site |
| c | change impact: a commit message from this repository's history | `find "<cleaned message>"` | 13 | the code files that commit changed |
| d | module path: how module A reaches module B | `path <A> <B>` | 5 | the intermediate modules of every shortest import chain |

`affected` is part of the shared CLI shape but no class uses it in Stage 0-alpha.

How the gold was established. Details for each question are in `questions.json`:
`gold_method` and `difficulty` everywhere; for class b, the call-site lines and the
excluded mentions; for class c, the full commit hash, the original subject, every
excluded changed file, and `file_notes` explaining how each gold file relates to
the subject.

- **a**: read the definition in the corpus and confirmed the behaviour; grepped
  for other code with the same behaviour. Python spans are checked with `ast` by
  `score.py check`; the one JavaScript span was counted by hand.
- **b**: `grep -rnw` over every corpus file, then each hit read by hand. Removed:
  definition lines, comments, docstrings, Markdown, strings, and same-name
  functions of other modules. Only direct call sites count; callers of a local
  wrapper are not added (b05's context_hub.py:41 and wiki_sync.py:110 are the
  bodies of the local wrappers `_locked_write` and `_write`, and nothing aliases
  the function). Tests and evals count as callers. The defining file counts only
  when it calls the function itself. b04 and b05 are same-name collisions; both
  arms receive the module-qualified symbol (`catalog_core.pipeline_table`,
  `oaw_common.atomic_write`), and the other seven questions use the bare name.
- **c**: non-merge commits whose subject names no file, excluding version bumps,
  example syncs and docs-only commits. Gold = the commit's changed `.py`, `.js`,
  `.html`, `.css` and `.sh` files that still exist at 6481437 and are not tests
  (`tests/`, `test_*.py`) or generated copies (`example/`).
  `scripts/harness_check.py` is dropped when its only change is test bookkeeping
  (`MINIMUM_TESTS`, `REQUIRED_TEST_MODULES`). Question text = the subject without
  its `type(scope):` prefix and OAW id; c07's `view.json` became "the generated
  view file". Commits that only make sense through the forbidden vocabulary of
  the old intake page were not used.
- **d**: import statements, module level and function local, read by hand along
  every chain; importlib loads and subprocess runs are not edges. A is never a
  direct importer of B; all shortest chains are accepted (d02 has two).

`score.py check` enforces the leak rules mechanically:

- No question text contains a gold file's name, its stem (stems of 4+ characters)
  or, for class a, the target identifier.
- Since A1, no question text contains any 4+ character word of a gold file's folder
  or stem names (such as status, pilot or core), unless the question lists the
  word under `allowed_path_words` and explains it under `difficulty`. The only
  such exception is c13, "skills", which is part of the commit subject itself.
- The class-b symbol and the class-d endpoints are given by design.

## Arms

- **R** (`native_search.py`): a simulated first native search, standard library,
  no index or cache.
  - `find`: keywords from the text (stop words dropped, snake and camel case split
    with the whole identifier kept, quoted names kept whole). Every non-binary file
    is searched as case-insensitive substrings, hidden ones included (like
    `rg --hidden -i`). Files are ranked by sum(idf x (1 + ln hits)) with
    idf = ln(1 + N/df), with one best line per file.
  - `callers`: whole-word matches of the symbol's last name part, definition lines
    dropped; call-like lines score 1, other mentions 0.25. For a qualified symbol
    (`module.name` or `path::name`, added in A1), files that import that module,
    are that module, or write `module.name` rank first. This is the second look
    an agent takes after grepping the bare name.
  - `path`: two greps (A's imports; files whose import lines resolve to B). It
    reports A -> X -> B or A -> B, else lists both sides as candidates.
  - Default output: 10 files.
  - Template: `py -3 {repo}/evals/code-map/native_search.py {sub} {args}`.
- **S**: the frozen code index above.

Each arm runs as a subprocess on its own fresh copy of the corpus (cwd = the
copy), once per question in text mode and once with `--json`. The scorer never
imports an arm. R was developed against the fixture corpus in
`tests/test_codemap_eval.py`. Before the first freeze it was never run on the real
corpus; since then, only the harness checks below have run it.

Full run (one per arm; a rerun only after an infrastructure failure such as a
load timeout, recorded with its reason):

```
py -3 evals/code-map/score.py run --questions evals/code-map/questions.json --corpus CORPUS_DIR \
  --arm "R=py -3 {repo}/evals/code-map/native_search.py {sub} {args}" \
  --arm "S=py -3 FROZEN_PATH/code_index.py {sub} {args}" --out OUT_DIR
```

## Metrics (per class, per arm)

- Result paths are read from the JSON results in arm order. Absolute paths
  inside the corpus copy are made relative, and `./` and a `:line` suffix are
  dropped. A path under `example/` whose bytes equal a file outside `example/`
  counts as that file (generated copies). A repeated file keeps its first rank.
  Class d drops the two endpoints before scoring.
- **Shown in text (QS-02, A1)**: a ranked gold file counts only if its path, as
  the arm reported it, also appears in the text-mode output (backslashes read as
  `/`). Gold files that are ranked in JSON but absent from the text are reported
  as `gold_not_in_text`.
- **top-1 / top-5 file hit rate**: a counted gold file at rank 1 / within ranks
  1-5. The number of top-5 hits is reported too.
- **MRR** over the first 10 distinct files.
- **precision / recall** over the first 10 distinct files (reported for b and c).
- **text output bytes** and **JSON output bytes**: stdout of each run, CRLF folded
  to LF, summed per class (text-mode median also reported).
- **wall time** of the text-mode run (secondary); line-in-definition at top 1 for
  class a (secondary).
- **Failures (QS-10, A1)**: a run that exits non-zero, times out (300 s), prints
  invalid JSON, prints no text or returns no results has failed. It is a miss
  for that arm whatever it returned. Questions where either arm failed are left
  out of the byte comparison, and the gate reports how many were left out.

## Pass rule (D24, fixed before any result)

S passes Stage 0-alpha if, in at least one class, all of the following hold:

1. `top5(S) - top5(R) >= 0.15` (D24);
2. S has at least 2 more top-5 hits than R in that class (pre-result
   clarification of D24 in A1, QS-01: one question must not decide the gate,
   since a single class-d question moves top-5 by 0.2);
3. S's text output bytes are not more than R's, summed over that class's
   questions where neither arm failed (D24; the failure exclusion is A1, QS-10).

`score.py run` evaluates this as `gate` only on a full run; a partial run
(`--ids`) never evaluates it. With these class sizes, one question moves top-5 by
1/12 (a), 1/9 (b), 1/13 (c) or 1/5 (d), so condition 2 binds only in class d.

- **Fail**: S stays "not measured as helpful". No paid Stage 1 (D24.4). S is not
  retuned against these questions, and no new question set is drawn for this
  decision.
- **Pass**: a Claude-only Stage 1 may be proposed (at most 10M tokens, 6 questions x
  2 arms x 1 run), judged by the D24.5 step-change threshold (median tool calls
  on file-location questions down at least 30%, correct answers not fewer than
  the native arm). Stage 0-alpha is not a model benchmark.

## Expected before the run (QS-05, QS-06)

- Class b top-5 is probably saturated for both arms: most gold sets are small and
  contain the defining file or a heavy caller, which a whole-word grep finds.
  Class b is therefore expected to be uninformative for the gate. Its
  precision and recall are reported but do not gate. That stays as D24 wrote it.
- Class c gold is every changed code file of the commit by rule, the same for both
  arms. Files whose role the subject does not name (for example c04's 3-line
  `markdown_lines` alias in oaw_common.py) lower the reachable recall for both
  arms alike; `file_notes` records each file's link to the subject.

## Limits

- One repository at one commit, 39 questions; class d has 5, so its rates move in
  steps of 0.2.
- R simulates one first search; a real agent searches several times. The
  result says whether S's first answer beats that first search, not whether an
  agent with S finishes faster (Stage 1 measures that).
- Class c gold is what one commit changed; other reasonable files count as wrong.
- The question author read the code and wrote R. S's author was told not to read
  the questions (see the residual risk under the arm S freeze). Measured on
  Windows with Python 3.13; `results.json` records the platform.

## Amendment log

A1, 2026-11-04. A zero-context goldfish reviewed the first freeze (questions file
`28954eba2a73`, R `e1e5e6ae64fa`, scorer `fa9cbc0476bd`). Each finding was resolved
before any arm-S output on these questions existed:

| id | severity | resolution |
|---|---|---|
| QS-01 | major | fixed: a class also needs at least 2 more top-5 hits (pre-result clarification of D24, not a new rule) |
| QS-02 | major | fixed: a hit must also appear in the text-mode output; JSON bytes are reported beside text bytes |
| QS-03 | major | fixed: S frozen above (commit, file sha256, ancestry); a full run refuses an arm file whose sha256 is not recorded here; residual risk stated |
| QS-04 | major | fixed: b04 and b05 give both arms the module-qualified symbol, and R ranks files tied to that module first |
| QS-05 | minor | documented: class b top-5 is expected to be saturated; precision and recall are reported, not gated |
| QS-06 | minor | documented: class-c gold is every changed code file by rule, the same for both arms; `file_notes` added |
| QS-07 | minor | fixed (documented, gold unchanged): the b05 lines are the bodies of local wrappers, not aliases |
| QS-08 | minor | fixed: a08, a10, a12 and b04 reworded; `check` now flags gold path words (c13 "skills" allowed, the commit subject) |
| QS-09 | minor | fixed: no harness change before results; later changes are deviations reported both ways; PREREG sha256 in results |
| QS-10 | minor | fixed: failures and empty output are misses; their questions leave the byte comparison, with a count |

Gold files did not change for any question. The amendment changed only
question texts (a08, a10, a12, b04, b05), the b04/b05 symbols, notes, and the
`allowed_path_words` of c13.

## Harness checks (not scores)

- First freeze, 2026-11-04, Windows 11, Python 3.13.13: `score.py run --ids
  a01,b01,d01` with arm R only. All six invocations exited 0 with valid JSON, the
  questions hash matched, and the gate was not evaluated (partial run). Text
  output was 1174, 647 and 289 bytes.
- Amendment A1, 2026-11-04, Windows 11, Python 3.13.13: the same three questions
  with arm R only, under this file. No failures, no deviations, every gold path
  ranked in JSON also shown in the text output, and the gate was not evaluated
  (partial run). Text output was 1174, 647 and 289 bytes (JSON 958, 562 and 330),
  at 0.23-0.34 s per invocation.
