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

# 2. Run the full local gate — same 8 checks CI runs
./scripts/harness_check.py           # pycompile + CLI surface + install
                                     # refusal + fresh install + wiki lint
                                     # (repo + install) + strict placeholders
                                     # + example drift

# 3. Optional extras when touching skills / wikis:
python3 scripts/wiki_sync.py lint --strict    # also flags unfilled placeholders
                                              # + skill frontmatter issues
```

CI runs `harness_check.py` as a single step. A green check is required before merge.

Run `./scripts/harness_check.py --verbose` to see the raw output of each
check, or `--json` for machine-readable output.

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
`study/*` or `*-preview` branch until at least one more user confirms the
pattern is useful. A recent example: a draft `CURRENT_STATE.md` template
was shelved from v1.1 until multi-user demand emerges.

When a piece of proposed work depends on a downstream consumer that doesn't
exist yet (e.g. "this audit log will be useful WHEN we have an evaluator"),
defer it to research, not to implementation. See
`docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md` for the
canonical example of accept / research / reject triage.

## Questions?

Open an issue with the `question` label — that way other users see the
answer too. Thanks for reading!
