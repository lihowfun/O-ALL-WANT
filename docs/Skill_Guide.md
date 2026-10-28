# OAW native skills

v2 ships three task-specific packages. Minimal installation includes only evidence; the other two are opt-in.

| Skill | Installed by | Purpose |
|---|---|---|
| oaw-evidence | minimal | Selectively recall or record durable project evidence with source references |
| oaw-wiki | knowledge profile | Explicit raw-to-wiki rendering and verification |
| oaw-improve | --with-improve | Propose and evaluate a reusable improvement without automatically applying it |

Each package uses `<name>/SKILL.md` with name and description frontmatter. The host chooses relevant skills from metadata and reads instructions/resources on demand. OAW has no custom trigger-scanning runtime.

Codex's repository skill location is `.agents/skills/<name>/SKILL.md`. Claude Code's project skill location is `.claude/skills/<name>/SKILL.md`; the installed `CLAUDE.md` imports the shared policy but does not itself register skills. Select `--host codex` (default), `--host claude`, or `--host both` on init/migrate. The installer generates the selected native folders from one authored template source without requiring symlinks. Host additions are retained on later operations. OAW does not silently edit `.claude` settings or install plugins.

Check the native skill listing in each target host. Local schema validation alone does not verify host discovery, version eligibility, or implicit activation quality.

Use `python3 scripts/validate_skills.py` to validate the three authored packages. The helper accepts a documented subset of frontmatter and checks local references; it does not replace the host's full skill specification.

Skills must not require memory writes, self-reviews or reports after unrelated tasks. Native personal memory and usage diagnostics stay with the host. Proposed permanent skill changes need a reusable problem and evidence, not a task's step count.
