#!/usr/bin/env python3
"""Create blinded immutable grading inputs without model calls."""
import argparse
from pathlib import Path
import random
import shutil
from bench import HERE, read, sha, tree, write


def make(out, destination):
    out, destination = Path(out), Path(destination)
    if destination.exists():
        raise ValueError("Use a fresh grading packet")
    manifest = read(out / "manifest.json")
    reports = list(manifest["runs"])
    if any(not (out / "reports" / (item["id"] + ".json")).is_file() for item in reports):
        raise ValueError("All planned review reports must exist before grading")
    random.Random(20261031).shuffle(reports)
    mapping = {}
    for index, item in enumerate(reports, 1):
        anon = f"R{index:02}"
        mapping[anon] = item["id"]
        source = out / "reports" / (item["id"] + ".json")
        # Reports are preserved verbatim in the private packet.
        write(destination / item["case"] / "reports" / (anon + ".json"), read(source))
    for case in read(out / "protocol.json")["review_cases"]:
        first = next(item for item in reports if item["case"] == case)
        workspace = Path(first["workspace"])
        for name in first["initial"]:
            if name == "README.md" or name.startswith(("docs/decisions/", "docs/archive/", "src/")) or name == "docs/design.md":
                target = destination / case / "source" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(workspace / name, target)
        write(destination / case / "rubric.json", read(out / "rubric.json")["reviews"][case])
    method_index = []
    for label, source in (("egm", out / "sources/egm"), ("oaw-v1", out / "sources/v1/templates"), ("oaw-v2", out / "sources/v2/templates")):
        for path in sorted(source.rglob("*.md")):
            relative = path.relative_to(source).as_posix()
            # EGM site/contributor files are not assigned method instructions.
            if label == "egm" and not (relative.startswith(("agents/", "skills/", "resources/", "docs/")) or relative in ("README.md", "AGENTS.md", "AI_POLICY.md")):
                continue
            target = destination / "method-reference" / label / (relative + ".txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            method_index.append({"original": label + "/" + relative, "reference": target.relative_to(destination).as_posix(), "sha256": sha(path)})
    required = ["egm/docs/codex.md", "egm/skills/egm-review/SKILL.md", "egm/agents/implementation_readiness.md", "egm/agents/codebase_details.md", "egm/agents/style.md", "egm/agents/synthesizer.md", "egm/resources/document_standards/implementation-readiness-standard.md", "egm/resources/document_standards/re-implementation-standard.md", "oaw-v1/AGENT_RULES.md", "oaw-v1/AGENTS.md", "oaw-v2/AGENTS.md", "oaw-v2/.agents/skills/oaw-evidence/SKILL.md"]
    index_by_name = {row["original"]: row for row in method_index}
    if not set(required).issubset(index_by_name):
        raise ValueError("Missing assigned method sources: " + str(set(required) - set(index_by_name)))
    write(destination / "method-index.json", {"required_sources": required, "files": method_index, "role": "Evidence about supplied methods, not new product requirements"})
    write(destination / "grade-prompt.md", (HERE / "grade-prompt.md").read_text(encoding="utf-8"))
    write(out / "grading-map.json", mapping)
    write(out / "grading-packet-hashes.json", tree(destination))
    print("Prepared all 12 reports with complete method references and no arm mapping")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--packet", required=True)
    args = parser.parse_args()
    make(args.out, args.packet)
