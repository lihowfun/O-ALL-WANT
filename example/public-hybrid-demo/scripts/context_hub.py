#!/usr/bin/env python3
"""
Context Hub — AI Agent Knowledge Management CLI.

Provides an interface for AI agents (and humans) to search, fetch,
annotate knowledge, manage rolling decision memory, and bootstrap
new sessions.

Part of OAW.
https://github.com/lihowfun/O-ALL-WANT
"""
import argparse
import base64
import hashlib
import json
import os
import re
from datetime import datetime
from oaw_common import (
    append_annotation, atomic_write, confined_path, locked_update,
    validate_topic_id,
)

# ─── Configuration ────────────────────────────────────────────────────────────
# Adjust these paths to match your project structure.

BASE_DIR = os.path.abspath(os.environ.get("AGENT_MEMORY_BASE_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
))
DOCS_DIR = os.path.join(BASE_DIR, "docs", "knowledge")
RAW_DIR = os.path.join(BASE_DIR, "docs", "raw")
MEMORY_FILE = os.path.join(BASE_DIR, ".agents", "memory.md")
AI_CONTEXT_FILE = os.path.join(BASE_DIR, "AI_CONTEXT.md")
META_PAGE_TYPES = {"meta"}

# ─── Utilities ────────────────────────────────────────────────────────────────


def _locked_write(filepath, content):
    """Compatibility helper for whole-file writes; dependent edits use RMW."""
    atomic_write(filepath, content, root=BASE_DIR)


def _topic_path(topic):
    validate_topic_id(topic, allow_meta=True)
    return confined_path(BASE_DIR, DOCS_DIR, f"{topic}.md")


def _strip_tag_prefix(note):
    """Remove a single leading [TAG] prefix while preserving the rest of the note."""
    return re.sub(r"^\[\w+\]\s*", "", note, count=1)


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
    """Normalize a scalar/list frontmatter field to a list of strings."""
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


def _page_title(filename, content, metadata):
    """Best-effort title resolution for a knowledge page."""
    if metadata.get("title"):
        return metadata["title"]
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return filename.replace(".md", "").replace("_", " ")


def _knowledge_pages(include_meta=False):
    """Yield loaded knowledge pages with parsed metadata."""
    docs_dir = confined_path(BASE_DIR, DOCS_DIR)
    if not os.path.exists(docs_dir):
        return []

    pages = []
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        path = confined_path(BASE_DIR, DOCS_DIR, filename)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
        metadata, body = _parse_frontmatter(content)
        if not include_meta and metadata.get("page_type") in META_PAGE_TYPES:
            continue
        pages.append(
            {
                "filename": filename,
                "path": path,
                "metadata": metadata,
                "content": content,
                "body": body,
                "title": _page_title(filename, body, metadata),
            }
        )
    return pages


def _raw_source_count():
    """Count raw markdown sources, excluding helper files."""
    raw_dir = confined_path(BASE_DIR, RAW_DIR)
    if not os.path.exists(raw_dir):
        return 0
    count = 0
    for filename in os.listdir(raw_dir):
        if not filename.endswith(".md"):
            continue
        if filename.startswith("_") or filename.lower() == "readme.md":
            continue
        count += 1
    return count


# ─── Search ───────────────────────────────────────────────────────────────────

def search(query, compact=False, include_memory=False):
    """Search knowledge base topics by keyword, optionally including memory entries."""
    if not compact:
        print(f"Searching for '{query}' in {DOCS_DIR}...")
    if not os.path.exists(DOCS_DIR):
        print("0 topics" if compact else "Knowledge directory not found.")
        return

    results = []
    for page in _knowledge_pages():
        filename = page["filename"]
        content = page["content"]
        metadata = page["metadata"]
        search_blob = "\n".join(
            [
                filename,
                page["title"],
                content,
                " ".join(_normalize_list(metadata.get("related_topics"))),
            ]
        )
        if not query or query.lower() in search_blob.lower():
            annotations = content.count("[AI Annotation")
            results.append((filename.replace(".md", ""), page["title"], annotations))

    if not results:
        if not compact:
            print("No matches found in knowledge base.")
    elif compact:
        print(f"{len(results)} topics: {', '.join(t[0] for t in results)}")
    else:
        print(f"\n{'='*70}")
        print(f"  MATCHING KNOWLEDGE TOPICS ({len(results)} found)")
        print(f"{'='*70}")
        print(f"  {'Topic ID':<30} | {'Annotations':>5} | {'Description'}")
        print(f"  {'-'*30}-+-{'-'*5}-+-{'-'*30}")
        for topic, title, ann_count in results:
            ann_str = f"[{ann_count}]" if ann_count > 0 else ""
            print(f"  {topic:<30} | {ann_str:>5} | {title}")
        print()

    if include_memory and os.path.exists(MEMORY_FILE):
        with open(confined_path(BASE_DIR, MEMORY_FILE), "r", encoding="utf-8") as f:
            mem_content = f.read()
        entries = re.split(r"(?=^## \[)", mem_content, flags=re.MULTILINE)
        entries = [e for e in entries if e.startswith("## [")]
        mem_hits = [e for e in entries if not query or query.lower() in e.lower()]
        if mem_hits:
            if compact:
                print(f"{len(mem_hits)} memory: {', '.join(e.splitlines()[0][:50] for e in mem_hits)}")
            else:
                print(f"  MATCHING MEMORY ENTRIES ({len(mem_hits)} found)")
                print(f"  {'-'*40}")
                for entry in mem_hits:
                    print(f"    {entry.strip().split(chr(10))[0]}")
                print()
        elif not compact and not results:
            print("No matches found. Try broadening the search.")

    if not include_memory and not results and compact:
        print("0 topics")


# ─── Get ──────────────────────────────────────────────────────────────────────

def get(topic):
    """Fetch the complete content of a knowledge topic."""
    file_path = _topic_path(topic)
    if not os.path.exists(file_path):
        print(f"Topic '{topic}' not found. Run 'search' to list topics.")
        return 1
    print(f"\n--- CONTENT OF {topic} ---")
    with open(file_path, "r", encoding="utf-8") as f:
        print(f.read())
    print("--- END OF CONTENT ---")
    return 0


# ─── Annotate ─────────────────────────────────────────────────────────────────

def annotate(topic, note):
    """Annotate a knowledge topic with a structured finding."""
    file_path = _topic_path(topic)
    if not os.path.exists(file_path):
        print(f"Topic '{topic}' not found. Cannot annotate.")
        return 1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Auto-detect tag from note content
    tag = ""
    tag_match = re.match(r'^\[(\w+)\]\s*', note)
    if tag_match:
        tag = f" ({tag_match.group(1)})"

    annotation_block = f"\n\n> **[AI Annotation{tag}]** ({timestamp}): {note}\n"

    def mutate(content):
        if not content:
            raise ValueError(f"Topic '{topic}' no longer exists or is empty.")
        metadata, _body = _parse_frontmatter(content)
        if metadata.get("page_type") in META_PAGE_TYPES:
            raise ValueError(f"Topic '{topic}' is a meta page and cannot be annotated.")
        return append_annotation(content, annotation_block)

    locked_update(file_path, mutate, root=BASE_DIR)
    print(f"✅ Annotated '{topic}' with: {note[:60]}...")
    return 0


# ─── Memory ───────────────────────────────────────────────────────────────────

def memory_add(note):
    """Add a structured entry to the rolling memory."""
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Auto-detect tag
    tag_match = re.match(r'^\[(\w+)\]', note)
    tag = tag_match.group(1) if tag_match else "NOTE"

    note_body = _strip_tag_prefix(note) if tag_match else note
    # Strip a duplicate leading date if the user already included today's date
    note_body = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', note_body)

    entry = f"\n## [{timestamp}] [{tag}] {note_body}\n"

    def mutate(content):
        separator = re.search(r"^---[ \t]*$", content, re.MULTILINE)
        if separator:
            insert_pos = separator.end()
            return content[:insert_pos] + "\n" + entry + content[insert_pos:]
        return content.rstrip() + "\n" + entry

    locked_update(
        confined_path(BASE_DIR, MEMORY_FILE), mutate,
        default="# Agent Memory — Decision & Finding Log\n\n---\n", root=BASE_DIR,
    )
    print(f"✅ Memory entry added: [{tag}] {note[:60]}...")


def memory_show(count=10):
    """Show recent memory entries."""
    if not os.path.exists(MEMORY_FILE):
        print("No memory file found.")
        return

    with open(confined_path(BASE_DIR, MEMORY_FILE), "r", encoding="utf-8") as f:
        content = f.read()

    entries = re.split(r'(?=^## \[)', content, flags=re.MULTILINE)
    entries = [e for e in entries if e.startswith("## [")]

    if not entries:
        print("No memory entries found.")
        return

    print(f"\n{'='*70}")
    print(f"  RECENT MEMORY ({min(count, len(entries))} of {len(entries)} entries)")
    print(f"{'='*70}\n")

    for entry in entries[:count]:
        print(entry.strip())
        print()


# ─── Lesson ───────────────────────────────────────────────────────────────────

def lesson(mistake, correction):
    """Record a lesson learned (mistake + correct approach)."""
    note = f"[INSIGHT] Lesson learned — Mistake: {mistake} | Correction: {correction}"
    memory_add(note)


def _recall_cursor(index, query_hash, snapshot):
    payload = json.dumps([1, index, query_hash, snapshot], separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("ascii")).decode("ascii").rstrip("=")


def _decode_recall_cursor(cursor, query_hash, snapshot):
    if not cursor:
        return 0
    try:
        if len(cursor) > 512:
            raise ValueError
        data = json.loads(base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True))
        if (not isinstance(data, list) or len(data) != 4 or data[0] != 1
                or type(data[1]) is not int or data[1] < 0
                or data[2:] != [query_hash, snapshot]):
            raise ValueError
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid recall cursor or sources changed; restart without --cursor.") from exc
    return data[1]


def _render_recall(packet, json_out):
    if json_out:
        return json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    lines = []
    for item in packet["results"]:
        lines.append(f"{item['source']}:{item['line']}")
        lines.append(item["excerpt"])
        if item["truncated"]:
            lines.append("[Excerpt truncated; read the cited source for the complete entry.]")
        lines.append("")
    if not lines:
        lines.append("No matches found.")
    if packet["continuation"]:
        lines.append("Next cursor: " + packet["continuation"])
    return "\n".join(lines).rstrip()


def memory_recall(query, limit=8, cursor=None, max_chars=12000, json_out=False):
    """Return bounded, cited excerpts; a cursor continues at the next entry.

    An entry never contributes more than 2,000 characters. The complete printed
    response (including JSON framing and its newline) respects max_chars. An
    entry's continuation cites its full source; the packet's continuation pages
    through additional matching entries. Cursors reject changed source snapshots.
    """
    if not query.strip() or len(query) > 512:
        raise ValueError("Recall requires a non-empty query of at most 512 characters.")
    if not 1 <= limit <= 100:
        raise ValueError("Recall --limit must be between 1 and 100.")
    if not 512 <= max_chars <= 1000000:
        raise ValueError("Recall --max-chars must be between 512 and 1000000.")

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits = []
    digest = hashlib.sha256()

    def scan(path, label, memory=False):
        path = confined_path(BASE_DIR, path)
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        digest.update(label.encode("utf-8") + b"\0" + content.encode("utf-8") + b"\0")
        if memory:
            starts = list(re.finditer(r"^## \[", content, re.MULTILINE))
            chunks = [(match.start(), starts[i + 1].start() if i + 1 < len(starts) else len(content)) for i, match in enumerate(starts)]
        else:
            chunks = [(0, len(content))]
        for start, end in chunks:
            entry = content[start:end].rstrip()
            match = pattern.search(entry)
            if match is None:
                continue
            # Keep each entry independent even when adjacent lines all match.
            excerpt_start = max(0, match.start() - 200)
            text = entry[excerpt_start:]
            line = content.count("\n", 0, start + excerpt_start) + 1
            hits.append({"source": label, "line": line, "text": text,
                         "match_start": match.start() - excerpt_start,
                         "match_end": match.end() - excerpt_start,
                         "prefix_omitted": excerpt_start > 0, "kind": "memory" if memory else "knowledge"})

    scan(MEMORY_FILE, ".agents/memory.md", memory=True)
    docs = confined_path(BASE_DIR, DOCS_DIR)
    if os.path.isdir(docs):
        for filename in sorted(os.listdir(docs)):
            if filename.endswith(".md"):
                scan(os.path.join(docs, filename), "docs/knowledge/" + filename)

    snapshot = digest.hexdigest()[:24]
    query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:24]
    start = _decode_recall_cursor(cursor, query_hash, snapshot)
    if start > len(hits):
        raise ValueError("Recall cursor is beyond the end of the results.")
    packet = {"schema_version": 1, "results": [], "truncated": False, "continuation": None}
    index = start
    while index < len(hits) and len(packet["results"]) < limit:
        hit = dict(hits[index])

        def candidate(length):
            excerpt = hit["text"][:length]
            truncated = hit["prefix_omitted"] or length < len(hit["text"])
            item = {"source": hit["source"], "line": hit["line"], "kind": hit["kind"],
                    "excerpt": excerpt, "truncated": truncated,
                    "continuation": {"source": hit["source"], "line": hit["line"]} if truncated else None}
            more = index + 1 < len(hits)
            return {"schema_version": 1, "results": packet["results"] + [item],
                    "truncated": more or any(row["truncated"] for row in packet["results"]) or truncated,
                    "continuation": _recall_cursor(index + 1, query_hash, snapshot) if more else None}

        fitting = None
        for trim_prefix in (False, True):
            if trim_prefix:
                offset = hit["match_start"]
                if not offset:
                    break
                hit["line"] += hit["text"].count("\n", 0, offset)
                hit["text"] = hit["text"][offset:]
                hit["match_end"] -= offset
                hit["match_start"] = 0
                hit["prefix_omitted"] = True
            low, high = hit["match_end"], min(2000, len(hit["text"]))
            # Every emitted excerpt must include its complete query match.
            # Escaped prefix text can be discarded before sacrificing the hit.
            while low <= high:
                middle = (low + high) // 2
                proposed = candidate(middle)
                if len(_render_recall(proposed, json_out)) + 1 <= max_chars:
                    fitting = proposed
                    low = middle + 1
                else:
                    high = middle - 1
            if fitting is not None:
                break
        if fitting is None:
            if not packet["results"]:
                raise ValueError("--max-chars is too small for this result's provenance; increase it.")
            break
        packet = fitting
        index += 1
    if index < len(hits):
        packet["continuation"] = _recall_cursor(index, query_hash, snapshot)
        packet["truncated"] = True
    output = _render_recall(packet, json_out)
    if len(output) + 1 > max_chars:
        raise ValueError("--max-chars is too small for the recall response.")
    print(output)
    return 0


# ─── Status ───────────────────────────────────────────────────────────────────

def status(compact=False):
    """Print a one-screen project status summary."""
    version_file = confined_path(BASE_DIR, "VERSION.json")
    version_str = "unknown"
    phase_str = ""
    dnr_count = 0
    if os.path.exists(version_file):
        with open(version_file, "r", encoding="utf-8") as f:
            v = json.load(f)
        version_str = v.get("version", "unknown")
        dnr_count = len(v.get("do_not_rerun", []))
        phase_str = v.get("current_phase", "")

    if compact:
        pages = _knowledge_pages()
        mem_count = 0
        if os.path.exists(MEMORY_FILE):
            with open(confined_path(BASE_DIR, MEMORY_FILE), "r", encoding="utf-8") as f:
                content = f.read()
            mem_count = len(
                [
                    entry
                    for entry in re.split(r"(?=^## \[)", content, flags=re.MULTILINE)
                    if entry.startswith("## [")
                ]
            )
        raw_count = _raw_source_count()
        parts = [f"v{version_str}", f"{len(pages)} topics", f"{mem_count} memories", f"{dnr_count} locked"]
        if phase_str:
            parts.append(f"phase: {phase_str}")
        if raw_count:
            parts.append(f"{raw_count} raw")
        print(" | ".join(parts))
        return

    print(f"\n{'='*70}")
    print(f"  📊 PROJECT STATUS")
    print(f"{'='*70}\n")

    # 1. Version
    if os.path.exists(version_file):
        with open(version_file, "r", encoding="utf-8") as f:
            v = json.load(f)
        print(f"  📦 VERSION: {v.get('version', 'unknown')}")
        dnr = v.get("do_not_rerun", [])
        print(f"  🚫 DO NOT RERUN: {len(dnr)} experiments locked")
        if v.get("current_phase"):
            print(f"  🎯 CURRENT PHASE: {v.get('current_phase')}")
    print()

    # 2. Recent memory
    print("  🧠 RECENT DECISIONS (last 3)")
    print(f"  {'-'*40}")
    if os.path.exists(MEMORY_FILE):
        with open(confined_path(BASE_DIR, MEMORY_FILE), "r", encoding="utf-8") as f:
            content = f.read()
        entries = re.split(r'(?=^## \[)', content, flags=re.MULTILINE)
        entries = [e for e in entries if e.startswith("## [")]
        for entry in entries[:3]:
            header = entry.strip().split("\n")[0]
            print(f"    {header}")
    print()

    # 3. Knowledge topics
    print("  📚 KNOWLEDGE TOPICS")
    print(f"  {'-'*40}")
    pages = _knowledge_pages()
    for page in pages:
        print(f"    {page['filename'].replace('.md', '')}")
    if _raw_source_count():
        print()
        print(f"  🧾 RAW SOURCES: {_raw_source_count()} file(s) in docs/raw/")
    print()


# ─── Bootstrap ────────────────────────────────────────────────────────────────

def bootstrap(compact=False):
    """Output everything a new agent session needs to get started."""
    if compact:
        status(compact=True)
        print()
        if os.path.exists(MEMORY_FILE):
            with open(confined_path(BASE_DIR, MEMORY_FILE), "r", encoding="utf-8") as f:
                content = f.read()
            entries = re.split(r"(?=^## \[)", content, flags=re.MULTILINE)
            entries = [entry for entry in entries if entry.startswith("## [")]
            if entries:
                print("Recent:")
                for entry in entries[:3]:
                    print(f"  {entry.strip().split(chr(10))[0]}")
        search("", compact=True)
        return

    print(f"\n{'='*70}")
    print(f"  🚀 CONTEXT HUB BOOTSTRAP — New Session")
    print(f"{'='*70}\n")

    # 1. Full AI context (single source of truth)
    if os.path.exists(AI_CONTEXT_FILE):
        print("📋 PROJECT CONTEXT (AI_CONTEXT.md)")
        print("-" * 40)
        with open(confined_path(BASE_DIR, AI_CONTEXT_FILE), "r", encoding="utf-8") as f:
            print(f.read())
        print()

    # 2. Recent memory
    print("🧠 RECENT DECISIONS (last 5)")
    print("-" * 40)
    memory_show(5)

    # 3. Knowledge topics
    print("📚 AVAILABLE KNOWLEDGE TOPICS")
    print("-" * 40)
    search("")


# ─── Setup ────────────────────────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r'\$\{[A-Za-z0-9_]+\}')
_SETUP_FILES = ["AI_CONTEXT.md", "CLAUDE.md", "VERSION.json", "ROADMAP.md"]


def setup():
    """Audit unfilled ${...} placeholders in key project files."""
    found_any = False
    for filename in _SETUP_FILES:
        filepath = confined_path(BASE_DIR, filename)
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        hits = []
        seen = set()
        for lineno, line in enumerate(lines, 1):
            for m in _PLACEHOLDER_RE.finditer(line):
                ph = m.group()
                if ph not in seen:
                    seen.add(ph)
                    hits.append((lineno, ph))
        if hits:
            found_any = True
            print(f"\n  📄 {filename}")
            for lineno, ph in hits:
                print(f"     line {lineno}: {ph}")
    if found_any:
        print("\n  To fill a placeholder, tell your agent:")
        print('  "Fill ${PROJECT_NAME} with MyProject in AI_CONTEXT.md"')
        print("  or edit the files directly in your editor.\n")
    else:
        print("✅ No unfilled placeholders found in key project files.")


# ─── Context Lane ─────────────────────────────────────────────────────────────

_LANE_NAMES = ("operational", "wiki", "execution", "debug")


def context_lane(lane):
    """Output the context files for a specific routing lane."""
    if lane not in _LANE_NAMES:
        print(f"Unknown lane '{lane}'. Available: {', '.join(_LANE_NAMES)}")
        return

    def _print_file(filepath, label=None, max_lines=None):
        filepath = confined_path(BASE_DIR, filepath)
        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if max_lines:
            lines = lines[:max_lines]
        print(f"\n{'─'*60}")
        print(f"  {label or os.path.relpath(filepath, BASE_DIR)}")
        print(f"{'─'*60}")
        print("".join(lines))

    if lane == "operational":
        _print_file(os.path.join(BASE_DIR, "AI_CONTEXT.md"))
        _print_file(os.path.join(BASE_DIR, "ROADMAP.md"), max_lines=60,
                    label="ROADMAP.md (first 60 lines)")
        _print_file(os.path.join(BASE_DIR, "VERSION.json"))
        if os.path.exists(MEMORY_FILE):
            print(f"\n{'─'*60}")
            print("  .agents/memory.md (last 5 entries)")
            print(f"{'─'*60}")
            memory_show(5)

    elif lane == "wiki":
        _print_file(os.path.join(DOCS_DIR, "index.md"))
        print(f"\n{'─'*60}")
        print("  Available knowledge topics")
        print(f"{'─'*60}")
        search("")

    elif lane == "execution":
        print(f"\n{'─'*60}")
        print("  Available native skill packages")
        print(f"{'─'*60}")
        canonical = confined_path(BASE_DIR, "templates", ".agents", "skills")
        directories = [canonical] if os.path.isdir(canonical) else [
            confined_path(BASE_DIR, ".agents", "skills"),
            confined_path(BASE_DIR, ".claude", "skills"),
        ]
        found = False
        for skills_dir in directories:
            if not os.path.isdir(skills_dir):
                continue
            for fname in sorted(os.listdir(skills_dir)):
                package = confined_path(BASE_DIR, skills_dir, fname, "SKILL.md")
                if os.path.isfile(package):
                    print("  " + os.path.relpath(package, BASE_DIR).replace("\\", "/"))
                    found = True
                elif fname.endswith(".md") and not fname.startswith("_") \
                        and fname.lower() != "readme.md":
                    print(f"  /{fname[:-3]} (legacy flat skill)")
                    found = True
        if not found:
            print("  No skills directory found.")

    elif lane == "debug":
        _print_file(os.path.join(DOCS_DIR, "Known_Limitations.md"))
        if os.path.exists(MEMORY_FILE):
            print(f"\n{'─'*60}")
            print("  .agents/memory.md (last 5 entries)")
            print(f"{'─'*60}")
            memory_show(5)


# ─── Main ─────────────────────────────────────────────────────────────────────

def _main():
    parser = argparse.ArgumentParser(
        description="OAW — Context Hub CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  %(prog)s search "query"                   Search knowledge topics
  %(prog)s search --include-memory          Also search .agents/memory.md
  %(prog)s search --compact                 One-line topic list (saves tokens)
  %(prog)s get Topic_Name                   Fetch a topic's full content
  %(prog)s annotate Topic "note"            Annotate a topic with a finding
  %(prog)s memory add "[TAG] note"          Add a memory entry
  %(prog)s memory show --last 5             Show recent decisions
  %(prog)s memory recall "query" --json    Bounded excerpts with provenance and cursor
  %(prog)s lesson "mistake" "fix"           Record a lesson learned
  %(prog)s status                           One-screen project status
  %(prog)s status --compact                 One-line status (saves tokens)
  %(prog)s bootstrap                        Get new-session context dump
  %(prog)s bootstrap --compact              Minimal bootstrap (saves tokens)
  %(prog)s setup                            Audit unfilled placeholders
  %(prog)s context --lane operational       Output context for a routing lane
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search
    p_search = subparsers.add_parser("search", help="Search knowledge base topics.")
    p_search.add_argument("query", nargs="?", default="", help="Query to search for.")
    p_search.add_argument("--compact", action="store_true", help="One-line output (saves tokens).")
    p_search.add_argument("--include-memory", action="store_true",
                          help="Also search .agents/memory.md entries.")

    # Get
    p_get = subparsers.add_parser("get", help="Get full content of a topic.")
    p_get.add_argument("topic", help="The topic ID (filename without .md).")

    # Annotate
    p_annotate = subparsers.add_parser("annotate", help="Annotate a topic with new findings.")
    p_annotate.add_argument("topic", help="The topic ID.")
    p_annotate.add_argument("note", help="Your observation (prefix with [TAG] for structure).")

    # Memory
    p_memory = subparsers.add_parser("memory", help="Manage the rolling decision memory.")
    mem_sub = p_memory.add_subparsers(dest="mem_action", required=True)

    p_mem_add = mem_sub.add_parser("add", help="Add a new memory entry.")
    p_mem_add.add_argument("note", help="The memory entry (format: '[TAG] Title - Details').")

    p_mem_show = mem_sub.add_parser("show", help="Show recent memory entries.")
    p_mem_show.add_argument("--last", type=int, default=10, help="Number of entries to show.")

    p_recall = mem_sub.add_parser("recall", help="Recall bounded memory and knowledge excerpts.")
    p_recall.add_argument("query", help="Literal case-insensitive substring to recall.")
    p_recall.add_argument("--limit", type=int, default=8, help="Maximum matching entries (1-100).")
    p_recall.add_argument("--cursor", default=None, help="Continuation cursor from a previous recall.")
    p_recall.add_argument("--max-chars", type=int, default=12000,
                          help="Total printed character budget, including JSON framing (512-1000000).")
    p_recall.add_argument("--json", action="store_true", dest="json_out", help="Emit structured provenance and continuation.")

    # Lesson
    p_lesson = subparsers.add_parser("lesson", help="Record a lesson learned (mistake + correction).")
    p_lesson.add_argument("mistake", help="What went wrong.")
    p_lesson.add_argument("correction", help="What the correct approach is.")

    # Status
    p_status = subparsers.add_parser("status", help="Print one-screen project status summary.")
    p_status.add_argument("--compact", action="store_true", help="One-line output (saves tokens).")

    # Bootstrap
    p_bootstrap = subparsers.add_parser("bootstrap", help="Output new-session bootstrap context.")
    p_bootstrap.add_argument("--compact", action="store_true", help="Minimal output (saves tokens).")

    # Setup
    subparsers.add_parser("setup", help="Audit unfilled ${...} placeholders in key project files.")

    # Context lane
    p_context = subparsers.add_parser("context", help="Output context files for a routing lane.")
    p_context.add_argument(
        "--lane", required=True,
        choices=list(_LANE_NAMES),
        help="Lane to load: operational, wiki, execution, or debug.",
    )

    args = parser.parse_args()
    for filepath in (DOCS_DIR, RAW_DIR, MEMORY_FILE, AI_CONTEXT_FILE):
        confined_path(BASE_DIR, filepath)
    os.makedirs(DOCS_DIR, exist_ok=True)

    if args.command == "search":
        search(args.query, compact=args.compact, include_memory=args.include_memory)
    elif args.command == "get":
        return get(args.topic)
    elif args.command == "annotate":
        return annotate(args.topic, args.note)
    elif args.command == "memory":
        if args.mem_action == "add":
            memory_add(args.note)
        elif args.mem_action == "show":
            memory_show(args.last)
        elif args.mem_action == "recall":
            return memory_recall(args.query, args.limit, args.cursor, args.max_chars, args.json_out)
    elif args.command == "lesson":
        lesson(args.mistake, args.correction)
    elif args.command == "status":
        status(compact=args.compact)
    elif args.command == "bootstrap":
        bootstrap(compact=args.compact)
    elif args.command == "setup":
        setup()
    elif args.command == "context":
        context_lane(args.lane)


def main():
    try:
        return _main() or 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
