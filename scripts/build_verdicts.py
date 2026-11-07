#!/usr/bin/env python3
"""Build catalog/verdicts.json, the tasting results OAW ships to users, from a tasting ledger.

The ledger is a project directory whose `.oaw/catalog/` holds the maintainer's catalog.py records
(registry and `record-tasting` results). It is only read. Only public GitHub foods are written; a local
food, a private reference or anything that looks like a local path refuses the build instead of shipping.

    python3 scripts/build_verdicts.py --ledger DIR            # print the file
    python3 scripts/build_verdicts.py --ledger DIR --write    # write catalog/verdicts.json
    python3 scripts/build_verdicts.py --ledger DIR --check    # exit 1 when the shipped file differs
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import catalog_core as core  # noqa: E402

ROOT = SCRIPTS.parent
OUTPUT = ROOT / "catalog" / "verdicts.json"
SCHEMA = "oaw-verdicts/1"
# Categories group foods that do the same job, so a user install can point out a structural overlap
# for free (two code maps). Plan 2.0.1, appendix A, "目前的分類和題庫".
CATEGORIES = {"code-map": "程式碼地圖", "review": "審查、批判", "token-saving": "省 token", "memory": "記憶"}
FOOD_CATEGORIES = {
    "github.com/colbymchenry/codegraph": "code-map",
    "github.com/graphify-labs/graphify": "code-map",
    "github.com/alexyc9381/court-skill": "review",
    "github.com/microsoft/tokeneconomizer": "token-saving",
    "github.com/thedotmack/claude-mem": "memory",
}
# OAW's own skills that do one of those jobs. A user skill of the same category overlaps them.
BUILTIN_CATEGORIES = {"oaw-codemap": "code-map", "oaw-review": "review"}
_PRIVATE = re.compile(r"(?i)(?:file://|private#|(?<![\w.])/(?:home|mnt|users|root|tmp|var|private|opt|srv)/|\b[a-z]:\\)")


class BuildError(Exception):
    """The ledger cannot produce a public-safe verdicts file."""


def _public(value, where: str):
    """Refuse any string that looks like a local path or private reference; return the value unchanged."""
    if isinstance(value, str) and _PRIVATE.search(value):
        raise BuildError(f"Not public-safe ({where}): {core.sanitize_text(value, 80)!r}")
    if isinstance(value, dict):
        for key, item in value.items():
            _public(item, f"{where}.{key}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _public(item, f"{where}[{index}]")
    return value


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise BuildError(f"Cannot read {path.name}: {exc}") from exc


def tasting_entry(record: dict) -> dict:
    """The latest valid tasting as users see it: outcome, label, the conditions it ran under and its evidence."""
    judgment = record.get("judgment") or {}
    protocol = record["protocol"]
    food_arm = next((arm for arm in record["arms"] if arm.get("food_arm")), {})
    label = core.d29_label(judgment) or core.TASTING_VERDICTS[record["verdict"]]
    return {
        "date": record["date"], "tasting_id": record.get("tasting_id"), "verdict": record["verdict"],
        "outcome": judgment.get("outcome"), "outcome_zh": core.D29_OUTCOMES_ZH.get(judgment.get("outcome")),
        "label_zh": label, "quality": judgment.get("quality"), "quality_class": judgment.get("quality_class"),
        "cost_ratio": judgment.get("cost_ratio"), "cost_ci": judgment.get("cost_ci"), "grading": judgment.get("grading"),
        "conditions_count": judgment.get("conditions"), "basis": judgment.get("basis"), "reason_zh": record["verdict_zh"],
        "conditions": {"corpus": protocol["corpus"], "models": list(protocol["models"]),
                       "questions": protocol["questions"]["count"], "repeats": protocol["repeats"],
                       "grading": protocol.get("grading"), "host": protocol.get("host"),
                       "food_arm": food_arm.get("label") or record.get("food_arm")},
        "evidence": {"branch": record["records"]["branch"], "commit": record["records"]["commit"], "path": record["records"]["path"]},
    }


def build(ledger: Path) -> dict:
    """The verdicts document for a ledger directory; deterministic for the same records."""
    catalog = Path(ledger) / ".oaw" / "catalog"
    registry = _load(catalog / "registry.json")
    if not isinstance(registry, dict) or not isinstance(registry.get("foods"), dict):
        raise BuildError("No catalog registry in the ledger (.oaw/catalog/registry.json).")
    foods = []
    for fid, entry in sorted(registry["foods"].items()):
        source = entry.get("source") or {}
        if source.get("kind") != "github" or not str(source.get("key", "")).startswith("github.com/"):
            continue  # papers are not installable; local foods are private
        evidence = []
        folder = catalog / "evidence" / core.slug(fid)
        if folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                value = _load(path)
                if isinstance(value, dict):
                    evidence.append(value)
        records = core.food_records(evidence, fid)
        tasting = tasting_entry(records["tastings"][-1]) if records["tastings"] else None
        owner, repo = source["owner"], source["repo"]
        foods.append(_public({
            "id": fid, "repo": f"{owner}/{repo}", "key": source["key"], "url": f"https://github.com/{owner}/{repo}",
            "commit": source.get("commit"), "category": FOOD_CATEGORIES.get(source["key"]), "tasting": tasting,
        }, fid))
    return {
        "schema": SCHEMA,
        "about": ("Tasting results from OAW's ledger, shipped so a user install can show them. A result holds only for "
                  "the conditions it lists; no record means 未試吃. Generated by scripts/build_verdicts.py; do not edit by hand."),
        "categories": CATEGORIES,
        "builtin": {name: {"category": category} for name, category in sorted(BUILTIN_CATEGORIES.items())},
        "foods": foods,
    }


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", required=True, help="project directory holding the tasting ledger (.oaw/catalog)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write catalog/verdicts.json")
    mode.add_argument("--check", action="store_true", help="exit 1 when catalog/verdicts.json differs from the ledger")
    args = parser.parse_args(argv)
    try:
        data = render(build(Path(args.ledger)))
    except BuildError as exc:
        print(f"verdicts error: {exc}", file=sys.stderr)
        return 2
    if args.check:
        current = OUTPUT.read_bytes() if OUTPUT.is_file() else b""
        print("verdicts: up to date" if current == data else "verdicts: catalog/verdicts.json differs from the ledger")
        return 0 if current == data else 1
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(data)
        print(f"wrote {OUTPUT.relative_to(ROOT).as_posix()}")
        return 0
    sys.stdout.write(data.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
