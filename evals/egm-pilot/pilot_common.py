"""Shared standard-library helpers for the EGM fast-track pilot.

Nothing here calls a model or runs a subprocess. run_pilot.py and score.py both
import it, and spec.json pins its hash, so scoring rules cannot change silently
after results are seen.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
SPEC_FILE = "spec.json"
SPEC_HASH_FILE = "spec.sha256"
SCENARIOS_FILE = "scenarios.json"
DEFECTS_FILE = "outcome/defects.json"
DRAFT_FILE = "outcome/project/docs/design_draft.md"
FIXTURE_DIRS = ("protocol/project", "outcome/project", "outcome/overlay-oaw")
SCORER_FILES = ("pilot_common.py", "score.py")
ARMS = ("A", "B", "C")
METRICS = ("tokens", "latency_ms", "cost_usd")  # the names scripts/improvement.py validates
QUESTION_TOOLS = ("AskUserQuestion",)
SUBAGENT_TOOLS = ("Agent", "Task")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def file_digest(path: Path) -> str:
    """Hash with CRLF folded to LF, so a Windows autocrlf checkout hashes the same."""
    return sha256(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def load_json(path: Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def json_digest(path: Path) -> str:
    return sha256(canonical(load_json(path)))


def tree_digest(root: Path, relative_dirs) -> str:
    entries = []
    for relative in relative_dirs:
        base = Path(root) / relative
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f"missing or aliased directory: {base}")
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"symlink in hashed tree: {path}")
            if path.is_file() and "__pycache__" not in path.parts:
                entries.append((path.relative_to(root).as_posix(), file_digest(path)))
    return sha256("\n".join(f"{name}\0{value}" for name, value in sorted(entries)).encode("utf-8"))


def spec_digest(spec: dict) -> str:
    return sha256(canonical(spec))


def recorded_spec_digest(root: Path) -> str | None:
    path = Path(root) / SPEC_HASH_FILE
    if not path.is_file():
        return None
    words = path.read_text(encoding="utf-8").split()
    return words[0] if words and re.fullmatch(r"[0-9a-f]{64}", words[0]) else None


def input_digests(root: Path) -> dict:
    root = Path(root)
    return {
        SCENARIOS_FILE: json_digest(root / SCENARIOS_FILE),
        DEFECTS_FILE: json_digest(root / DEFECTS_FILE),
        "fixtures": tree_digest(root, FIXTURE_DIRS),
        "scorer": sha256("\n".join(f"{name}\0{file_digest(root / name)}" for name in SCORER_FILES).encode("utf-8")),
    }


def spec_problems(root: Path) -> list[str]:
    """Why the pre-registered contract no longer matches the files (empty = intact)."""
    root = Path(root)
    spec = load_json(root / SPEC_FILE)
    problems = []
    recorded = recorded_spec_digest(root)
    if recorded is None:
        problems.append(f"{SPEC_HASH_FILE} is missing or malformed")
    elif recorded != spec_digest(spec):
        problems.append(f"{SPEC_FILE} changed after {SPEC_HASH_FILE} was written")
    expected = spec.get("inputs", {})
    for name, value in input_digests(root).items():
        if expected.get(name) != value:
            problems.append(f"input {name} differs from the hash pinned in {SPEC_FILE}")
    return problems


def approval_token(phase: str, digest: str) -> str:
    return f"{phase}-{digest[:12]}"


# ---- assertions (protocol suite) -------------------------------------------------

def operand(assertion: dict) -> str:
    return assertion["pattern"] if "pattern" in assertion else assertion["value"]


def assertion_passes(assertion: dict, text: str) -> bool:
    kind, value = assertion["type"], operand(assertion)
    if kind == "required_pattern":
        return re.search(value, text) is not None
    if kind == "forbidden_pattern":
        return re.search(value, text) is None
    if kind == "contains":
        return value in text
    if kind == "not_contains":
        return value not in text
    raise ValueError(f"unknown assertion type {kind!r}")


def assertion_keys(scenario: dict) -> list[str]:
    return [f"{scenario['case_id']}#{assertion['id']}" for turn in scenario["turns"] for assertion in turn["assertions"]]


# ---- raw host output ---------------------------------------------------------------

def parse_output(raw: str) -> dict:
    """Parse `--output-format json` (one object or array) or stream-json (JSON lines)."""
    events = []
    stripped = raw.strip()
    if stripped:
        try:
            value = json.loads(stripped)
            events = value if isinstance(value, list) else [value]
        except ValueError:
            for line in raw.split("\n"):  # literal LF: splitlines() would split inside JSON strings
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except ValueError:
                    events.append({"type": "unparsed"})
    events = [event for event in events if isinstance(event, dict)]
    result = next((event for event in reversed(events) if event.get("type") == "result"), None)
    init = next((event for event in events if event.get("type") == "system" and event.get("subtype") == "init"), None)
    return {"events": events, "result": result, "init": init,
            "unparsed": sum(event.get("type") == "unparsed" for event in events)}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def parent_blocks(parsed: dict):
    for event in parsed["events"]:
        if event.get("type") != "assistant" or event.get("parent_tool_use_id"):
            continue
        content = (event.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict):
                yield block


def response_text(parsed: dict) -> str:
    """Parent-session assistant text plus question-tool options of one turn."""
    parts = []
    for block in parent_blocks(parsed):
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
        elif block.get("type") == "tool_use" and block.get("name") in QUESTION_TOOLS:
            parts.extend(strings(block.get("input")))
    final = (parsed["result"] or {}).get("result")
    if isinstance(final, str) and final.strip() and all(final.strip() not in part for part in parts):
        parts.append(final)
    return "\n".join(parts)


def subagent_count(parsed: dict) -> int:
    return sum(block.get("type") == "tool_use" and block.get("name") in SUBAGENT_TOOLS for block in parent_blocks(parsed))


def failure(parsed: dict, invocation: dict) -> str | None:
    """Why an invocation does not count as a completed turn (None when it does)."""
    if invocation.get("timed_out"):
        return "timeout"
    if invocation.get("exit_code") != 0:
        return f"exit {invocation.get('exit_code')}"
    result = parsed["result"]
    if result is None:
        return "no result event"
    if result.get("is_error"):
        return f"error result ({result.get('subtype')})"
    if result.get("subtype") not in (None, "success"):
        return str(result.get("subtype"))
    return None


def usage(parsed: dict) -> dict:
    """Operator-reported resource numbers from the host's result event."""
    result = parsed["result"] or {}
    tokens, source = None, None
    model_usage = result.get("modelUsage")
    if isinstance(model_usage, dict) and model_usage:
        tokens, source = 0, "modelUsage"
        for entry in model_usage.values():
            for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"):
                tokens += int((entry or {}).get(key) or 0)
    elif isinstance(result.get("usage"), dict):
        tokens, source = 0, "usage"
        for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            tokens += int(result["usage"].get(key) or 0)
    cost = result.get("total_cost_usd")
    return {"tokens": tokens, "tokens_source": source,
            "cost_usd": float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
            "duration_ms": result.get("duration_ms"), "num_turns": result.get("num_turns")}


def init_summary(parsed: dict) -> dict | None:
    """What the host says it loaded: the isolation evidence for an arm."""
    init = parsed["init"]
    if not isinstance(init, dict):
        return None

    def names(field):
        value = init.get(field)
        if not isinstance(value, list):
            return None
        return sorted({str(item.get("name") if isinstance(item, dict) else item) for item in value})

    plugins, commands, skills, servers = names("plugins"), names("slash_commands"), names("skills"), names("mcp_servers")
    offered = (commands or []) + (skills or [])
    return {
        "model": init.get("model"),
        "plugins": plugins,
        "other_plugins": None if plugins is None else [name for name in plugins if name != "egm"],
        "egm_loaded": (plugins is not None and "egm" in plugins) or any(name.startswith("egm:") for name in offered),
        "oaw_loaded": any(name == "oaw-evidence" or name.endswith(":oaw-evidence") for name in offered),
        "mcp_servers": servers,
        "fields_present": sorted(field for field in ("plugins", "slash_commands", "skills", "mcp_servers") if field in init),
    }


# ---- planted defects (outcome suite) ----------------------------------------------

MARKERS = re.compile(r"^[\s>*+#|`\-\d.)]*")


def normalized(line: str) -> str:
    return re.sub(r"\s+", " ", MARKERS.sub("", line)).strip().lower()


def strip_echo(text: str, source: str) -> str:
    """Drop corpus lines that only repeat the reviewed draft (quoting is not detecting)."""
    known = {normalized(line) for line in source.splitlines() if len(normalized(line)) >= 12}
    return "\n".join(line for line in text.splitlines() if normalized(line) not in known)


def windows(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index in range(len(lines)):
        yield " ".join(lines[index:index + 2])


def detection(defect: dict, text: str) -> str | None:
    """The first window that detects the defect, or None."""
    for window in windows(text):
        if any(re.search(guard, window, re.IGNORECASE) for guard in defect.get("guards", [])):
            continue
        for alternative in defect["detect"]:
            if all(re.search(pattern, window, re.IGNORECASE) for pattern in alternative["all"]):
                return window
    return None


def defect_passes(defect: dict, text: str) -> bool:
    found = detection(defect, text) is not None
    return found if defect["kind"] == "planted" else not found
