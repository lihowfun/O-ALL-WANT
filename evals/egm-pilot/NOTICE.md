# NOTICE

Part of this directory is derived from the Elephant-Goldfish Model (EGM):

- Copyright 2026 Google LLC
- Source: https://github.com/google/elephant-goldfish-model at commit
  `f0ba151b252c9abf1318d9fe857a43265d06de89`
- License: Apache License, Version 2.0. A copy is in [LICENSE.egm](LICENSE.egm).

## Derived (modified) file

`scenarios.json` is converted from EGM's seven `skills/*/test_scenarios.yaml`
files (30 scenarios) by `convert_scenarios.py`. It is a modified version of
those files. The changes are:

1. YAML was converted to JSON. YAML comments, including each file's license
   header, were dropped; the copyright and license are kept in this notice, in
   `LICENSE.egm`, and in the `source` block of `scenarios.json`.
2. YAML anchors and aliases were expanded into explicit copies.
3. Each scenario gained a `case_id` (`<skill>/<scenario_id>`) and each assertion
   an `id` (`t<turn>a<index>`).
4. `system_prompt.skill_file` was flattened to `skill_file`.
5. The assertion semantics were written down (`assertion_semantics`). Upstream
   ships no runner for these assertions, so the semantics are OAW's reading,
   not EGM's.

Scenario text, patterns and messages are otherwise unchanged. `scenarios.json`
lists each source file with its SHA-256 (CRLF folded to LF).

## Not copied

EGM's skills, reviewer agents, resources and documentation are not included.
Live runs load EGM's own packaged Claude plugin (`distributions/claude`) from a
local checkout at the pinned commit with `--plugin-dir`, as decided in the plan
(decision 1: no fork, no vendoring).

Everything else in this directory (fixtures, planted defects, scripts and
documentation) is OAW's own work under the repository's license.
