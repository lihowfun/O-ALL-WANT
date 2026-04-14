# CLI Reference

`context_hub.py` is the optional command-line helper that ships with the Agent
Memory Framework. It assumes the standard installed layout:

- `AI_CONTEXT.md`
- `VERSION.json`
- `.agents/memory.md`
- `docs/knowledge/*.md`

`docs/knowledge/index.md` and `docs/knowledge/log.md` are treated as meta pages
and are skipped by the topic listing commands. For the raw-source compiler, see
`docs/Wiki_Sync_Guide.md`.

If your machine does not provide a `python` alias, use `python3`.

## Quick Use

```bash
python3 scripts/context_hub.py status
```

## Command Summary

| Command | Purpose | Example |
|---------|---------|---------|
| `search [query]` | List matching knowledge topics | `python3 scripts/context_hub.py search "bug"` |
| `get TOPIC` | Print a topic's full markdown | `python3 scripts/context_hub.py get Known_Limitations` |
| `annotate TOPIC "NOTE"` | Append a dated annotation to a topic | `python3 scripts/context_hub.py annotate Known_Limitations "[BUG] Reproduced on Windows"` |
| `memory add "NOTE"` | Insert a newest-first memory entry | `python3 scripts/context_hub.py memory add "[DECISION] Use python3 in docs"` |
| `memory show --last N` | Show recent memory entries | `python3 scripts/context_hub.py memory show --last 5` |
| `lesson "MISTAKE" "CORRECTION"` | Record a lesson-learned note | `python3 scripts/context_hub.py lesson "Used stale baseline" "Always read VERSION.json first"` |
| `status` | Show version, recent decisions, and topics | `python3 scripts/context_hub.py status` |
| `bootstrap` | Dump startup context for a new session | `python3 scripts/context_hub.py bootstrap` |

## Commands

### `search [query]`

Searches `docs/knowledge/` by filename and content. An empty query lists every
available topic.

```bash
python3 scripts/context_hub.py search ""
```

### `get TOPIC`

Prints the complete contents of a topic file, where `TOPIC` is the filename
without `.md`.

```bash
python3 scripts/context_hub.py get Performance_Baselines
```

### `annotate TOPIC "NOTE"`

Appends a timestamped note to the topic. Prefix the note with a tag such as
`[BUG]`, `[EXPERIMENT]`, or `[INSIGHT]` when you want the annotation label to
stay structured.

```bash
python3 scripts/context_hub.py annotate Known_Limitations "[BUG] Windows lock fallback still needs native QA"
```

### `memory add "NOTE"`

Creates a newest-first entry in `.agents/memory.md`. Prefix the note with a tag
to keep memory entries easy to scan.

```bash
python3 scripts/context_hub.py memory add "[DECISION] Keep install.sh overwrite prompt explicit"
```

### `memory show --last N`

Shows the newest `N` entries from `.agents/memory.md`.

```bash
python3 scripts/context_hub.py memory show --last 3
```

### `lesson "MISTAKE" "CORRECTION"`

Shortcut for writing a structured lesson into rolling memory.

```bash
python3 scripts/context_hub.py lesson "Used python examples on a python3-only machine" "Standardize docs on python3"
```

### `status`

Shows the current version, the `do_not_rerun` count, the newest memory headers,
and the list of knowledge topics.

```bash
python3 scripts/context_hub.py status
```

### `bootstrap`

Prints the contents of `AI_CONTEXT.md`, the latest memory entries, and the
topic index. This is useful when starting a new agent session.

```bash
python3 scripts/context_hub.py bootstrap
```

## Notes

- File writes use the best available local file lock:
  - POSIX: `fcntl.flock`
  - Windows: `msvcrt.locking`
  - Fallback: unlocked write if neither backend exists
- `memory add` keeps the newest entries at the top of `.agents/memory.md`.
- `annotate` creates an `## AI Annotations` section automatically if a topic
  does not already have one.
- `status` also reports how many raw source notes exist in `docs/raw/` when the
  hybrid wiki layer is enabled.
