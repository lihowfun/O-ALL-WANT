# Author brief B: units that span several sessions

You are writing evaluation units for coding agents. The repository in the current directory is `pallets/flask` at
commit 49943b5a. Its test suite runs with `python -m pytest`.

A unit is a short series of separate agent sessions on the same working copy. Each session starts with no memory of
the earlier conversation. Only the files on disk carry over, plus whatever the agent's own tooling chose to save. The
unit measures whether a decision the user stated in an earlier session is honoured by the work of the final session.

Write 8 units, two of each type, in this order: `explicit-1`, `explicit-2`, `passing-1`, `passing-2`,
`superseded-1`, `superseded-2`, `handoff-1`, `handoff-2`.

- **explicit** (2 sessions). Session 1 asks for a small change and also tells the agent, in so many words, to remember
  a decision for later work. Session 2 asks for the later work and refers to the decision without restating it.
- **passing** (2 sessions). As explicit, but session 1 only mentions the decision in passing. It does not ask the
  agent to remember or record anything.
- **superseded** (3 sessions). Session 1 mentions a decision in passing. Session 2 asks for a different small change
  and mentions in passing that the decision has been replaced by a new one. Session 3 asks for the work that depends
  on the decision, restating neither version. The hidden test expects the new one.
- **handoff** (2 sessions). Session 1 describes a two-part job with requirements for both parts and asks for part 1
  only. Session 2 asks to continue with part 2 and does not restate its requirements. Here the "decision" is the
  set of requirements for part 2.

## Rules

1. The decision is arbitrary, so that it cannot be guessed, inferred from the repository, or inferred from
   convention. Examples: a specific config key name with an unusual default value, the exact wording of an error
   message, a specific response header name, a specific numeric limit. Each unit uses at least two independent
   arbitrary elements.
2. The work asked for before the final session does not require writing the decision into the code, and an agent
   that follows those prompts has no reason to. The decision concerns the later work only.
3. Every session asks for a small, realistic change to Flask's source under `src/flask` (about 15 to 80 lines).
   Units are independent of each other.
4. Prompts read as a maintainer would write them: plain English, 3 to 10 sentences. No prompt mentions tests to
   write, hidden tests, memory tools, notes files, or this brief. The final prompt makes clear that an earlier
   decision applies ("use the key we agreed on", "as decided earlier") but does not restate it.
5. Apart from the decision, every public name, signature, config key and message that the hidden test relies on is
   stated in a prompt. An agent that had all the prompts of the unit in front of it could pass the hidden test from
   the prompts alone.
6. Hidden test: one pytest file with 4 to 8 test functions that use only public behaviour. They are plain
   module-level functions: no test classes or methods (a file that contains any is rejected). Two kinds, told apart
   by name:
   - `test_recall_*` (at least 2): passes only if the decision was honoured. With any other value in place of the
     decision's, it fails. This holds for each element of the decision on its own: if only one entry of `facts` is
     wrong and all the others are right, at least one recall test fails. An answer that gets one element right and
     another wrong must not pass every recall test.
   - `test_base_sK_*`, where K is a session number: checks that the work session K asked for is present at the end,
     and does not depend on the decision. It passes whatever values the decision takes. Every session before the
     final one has at least one. The final session may have some too.
7. `reference_patch`: a unified diff in `git diff` format against the base commit, touching only files under `src/`,
   that implements the work of all sessions. With it, the hidden test and the whole existing suite pass. Without it,
   the hidden test fails. Check this yourself before you write the unit down.
8. `facts` lists every literal string or value of the decision that a recall test depends on. Each entry is written
   exactly as it appears in an earlier prompt and in an added line of the reference patch, so that a plain text
   search finds it in both. In the patch it stands as a whole token: not directly preceded or followed by a letter,
   a digit or an underscore. It must not appear in the final prompt, and must not appear as a whole token anywhere
   in the repository at the base commit (lock files, documentation and tests included), so choose unusual values and
   check with a search first.
   No entry may be contained in another entry (of `facts` or `superseded_facts`): `TTL` and `TTL_729` cannot both
   be listed.
   For the superseded type, session 2 replaces every element of the decision, and `facts` holds the values of
   session 2. `superseded_facts` lists the values of session 1 in the same order and of the same length, so that
   entry i of one list is the old value of entry i of the other; every entry differs from its replacement. Putting
   back any one old value on its own, with the other entries left at their new values, must make at least one recall
   test fail, and putting back the old values (all of them, or any one of them) must leave every `test_base_*` passing.
   These checks are run mechanically: each entry is replaced in the reference patch on its own and the hidden test is
   run again. Every recall test must fail when all entries are wrong; at least one must fail when any single entry is
   wrong; every `test_base_*` must still pass in all of these cases.
9. No network, no dependence on the clock, no new dependencies.

## Output

Write one JSON file, `_out/units_B.json`:

```json
{"units": [{
  "id": "explicit-1",
  "type": "explicit",
  "sessions": ["prompt of session 1", "prompt of session 2"],
  "facts": ["each literal string or value of the final decision that the recall tests depend on"],
  "superseded_facts": ["superseded type only: the replaced values, in the same order"],
  "hidden_test": "the full text of the pytest file",
  "reference_patch": "the full diff"
}]}
```

When you are done, restore the working copy to the base commit (`git checkout -- . && git clean -fd -e _out -e .venv`)
and leave `_out/` in place. Your final message is one line: the number of units written.
