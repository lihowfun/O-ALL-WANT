# graphify drawn-map intake

Decision: absorb a bounded file dependency view, independently implemented over
OAW's existing index. Do not adopt graphify's runtime or extraction pipeline.
This assessment reads graphifyy 0.9.101 source as data; it does not execute it.
References below are relative to the unpacked package, not this repository.

## What the drawn map adds

- `graphify/exporters/html.py:508` (`to_html`) makes `graph.html`: directed
  edges, degree-sized nodes, community colors, confidence styles and a legend.
  `_html_script` at line 153 adds search, click inspection, neighbor navigation
  and community filtering. This gives a person spatial orientation and an
  immediate way to follow connections that OAW's text queries do not provide.
- `graphify/cluster.py` (`_partition`, `cluster`, `score_all`) groups connected
  concepts and scores cohesion; `graphify/report.py:111` (`generate`) summarizes
  corpus coverage, extraction confidence, communities, hubs and surprising
  connections in `GRAPH_REPORT.md`. An agent can read this structural summary
  without consuming the whole node list; it is not proof of architecture.
- `graphify/exporters/html.py:532` bounds visualization size and can aggregate
  communities. This recognizes that a full symbol graph becomes unreadable.
  OAW already has an overview; its missing piece is a visible, navigable graph
  and a compact diagram representation an agent can receive as text.

## Noise and risks

- A symbol/document/comment graph mixes different kinds of evidence. A thick
  edge or attractive cluster can suggest a relationship stronger than its
  extraction supports. `graphify/build.py` preserves EXTRACTED, INFERRED and
  AMBIGUOUS evidence; `report.py:133` counts those distinctions. Name similarity
  and semantic inference must not silently become resolved dependency edges.
- Many generated copies, vendored files or standard-library stubs can dominate
  the picture. OAW's existing exclusions help; vendor/test files still need
  deliberate scoping. A cap is a partial view, not a claim of full coverage.
- `graphify/cluster.py:_partition` seeds and canonicalizes its input, but can
  select different Leiden/Louvain backends depending on installed packages.
  Directory groups are cheaper, stable and verifiable, though not semantic.
- `graphify/exporters/html.py:733` loads vis-network from unpkg. That HTML needs
  network access and third-party JavaScript. `graphify/llm.py` configures remote
  semantic/label backends; those optional paths can send source-derived data.
  Neither is needed for a dependency drawing. Exported filenames and structure
  can themselves disclose private information even without source snippets.
- `graphifyy-0.9.101.dist-info/METADATA` requires networkx, numpy, rapidfuzz,
  PyYAML and numerous tree-sitter packages; optional Leiden adds native code.
  Absorbing that stack conflicts with OAW's standard-library portability.
- The earlier tasting measured file-list answers, not visual comprehension.
  Its reported counts and errors are unverified historical observations here;
  neither its negative verdict nor the owner request establishes map benefit.

## Absorb now / leave out

Implement `graph` with HTML, Mermaid and JSON from the existing import and call
resolution tables. Nodes are indexed Python/JS/TS files, including isolated files
and tests. Directed cross-file edges count import bindings plus resolved call
sites separately; weight is their sum. Exclude external/unresolved targets and
intra-file calls. Use immediate directory groups and deterministic placement,
not physics. Search, neighbor highlighting and top incoming/outgoing file lists
support navigation. Reuse call-graph resolution with an explicit include-tests
option so overview's current test exclusion stays intact.

All formats expose scope, totals, caps, complete/truncated and index limits.
Apply node caps by total incident edge weight, then retain strongest edges with path tie-breaks;
report both kinds of omission. HTML is a single offline document with escaped
labels, inline CSS/JS and no resource requests. Mermaid uses generated IDs and
escaped labels. Output contains relative paths and counts, not source or cache
locations. Keep an explicit export path/stdout choice; do not auto-open browsers.

Leave out semantic edges, LLM labels, community algorithms, work memory, hooks,
servers, cloud publishing, additional languages and a duplicate report system.
They add uncertainty or lifecycle scope without being necessary to draw a map.

## Fixed acceptance contract (before measurements)

1. A hand-written Python and JS/TS fixture must match exact directed pairs,
   import/call counts and isolated nodes. Unknown calls, external targets and
   self edges must not appear. Directory scope must exclude boundary edges.
2. Repeated exports of unchanged input must be byte-identical in all formats,
   including after cache reuse; Windows-style scope separators must work.
3. Over-cap fixtures must stay within node/edge caps, preserve valid endpoints,
   and report exact omitted counts. Empty and cyclic graphs must export.
4. HTML must contain a real SVG drawing, search, keyboard/click selection,
   neighbor emphasis, top callers/callees and a legend. Hostile labels must
   remain text in HTML and Mermaid; there must be no external resources or
   network API calls. Browser inspection, if available, separately checks that
   search and selection work offline; structural checks alone do not prove it.
5. All existing unittests and the repository harness must pass. Record actual
   counts, platform and unavailable checks; do not label fixtures a model study.
6. Later comprehension study: freeze tasks and answers before running matched
   text-only versus text-plus-map sessions on the same snapshots/host/model.
   Use at least 12 cross-file tasks across 3 repositories; grade correct
   dependency routes, missed dependencies, unsupported claims, time and tokens.
   Accept a benefit claim only with no accuracy loss or extra unsupported
   claims and at least 15% lower median time or tokens. No such claim is made
   by shipping this feature; an agent must actually receive the diagram/data.

## Measured validation (2026-11-08)

Linux x86_64, Python 3.10.12, restricted filesystem/socket sandbox:
- `python3 -m unittest discover -s tests -p test_code_index.py -q`: 62 tests,
  3.866 s, OK (8 new graph tests; all prior code-index tests retained).
- `python3 -m unittest discover -s tests -q`: 650 tests, 117.389 s,
  FAILED (errors=16). All 16 are existing catalog UI tests denied socket
  creation with `PermissionError: Operation not permitted`; no skips.
- `python3 scripts/harness_check.py`: 8/9 checks passed, exit 1. Only behavior
  regressions failed: the same 16 socket errors (650 tests, 117.526 s).
- Generated examples match; diff whitespace checks pass. The scripts scope
  exports 20 nodes/26 edges, complete within the index (not an accuracy study).
- Existing Node 24.13.0 executed the inline JS against a minimal DOM double:
  search, click/keyboard selection, neighbor states, reset and zoom passed;
  empty graph initialization passed. This is not a real browser check.
- Browser validation unavailable: Firefox requires writes outside the sandbox;
  Playwright has no bundled browser. No browser/dependency was installed.
  Acceptance item 5 remains blocked by the environment; no model study ran.
