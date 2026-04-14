# BRANCH

- Branch: `codex/wiki-router-experiment`
- Goal: validate the hybrid wiki router before merging into the public starter
- Non-goals:
  - do not force wiki sync into the default onboarding path
  - do not add a vector database
  - do not copy private project details

## Merge Criteria

1. The starter remains simple for first-time users
2. `python3 scripts/wiki_sync.py lint` passes on the public demo
3. Topic refreshes stay small and deterministic
4. The hybrid route clearly beats or matches baseline quality
