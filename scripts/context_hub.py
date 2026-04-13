#!/usr/bin/env python3
"""
Context Hub — AI Agent Knowledge Management CLI.

Provides an interface for AI agents (and humans) to search, fetch,
annotate knowledge, manage rolling decision memory, and bootstrap
new sessions.

Part of the Agent Memory Framework.
https://github.com/YOUR_ORG/agent-memory-framework
"""
import fcntl
import os
import re
import sys
import argparse
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────
# Adjust these paths to match your project structure.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs", "knowledge")
MEMORY_FILE = os.path.join(BASE_DIR, ".agents", "memory.md")
AI_CONTEXT_FILE = os.path.join(BASE_DIR, "AI_CONTEXT.md")

# ─── Utilities ────────────────────────────────────────────────────────────────


def _locked_write(filepath, content):
    """Write file content with exclusive lock to prevent multi-agent race conditions."""
    with open(filepath, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(content)
        fcntl.flock(f, fcntl.LOCK_UN)


# ─── Search ───────────────────────────────────────────────────────────────────

def search(query):
    """Search knowledge base topics by keyword."""
    print(f"Searching for '{query}' in {DOCS_DIR}...")
    if not os.path.exists(DOCS_DIR):
        print("Knowledge directory not found.")
        return

    results = []
    for f in sorted(os.listdir(DOCS_DIR)):
        if not f.endswith(".md"):
            continue
        path = os.path.join(DOCS_DIR, f)
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
            if not query or query.lower() in content.lower() or query.lower() in f.lower():
                title = f
                for line in content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                annotations = content.count("[AI Annotation]")
                results.append((f.replace(".md", ""), title, annotations))

    if not results:
        print("No matches found. Try broadening the search.")
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

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Auto-detect tag from note content
    tag = ""
    tag_match = re.match(r'^\[(\w+)\]\s*', note)
    if tag_match:
        tag = f" ({tag_match.group(1)})"

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

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

    entry = f"\n## [{timestamp}] [{tag}] {note.lstrip('[' + tag + '] ') if tag_match else note}\n"

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

def status():
    """Print a one-screen project status summary."""
    print(f"\n{'='*70}")
    print(f"  📊 PROJECT STATUS")
    print(f"{'='*70}\n")

    # 1. Version
    import json
    version_file = os.path.join(BASE_DIR, "VERSION.json")
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            v = json.load(f)
        print(f"  📦 VERSION: {v.get('version', 'unknown')}")
        dnr = v.get("do_not_rerun", [])
        print(f"  🚫 DO NOT RERUN: {len(dnr)} experiments locked")
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
    if os.path.exists(DOCS_DIR):
        for f in sorted(os.listdir(DOCS_DIR)):
            if f.endswith(".md"):
                print(f"    {f.replace('.md', '')}")
    print()


# ─── Bootstrap ────────────────────────────────────────────────────────────────

def bootstrap():
    """Output everything a new agent session needs to get started."""
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


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Agent Memory Framework — Context Hub CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  %(prog)s search "query"              Search knowledge topics
  %(prog)s get Topic_Name              Fetch a topic's full content
  %(prog)s annotate Topic "note"       Annotate a topic with a finding
  %(prog)s memory add "[TAG] note"     Add a memory entry
  %(prog)s memory show --last 5        Show recent decisions
  %(prog)s lesson "mistake" "fix"      Record a lesson learned
  %(prog)s status                      One-screen project status
  %(prog)s bootstrap                   Get new-session context dump
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search
    p_search = subparsers.add_parser("search", help="Search knowledge base topics.")
    p_search.add_argument("query", nargs="?", default="", help="Query to search for.")

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
    subparsers.add_parser("status", help="Print one-screen project status summary.")

    # Bootstrap
    subparsers.add_parser("bootstrap", help="Output new-session bootstrap context.")

    args = parser.parse_args()
    os.makedirs(DOCS_DIR, exist_ok=True)

    if args.command == "search":
        search(args.query)
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
        status()
    elif args.command == "bootstrap":
        bootstrap()


if __name__ == "__main__":
    main()
