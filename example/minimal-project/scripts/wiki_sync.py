#!/usr/bin/env python3
"""
Wiki Sync — deterministic compiler for docs/raw -> docs/knowledge.

This tool keeps durable topic pages compact and searchable while letting teams
store longer raw source notes separately. It is intentionally markdown-first
and vector-DB-free.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime

BASE_DIR = os.environ.get("AGENT_MEMORY_BASE_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
RAW_DIR = os.path.join(BASE_DIR, "docs", "raw")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "docs", "knowledge")
META_FILES = {"index.md", "log.md"}


def _parse_frontmatter(content):
    """Parse a minimal YAML-like frontmatter block if present."""
    if not content.startswith("---\n"):
        return {}, content

    lines = content.splitlines()
    closing_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_index = i
            break

    if closing_index is None:
        return {}, content

    metadata = {}
    current_key = None
    current_list = None

    for raw_line in lines[1:closing_index]:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            if current_list is None:
                current_list = []
                metadata[current_key] = current_list
            current_list.append(stripped[2:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value:
            metadata[current_key] = value
            current_list = None
        else:
            current_list = []
            metadata[current_key] = current_list

    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    return metadata, body


def _normalize_list(value):
    """Normalize a scalar or list-like value into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",")]
            return [item for item in items if item]
        return [value]
    return [str(value)]


def _topic_title(topic_id):
    """Convert a topic id into a readable heading."""
    return topic_id.replace("_", " ")


def _today():
    return date.today().isoformat()


def _safe_read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _body_without_h1(body):
    """Drop a leading h1 from raw source notes to avoid duplicate page titles."""
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).lstrip("\n")
    return body.strip()


def _first_paragraph(body):
    """Use the first non-heading paragraph as a fallback summary."""
    paragraphs = []
    current = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if stripped.startswith("#"):
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs[0] if paragraphs else "No summary provided."


def _discover_raw_sources():
    """Load all raw source notes from docs/raw/."""
    sources = []
    if not os.path.exists(RAW_DIR):
        return sources

    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.endswith(".md"):
            continue
        if filename.startswith("_") or filename.lower() == "readme.md":
            continue

        path = os.path.join(RAW_DIR, filename)
        content = _safe_read(path)
        metadata, body = _parse_frontmatter(content)
        topic_id = metadata.get("topic_id") or os.path.splitext(filename)[0].replace(" ", "_")
        source_id = metadata.get("source_id") or os.path.splitext(filename)[0]
        title = metadata.get("title") or _topic_title(source_id)
        summary = metadata.get("summary") or _first_paragraph(body)
        last_updated = metadata.get("last_updated") or _today()
        related_topics = sorted(
            topic
            for topic in set(_normalize_list(metadata.get("related_topics")))
            if topic and topic != topic_id
        )

        sources.append(
            {
                "metadata": metadata,
                "filename": filename,
                "path": path,
                "relative_path": os.path.join("docs", "raw", filename).replace("\\", "/"),
                "source_id": source_id,
                "topic_id": topic_id,
                "title": title,
                "summary": summary,
                "last_updated": last_updated,
                "related_topics": related_topics,
                "body": _body_without_h1(body) or "_No additional source notes._",
            }
        )

    return sources


def _load_knowledge_pages(include_meta=False):
    """Load current knowledge pages from docs/knowledge/."""
    pages = []
    if not os.path.exists(KNOWLEDGE_DIR):
        return pages

    for filename in sorted(os.listdir(KNOWLEDGE_DIR)):
        if not filename.endswith(".md"):
            continue
        if not include_meta and filename in META_FILES:
            continue

        path = os.path.join(KNOWLEDGE_DIR, filename)
        content = _safe_read(path)
        metadata, body = _parse_frontmatter(content)
        page_type = metadata.get("page_type", "topic")
        if not include_meta and page_type == "meta":
            continue

        page_id = metadata.get("id") or os.path.splitext(filename)[0]
        title = metadata.get("title")
        if not title:
            for line in body.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        pages.append(
            {
                "metadata": metadata,
                "filename": filename,
                "path": path,
                "id": page_id,
                "title": title or _topic_title(page_id),
                "page_type": page_type,
                "build_origin": metadata.get("build_origin", "manual"),
                "source_refs": _normalize_list(metadata.get("source_refs")),
                "related_topics": _normalize_list(metadata.get("related_topics")),
                "last_updated": metadata.get("last_updated", ""),
                "content": content,
                "body": body,
            }
        )

    return pages


def _render_frontmatter(fields):
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _extract_ai_annotations(existing_content):
    """Preserve the AI Annotations section across deterministic rebuilds."""
    marker = "\n## AI Annotations\n"
    if marker not in existing_content:
        return ""
    return existing_content.split(marker, 1)[1].strip()


def _render_topic_page(topic_id, sources, existing_annotations=""):
    """Compile all raw sources for a topic into one durable knowledge page."""
    # Prefer the first raw source's title (preserves user's casing); fall back
    # to deriving from the topic_id.
    title = next((s["title"] for s in sources if s.get("title")), None) or _topic_title(topic_id)
    related_topics = sorted(
        topic
        for topic in set(
            linked_topic
            for source in sources
            for linked_topic in source["related_topics"]
        )
        if topic and topic != topic_id
    )
    source_refs = sorted(source["relative_path"] for source in sources)
    last_updated = max(source["last_updated"] for source in sources)

    sections = [
        _render_frontmatter(
            {
                "id": topic_id,
                "title": title,
                "page_type": "topic",
                "build_origin": "wiki_sync",
                "source_refs": source_refs,
                "last_updated": last_updated,
                "related_topics": related_topics,
            }
        ),
        f"# {title}",
        "",
        "> Generated from `docs/raw/` notes by `python3 scripts/wiki_sync.py refresh "
        f"{topic_id}`. Edit raw sources first, then rebuild.",
        "",
        "## Summary",
    ]

    for source in sources:
        sections.append(f"- **{source['title']}**: {source['summary']}")

    sections.extend(["", "## Compiled Source Notes"])
    for source in sources:
        sections.extend(
            [
                "",
                f"### {source['title']}",
                f"- Source ref: `{source['relative_path']}`",
                f"- Source ID: `{source['source_id']}`",
                f"- Last updated: {source['last_updated']}",
            ]
        )
        if source["related_topics"]:
            sections.append("- Related topics: " + ", ".join(f"`{item}`" for item in source["related_topics"]))
        sections.extend(["", source["body"].strip()])

    if related_topics:
        sections.extend(["", "## Related Topics"])
        for related_topic in related_topics:
            sections.append(f"- `{related_topic}`")

    sections.extend(["", "## AI Annotations", ""])
    if existing_annotations:
        sections.append(existing_annotations)
    else:
        sections.extend(
            [
                "<!-- Auto-appended by agents via: python3 scripts/context_hub.py annotate "
                f"{topic_id} \"note\" -->",
                "",
            ]
        )

    return "\n".join(sections)


def _render_index(pages):
    """Render the generated knowledge index page."""
    generated_at = _today()
    lines = [
        _render_frontmatter(
            {
                "id": "index",
                "title": "Knowledge Index",
                "page_type": "meta",
                "build_origin": "wiki_sync",
                "last_updated": generated_at,
                "related_topics": [],
            }
        ),
        "# Knowledge Index",
        "",
        "> Generated by `python3 scripts/wiki_sync.py build`. Read this only when you",
        "> need the knowledge map; it is not a startup-default file.",
        "",
        "| Topic ID | Title | Source Count | Last Updated | Related Topics |",
        "|----------|-------|--------------|--------------|----------------|",
    ]

    for page in sorted(pages, key=lambda item: item["id"].lower()):
        related = ", ".join(page["related_topics"]) if page["related_topics"] else "—"
        source_count = len(page["source_refs"])
        lines.append(
            f"| `{page['id']}` | {page['title']} | {source_count} | "
            f"{page['last_updated'] or '—'} | {related} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Compiled topics list raw source refs in frontmatter.",
            "- Manual pages can stay in `docs/knowledge/` if they still obey the same",
            "  metadata contract (`id`, `last_updated`, `related_topics`).",
            "",
        ]
    )
    return "\n".join(lines)


def _render_log(pages):
    """Render the generated sync ledger."""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        _render_frontmatter(
            {
                "id": "log",
                "title": "Knowledge Sync Log",
                "page_type": "meta",
                "build_origin": "wiki_sync",
                "last_updated": _today(),
                "related_topics": [],
            }
        ),
        "# Knowledge Sync Log",
        "",
        f"> Generated at {generated_at}. `refresh <topic>` should only touch the target",
        "> topic plus this file and `index.md`.",
        "",
        "| Topic ID | Mode | Source Count | Last Updated |",
        "|----------|------|--------------|--------------|",
    ]

    for page in sorted(pages, key=lambda item: item["id"].lower()):
        mode = "compiled" if page["build_origin"] == "wiki_sync" else "manual"
        lines.append(
            f"| `{page['id']}` | {mode} | {len(page['source_refs'])} | "
            f"{page['last_updated'] or '—'} |"
        )

    lines.append("")
    return "\n".join(lines)


def _build_meta_pages():
    pages = _load_knowledge_pages()
    _write(os.path.join(KNOWLEDGE_DIR, "index.md"), _render_index(pages))
    _write(os.path.join(KNOWLEDGE_DIR, "log.md"), _render_log(pages))
    return pages


def _build_topic_pages(topic_filter=None):
    """Compile all matching raw topics. Returns a list of written topic ids."""
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    grouped_sources = defaultdict(list)
    for source in _discover_raw_sources():
        grouped_sources[source["topic_id"]].append(source)

    if topic_filter and topic_filter != "all" and topic_filter not in grouped_sources:
        raise ValueError(f"No raw sources found for topic '{topic_filter}'.")

    written = []
    for topic_id, sources in sorted(grouped_sources.items()):
        if topic_filter not in (None, "all") and topic_id != topic_filter:
            continue

        target_path = os.path.join(KNOWLEDGE_DIR, f"{topic_id}.md")
        existing_annotations = ""
        if os.path.exists(target_path):
            existing_content = _safe_read(target_path)
            metadata, _ = _parse_frontmatter(existing_content)
            origin = metadata.get("build_origin", "manual")
            if origin != "wiki_sync":
                raise ValueError(
                    f"Refusing to overwrite manual page '{topic_id}'. "
                    "Rename the raw topic or migrate the page metadata first."
                )
            existing_annotations = _extract_ai_annotations(existing_content)

        _write(target_path, _render_topic_page(topic_id, sources, existing_annotations=existing_annotations))
        written.append(topic_id)

    return written


def build():
    """Rebuild all compiled topic pages plus index/log."""
    written = _build_topic_pages()
    pages = _build_meta_pages()
    print(f"✅ Wiki build complete. Compiled {len(written)} topic(s).")
    print(f"📚 Knowledge pages indexed: {len(pages)}")


def refresh(topic):
    """Refresh one topic or all topics, then rebuild index/log."""
    written = _build_topic_pages(topic_filter=topic)
    _build_meta_pages()
    if topic == "all":
        print(f"✅ Refreshed all compiled topics ({len(written)} total).")
    else:
        print(f"✅ Refreshed topic '{topic}'.")


def _relative_path(from_path, target):
    """Resolve a repo-relative markdown link against the current file."""
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    normalized = target.split("#", 1)[0]
    if not normalized:
        return None
    if os.path.isabs(normalized):
        return normalized
    return os.path.normpath(os.path.join(os.path.dirname(from_path), normalized))


def _extract_markdown_links(content):
    """Return relative markdown targets mentioned in the document body."""
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", content)


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


PLACEHOLDER_PATTERNS = (
    (re.compile(r"\$\{[A-Za-z0-9_]+\}"), "unfilled `${...}` placeholder"),
    # Match literal YYYY-MM-DD but not real ISO dates like 2026-04-17.
    (re.compile(r"\bYYYY-MM-DD\b"), "literal `YYYY-MM-DD` date placeholder"),
)
PLACEHOLDER_SKIP_BASENAMES = {
    "_TEMPLATE.md",
    "_SOURCE_TEMPLATE.md",
    "README.md",
}

REQUIRED_RAW_FIELDS = ("source_id", "title", "topic_id", "summary", "last_updated")
REQUIRED_KNOWLEDGE_FIELDS = ("id", "title", "page_type", "last_updated", "related_topics")
HOLLOW_PHRASES = (
    "best practice",
    "enhance",
    "ensure",
    "improve",
    "leverage",
    "optimize",
    "robust",
    "seamless",
    "streamline",
)

# Skill lint: at least one of `triggers` / `outputs` must be present in frontmatter,
# and the body must have an execution-structure heading we recognise. `Rules` is
# allowed so protocol-style skills (e.g. self-improving) without step-by-step
# workflows still pass.
SKILL_FRONTMATTER_REQUIRED_ANY = ("triggers", "outputs")
SKILL_BODY_STRUCTURE_PATTERNS = (
    re.compile(r"^##+\s+Steps\b", re.MULTILINE),
    re.compile(r"^###+\s+Step\s+\d+", re.MULTILINE),
    re.compile(r"^##+\s+Rules\b", re.MULTILINE),
    re.compile(r"^###+\s+Rule\s+\d+", re.MULTILINE),
    re.compile(r"^##+\s+Workflow\b", re.MULTILINE),
    re.compile(r"^##+\s+Procedure\b", re.MULTILINE),
)
SKILL_SKIP_BASENAMES = {"README.md"}


def _discover_skill_files():
    """Locate `.agents/skills/*.md` — works for both self-hosting and user installs.

    Returns a list of absolute paths. Prefers `templates/.agents/skills/` (canonical
    for OAW itself) and falls back to `.agents/skills/` (how user installs look).
    Skips `README.md` and any underscore-prefixed fixtures.
    """
    candidates = [
        os.path.join(BASE_DIR, "templates", ".agents", "skills"),
        os.path.join(BASE_DIR, ".agents", "skills"),
    ]
    seen = set()
    files = []
    for skill_dir in candidates:
        if not os.path.isdir(skill_dir):
            continue
        for filename in sorted(os.listdir(skill_dir)):
            if not filename.endswith(".md"):
                continue
            if filename in SKILL_SKIP_BASENAMES or filename.startswith("_"):
                continue
            full = os.path.join(skill_dir, filename)
            if full in seen:
                continue
            seen.add(full)
            files.append(full)
    return files


def _lint_skill_file(path):
    """Return a list of issue strings for a single skill markdown file.

    Empty list means the skill passed. Issues cover:
      - missing frontmatter entirely
      - neither `triggers` nor `outputs` present in frontmatter
      - no execution-structure heading (Steps / Rule / Workflow / Procedure)
    """
    issues = []
    try:
        content = _safe_read(path)
    except OSError as exc:
        return [f"skill file unreadable: {exc}"]

    metadata, body = _parse_frontmatter(content)
    rel_path = os.path.relpath(path, BASE_DIR)

    if not metadata:
        issues.append(f"skill missing frontmatter block: {rel_path}")
        return issues

    if not any(metadata.get(field) for field in SKILL_FRONTMATTER_REQUIRED_ANY):
        issues.append(
            f"skill missing required frontmatter (need at least one of "
            f"{', '.join(SKILL_FRONTMATTER_REQUIRED_ANY)}): {rel_path}"
        )

    if not any(pattern.search(body) for pattern in SKILL_BODY_STRUCTURE_PATTERNS):
        issues.append(
            f"skill body has no execution-structure heading "
            f"(Steps / Rules / Workflow / Procedure): {rel_path}"
        )

    return issues


def _scan_placeholders(paths):
    """Yield (path, lineno, pattern_desc, snippet) for placeholder hits."""
    for path in paths:
        basename = os.path.basename(path)
        if basename in PLACEHOLDER_SKIP_BASENAMES or basename.startswith("_"):
            continue
        try:
            content = _safe_read(path)
        except OSError:
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            for pattern, desc in PLACEHOLDER_PATTERNS:
                if pattern.search(line):
                    yield path, lineno, desc, line.strip()[:120]


def _missing_metadata(metadata, required_fields):
    """Return required metadata keys that are absent or empty."""
    missing = []
    for field in required_fields:
        if field not in metadata:
            missing.append(field)
            continue
        value = metadata.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def _content_lines(body):
    """Return prose-ish lines used by lightweight quality checks."""
    lines = []
    in_fence = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        if stripped.startswith(("#", "|", ">", "---")):
            continue
        lines.append(stripped)
    return lines


def _has_concrete_signal(body):
    """Detect whether a page contains anchors beyond generic prose."""
    return bool(
        re.search(r"\b20\d{2}-\d{2}-\d{2}\b", body)
        or re.search(r"\b20\d{2}\b", body)
        or re.search(r"`[^`]+`", body)
        or re.search(r"https?://", body)
        or re.search(r"\[[^\]]+\]\([^)]+\)", body)
        or re.search(r"\b\d+(?:\.\d+)?%?\b", body)
    )


def _hollow_phrase_hits(body):
    """Return hollow prose phrases found in the page body."""
    hits = []
    lowered = body.lower()
    for phrase in HOLLOW_PHRASES:
        count = lowered.count(phrase)
        if count:
            hits.append((phrase, count))
    return hits


def lint(strict=False):
    """Check metadata quality for docs/raw and docs/knowledge.

    ``strict=True`` also flags unfilled placeholders (``${...}`` and literal
    ``YYYY-MM-DD``). Default keeps quality smells warn-only so existing users
    get guidance without breaking docs-only PRs.
    """
    issues = []
    warnings = []
    raw_sources = _discover_raw_sources()
    knowledge_pages = _load_knowledge_pages()
    placeholder_scan_pages = knowledge_pages
    if strict:
        # Strict mode is the opt-in "everything still carrying placeholders"
        # gate, so include template topics and meta pages on that path only.
        placeholder_scan_pages = _load_knowledge_pages(include_meta=True)
    pages_by_id = defaultdict(list)
    raw_sources_by_ref = {source["relative_path"]: source for source in raw_sources}

    raw_source_ids = defaultdict(list)
    for source in raw_sources:
        missing_raw_fields = _missing_metadata(source["metadata"], REQUIRED_RAW_FIELDS)
        if missing_raw_fields:
            issues.append(
                f"raw source missing required metadata in {source['relative_path']}: "
                + ", ".join(missing_raw_fields)
            )

        raw_date = _parse_date(source["last_updated"])
        if source["last_updated"] and raw_date is None:
            issues.append(
                f"raw source has invalid last_updated in {source['relative_path']}: "
                f"{source['last_updated']}"
            )

        raw_source_ids[source["source_id"]].append(source["relative_path"])
        if not source["topic_id"]:
            issues.append(f"raw source missing topic_id: {source['relative_path']}")
        if not source["summary"]:
            issues.append(f"raw source missing summary: {source['relative_path']}")
        for link in _extract_markdown_links(source["body"]):
            resolved = _relative_path(source["path"], link)
            if resolved and not os.path.exists(resolved):
                issues.append(f"broken raw link in {source['relative_path']}: {link}")

    for source_id, refs in raw_source_ids.items():
        if len(refs) > 1:
            issues.append(f"duplicate raw source_id '{source_id}': {', '.join(refs)}")

    for page in knowledge_pages:
        missing_page_fields = _missing_metadata(page["metadata"], REQUIRED_KNOWLEDGE_FIELDS)
        if missing_page_fields:
            issues.append(
                f"knowledge page missing required metadata in {page['filename']}: "
                + ", ".join(missing_page_fields)
            )

        page_date = _parse_date(page["last_updated"])
        if page["last_updated"] and page_date is None:
            message = (
                f"knowledge page has invalid last_updated in {page['filename']}: "
                f"{page['last_updated']}"
            )
            if page["build_origin"] == "template":
                warnings.append(message)
            else:
                issues.append(message)

        if page["page_type"] == "topic":
            if page["build_origin"] == "manual" and not page["source_refs"] and not page["metadata"].get("source"):
                warnings.append(
                    f"manual topic has no source refs in {page['filename']}: "
                    "add docs/raw source refs or stable source metadata when practical"
                )

            content_lines = _content_lines(page["body"])
            if len(content_lines) < 4:
                warnings.append(
                    f"thin topic body in {page['filename']}: add durable facts or keep it in memory until ready"
                )
            elif len(page["body"]) > 600 and not _has_concrete_signal(page["body"]):
                warnings.append(
                    f"low-concrete topic body in {page['filename']}: add files, commands, dates, links, or measurements"
                )

            hollow_hits = _hollow_phrase_hits(page["body"])
            hollow_total = sum(count for _, count in hollow_hits)
            if hollow_total >= 5:
                phrases = ", ".join(f"{phrase} ({count})" for phrase, count in hollow_hits)
                warnings.append(
                    f"possible generic prose in {page['filename']}: {phrases}"
                )

        pages_by_id[page["id"]].append(page["filename"])
        if page["page_type"] != "topic":
            issues.append(f"non-topic page left outside meta set: {page['filename']}")
        for source_ref in page["source_refs"]:
            resolved = os.path.normpath(os.path.join(BASE_DIR, source_ref))
            if not os.path.exists(resolved):
                issues.append(f"missing source ref in {page['filename']}: {source_ref}")
        for related_topic in page["related_topics"]:
            if related_topic == page["id"]:
                issues.append(f"self-referential related topic in {page['filename']}: {related_topic}")
        for link in _extract_markdown_links(page["body"]):
            resolved = _relative_path(page["path"], link)
            if resolved and not os.path.exists(resolved):
                issues.append(f"broken knowledge link in {page['filename']}: {link}")

    for page_id, filenames in pages_by_id.items():
        if len(filenames) > 1:
            issues.append(f"duplicate topic id '{page_id}': {', '.join(filenames)}")

    known_page_ids = set(pages_by_id.keys())
    inbound_links = defaultdict(int)
    for page in knowledge_pages:
        for related_topic in page["related_topics"]:
            if related_topic not in known_page_ids:
                warnings.append(f"unresolved related topic in {page['filename']}: {related_topic}")
            inbound_links[related_topic] += 1

        if page["source_refs"]:
            source_dates = []
            for source_ref in page["source_refs"]:
                source = raw_sources_by_ref.get(source_ref)
                if source:
                    source_date = _parse_date(source["last_updated"])
                    if source_date:
                        source_dates.append(source_date)
            if source_dates and page_date and page_date < max(source_dates):
                issues.append(f"stale page '{page['id']}': raw source newer than page metadata")

        if not page["source_refs"] and not page["related_topics"] and inbound_links[page["id"]] == 0:
            # Singleton pages (no source refs, no cross-links) are a soft signal,
            # not a hard error — a repo with one curated note is fine.
            warnings.append(f"orphan page '{page['id']}': no sources and no topic links")

    # Placeholder scan — default lint stays quiet on shipped template pages,
    # but strict mode should still fail on a fresh install until placeholders
    # are filled in.
    scan_paths = [
        page["path"] for page in placeholder_scan_pages
        if strict or page.get("build_origin") != "template"
    ]
    scan_paths.extend(source["path"] for source in raw_sources)
    for path, lineno, desc, snippet in _scan_placeholders(scan_paths):
        rel = os.path.relpath(path, BASE_DIR)
        warnings.append(f"{desc} in {rel}:{lineno}: {snippet}")

    # Skill frontmatter lint — warn by default, promote to error under --strict.
    # Skills are the surface users write most often, so catching "forgot triggers"
    # or "no Steps section" early prevents a whole class of silent dispatch bugs.
    for skill_path in _discover_skill_files():
        for skill_issue in _lint_skill_file(skill_path):
            warnings.append(skill_issue)

    if warnings:
        label = "❌" if strict else "⚠️"
        verb = "errors" if strict else "warnings"
        print(f"{label} wiki_sync lint {verb} — {len(warnings)} soft issue(s):")
        for warning in warnings:
            print(f"  - {warning}")
        if strict:
            issues.extend(warnings)

    if issues:
        print("❌ wiki_sync lint found unresolved issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("✅ wiki_sync lint passed — no unresolved issues found.")
    return 0


EXPERIMENT_LOG_PATH = os.path.join(KNOWLEDGE_DIR, "EXPERIMENT_LOG.md")
CURRENT_STATE_PATH = os.path.join(KNOWLEDGE_DIR, "CURRENT_STATE.md")


def _ensure_experiment_log():
    """Create EXPERIMENT_LOG.md with a default header if it does not exist."""
    if os.path.exists(EXPERIMENT_LOG_PATH):
        return
    header = [
        _render_frontmatter(
            {
                "id": "EXPERIMENT_LOG",
                "title": "Experiment Log",
                "page_type": "topic",
                "build_origin": "wiki_sync",
                "source_refs": [],
                "last_updated": _today(),
                "related_topics": ["CURRENT_STATE", "Performance_Baselines"],
            }
        ),
        "# Experiment Log",
        "",
        "> Append-only ledger of experiments. Maintained by",
        "> `python3 scripts/wiki_sync.py add-experiment`. Newest entries on top.",
        "",
        "| Date | Name | Status | Result | Conclusion |",
        "|------|------|:------:|--------|------------|",
        "",
    ]
    _write(EXPERIMENT_LOG_PATH, "\n".join(header))


def _replace_frontmatter_field(content, key, value):
    """Rewrite a scalar frontmatter field without reformatting the body."""
    if not content.startswith("---\n"):
        return content
    lines = content.splitlines()
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
    if closing is None:
        return content
    pattern = re.compile(rf"^{re.escape(key)}\s*:.*$")
    replaced = False
    for i in range(1, closing):
        if pattern.match(lines[i]):
            lines[i] = f"{key}: {value}"
            replaced = True
            break
    if not replaced:
        lines.insert(closing, f"{key}: {value}")
        closing += 1
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def add_experiment(name, status, result, conclusion, exp_date=None, dir_path=None):
    """Append a row to EXPERIMENT_LOG.md (non-interactive)."""
    if dir_path:
        global KNOWLEDGE_DIR, EXPERIMENT_LOG_PATH
        KNOWLEDGE_DIR = dir_path
        EXPERIMENT_LOG_PATH = os.path.join(KNOWLEDGE_DIR, "EXPERIMENT_LOG.md")

    _ensure_experiment_log()
    entry_date = exp_date or _today()
    safe = lambda s: (s or "").replace("|", "\\|").replace("\n", " ").strip()
    row = f"| {entry_date} | {safe(name)} | {safe(status)} | {safe(result)} | {safe(conclusion)} |"

    existing = _safe_read(EXPERIMENT_LOG_PATH)
    lines = existing.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("|------"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("EXPERIMENT_LOG.md missing table header; delete the file to regenerate.")
    lines.insert(header_idx + 1, row)
    updated = "\n".join(lines)
    updated = _replace_frontmatter_field(updated, "last_updated", _today())
    if not updated.endswith("\n"):
        updated += "\n"
    _write(EXPERIMENT_LOG_PATH, updated)
    print(f"✅ Experiment logged: {name} [{status}] → {EXPERIMENT_LOG_PATH}")


def update_state(phase=None, status=None, note=None, dir_path=None):
    """Update CURRENT_STATE.md phase row + append an AI annotation (non-interactive)."""
    if dir_path:
        global KNOWLEDGE_DIR, CURRENT_STATE_PATH
        KNOWLEDGE_DIR = dir_path
        CURRENT_STATE_PATH = os.path.join(KNOWLEDGE_DIR, "CURRENT_STATE.md")

    if not os.path.exists(CURRENT_STATE_PATH):
        raise ValueError(
            f"CURRENT_STATE.md not found at {CURRENT_STATE_PATH}. "
            "Copy it from templates/docs/knowledge/CURRENT_STATE.md first."
        )

    content = _safe_read(CURRENT_STATE_PATH)
    content = _replace_frontmatter_field(content, "last_updated", _today())

    if phase and status:
        pattern = re.compile(
            rf"^(\|\s*`?{re.escape(phase)}`?\s*\|)([^|]*)(\|)",
            re.MULTILINE,
        )
        new_content, n = pattern.subn(
            lambda m: f"{m.group(1)} {status} {m.group(3)}", content, count=1
        )
        if n:
            content = new_content
        else:
            print(f"⚠️  Phase row '{phase}' not found in CURRENT_STATE.md — appending annotation only.")

    if note:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        annotation = f"- [{stamp}] {note}"
        marker = "## AI Annotations"
        if marker in content:
            head, tail = content.split(marker, 1)
            tail_stripped = tail.lstrip("\n")
            tail_stripped = re.sub(r"^<!--[^>]*-->\s*", "", tail_stripped)
            content = f"{head}{marker}\n\n{annotation}\n{tail_stripped}"
        else:
            content = content.rstrip() + f"\n\n## AI Annotations\n\n{annotation}\n"

    if not content.endswith("\n"):
        content += "\n"
    _write(CURRENT_STATE_PATH, content)
    print(f"✅ CURRENT_STATE updated: phase={phase or '—'} status={status or '—'}")


def _resolve_ssot_value(spec, base_dir):
    """Resolve a single `<file>:<locator>` spec into a comparable string.

    Supported locator forms:
      - JSON file (`VERSION.json`): dot-path into the object, e.g.
        `benchmark_snapshot.summary` → nested value.
      - Markdown file: literal section heading (`## Current Baselines`)
        returns the paragraph-stripped body of that section until the next
        heading of same or higher level.

    Returns (value_or_None, error_or_None). value is a normalized string
    (whitespace-collapsed); error is a human-readable reason if we can't
    resolve it.
    """
    if ":" not in spec:
        return None, f"ssot_mirror spec missing `:` — expected `<file>:<locator>`, got {spec!r}"
    file_part, locator = spec.split(":", 1)
    path = os.path.normpath(os.path.join(base_dir, file_part))
    if not os.path.exists(path):
        return None, f"file not found: {file_part}"

    try:
        raw = _safe_read(path)
    except OSError as exc:
        return None, f"unreadable {file_part}: {exc}"

    if file_part.endswith(".json"):
        try:
            import json as _json
            obj = _json.loads(raw)
        except (_json.JSONDecodeError, ValueError) as exc:
            return None, f"{file_part} not valid JSON: {exc}"
        cursor = obj
        for segment in locator.split("."):
            if isinstance(cursor, dict) and segment in cursor:
                cursor = cursor[segment]
            else:
                return None, f"path {locator!r} not found in {file_part}"
        return _normalize_whitespace(str(cursor)), None

    # Markdown path: locator is a section heading text; extract the body.
    target = locator.strip()
    lines = raw.splitlines()
    start_idx = None
    heading_level = 0
    for idx, line in enumerate(lines):
        m = re.match(r"^(#+)\s+(.+?)\s*$", line)
        if m and m.group(2).strip() == target:
            start_idx = idx + 1
            heading_level = len(m.group(1))
            break
    if start_idx is None:
        return None, f"markdown section {target!r} not found in {file_part}"

    body_lines = []
    for line in lines[start_idx:]:
        m = re.match(r"^(#+)\s+", line)
        if m and len(m.group(1)) <= heading_level:
            break
        body_lines.append(line)
    return _normalize_whitespace(" ".join(body_lines)), None


def _normalize_whitespace(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def cross_check():
    """Verify SSOT mirrors declared in knowledge-page frontmatter agree with their sources.

    A knowledge page can declare `ssot_mirrors` in its frontmatter, each item a
    `<file>:<locator>` spec. All declared mirrors must resolve to the same
    normalized value; otherwise this function reports the mismatch.
    """
    pages = _load_knowledge_pages(include_meta=True)
    mismatches = []
    checked = 0

    for page in pages:
        mirrors = _normalize_list(page["metadata"].get("ssot_mirrors") if page.get("metadata") else [])
        if not mirrors:
            continue
        checked += 1

        resolved = []
        for spec in mirrors:
            value, err = _resolve_ssot_value(spec, BASE_DIR)
            resolved.append((spec, value, err))

        errs = [(spec, err) for spec, _v, err in resolved if err]
        if errs:
            for spec, err in errs:
                mismatches.append(
                    f"{page['filename']}: cannot resolve {spec} — {err}"
                )
            continue

        values = {value for _spec, value, _err in resolved}
        if len(values) > 1:
            mismatches.append(
                f"{page['filename']}: SSOT mirrors disagree — "
                + "; ".join(f"{spec}={value!r}" for spec, value, _err in resolved)
            )

    if not mismatches:
        print(f"✅ wiki_sync cross-check passed — {checked} page(s) with ssot_mirrors all agree.")
        return 0

    print(f"❌ wiki_sync cross-check found {len(mismatches)} mismatch(es):")
    for issue in mismatches:
        print(f"  - {issue}")
    return 1


def stale(threshold_days=30):
    """List knowledge pages whose `last_updated` is older than threshold_days.

    Informational only (exit 0). Reuses the same page loader and date parser
    as `lint`, so staleness is measured identically everywhere.
    """
    today = date.today()
    pages = _load_knowledge_pages(include_meta=True)
    stale_pages = []
    for page in pages:
        last = _parse_date(page.get("last_updated"))
        if last is None:
            continue
        age = (today - last).days
        if age > threshold_days:
            stale_pages.append((age, page))

    if not stale_pages:
        print(f"✅ No knowledge pages older than {threshold_days} days.")
        return 0

    stale_pages.sort(key=lambda item: item[0], reverse=True)
    print(f"⏳ {len(stale_pages)} page(s) older than {threshold_days} days:")
    for age, page in stale_pages:
        rel = os.path.relpath(page["path"], BASE_DIR)
        print(f"  - {rel} | {page['last_updated']} | {age} days")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="OAW — deterministic wiki compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  %(prog)s build                        Compile docs/raw/ into docs/knowledge/ + index/log
  %(prog)s refresh Topic_Name           Rebuild one topic, then update index/log
  %(prog)s refresh all                  Rebuild every compiled topic
  %(prog)s lint                         Check wiki metadata quality
  %(prog)s stale [--threshold N]        Report knowledge pages older than N days
  %(prog)s cross-check                  Verify frontmatter `ssot_mirrors` agree across files
  %(prog)s add-experiment --name ...    Append row to docs/knowledge/EXPERIMENT_LOG.md
  %(prog)s update-state --phase ...     Update a phase row in docs/knowledge/CURRENT_STATE.md

Non-interactive flags on add-experiment / update-state exist so AI workflows
can call them without prompting the user.
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Compile all raw sources into the wiki.")

    p_refresh = subparsers.add_parser("refresh", help="Refresh one topic or all topics.")
    p_refresh.add_argument("topic", help="Topic ID or 'all'.")

    p_lint = subparsers.add_parser("lint", help="Validate raw/wiki metadata and links.")
    p_lint.add_argument(
        "--strict",
        action="store_true",
        help="Treat unfilled `${...}` / `YYYY-MM-DD` placeholders as errors (default: warn only).",
    )

    p_stale = subparsers.add_parser(
        "stale",
        help="Report knowledge pages whose last_updated is older than a threshold.",
    )
    p_stale.add_argument(
        "--threshold",
        type=int,
        default=30,
        help="Age threshold in days (default: 30).",
    )

    subparsers.add_parser(
        "cross-check",
        help="Verify that frontmatter ssot_mirrors on knowledge pages agree across files.",
    )

    p_add = subparsers.add_parser(
        "add-experiment",
        help="Append an experiment row to EXPERIMENT_LOG.md (non-interactive).",
    )
    p_add.add_argument("--name", required=True, help="Experiment short name.")
    p_add.add_argument(
        "--status", required=True,
        choices=["accepted", "rejected", "running", "blocked", "inconclusive"],
        help="Outcome status.",
    )
    p_add.add_argument("--result", default="", help="One-line metric / observation.")
    p_add.add_argument("--conclusion", default="", help="One-line decision / next step.")
    p_add.add_argument("--date", default=None, help="Override date (YYYY-MM-DD).")
    p_add.add_argument(
        "--dir", default=None,
        help="Override knowledge dir (default: docs/knowledge/).",
    )

    p_state = subparsers.add_parser(
        "update-state",
        help="Update CURRENT_STATE.md phase row and annotation (non-interactive).",
    )
    p_state.add_argument("--phase", default=None, help="Phase id / label (matches first column).")
    p_state.add_argument(
        "--status", default=None,
        help="New phase status (e.g. '✅ done', '🔄 in progress', '⏳ queued').",
    )
    p_state.add_argument("--note", default=None, help="Annotation line appended under AI Annotations.")
    p_state.add_argument(
        "--dir", default=None,
        help="Override knowledge dir (default: docs/knowledge/).",
    )

    args = parser.parse_args()

    try:
        if args.command == "build":
            build()
        elif args.command == "refresh":
            refresh(args.topic)
        elif args.command == "lint":
            raise SystemExit(lint(strict=args.strict))
        elif args.command == "stale":
            raise SystemExit(stale(threshold_days=args.threshold))
        elif args.command == "cross-check":
            raise SystemExit(cross_check())
        elif args.command == "add-experiment":
            add_experiment(
                name=args.name,
                status=args.status,
                result=args.result,
                conclusion=args.conclusion,
                exp_date=args.date,
                dir_path=args.dir,
            )
        elif args.command == "update-state":
            update_state(
                phase=args.phase,
                status=args.status,
                note=args.note,
                dir_path=args.dir,
            )
    except ValueError as exc:
        print(f"❌ {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
