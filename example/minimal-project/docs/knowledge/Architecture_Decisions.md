# Architecture Decisions

> Track major architecture decisions and their rationale. Agents read this to
> understand why the project is shaped the way it is.

---

## Standardize operator-facing commands on `python3`

**Date**: 2026-04-13
**Context**: The first P0 smoke fixture succeeded with `python3`, but the host
environment did not provide a `python` alias.
**Decision**: Use `python3 scripts/context_hub.py ...` in README, installer
output, and bundled documentation.
**Rationale**: The examples should match the command that actually works on the
widest range of modern macOS and Linux developer setups.
**Alternatives Considered**: Keep `python` in docs and ask users to infer the
correct interpreter; add a separate wrapper binary.
**Status**: ✅ Active

---

## AI Annotations

<!-- Auto-appended by agents via: python3 scripts/context_hub.py annotate Architecture_Decisions "note" -->
