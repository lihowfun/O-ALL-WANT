# Author brief C: larger changes with many stated requirements

You are writing evaluation tasks for coding agents. The repository in the current directory is `pallets/flask` at
commit 49943b5a. Its test suite runs with `python -m pytest`.

Each task is done in one agent session. The tasks are larger or riskier changes, of the kind where a careful engineer
plans first and checks the result against the request before calling it done. The measure is how many of the stated
requirements the finished work meets.

Write 6 tasks in this order: `large-1`, `design-1`, `large-2`, `design-2`, `large-3`, `design-3`.

- **large**. A feature or refactor in `src/flask` whose correct implementation changes at least 300 lines of
  non-documentation code. The count is the added plus deleted lines of the reference patch in files that are not
  documentation: files under `docs/` and files ending in `.md`, `.markdown`, `.rst`, `.txt` or `.adoc` do not count,
  wherever they are.
- **design**. The prompt asks the agent to first write a short design note at `docs/designs/<name>.md` (the prompt
  gives the file name) and then implement it in the same session. The implementation is about 100 to 250 lines. The
  note is a new file: that path does not exist at the base commit.

## Rules

1. Each prompt states 8 to 12 distinct requirements. Include interactions with existing behaviour (blueprints and
   nested blueprints, async views, application and request contexts, error handlers, config, the CLI, the JSON
   provider, sessions and so on), edge cases, and backward compatibility.
2. The requirements are of the kind that is easy to overlook or to get subtly wrong. They are not trick questions:
   each is stated in the prompt without ambiguity, and each can be checked through public behaviour.
3. Every public name, signature, config key, default and message that the hidden test relies on is stated in the
   prompt. A correct implementation written from the prompt alone passes the hidden test. The hidden test checks
   nothing that the prompt does not state.
4. Aim for tasks on which a strong agent working quickly gets most of the requirements right at the first attempt,
   but not all of them.
5. Prompts read as a maintainer would write an issue: plain English. No prompt mentions tests to write, hidden
   tests, review, or this brief.
6. Requirements and tests. Number the requirements r01, r02 and so on. `requirements` maps each number to the
   sentence of the prompt that states it, copied exactly, so that a plain text search finds it in the prompt. The
   hidden test is one pytest file of plain module-level test functions (no test classes or methods; a file that
   contains any is rejected), each named `test_rNN_*` after the one
   requirement it checks. A requirement has one function, or a few when it needs several cases; it counts as met
   only when all of its functions pass. Every requirement has at least one function, every function belongs to a
   listed requirement, and the file has at most 20 functions.
7. `reference_patch`: a unified diff in `git diff` format against the base commit that meets every requirement. It
   touches only files under `src/`; a design task's patch also creates the design note, as a new file with content,
   at the path its prompt names, and nothing else outside `src/`. With the patch, the hidden test and the whole existing suite pass. Without it,
   the hidden test fails. Check this yourself before you write the task down.
8. Tasks are independent of each other. No network, no dependence on the clock, no new dependencies.

## Output

Write one JSON file, `_out/units_C.json`:

```json
{"units": [{
  "id": "large-1",
  "type": "large",
  "sessions": ["the prompt"],
  "requirements": {"r01": "the sentence of the prompt that states requirement 1, copied exactly"},
  "hidden_test": "the full text of the pytest file",
  "reference_patch": "the full diff"
}]}
```

When you are done, restore the working copy to the base commit (`git checkout -- . && git clean -fd -e _out -e .venv`)
and leave `_out/` in place. Your final message is one line: the number of tasks written.
