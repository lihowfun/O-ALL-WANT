---
name: read-discipline
description: "Extract-first, refuse-last. When the answer is literally in a file you were given, state it. 'INSUFFICIENT EVIDENCE' is for when no given file contains the answer — not for when phrasing feels ambiguous."
triggers: ["what does memory say", "find in the wiki", "answer from docs", "insufficient evidence", "do we have", "did we decide"]
requires:
  - the file(s) the user pointed you at (or the ones the router lane specifies)
outputs:
  - A fact answer when the file contains it, or
  - "INSUFFICIENT EVIDENCE: <what's missing>" when no given file contains it
---

# /read-discipline — Extract First, Refuse Last

> **Why this skill exists**: A fresh-context agent dogfood on 2026-04-21
> refused a question (`INSUFFICIENT EVIDENCE`) whose answer was literally
> in the file it had been given. That's the mirror failure of
> over-writing: **over-refusing**. This skill is the vocabulary that
> catches it. See `docs/archive/Inheritance_And_Promotion_Experiment_2026-04-21.md`.

## The rule, in one sentence

**If the answer is literally in a given file, extract it verbatim. Refuse only when no given file contains the answer.**

## Failure modes this prevents

| Failure | Example | Why it's bad |
|---------|---------|--------------|
| **Over-refuse** | "The memory says 8 skills pass, but the question asks 'as of 2026-04-21' — so INSUFFICIENT EVIDENCE" | Answer was in file; phrasing ambiguity is not absence of evidence |
| **Silent hedging** | "The file seems to suggest X" | If X is literally in the file, say so. If it isn't, don't say it at all |
| **Refuse-then-guess** | "Insufficient evidence — but my best guess is …" | Pick one: either you have the fact or you don't |

## Rules

### Rule 1: Verbatim extraction beats paraphrase

If the file says "7/7 PASS, 0 FAIL, 0 UNCERTAIN", answer with those exact numbers. Don't rephrase to "all criteria passed" — that loses information a future reader might need.

### Rule 2: Ambiguous phrasing → give the fact + flag the ambiguity

If the user asks "as of X date, how many Y?" and the file says "Y = 8 on that date":
- ✅ **Right**: "8, as recorded in file.md:L12. Note: the entry is dated 2026-04-21; if you meant strictly after that date, the file doesn't say."
- ❌ **Wrong**: "INSUFFICIENT EVIDENCE — no post-date figure given."

### Rule 3: Refuse means "no file contains this"

Use `INSUFFICIENT EVIDENCE: <what's missing>` **only** when:
- No file you were given contains the answer, AND
- You cannot derive it from what's in the files (e.g. basic arithmetic on given numbers is still extraction, not guessing).

### Rule 4: Cite where you extracted

Always pair the fact with a locator: `file.md:L<n>` or an exact quoted phrase. If the reader can't re-find your source in ≤10s, you've hedged.

## Steps

### Step 1: Re-read the question with "is this extractable?" in mind

Before answering, ask: would a different agent reading the same files agree the answer is / is not present? If yes → extract. If no → re-check; you may be pattern-matching on a surface similarity.

### Step 2: If extractable, give fact + cite

```
<fact, verbatim or minimally paraphrased>
Source: <file>:<line> — "<short quote if useful>"
```

### Step 3: If not extractable, refuse precisely

```
INSUFFICIENT EVIDENCE: <what's missing>.
Files checked: <list>.
Would need: <what file / section / measurement / source would answer this>.
```

Do **not** then volunteer a guess.

### Step 4: If ambiguous, extract + flag

Give the extractable fact. In a second sentence, name the ambiguity. Let the reader resolve, not you.

## When NOT to use this skill

- When the user explicitly asks for your opinion or a judgment call. Those aren't extraction tasks.
- When the task is exploratory ("what do you think of X?"). Refuse-or-extract is too binary.
- When you're writing, not reading. Write-side discipline is `classify-evidence`.

## Reference

- `docs/archive/Inheritance_And_Promotion_Experiment_2026-04-21.md` — the
  experiment that named over-refusal. Q3 there is the canonical example.
- `templates/.agents/skills/classify-evidence.md` — mirror skill on the
  write side. Together they cover evidence in both directions.
