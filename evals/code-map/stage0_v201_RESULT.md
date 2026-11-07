# Code map Stage 0 for OAW 2.0.1 (W2): result

Zero model tokens. Harness: `stage0_v201.py`; numbers: `stage0_v201_results.json`;
callers truth sets: `stage0_v201_truth_erpnext.json`, `stage0_v201_truth_vscode.json`.
Measured 2026-11-07 on Linux 6.8, Python 3.10.12, 56 CPUs, local SSD, with
`scripts/code_index.py` of commit f959e0c. Arm R is `native_search.py`, the frozen
Stage 0-alpha grep baseline, unchanged.

| repository | commit | files | Python | JS/TS |
|---|---|---|---|---|
| ERPNext | d9cb916 | 5,952 | 3,130 | 828 |
| VS Code | 29ad5e7 | 20,942 | 10 | 15,853 |

Both corpora are clean `git archive` copies of the commit (the source checkouts were
only read; their HEADs were checked against the commits).

## Verdicts

| rule | ERPNext | VS Code |
|---|---|---|
| (a) D24: S top-5 file hit rate beats grep by >= 0.15 in some question type, with no more text output bytes | **fail** (beats grep by +0.33 to +0.50 in every type, but prints 1.4-1.9x the bytes) | **fail** (+0.04 at best) |
| (b) callers recall >= 0.95 | **pass** counting every row (0.955); **fail** counting resolved rows only (0.900) | **pass** (1.000 both ways) |
| resolved callers that are wrong | 0 of 99 | 0 of 338 |

## (a) find against grep (top 5, frozen questions)

Gold files are the files named in each question's facts. A file counts when it is in
an arm's top 5 and shown in its text output.

| repository | type | questions | gold files | S hits | R hits | S rate | R rate | S bytes | R bytes |
|---|---|---|---|---|---|---|---|---|---|
| ERPNext | flow | q3 | 2 | 1 | 0 | 0.50 | 0.00 | 1,095 | 595 |
| ERPNext | impact | q1, q2 | 12 | 4 | 0 | 0.33 | 0.00 | 2,249 | 1,188 |
| ERPNext | mechanism | q4 | 3 | 1 | 0 | 0.33 | 0.00 | 1,080 | 745 |
| VS Code | flow | q2 | 10 | 0 | 0 | 0.00 | 0.00 | 1,111 | 803 |
| VS Code | impact | q3 | 10 | 0 | 0 | 0.00 | 0.00 | 1,238 | 942 |
| VS Code | mechanism | q1, q4 | 23 | 4 | 3 | 0.17 | 0.13 | 2,141 | 1,638 |

- On ERPNext grep's top 5 are translation files (`erpnext/locale/*.po`) for every
  question, so it hits nothing; S finds the defining module for each question.
  S loses the byte condition because each S result has a header, a symbol name, a
  score and a source line, against grep's single `path:line: text` line.
- On VS Code neither arm reaches the flow and impact facts in the top 5: the
  questions are long and their words are common across 20k files.
- One or two questions per type: one question moves a rate by 0.04 to 0.5.

## (b) callers against a hand-built truth set (20 symbols per repository)

Symbols are definitions the frozen questions name. Each truth entry was found with a
whole-word search and read with its enclosing definition; receivers were traced in the
source. Calls through string paths (hooks, `frappe.get_attr`, `run_method`) and through
`invokeFunction` are recorded as dynamic, not as callers. `callers` ran with `--limit 1000`.

| repository | true call sites | recall, all rows | recall, resolved rows | wrong resolved | unresolved rows (wrong) | file level: S found / wrong | file level: grep found / wrong |
|---|---|---|---|---|---|---|---|
| ERPNext | 110 | 0.955 | 0.900 | 0 / 99 | 15 (9) | 70/75, 8 | 75/75, 80 |
| VS Code | 338 | 1.000 | 1.000 | 0 / 338 | 988 (988) | 124/124, 404 | 124/124, 1,020 |

- ERPNext misses 5 sites, all `x = frappe.get_doc(...); x.method()`: the Python
  resolver treats a value returned by an external call as external, so the call is
  neither resolved nor listed. Python resolution was left unchanged in this work; the
  `limits` note now says so. A what-if that lists such calls as unresolved instead found
  110/110 with 3 more wrong unresolved rows (not applied).
- 6 ERPNext true callers are listed only as unresolved: calls on documents whose class the
  source does not write (`parent.update_ordered_qty()`, `doc = self.doc`), on an attribute
  set from outside (`self.sle_self`), and on a new instance
  (`StatusService(self).update_planned_qty()`).
- VS Code's unresolved rows are almost all same-name `resolve(` calls for
  `KeybindingResolver.resolve` (2,750 rows in total; the 14 true callers are resolved and
  listed first; the list says `truncated`). One returned unresolved row is a dynamic call
  that does reach the target (`IExtHostRpcService.assertRegistered`, a bound
  `RPCProtocol.assertRegistered`); it is scored as wrong.
- First run (779f8d5, same truth sets): ERPNext identical; VS Code resolved recall 0.997.
  Its one miss came from two engine bugs fixed in f959e0c (a spread `...X.f()` read as a
  receiver; `const IFoo = createDecorator<IFoo>()` beside `interface IFoo` kept the
  value's kind). The fixes were found by reading these misses.

## (c) Cost

| | ERPNext | VS Code |
|---|---|---|
| cold build, up to 8 worker processes | 4.8 s, 301 MB peak | 34.9 s, 2,092 MB peak |
| cold build, one process, no cache | 13.4 s, 287 MB | 76.3 s, 1,902 MB |
| cache on disk (two files) | 52.6 MB | 366.0 MB |
| warm `stats` / `callers` | 0.42 s / 1.03 s, 164 MB | 4.4 s / 6.3 s, 1,208 MB |
| warm `find` (loads search units) | 2.5 s, 385 MB | 11.3 s, 2,635 MB |
| warm `overview` | 1.2 s, 169 MB | 13.5 s, 1,228 MB |
| `overview` size | 4,355 chars | 5,884 chars (cap 6,000) |

Peak RSS is `ru_maxrss` of the largest single process the command waited for; worker
processes are not summed.

## Limits of this measurement

- The truth sets were built by the author of the index, from grep and reading, before
  `callers` ran on these symbols, except five VS Code symbols that served as engine
  checks during development (listed in the truth file). Nobody else has reviewed them.
- 20 symbols per repository, chosen from the questions; many have one or two callers.
  Recall on symbols reached mainly through dependency injection or framework hooks is
  not measured beyond the two recorded as dynamic.
- Stage 0 says nothing about agents: whether a model answers better with these pointers
  is Stage 1 (X1).
