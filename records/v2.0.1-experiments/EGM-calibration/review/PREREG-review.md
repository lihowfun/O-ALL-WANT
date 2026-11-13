1. **P-01 — blocker — [cal_grade.py:223](cal_grade.py:223)**  
   Batch 2 drops batch-1 review validity. If one grader marks Codex N1 unreadable while both graders detect every primary in Codex N2, batch 1 correctly returns `NC1`. Batch 2 skips validity checks for repeated reports and recomputes completeness, changing Codex to `ceiling`. Reproduced offline.  
   **Smallest fix:** preserve batch-1 validity/completeness and its Codex decision; allow subsequent accounting failures to invalidate it, but never upgrade it through batch 2.

2. **P-02 — blocker — [PREREG.md:131](PREREG.md:131), [RUNBOOK.md:159](RUNBOOK.md:159)**  
   The lead chooses the remaining grading reserve after seeing batch-1 results, without a frozen value or calculation rule. With 8M spent and N1 costing 4M, a 1.8M reserve funds N2; a 2M reserve produces terminal `NC5`. Thus identical observations permit discretionary continuation or stopping. Preventing reopening an existing stop does not prevent this initial choice.  
   **Smallest fix:** freeze a reserve value or deterministic calculation before subject data, and enforce that calculation in `sequential_n2`.

3. **P-03 — blocker — [cal_grade.py:69](cal_grade.py:69), [cal_run.py:808](cal_run.py:808)**  
   Absolute source citations disclose provenance. Native workspaces contain paths such as `attempts/codex-N1/codex-N1.a1/workspace/`; the prompt permits source-file citations, and packing preserves every string inside findings and uncertainties. A valid report citing that absolute path reaches both graders with its cell and run exposed. Reproduced offline.  
   **Smallest fix:** deterministically convert each report’s known workspace prefixes to relative packet paths before hashing and packing.

4. **P-04 — blocker — [cal_run.py:51](cal_run.py:51), [cal_run.py:101](cal_run.py:101)**  
   Missing counters become zero rather than incomplete metering. A final `modelUsage` containing `{"claude-fable-5-2": {}}`, without streamed usage, passes as complete zero usage. A synthetic CLI exercising the actual request adapter produced `status: completed` and a complete zero-token charge. Paid grading can therefore escape both caps.  
   **Smallest fix:** validate the required final counter schema before declaring metering complete; missing counters must retain unknown status and observed lower bounds.

5. **P-05 — blocker — [cal_ledger.py:35](cal_ledger.py:35), [cal_grade.py:485](cal_grade.py:485)**  
   Scoring overlooks unsettled native and grader intents, although launch accounting checks them. If Claude N2 spends tokens and crashes before appending its row, rescoring batch 1 treats N2 as never launched. The offline reproduction omitted 500,050 observed tokens, accepted the existing accounting audit, and returned Claude `NC4` instead of `NC1`.  
   **Smallest fix:** apply the launch path’s unsettled-intent checks during scoring and ledger summarization; count an N2 intent as launched and require `NC1` until its usage is recovered.

BLOCKED