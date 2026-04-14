# ROADMAP

## Current Focus

- Phase: Hybrid wiki router validation
- Goal: prove the hybrid mode is better than baseline without making onboarding worse
- Definition of done: prompt suite is documented, wiki lint passes, and merge recommendation is explicit

## Active Work

| Priority | Workstream | Status | Notes |
|----------|------------|--------|-------|
| P0 | Hybrid router comparison | In progress | Compare baseline / wiki-heavy / hybrid-router |
| P1 | Wiki maintenance ergonomics | In progress | Keep topic refresh deterministic and small |
| P1 | Public example quality | In progress | Make the repo feel real without exposing private data |
| P2 | Merge recommendation | Planned | Land only if hybrid wins cleanly |

## Next Milestones

1. Refresh all wiki topics from `docs/raw/`
2. Run `python3 scripts/wiki_sync.py lint`
3. Update `Experiment_Findings.md` with the latest recommendation
4. Decide whether to merge or keep this branch experimental
