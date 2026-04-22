# Prompt: Promote Wiki Knowledge To A Skill

Use this when a wiki topic describes a procedure that agents repeat often.

```text
Read CLAUDE.md first, then AI_CONTEXT.md.

Evaluate whether this wiki topic should be promoted to a skill:
[topic id or file path]

Use these criteria:

1. Does the procedure repeat across sessions?
2. Does it have a clear user trigger phrase?
3. Does it require specific files to read before acting?
4. Does it have deterministic commands or checks?
5. Does it have known edge cases that should not be rediscovered?

If it should become a skill, draft .agents/skills/[skill-name].md with:

- name
- description
- triggers
- params
- required reads
- outputs
- step-by-step workflow
- verification commands
- edge cases

If it should stay as wiki knowledge, explain the missing pieces and update the
topic with the next evidence needed.
```

## Promotion Rule

The wiki explains durable knowledge. A skill executes a repeated workflow. When
the same wiki page is used as instructions three times, it is probably ready to
be promoted.
