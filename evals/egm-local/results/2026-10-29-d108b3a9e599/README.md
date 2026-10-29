# Fixed-suite Codex review evidence

Read the [full study and limitations](../../../../docs/validation/egm-codex-2026-10-29.md).
The authoritative result is `aggregate.json`, derived from `evidence.json`
using the registered rules: A/B/C detect 24/24 planted defects, false claims
0/1/0. The overall gate fails B versus A; C matches A and is non-regressing
versus B on this suite. No indexing causality or efficiency claim is made.

`reports/` contains all anonymous findings/uncertainties. `grades/` contains the
six complete-source independent judgments. `adjudication/` preserves the sole
disputed label and its source-grounded resolution. `unblind-map.json` is released
after grading. `dispatch.json` records actual canonical context identifiers;
these are agent contexts, not API-request or billing counts.

`invalid-grading-v1/` is explicitly excluded. Its packet omitted actual EGM
review standards, causing false unsupported-standard attributions. Every vote,
adjudication and provisional aggregate is retained. All 27 unchanged reviews
were regraded by six fresh contexts after adding the missing method evidence;
the rubric and grade prompt did not change.

The method bundle is not vendored. `method-source-identity.json` supplies
full upstream commits, file hashes and source URLs. EGM manifest 0.1.0 is
Apache-2.0; see the existing [upstream license](../../../egm-pilot/LICENSE.egm)
and [notice](../../../egm-pilot/NOTICE.md). The case fixtures and OAW auxiliary
guidance are repository material. No native transcripts, credentials or host
workspace paths are included.

From the repository root:

```sh
python3 evals/egm-local/measure.py evals/egm-local/results/2026-10-29-d108b3a9e599/evidence.json
```

Exit 1 is expected: it truthfully reports the failed quality gate. Functional
unit tests and CI are separate from the model quality decision. Artifact hashes
cover this directory except the self-referential hash manifest itself.
