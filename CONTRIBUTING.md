# Contributing to O-ALL-WANT

Thanks for looking! OAW is still small — **issues and small PRs are the fastest
way to help right now**.

## What's useful

- **Bug reports** on `install.sh`, `scripts/wiki_sync.py`, `scripts/context_hub.py`
  — especially edge cases (weird paths, unusual agents, Windows).
- **Skill contributions** — if you built a reusable workflow in
  `.agents/skills/`, consider PR-ing it as a template (see
  `templates/.agents/skills/_TEMPLATE.md`).
- **Doc clarifications** — if something in `README.md` / `docs/` confused you,
  fix it.
- **Cross-agent validation** — we tested mostly on Claude Code and Codex. If
  you use Cursor, Windsurf, or Gemini and something's off, please report.

## What to skip for now

- Large architecture rewrites — please open an issue first so we align on scope.
- New top-level abstractions (new lanes, new file categories) — the surface is
  deliberately small; proposals welcome as issues, not PRs.
- Features based on a single user's preference — we're keeping v1.x
  additive-only until multiple users confirm patterns.

## Before you open a PR

```bash
# 1. Fork + branch
git checkout -b your-feature-branch

# 2. Run the checks locally (same as CI)
python3 -m py_compile scripts/context_hub.py scripts/wiki_sync.py
python3 scripts/wiki_sync.py lint              # metadata + link check
python3 scripts/wiki_sync.py lint --strict     # also catches unfilled placeholders

# 3. If you touched install.sh, verify both paths:
./install.sh                                     # should refuse (self-install)
( cd "$(mktemp -d)" && echo y | /path/to/OAW/install.sh )  # should succeed
```

CI runs the above automatically on every PR (see `.github/workflows/test.yml`).
A green check is required before merge.

## Commit and PR style

- Keep PRs small. One concern per PR is easier to review and easier to revert.
- Conventional-commit-ish titles are nice but not required:
  `fix(install): ...`, `feat(wiki_sync): ...`, `docs: ...`, `ci: ...`.
- Explain **why** in the commit body, not just **what** — the diff already
  shows what.
- If your change is user-visible, add a line to `CHANGELOG.md` under a new
  `[Unreleased]` section (if one doesn't exist, start it).

## Releasing (maintainers only)

Cadence rule-of-thumb — **not dogma, just recent learnings**:

- **patch (x.y.Z)**: doc polish, bug fixes, internal refactors, lint relaxations
- **minor (x.Y.0)**: new user-visible features; prefer to **wait for multiple
  independent requests** before shipping a feature to main
- **major (X.0.0)**: breaking changes to the installed file layout or CLI
  contracts

Feature work driven by a single integrator's feedback should live on a
`*-preview` branch until at least one more user confirms the pattern is
useful. See `v1.1-preview` for the current example of that holding pattern.

## Questions?

Open an issue with the `question` label — that way other users see the
answer too. Thanks for reading!
