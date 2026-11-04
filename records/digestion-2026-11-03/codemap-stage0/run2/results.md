# Code-map scores (full run)

- questions: questions.json sha256 `9fae80bdfb16f7acd28dfa6785decd4b6a1a1a246d9af4b7e7988e3091885970` (matches PREREG)
- corpus: commit 6481437f14705dacf18f5b7d713003598e2f0bfe, 536 files, file list `23999a79b547fb751cd6126249a5d628e32530650d78a3fee5b90d2bed276702`
- questions run: 39; top-k 5; MRR and precision/recall over the first 10 distinct files; a file counts only if the text output shows it
- deviations: none

| arm | class | n | top-1 | top-5 | top-5 hits | MRR | P@10 | R@10 | text bytes | JSON bytes | seconds | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R | a (concept -> definition) | 12 | 0.500 | 0.750 | 9 | 0.623 | - | - | 15298 | 11789 | 3.73 | 0 |
| R | b (callers) | 9 | 1.000 | 1.000 | 9 | 1.000 | 0.793 | 1.000 | 4940 | 4073 | 2.50 | 0 |
| R | c (change impact (git history)) | 13 | 0.308 | 0.846 | 11 | 0.515 | 0.128 | 0.712 | 15903 | 11261 | 3.27 | 0 |
| R | d (module path) | 5 | 1.000 | 1.000 | 5 | 1.000 | - | - | 1489 | 1883 | 1.08 | 0 |
| S | a (concept -> definition) | 12 | 0.667 | 1.000 | 12 | 0.760 | - | - | 10451 | 10597 | 12.59 | 0 |
| S | b (callers) | 9 | 1.000 | 1.000 | 9 | 1.000 | 1.000 | 0.907 | 5888 | 6623 | 9.14 | 0 |
| S | c (change impact (git history)) | 13 | 0.692 | 0.923 | 12 | 0.782 | 0.246 | 0.769 | 10256 | 9626 | 13.20 | 0 |
| S | d (module path) | 5 | 0.000 | 0.000 | 0 | 0.000 | - | - | 429 | 874 | 5.01 | 5 |

Gate for S vs R: PASS (passing classes: a; rule: in one class: top-5 rate delta >= 0.15, at least 2 more top-5 hits, and text bytes <= baseline over the questions where neither arm failed).
- a: top-5 delta +0.250 (+3 questions); text bytes 10451 vs 15298 over 12 questions (0 excluded after a failure); JSON bytes 10597 vs 11789
- b: top-5 delta +0.000 (+0 questions); text bytes 5888 vs 4940 over 9 questions (0 excluded after a failure); JSON bytes 6623 vs 4073
- c: top-5 delta +0.077 (+1 questions); text bytes 10256 vs 15903 over 13 questions (0 excluded after a failure); JSON bytes 9626 vs 11261
- d: top-5 delta -1.000 (-5 questions); text bytes 0 vs 0 over 0 questions (5 excluded after a failure); JSON bytes 0 vs 0
