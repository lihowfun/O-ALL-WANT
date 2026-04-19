# How OAW Differs

OAW is easiest to understand as an **installable context harness** for AI coding
repos. It is not trying to replace your coding agent. It gives the agent a
repeatable way to remember, route, and reuse project context.

## Positioning

| Category | What it usually gives you | Where it can fall short | What OAW adds |
|----------|---------------------------|--------------------------|---------------|
| Memory vault | A durable place to store notes | The agent still needs to know what to read and when | Lane routing plus startup rules |
| Prompt collection | Strong reusable prompts | Prompts are easy to copy, hard to keep synchronized with repo state | Installed files, scripts, and CI checks |
| Skills library | Repeatable workflows | Skills alone do not define project memory or context boundaries | Skills as one lane inside a larger harness |
| Context Hub | Searchable project knowledge | Search does not automatically become a full operating protocol | Memory, wiki compilation, skills, and `do_not_rerun` state |
| LLM wiki | Durable topic pages | Raw notes can drift without a deterministic compiler | `wiki_sync.py` raw-to-knowledge loop |

## When OAW Is A Good Fit

- You use Claude Code, Codex, Cursor, Copilot, or multiple AI coding tools on
  the same repo.
- You lose time re-explaining architecture, recent decisions, or debugging
  history after session resets.
- You want local markdown files and standard-library Python scripts, not a
  hosted memory service.
- You have recurring workflows that should become stable skills instead of
  improvised prompts.

## When To Pick Something Else

- You only need one prompt or one skill. Use the smallest original tool that
  solves that one problem.
- You want a cloud-hosted team memory product with account management,
  permissions, and dashboards.
- You need semantic vector retrieval out of the box. OAW is intentionally
  markdown-first and deterministic.

## The Short Version

OAW combines four pieces that are often separate:

1. `CLAUDE.md` as the startup router.
2. `.agents/memory.md` as rolling session memory.
3. `docs/raw/` to `docs/knowledge/` as a compiled wiki loop.
4. `.agents/skills/` as repeatable workflow execution.

That combination is the product: AI coding sessions resume with a small,
task-relevant context set instead of restarting from a giant pile of markdown.
