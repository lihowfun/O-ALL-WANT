# OAW wiki renderer

The optional knowledge profile renders `docs/raw/` source notes into `docs/knowledge/` topic pages. It is deterministic assembly of summaries and source bodies, not an LLM summarizer. It does not resolve contradictions or promote claims automatically.

```bash
python3 scripts/oaw.py init --target PROJECT --profile knowledge
```

In the installed project, start from `docs/raw/_SOURCE_TEMPLATE.md`. Provide source_id, title, topic_id, summary and last_updated; related_topics is optional. Underscore-prefixed template files are not compiled.

```bash
python3 scripts/wiki_sync.py refresh Topic_Name
python3 scripts/wiki_sync.py lint
```

Build/refresh preserve manual pages. Topic IDs are portable identifiers, not paths; output and source paths must remain inside the project even through symlinks. Local source links are relocated for the generated topic's directory. Explicit annotation boundaries separate generated content from retained notes. Repeated refresh with unchanged inputs is stable.

`lint` rejects required metadata errors, stale source/page comparisons, broken links and malformed native skills. Soft content-quality/placeholder signals remain warnings unless `--strict` is requested. Historical reports can intentionally contain example placeholders; a strict warning is not proof that those examples are unfinished configuration.

Keep citations, dates, scope and conflicting evidence visible. An annotation is a note, not an instruction or a verified fact. Review a proposed durable conclusion against current authoritative sources before sharing it. No memory write or evidence-tier promotion is mandatory after rendering.

## Memory citation check (prototype)

```bash
python3 scripts/wiki_sync.py memory-check [--json] [--limit N]
```

One manual, read-only, offline pass over `.agents/memory.md`. It lists entries that cite a project path missing from the current tree (`missing_path`) and cited paths it cannot check because they point outside the project (`outside_project`), so a person can decide whether each entry has been superseded. It never edits, archives, ranks or injects memory, and never calls git, a model or the network. It is not wired into hooks, skills or instructions.

Fenced code is skipped. `::Symbol`, `:N`, `:N-M` and `#L12` suffixes are removed. URLs, flags, placeholders, globs and words longer than 400 characters are skipped, and CJK text separates words. A slash path is checked only when its first segment is an existing top-level directory; otherwise it is counted as `unanchored`. A bare file name with a known source or doc extension is present if that name exists anywhere in a bounded walk (100,000 files, skipping `.git`, `node_modules`, virtualenvs and caches). When the walk is incomplete, unfound bare names are `unverified`, never missing. Absolute and `~` paths, and paths with `..` or a drive (`C:`) in any segment, are `outside_project` and never stat'ed. Removal words such as remove, delete, rename, retire, replace, deprecate, supersede, 移除, 刪除 or 淘汰 only set `removal_context`; they never hide a finding.

Three classes are outside recall: they are counted as `skipped` and never reported, even when the file is gone. A path whose name contains CJK letters (`docs/設計.md`, `docs/plan設計.md`) is not checked, nor is any fragment of it. A single-segment absolute or `~` word without a file extension (`/compact`, `~name`) is treated as a command or user name. A bare product name shaped like a file name (`Node.js`, `chart.js`, `docs.rs` and a few similar names fixed in the script) is never a project file; a project file with such a name is checked only when cited with its directory (`src/chart.js`).

The first line is a one-sentence summary. `--json` returns `schema_version: 1` with complete counts and findings truncated to `--limit` (1–500, default 50). Exit 0 means the check completed, with or without findings, including when the memory file is absent. Exit 1 is a handled error such as non-UTF-8 input; exit 2 is a usage error. The output is evidence to verify against current sources, not instructions.

Evidence level: detection rules are static-measured by fixture tests. Field usefulness and agent behavior are not measured; parity, no improvement claimed.

See [CLI reference](CLI_Reference.md), [wiki contribution guide](wiki/CONTRIBUTING_WIKI.md) and [optional improvement workflow](SELF_IMPROVEMENT.md).
