# Contributing to OAW

OAW owns project evidence and deterministic maintenance; native hosts own agent execution and personal memory. Keep new integrations optional unless there is a demonstrated project need.

## Validation

Use Python 3.10+ and the standard library:

```bash
python3 scripts/harness_check.py
python3 scripts/harness_check.py --verbose
```

For focused work use `python3 -m unittest discover -s tests -p 'test_NAME.py'`.
After modifying installer payloads, scripts or templates run
`python3 scripts/sync_examples.py --write`, then the gate. Do not hand-edit generated framework copies in examples. Curated demo source/topic pages and README files are maintained separately.

Behavior regressions should demonstrate a real failure, not mirror implementation text. A green schema/gate result proves its assertions, not native model quality. Preserve separate baseline/candidate evidence for model evaluations.

## Native skills

Skills live at `templates/.agents/skills/<name>/SKILL.md`. Include concise name/description frontmatter and only guidance that changes the host's decisions for OAW-specific work. No mandatory logging, generic thinking instructions, or per-task skill creation. Use `python3 scripts/validate_skills.py` for the supported schema subset.

## Migration and state

Custom project content is protected. Init must fail before payload writes on conflicts. Migrate previews by default and applies known changes with backups and receipts. Never template-manage project memory, raw/knowledge content, root version or roadmap. Add negative tests for path/type conflicts and rollback when changing installation code.

## Pull requests and releases

Explain the final behavior, why it changed, validation and compatibility impact. Update CHANGELOG and migration docs for user-visible changes. Breaking file-layout/installation changes use a major version. A proposed version in a PR is not a published release; maintainers review, merge and release separately.
