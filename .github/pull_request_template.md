<!--
Thanks for contributing to OAW. Keep this short — a tight PR description
beats a long one. Aim for 30 seconds of reviewer time per section.
-->

## What this changes

<!-- One or two sentences. What behavior is different after this PR? -->

## Why

<!-- Which problem from an issue, the continuity test, or your own use
prompted this? Link the issue if there is one. -->

## How it was verified

- [ ] `python3 scripts/wiki_sync.py lint` passes
- [ ] `python3 -m py_compile scripts/*.py` passes
- [ ] I ran `bash install.sh` in a fresh project and confirmed the
      managed-file overwrite prompt still works (if installer touched)
- [ ] I updated `CHANGELOG.md` / `ROADMAP.md` / `VERSION.json` where
      user-facing behavior changed

<!-- If this is a docs-only or typo-fix, just write "docs only — not verified" -->

## Wiki / skills impact

- [ ] I updated `docs/raw/` before changing compiled wiki topics, or this PR is
      manual docs-only work
- [ ] New wiki topics include concrete sources, `last_updated`, and
      `related_topics`
- [ ] Repeated procedures were linked to an existing skill or noted as future
      `.agents/skills/` candidates

## Related issues / context

<!-- #123, link to docs/archive/, or "N/A" -->
