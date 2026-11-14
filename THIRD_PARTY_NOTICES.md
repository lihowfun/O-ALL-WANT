# Third-party notices

Parts of OAW's scripts re-implement or adapt methods from the projects below. Each
is licensed under the Apache License, Version 2.0; the license text is in
[`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt). Every adapted block carries an
`Adapted from ... (Apache-2.0); modified: ...` comment that states what was changed.
The bundled EGM has its own license and notice in `vendor/egm/` and `evals/egm-pilot/`.

## claude-mem
- Source: https://github.com/thedotmack/claude-mem at `02584c4ac9d92fea45adf5c61e22c546b5738621`
- Used in: `scripts/oaw_common.py` (`SECRET_PATTERNS`, adapted from `src/utils/redaction.ts`,
  OAW-12), `scripts/context_hub.py` (`memory recall --index`, method from
  `plugin/skills/mem-search/SKILL.md`, OAW-15). `scripts/improvement.py`'s trigger rule (OAW-03)
  re-implements the idea without copying code.
- NOTICE of that project:

  ```text
  Claude-Mem
  Copyright 2026 Alex Newman

  This product includes software developed for the Claude-Mem project.

  Licensed under the Apache License, Version 2.0.
  ```

## TokenEconomizer
- Source: https://github.com/microsoft/TokenEconomizer at `d58755d849cd9157d29aef539f2beab3d5fee0fc`
- Used in: `scripts/oaw_common.py` (`resolve_cli`, npm shim parsing adapted from
  `tokeneconomizer/plugin/sidecall.py`, OAW-01), `scripts/improvement.py` (`overhead_frac`,
  adapted from `tokeneconomizer/plugin/accounting.py`, OAW-04).
- That project ships no NOTICE file.

## graphify
- Source: https://github.com/Graphify-Labs/graphify at `8e6a6d2` (Apache-2.0; its NOTICE keeps earlier contributions under MIT).
- Used in: `scripts/wiki_sync.py` code-citation lint and `cites` (OAW-21, OAW-22) re-implement
  the method with the standard library; no graphify code is copied, so no notice text is required.
