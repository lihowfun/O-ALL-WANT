#!/usr/bin/env python3
"""Hash this preparation without reading KEY.json or calling a model."""
import argparse
from pathlib import Path
from cal_common import canonical, load, require, save, sha

HERE = Path(__file__).resolve().parent
FILES = ['DEVIATIONS.md', 'source_provenance.json', 'PREREG.md', 'GRADER.md', 'RUNBOOK.md', 'build_packet.py', 'cal_run.py',
         'cal_grade.py', 'cal_requests.py', 'cal_common.py', 'cal_sandbox.py', 'cal_ledger.py',
         'freeze_tools.py', 'packet_manifest.json', 'packet_audit.json',
         'prompt_manifest.json', 'ledger_manifest.json', 'gate.template.json', 'accounting.template.json',
         'tests/__init__.py', 'tests/test_calibration.py', 'tests/test_round3.py', 'tests/test_round4.py',
         'prompts/native.txt', 'prompts/merge.txt', 'prompts/task_context.txt',
         'prompts/x2-native.txt', 'prompts/native-vs-x2.diff']


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--create', action='store_true')
    p.add_argument('--check', action='store_true')
    p.add_argument('--refresh', action='store_true', help='archive prior round snapshot and replace preparation snapshot; not a lead freeze')
    a = p.parse_args(argv)
    path = HERE / 'freeze_manifest.json'
    actual = {'schema_version': 1, 'status': 'round 4 preparation; eligibility settled; awaiting lead preflight and freeze',
              'files': {n: sha((HERE / n).read_bytes()) for n in FILES}}
    if a.refresh:
        previous = HERE / 'freeze_manifest.round2.json'
        require(path.exists(), 'no prior preparation snapshot')
        if not previous.exists():
            save(previous, load(path))
        save(path, actual)
    if a.create:
        require(not path.exists(), 'snapshot exists; use --check')
        save(path, actual)
    require(load(path) == actual, 'preparation files changed')
    print(sha(canonical(actual)))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError):
        raise SystemExit('freeze check failed')
