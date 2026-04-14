# Agent Memory — Decision & Finding Log

---

## [2026-04-13] [DECISION] Validated the public demo flow

Confirmed that the public demo can build the wiki, pass lint, and answer status
queries without requiring any private data or extra services.

## [2026-04-13] [DECISION] Kept the wiki compiler optional

The default onboarding path should stay simple. The hybrid wiki layer is an
upgrade path, not a prerequisite.

## [2026-04-13] [INSIGHT] Operational docs and wiki docs solve different tasks

`ROADMAP.md` and `VERSION.json` answer current-state questions faster than topic
pages. Durable knowledge belongs in the compiled wiki, not in release-status docs.

## [2026-04-13] [EXPERIMENT] Hybrid router branch initialized

Working hypothesis: routing between operational docs, compiled wiki, and skills
will outperform both the baseline and a wiki-heavy setup.
