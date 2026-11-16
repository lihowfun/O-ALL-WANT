#!/usr/bin/python3
"""Summarise the planted-error sample: caught / missed, by kind and by file, with a Wilson interval."""
import collections
import json
import math
import sys


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


rows = [json.loads(line) for line in open(sys.argv[1])]
controls = [r for r in rows if r['kind'] == 'control']
mutants = [r for r in rows if r['kind'] == 'mutant']
print('jobs', len(rows), 'controls', len(controls), 'mutants', len(mutants))
for r in sorted(controls, key=lambda r: r['id']):
    print('  control', r['id'], r['outcome'], r['seconds'], 's', r['summary'])
outcomes = collections.Counter(r['outcome'] for r in mutants)
print('mutant outcomes', dict(outcomes))
valid = [r for r in mutants if r['outcome'] != 'invalid']
caught = [r for r in valid if r['outcome'] != 'survived']
low, high = wilson(len(caught), len(valid))
print(f'caught {len(caught)}/{len(valid)} = {len(caught) / max(1, len(valid)):.1%}  (95% Wilson {low:.1%}..{high:.1%})')
for key in ('op', 'file'):
    table = collections.defaultdict(lambda: [0, 0])
    for r in valid:
        table[r[key]][1] += 1
        table[r[key]][0] += r['outcome'] != 'survived'
    print(f'-- by {key}')
    for name, (k, n) in sorted(table.items()):
        print(f'  {name:32s} {k}/{n}')
seconds = sorted(r['seconds'] for r in rows if r.get('seconds'))
print('seconds per run: median', seconds[len(seconds) // 2], 'max', seconds[-1])
fails = sorted(r['summary']['failures'] + r['summary']['errors'] for r in caught if r.get('summary'))
if fails:
    print('failing tests per caught mutant: min', fails[0], 'median', fails[len(fails) // 2], 'max', fails[-1],
          '| caught by exactly one test:', sum(1 for f in fails if f == 1))
print('-- missed (survived)')
for r in sorted((r for r in valid if r['outcome'] == 'survived'), key=lambda r: (r['file'], r['line'])):
    print(f"  {r['file']}:{r['line']} [{r['op']}] {r['old']!r}->{r['new']!r} | {r['source']}")
