"""Small, host-independent filesystem and Markdown primitives for OAW.

Writers coordinate on a stable sidecar lock, then replace the data file. Never
delete the lock file: deleting it could let two writers lock different inodes.
"""

from contextlib import contextmanager
import hashlib
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

# Credential shapes refused on evidence writes, because memory and annotations
# are committed project files. Only vendor-prefixed or key-anchored shapes:
# generic password=/TOKEN= heuristics stay out (too many false positives).
# re.ASCII keeps \w and \b ASCII-only, so a token right after CJK text still matches.
# Every start is bounded (a 32-character scheme, a JWT only outside a base64url run), so a
# long note scans in linear time.
# Adapted from claude-mem src/utils/redaction.ts:108-177 (Apache-2.0); modified: variable-width lookbehinds rewritten as consuming matches, PEM header only, refusal instead of redaction, generic and claude_mem_key patterns dropped, url_credentials/openai_key/aws_access_key/jwt bounded or anchored.
SECRET_PATTERNS = tuple((name, re.compile(pattern, re.ASCII | flags)) for name, pattern, flags in (
    # A password that is wholly a placeholder (${DB_PASS}, $DB_PASS, {db_pass}, {{db_pass}}, %s,
    # %(pw)s, ***) is exempt; <PASSWORD> never matches because '<' ends the value. A literal
    # user:pass or user:password is refused: documentation examples use a placeholder.
    ("url_credentials", r"\b[a-z][a-z0-9+.-]{0,31}://[^\s:/@'\"<>]*:"
                        r"(?!(?:\$\{[^}\s/@'\"<>]*\}|(?-i:\$[A-Z_][A-Z0-9_]*)|\{\{?[^{}\s/@'\"<>]*\}\}?"
                        r"|%(?:\(\w+\))?s|\*+)@)[^\s/@'\"<>]+@", re.IGNORECASE),
    ("aws_access_key", r"(?<![A-Za-z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Za-z0-9])", 0),
    ("aws_secret_key", r"(?i:aws_secret_access_key|\bSecretAccessKey)[\"']?\s*[:=]\s*[\"']?"
                       r"[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])", 0),
    ("aws_session_token", r"(?i:\baws_session_token|\bSessionToken)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{100,}", 0),
    ("github_pat", r"\bgh[oprsu]_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{82}\b", 0),
    # Project, service-account and admin keys name their kind; a legacy key is one alphanumeric
    # run with a digit, so kebab-case prose such as sk-learn-compatible-api is not a key.
    ("openai_key", r"\bsk-(?:(?:proj|svcacct|admin|None)-[A-Za-z0-9_-]{20,}(?!\w)"
                   r"|(?=[A-Za-z]*[0-9])[A-Za-z0-9]{20,}(?![\w-]))", 0),
    ("anthropic_key", r"\bsk-ant-[A-Za-z0-9_-]{20,}(?!\w)", 0),
    ("slack_token", r"\b(?:xox[abeprs]|xapp)-[A-Za-z0-9-]{10,}(?!\w)", 0),
    ("jwt", r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?!\w)", 0),
    ("private_key_pem", r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----", 0),
    ("stripe_key", r"\b(?:(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{24,}|whsec_[A-Za-z0-9]{32,})\b", 0),
    ("google_api_key", r"\bAIza[0-9A-Za-z_-]{35}(?!\w)", 0),
    ("gitlab_token", r"\bgl(?:pat|dt|rt)-[A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]+)*(?!\w)", 0),
    ("huggingface_token", r"\bhf_[A-Za-z0-9]{30,}\b", 0),
    ("npm_token", r"\bnpm_[A-Za-z0-9]{36}\b", 0),
    ("docker_pat", r"\bdckr_pat_[A-Za-z0-9_-]{27,}(?!\w)", 0),
    ("sendgrid_key", r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}(?![\w-])", 0),
    ("digitalocean_token", r"\bdo[opr]_v1_[a-f0-9]{64}\b", 0),
    ("shopify_token", r"\bshp(?:at|ca|pa|ss)_[a-fA-F0-9]{32}\b", 0),
    ("pypi_token", r"\bpypi-AgE[A-Za-z0-9_-]{50,}(?!\w)", 0),
    # Webhook URLs carry their secret in the path; the host must start the URL's host part.
    ("slack_webhook", r"(?:^|//|@|[^\w./@%-])(?i:hooks\.slack\.com)/(?:services|workflows|triggers)/"
                      r"T[A-Z0-9]+/[A-Z0-9]+/(?:[0-9]+/)?[A-Za-z0-9]{20,}(?!\w)", 0),
    ("discord_webhook", r"(?:^|//|@|[^\w./@%-])(?i:(?:(?:ptb|canary)\.)?discord(?:app)?\.com)/api/(?:v\d+/)?"
                        r"webhooks/[0-9]{17,20}/[A-Za-z0-9_-]{60,}(?![\w-])", 0),
))


def validate_topic_id(topic, allow_meta=False):
    """Accept a single portable filename stem, never a relative/absolute path."""
    if not isinstance(topic, str) or not re.fullmatch(r"[\w-]+", topic):
        raise ValueError("Topic IDs must contain only letters, digits, underscores or hyphens.")
    if topic.casefold() in _RESERVED:
        raise ValueError(f"Reserved topic ID: {topic!r}.")
    if not allow_meta and topic.casefold() in {"index", "log"}:
        raise ValueError(f"Topic ID {topic!r} is reserved for generated metadata.")
    return topic


def find_secret_names(text):
    """Names of the SECRET_PATTERNS found in text, never the matched values."""
    return [name for name, pattern in SECRET_PATTERNS if pattern.search(text)]


def evidence_write_refusal(text):
    """Return why an evidence write must be refused, or None to allow it.

    The one guard for the Context Hub CLI write path (memory add, lesson,
    annotate). It refuses instead of stripping and never echoes the text. A
    direct edit of the files bypasses it.
    """
    names = find_secret_names(text)
    if names:
        return (f"Refused: the note appears to contain a credential ({', '.join(names)}); nothing was written. "
                f"Replace it with a placeholder such as <{names[0].upper()}>.")
    return None


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


_DRIVE = re.compile(r"^[A-Za-z]:")


def normalize_cited_path(text):
    """Return a cited path as a project-relative POSIX path, identically on every OS.

    Backslashes become '/', and empty and '.' segments are dropped. A leading
    '/', a drive ('C:') in any segment or a '..' segment raises ValueError, so a
    Windows-shaped path is rejected on Linux too, before any join or stat.
    """
    path = text.strip().replace("\\", "/")
    parts = [part for part in path.split("/") if part not in ("", ".")]
    if path.startswith("/") or ".." in parts or any(_DRIVE.match(part) for part in parts):
        raise ValueError(f"Cited path is outside the project: {text}")
    if not parts:
        raise ValueError("Cited path is empty.")
    return "/".join(parts)


def exact_case_path(root, relative):
    """Resolve a cited project-relative path only when every segment matches on-disk case.

    Windows and macOS accept 'Scripts/A.py' for 'scripts/a.py'; comparing each
    segment with its directory listing gives the case-sensitive verdict on every
    OS. Returns the confined path, or None when a segment is missing or differs
    in case. Raises ValueError for a path outside root, including via symlinks.
    """
    parts = normalize_cited_path(relative).split("/")
    resolved = confined_path(root, *parts)
    current = str(Path(root).resolve())
    for part in parts:
        try:
            if part not in os.listdir(current):
                return None
        except OSError:
            return None
        current = os.path.join(current, part)
    return resolved


def _checked(path, root):
    return confined_path(root, path) if root is not None else str(Path(path).resolve())


def _unopened(path, root):
    """Confine like _checked without opening the target before its lock is held.

    On Windows resolve() opens the file, and any open handle makes the lock
    holder's os.replace fail. Resolve the parent and lstat the name instead.
    """
    path = os.path.join(Path(root).resolve(), path) if root is not None else os.path.abspath(path)
    name = os.path.basename(path)
    candidate = os.path.join(_checked(os.path.dirname(path), root), name)
    try:
        info = os.lstat(candidate)
        linked = stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0)
    except FileNotFoundError:
        linked = False
    # Links, junctions, 8.3 aliases and trailing dots need full canonicalization.
    if linked or not name or "~" in name or name.rstrip(". ") != name:
        return _checked(candidate, root)
    return candidate


@contextmanager
def _exclusive_lock(path, root=None, timeout=30):
    path = _unopened(path, root)
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
        _commit(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _commit(temporary, path, timeout=3):
    """os.replace, retrying while a Windows reader briefly holds the target open."""
    deadline, delay = time.monotonic() + timeout, 0.002
    while True:
        try:
            return os.replace(temporary, path)
        except PermissionError as exc:
            # ERROR_ACCESS_DENIED / ERROR_SHARING_VIOLATION; POSIX errors carry no winerror.
            if getattr(exc, "winerror", None) not in (5, 32) or time.monotonic() >= deadline:
                raise
        time.sleep(delay)
        delay = min(delay * 2, 0.05)


def locked_update(path, mutate, default="", *, root=None):
    """Apply mutate(text) under a process lock and atomically commit its result."""
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


def _fence_after(line, fence):
    """Fence state after line: only the opener's character, at least as long, closes it."""
    marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
    if not marker:
        return fence
    token = marker.group(1)
    if fence is None:
        return token
    return None if token[0] == fence[0] and len(token) >= len(fence) else fence


def _markdown_lines(content):
    """Yield offsets and fence state so code examples cannot delimit live notes."""
    offset, fence = 0, None
    for line in content.splitlines(keepends=True):
        after = _fence_after(line, fence)
        yield offset, line, fence is not None or after is not None
        offset, fence = offset + len(line), after


markdown_lines = _markdown_lines


def close_fence(text):
    """Terminate a fence text leaves open so following generated markers stay live."""
    fence = None
    for line in text.splitlines(keepends=True):
        fence = _fence_after(line, fence)
    if fence:
        text += ("" if text.endswith("\n") else "\n") + fence
    return text


def extract_annotations(content):
    return _annotation_parts(content)[1]


def render_annotations(notes=""):
    safe = []
    for _offset, line, in_code in _markdown_lines(notes.strip()):
        if not in_code and line.strip() in {ANNOTATIONS_START, ANNOTATIONS_END}:
            line = line.replace("<", "&lt;", 1)
        safe.append(line)
    # A partially pasted example must not swallow the structural end marker.
    return "## AI Annotations\n\n" + ANNOTATIONS_START + "\n" + close_fence("".join(safe)) + "\n" + ANNOTATIONS_END + "\n"


def append_annotation(content, annotation):
    head, notes, tail = _annotation_parts(content)
    notes = notes.rstrip() + ("\n\n" if notes.strip() else "") + annotation.strip()
    return head.rstrip() + "\n\n" + render_annotations(notes) + tail


# >>> cli resolver
# resolver_sha256() hashes every line from the opening marker through the closing marker.
_SHIM_LIMIT = 8192
# npm cmd-shim forms: "%_prog%" "%dp0%\node_modules\...\cli.js" %*  or  "%dp0%\node_modules\...\x.exe" %*
_CMD_TARGET = re.compile(r'("%_prog%"[ \t]+)?"%dp0%\\([^"%\r\n]+)"[ \t]*%\*')
_CMD_PROGRAM = re.compile(r'SET "_prog=([^"\r\n]*)"', re.IGNORECASE)
_PS1_TARGET = re.compile(r'&[ \t]+("(?:\$basedir/)?node\$exe"[ \t]+)?"\$basedir/([^"$`\r\n]+)"[ \t]*\$args')


def _which(name, directories, extensions, windows):
    suffix = os.path.splitext(name)[1].lower()
    known = suffix in extensions or (windows and suffix == ".ps1")
    names = [name] if suffix and known else [name + extension for extension in extensions]
    for directory in directories:
        for candidate in (os.path.join(directory, item) for item in names):
            if os.path.isfile(candidate) and (windows or os.access(candidate, os.X_OK)):
                return os.path.abspath(candidate)
    return None


def _npm_shim(path, directories):
    """[node.exe, script.js] or [program.exe] for an npm .cmd/.ps1 shim; refuse anything else."""
    # Adapted from tokeneconomizer tokeneconomizer/plugin/sidecall.py (Apache-2.0); modified: own patterns, one target only, node_modules confinement, 8 KB cap, refusal raises.
    with open(path, "rb") as handle:
        data = handle.read(_SHIM_LIMIT + 1)
    text = data.decode("utf-8", "replace")
    powershell = path.lower().endswith(".ps1")
    targets = {(bool(node), relative) for node, relative in (_PS1_TARGET if powershell else _CMD_TARGET).findall(text)}
    programs = {value.lower() for value in _CMD_PROGRAM.findall(text)}
    folder = os.path.dirname(path)
    if len(data) <= _SHIM_LIMIT and len(targets) == 1 and programs <= {"%dp0%\\node.exe", "node"}:
        (node, relative), = targets
        modules = os.path.normcase(os.path.join(folder, "node_modules")) + os.sep
        target = os.path.normpath(os.path.join(folder, relative.replace("\\", os.sep)))
        if (os.path.normcase(target).startswith(modules) and os.path.isfile(target)
                and target.lower().endswith(".js" if node else ".exe") and (powershell or not node or programs)):
            if not node:
                return [target]
            program = os.path.join(folder, "node.exe")
            program = program if os.path.isfile(program) else _which("node.exe", directories, (".exe",), True)
            if not program:
                raise FileNotFoundError(f"node.exe for npm shim {path} is not on PATH")
            return [program, target]
    raise ValueError(f"refusing non-npm {'PowerShell script' if powershell else 'batch file'}: {path}")


def resolve_cli(name_or_path, *, platform=os.name, search_path=None):
    """Return the argv list that starts a CLI directly; run it with shell=False.

    Only absolute PATH entries are searched, never the current directory. On Windows an npm
    .cmd/.ps1 shim is read and its node script or native .exe is started instead, so cmd.exe
    never parses the arguments again; any other script is refused. Elsewhere the result is
    the plain absolute path.
    """
    if not isinstance(name_or_path, str) or not name_or_path.strip():
        raise ValueError("A CLI name or path is required")
    windows = platform == "nt"
    pathext = (os.environ.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD").split(";")
    extensions = tuple(dict.fromkeys(item.lower() for item in pathext if item.startswith("."))) if windows else ("",)
    entries = os.environ.get("PATH", "") if search_path is None else search_path
    directories = [entry for entry in (item.strip('"') for item in entries.split(os.pathsep)) if os.path.isabs(entry)]
    if os.path.dirname(name_or_path):
        explicit = os.path.abspath(name_or_path)
        found = _which(os.path.basename(explicit), [os.path.dirname(explicit)], extensions, windows)
    else:
        found = _which(name_or_path, directories, extensions, windows)
    if not found:
        raise FileNotFoundError(f"CLI not found: {name_or_path!r} (the current directory is not searched)")
    suffix = os.path.splitext(found)[1].lower()
    if not windows or suffix in (".exe", ".com"):
        return [found]
    if suffix in (".cmd", ".bat", ".ps1"):
        return _npm_shim(found, directories)
    raise ValueError(f"refusing {found}: only an .exe or an npm shim starts without a shell")
# <<< cli resolver


def resolver_sha256():
    """SHA-256 of the CLI resolver block above (LF line endings); record it beside cli_argv."""
    lines = Path(__file__).read_text(encoding="utf-8").splitlines()
    start, end = lines.index("# >>> cli resolver"), lines.index("# <<< cli resolver")
    return hashlib.sha256("\n".join(lines[start:end + 1]).encode("utf-8")).hexdigest()
