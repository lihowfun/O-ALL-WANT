# Agent Memory — Decision & Finding Log

> **Format**: `## [YYYY-MM-DD] [TAG] Title`, then write a conclusion. Newest entries on top.
>
> **Available TAGs**: `[BUG]` `[INSIGHT]` `[DECISION]` `[WORKAROUND]` `[EXPERIMENT]` `[ARCHITECTURE]`
>
> **How to write**:
> - Edit this file directly, or
> - `python3 scripts/context_hub.py memory add "[TAG] Title - Details"`

---

## [2026-04-13] [DECISION] Validated minimal-project onboarding fixture

Confirmed that install + first `python3 scripts/context_hub.py status` completed
within the README promise and that overwrite warnings now enumerate every managed
file the installer can replace.

## [2026-04-13] [WORKAROUND] Standardize docs and installer examples on python3

The validation machine did not provide a `python` alias. Using `python3`
avoids a copy-paste failure in README, install output, and bundled workflow
examples.

## [2026-01-15] [DECISION] Initialized agent memory system

Adopted the three-layer memory architecture and kept the default self-improving
skill enabled so every future task leaves a traceable record.

---

<!-- New entries go above this line. Keep newest on top. -->
<!-- Archive entries older than 30-50 items to docs/knowledge/ -->
