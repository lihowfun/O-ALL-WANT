# Skill Guide

Skills are reusable markdown workflows that teach agents how to handle a task
the same way every time. The bundled examples live in `.agents/skills/`, and
the starting point for your own skill is `.agents/skills/_TEMPLATE.md`.

In the hybrid router version of this framework, skills are the **execution
lane**. They sit alongside:

- the **operational lane** (`AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, recent memory)
- the **wiki lane** (`docs/knowledge/*.md`, `index.md`, `log.md`)
- the **raw source fallback** (`docs/raw/*.md`)

## When To Create A Skill

Create a skill when:

- you repeat the same task often enough that re-explaining it is annoying
- the task has known edge cases or safety checks
- the task benefits from a fixed verification or reporting step

Skip a skill when:

- the task is one-off
- the process is still changing every day
- the task is fully deterministic and should really be a script

## Anatomy Of A Skill

Every skill has two parts.

### 1. Frontmatter

```yaml
---
name: skill-name
description: "One sentence summary"
triggers: ["keyword1", "keyword2"]
params:
  PARAM1: "description | allowed values"
requires:
  - AI_CONTEXT.md
optional_reads:
  - docs/knowledge/relevant_topic.md
outputs:
  - .agents/memory.md entry
---
```

Field meanings:

- `name`: the stable slash-command style identifier
- `description`: what the skill does in one sentence
- `triggers`: words the resolver can match against user requests
- `params`: the inputs that must be filled in before execution
- `requires`: files that must be read first
- `optional_reads`: files that are helpful only for certain situations
- `outputs`: what artifacts the skill is expected to leave behind

### 2. Body

The body should include:

- a short title
- parameter definitions
- ordered execution steps
- a verification step
- a structured record step
- an `Edge Cases (Learning Block)` section

## Placeholder Conventions

The repo uses two kinds of placeholders.

### Setup-Time Placeholders

These appear in project templates such as `AI_CONTEXT.md`, `CLAUDE.md`, and the
knowledge templates. Replace them once when installing the framework into your
project.

Examples:

- `${PROJECT_NAME}`
- `${LANGUAGE}`
- `${SMOKE_TEST_CMD}`
- `${LIMITATION_1_TITLE}`

### Skill-Time Placeholders

These appear inside skills and are meant to be filled in while the skill is
being executed.

- `${PARAM_NAME}` means the value should come from the skill's `params` block.
- `${RUNTIME_VALUE}` means the skill should compute or extract the value during
  execution and substitute it into the command or report.

Common bundled examples:

| Placeholder | Meaning |
|-------------|---------|
| `${MODEL_PATH}` | The model, checkpoint, or config being evaluated |
| `${EVAL_COMMAND}` | The exact benchmark command to run |
| `${PRIMARY_METRIC}` / `${SECONDARY_METRICS}` | Metrics to extract from output |
| `${VALUE}` / `${DELTA}` / `${NEW_VALUE}` | Measured result values |
| `${EXPERIMENT_NAME}` / `${summary}` | Structured experiment identifiers and summaries |
| `${ERROR_MSG}` / `${ROOT_CAUSE}` / `${SOLUTION}` | Debug-report fields |
| `${NEW_VERSION}` / `${RELEASE_BRANCH}` | Release inputs |

If you add a new placeholder, explain it either:

- in the `params` block
- in the nearby prose
- or in the command block immediately above where it is used

## Writing A New Skill

1. Copy the template:

```bash
cp .agents/skills/_TEMPLATE.md .agents/skills/my-skill.md
```

2. Fill in the frontmatter.
3. Replace every `${...}` token.
4. Make the verification step explicit.
5. End with a memory write and, when useful, a knowledge annotation.

## Example Skill

````markdown
---
name: cleanup-logs
description: "Archive old logs and record what was removed"
triggers: ["cleanup logs", "archive logs"]
params:
  LOG_DIR: "directory containing log files"
  DAYS: "minimum age in days"
requires:
  - AI_CONTEXT.md
outputs:
  - .agents/memory.md entry
---

# /cleanup-logs — Archive Old Logs

## Parameters
- **LOG_DIR**: Directory containing logs
- **DAYS**: Minimum age threshold

## Steps
1. Confirm `LOG_DIR` exists.
2. Preview candidate files with `find "$LOG_DIR" -type f -mtime +"$DAYS"`.
3. Move approved files into an archive folder.
4. Verify the archive count.
5. Record the result:

```bash
python3 scripts/context_hub.py memory add "[WORKAROUND] Archived old logs from ${LOG_DIR} older than ${DAYS} days"
```
````

## Bundled Skills

The installed framework includes these reference skills:

- `self-improving.md`
- `benchmark.md`
- `experiment-report.md`
- `debug-pipeline.md`
- `version-release.md`
- `wiki-refresh.md`

Read them before writing your own. They show how to combine deterministic steps,
judgment calls, and mandatory reporting.
