# Key freeze record (key content withheld until grading is finished)

2026-11-14. The item key is not published before the runs and their grading are complete. This file
fixes what was frozen.

| Step | Who | Result | SHA-256 of `KEY.json` |
|---|---|---|---|
| Curation from the two historical reviews of 2026-11-07 (33 findings) | `gpt-6-astra` (not a model under test; wrote neither the plan nor the reviews) | 30 items: 16 primary, 14 secondary; 1 finding not verified, 1 not adjudicable | `c5e672866b97d29d23d83b286ec8bcef577b635f973ff8474d3ad77b4e087f93` |
| Packet digest field corrected to the manifest's tree digest (the lead had given the curator an ad-hoc digest of the same files); items unchanged | lead | 30 items, 16 primary | `41efe96a84ada8b87321fbbf70474e39c5f98273f6d522ae2141dea093429ca4` |
| Independent eligibility check of the 16 primary items against the packet, then the rule fixed beforehand: a disputed primary is demoted, nothing is added | `claude-fable-5-2` (not a model under test; different family from the curator) | 7 keep, 2 keep with tightened judging text, 7 demoted to secondary, 0 excluded. **Frozen key: 30 items, 9 primary** (K02, K05, K07, K09, K14, K15, K18, K29, K30) | `6d7497e90b9baf7f872bfd04c4750fee77a523e69169fd840d48df02d8e1f99e` |

Edits applied with the eligibility check (all before any run): the seven demotions; for K02 and K29
the checker's proposed tightening of `detected_if` and removal of one sub-claim the draft itself
already raised; for K02, K05 and K18 a vague report is now mention-only instead of "not adjudicable";
K15 gained a guard against double credit with K18. The edit log (before and after text) is kept with
the key and is published with it.

Notes from the checker that stay as limits of the stage: three of the nine primaries (K14, K15, K18)
sit in one code area, so recall is also reported without them; K02 and a secondary item (K03) are the
same kind of defect at different tiers, and the fixed rule did not allow promoting K03; the key is the
union of two historical reviews, so it measures recall against those findings, not precision.

Measured cost of the preparation that used models:

| Work | Model | Logical tokens | Without cache reads | Counted toward |
|---|---|---:|---:|---|
| Curation | `gpt-6-astra` (Codex CLI) | 2,046,318 | 132,846 | Codex side, recorded separately |
| Eligibility check | `claude-fable-5-2` | 3,398,755 | 359,512 | this stage's Claude total and the 30M experiment cap |

The eligibility check cost about twenty times the allowance the design had given such work. The
design's Claude estimate (2.66–3.60M for the stage, native review 0.67M per run, scaled from small
documents) was withdrawn before any run for that reason; see `PREREG.md`, budget section.

Frozen preparation hash (`freeze_tools.py --check`): `d046bb592f6c038a9f8a36c01f1fcaa64bd82ebde0dffbad311692e541188ce5`.
Packet tree digest: `3f61293d1b071118f73eb4590dfcefc437ecd12da735c1bd6025b4f24dd21bc1` (572 files).
One blind review of the package before freeze found five blockers in the scripts; all five were fixed
and confirmed closed by the same reviewer (`review/`).
