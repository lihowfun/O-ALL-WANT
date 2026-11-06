#!/usr/bin/env bash
# Tasting area for the EGM self-test (PREREG.md): one workspace per (arm, case), OAW V2 without EGM in every one,
# EGM's official Claude Code plugin at project scope in the E workspaces only, pristine tars for the runner.
#
#   T=<tasting dir> OAW=<claude/oaw-2 checkout> CLAUDE=<claude CLI> RECORDS=<this folder> bash setup.sh
set -euo pipefail
: "${T:?tasting dir}" "${OAW:?claude/oaw-2 checkout}" "${CLAUDE:?claude CLI}" "${RECORDS:?this folder}"
PIN=f0ba151b252c9abf1318d9fe857a43265d06de89
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
export DISABLE_AUTOUPDATER=1
mkdir -p "$T/ws" "$T/pristine" "$T/proof"
cd "$T"

# 1. The frozen cases: spec canonical hash and every case file hash (LF-normalized), as registered on 2026-10-29.
python3 -I - "$OAW/evals/egm-local" <<'PY'
import hashlib, json, pathlib, sys
here = pathlib.Path(sys.argv[1])
spec = json.loads((here / "spec.json").read_text(encoding="utf-8"))
canonical = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
registered = (here / "spec.sha256").read_text(encoding="utf-8").split()[0]
assert hashlib.sha256(canonical).hexdigest() == registered, "spec changed after registration"
for rel, expected in spec["case_hashes"].items():
    data = (here / rel).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == expected, rel
print("spec and", len(spec["case_hashes"]), "case files intact; spec", registered[:12])
PY

# 2. The food at the pin V2 bundles.
[ -d egm-upstream ] || git clone -q https://github.com/google/elephant-goldfish-model.git egm-upstream
git -C egm-upstream checkout -q --detach "$PIN"
test "$(git -C egm-upstream rev-parse HEAD)" = "$PIN"

# 3. Workspaces: case files + OAW V2 (claude host) with EGM taken out.
CHECKLIST='Project review checklist: check that check-then-act steps on shared state are atomic and that a repeated or retried request cannot take effect twice; check every storage and technology choice against the accepted ADRs; check that data retention windows cover every stated lookup or support need; check that state updated from events cannot move backwards when events arrive late, out of order or twice; check that logs never contain secrets or full credentials; check that every named component, shim or dependency is actually defined; check that the implementation plan has concrete scope and done criteria.'
for case in orders events clean; do
  for arm in N E P; do
    ws="$T/ws/$case-$arm"
    rm -rf "$ws" && mkdir -p "$ws"
    cp -r "$OAW/evals/egm-local/cases/$case/." "$ws/"
    # The supported recipe without EGM: only the oaw-evidence skill. Both supported removal paths (this recipe and
    # `catalog.py remove egm`) still leave the inert EGM runtime under .oaw/integrations/egm and the AGENTS.md
    # sentence that V2 includes it; the runtime folder is deleted so the host really has no EGM to find.
    python3 "$OAW/scripts/oaw.py" init --target "$ws" --host claude --skills oaw-evidence --json > /dev/null
    rm -rf "$ws/.oaw/integrations/egm"
    if ls "$ws/.claude/skills" | grep -q '^egm'; then echo "egm skill left in $ws"; exit 2; fi
    if [ "$arm" = P ]; then printf '\n%s\n' "$CHECKLIST" >> "$ws/CLAUDE.md"; fi
  done
done

# 4. The food, official Claude Code install at project scope (README "Claude Code", docs/claude.md), E only.
python3 -I "$RECORDS/snap_user_state.py" proof/before_install.json "$CLAUDE" > /dev/null
for case in orders events clean; do
  ( cd "$T/ws/$case-E"
    "$CLAUDE" plugin marketplace add --scope project "$T/egm-upstream"
    "$CLAUDE" plugin install --scope project egm@egm )
done
python3 -I "$RECORDS/snap_user_state.py" proof/after_install.json "$CLAUDE" > /dev/null
ROOT="$(ls -d "$HOME"/.claude/plugins/cache/egm/egm/* | head -1)"
test -f "$ROOT/skills/egm-review/SKILL.md"
echo "plugin root: $ROOT"

# 5. Pristine tars (the runner restores each workspace from its tar before and after every run) and arms.json.
python3 -I - "$T" "$ROOT" <<'PY'
import json, os, sys, tarfile
t, root = sys.argv[1], sys.argv[2]
arms = {}
for arm in "NEP":
    spec = {"workspaces": {}, "pristine": {}}
    for case in ("orders", "events", "clean"):
        ws, tar = f"{t}/ws/{case}-{arm}", f"{t}/pristine/{case}-{arm}.tar"
        with tarfile.open(tar, "w") as archive:
            for name in sorted(os.listdir(ws)):
                archive.add(os.path.join(ws, name), arcname=name)
        spec["workspaces"][case], spec["pristine"][case] = ws, tar
    if arm == "E":
        spec["add_dir"] = root
    arms[arm] = spec
json.dump(arms, open(f"{t}/arms.json", "w"), indent=1)
print("arms.json written")
PY
