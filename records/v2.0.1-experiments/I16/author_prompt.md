You are planting defects in a command-line tool for a bug-bash study. Testers will later get a user journey and the
tool, and try to find what is wrong through the command line. Half of the journeys they get have no planted defect.

## What is in this folder

- `./oaw`: the tool's source (OAW, a standard-library Python toolkit). Read its AGENTS.md, scripts/, tests/ and
  docs/CLI_Reference.md. Python is `/usr/bin/python3`. Do not change `./oaw`; work on copies.
- `./inventory.json`: user journeys that the tool's existing tests already cover. Each has `id`, `goal` (the text a
  tester will get), `setup` (shell commands that build the starting state in an empty folder holding a copy of the
  source at `./oaw`), `commands`, `oracle_tests` and `can_host`.
- `./categories.json`: the defect categories and rules. Read `seeded_defect_rules`.

## Task

Plant exactly three defects, each on a different journey from the inventory, with these categories and severities:
{assignment}

For each, create `./defects/<journey id>/` with:
1. `mutation.patch`: a unified diff against `./oaw`, paths `a/...` and `b/...` relative to the source root
   (it is applied with `patch -p1` inside a copy of the source). A small change a real developer could make by
   mistake. No comment, name, message or test change that hints at the defect. Do not edit tests.
2. `oracle.sh`: a deterministic bash script, run from a workspace folder that holds `./oaw` (patched or not) after
   the journey's `setup` has run. Exit 0 only when it positively confirms the correct behavior (the expected exit
   code, output and resulting files), exit 1 only when it observes the defect's specific wrong behavior, and exit 2
   for anything else (a setup problem, an unrelated error, an unexpected state). Offline, under 60 seconds, no
   network, no model calls. It may call `oracle_tests` from the inventory if they catch it.
3. `truth.json`: {{"journey": "<id>", "category": "B<n>", "severity": "critical|major", "rubric": "<one line a
   grader can match against a tester's report: the wrong behavior a user sees>", "trigger": "<the input or sequence
   that shows it>", "user_impact": "<one or two sentences>", "intended_lookalikes": ["<behavior on this journey that
   may look wrong but is intended or documented>", ...]}}

Rules:
- The defect must be observable through the command line by a user following the journey or a variation of it a
  careful tester could try. It should not show up when the journey is run once in the most ordinary way with
  ordinary inputs; it shows up with an input variation, a repeated or interrupted run, another working directory or
  a check of resulting state that a careful tester could think of.
- The journey's `setup` must still succeed with the patch applied.
- Verify each defect yourself: copy the source twice (patched and clean) into temporary folders under the current
  folder, run the journey setup in each, run `oracle.sh` in each (patched exits 1, clean exits 0), and run the full
  test suite on the patched copy (`/usr/bin/python3 -m unittest discover -s tests` from the source root) to list
  which tests fail. Record all of this in `./defects/<journey id>/verify.md` (commands and results). Be economical:
  run the full suite once per defect, after the oracle passes both ways.
- Do not plant two defects in the same function. Do not plant anything in `./oaw/tests`.
- No network, no model calls, nothing outside the current folder. Keep absolute paths out of the files you write
  (use paths relative to the workspace).

Final message under 25 lines: the three journeys, categories, severities, and the verification results.
