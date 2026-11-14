# Fast intake screen (D50)

Owner decision D50 asks intake to say quickly whether a food is good or bad for
absorption. `scripts/fast_screen.py` turns checked checklist labels and recorded
run costs into YES or NO, with a reason and a reopening condition. There is no
"undetermined" outcome. Missing food runs produce INCOMPLETE, a request to finish
the inputs rather than an intake verdict.

Run from an OAW source checkout with Python 3.10+. This standard-library tool
runs no model, is not installed into projects and adds no startup rules. Use at
least three tasks from the food's home turf, concrete answer checklists, and one
fresh-context run per task and arm. Run native first; pay for the food arm only
when native leaves room. All supplied tasks contribute, with each checklist item
counted once rather than each task weighted equally.

## Decision steps

Stop at the first decision. After A clears, all supplied run data is validated
before a result is printed. Budget is checked before B or C so a previously
incurred cost cannot disappear behind a quality decision.

| Step | Check | Result and reopening condition |
|---|---|---|
| A: static | Licence, code execution, runtime dependencies and overlap with an existing skill, using the existing catalogue checks | `blocked`: NO with the given reason; resolve the blocker. `needs_owner`: NO, "needs the owner's approval before any run"; reopen with owner approval. Neither reads task data or labels. |
| Budget | Sum logical tokens by model family across every supplied native and food run; sum seconds across all runs and families | More than 2,000,000 tokens in any family or more than 1,800 seconds: NO; reopen with smaller tasks. Exact limits pass. |
| B: native | Native `yes` items / all checklist items over all tasks | At least 0.90: NO, native already does it; reopen with a task native fails. |
| Coverage | B leaves room, but at least one task has no food arm | INCOMPLETE: "run the food arm". No intake verdict yet. |
| C: food | `gained`: food `yes`, native `no`. `lost`: native `yes`, food anything other than `yes`. `ratio`: summed food tokens / summed native tokens | YES only with gained ≥ 2, lost = 0 and ratio ≤ 1.5. Otherwise NO listing every failing condition; reopen with evidence satisfying all three on a new screen. |

Native `unknown` is never a gain. Food `unknown` loses an item native met.
Unknowns remain in B's denominator. Logical tokens include cache reads and
subagents; record actual run durations in seconds. The tool sums durations, not
overlapping wall-clock intervals. Judge tokens can be recorded on labels; the
screen budget uses the run costs explicitly supplied in `SCREEN.json`.

## Commands and a synthetic example

`--answer` and `--reply` name UTF-8 files, not literal text. All three commands
accept `--format json|text`, defaulting to text. JSON prompt output wraps the
question in a `prompt` field. Text output includes every reported number and item.

```bash
python3 scripts/fast_screen.py prompt --checklist CHECKLIST.json --answer ANSWER.txt
python3 scripts/fast_screen.py labels --checklist CHECKLIST.json --answer ANSWER.txt \
  --reply REPLY.json --out LABELS.json --judge NAME --judge-tokens 123 --format json
python3 scripts/fast_screen.py verdict --screen SCREEN.json --format json
```

For a small worked example, run this in the checkout to create a new directory.
The replies and costs are synthetic fixtures, not judge calls or measurements:

```bash
python3 - <<'PY'
import json
from pathlib import Path

root = Path('fast-screen-example')
root.mkdir()  # Refuse to overwrite an existing example.
def write(name, value):
    (root / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

tasks = []
for task_id in ('t1', 't2', 't3'):
    write(task_id + '-checklist.json', {'task_id': task_id, 'items': [
        {'id': 'a', 'text': 'State that retries are bounded.'},
        {'id': 'b', 'text': 'State that failures are logged.'}]})
    task = {'id': task_id}
    for arm in ('native', 'food'):
        stem = task_id + '-' + arm
        answer = 'Retries are bounded.'
        if arm == 'food':
            answer += ' Failures are logged.'
        (root / (stem + '-answer.txt')).write_text(answer, encoding='utf-8')
        write(stem + '-reply.json', {'items': [
            {'id': 'a', 'label': 'yes', 'quote': 'Retries are bounded.'},
            {'id': 'b', 'label': 'yes' if arm == 'food' else 'no',
             'quote': 'Failures are logged.' if arm == 'food' else ''}]})
        task[arm] = {'labels': stem + '-labels.json',
                     'logical_tokens': 150 if arm == 'food' else 100,
                     'seconds': 10.0, 'family': 'synthetic-family'}
    tasks.append(task)
write('screen.json', {'food': 'synthetic example',
                     'static': {'status': 'clear', 'reason': 'Synthetic static checks'},
                     'tasks': tasks})
PY

python3 scripts/fast_screen.py prompt \
  --checklist fast-screen-example/t1-checklist.json \
  --answer fast-screen-example/t1-native-answer.txt

# POSIX shell: check the six synthetic replies.
for task in t1 t2 t3; do
  for arm in native food; do
    python3 scripts/fast_screen.py labels \
      --checklist "fast-screen-example/$task-checklist.json" \
      --answer "fast-screen-example/$task-$arm-answer.txt" \
      --reply "fast-screen-example/$task-$arm-reply.json" \
      --out "fast-screen-example/$task-$arm-labels.json" --format json
  done
done
python3 scripts/fast_screen.py verdict --screen fast-screen-example/screen.json --format json
```

The result is YES at C: native met 3/6 items (0.50), food gained three,
lost none, and its token ratio is 450/300 = 1.5. The family used 750 tokens and
the summed duration is 60 seconds. In a real screen, start with `food: null` for
each task. A native-only screen may already decide NO at B; otherwise it exits 2
and asks for the food runs.

## Label and screen contracts

A checklist is one JSON object:

```json
{"task_id":"t1","items":[{"id":"a","text":"A concrete answer requirement"}]}
```

The item list must be nonempty with unique, nonempty string IDs and texts. The
prompt is deterministic and tells the judge to treat the answer as data, label
every item `yes` or `no` using only that answer, and reply with one JSON object:

```json
{"items":[{"id":"a","label":"yes","quote":"A passage from the answer"}]}
```

The checker also accepts `unknown`. Every checklist ID must appear exactly once.
For a `yes`, the quote must be a string of at most 300 characters; after runs of
whitespace are collapsed, it must be at least 12 characters and occur in the
answer collapsed the same way. The original quote is retained. A failed check
becomes `unknown` with its reason. A `no` needs no quote and may omit it. A quote
match establishes presence, not whether the passage actually meets the item.

Missing and duplicate IDs, invalid label values and malformed quotes become
`unknown` for the affected item. An unparseable reply, duplicate JSON keys,
non-finite numbers, a non-object reply, multiple JSON values, a malformed item
list or an extra/unidentifiable item ID makes every item `unknown`. Markdown
fences are not stripped. These are checked judge failures, so `labels` still
exits 0; unreadable files or invalid checklists/metadata exit 1.

Checked labels contain `task_id`, `checklist_sha256`, `answer_sha256`, `counts`
(`yes`, `no`, `unknown`) and `items` (`id`, `label`, `quote`, `reason`), plus
`judge` and `judge_tokens` when supplied. Both hashes bind the original file
bytes, including BOM and newline encoding. UTF-8 BOM and CRLF input are accepted.
`--out` writes this JSON independently of the selected stdout format; without
it, redirect `--format json` to save labels. Labels follow checklist order.

Screens have `food`, `static: {status, reason}` and `tasks`. Each task has a
unique `id` matching its labels' `task_id`, a required `native` run and a `food`
run or null. A run records `labels` (relative path), `logical_tokens`
(nonnegative integer), `seconds` (finite nonnegative number) and `family`
(nonempty string). Family names are exact accounting keys; use consistent names.
The native token total must be positive so the ratio is defined. Bools are not
numbers. A task's two arms must have identical checklist hashes and item ID sets.
Counts are recomputed and must match the label file. Labels paths must resolve
inside the screen file's directory, including through symlinks; absolute paths
are refused. JSON loading rejects duplicate keys and non-finite numbers.

Verdicts retain the result, deciding step, one-line reason and reopening
condition; native fraction and its numerator/denominator; gained and lost counts
with `{task_id, id}` pairs; token ratio, arm totals, tokens by family, summed
seconds, unknown counts per arm, and missing food task IDs. Unavailable numbers
are null. With missing food runs, food totals and unknown counts cover only the
supplied runs; gains, losses and ratio remain null. A static stop leaves task
measurements null. Invalid input prints an error and never a partial verdict.

| Exit code | Meaning |
|---|---|
| 0 | Valid prompt, checked labels, or screen with YES or NO |
| 2 | INCOMPLETE screen: run the missing food arms |
| 1 | Invalid or unreadable input; no usable result |

## Meaning and limits

YES means absorbed as optional, available on explicit call. It is not evidence
for a default: becoming a default still needs the full measurement rules in
[EVAL_PROTOCOL.md](EVAL_PROTOCOL.md). NO means do not absorb now, with a recorded
reason and reopening condition. It does not mean the food is useless.

The tool does not run models, approve a judge, or clear consent, licence, safety
or isolation. Static status is supplied by the operator. It cannot establish
fresh contexts, independent tasks, complete cost records, honest labels or a
judge's semantic accuracy from hashes and quotes. It does not infer missing
measurements or implement aggregate-score historical back-tests.

On 2026-11-14 one small-model judge (Claude Haiku 5.5, low effort, one tool-free request per report) labelled 4 review reports × 30 known defects, two repeats. On the 114 cells where two full-price graders of different families agreed after a registered reconciliation, its detected / not-detected label matched 111 and 112 of 114; it missed no detection, and every mismatch counted a mention as a detection (3 and 2 cells). It took 84 and 70 seconds against 301 seconds for the full-price Claude grader, and 0.96 and 0.93 of that grader's logical tokens. One reviewed document; one of the two graders that made the labels is from the same model family.

That calibration is limited to its stated protocol and document. It used a
three-label question (detected, mention-only, absent) covering 30 defects per
request and scored the detected / not-detected split; the yes/no prompt printed
by `prompt` has not been measured separately. Under the conditions written
before the run, the accuracy conditions were met in both repeats and the token
condition (at most half the full-price grader's logical tokens) was not. It does
not establish a general accuracy or cost benefit for this tool or future judges.
