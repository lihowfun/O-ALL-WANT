# Code-map Stage 0-alpha: pre-registration (D24)

Frozen on 2026-11-04, before any arm was run on the questions. The only run on
the real questions before the full evaluation is the 3-question harness check of
arm R recorded at the end of this file; it is not a score.

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

## Frozen files

- questions.json sha256: `28954eba2a73bb7a439d5ce9f47f885c01a765ed4d72e44cf7e3132b2954f449`
- native_search.py (arm R) sha256: `e1e5e6ae64fa82811e95738c839d307ff86cf30e700b694b5b28de5871381246`
- score.py sha256: `fa9cbc0476bd0ec534043b7ef6df452da8cfaca4f9a2b0cd89d0be274d0d9d39`

`score.py run` checks the questions hash against this file and records the
harness hashes and the hash of every file an arm template names in
`results.json`. A harness fix before the full run must be added here with its
reason and new hashes; the questions and the pass rule do not change.

## Questions (39)

| class | task | subcommand | n | gold |
|---|---|---|---|---|
| a | concept -> definition: behaviour in plain words | `find "<question text>"` | 12 | the defining file (symbol and line span recorded) |
| b | callers of a named public function | `callers <symbol>` | 9 | every file with a call site |
| c | change impact: a commit message from this repository's history | `find "<cleaned message>"` | 13 | the code files that commit changed |
| d | module path: how module A reaches module B | `path <A> <B>` | 5 | the intermediate modules of every shortest import chain |

`affected` is part of the shared CLI shape but no class uses it in Stage 0-alpha.

How the gold was established (details per question in `questions.json`:
`gold_method`, `difficulty`, and for class b the call-site lines and the
excluded mentions, for class c the full commit hash, original subject and every
excluded changed file):

- **a**: read the definition in the corpus and confirmed the behaviour; grepped
  for other code with the same behaviour. Python spans are checked with `ast` by
  `score.py check`; the one JavaScript span was counted by hand.
- **b**: `grep -rnw` over every corpus file, then each hit read by hand; definition
  lines, comments, docstrings, Markdown, strings and same-name functions of other
  modules removed (b04 and b05 are same-name collisions). Tests and evals count
  as callers; the defining file counts only when it calls the function itself.
- **c**: non-merge commits whose subject names no file, excluding version bumps,
  example syncs and docs-only commits. Gold = the commit's changed `.py`, `.js`,
  `.html`, `.css` and `.sh` files that still exist at 6481437 and are not tests
  (`tests/`, `test_*.py`) or generated copies (`example/`);
  `scripts/harness_check.py` is dropped when its only change is test bookkeeping
  (`MINIMUM_TESTS`, `REQUIRED_TEST_MODULES`). Question text = the subject without
  its `type(scope):` prefix and OAW id; c07's `view.json` became "the generated
  view file". Commits that only make sense through the forbidden vocabulary of
  the old intake page were not used.
- **d**: import statements, module level and function local, read by hand along
  every chain; importlib loads and subprocess runs are not edges. A is never a
  direct importer of B; all shortest chains are accepted (d02 has two).

Question texts never contain a gold file's name or stem (stems of 4+
characters) or, for class a, the target identifier; `score.py check` enforces
this mechanically. The class-b symbol and the class-d endpoints are given by
design. Common words that also occur inside an identifier are allowed and noted
under `difficulty`.

## Arms

- **R** (`native_search.py`): a simulated first native search, standard library,
  no index or cache. `find`: keywords from the text (stop words dropped, snake and
  camel case split with the whole identifier kept, quoted names kept whole),
  case-insensitive substring search of every non-binary file including hidden
  ones (like `rg --hidden -i`), files ranked by
  sum(idf x (1 + ln hits)) with idf = ln(1 + N/df), one best line per file.
  `callers`: whole-word matches of the symbol, definition lines dropped, call-like
  lines 1, other mentions 0.25. `path`: two greps (A's imports; files whose import
  lines resolve to B), reports A -> X -> B or A -> B, else lists both sides as
  candidates. Default 10 files of output.
  Template: `py -3 {repo}/evals/code-map/native_search.py {sub} {args}`.
- **S**: the stdlib code index built by a separate agent that did not see these
  questions, run as `py -3 {repo}/scripts/code_index.py {sub} {args}` (or its
  final path) with any index build passed as `--setup S=...`; its build time is
  reported separately and does not count toward wall time.

Each arm runs as a subprocess on its own fresh copy of the corpus (cwd = the
copy), once per question in text mode and once with `--json`. The scorer never
imports an arm. R was developed against the fixture corpus in
`tests/test_codemap_eval.py`; before the questions were frozen it was never run
on the real corpus.

Full run (one per arm; a rerun only after an infrastructure failure such as a
load timeout, recorded with its reason):

```
py -3 evals/code-map/score.py run --questions evals/code-map/questions.json --corpus CORPUS_DIR \
  --arm "R=py -3 {repo}/evals/code-map/native_search.py {sub} {args}" \
  --arm "S=py -3 {repo}/scripts/code_index.py {sub} {args}" --out OUT_DIR
```

## Metrics (per class, per arm)

- Result paths are read from the JSON results in arm order; absolute paths
  inside the corpus copy are made relative, `./` and a `:line` suffix are
  dropped. A path under `example/` whose bytes equal a file outside `example/`
  counts as that file (generated copies); a repeated file keeps its first rank.
  Class d drops the two endpoints before scoring.
- **top-1 / top-5 file hit rate**: a gold file at rank 1 / within ranks 1-5.
- **MRR** over the first 10 distinct files.
- **precision / recall** over the first 10 distinct files (reported for b and c).
- **text output bytes**: stdout of the text-mode run, CRLF folded to LF, summed
  per class (median also reported).
- **wall time** of the text-mode run (secondary); line-in-definition at top 1 for
  class a (secondary).
- A run that exits non-zero, times out (300 s) or prints invalid JSON is flagged
  as an error; whatever it returned is still scored and nothing returned is a miss.

## Pass rule (D24, fixed before any result)

S passes Stage 0-alpha if, in at least one class,
`top5(S) - top5(R) >= 0.15` **and** S's text output bytes in that class are not
more than R's. `score.py run` evaluates this as `gate` only on a full run; a
partial run (`--ids`) never evaluates it. With these class sizes one question
moves top-5 by 1/12 (a), 1/9 (b), 1/13 (c) or 1/5 (d).

- **Fail**: S stays "not measured as helpful". No paid Stage 1 (D24.4); S is not
  retuned against these questions and no new question set is drawn for this
  decision.
- **Pass**: a Claude-only Stage 1 may be proposed (at most 10M tokens, 6 questions x
  2 arms x 1 run), judged by the D24.5 step-change threshold (median tool calls
  on file-location questions down at least 30%, correct answers not fewer than
  the native arm). Stage 0-alpha is not a model benchmark.

## Limits

- One repository at one commit, 39 questions; class d has 5, so its rates move in
  steps of 0.2.
- R simulates one first search; a real agent searches several times. The
  result says whether S's first answer beats that first search, not whether an
  agent with S finishes faster (Stage 1 measures that).
- Class c gold is what one commit changed; other reasonable files count as wrong.
- The question author read the code and wrote R; S's author did not see the
  questions. Measured on Windows with Python 3.13; `results.json` records the
  platform.

## Harness check (added after freezing; not a score)

2026-11-04, Windows 11, Python 3.13.13: `score.py run --ids a01,b01,d01` with arm R
only, on the corpus above. All six invocations exited 0 and printed valid JSON;
the questions hash matched this file; the run was marked partial and the gate
was not evaluated; harness hashes equal the frozen ones. Text output 1174, 647
and 289 bytes; about 0.2-0.35 s per invocation. The full run reruns these three
questions together with all the others; this check is not a result.
