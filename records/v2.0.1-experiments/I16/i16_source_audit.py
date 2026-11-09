"""I16 black-box audit: recount source reads per row from the raw tester transcripts, line by line.

Why (deviation recorded in RESULT.md): the registered counter in i16_run.py scans each Codex tool call as one string. Codex
sends its shell commands as JavaScript string literals, where a newline is the two characters backslash-n, so a heredoc
that writes a helper script ("cat > bugbash_out/run.py <<'PY'" followed by lines that invoke oaw/scripts/oaw.py) reads as
one long command that starts with "cat" and names a file under scripts/. The registered count is kept unchanged (its
sha256 is bound to the positive control); this audit is a second, descriptive count for the black-box analysis.

Rules (a tool call counts once at most):
- Shell text is split on real newlines; Codex string literals are unescaped first and every literal is scanned, so
  commands kept in arrays count too. Each line is split into simple commands on | || && ; and &.
- A simple command reads the source when its first word (after env assignments and sudo/env/command/time/xargs/
  timeout/nohup) is a reading verb, it is not "cat > file", and one of its arguments is a file under scripts/, templates/,
  tests/ or vendor/ (in ./oaw or installed into a project). After a cd into such a folder, or with the call's workdir set
  there, a bare *.py or *.sh argument also counts.
- open("<that file>") and Path("<that file>").read_text()/read_bytes() count anywhere, including inside heredoc bodies.
- Claude Read/Grep/Glob calls count as in the registered counter (a path or pattern naming such a file).
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i16_run import READ_TOOLS, SOURCE  # noqa: E402  same file pattern as the registered counter

VERBS = {"cat", "less", "more", "head", "tail", "sed", "awk", "grep", "egrep", "rg", "nl", "bat", "strings", "xxd",
         "od", "diff", "wc", "cp", "tar", "zip"}
PREFIX = re.compile(r"^(?:\w+=\S*\s+|sudo\s+|env\s+|command\s+|time\s+|nohup\s+|timeout\s+\S+\s+|xargs(?:\s+-\S+)*\s+)+")
SPLIT = re.compile(r"\|\||&&|;|\|&?|(?<![>&\d])&(?![>&])")
SRC_DIR = re.compile(r"(?:^|[\s/'\"])(?:scripts|templates|tests|vendor)/?(?:$|[\s'\"])")
OPEN = re.compile(r"open\(\s*[rbuf]*['\"]" + SOURCE + r"|Path\(\s*[rbuf]*['\"]" + SOURCE + r"['\"]\s*\)\s*\.\s*read_")
BARE = re.compile(r"(?<![\w/.-])[\w*.-]+\.(?:py|sh)\b")
JS_STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|`(?:[^`\\]|\\.)*`', re.S)


ESCAPE = re.compile(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", re.S)
SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def unescape(literal):
    """The value of one JavaScript string literal (quotes included)."""
    def one(m):
        e = m.group(1)
        if e[0] in "ux" and len(e) > 1:
            return chr(int(e[1:], 16))
        return SIMPLE.get(e, e)
    return ESCAPE.sub(one, literal[1:-1])


def simple_reads(segment, in_src):
    seg = segment.strip().lstrip("'\"([{,`$").strip()
    seg = PREFIX.sub("", seg)
    words = seg.split()
    if not words or words[0] not in VERBS:
        return False
    if len(words) > 1 and words[1].startswith("="):  # an assignment such as "cp = subprocess.run(...)"
        return False
    if words[0] == "cat" and re.match(r"cat\s*>", seg):
        return False
    rest = seg[len(words[0]):]
    if re.search(SOURCE, rest):
        return True
    return bool(in_src and BARE.search(rest))


def text_reads(text, workdir=""):
    """(reads, matched line) for one shell text."""
    in_src = bool(workdir and SRC_DIR.search(workdir.rstrip("/") + "/"))
    for line in text.split("\n"):
        if OPEN.search(line):
            return True, line.strip()
        for seg in SPLIT.split(line):
            cd = re.match(r"\s*cd\s+(\S+)", seg)
            if cd:
                in_src = bool(SRC_DIR.search(cd.group(1).strip("'\"").rstrip("/") + "/"))
                continue
            if simple_reads(seg, in_src):
                return True, line.strip()
    return False, ""


def codex_call_reads(js):
    literals = [unescape(m.group(0)) for m in JS_STRING.finditer(js)]
    workdirs = [unescape(m.group(1)) for m in re.finditer(r"workdir\s*:\s*(" + JS_STRING.pattern + ")", js, re.S)]
    workdir = workdirs[0] if workdirs else ""
    for literal in literals:
        hit, line = text_reads(literal, workdir)
        if hit:
            return True, line
    return False, ""


def codex_row(rollout_dir):
    hits = []
    for path in sorted(glob.glob(os.path.join(rollout_dir, "**", "*.jsonl"), recursive=True)):
        for line in open(path, encoding="utf-8", errors="replace"):
            try:
                payload = json.loads(line).get("payload") or {}
            except ValueError:
                continue
            kind = payload.get("type")
            if kind == "custom_tool_call":
                hit, text = codex_call_reads(payload.get("input") or "")
            elif kind == "function_call":
                try:
                    args = json.loads(payload.get("arguments") or "{}")
                except ValueError:
                    args = {}
                cmd = args.get("cmd") or args.get("command") or ""
                hit, text = text_reads(" ".join(cmd) if isinstance(cmd, list) else str(cmd), args.get("workdir") or "")
            elif kind == "local_shell_call":
                action = payload.get("action") or {}
                hit, text = text_reads(" ".join(action.get("command") or []), action.get("working_directory") or "")
            else:
                continue
            if hit:
                hits.append(text[:240])
    return hits


def claude_row(events_path):
    hits = []
    for line in open(events_path, encoding="utf-8", errors="replace"):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        for block in (message or {}).get("content") or [] if isinstance(message, dict) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name, data = block.get("name"), block.get("input") or {}
            if name in READ_TOOLS:
                text = " ".join(str(v) for v in data.values())
                if re.search(SOURCE, text):
                    hits.append(f"{name} {text}"[:240])
            elif name == "Bash":
                hit, text = text_reads(str(data.get("command") or ""))
                if hit:
                    hits.append(text[:240])
    return hits


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--run-dirs", required=True, help="comma-separated run folders (each with rows.jsonl and raw/)")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    out = []
    for run_dir in a.run_dirs.split(","):
        for line in open(os.path.join(run_dir, "rows.jsonl"), encoding="utf-8"):
            row = json.loads(line)
            base = os.path.join(run_dir, "raw")
            prefix = f"{row['arm']}-{row['id']}."
            names = [n for n in os.listdir(base) if n.startswith(prefix) and n.endswith(f".a{row.get('attempt', 1)}.jsonl")]
            if any(".r" in n[len(prefix) - 1:] for n in names):
                names = [n for n in names if f".r{row.get('rep', 1)}." in n[len(prefix) - 1:]]
            if len(names) != 1:
                raise SystemExit(f"{run_dir}: cannot find the raw events for {prefix} rep {row.get('rep')}: {names}")
            events = os.path.join(base, names[0])
            if row["cell"] == "codex":
                hits = codex_row(events[:-len(".jsonl")] + "-rollouts")
            else:
                hits = claude_row(events)
            out.append({"cell": row["cell"], "arm": row["arm"], "id": row["id"], "rep": row.get("rep", 1),
                        "registered": row["source_reads"], "audit": len(hits), "hits": hits})
    with open(a.out, "w", encoding="utf-8") as stream:
        for item in out:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    for cell in sorted({o["cell"] for o in out}):
        for arm in "NCDF":
            sel = [o for o in out if o["cell"] == cell and o["arm"] == arm]
            if sel:
                print(f"{cell} {arm}: registered {sum(o['registered'] for o in sel)} in {sum(1 for o in sel if o['registered'])} rows;"
                      f" audit {sum(o['audit'] for o in sel)} in {sum(1 for o in sel if o['audit'])} rows")


if __name__ == "__main__":
    main()
