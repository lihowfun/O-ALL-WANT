# LLM Wiki Pipeline

OAW borrows the strongest part of large markdown knowledge bases: separate the
research trail from the compact page agents actually read.

## Pipeline

| Stage | Output | Gate |
|-------|--------|------|
| 0. Scope | Topic ID, owner, related topics | It belongs in wiki, not only memory |
| 1. Gather | `docs/raw/<source>.md` | Source has title, summary, date, topic ID |
| 2. Compile | `docs/knowledge/<topic>.md` | `wiki_sync.py refresh <topic>` succeeds |
| 3. Verify | Updated links and metadata | `wiki_sync.py lint` passes |
| 4. Connect | `related_topics` and index/log updated | Topic is discoverable by search |
| 5. Promote | Optional `.agents/skills/<workflow>.md` | The procedure repeats across sessions |

## Stage Rules

### 0. Scope

Use the wiki for durable project knowledge:

- architecture decisions
- recurring failure modes
- benchmark baselines
- release lessons
- cross-agent collaboration rules
- workflows that are almost ready to become skills

Keep one-off status updates in `.agents/memory.md` until a pattern repeats.

### 1. Gather

Start from `docs/raw/_SOURCE_TEMPLATE.md`. Raw notes can be longer than compiled
topic pages because they preserve context that may be useful later but should
not be loaded by default.

Every source note should answer:

- What happened?
- Why does it matter for future agents?
- Which files, commands, issues, PRs, or reports back it up?
- Which topic page should receive the distilled version?

### 2. Compile

Run:

```bash
python3 scripts/wiki_sync.py refresh <topic>
```

Compiled pages are optimized for retrieval. They should be short enough for an
agent to read during a task without loading the whole repository history.

### 3. Verify

Run:

```bash
python3 scripts/wiki_sync.py lint
```

The lint gate checks metadata, source refs, links, stale compiled pages, orphan
topics, placeholder leaks, and light quality signals.

### 4. Connect

Add `related_topics` when another topic helps interpret the page. A topic with
no links and no sources is a weak retrieval node unless it is intentionally
standalone.

### 5. Promote

Promote a topic to `.agents/skills/` when the page describes a repeatable
procedure with a clear trigger, required reads, commands, verification, and
known edge cases.

## Failure Modes

- **Raw drift**: raw notes changed but the compiled topic was not refreshed.
- **Manual overwrite risk**: a generated topic is edited directly instead of
  refreshing from `docs/raw/`.
- **AI slop**: a page uses polished but unsourced prose with no concrete files,
  dates, commands, or decisions.
- **Skill delay**: a repeated process stays in the wiki forever and never
  becomes an executable skill.
