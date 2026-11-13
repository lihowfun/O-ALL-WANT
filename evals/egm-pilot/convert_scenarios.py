#!/usr/bin/env python3
"""Convert EGM's test_scenarios.yaml files into the pilot's scenarios.json.

The upstream checkout is untrusted data: this script only reads files (it never
imports or runs anything from it, and it resolves the pinned commit by reading
.git/HEAD and refs as text). Run it with ``python -I -X utf8``.

Only the YAML subset that EGM actually uses is accepted: block mappings and
sequences, double/single-quoted scalars, simple plain scalars, and ``&anchor`` /
``*alias`` on whole sequence items. Anything else (flow collections, block
scalars, tags, merge keys, multi-line scalars, unknown keys or assertion types)
fails loudly instead of being guessed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
UPSTREAM_REPOSITORY = "https://github.com/google/elephant-goldfish-model"
UPSTREAM_COMMIT = "f0ba151b252c9abf1318d9fe857a43265d06de89"
EXPECTED_SCENARIOS = 30
MAX_SOURCE_BYTES = 200_000

ASSERTION_TYPES = {"required_pattern": "regex", "forbidden_pattern": "regex",
                   "contains": "literal", "not_contains": "literal"}
EVAL_TYPES = ("deterministic",)
TOP_KEYS = ("skill", "description", "scenarios")
SCENARIO_KEYS = ("scenario_id", "description", "eval_type", "system_prompt", "turns")
TURN_KEYS = ("user_input", "assertions")
MODIFICATIONS = [
    "YAML converted to JSON; YAML comments (the upstream license header) dropped.",
    "YAML anchors/aliases expanded into explicit copies.",
    "Each scenario gains case_id '<skill>/<scenario_id>' and each assertion an id 't<turn>a<index>'.",
    "system_prompt.skill_file flattened to skill_file.",
    "Assertion semantics made explicit (assertion_semantics); upstream has no in-repo runner.",
]
SEMANTICS = {
    "required_pattern": "Python re.search(pattern, text) must find a match; case-sensitive unless the pattern sets (?i).",
    "forbidden_pattern": "Python re.search(pattern, text) must find no match.",
    "contains": "the literal operand must occur in text (case-sensitive).",
    "not_contains": "the literal operand must not occur in text.",
    "operand": "the 'pattern' or 'value' key, whichever the upstream assertion uses.",
    "text": "the response of the turn the assertion belongs to (see spec.json scoring.protocol_corpus).",
}

KEY = re.compile(r"([A-Za-z_][A-Za-z0-9_]*):(?:[ ]+(.*))?$")
NAME = re.compile(r"[A-Za-z0-9_-]+")
PLAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-/ ]*")
AMBIGUOUS = re.compile(r"(?i)(true|false|yes|no|on|off|null|~|[-+]?(\d[\d_]*)?(\.\d+)?([eE][-+]?\d+)?)")
ESCAPES = {"\\": "\\", '"': '"', "/": "/", "n": "\n", "t": "\t"}


class ScenarioError(ValueError):
    """The upstream file uses a construct or value this converter does not understand."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scalar(text: str, where: str) -> str:
    if text.startswith('"'):
        out, index = [], 1
        while index < len(text):
            char = text[index]
            if char == "\\":
                following = text[index + 1:index + 2]
                if following not in ESCAPES:
                    raise ScenarioError(f"{where}: unsupported escape \\{following}")
                out.append(ESCAPES[following])
                index += 2
                continue
            if char == '"':
                if text[index + 1:].strip():
                    raise ScenarioError(f"{where}: unexpected text after a closing quote")
                return "".join(out)
            out.append(char)
            index += 1
        raise ScenarioError(f"{where}: unterminated double-quoted scalar (multi-line scalars are not supported)")
    if text.startswith("'"):
        out, index = [], 1
        while index < len(text):
            if text[index] == "'":
                if text[index + 1:index + 2] == "'":
                    out.append("'")
                    index += 2
                    continue
                if text[index + 1:].strip():
                    raise ScenarioError(f"{where}: unexpected text after a closing quote")
                return "".join(out)
            out.append(text[index])
            index += 1
        raise ScenarioError(f"{where}: unterminated single-quoted scalar")
    if text[:1] in set("&*!|>%@`{}[],#?:-") or " #" in text or ": " in text:
        raise ScenarioError(f"{where}: unsupported YAML construct {text[:40]!r}")
    if not PLAIN.fullmatch(text) or AMBIGUOUS.fullmatch(text):
        raise ScenarioError(f"{where}: ambiguous plain scalar {text[:40]!r}; quote it")
    return text.rstrip()


class Parser:
    def __init__(self, text: str, label: str):
        self.label = label
        self.anchors: dict[str, object] = {}
        self.lines = []
        if "\t" in text:
            raise ScenarioError(f"{label}: tab characters are not supported")
        for number, raw in enumerate(text.split("\n"), 1):
            raw = raw.rstrip("\r").rstrip(" ")
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if raw.startswith(("---", "...", "%")):
                raise ScenarioError(f"{label}:{number}: document markers and directives are not supported")
            self.lines.append((number, len(raw) - len(raw.lstrip(" ")), stripped))

    def where(self, index: int) -> str:
        return f"{self.label}:{self.lines[index][0]}" if index < len(self.lines) else f"{self.label}:end"

    def parse(self):
        if not self.lines or self.lines[0][1] != 0:
            raise ScenarioError(f"{self.label}: expected a top-level mapping at column 0")
        value, index = self.block(0, 0)
        if index != len(self.lines):
            raise ScenarioError(f"{self.where(index)}: unexpected indentation")
        return value

    def block(self, index: int, indent: int):
        text = self.lines[index][2]
        if text == "-" or text.startswith("- "):
            return self.sequence(index, indent)
        return self.mapping(index, indent)

    def nested(self, index: int, indent: int, what: str):
        if index >= len(self.lines) or self.lines[index][1] <= indent:
            raise ScenarioError(f"{self.where(index - 1)}: {what} needs an indented block (empty values are not supported)")
        return self.block(index, self.lines[index][1])

    def mapping(self, index: int, indent: int, first: str | None = None):
        result: dict[str, object] = {}
        while index < len(self.lines):
            _, actual, text = self.lines[index]
            if first is not None:
                text, first = first, None
            elif actual < indent:
                break
            elif actual > indent:
                raise ScenarioError(f"{self.where(index)}: unexpected indentation")
            elif text == "-" or text.startswith("- "):
                raise ScenarioError(f"{self.where(index)}: a sequence at the same indentation as its key is not supported")
            match = KEY.match(text)
            if not match:
                raise ScenarioError(f"{self.where(index)}: expected 'key: value', found {text[:40]!r}")
            key, rest = match.group(1), match.group(2)
            if key in result:
                raise ScenarioError(f"{self.where(index)}: duplicate key {key!r}")
            if rest:
                result[key] = scalar(rest, self.where(index))
                index += 1
            else:
                result[key], index = self.nested(index + 1, indent, f"key {key!r}")
        return result, index

    def sequence(self, index: int, indent: int):
        items = []
        while index < len(self.lines):
            _, actual, text = self.lines[index]
            if actual < indent:
                break
            if actual > indent:
                raise ScenarioError(f"{self.where(index)}: unexpected indentation")
            if not (text == "-" or text.startswith("- ")):
                raise ScenarioError(f"{self.where(index)}: mixed sequence and mapping at one indentation")
            content = text[1:].strip()
            where = self.where(index)
            if not content:
                raise ScenarioError(f"{where}: empty sequence items are not supported")
            if content.startswith("&") and NAME.fullmatch(content[1:]):
                name = content[1:]
                if name in self.anchors:
                    raise ScenarioError(f"{where}: duplicate anchor {name!r}")
                value, index = self.nested(index + 1, indent, f"anchor {name!r}")
                self.anchors[name] = value
                items.append(copy.deepcopy(value))
            elif content.startswith("*") and NAME.fullmatch(content[1:]):
                if content[1:] not in self.anchors:
                    raise ScenarioError(f"{where}: undefined alias {content!r}")
                items.append(copy.deepcopy(self.anchors[content[1:]]))
                index += 1
            elif content[0] not in "\"'" and KEY.match(content):
                value, index = self.mapping(index, indent + 2, first=content)
                items.append(value)
            else:
                items.append(scalar(content, where))
                index += 1
        return items, index


def parse_yaml(text: str, label: str = "<yaml>"):
    return Parser(text, label).parse()


def mapping(value, keys, where):
    if not isinstance(value, dict):
        raise ScenarioError(f"{where}: expected a mapping")
    unknown = sorted(set(value) - set(keys))
    missing = sorted(set(keys) - set(value))
    if unknown:
        raise ScenarioError(f"{where}: unknown key(s) {unknown}")
    if missing:
        raise ScenarioError(f"{where}: missing key(s) {missing}")
    return value


def text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where}: expected a nonempty string")
    return value


def items(value, where):
    if not isinstance(value, list) or not value:
        raise ScenarioError(f"{where}: expected a nonempty list")
    return value


def convert_document(data, relative: str):
    """Validate one parsed test_scenarios.yaml and return (skill, description, scenarios)."""
    mapping(data, TOP_KEYS, relative)
    skill = text(data["skill"], f"{relative}: skill")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", skill) or relative != f"skills/{skill}/test_scenarios.yaml":
        raise ScenarioError(f"{relative}: skill {skill!r} does not match its directory")
    scenarios = []
    for number, raw in enumerate(items(data["scenarios"], f"{relative}: scenarios"), 1):
        where = f"{relative}: scenario {number}"
        mapping(raw, SCENARIO_KEYS, where)
        scenario_id = text(raw["scenario_id"], f"{where}: scenario_id")
        if not re.fullmatch(r"[a-z0-9_]+", scenario_id):
            raise ScenarioError(f"{where}: unsupported scenario_id {scenario_id!r}")
        where = f"{relative}: {scenario_id}"
        if raw["eval_type"] not in EVAL_TYPES:
            raise ScenarioError(f"{where}: unknown eval_type {raw['eval_type']!r}")
        skill_file = text(mapping(raw["system_prompt"], ("skill_file",), f"{where}: system_prompt")["skill_file"],
                          f"{where}: skill_file")
        if skill_file != f"skills/{skill}/SKILL.md":
            raise ScenarioError(f"{where}: skill_file {skill_file!r} is not this skill's SKILL.md")
        turns = []
        for turn_number, turn in enumerate(items(raw["turns"], f"{where}: turns"), 1):
            turn_where = f"{where}: turn {turn_number}"
            mapping(turn, TURN_KEYS, turn_where)
            assertions = []
            for index, assertion in enumerate(items(turn["assertions"], f"{turn_where}: assertions"), 1):
                assertion_where = f"{turn_where}: assertion {index}"
                if not isinstance(assertion, dict):
                    raise ScenarioError(f"{assertion_where}: expected a mapping")
                operand_keys = [key for key in ("pattern", "value") if key in assertion]
                if len(operand_keys) != 1:
                    raise ScenarioError(f"{assertion_where}: needs exactly one of 'pattern' or 'value'")
                mapping(assertion, ("type", operand_keys[0], "message"), assertion_where)
                kind = assertion["type"]
                if kind not in ASSERTION_TYPES:
                    raise ScenarioError(f"{assertion_where}: unknown assertion type {kind!r}")
                operand = text(assertion[operand_keys[0]], f"{assertion_where}: {operand_keys[0]}")
                if ASSERTION_TYPES[kind] == "regex":
                    try:
                        re.compile(operand)
                    except re.error as exc:
                        raise ScenarioError(f"{assertion_where}: invalid regex: {exc}") from exc
                assertions.append({"id": f"t{turn_number}a{index}", "type": kind, operand_keys[0]: operand,
                                   "message": text(assertion["message"], f"{assertion_where}: message")})
            turns.append({"user_input": text(turn["user_input"], f"{turn_where}: user_input"), "assertions": assertions})
        scenarios.append({"case_id": f"{skill}/{scenario_id}", "skill": skill, "scenario_id": scenario_id,
                          "description": text(raw["description"], f"{where}: description"),
                          "eval_type": raw["eval_type"], "skill_file": skill_file, "turns": turns})
    return skill, text(data["description"], f"{relative}: description"), scenarios


def quote(value: str) -> str:
    if re.search(r"[\x00-\x08\x0b-\x1f]", value):
        raise ScenarioError("control characters cannot be emitted")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def to_yaml(skill: str, description: str, scenarios: list[dict]) -> str:
    """Emit the restricted YAML subset again (used by the round-trip test)."""
    lines = [f"skill: {quote(skill)}", f"description: {quote(description)}", "", "scenarios:"]
    for scenario in scenarios:
        lines += [f"  - scenario_id: {quote(scenario['scenario_id'])}",
                  f"    description: {quote(scenario['description'])}",
                  f"    eval_type: {quote(scenario['eval_type'])}",
                  "    system_prompt:", f"      skill_file: {quote(scenario['skill_file'])}", "    turns:"]
        for turn in scenario["turns"]:
            lines += [f"      - user_input: {quote(turn['user_input'])}", "        assertions:"]
            for assertion in turn["assertions"]:
                key = "pattern" if "pattern" in assertion else "value"
                lines += [f"          - type: {quote(assertion['type'])}",
                          f"            {key}: {quote(assertion[key])}",
                          f"            message: {quote(assertion['message'])}"]
    return "\n".join(lines) + "\n"


def resolve_head(source: Path) -> str:
    """Read the checkout's commit from .git as plain text (never runs git there)."""
    git = source / ".git"
    if not git.is_dir() or git.is_symlink():
        raise ScenarioError("cannot verify the upstream commit: no .git directory")
    head = (git / "HEAD").read_text(encoding="ascii").strip()
    if re.fullmatch(r"[0-9a-f]{40}", head):
        return head
    match = re.fullmatch(r"ref: (refs/[A-Za-z0-9._/-]+)", head)
    if not match or ".." in match.group(1):
        raise ScenarioError(f"unsupported .git/HEAD: {head[:60]!r}")
    ref = git.joinpath(*match.group(1).split("/"))
    if ref.is_file() and not ref.is_symlink():
        value = ref.read_text(encoding="ascii").strip()
    else:
        packed = git / "packed-refs"
        lines = packed.read_text(encoding="ascii").splitlines() if packed.is_file() else []
        value = next((line.split()[0] for line in lines if line.endswith(" " + match.group(1))), "")
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ScenarioError(f"cannot resolve {match.group(1)} to a commit")
    return value


def read_source(path: Path, relative: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ScenarioError(f"{relative}: not a regular file")
    data = path.read_bytes()
    if len(data) > MAX_SOURCE_BYTES:
        raise ScenarioError(f"{relative}: larger than {MAX_SOURCE_BYTES} bytes")
    return data.replace(b"\r\n", b"\n")  # a core.autocrlf checkout must hash like the committed text


def build(source: Path, *, commit: str = UPSTREAM_COMMIT, expected: int | None = EXPECTED_SCENARIOS):
    """Return (scenarios document, license bytes) from an upstream checkout."""
    head = resolve_head(source)
    if head != commit:
        raise ScenarioError(f"upstream checkout is at {head}, expected pinned {commit}")
    license_bytes = read_source(source / "LICENSE", "LICENSE")
    if b"Apache License" not in license_bytes[:400] or b"Version 2.0" not in license_bytes[:400]:
        raise ScenarioError("upstream LICENSE is not the Apache License 2.0")
    skills = source / "skills"
    if not skills.is_dir() or skills.is_symlink():
        raise ScenarioError("upstream checkout has no skills/ directory")
    files, scenarios = [], []
    for directory in sorted(skills.iterdir(), key=lambda path: path.name):
        if not directory.is_dir() or directory.name.startswith((".", "_")):
            continue
        relative = f"skills/{directory.name}/test_scenarios.yaml"
        data = read_source(directory / "test_scenarios.yaml", relative)
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ScenarioError(f"{relative}: not UTF-8") from exc
        skill, description, converted = convert_document(parse_yaml(decoded, relative), relative)
        files.append({"path": relative, "sha256": digest(data), "skill": skill, "description": description,
                      "scenarios": len(converted)})
        scenarios.extend(converted)
    ids = [scenario["case_id"] for scenario in scenarios]
    if len(set(ids)) != len(ids):
        raise ScenarioError("duplicate scenario ids across files")
    if expected is not None and len(scenarios) != expected:
        raise ScenarioError(f"found {len(scenarios)} scenarios, expected {expected} at the pinned commit")
    document = {
        "schema_version": 1,
        "kind": "oaw-egm-pilot-scenarios",
        "source": {"repository": UPSTREAM_REPOSITORY, "commit": commit, "copyright": "Copyright 2026 Google LLC",
                   "license": "Apache-2.0", "notice": "NOTICE.md",
                   "license_file": "LICENSE.egm", "license_sha256": digest(license_bytes),
                   "hash_basis": "sha256 of the file bytes with CRLF folded to LF", "files": files},
        "generated_by": "evals/egm-pilot/convert_scenarios.py",
        "modifications": MODIFICATIONS,
        "assertion_semantics": SEMANTICS,
        "scenarios": scenarios,
    }
    return document, license_bytes


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="EGM checkout at the pinned commit (read as data only)")
    parser.add_argument("--out", default=str(HERE / "scenarios.json"))
    parser.add_argument("--license-out", default=str(HERE / "LICENSE.egm"))
    parser.add_argument("--check", action="store_true", help="verify existing outputs instead of writing them")
    args = parser.parse_args(argv)
    try:
        document, license_bytes = build(Path(args.source).resolve())
    except (ScenarioError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    outputs = {Path(args.out): render(document), Path(args.license_out): license_bytes}
    if args.check:
        stale = [str(path) for path, data in outputs.items() if not path.is_file() or path.read_bytes() != data]
        if stale:
            print("stale: " + ", ".join(stale), file=sys.stderr)
            return 1
        print(f"ok: {len(document['scenarios'])} scenarios match {UPSTREAM_COMMIT[:7]}")
        return 0
    for path, data in outputs.items():
        path.write_bytes(data)
    turns = sum(len(scenario["turns"]) for scenario in document["scenarios"])
    print(f"wrote {len(document['scenarios'])} scenarios ({turns} turns) from {len(document['source']['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
