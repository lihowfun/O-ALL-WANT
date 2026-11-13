#!/usr/bin/env python3
"""Print OAW task progress, the current skill digest and the catalog view from project files.

The host-neutral counterpart of the Claude Code `oaw-digest-monitor` mod: any
terminal, Codex included, reads the same `.oaw/progress.json`,
`.oaw/catalog/status.json` and `.oaw/catalog/view.json`. It only reads; a missing
or invalid file is reported, never repaired. A progress percent without a basis
is shown as `?`. The catalog display rules here are the ones the `catalog.py
ui` page and `catalog.py menu` follow: every food is one line on the intake
pipeline that view.json carries (the stage table of docs/SKILL_INTAKE.md), a
verdict always carries its symbol and text, every effect line names its
evidence level, quality is "未量測" without measured evidence, stars appear only
as scout queue order, and imported reports are labelled 歷史證據.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from catalog_core import RELEASE

PROGRESS_FILE = Path(".oaw/progress.json")
STATUS_FILE = Path(".oaw/catalog/status.json")
VIEW_FILE = Path(".oaw/catalog/view.json")
QUESTIONS_FILE = Path(".oaw/catalog/questions.jsonl")
VIEW_SCHEMA = "oaw-catalog-view/3"
# Files build_view() reads; a newer one means view.json may be out of date.
VIEW_SOURCES = ("registry.json", "decisions.jsonl", "builds.json", "policy.json", "scout.json", "effect.json")
STALE_SECONDS = 600
ICONS = {"done": "✅", "in_progress": "⏳", "waiting": "⏸", "todo": "○"}
# status.json stages, named like the intake pipeline stages they belong to.
STAGES = {"ingest": "入口", "quarantine": "封存", "static": "靜態", "goldfish": "盲審", "behavior-ab": "實測", "verdict": "分流"}
VERDICTS = {"evolved": "進化", "parity": "齊平", "regressed": "退步", "pending": "進行中"}
HEADLINES = {"nutritious": "營養", "no-gain": "沒營養", "untested": "未測", "incomplete": "證據不完整", "regressed": "變差",
             "diarrhea": "拉肚子", "risky": "有疑慮", "toxic": "有毒", "inedible": "不能吃"}
LEVELS = {"measured": "實測", "static-measured": "靜態量測", "not-measured": "未量測", "historical-prior": "歷史證據"}
DISPOSITIONS = {"absorb": "🟢 吸收", "excrete": "🔴 排掉", "hold": "🟡 暫留"}
METRICS = {"skills": "skill 數", "files": "檔案數", "bytes": "大小（bytes）",
           "startup-loaded text bytes (codex)": "啟動載入文字 bytes（Codex）",
           "startup-loaded text bytes (claude)": "啟動載入文字 bytes（Claude）", "hooks": "hooks",
           "non-stdlib dependencies": "非標準函式庫相依", "host settings writes": "寫入 host 設定", "quality": "品質"}
BUILD_KINDS = {"baseline": "基準版", "restore-point": "還原點", "absorb": "吸收", "remove": "移除", "restore": "還原", "readd": "加回"}
HOST_NAMES = {"codex": "Codex", "claude": "Claude"}
CHIPS = {"free-checks-passed": "免費檢查通過", "rules-updated-free-T0-pending": "規則已更新，待重跑免費檢查"}
INTEGRITY = {"git-object-verified": "git 物件驗證", "unverified-against-commit": "未對 commit 驗證",
             "sha256-recorded": "已記 sha256（arXiv 沒有可驗證的 hash）"}
REUSE = {"quote-with-attribution": "可引用原文（要附出處）", "ideas-only": "只取想法：重新實作，不複製原文"}
PLAN_STATUS = (("waiting for standing policy", "等你設定常設預算"),
               ("within policy", "第 0/1 階段在常設預算內；第 2 階段和第二個 host 要先問你（v0 尚未開放付費實測）"),
               ("exceeds standing policy", "第 0/1 階段超過常設預算：需要你同意（v0 尚未開放付費實測）"),
               ("taste first", "先試吃：免費靜態檢查決定付費計畫"),
               ("no paid test: owner confirmed toxic", "不需實測：已確認有毒"),
               ("no paid test: oaw cannot digest", "不需實測：OAW 無法消化"),
               ("blocked", "被擋住：你擋下了這樣食物"),
               ("no paid test needed", "不需付費實測：沒有可吸收的成分"),
               ("no components yet", "還沒有成分：論文要由 Elephant 拆成分（規劃中），或匯入已有的消化紀錄"))
# Stage id -> label, for the stage notes on a food card (the full table travels in view.json's pipeline).
STAGE_LABELS = {"intake": "入口", "quarantine": "封存", "static": "靜態", "plan": "計畫", "review": "盲審", "test": "實測",
                "sort": "分流", "approve": "核准", "build": "版本"}
_UNSAFE = re.compile("[\x00-\x1f\x7f-\x9f\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")


def clean(value, limit=120):
    """Food-derived text: no control, bidi or zero-width characters; bounded length."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", _UNSAFE.sub(" ", str(value))).strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def verdict_label(data):
    """A catalog headline wins; an unknown word is shown as unknown, never as in progress."""
    if data.get("headline") is not None:
        return HEADLINES.get(data["headline"]) or f"未知（{clean(data['headline'], 40)}，請更新 OAW）"
    value = data.get("verdict_so_far")
    if value is None:
        return VERDICTS["pending"]
    return VERDICTS.get(value) or f"未知（{clean(value, 40)}，請更新 OAW）"


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
    return {"skill": clean(data.get("skill")), "source": clean(data.get("source")), "stage": stage,
            "stage_label": "完成" if stage == "done" else STAGES.get(stage, clean(stage, 40)),
            "done": progress.get("done"), "total": progress.get("total"), "host": clean(data.get("host")),
            "verdict": verdict_label(data), "stop_reason": clean(data.get("stop_reason"), 160),
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
        stalled = f" · 已停止：{digest['stop_reason']}" if digest["stop_reason"] else " · 可能已中斷" if digest["stalled"] else ""
        # A finished or stopped taste is the latest one, no longer "being digested".
        title = "最近一次試吃" if digest["stage"] == "done" or digest["stop_reason"] else "正在消化"
        lines.append(f"{title}：{digest['skill']} · {digest['stage_label']}{count} · {digest['verdict']}{stalled}")
        if digest["source"]:
            lines.append(f"  來源：{digest['source']}" + (f" · host：{digest['host']}" if digest["host"] else ""))
    return "\n".join(lines)


# --------------------------------------------------------------------------- catalog view (view.json)

def load_view(project):
    """Return (view, note) for .oaw/catalog/view.json; note is None, 'missing' or 'invalid'."""
    try:
        data = json.loads((Path(project) / VIEW_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except (OSError, ValueError):
        return None, "invalid"
    if not isinstance(data, dict) or data.get("schema") != VIEW_SCHEMA or not isinstance(data.get("foods"), list):
        return None, "invalid"
    return data, None


def view_stale(project):
    """True when a catalog source or the install manifest changed after view.json was written."""
    project = Path(project)
    folder = project / ".oaw" / "catalog"
    try:
        built = (project / VIEW_FILE).stat().st_mtime
    except OSError:
        return False
    sources = [folder / name for name in VIEW_SOURCES] + [project / ".oaw" / "install.json"]
    sources += list((folder / "evidence").glob("*/*.json")) + list((folder / "absorbed").glob("*.json"))
    newest = 0.0
    for path in sources:
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return newest > built


def level_label(code):
    return LEVELS.get(code) or f"未知等級（{clean(code, 30)}）"


def headline_label(verdict):
    """Symbol and text together; an unknown word is unknown, never in progress."""
    verdict = verdict if isinstance(verdict, dict) else {}
    code = verdict.get("headline")
    if code in HEADLINES:
        return f"{clean(verdict.get('symbol'), 4) or ''} {HEADLINES[code]}".strip()
    return f"未知（{clean(code, 40)}，請更新 OAW）"


def plan_status_label(text):
    folded = str(text or "").casefold()
    for prefix, label in PLAN_STATUS:
        if folded.startswith(prefix):
            return label
    return clean(text, 120) or "—"


def chip_label(text):
    match = re.fullmatch(r"open-flags:(\d+)", str(text))
    if match:
        return f"{match.group(1)} 個旗標待分流"
    return CHIPS.get(text) or clean(text, 60)


def quality_label(line):
    """'加強' only next to measured evidence; otherwise 未量測."""
    if line.get("level") != "measured":
        return "未量測"
    if line.get("note") == "enhanced":
        return "加強（實測）"
    return f"{clean(line.get('value'), 40)}（實測，未宣稱改善）"


# --------------------------------------------------------------------------- intake pipeline (view.json "pipeline")

def pipeline_table(view):
    """The stage table view.json carries; None for a view without one."""
    table = view.get("pipeline") if isinstance(view, dict) else None
    if not isinstance(table, dict) or not isinstance(table.get("stages"), list):
        return None
    return table


def pipeline_legend(table):
    symbols, names = table.get("symbols") or {}, table.get("states_zh") or {}
    order = [k for k in table.get("legend") or [] if k in symbols] + sorted(set(symbols) - set(table.get("legend") or []))
    return "流程（" + " ".join(f"{clean(symbols.get(k), 2)} {clean(names.get(k), 8)}" for k in order) + "）"


def pipeline_cells(food, table):
    """'入口 ● 封存 ● 靜態 ◉ …' for one food; an unknown state shows ?, never a guess."""
    symbols = table.get("symbols") or {}
    states = ((food.get("pipeline") or {}).get("stages")) or {}
    return " ".join(f"{clean(stage.get('label_zh'), 6)} {clean(symbols.get(states.get(stage.get('id'))), 2) or '?'}"
                    for stage in table["stages"] if isinstance(stage, dict))


def pipeline_line(food, table, width=0):
    pipeline = food.get("pipeline") if isinstance(food.get("pipeline"), dict) else {}
    note = clean(pipeline.get("note_zh"), 120)
    return f"  {clean(food.get('id'), 64):<{width}}  {pipeline_cells(food, table)}" + (f"  {note}" if note else "")


def pipeline_automation_line(table):
    names = table.get("automation_zh") or {}
    groups = {}
    for stage in table["stages"]:
        if isinstance(stage, dict):
            groups.setdefault(stage.get("automation"), []).append(clean(stage.get("label_zh"), 6))
    order = [k for k in table.get("automation_order") or [] if k in groups] + [k for k in groups if k not in (table.get("automation_order") or [])]
    return "  " + " · ".join(f"{clean(names.get(kind), 8) or clean(kind, 12)}：{' '.join(groups[kind])}" for kind in order)


def pipeline_lines(view):
    """The same stage table as the web page: one line per food, from view.json."""
    table = pipeline_table(view)
    if table is None:
        return ["流程：view.json 沒有站別表（請執行 catalog.py view）"]
    foods = [f for f in view.get("foods") or [] if isinstance(f, dict)]
    lines = [pipeline_legend(table), pipeline_automation_line(table)]
    width = min(28, max([len(clean(f.get("id"), 64) or "") for f in foods] or [0]))
    lines += [pipeline_line(food, table, width) for food in foods]
    if not foods:
        lines.append("  " + (clean(table.get("empty_zh"), 200) or "還沒有食物"))
    else:
        lines.append(waiting_line(foods, table))
    return lines


def waiting_line(foods, table):
    """'  等你 1 · 自動（Claude 接手） 3 · 等發布（合併 PR 時一次決定） 1': who the foods wait on (D28), from view.json."""
    names = table.get("waiting_zh") or {}
    order = [k for k in table.get("waiting_order") or [] if isinstance(k, str)]
    counts = {}
    for food in foods:
        waiting = ((food.get("pipeline") or {}).get("waiting_on")) or "unknown"
        counts[waiting] = counts.get(waiting, 0) + 1
    keys = [k for k in order if counts.get(k)] + sorted(k for k in counts if k not in order)
    return "  " + " · ".join(f"{clean(names.get(k), 30) or '未知（' + clean(k, 20) + '）'} {counts[k]}" for k in keys)


def stage_actions(view):
    """(food, action) pairs for every food's current stage, in view order: the menu's lettered choices."""
    pairs = []
    for food in view.get("foods") or []:
        if isinstance(food, dict):
            for action in ((food.get("pipeline") or {}).get("actions")) or []:
                if isinstance(action, dict):
                    pairs.append((food, action))
    return pairs


def safety_label(food):
    verdict = (food.get("verdict") or {}).get("headline")
    flags = food.get("flags") if isinstance(food.get("flags"), dict) else {}
    if verdict == "toxic":
        return "經人工確認有毒"
    if not food.get("tasted"):
        return "尚未檢查"
    if flags.get("open"):
        return f"{flags['open']} 個旗標未分流（高 {flags.get('open_high', 0)}）"
    if food.get("kind") == "paper":
        pdf = clean((food.get("pinned") or {}).get("pdf_sha12"), 12)
        return "論文：只封存 PDF，不解析、不執行" + (f"（sha256 {pdf}）" if pdf else "")
    tree = clean((food.get("pinned") or {}).get("tree_sha12"), 12)
    return f"沒有觀察到有毒訊號（tree {tree}）" if tree else "沒有觀察到有毒訊號"


def installed_skills(view):
    """(name, tag) rows; tag is '', '新增' or '比預設少'.

    A fresh static effect is the source. When it is stale (the layer changed after
    it was computed), the current build's recorded skills are used instead, and
    compared with the default recipe the effect names (same + removed).
    """
    my = view.get("my_oaw") or {}
    effect = my.get("effect") if isinstance(my.get("effect"), dict) else {}
    skills = effect.get("skills") if isinstance(effect.get("skills"), dict) else None
    timeline = my.get("timeline") if isinstance(my.get("timeline"), list) else []
    current = next((b for b in timeline if isinstance(b, dict) and b.get("current")), None)
    if skills is not None and not effect.get("stale"):
        present = list(skills.get("same", [])) + list(skills.get("added", []))
        default = list(skills.get("same", [])) + list(skills.get("removed", []))
    elif current is not None and my.get("current_matches_build") is not False:
        present = list(current.get("skills") or [])
        default = list(skills.get("same", [])) + list(skills.get("removed", [])) if skills is not None else None
    elif skills is not None:
        present = list(skills.get("same", [])) + list(skills.get("added", []))
        default = list(skills.get("same", [])) + list(skills.get("removed", []))
    else:
        return None
    if default is None:
        return sorted((clean(name, 64), "") for name in set(present))
    rows = [(clean(name, 64), "" if name in default else "新增") for name in set(present)]
    rows += [(clean(name, 64), "比預設少") for name in set(default) - set(present)]
    return sorted(rows, key=lambda row: (row[1] == "比預設少", row[0]))


def count_text(value):
    """A count, or — when the record has no such list (missing data is not 0)."""
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else "—"


def effect_line_text(line):
    if line.get("metric") == "quality":
        return f"品質：{quality_label(line)} [{level_label(line.get('level'))}]"
    delta = line.get("delta")
    change = f"（{delta:+d}）" if isinstance(delta, int) and not isinstance(delta, bool) else ""
    return (f"{METRICS.get(line.get('metric')) or clean(line.get('metric'), 60)}："
            f"{count_text(line.get('current'))} 對 {count_text(line.get('default'))}{change} [{level_label(line.get('level'))}]")


def effect_lines(effect, release=RELEASE):
    if not isinstance(effect, dict) or not isinstance(effect.get("lines"), list):
        return ["  和預設比：尚未評估（catalog.py effect）"]
    lines = [f"  和預設 {clean(effect.get('release') or release, 20)} 比" + ("（過期，請重新評估）" if effect.get("stale") else "") + "："]
    lines += ["    " + effect_line_text(line) for line in effect["lines"] if isinstance(line, dict)]
    return lines


def build_label(build):
    return clean(build.get("label_zh") or build.get("label"), 120)


def timeline_lines(timeline, detail=True):
    """Each build with its skills, absorbed components and effect versus the default, every line with its level (D12)."""
    lines = []
    for build in reversed([b for b in timeline or [] if isinstance(b, dict)]):
        mark = "★ 目前" if build.get("current") else "  還原到這版：catalog.py restore " + clean(build.get("name"), 60)
        lines.append(f"  {clean(build.get('name'), 60)} · {BUILD_KINDS.get(build.get('kind')) or clean(build.get('kind'), 20)}"
                     f" · {build_label(build)} · {clean(build.get('created_at'), 25)}")
        if detail:
            skills = [clean(s, 64) for s in build.get("skills") or []]
            lines.append(f"      skill（{len(skills)}）：" + ("、".join(skills) or "（沒有）"))
            components = [clean(c, 120) for c in build.get("components") or []]
            lines.append("      吸收的成分：" + ("、".join(components) or "（沒有）"))
            effect = build.get("effect") if isinstance(build.get("effect"), dict) else None
            if effect and isinstance(effect.get("lines"), list):
                lines.append("      和預設比：" + " · ".join(effect_line_text(line) for line in effect["lines"] if isinstance(line, dict)))
            else:
                lines.append("      和預設比：這一版沒有評估紀錄")
        lines.append(f"      {mark}")
    return lines or ["  還沒有版本：第一次吸收或移除時，會先存一個基準版"]


def host_note(view, name):
    """'（只在 Codex）' when an absorbed skill is installed on only some of the install's hosts."""
    effect = ((view.get("my_oaw") or {}).get("effect")) or {}
    only = ((effect.get("skills") or {}).get("only_on") or {}).get(name)
    if only is None or effect.get("stale"):
        return ""
    return "（只在 " + "、".join(HOST_NAMES.get(h, clean(h, 20)) for h in only) + "）" if only else "（沒有裝到任何 host）"


def my_oaw_lines(view):
    my = view.get("my_oaw") or {}
    timeline = my.get("timeline") if isinstance(my.get("timeline"), list) else []
    current = next((b for b in timeline if isinstance(b, dict) and b.get("current")), None)
    name = clean(my.get("current_build"), 60)
    if name:
        lines = [f"我的 OAW：{name}" + (f"「{build_label(current)}」" if current else "")]
    else:
        lines = [f"我的 OAW：預設 {clean(view.get('release'), 20)}（尚未建立版本）"]
    if name and my.get("current_matches_build") is False:
        lines.append("  ⚠ 目前的安裝和記錄的版本不同（在 catalog 之外被改過）")
    rows = installed_skills(view)
    if rows is None:
        lines.append("  skill：尚未評估（catalog.py effect）")
    else:
        lines.append("  skill：" + (", ".join(name + (f"（{tag}）" if tag else "") + host_note(view, name) for name, tag in rows) or "（沒有）"))
    lines += effect_lines(my.get("effect"), view.get("release") or RELEASE)
    lines.append("  版本時間線：")
    lines += timeline_lines(timeline)
    return lines


def part_state(part):
    """Owner decision and whether the part is in the current build (a restore can remove it)."""
    if part.get("in_current_build"):
        # D6: a removed part a restore brought back was not tested again.
        return "在目前版本中（移除後又還原回來：要重新測試）" if part.get("decision") == "removed" else "在目前版本中"
    decision = part.get("decision")
    if decision == "absorbed":
        return "已吸收（不在目前版本）"
    return {"excreted": "已排掉", "removed": "已移除", "absorbed as backlog item": "已記成待辦（未改程式）"}.get(decision) or clean(decision, 40) or ""


def part_reason(part):
    return clean(part.get("reason_zh") or part.get("reason"), 200)


def part_missing(part):
    return clean(part.get("missing_zh") or part.get("missing_test"), 120)


def pin_text(food):
    """A repository's commit, or a paper's arXiv version plus the sha256 of its sealed PDF."""
    pinned = food.get("pinned") or {}
    if food.get("kind") != "paper":
        return clean(pinned.get("commit7"), 12) or "未固定"
    if not pinned.get("pdf_sha12"):
        return "論文 · 未固定"
    version = f"arXiv {clean(pinned.get('version'), 8)}" if pinned.get("version") else "本機 PDF"
    return f"論文 {version} · sha256 {clean(pinned.get('pdf_sha12'), 12)}"


def paper_lines(paper):
    """Title, authors, version and license of a paper card (from the taste, or as an imported record states them)."""
    if not isinstance(paper, dict):
        return []
    authors = [clean(a, 80) for a in paper.get("authors") or [] if isinstance(a, str)]
    total = paper.get("authors_total") if isinstance(paper.get("authors_total"), int) else len(authors)
    version = clean(paper.get("version"), 8) or "沒有版本（本機 PDF）"
    if paper.get("version_date"):
        version += f"（{clean(paper.get('version_date'), 20)}）"
    reuse = REUSE.get(paper.get("reuse"))
    imported = "（匯入的紀錄寫的，歷史證據）" if paper.get("from") == "imported" else ""
    return [f"  論文：{clean(paper.get('title'), 160) or '（沒有標題）'}{imported}",
            f"    作者：{'、'.join(authors) or '未記錄'}" + (f"（共 {total} 位）" if total > len(authors) else "")
            + f" · 版本 {version} · 授權 {clean(paper.get('license'), 60) or '不明'}" + (f"：{reuse}" if reuse else "")]


def food_lines(food, detail=False):
    verdict = food.get("verdict") or {}
    pinned = food.get("pinned") or {}
    counts = food.get("counts") or {}
    historical = food.get("historical") if isinstance(food.get("historical"), list) else []
    pipeline = food.get("pipeline") if isinstance(food.get("pipeline"), dict) else {}
    parity = clean((pipeline.get("parity") or {}).get("label_zh"), 60)
    lines = [f"{headline_label(verdict)} · {clean(food.get('display'), 80)} [{clean(food.get('id'), 64)}]"
             f" · {pin_text(food)} · {INTEGRITY.get(pinned.get('integrity')) or '未試吃'}"
             f" · 證據：{level_label(verdict.get('level'))}",
             f"  這一站：{clean(pipeline.get('stage_label_zh'), 8) or '?'}（{clean(pipeline.get('state_zh'), 8) or '?'}）"
             f" · {clean(pipeline.get('note_zh'), 160) or '—'}",
             "  成分：" + " · ".join(f"{DISPOSITIONS[k]} {counts.get(k, 0)}" for k in DISPOSITIONS)
             + (f" · 歷史證據 {len(historical)} 份（不計入判定）" if historical else ""),
             f"  安全：{safety_label(food)}",
             f"  實測：{plan_status_label((food.get('plan') or {}).get('status'))}" + (f" · {parity}" if parity else "")]
    # What a recorded tasting or D21 absorption says at its stop (D28), in stage order.
    notes = pipeline.get("stage_notes_zh") if isinstance(pipeline.get("stage_notes_zh"), dict) else {}
    for sid in [k for k in STAGE_LABELS if k in notes] + sorted(k for k in notes if k not in STAGE_LABELS):
        if isinstance(notes[sid], str) and notes[sid]:
            lines.append(f"  {STAGE_LABELS.get(sid) or clean(sid, 20)}站：{clean(notes[sid], 200)}")
    if not detail:
        return lines
    lines += paper_lines(food.get("paper"))
    lines += blocker_lines(pipeline)
    if food.get("components_note_zh"):
        lines.append(f"  成分：{clean(food.get('components_note_zh'), 200)}")
    reasons = verdict.get("reasons_zh") or verdict.get("reasons") or []
    if reasons:
        lines.append("  判定依據：" + "；".join(clean(r, 160) for r in reasons))
    chips = [chip_label(c) for c in verdict.get("chips") or []]
    if chips:
        lines.append("  標示：" + "、".join(chips))
    if food.get("allergens"):
        lines.append("  過敏原：" + "、".join(clean(a, 40) for a in food["allergens"]))
    for key in DISPOSITIONS:
        parts = [c for c in food.get("components") or [] if isinstance(c, dict) and c.get("disposition") == key]
        for part in parts:
            lines.append(f"  {DISPOSITIONS[key]} {clean(part.get('id'), 80)} · {clean(part.get('kind'), 20)} · {clean(part.get('exec_class'), 10)}"
                         + f" · {level_label(part.get('level'))}"
                         + (f" · {part_state(part)}" if part_state(part) else ""))
            lines.append(f"      {part_reason(part)}" + (f" · 缺：{part_missing(part)}" if part_missing(part) else ""))
    flags = [f for f in food.get("flag_list") or [] if isinstance(f, dict)]
    open_flags = [f for f in flags if f.get("triage") not in ("benign", "allergen")]
    for flag in open_flags[:12]:
        triage = {"confirm-toxic": " · 你確認有毒"}.get(flag.get("triage"), "")
        lines.append(f"  旗標 [{clean(flag.get('severity'), 8)}] {clean(flag.get('rule'), 16)} {clean(flag.get('path'), 80)}:{flag.get('line')}"
                     f" · {clean(flag.get('meaning_zh') or flag.get('meaning'), 80)}{triage}")
    if (food.get("flags") or {}).get("open"):
        lines.append("  分流：catalog.py menu → 12 分流旗標（良性、過敏原或確認有毒）")
    if isinstance(food.get("last_error"), dict):
        error = food["last_error"]
        lines.append(f"  上次試吃失敗：{clean(error.get('error_zh') or error.get('error'), 160)}")
    for report in historical:
        lines.append(f"  歷史證據（不計入判定）：{clean(report.get('evidence_id'), 80)}")
        elephant = report.get("elephant") if isinstance(report.get("elephant"), dict) else None
        if elephant:
            lines.append(f"    🐘 Elephant：整合方式 {clean(elephant.get('integration_mode'), 40)} · 關口 {len(elephant.get('gates') or [])}"
                         f" · 養分／拉肚子風險／提議的 A/B {count_text(elephant.get('nutrients'))}／{count_text(elephant.get('diarrhea_risks'))}"
                         f"／{count_text(elephant.get('proposed_ab_tests'))}")
        verify = report.get("verify") if isinstance(report.get("verify"), dict) else None
        if verify:
            lines.append(f"    查證 {count_text(verify.get('checks'))} 項 · 漏掉 {count_text(verify.get('missed_issues'))}")
        for fish in report.get("goldfish") or []:
            severity = "、".join(f"{clean(k, 20)} {v}" for k, v in (fish.get("by_severity") or {}).items())
            lines.append(f"    🐟 Goldfish {clean(fish.get('reviewer'), 40)}：{fish.get('findings')} 項發現" + (f"（{severity}）" if severity else ""))
        for review in report.get("reviews") or []:
            if isinstance(review, dict):
                lines.append(f"    其他審查 {clean(review.get('reviewer'), 40)}：{review.get('findings')} 項發現")
        paper = report.get("paper") if isinstance(report.get("paper"), dict) else None
        if paper:
            lines.append(f"    論文（紀錄裡寫的）：{clean(paper.get('title'), 120) or '—'} · {clean(paper.get('version'), 8) or '沒有版本'}"
                         f" · 授權 {clean(paper.get('license'), 40) or '不明'}")
        for part in report.get("components") or []:
            if isinstance(part, dict):
                lines.append(f"    {DISPOSITIONS.get(part.get('disposition'), '🟡 暫留')} {clean(part.get('id'), 80)} · {clean(part.get('name'), 80)}"
                             + (f" · {part_state(part)}" if part_state(part) else ""))
    return lines


def blocker_lines(pipeline):
    """The page's blocker explanation as terminal lines (view.json pipeline.blocker); nothing when absent."""
    blocker = pipeline.get("blocker") if isinstance(pipeline.get("blocker"), dict) else None
    if not blocker:
        return []
    lines = [f"  卡在哪：{clean(blocker.get('where_zh'), 200) or '—'}" + (f" · {clean(pipeline.get('waiting_zh'), 30)}" if pipeline.get("waiting_zh") else "")]
    basis = [clean(b, 200) for b in blocker.get("basis_zh") or [] if b]
    if basis:
        lines.append("  依據：" + "；".join(basis))
    if blocker.get("if_ignored_zh"):
        lines.append(f"  你不處理會怎樣：{clean(blocker.get('if_ignored_zh'), 200)}")
    unknown = [clean(u, 200) for u in blocker.get("unknown_zh") or [] if u]
    if unknown:
        lines.append("  紀錄沒寫的：" + "；".join(unknown))
    return lines


def open_questions(project):
    """How many questions the owner recorded on the page are still unanswered (0 without the file)."""
    try:
        text = (Path(project) / QUESTIONS_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return 0
    count = 0
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and isinstance(record.get("question"), str) and record.get("status") != "answered":
            count += 1
    return count


def scout_lines(view, limit=None):
    scout = ((view.get("feeding") or {}).get("scout")) or {}
    candidates = [c for c in scout.get("candidates") or [] if isinstance(c, dict)]
    last = scout.get("last_run") if isinstance(scout.get("last_run"), dict) else None
    lines = [f"每週偵查：候選 {len(candidates)} · 已自動濾掉 {scout.get('dropped_without_review', 0)} 個無關 repo（不經審查）"
             + (f" · 上次 {clean(last.get('week'), 10)}" if last else " · 還沒偵查過")]
    for item in candidates[:limit] if limit else candidates:
        status = "已送去" if item.get("status") == "picked" else "候選"
        lines.append(f"  {item.get('rank')}. {clean(item.get('display'), 60)} · ★{item.get('stars') or 0}（排隊依據，非品質） · {status}")
        if item.get("description"):
            lines.append(f"      {clean(item.get('description'), 120)}")
    return lines


def catalog_lines(view, stale=False):
    funnel = view.get("funnel") or {}
    lines = ["視圖可能過期：請執行 catalog.py view"] if stale else []
    lines += my_oaw_lines(view)
    lines.append(f"食物 {funnel.get('submitted', 0)} · 已試吃 {funnel.get('tasted', 0)} · 實測 {funnel.get('measured', 0)}"
                 f" · 已吸收成分 {funnel.get('absorbed_parts', 0)}" + (f" · 待辦 {funnel['backlog_items']}" if funnel.get("backlog_items") else ""))
    lines += pipeline_lines(view)
    foods = [f for f in view.get("foods") or [] if isinstance(f, dict)]
    for food in foods:
        lines += food_lines(food)
    if not foods:
        lines.append("  操作：catalog.py ui（網頁）或 catalog.py menu（終端選單）")
    lines += scout_lines(view, limit=5)
    return lines


def catalog_summary(view, stale=False):
    my = view.get("my_oaw") or {}
    return {"current_build": my.get("current_build"), "stale": stale, "funnel": view.get("funnel"),
            "quality": quality_label(((my.get("effect") or {}).get("quality")) or {}),
            "foods": [{"id": f.get("id"), "headline": (f.get("verdict") or {}).get("headline"),
                       "label": headline_label(f.get("verdict")), "stage": (f.get("pipeline") or {}).get("stage"),
                       "stages": (f.get("pipeline") or {}).get("stages")}
                      for f in view.get("foods") or [] if isinstance(f, dict)]}


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
    view, view_note = load_view(project)
    stale = view_stale(project) if view else False
    questions = open_questions(project)
    if args.json:
        print(json.dumps({"project": str(project), "progress": progress, "progress_note": progress_note,
                          "digest": digest, "digest_note": digest_note,
                          "catalog": catalog_summary(view, stale) if view else None, "catalog_note": view_note,
                          "open_questions": questions},
                         ensure_ascii=False, indent=2))
    else:
        text = render(project, progress, progress_note, digest, digest_note)
        if view:
            text += "\n\n" + "\n".join(catalog_lines(view, stale))
        elif view_note == "invalid":
            text += "\n\n消化目錄：view.json 無效（請執行 catalog.py view）"
        if questions:
            text += f"\n\n你在網頁上問的問題：{questions} 個還沒回答（catalog.py questions 列出；Claude 在對話裡回答）"
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
