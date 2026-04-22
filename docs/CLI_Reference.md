# CLI Reference

OAW ships three command-line helpers:

- **`scripts/harness_check.py`** — one-command local health gate (8 checks;
  same as CI). Run before opening a PR.
- **`scripts/context_hub.py`** — knowledge + memory management
  (search / get / annotate / memory / status / bootstrap / lesson).
- **`scripts/wiki_sync.py`** — deterministic raw → wiki compiler with
  metadata and quality lint.

All three assume the standard installed layout:

- `AI_CONTEXT.md`
- `VERSION.json`
- `.agents/memory.md` (+ `.agents/skills/*.md`)
- `docs/knowledge/*.md` (+ `docs/raw/*.md` for raw-source compilation)

`docs/knowledge/index.md` and `docs/knowledge/log.md` are meta pages and are
skipped by topic listing commands. For the raw-source compiler, see
`docs/Wiki_Sync_Guide.md`.

If your machine does not provide a `python` alias, use `python3`.

## `harness_check.py` — local CI equivalent

```bash
./scripts/harness_check.py              # all 8 checks, summary output
./scripts/harness_check.py --verbose    # include raw stdout/stderr per check
./scripts/harness_check.py --json       # machine-readable summary
```

Checks (in order): pycompile, CLI surface, self-install refusal, fresh-install
file set, fresh-install lint, repo lint, strict placeholder detection, example
drift. Exit 0 iff all pass.

## `context_hub.py`

### Quick Use

```bash
python3 scripts/context_hub.py status
```

### Command Summary

| Command | Purpose | Example |
|---------|---------|---------|
| `search [query] [--compact]` | List matching knowledge topics | `python3 scripts/context_hub.py search "bug"` |
| `get TOPIC` | Print a topic's full markdown | `python3 scripts/context_hub.py get Known_Limitations` |
| `annotate TOPIC "NOTE"` | Append a dated annotation to a topic | `python3 scripts/context_hub.py annotate Known_Limitations "[BUG] Reproduced on Windows"` |
| `memory add "NOTE"` | Insert a newest-first memory entry | `python3 scripts/context_hub.py memory add "[DECISION] Use python3 in docs"` |
| `memory show --last N` | Show recent memory entries | `python3 scripts/context_hub.py memory show --last 5` |
| `lesson "MISTAKE" "CORRECTION"` | Record a lesson-learned note | `python3 scripts/context_hub.py lesson "Used stale baseline" "Always read VERSION.json first"` |
| `status [--compact]` | Show version, recent decisions, and topics | `python3 scripts/context_hub.py status --compact` |
| `bootstrap [--compact]` | Dump startup context for a new session | `python3 scripts/context_hub.py bootstrap --compact` |

### Commands

#### `search [query] [--compact]`

Searches `docs/knowledge/` by filename and content. An empty query lists every
available topic. Add `--compact` when you only want a one-line topic summary.

```bash
python3 scripts/context_hub.py search ""
python3 scripts/context_hub.py search "bug" --compact
```

#### `get TOPIC`

Prints the complete contents of a topic file, where `TOPIC` is the filename
without `.md`.

```bash
python3 scripts/context_hub.py get Performance_Baselines
```

#### `annotate TOPIC "NOTE"`

Appends a timestamped note to the topic. Prefix the note with a tag such as
`[BUG]`, `[EXPERIMENT]`, or `[INSIGHT]` when you want the annotation label to
stay structured.

```bash
python3 scripts/context_hub.py annotate Known_Limitations "[BUG] Windows lock fallback still needs native QA"
```

#### `memory add "NOTE"`

Creates a newest-first entry in `.agents/memory.md`. Prefix the note with a tag
to keep memory entries easy to scan.

```bash
python3 scripts/context_hub.py memory add "[DECISION] Keep install.sh overwrite prompt explicit"
```

#### `memory show --last N`

Shows the newest `N` entries from `.agents/memory.md`.

```bash
python3 scripts/context_hub.py memory show --last 3
```

#### `lesson "MISTAKE" "CORRECTION"`

Shortcut for writing a structured lesson into rolling memory.

```bash
python3 scripts/context_hub.py lesson "Used python examples on a python3-only machine" "Standardize docs on python3"
```

#### `status [--compact]`

Shows the current version, the `do_not_rerun` count, the newest memory headers,
and the list of knowledge topics. Add `--compact` for a one-line summary that is
friendlier to agent token budgets.

```bash
python3 scripts/context_hub.py status
python3 scripts/context_hub.py status --compact
```

#### `bootstrap [--compact]`

Prints the contents of `AI_CONTEXT.md`, the latest memory entries, and the
topic index. This is useful when starting a new agent session. Add `--compact`
when you want a minimal bootstrap instead of the full dump.

```bash
python3 scripts/context_hub.py bootstrap
python3 scripts/context_hub.py bootstrap --compact
```

## `wiki_sync.py` — raw → wiki compiler + lint

See [`Wiki_Sync_Guide.md`](Wiki_Sync_Guide.md) for the full compiler guide. The
subcommands most often run interactively:

```bash
python3 scripts/wiki_sync.py build                 # compile docs/raw → docs/knowledge
python3 scripts/wiki_sync.py refresh <Topic>       # recompile one topic
python3 scripts/wiki_sync.py lint                  # metadata + links + soft quality
python3 scripts/wiki_sync.py lint --strict         # also fails on unfilled
                                                   # ${...} / YYYY-MM-DD and on
                                                   # skill frontmatter violations
```

Default lint returns 0 with warnings; `--strict` promotes warnings to errors.

## Notes

- File writes use the best available local file lock:
  - POSIX: `fcntl.flock`
  - Windows: `msvcrt.locking`
  - Fallback: unlocked write if neither backend exists
- `memory add` keeps the newest entries at the top of `.agents/memory.md`.
- `annotate` creates an `## AI Annotations` section automatically if a topic
  does not already have one.
- `search`, `status`, and `bootstrap` support `--compact` for token-friendly
  summaries without changing the default full output.
- `status` also reports how many raw source notes exist in `docs/raw/` when the
  hybrid wiki layer is enabled.
