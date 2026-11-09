"""I16 freeze (PREREG.md): verify every planted defect mechanically and write frozen/spec.json.

For each author's defects/<journey>/ (mutation.patch, oracle.sh, truth.json): the patch applies to the OAW snapshot,
the journey's setup succeeds on the patched and the clean build, oracle.sh exits 1 on the patched build and 0 on the
clean build (each inside the same sandbox the testers get). Clean controls: three journeys from each author's pool
that neither author used, the first three by sha256("i16-clean|" + id); their setup must succeed.

    python3 i16_build_spec.py --inventory inventory.json --pools author_pools.json --defects A/defects,B/defects \
        --oaw-src DIR --skill SKILL.md --out FROZEN
Any failure stops the freeze and names the journey.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from i16_run import base_env, build, bwrap, skill_texts, tree_digest  # noqa: E402

REQUIRED_TRUTH = ("journey", "category", "severity", "rubric", "trigger", "user_impact", "intended_lookalikes")


def oracle(work, script):
    shutil.copy(script, os.path.join(work, ".oracle.sh"))
    done = subprocess.run(bwrap(work, None, ["/bin/bash", ".oracle.sh"]), env=base_env(work, ""), capture_output=True,
                          text=True, timeout=180)
    os.remove(os.path.join(work, ".oracle.sh"))
    return done.returncode, (done.stdout + done.stderr)[-600:]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", required=True)
    p.add_argument("--pools", required=True)
    p.add_argument("--defects", required=True, help="comma list: opus defects folder, then codex defects folder")
    p.add_argument("--oaw-src", required=True)
    p.add_argument("--skill", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--replaced", default="", help="OLD:NEW,... ceiling replacements (one round only, PREREG)")
    p.add_argument("--prior-spec", help="with --replaced: the spec the calibration ran on")
    p.add_argument("--prior-floor", help="with --replaced: that calibration's floor-final.json")
    a = p.parse_args(argv)
    replaced = dict(x.split(":", 1) for x in filter(None, a.replaced.split(",")))
    provenance = None
    if replaced:  # the old journeys must have been at the ceiling in the prior calibration, replaced only once
        prior = json.load(open(a.prior_spec, encoding="utf-8"))
        floor = json.load(open(a.prior_floor, encoding="utf-8"))
        if prior.get("ceiling_replaced") or floor["spec_sha256"] != hashlib.sha256(open(a.prior_spec, "rb").read()).hexdigest():
            raise SystemExit("replacement allowed once, from the calibration of the prior spec only")
        if not set(replaced) <= set(floor["ceiling"]):
            raise SystemExit("a replaced journey was not at the ceiling in the prior calibration")
        provenance = {"prior_spec_sha256": floor["spec_sha256"],
                      "prior_floor_sha256": hashlib.sha256(open(a.prior_floor, "rb").read()).hexdigest(),
                      "prior_truth": {old: prior["truth"][old] for old in replaced},
                      "prior_authors": {old: prior["authors"][old] for old in replaced}}
    inventory = {j["id"]: j for j in json.load(open(a.inventory, encoding="utf-8"))}
    pools = json.load(open(a.pools, encoding="utf-8"))
    authors = dict(zip(("opus", "codex"), a.defects.split(",")))
    base = tempfile.mkdtemp(prefix="i16spec-")
    cases_out = os.path.join(a.out, "cases")
    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(cases_out)
    kinds, truth, built, author_of, verification = {}, {}, {}, {}, {}
    for who, folder in authors.items():
        names = sorted(n for n in os.listdir(folder) if os.path.isdir(os.path.join(folder, n)))
        if len(names) != 3:
            raise SystemExit(f"{who}: expected 3 defects, found {names}")
        for jid in names:
            if jid not in pools[who]:
                raise SystemExit(f"{who}: {jid} is not in its pool")
            src = os.path.join(folder, jid)
            t = json.load(open(os.path.join(src, "truth.json"), encoding="utf-8"))
            if any(k not in t for k in REQUIRED_TRUTH) or t["journey"] != jid or t["severity"] not in ("critical", "major"):
                raise SystemExit(f"{who} {jid}: truth.json incomplete or inconsistent")
            dest = os.path.join(cases_out, jid)
            os.makedirs(dest)
            journey = {k: inventory[jid][k] for k in ("id", "goal", "setup", "commands")}
            json.dump(journey, open(os.path.join(dest, "journey.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            for name in ("mutation.patch", "oracle.sh", "truth.json"):
                shutil.copy(os.path.join(src, name), os.path.join(dest, name))
            patched, clean = tempfile.mkdtemp(dir=base), tempfile.mkdtemp(dir=base)
            facts = build(dest, a.oaw_src, patched, with_defect=True)
            build(dest, a.oaw_src, clean, with_defect=False)
            bad, out_bad = oracle(patched, os.path.join(dest, "oracle.sh"))
            good, out_good = oracle(clean, os.path.join(dest, "oracle.sh"))
            verification[jid] = {"author": who, "oracle_patched_exit": bad, "oracle_clean_exit": good,
                                 "patched_tail": out_bad[-300:], "clean_tail": out_good[-300:]}
            if bad != 1 or good != 0:
                raise SystemExit(f"{who} {jid}: oracle patched {bad} (want 1), clean {good} (want 0)\n{out_bad}\n{out_good}")
            kinds[jid], truth[jid], built[jid], author_of[jid] = "defect", t, facts["oaw_digest"], who
    for who in ("opus", "codex"):
        free = [j for j in pools[who] if j not in kinds and j not in replaced]  # a retired journey never turns clean
        for jid in sorted(free, key=lambda j: hashlib.sha256(f"i16-clean|{j}".encode()).hexdigest())[:3]:
            dest = os.path.join(cases_out, jid)
            os.makedirs(dest)
            journey = {k: inventory[jid][k] for k in ("id", "goal", "setup", "commands")}
            json.dump(journey, open(os.path.join(dest, "journey.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            work = tempfile.mkdtemp(dir=base)
            facts = build(dest, a.oaw_src, work)
            kinds[jid], built[jid], author_of[jid] = "clean", facts["oaw_digest"], f"{who} pool"
            verification[jid] = {"author": f"{who} pool", "setup": "ok"}
    order = sorted(kinds, key=lambda j: hashlib.sha256(f"i16-order|{j}".encode()).hexdigest())
    os.makedirs(os.path.join(a.out, "skill"))
    shutil.copy(a.skill, os.path.join(a.out, "skill", "SKILL.md"))
    full, _desc = skill_texts(a.skill)
    spec = {"order": order, "kinds": kinds, "truth": truth, "authors": author_of, "built_digests": built,
            "oaw_src_digest": tree_digest(a.oaw_src), "skill_sha256": hashlib.sha256(full.encode()).hexdigest(),
            "case_digests": {j: tree_digest(os.path.join(cases_out, j)) for j in order},
            "inputs": {os.path.basename(x): hashlib.sha256(open(x, "rb").read()).hexdigest()
                       for x in (a.inventory, a.pools, os.path.join(HERE, "categories.json"),
                                 os.path.join(HERE, "categories-authors.json"), os.path.join(HERE, "author_prompt.md"))},
            "ceiling_replaced": replaced, "ceiling_provenance": provenance}
    for old, new in replaced.items():
        p_truth, p_author = provenance["prior_truth"][old], provenance["prior_authors"][old]
        if (truth[new]["category"], truth[new]["severity"], author_of[new]) != (p_truth["category"], p_truth["severity"], p_author):
            raise SystemExit(f"{new} must keep {old}'s author, category and severity")
    if set(replaced) & set(order) or not set(replaced.values()) <= {j for j in order if kinds[j] == "defect"}:
        raise SystemExit("a replaced journey is still in the bank, or a replacement is not a defect journey")
    json.dump(spec, open(os.path.join(a.out, "spec.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(verification, open(os.path.join(a.out, "verification.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shutil.rmtree(base, ignore_errors=True)
    print(f"frozen: {sum(v == 'defect' for v in kinds.values())} defect, {sum(v == 'clean' for v in kinds.values())} clean")
    print("order:", order)
    return 0


if __name__ == "__main__":
    sys.exit(main())
