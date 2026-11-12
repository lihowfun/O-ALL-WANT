# Author brief: slide-deck tasks

You are writing evaluation tasks for agents that make PowerPoint decks. A user hands the agent a short request and
some source material and expects a finished `.pptx`. Each task is done in one agent session on a Linux machine with
no network. The machine has Python 3.10 with python-pptx 1.0.2 and Pillow, LibreOffice 7.3 (headless), Poppler,
Noto Sans CJK fonts and Node 24. The measure is whether the delivered deck meets every requirement the request
states. A program decides that; nobody looks at the deck.

The users write Traditional Chinese (Taiwan usage). The request, the source material and the text on the slides
are in Traditional Chinese.

Write 6 tasks, in the folders `t1` to `t6`.

## What the tasks are about

The requests are ordinary office work: turn a report, a meeting record, a product comparison, a survey result or a
budget into a deck of 5 to 10 slides. Each task leans on several of the things below, which are easy to get wrong
when a deck is produced by a script and never looked at:

- **Too much content for one slide.** The source has more than fits; the request states a limit per slide (for
  example at most 5 bullet points of at most 30 characters, or at most 8 table rows per slide) and the content has
  to be split over slides without losing any of it.
- **Long Chinese titles.** Titles of 25 to 40 characters, given in the request word for word, at a stated minimum
  size.
- **A table with many rows.** 12 to 30 rows of source data, as real table objects, with a stated minimum text size.
- **A chart that can be edited.** Built from numbers in the source: the request states the chart type, the
  categories, the series and the unit.
- **Stated minimum font sizes** for titles, body text and table text.

Every task uses at least three of the five. Over the six tasks each of the five appears at least three times.

## Rules

1. The request states every requirement the check relies on. A deck made correctly from the request and the source
   material passes. The check tests nothing that the request does not state. Nothing about looks, colours or taste.
2. Requirements are exact and checkable from the file and its rendering: the number of slides (exact or a range),
   the title of given slides, which facts and numbers appear on which slide, the shape and cell contents of
   tables, the type, categories, series values and unit of charts, minimum font sizes.
3. Every request states these standing requirements in its own words:
   - the slide size is 13.333 by 7.5 inches (16:9);
   - every slide has its title in the slide's title placeholder;
   - text is horizontal: no rotated and no vertical text, inside charts too (an axis title that runs up the side
     of a chart is rotated text; a unit belongs in the chart title or in a level axis title);
   - all text is fully visible: inside its own text box, inside the slide, and not covered by another object;
   - tables are real tables and charts are real charts whose data can be edited in PowerPoint, not pictures;
   - the deck is saved as `output.pptx` in the working directory.
4. The source material is plain text files in `inputs/` (Markdown, CSV or JSON). No pictures, no `.pptx`.
5. Aim for requests that a strong agent working quickly gets mostly right at the first attempt, but often not
   entirely. They are not trick questions.
6. A request reads as a colleague would write it: plain sentences, the requirements as a short list. It does not
   mention checks, tests, this brief or how the deck will be judged.
7. Tasks are independent of each other. No network, no clock, nothing to install.

## The check

`ppt_check.py` in this directory does the general part. Read its docstring. It opens the deck, renders it with
LibreOffice and applies these rules to every frame (a shape with text, a table, or a chart): `rotated`, `no-ink`,
`coverage`, `outside`, `off-page`, `unmatched`, `word-out`. Any broken rule fails the deck. You do not repeat them.

For each task you write `check.py` with one function:

```python
def check(deck):
    """Return a list of strings, one per requirement the deck does not meet. Empty list: all met."""
```

`deck` is what `ppt_check.analyze` returns. Use only these parts of it, and only the standard library besides:

- `deck.width`, `deck.height`: slide size in points (13.333 in = 960.0, 7.5 in = 540.0).
- `deck.slides`: list of slides in order. For a slide `s`:
  - `s.title`: the text of its title placeholder, normalized, or `None`.
  - `s.has(text)`: whether the normalized text occurs in the slide's text frames or chart texts. What a field
    shows (a slide number, a date) is not part of this; use `s.rendered` for it.
  - `s.rendered(text)`: whether it occurs in the rendered page.
  - `s.hidden`: the slide is hidden.
  - `s.pictures`: how many pictures the slide has.
  - `s.frames`: its text frames. For a frame `f`: `f.kind` (`"shape"` or `"table"`), `f.text` (normalized),
    `f.paragraphs` (normalized, one per paragraph that has text), `f.is_title`, `f.placeholder` (type or `None`),
    `f.size_min` and `f.size_max` (effective font size in points: inherited sizes are resolved, and a size the
    renderer shrank counts as shrunk), `f.rect` (x0, y0, x1, y1 in points).
  - `s.tables`: its tables. For a table `t`: `t.rows`, `t.cols`, `t.cells` (rows of normalized cell text),
    `t.frame` (the table's frame, with `size_min`), `t.editable` (a cell was changed, saved, reopened and the
    change showed in the rendering).
  - `s.charts`: its charts. For a chart `c`: `c.type` (python-pptx name such as `COLUMN_CLUSTERED`, `LINE`,
    `PIE`, `BAR_CLUSTERED`), `c.categories` (list of strings), `c.series` (list of `(name, [values])`), `c.title`,
    `c.axis_titles` (`{"category": ..., "value": ...}`), `c.texts` (every text in the chart), `c.number_formats`,
    `c.size_min` (the smallest font size of the chart's text as rendered, in whole points rounded down, or `None`
    when the chart shows no text), `c.editable` (a value was changed through python-pptx, saved, reopened and the
    drawing changed).
- `deck.find(text)`: 1-based numbers of the slides whose text contains it.

`check` has to answer for any deck at all, not only for decks that resemble yours: a deck with a single empty
slide, with twice as many slides as asked, with no table, with a chart that has no categories. It returns its list
and never raises: test for what is there before you index into it. A check that raises on some deck makes its task
unusable.

Normalized means NFKC with all white space removed; normalize your own strings the same way with
`import unicodedata` or compare through `s.has`. Compare numbers as numbers, with a tolerance where the source
has decimals.

## What to deliver for each task

In `_out/<task>/`:

- `prompt.md`: the request, exactly as the agent receives it.
- `inputs/`: the source material.
- `check.py`: as above.
- `build.py`: a script that writes the decks below into `_out/<task>/decks/` with python-pptx.
- `decks/reference.pptx`: a deck that meets every requirement.
- `decks/alt-1.pptx`, `decks/alt-2.pptx` (more are welcome): decks that also meet every requirement but are built
  differently from the reference and from each other: a different number of slides where the request allows a
  range, text boxes instead of body placeholders or the other way round, a different split of the content, other
  sizes above the minimum, a table split differently, another slide layout.
- Counterexamples, each made from the reference by breaking one thing, each of which must fail:
  - `decks/bad-overflow.pptx`: a text box holds more text than fits, so the text runs past the box.
  - `decks/bad-cut.pptx`: text or a table runs past the edge of the slide.
  - `decks/bad-covered.pptx`: an opaque shape lies over part of some text.
  - `decks/bad-duplicate.pptx`: a text box is copied to another place on its slide and the original is covered
    by an opaque shape, so the text is in the file twice but can be read once.
  - `decks/bad-rotated.pptx`: a text box with Chinese text is rotated.
  - `decks/bad-white.pptx`: some text is white on a white background.
  - `decks/bad-picture.pptx`: a table (or, in a task without a table, a chart) is replaced by a picture of it.
  - at least two more that break a requirement of this task's own, named `decks/bad-x-<what>.pptx`: a wrong
    number, a missing slide, a font below the minimum, a wrong chart type, content left out, and so on.
- `expect.json`: for every counterexample, the rules of which at least one must be broken, for example
  `{"bad-overflow.pptx": ["outside"], "bad-picture.pptx": ["task"], "bad-x-small-font.pptx": ["task"]}`. Rule names
  are those of `ppt_check.py`; `"task"` stands for your own `check.py`.

Check your work before you finish. This command grades one deck and prints the result as JSON (`"pass"`,
`"failures"` for the general rules, `"task_failures"` for yours):

```
python3 ppt_check.py grade _out/t1/decks/reference.pptx _out/t1/check.py /tmp/work-t1-ref
```

The reference and every alternative must pass. Every counterexample must fail on a rule you listed for it. A
delivery with no file, and a delivery that is just one of the input files renamed to `output.pptx`, must fail.
The rendering is LibreOffice's: where it wraps or places text differently from what you expected, the rendering
decides. Leave enough room in the reference and the alternatives that they pass with a clear margin.

A task that does not hold up under these checks is dropped, not repaired, so make sure each one does. When you
are done, leave `_out/` in place and remove your temporary files. Your final message is one line: the number of
tasks written.
