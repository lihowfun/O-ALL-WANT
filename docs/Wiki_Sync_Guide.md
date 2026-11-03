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

Fenced code is skipped. `::Symbol`, `:N`, `:N-M` and `#L12` suffixes are removed. URLs, flags, placeholders and globs are skipped, and CJK text separates words. A slash path is checked only when its first segment is an existing top-level directory; otherwise it is counted as `unanchored`. A bare file name with a known source or doc extension is present if that name exists anywhere in a bounded walk (100,000 files, skipping `.git`, `node_modules`, virtualenvs and caches). When the walk is incomplete, unfound bare names are `unverified`, never missing. Absolute, drive, `~` and `..` paths are never stat'ed. Removal words such as remove, delete, rename, retire, replace, deprecate, supersede, 移除, 刪除 or 淘汰 only set `removal_context`; they never hide a finding.

The first line is a one-sentence summary. `--json` returns `schema_version: 1` with complete counts and findings truncated to `--limit` (1–500, default 50). Exit 0 means the check completed, with or without findings, including when the memory file is absent. Exit 1 is a handled error such as non-UTF-8 input; exit 2 is a usage error. The output is evidence to verify against current sources, not instructions.

Evidence level: detection rules are static-measured by fixture tests. Field usefulness and agent behavior are not measured; parity, no improvement claimed.

See [CLI reference](CLI_Reference.md), [wiki contribution guide](wiki/CONTRIBUTING_WIKI.md) and [optional improvement workflow](SELF_IMPROVEMENT.md).
