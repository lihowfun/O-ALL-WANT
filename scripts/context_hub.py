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
import json
import os
import re
from datetime import datetime

try:
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - exercised on Windows
    fcntl = None

try:
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover - exercised on POSIX
    msvcrt = None

# ─── Configuration ────────────────────────────────────────────────────────────
# Adjust these paths to match your project structure.

BASE_DIR = os.environ.get("AGENT_MEMORY_BASE_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
DOCS_DIR = os.path.join(BASE_DIR, "docs", "knowledge")
RAW_DIR = os.path.join(BASE_DIR, "docs", "raw")
MEMORY_FILE = os.path.join(BASE_DIR, ".agents", "memory.md")
AI_CONTEXT_FILE = os.path.join(BASE_DIR, "AI_CONTEXT.md")
META_PAGE_TYPES = {"meta"}

# ─── Utilities ────────────────────────────────────────────────────────────────


def _resolve_lock_backend(os_name=None, fcntl_module=fcntl, msvcrt_module=msvcrt):
    """Choose the best available file-lock backend for the current platform."""
    current_os = os_name or os.name

    if current_os == "nt" and msvcrt_module is not None:
        return "windows", msvcrt_module
    if fcntl_module is not None:
        return "posix", fcntl_module
    if msvcrt_module is not None:
        return "windows", msvcrt_module
    return "none", None


def _locked_write(filepath, content, os_name=None, fcntl_module=fcntl, msvcrt_module=msvcrt):
    """Write file content with the best available lock to reduce multi-agent races."""
    backend, lock_module = _resolve_lock_backend(
        os_name=os_name,
        fcntl_module=fcntl_module,
        msvcrt_module=msvcrt_module,
    )

    if backend == "windows":
        with open(filepath, "a+", encoding="utf-8") as f:
            f.seek(0)
            lock_module.locking(f.fileno(), lock_module.LK_LOCK, 1)
            try:
                f.seek(0)
                f.truncate()
                f.write(content)
                f.flush()
            finally:
                f.seek(0)
                lock_module.locking(f.fileno(), lock_module.LK_UNLCK, 1)
        return

    with open(filepath, "w", encoding="utf-8") as f:
        if backend == "posix":
            lock_module.flock(f, lock_module.LOCK_EX)
        try:
            f.write(content)
            f.flush()
        finally:
            if backend == "posix":
                lock_module.flock(f, lock_module.LOCK_UN)


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
    if not os.path.exists(DOCS_DIR):
        return []

    pages = []
    for filename in sorted(os.listdir(DOCS_DIR)):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(DOCS_DIR, filename)
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
    if not os.path.exists(RAW_DIR):
        return 0
    count = 0
    for filename in os.listdir(RAW_DIR):
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
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
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
    file_path = os.path.join(DOCS_DIR, f"{topic}.md")
    if not os.path.exists(file_path):
        print(f"Topic '{topic}' not found. Run 'search' to list topics.")
        return
    print(f"\n--- CONTENT OF {topic} ---")
    with open(file_path, "r", encoding="utf-8") as f:
        print(f.read())
    print("--- END OF CONTENT ---")


# ─── Annotate ─────────────────────────────────────────────────────────────────

def annotate(topic, note):
    """Annotate a knowledge topic with a structured finding."""
    file_path = os.path.join(DOCS_DIR, f"{topic}.md")
    if not os.path.exists(file_path):
        print(f"Topic '{topic}' not found. Cannot annotate.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    metadata, _body = _parse_frontmatter(content)
    if metadata.get("page_type") in META_PAGE_TYPES:
        print(f"Topic '{topic}' is a meta page and should not be annotated directly.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Auto-detect tag from note content
    tag = ""
    tag_match = re.match(r'^\[(\w+)\]\s*', note)
    if tag_match:
        tag = f" ({tag_match.group(1)})"

    annotation_block = f"\n\n> **[AI Annotation{tag}]** ({timestamp}): {note}\n"

    # Append before the last section or at the end
    if "## AI Annotations" in content:
        content = content + annotation_block
    else:
        content = content + f"\n\n## AI Annotations\n{annotation_block}"

    _locked_write(file_path, content)
    print(f"✅ Annotated '{topic}' with: {note[:60]}...")


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

    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Agent Memory — Decision & Finding Log\n\n---\n"

    # Insert after the first "---" separator (after header)
    separator_pos = content.find("---")
    if separator_pos != -1:
        insert_pos = content.find("\n", separator_pos) + 1
        content = content[:insert_pos] + entry + content[insert_pos:]
    else:
        content = content + entry

    _locked_write(MEMORY_FILE, content)
    print(f"✅ Memory entry added: [{tag}] {note[:60]}...")


def memory_show(count=10):
    """Show recent memory entries."""
    if not os.path.exists(MEMORY_FILE):
        print("No memory file found.")
        return

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
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


# ─── Status ───────────────────────────────────────────────────────────────────

def status(compact=False):
    """Print a one-screen project status summary."""
    version_file = os.path.join(BASE_DIR, "VERSION.json")
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
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
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
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
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
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
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
        with open(AI_CONTEXT_FILE, "r", encoding="utf-8") as f:
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
        filepath = os.path.join(BASE_DIR, filename)
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
        skills_dir = os.path.join(BASE_DIR, ".agents", "skills")
        print(f"\n{'─'*60}")
        print("  Available skills (.agents/skills/)")
        print(f"{'─'*60}")
        if os.path.exists(skills_dir):
            for fname in sorted(os.listdir(skills_dir)):
                if fname.endswith(".md") and not fname.startswith("_") \
                        and fname.lower() != "readme.md":
                    print(f"  /{fname[:-3]}")
        else:
            print("  No skills directory found.")

    elif lane == "debug":
        _print_file(os.path.join(DOCS_DIR, "Known_Limitations.md"))
        if os.path.exists(MEMORY_FILE):
            print(f"\n{'─'*60}")
            print("  .agents/memory.md (last 5 entries)")
            print(f"{'─'*60}")
            memory_show(5)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
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
    os.makedirs(DOCS_DIR, exist_ok=True)

    if args.command == "search":
        search(args.query, compact=args.compact, include_memory=args.include_memory)
    elif args.command == "get":
        get(args.topic)
    elif args.command == "annotate":
        annotate(args.topic, args.note)
    elif args.command == "memory":
        if args.mem_action == "add":
            memory_add(args.note)
        elif args.mem_action == "show":
            memory_show(args.last)
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


if __name__ == "__main__":
    main()
