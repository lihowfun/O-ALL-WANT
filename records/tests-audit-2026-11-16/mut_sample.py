#!/usr/bin/python3
"""Plant one small logic error at a time in scripts/*.py and see whether the unit tests notice.

Each job runs the whole test suite on a private copy of the tree inside a bubblewrap sandbox
(whole filesystem read-only except the job directory, no network). Controls are unmutated copies
run under the same parallel load.
"""
import argparse
import ast
import concurrent.futures
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

RUNNER = r'''
import sys, json, unittest
suite = unittest.defaultTestLoader.discover('tests')
r = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
bad = r.failures + r.errors
print('MUT-SUMMARY ' + json.dumps({'run': r.testsRun, 'failures': len(r.failures), 'errors': len(r.errors),
                                   'skipped': len(r.skipped), 'ok': r.wasSuccessful(),
                                   'first': [t.id() for t, _ in bad[:5]]}))
raise SystemExit(0 if r.wasSuccessful() else 1)
'''

CMP_SWAP = {'==': '!=', '!=': '==', '<': '<=', '<=': '<', '>': '>=', '>=': '>',
            'is not': 'is', 'is': 'is not', 'not in': 'in', 'in': 'not in'}
CMP_TEXT = {ast.Eq: '==', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>=',
            ast.Is: 'is', ast.IsNot: 'is not', ast.In: 'in', ast.NotIn: 'not in'}


def offsets(source):
    starts, total = [], 0
    for line in source.split(b'\n'):
        starts.append(total)
        total += len(line) + 1
    return starts


def find_sites(path, rel):
    source = path.read_bytes()
    tree = ast.parse(source)
    starts = offsets(source)
    pos = lambda line, col: starts[line - 1] + col
    sites = []

    def between(a, b, token):
        lo, hi = pos(a.end_lineno, a.end_col_offset), pos(b.lineno, b.col_offset)
        gap = source[lo:hi].decode('utf-8', 'replace')
        if '#' in gap:
            return None
        pattern = r'\s+'.join(re.escape(part) for part in token.split())
        if token[0].isalpha():
            pattern = r'(?<![A-Za-z0-9_])' + pattern + r'(?![A-Za-z0-9_])'
        found = list(re.finditer(pattern, gap))
        if len(found) != 1:
            return None
        # reject a longer operator that contains this one (for example "<" inside "<=")
        m = found[0]
        if token in ('<', '>', '=') and gap[m.end():m.end() + 1] == '=':
            return None
        if token == 'is' and re.match(r'\s+not(?![A-Za-z0-9_])', gap[m.end():]):
            return None
        if token == 'in' and re.search(r'not\s+$', gap[:m.start()]):
            return None
        prefix = len(gap[:m.start()].encode())
        return lo + prefix, lo + prefix + len(m.group(0).encode())

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in CMP_TEXT:
            token = CMP_TEXT[type(node.ops[0])]
            span = between(node.left, node.comparators[0], token)
            if span:
                sites.append((rel, node.lineno, 'compare', span, token, CMP_SWAP[token]))
        elif isinstance(node, ast.BoolOp) and len(node.values) >= 2:
            token = 'and' if isinstance(node.op, ast.And) else 'or'
            span = between(node.values[0], node.values[1], token)
            if span:
                sites.append((rel, node.lineno, 'boolop', span, token, 'or' if token == 'and' else 'and'))
        elif isinstance(node, ast.Constant) and (node.value is True or node.value is False):
            lo, hi = pos(node.lineno, node.col_offset), pos(node.end_lineno, node.end_col_offset)
            text = source[lo:hi].decode()
            if text in ('True', 'False'):
                sites.append((rel, node.lineno, 'constant', (lo, hi), text, 'False' if text == 'True' else 'True'))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            lo = pos(node.lineno, node.col_offset)
            m = re.match(rb'not\s+', source[lo:lo + 12])
            if m:
                sites.append((rel, node.lineno, 'not', (lo, lo + m.end()), 'not ', ''))
    return sites


def mutate(source, span, new):
    return source[:span[0]] + new.encode() + source[span[1]:]


def run_job(job, base, work, timeout):
    jobdir = work / f'job{job["id"]:03d}'
    shutil.rmtree(jobdir, ignore_errors=True)
    repo = jobdir / 'repo'
    shutil.copytree(base, repo, symlinks=True)
    (jobdir / 'home').mkdir()
    (jobdir / 'tmp').mkdir()
    if job['kind'] == 'mutant':
        target = repo / job['file']
        source = target.read_bytes()
        changed = mutate(source, tuple(job['span']), job['new'])
        try:
            compile(changed, job['file'], 'exec')
        except SyntaxError as error:
            shutil.rmtree(jobdir, ignore_errors=True)
            return dict(job, outcome='invalid', detail=str(error))
        target.write_bytes(changed)
    command = ['bwrap', '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp',
               '--bind', str(jobdir), str(jobdir), '--unshare-net', '--die-with-parent',
               '--setenv', 'HOME', str(jobdir / 'home'), '--setenv', 'TMPDIR', str(jobdir / 'tmp'),
               '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', '--chdir', str(repo),
               '/usr/bin/python3', '-c', RUNNER]
    started = time.time()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               errors='replace', start_new_session=True)
    try:
        out, err = process.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
        timed_out = True
    seconds = round(time.time() - started, 1)
    summary = None
    for line in out.splitlines():
        if line.startswith('MUT-SUMMARY '):
            summary = json.loads(line[len('MUT-SUMMARY '):])
    if timed_out:
        outcome = 'killed-timeout'
    elif summary is None:
        outcome = 'killed-crash'
    elif summary['ok'] and process.returncode == 0:
        outcome = 'survived'
    else:
        outcome = 'killed'
    result = dict(job, outcome=outcome, seconds=seconds, returncode=process.returncode, summary=summary,
                  tail=err[-600:] if outcome in ('killed-crash',) or job['kind'] == 'control' else '')
    shutil.rmtree(jobdir, ignore_errors=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--work', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--n', type=int, default=60)
    parser.add_argument('--controls', type=int, default=4)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--seed', type=int, default=20261116)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--list-only', action='store_true')
    args = parser.parse_args()
    base, work = Path(args.base), Path(args.work)
    sites = []
    for path in sorted((base / 'scripts').glob('*.py')):
        sites.extend(find_sites(path, f'scripts/{path.name}'))
    by_kind, by_file = {}, {}
    for site in sites:
        by_kind[site[2]] = by_kind.get(site[2], 0) + 1
        by_file[site[0]] = by_file.get(site[0], 0) + 1
    print(json.dumps({'sites': len(sites), 'by_kind': by_kind, 'files': len(by_file)}), flush=True)
    rng = random.Random(args.seed)
    chosen = rng.sample(sites, args.n)
    jobs = []
    for site in chosen:
        rel, line, kind, span, old, new = site
        text = (base / rel).read_bytes().split(b'\n')[line - 1].decode('utf-8', 'replace').strip()
        jobs.append({'kind': 'mutant', 'file': rel, 'line': line, 'op': kind, 'span': list(span), 'old': old,
                     'new': new, 'source': text[:160]})
    step = max(1, len(jobs) // max(1, args.controls))
    for index in range(args.controls):
        jobs.insert(min(len(jobs), index * (step + 1)), {'kind': 'control'})
    for index, job in enumerate(jobs):
        job['id'] = index
    if args.list_only:
        for job in jobs:
            print(json.dumps(job, ensure_ascii=False))
        return 0
    work.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w') as handle, concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(run_job, job, base, work, args.timeout) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            handle.write(json.dumps(result, ensure_ascii=False) + '\n')
            handle.flush()
            print(result['id'], result['kind'], result['outcome'], result.get('seconds'), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
