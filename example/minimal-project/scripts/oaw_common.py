"""Small, host-independent filesystem and Markdown primitives for OAW.

Writers coordinate on a stable sidecar lock, then replace the data file. Never
delete the lock file: deleting it could let two writers lock different inodes.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat
import tempfile
import time

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None

ANNOTATIONS_START = "<!-- oaw:annotations:start -->"
ANNOTATIONS_END = "<!-- oaw:annotations:end -->"
_ANNOTATION_HEADING = re.compile(r"^## AI Annotations[ \t]*$", re.MULTILINE)
_RESERVED = {"con", "prn", "aux", "nul"} | {
    prefix + str(number) for prefix in ("com", "lpt") for number in range(1, 10)
}


def validate_topic_id(topic, allow_meta=False):
    """Accept a single portable filename stem, never a relative/absolute path."""
    if not isinstance(topic, str) or not re.fullmatch(r"[\w-]+", topic):
        raise ValueError("Topic IDs must contain only letters, digits, underscores or hyphens.")
    if topic.casefold() in _RESERVED:
        raise ValueError(f"Reserved topic ID: {topic!r}.")
    if not allow_meta and topic.casefold() in {"index", "log"}:
        raise ValueError(f"Topic ID {topic!r} is reserved for generated metadata.")
    return topic


def confined_path(root, *parts):
    """Resolve a path and reject escapes through '..', absolute paths or symlinks.

    The root itself may be a user-selected symlink. Its resolved directory is
    the boundary. Existing symlink ancestors of the target are resolved too.
    """
    boundary = Path(root).resolve()
    candidate = boundary.joinpath(*parts).resolve()
    try:
        common = os.path.commonpath([os.path.normcase(str(boundary)), os.path.normcase(str(candidate))])
    except ValueError as exc:
        raise ValueError("Path is outside the project boundary.") from exc
    if common != os.path.normcase(str(boundary)):
        raise ValueError("Path is outside the project boundary.")
    return str(candidate)


def _checked(path, root):
    return confined_path(root, path) if root is not None else str(Path(path).resolve())


@contextmanager
def _exclusive_lock(path, root=None, timeout=30):
    path = _checked(path, root)
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    lock_path = _checked(os.path.join(parent, "." + os.path.basename(path) + ".oaw.lock"), root)
    with open(lock_path, "a+b") as handle:
        # Windows byte-range locks require a stable byte even for a new file.
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:
            deadline = time.monotonic() + timeout
            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Timed out waiting for the OAW file lock.")
                    time.sleep(0.025)
        else:
            raise RuntimeError("This platform does not provide a supported file lock.")
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _replace(path, text, root=None):
    path = _checked(path, root)
    parent = os.path.dirname(path)
    descriptor, temporary = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if os.path.exists(path):
            os.chmod(temporary, stat.S_IMODE(os.stat(path).st_mode))
        # Recheck after mutate() and before committing, including symlink parents.
        checked = _checked(path, root)
        if checked != path:
            raise ValueError("The write target changed while it was locked.")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def locked_update(path, mutate, default="", *, root=None):
    """Apply mutate(text) under a process lock and atomically commit its result."""
    path = _checked(path, root)
    with _exclusive_lock(path, root=root):
        path = _checked(path, root)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                current = handle.read()
        except FileNotFoundError:
            current = default
        updated = mutate(current)
        if not isinstance(updated, str):
            raise TypeError("A locked_update mutation must return text.")
        if updated != current or not os.path.exists(path):
            _replace(path, updated, root=root)
        return updated


def atomic_write(path, text, *, root=None):
    locked_update(path, lambda _current: text, root=root)


def _annotation_parts(content):
    headings, starts, ends = [], [], []
    for offset, line, in_code in _markdown_lines(content):
        if in_code:
            continue
        stripped = line.rstrip("\r\n \t")
        if _ANNOTATION_HEADING.fullmatch(stripped):
            headings.append((offset, offset + len(stripped)))
        elif stripped == ANNOTATIONS_START:
            starts.append((offset, offset + len(stripped)))
        elif stripped == ANNOTATIONS_END:
            ends.append((offset, offset + len(stripped)))
    blocks = [(heading, start) for heading in headings for start in starts
              if start[0] > heading[1] and not content[heading[1]:start[0]].strip()]
    if blocks:
        heading, start = blocks[-1]
        following_ends = [end for end in ends if end[0] > start[1]]
        if not following_ends:
            raise ValueError("Annotation block is missing its closing delimiter.")
        end = following_ends[-1]
        return content[:heading[0]], content[start[1]:end[0]].strip(), content[end[1]:]
    # Legacy generated pages always put their own annotation heading last.
    # Taking the first heading accidentally preserves copied raw source content.
    if not headings:
        return content, "", ""
    heading = headings[-1]
    remainder = content[heading[1]:]
    next_heading = re.search(r"^#{1,2}\s+", remainder, re.MULTILINE)
    if next_heading:
        return content[:heading[0]], remainder[:next_heading.start()].strip(), remainder[next_heading.start():]
    return content[:heading[0]], remainder.strip(), ""


def _markdown_lines(content):
    """Yield offsets and fence state so code examples cannot delimit live notes."""
    offset, fence = 0, None
    for line in content.splitlines(keepends=True):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        in_code = fence is not None or marker is not None
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        yield offset, line, in_code
        offset += len(line)


def extract_annotations(content):
    return _annotation_parts(content)[1]


def render_annotations(notes=""):
    safe = []
    fence = None
    for _offset, line, in_code in _markdown_lines(notes.strip()):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        if not in_code and line.strip() in {ANNOTATIONS_START, ANNOTATIONS_END}:
            line = line.replace("<", "&lt;", 1)
        safe.append(line)
    if fence:
        # A partially pasted example must not swallow the structural end marker.
        safe.append("\n" + fence)
    return "## AI Annotations\n\n" + ANNOTATIONS_START + "\n" + "".join(safe) + "\n" + ANNOTATIONS_END + "\n"


def append_annotation(content, annotation):
    head, notes, tail = _annotation_parts(content)
    notes = notes.rstrip() + ("\n\n" if notes.strip() else "") + annotation.strip()
    return head.rstrip() + "\n\n" + render_annotations(notes) + tail
