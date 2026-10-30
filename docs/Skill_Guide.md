# OAW native skills

V2 includes EGM: seven pinned EGM skill entrypoints and three OAW packages.
The minimal recipe enables all seven EGM entries plus evidence; wiki and improve
are opt-in. Bundling is distinct from triggering a workflow on an unrelated task.

| Skill | Installed by | Purpose |
|---|---|---|
| egm-bootstrap, egm-brainstorm, egm-draft | V2 default | The complete upstream document workflows, explicitly invoked |
| egm-review, egm-review-loop, egm-drift-report, egm-resolve | V2 default | The complete upstream review workflows, explicitly invoked |
| oaw-evidence | minimal | Selectively recall or record durable project evidence with source references |
| oaw-wiki | knowledge profile | Explicit raw-to-wiki rendering and verification |
| oaw-improve | --with-improve | Propose and evaluate a reusable improvement without automatically applying it |

Each package uses `<name>/SKILL.md` with name and description frontmatter. The host chooses relevant skills from metadata and reads instructions/resources on demand. OAW has no custom trigger-scanning runtime.

Codex's repository skill location is `.agents/skills/<name>/SKILL.md`. Claude Code's project skill location is `.claude/skills/<name>/SKILL.md`; the installed `CLAUDE.md` imports the shared policy but does not itself register skills. Select `--host codex` (default), `--host claude`, or `--host both` on init/migrate. The installer generates the selected native folders from one authored template source without requiring symlinks. Host additions are retained on later operations. OAW does not silently edit `.claude` settings or install plugins.

Check the native skill listing in each target host. Local schema validation alone does not verify host discovery, version eligibility, or implicit activation quality.

Use `python3 scripts/validate_skills.py` to validate the ten native packages and
`python3 scripts/sync_egm.py --check-bundled` to verify runtime hashes and every
generated adapter. The helper accepts a documented subset of frontmatter and
checks local references; it does not replace the host's full skill specification.

`oaw.py skills` lists bundled names and origins; `--skills LIST|none|default` on
init/migrate chooses native entrypoints. Migrate previews retirement and backs
up unchanged owned packages on apply; customized entrypoints block removal.
The complete runtime remains at `.oaw/integrations/egm/`. External native skills
are user/project owned. Automatic scouting, ingestion and skill promotion are
planned, not implemented by this selector.

EGM source is manifest 0.1.0, Apache-2.0, immutable commit
[`f0ba151b252c9abf1318d9fe857a43265d06de89`](https://github.com/google/elephant-goldfish-model/tree/f0ba151b252c9abf1318d9fe857a43265d06de89).
Upstream files are unchanged. Native bridges bind the project runtime path;
Claude agent adapters retain tools/model/context policy, and Codex UI adapters
preserve the upstream manual invocation policy. Neither schema nor hashes prove
actual host discovery or model benefit.

Skills must not require memory writes, self-reviews or reports after unrelated tasks. Native personal memory and usage diagnostics stay with the host. Proposed permanent skill changes need a reusable problem and evidence, not a task's step count.
