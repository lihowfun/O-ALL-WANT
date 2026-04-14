# Release Checklist

P0 validation run completed on 2026-04-13 in a fresh macOS install fixture.

## Timings

- Clone + install + first `python3 scripts/context_hub.py status`: 3.55s
- Install-only: 0.04s

## Install Blockers

- [x] `README.md` and installer examples now use `python3`, which matches the
  tested environment where `python` was missing.
- [x] `install.sh` now warns about every managed file it may overwrite, not just
  `CLAUDE.md` and `AI_CONTEXT.md`.
- [x] `memory add` now preserves the full first word instead of stripping the
  leading character when a tagged note is recorded.

## Doc Inconsistencies

- [x] Added `docs/CLI_Reference.md`.
- [x] Added `docs/Skill_Guide.md`.
- [x] Added `templates/ROADMAP.md` so installed repos match the lazy-read routing docs.
- [x] README wording now says the installer "installs the CLI script" rather
  than implying a separate wrapper command exists.
- [x] Added `example/minimal-project/README.md` and linked it from README.

## Placeholder Gaps

- [x] Added inline customization notes to `templates/AI_CONTEXT.md`,
  `templates/AGENT_RULES.md`, and the knowledge templates.
- [x] Replaced JSON-only `${...}` placeholders in `templates/VERSION.json` with
  self-describing sample values.
- [x] Documented skill placeholder conventions in `docs/Skill_Guide.md`.

## Platform Issues

- [x] `scripts/context_hub.py` now chooses a cross-platform write lock:
  `fcntl` on POSIX, `msvcrt` on Windows, unlocked fallback otherwise.
- [ ] Native Windows smoke test is still recommended before public launch.

## Polish-Only

- [x] Added a committed minimal example deployment.
- [x] Counted annotations correctly even when tagged, so `search ""` reflects
  annotated topics.
