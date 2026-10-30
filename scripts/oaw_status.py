#!/usr/bin/env python3
"""Print OAW task progress and the current skill digest from project files.

The host-neutral counterpart of the Claude Code `oaw-digest-monitor` mod: any
terminal, Codex included, reads the same `.oaw/progress.json` and
`.oaw/catalog/status.json`. It only reads; a missing or invalid file is reported,
never repaired. A progress percent without a basis is shown as `?`.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

PROGRESS_FILE = Path(".oaw/progress.json")
STATUS_FILE = Path(".oaw/catalog/status.json")
STALE_SECONDS = 600
ICONS = {"done": "✅", "in_progress": "⏳", "waiting": "⏸", "todo": "○"}
STAGES = {"ingest": "攝取", "static": "靜態", "goldfish": "金魚", "behavior-ab": "A/B", "verdict": "判定"}
VERDICTS = {"evolved": "進化", "parity": "齊平", "regressed": "退步", "pending": "進行中"}


def load(path):
    """Return (data, note); note is None, 'missing' or 'invalid'."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except (OSError, ValueError):
        return None, "invalid"
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return None, "invalid"
    return data, None


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def progress_summary(data):
    items = []
    for item in data.get("items") if isinstance(data.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        percent, basis = item.get("percent"), str(item.get("basis") or "").strip()
        known = isinstance(percent, int) and not isinstance(percent, bool) and 0 <= percent <= 100 and basis
        status = item.get("status") if item.get("status") in ICONS else "todo"
        items.append({"id": item.get("id"), "title": str(item.get("title") or item.get("id") or "?"),
                      "status": status, "percent": percent if known else None, "basis": basis})
    return {"title": str(data.get("title") or "交辦進度"), "items": items,
            "done": sum(item["status"] == "done" for item in items),
            "waiting": sum(item["status"] == "waiting" for item in items), "total": len(items)}


def digest_summary(data, now=None):
    now = now or datetime.now(timezone.utc)
    updated = _timestamp(data.get("updated_at"))
    progress = data.get("progress") if isinstance(data.get("progress"), dict) else {}
    stage = data.get("stage")
    return {"skill": data.get("skill"), "source": data.get("source"), "stage": stage,
            "stage_label": "完成" if stage == "done" else STAGES.get(stage, str(stage)),
            "done": progress.get("done"), "total": progress.get("total"), "host": data.get("host"),
            "verdict": VERDICTS.get(data.get("verdict_so_far"), "進行中"),
            "stalled": stage != "done" and (updated is None or (now - updated).total_seconds() > STALE_SECONDS)}


def render(project, progress, progress_note, digest, digest_note):
    lines = [f"讀取：{project}", ""]
    if progress is None:
        lines.append(f"交辦進度：沒有進度檔（{progress_note}）：{PROGRESS_FILE.as_posix()}")
    else:
        waiting = f" · 等你 {progress['waiting']}" if progress["waiting"] else ""
        lines.append(f"{progress['title']}：完成 {progress['done']}/{progress['total']}{waiting}")
        for item in progress["items"]:
            if item["percent"] is None:
                bar, percent = "?" * 10, "  ?"
            else:
                filled = round(item["percent"] / 10)
                bar, percent = "█" * filled + "░" * (10 - filled), f"{item['percent']:>3}"
            lines.append(f"  {ICONS[item['status']]} {bar} {percent}%  {item['title']}")
            if item["basis"]:
                lines.append(f"       {item['basis']}")
    lines.append("")
    if digest is None:
        lines.append("正在消化：沒有進行中的消化" + ("" if digest_note == "missing" else "（狀態檔無效）"))
    else:
        count = f" {digest['done']}/{digest['total']}" if digest["total"] else ""
        stalled = " · 可能已中斷" if digest["stalled"] else ""
        lines.append(f"正在消化：{digest['skill']} · {digest['stage_label']}{count} · {digest['verdict']}{stalled}")
        if digest["source"]:
            lines.append(f"  來源：{digest['source']}" + (f" · host：{digest['host']}" if digest["host"] else ""))
    return "\n".join(lines)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="project directory holding .oaw/ (default: current directory)")
    parser.add_argument("--json", action="store_true", help="print a machine-readable summary")
    args = parser.parse_args(argv)
    project = Path(args.project).resolve()
    raw_progress, progress_note = load(project / PROGRESS_FILE)
    raw_digest, digest_note = load(project / STATUS_FILE)
    progress = progress_summary(raw_progress) if raw_progress else None
    digest = digest_summary(raw_digest) if raw_digest else None
    if args.json:
        print(json.dumps({"project": str(project), "progress": progress, "progress_note": progress_note,
                          "digest": digest, "digest_note": digest_note}, ensure_ascii=False, indent=2))
    else:
        print(render(project, progress, progress_note, digest, digest_note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
