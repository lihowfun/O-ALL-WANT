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
SKILLS_DIR = os.path.join(BASE_DIR, ".agents", "skills")
SKILLS_USAGE_FILE = os.path.join(SKILLS_DIR, ".usage.json")
SKILLS_ARCHIVE_DIR = os.path.join(SKILLS_DIR, ".archive")
META_PAGE_TYPES = {"meta"}

# Skill audit thresholds (env-overridable)
SKILL_STALE_DAYS = int(os.environ.get("OAW_SKILL_STALE_DAYS", "30"))
# Grace period (days since the .md file was created) during which an
# unused skill is shown as 🌱 fresh instead of ⚠️ stale. Stops day-1
# audits from yelling "everything is stale" on a freshly installed repo.
SKILL_STALE_GRACE_DAYS = int(os.environ.get("OAW_SKILL_STALE_GRACE_DAYS", "7"))

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


def _locked_rmw(filepath, mutate, default_initial="", os_name=None,
                fcntl_module=fcntl, msvcrt_module=msvcrt):
    """Atomic read-modify-write under an exclusive lock.

    `mutate(current_content) -> new_content` is called with the file's current
    text (or `default_initial` if the file is missing/empty). The file is then
    truncated and rewritten with the result. The lock spans **both** the read
    and the write, so two concurrent writers cannot independently snapshot the
    same state and overwrite each other's edits.

    Use this instead of read-then-`_locked_write` whenever the new content
    depends on the existing content (append, increment, JSON merge, etc.).
    """
    backend, lock_module = _resolve_lock_backend(
        os_name=os_name,
        fcntl_module=fcntl_module,
        msvcrt_module=msvcrt_module,
    )
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)

    # "a+" gives us read access AND creates the file if missing. After
    # truncate() the file size is 0; subsequent write() lands at offset 0
    # because that is current EOF.
    with open(filepath, "a+", encoding="utf-8") as f:
        # Acquire exclusive lock BEFORE the read so no other writer can sneak
        # in between our read and our write.
        if backend == "windows":
            f.seek(0)
            lock_module.locking(f.fileno(), lock_module.LK_LOCK, 1)
        elif backend == "posix":
            lock_module.flock(f, lock_module.LOCK_EX)

        try:
            f.seek(0)
            content = f.read()
            if not content:
                content = default_initial
            new_content = mutate(content)
            f.seek(0)
            f.truncate()
            f.write(new_content)
            f.flush()
            try:
                os.fsync(f.fileno())  # durability — survives a process kill
            except OSError:
                pass
        finally:
            if backend == "windows":
                f.seek(0)
                try:
                    lock_module.locking(f.fileno(), lock_module.LK_UNLCK, 1)
                except OSError:
                    pass
            elif backend == "posix":
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

    # Pre-flight read to bail on meta pages before taking the lock.
    with open(file_path, "r", encoding="utf-8") as f:
        preview = f.read()
    metadata, _body = _parse_frontmatter(preview)
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

    def _append(content: str) -> str:
        if "## AI Annotations" in content:
            return content + annotation_block
        return content + f"\n\n## AI Annotations\n{annotation_block}"

    _locked_rmw(file_path, _append, default_initial=preview)
    print(f"✅ Annotated '{topic}' with: {note[:60]}...")


# ─── Memory ───────────────────────────────────────────────────────────────────

def memory_add(note):
    """Add a structured entry to the rolling memory.

    Atomic w.r.t. concurrent writers: 20 processes calling this in parallel
    will all 20 entries survive (verified by a concurrency test in
    harness_check.py). Implementation uses _locked_rmw so the read and the
    write happen under the same exclusive lock.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Auto-detect tag
    tag_match = re.match(r'^\[(\w+)\]', note)
    tag = tag_match.group(1) if tag_match else "NOTE"

    note_body = _strip_tag_prefix(note) if tag_match else note
    # Strip a duplicate leading date if the user already included today's date
    note_body = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', note_body)

    entry = f"\n## [{timestamp}] [{tag}] {note_body}\n"

    def _insert(content: str) -> str:
        # Insert after the first "---" separator (after header).
        separator_pos = content.find("---")
        if separator_pos != -1:
            insert_pos = content.find("\n", separator_pos) + 1
            return content[:insert_pos] + entry + content[insert_pos:]
        return content + entry

    _locked_rmw(
        MEMORY_FILE,
        _insert,
        default_initial="# Agent Memory — Decision & Finding Log\n\n---\n",
    )
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


# ─── Memory recall ────────────────────────────────────────────────────────────
#
# Inspired by Hermes Agent's session_search (FTS5 + LLM summary). OAW is
# markdown-first so we use Python regex over memory.md + docs/knowledge/*.md
# and return the top hits with surrounding context, leaving any summarization
# to the calling LLM. Cheap, predictable, no extra deps.

def memory_recall(query, limit=8, context_lines=2):
    """Find query across memory.md + knowledge pages; show top hits with context."""
    if not query.strip():
        print("Empty query — provide at least one word.")
        return

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits = []

    def _scan(filepath, label):
        if not os.path.exists(filepath):
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return
        # Collect all matching line indices in this file.
        match_idxs = [i for i, line in enumerate(lines) if pattern.search(line)]
        if not match_idxs:
            return
        # Merge matches whose context windows overlap so adjacent hits don't
        # produce near-duplicate output blocks. Each merged hit lists the
        # union of match line_nos and the union of context lines.
        groups: list[list[int]] = []
        for i in match_idxs:
            if groups and i - groups[-1][-1] <= 2 * context_lines + 1:
                groups[-1].append(i)
            else:
                groups.append([i])
        for grp in groups:
            start = max(0, grp[0] - context_lines)
            end = min(len(lines), grp[-1] + context_lines + 1)
            match_set = set(grp)
            ctx = []
            for j in range(start, end):
                ctx.append({"line": lines[j].rstrip(), "is_match": j in match_set})
            hits.append({
                "file": label,
                "line_no": grp[0] + 1,
                "match_line_nos": [j + 1 for j in grp],
                "context": ctx,
            })

    # Memory first (chronological signal), then knowledge wiki.
    _scan(MEMORY_FILE, ".agents/memory.md")
    if os.path.isdir(DOCS_DIR):
        for fname in sorted(os.listdir(DOCS_DIR)):
            if fname.endswith(".md"):
                _scan(os.path.join(DOCS_DIR, fname), f"docs/knowledge/{fname}")

    if not hits:
        print(f"No matches for {query!r} across memory.md + docs/knowledge/.")
        return

    print(f"\n{'='*70}")
    print(f"  RECALL: {query!r} — {len(hits)} hit(s) (showing top {min(limit, len(hits))})")
    print(f"{'='*70}\n")
    for h in hits[:limit]:
        # When a group merges multiple match lines, show all of them.
        line_repr = (
            f"{h['line_no']}"
            if len(h["match_line_nos"]) == 1
            else f"{h['line_no']} (+{len(h['match_line_nos']) - 1} more)"
        )
        print(f"📍 {h['file']}:{line_repr}")
        for cl in h["context"]:
            marker = "▶ " if cl["is_match"] else "│ "
            print(f"  {marker}{cl['line']}")
        print()


# ─── Skills lifecycle (usage tracking + audit + archive) ─────────────────────
#
# Inspired by Hermes Agent's curator (agent/curator.py) — every skill carries
# usage metadata in a sidecar so we can spot dead weight and archive it.
# Differences from Hermes:
#   - One shared JSON (.usage.json) instead of per-skill sidecars — easier to
#     hand-edit and audit at a glance.
#   - No background daemon; archive is opt-in via `skills archive <name>`.
#   - State machine: active → stale → archived. `pinned: true` exempts a skill.

def _load_skill_usage():
    """Read-only load — fine for audit / display where we don't write back."""
    if not os.path.exists(SKILLS_USAGE_FILE):
        return {}
    try:
        with open(SKILLS_USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _update_skill_usage(mutate):
    """Atomic load → mutate(dict) → save under one exclusive lock.

    Two processes calling skills use/patch/pin concurrently will NOT
    overwrite each other's increments. Use this for any operation that
    needs the post-read value to be still-valid at write time.
    """
    os.makedirs(SKILLS_DIR, exist_ok=True)

    def _do(text: str) -> str:
        try:
            data = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            data = {}
        mutate(data)
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    _locked_rmw(SKILLS_USAGE_FILE, _do, default_initial="{}\n")


def _list_skill_files(include_archive=False):
    if not os.path.isdir(SKILLS_DIR):
        return []
    out = []
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if fname.startswith("_") or fname.startswith("."):
            continue
        if fname.lower() == "readme.md":
            continue
        if fname.endswith(".md"):
            out.append(fname[:-3])  # strip .md
    if include_archive and os.path.isdir(SKILLS_ARCHIVE_DIR):
        for fname in sorted(os.listdir(SKILLS_ARCHIVE_DIR)):
            if fname.endswith(".md"):
                out.append(f".archive/{fname[:-3]}")
    return out


def _ensure_entry(data, name):
    """In-place: make sure data[name] has the standard fields."""
    entry = data.get(name, {})
    now = datetime.now().isoformat(timespec="seconds")
    entry.setdefault("first_seen", now)
    entry.setdefault("use_count", 0)
    entry.setdefault("patch_count", 0)
    entry.setdefault("pinned", False)
    entry.setdefault("state", "active")
    data[name] = entry
    return entry


def skill_use(name):
    """Record that a skill was used this session (+1 to use_count, refresh ts)."""
    skill_path = os.path.join(SKILLS_DIR, f"{name}.md")
    if not os.path.exists(skill_path):
        print(f"❌ Skill {name!r} not found at {skill_path}")
        return
    new_count = [0]
    last = [""]

    def _bump(data):
        entry = _ensure_entry(data, name)
        entry["use_count"] = int(entry["use_count"]) + 1
        entry["last_used"] = datetime.now().isoformat(timespec="seconds")
        new_count[0] = entry["use_count"]
        last[0] = entry["last_used"]

    _update_skill_usage(_bump)
    print(f"✓ {name}: use_count={new_count[0]} last_used={last[0]}")


def skill_patch(name):
    """Record that a skill was modified (e.g. via /skill-review). +1 patch_count."""
    skill_path = os.path.join(SKILLS_DIR, f"{name}.md")
    if not os.path.exists(skill_path):
        print(f"❌ Skill {name!r} not found")
        return
    new_count = [0]

    def _bump(data):
        entry = _ensure_entry(data, name)
        entry["patch_count"] = int(entry["patch_count"]) + 1
        entry["last_patched"] = datetime.now().isoformat(timespec="seconds")
        new_count[0] = entry["patch_count"]

    _update_skill_usage(_bump)
    print(f"✓ {name}: patch_count={new_count[0]}")


def skill_pin(name, pinned=True):
    """Toggle the pinned flag so the audit will not flag a skill as stale."""

    def _toggle(data):
        entry = _ensure_entry(data, name)
        entry["pinned"] = bool(pinned)

    _update_skill_usage(_toggle)
    print(f"{'📌 pinned' if pinned else 'unpinned'}: {name}")


def skills_audit():
    """List skills, flag stale ones (no use in SKILL_STALE_DAYS, not pinned).

    Skills installed within SKILL_STALE_GRACE_DAYS are shown as 🌱 fresh
    instead of ⚠️ stale, so a Day-1 audit on a freshly installed repo
    doesn't blanket-flag everything.
    """
    files = _list_skill_files()
    usage = _load_skill_usage()
    if not files:
        print("No skills present.")
        return
    now = datetime.now()
    print(f"\n{'='*70}")
    print(
        f"  SKILLS AUDIT — {len(files)} skills, stale={SKILL_STALE_DAYS}d, "
        f"grace={SKILL_STALE_GRACE_DAYS}d"
    )
    print(f"{'='*70}\n")
    rows = []
    for name in files:
        entry = usage.get(name, {})
        uc = entry.get("use_count", 0)
        pc = entry.get("patch_count", 0)
        last = entry.get("last_used") or entry.get("first_seen")
        pinned = bool(entry.get("pinned"))
        state = entry.get("state", "active")
        age_days = None
        if last:
            try:
                age_days = (now - datetime.fromisoformat(last)).days
            except ValueError:
                pass

        # File mtime gives a robust "how long has this skill been here" signal
        # that survives missing usage entries.
        skill_path = os.path.join(SKILLS_DIR, f"{name}.md")
        install_age_days = None
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(skill_path))
            install_age_days = (now - mtime).days
        except OSError:
            pass

        fresh = (
            uc == 0 and pc == 0
            and install_age_days is not None
            and install_age_days < SKILL_STALE_GRACE_DAYS
        )
        stale = not pinned and not fresh and (
            (uc == 0 and pc == 0)
            or (age_days is not None and age_days >= SKILL_STALE_DAYS)
        )
        rows.append((name, uc, pc, last or "(never recorded)", pinned, stale, fresh, state))

    # Sort: stale first, then fresh, then by use_count ascending
    rows.sort(key=lambda r: (not r[5], not r[6], r[1]))

    for name, uc, pc, last, pinned, stale, fresh, state in rows:
        flags = []
        if pinned:
            flags.append("📌pinned")
        if stale:
            flags.append("⚠️stale")
        elif fresh:
            flags.append("🌱fresh")
        if state != "active":
            flags.append(f"[{state}]")
        marker = " ".join(flags)
        print(f"  {name:<28}  use={uc:>3}  patch={pc:>2}  last={last}  {marker}")
    print()
    stale_count = sum(1 for r in rows if r[5])
    if stale_count:
        print(f"  → {stale_count} stale skill(s). Review and consider:")
        print('    python3 scripts/context_hub.py skills archive <name>')
        print('    python3 scripts/context_hub.py skills pin <name>     # if still relevant')
    else:
        print("  → no stale skills.")


def skills_archive(name):
    """Move <name>.md into .archive/ and mark its usage entry archived."""
    src = os.path.join(SKILLS_DIR, f"{name}.md")
    if not os.path.exists(src):
        print(f"❌ Skill {name!r} not found")
        return
    os.makedirs(SKILLS_ARCHIVE_DIR, exist_ok=True)
    dst = os.path.join(SKILLS_ARCHIVE_DIR, f"{name}.md")
    if os.path.exists(dst):
        print(f"❌ {dst} already exists — rename or delete first")
        return
    os.rename(src, dst)

    def _mark(data):
        entry = _ensure_entry(data, name)
        entry["state"] = "archived"
        entry["archived_at"] = datetime.now().isoformat(timespec="seconds")

    _update_skill_usage(_mark)
    print(f"📦 archived: {name}.md → .archive/{name}.md")


def skills_unarchive(name):
    """Move <name>.md back from .archive/ to the live skill set."""
    src = os.path.join(SKILLS_ARCHIVE_DIR, f"{name}.md")
    if not os.path.exists(src):
        print(f"❌ {src} not found")
        return
    dst = os.path.join(SKILLS_DIR, f"{name}.md")
    if os.path.exists(dst):
        print(f"❌ {dst} already present — refusing to overwrite")
        return
    os.rename(src, dst)

    def _mark(data):
        entry = _ensure_entry(data, name)
        entry["state"] = "active"
        entry.pop("archived_at", None)

    _update_skill_usage(_mark)
    print(f"✓ restored: .archive/{name}.md → {name}.md")


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

    p_mem_recall = mem_sub.add_parser(
        "recall",
        help="Find query across memory.md + docs/knowledge with surrounding context.",
    )
    p_mem_recall.add_argument("query", help="Substring (case-insensitive).")
    p_mem_recall.add_argument("--limit", type=int, default=8, help="Max hits to show.")
    p_mem_recall.add_argument("--context", type=int, default=2, help="Lines of context per hit.")

    # Skills
    p_skills = subparsers.add_parser("skills", help="Skill lifecycle: usage, audit, archive.")
    sk_sub = p_skills.add_subparsers(dest="sk_action", required=True)

    p_sk_use = sk_sub.add_parser("use", help="Record a skill was used (+1 use_count).")
    p_sk_use.add_argument("name", help="Skill name (filename without .md).")

    p_sk_patch = sk_sub.add_parser("patch", help="Record a skill was modified (+1 patch_count).")
    p_sk_patch.add_argument("name", help="Skill name.")

    p_sk_pin = sk_sub.add_parser("pin", help="Pin a skill (exempt from stale audit).")
    p_sk_pin.add_argument("name", help="Skill name.")
    p_sk_unpin = sk_sub.add_parser("unpin", help="Unpin a skill.")
    p_sk_unpin.add_argument("name", help="Skill name.")

    sk_sub.add_parser("audit", help="List skills with usage + flag stale candidates.")

    p_sk_arch = sk_sub.add_parser("archive", help="Move skill into .archive/ subdir.")
    p_sk_arch.add_argument("name", help="Skill name (without .md).")
    p_sk_unarch = sk_sub.add_parser("unarchive", help="Restore a skill from .archive/.")
    p_sk_unarch.add_argument("name", help="Skill name.")

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
        elif args.mem_action == "recall":
            memory_recall(args.query, limit=args.limit, context_lines=args.context)
    elif args.command == "skills":
        if args.sk_action == "use":
            skill_use(args.name)
        elif args.sk_action == "patch":
            skill_patch(args.name)
        elif args.sk_action == "pin":
            skill_pin(args.name, pinned=True)
        elif args.sk_action == "unpin":
            skill_pin(args.name, pinned=False)
        elif args.sk_action == "audit":
            skills_audit()
        elif args.sk_action == "archive":
            skills_archive(args.name)
        elif args.sk_action == "unarchive":
            skills_unarchive(args.name)
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
