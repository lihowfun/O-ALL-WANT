PASS WITH FIXES

1. **OK — note — README.md:22–23.** Independent recount: 64 unique jobs, 4 controls, 60 mutants; 37 `killed`, 3 `killed-crash`, 20 `survived`. Controls ran 797 tests with no failures/errors/skips in 176.2, 185.5, 182.3 and 183.1 seconds; all 20 survivors also ran 797 with no skips. The recorded outcome labels give 40/60 = 66.7%; independently calculated 95% Wilson bounds are 0.5405687–0.7727074, matching 54.1%–77.3%. This validates the arithmetic, subject to finding 5.

2. **OK — note — README.md:24,29.** Independent caught/sample counts match every entry: compare 27/36, boolop 7/14, not 6/6, constant 0/4; catalog 3/5, catalog_core 5/6, catalog_ui_server 3/6, code_index 5/9, context_hub 0/2, eval_ledger 2/2, eval_ledger_fixcheck 2/2, fast_screen 1/1, goldfish_review 2/2, harness_check 1/2, improvement 3/3, judge_calibration 1/1, oaw 6/7, oaw_mode 1/2, oaw_status 0/2, user_install 3/5, validate_skills 0/1, wiki_sync 2/2.

3. **OK — note — README.md:25.** The 37 non-null failing summaries have failure+error counts min 1, median 5, max 147. Exactly nine have one entry: job IDs 2, 18, 23, 28, 44, 47, 50, 54, 62. These are unittest failure/error entries, not a general measure of independent test coverage.

4. **OK — note — README.md:12–15.** Re-running only site enumeration and deterministic selection reproduces 6,690 sites in 23 files (3,244 compare, 1,871 boolop, 921 not, 654 constants) and all 60 selected file/line/operator changes. `mut_sample.py:77–96` considers single comparisons, the first connector of each BoolOp, boolean literals (including defaults), and removable `not`; `random.sample` samples without replacement. Lines 104–125 copy the tree, apply one byte-span replacement, compile it, and run unittest discovery under bubblewrap with network isolation and a 900-second default. Ten workers requires `--workers 10`; the default is eight and the invocation is not retained in these results.

5. **WRONG — must-fix — README.md:16,23,27.** The stated “caught = at least one failure/error” is narrower than the implementation: `mut_sample.py:141–148` also labels any timeout or missing summary as killed; `analyze.py:26–28` counts all such jobs as caught. A sandbox startup failure, discovery/runner crash, resource failure or unrelated timeout can therefore be a false catch. Conversely, a successful shortened/zero-test suite or skipped coverage can survive: no 797-test/no-skip assertion exists. IDs 17, 25, 61 contain only `summary: null` and an explanatory note; their stderr/return codes are absent. The supplied evidence cannot independently verify the claimed `FAILED` output, 25–29 failures/errors, or the runner-crash cause. Preserve that raw evidence or qualify these three catches and the resulting rate.

6. **WRONG — should-fix — README.md:15.** “工作目錄以外唯讀” is too literal: bubblewrap also provides a writable private `/tmp`, mounts `/dev` and `/proc`, and binds the entire job directory writable, including sibling temporary/user-state directories outside the repository working directory (`mut_sample.py:121–124`). The isolation description should name these exceptions.

7. **OK — note — README.md:35, `catalog.py:617`.** At origin/main, `read(limit + 1)` precedes `len(pdf) > limit`; changing it to `>=` rejects a valid PDF exactly at the limit.

8. **OK — note — README.md:36, `catalog.py:888`.** The equality chooses whether to append the imported-record disclaimer; reversing it exchanges the static/imported annotation.

9. **OK — note — README.md:37, `catalog_core.py:1686`.** The first `or` becomes `and`, yielding `(full_name and name) or ""`. A full-name-only record loses its name; a record with both switches from full name to short name, changing relevance signals.

10. **WRONG — should-fix — README.md:38, `catalog_ui_server.py:797`.** Actions are not simply exchanged. With an untasted food, `t` stops tasting; any other answer, including Enter and `f`, starts tasting and prevents the `elif answer == "f"` branch. Evidence: origin/main lines 791–801.

11. **OK — note — README.md:39, `catalog_ui_server.py:863`.** The second list changes from non-EGM missing skills to EGM missing skills, while the preceding optional `egm` group remains; the re-add choices change.

12. **OK — note — README.md:40, `catalog_ui_server.py:959`.** Lines 947–948 retain high/medium flags. Reversing the boolean sort key puts medium before high instead of high before medium.

13. **OK — should-fix — README.md:41, `code_index.py:986`.** The boundary description is correct but should state the consequence: an unterminated JSX element whose text reaches EOF now falls through to `text[index]` and raises `IndexError`. A source-only, in-memory comparison using `<div>tail` returned `None` before the mutation and `IndexError` after it; no repository files were written.

14. **OK — note — README.md:42, `code_index.py:1454`.** `split("\n")` always returns a nonempty list, so the mutated `or` always pops its final entry. In-memory parsing of `function f() {}` without a terminal newline loses the function definition.

15. **OK — should-fix — README.md:43, `code_index.py:1646`.** The flag is behavioral, not merely a stored detail: `open_function(..., plain)` at lines 1612–1625 adds an unknown local `this` when true. Mutating an arrow callback adds that binding and can hide its inherited `this`; an in-memory arrow example produced different type records.

16. **OK — note — README.md:44, `code_index.py:3709`.** This changes default-import alias selection; the following target-resolution branch does not make it equivalent. In a source-only synthetic index, an unrelated default import named `alias` plus `unknown.alias()` adds a false unresolved caller of another target after mutation, whereas the original returns no caller.

17. **OK — note — README.md:45, `context_hub.py:136`.** `_knowledge_pages()` has three callers omitting the argument. The changed default bypasses the meta-page exclusion at lines 152–153.

18. **OK — should-fix — README.md:46, `context_hub.py:379`.** The initial flag changes, but it does not reroute writes: the exception handler still selects pending memory. Its observable effect on successful primary writes is a false “pending: primary memory is read-only or permission denied” output suffix (lines 377–392).

19. **OK — note — README.md:47, `harness_check.py:148`.** An invalid help response is rejected only when both return code and missing-command checks fail, instead of either; the CLI contract check becomes weaker.

20. **OK — note — README.md:48, `oaw.py:319`.** A nonempty skill directory lacking `SKILL.md`, or an empty non-skill tree, no longer triggers this rejection. The source validation becomes weaker.

21. **OK — note — README.md:49, `oaw_mode.py:865`.** A step with exactly one round gains the literal text `, up to 1 rounds`; the existing `> 1` omitted it.

22. **OK — should-fix — README.md:50, `oaw_status.py:545`.** A nonempty goldfish list now evaluates to `[]`, suppressing its output as described. Also, an absent/null `goldfish` evaluates to `None`, so iteration raises `TypeError`; “no longer lists results” understates the effect.

23. **OK within the existing CLI — note — README.md:51.** `git grep` at origin/main finds the definition and only one call, at `oaw_status.py:655`, which passes `stale` explicitly. Therefore current repository execution is unaffected. It is not universally behavior-free: calling `catalog_summary({})` without the argument changes its returned `stale` value from false to true.

24. **OK — note — README.md:52, `user_install.py:837`.** An invalid package name with a valid parts dictionary is now accepted by this guard. A valid name with invalid parts may fail later with a different exception; validation is weakened, not equivalent.

25. **OK — note — README.md:53, `user_install.py:1256`.** Hook events are now counted for statuses outside `install`/`needs-consent` and excluded for those two statuses, changing conflict/advisory output.

26. **OK — note — README.md:54, `validate_skills.py:275`.** Replacing the first connector yields `(not name and len(name) > 64) or not NAME_RE.fullmatch(name)`. The first term is impossible for these strings; the regex has no length cap (`:21`), so a valid-character 65-letter name loses the length error. This is not an equivalent removal of an empty-name check.

27. **OK with scope qualification — note — README.md:56,101.** No additional equivalent change was found among the other 19 rows. The “one equivalent” conclusion is defensible for existing call paths, provided the `catalog_summary` API-default qualification in finding 23 is retained. An unchanged test outcome alone does not establish equivalence.

28. **OK on symptoms/fix — note — README.md:66, CI #1.** `122690275338.log:137–340` shows macOS installation failures rooted in refusal of `/var`; `122690275261.log:138–157` shows successful behavior tests followed by a cp1252 `UnicodeEncodeError` in gate output. `7801940` changes product path handling in `scripts/oaw.py`, UTF-8 stream configuration in `scripts/harness_check.py`, and regression tests in `tests/test_install.py`/`test_gate.py`. These are two separate source defects; see finding 38 for counting scope.

29. **OK — note — README.md:67,74,80, CI #2 and #9.** `123962638741.log:207–225` reaches `_exclusive_lock:95` through `wiki_sync.add_experiment`; `132506339370.log:205–225` reaches `_exclusive_lock:231` through pending `context_hub.memory_add`. Both fail at `handle.flush()` with PermissionError and a writer exit code of 1. Extracted `_exclusive_lock` blocks are byte-identical at e7877dc, 99a16b2, dd91780, v2.0.1 and origin/main. `git diff 036a3e6 dd91780` is empty, supporting identical PR/main source, not a root-cause conclusion.

30. **OK for installed-product scope — should-fix — README.md:68, CI #3.** Logs `123983178275:291–299` and `123983178319:255–264` fail the same `evals/skill-value/test_experiment.py:135` assertion: an explicit cohort gold-file access is not flagged. This is an experiment-controller boundary-audit defect, not evidence that a test was wrong. It is outside installed product payloads, so the measurement-tool label is reasonable if that scope is explicit. `c2d9852` later changes `boundary_issues` to resolve literal paths and account for aliases; this is a relevant follow-up to investigate rather than leaving the fix wholly untraced.

31. **OK — note — README.md:69, CI #4.** `132115233777.log:202–259` shows the Windows probe, quoting and range-review failures; `132115234120.log:189–201` fails while the test creates a non-UTF-8 filename. `651d468` fixes product host launch/resolution and Git-filtered range comparison in `scripts/oaw.py`/`oaw_mode.py`; it changes the fake host, platform-specific quoting expectations and EILSEQ skip in tests. Gate skip accounting also changes under `scripts/harness_check.py`. The two installed-product defects versus two fixture/assertion portability issues are supported.

32. **OK on duplication; WRONG on “only version” — should-fix — README.md:70, CI #5.** `132123689610.log:203–260` and `132123689541.log:189–201` repeat #4's failures. But `git show 06ed481` changes scripts, tests, release-derived text and installation checks as well as version constants; e.g. `oaw_status.effect_lines` adopts `RELEASE`. Describe it as release preparation without the relevant fixes, not literally only a version-number edit.

33. **OK — note — README.md:71, CI #6.** `132131798365.log:204–219` reports a writer's false outside-boundary `ModeError`. `b898e4d` changes `scripts/oaw_common.py` path comparison to strip Windows extended-length prefixes, adds tests in `tests/test_cli_resolve.py`, and synchronizes examples. This is a product fix, not relaxed expectations.

34. **OK — note — README.md:72, CI #7.** `132166760103.log:205–213` reports host not found in absolute PATH directories. `7504eca` replaces the qualified `shutil.which` lookup with explicit PATHEXT candidates in `scripts/oaw.py`, and updates `tests/test_doctor_probe.py`. The commit also contains unrelated memory fixes; the cited host fix is correctly identified.

35. **WRONG as a confirmed cause — must-fix — README.md:73,81, CI #8.** `132360792977.log:158–169` proves only that a token was missing from the primary file after the workers passed their exit-code checks. `d7910ce` modifies only `tests/test_context_hub.py`, counting primary plus pending content, consistent with the documented product fallback. Its own commit message explicitly says the fallback was not observed directly in CI. “測試太嚴” is a plausible diagnosis, not established by this log; the missing entry's presence in pending memory was not captured. “產品沒改” is verified.

36. **OK on timeout; WRONG on exclusion of product defect — must-fix — README.md:75,81, CI #10.** `132510750310.log:188` records `behavior-regressions` exceeding 900 seconds. No completed unittest summary or per-test timings identify why. A passing run of the same source cannot exclude a product deadlock, contention or performance defect. Classify the observation as timeout, cause undetermined, rather than “不是產品缺陷”.

37. **WRONG — must-fix — README.md:81.** #5 repeats #4's product failures, so it is not a non-product failure merely because it adds no new defect. Together with the uncertain #8/#10 causes, the categorical total “4 次紅燈不是產品缺陷” is unsupported. Distinguish duplicate defect observations, measurement-tool failures, suspected test-contract mismatch, and unknown-cause timeout.

38. **WRONG/undefined counting scope — must-fix — README.md:79.** The listed fixes cover six separate source problems: #1 macOS path aliases and gate encoding (2), #4 range normalization and host launch (2), #6 path-prefix comparison (1), #7 qualified PATHEXT lookup (1). Five is defensible only if the gate encoding defect is explicitly excluded as tooling, consistently with #3's installed-product scope; then report five installed-product defects plus one gate defect. All cited fix commits are ancestors of v2.0.1. “只在 Windows 或 macOS 才出現” also overstates platform exclusivity: the CRLF regression test in `651d468` constructs the case on Linux; the evidence establishes where CI exposed it.

39. **OK as a hypothesis — note — README.md:84,99; issue-draft-windows-lock.md:17–19.** The unprotected empty-file check/write/flush precedes byte-range locking; only lock acquisition retries (`oaw_common.py:226–244`). An initialization race is plausible and appropriately marked un-reproduced. However, the file is opened in append mode, so “both saw empty” alone does not establish that a later flush targets the locked byte; actual Windows append/write interleaving needs verification. The logs contain no byte offsets, lock ownership or file-size trace proving this mechanism.

40. **WRONG as known incident history — should-fix — README.md:80,82; issue-draft-windows-lock.md:6,13,23.** Logs establish the exception sites and observed pass/fail variability, not that nobody inspected the runs or that no investigation occurred. “New lock file” is also narrower than the observed empty-at-check branch, which could concern an existing empty file. Attribute human-history claims to a separate record, and keep first-use/concurrency conditions and the inferred mechanism conditional. Identical source passing in PR does not isolate timing as the cause.

41. **WRONG attribution — should-fix — README.md:91.** The four controls span 176.2–185.5 seconds, not 176–194. The 194.1-second maximum belongs to mutant job 23. No supplied control records a standalone 137-second run; that measurement needs its own retained run record instead of citing these controls.

42. **WRONG as a prediction of established cause — should-fix — README.md:75,79,81 and the draft linked at :100.** The README's unsupported causal/exclusive claims are identified in findings 35–38; it contains no explicit claim that increasing test count will cause future timeouts. That prediction is in `issue-draft-ci-time-limit.md:13`: “測試再增加，這一格會更常逾時”. Observed suite durations do not establish this relationship or its frequency; phrase it as a risk/hypothesis. The same sentence's “逾時的紅燈不代表程式有問題” must mean that timeout alone is inconclusive, not that product problems are excluded.

43. **OK with evidence limit — note — README.md:62,82,102.** The supplied failed-job logs support the individual symptoms above, but do not constitute a complete 36-run/six-cell status inventory or a record of human attention/permission decisions. Those aggregate and administrative assertions need a status export or attributed provenance if they are intended to be independently auditable. No source document or checkout was modified during this review; only this report was created.
