#!/usr/bin/env python3
"""ppt_check: mechanical checks of a .pptx deliverable (capability/PLAN.md section 5, PPT). No model is called.

A deck is opened with python-pptx, variant decks are written next to it and converted to PDF by LibreOffice in one
call, and everything else is read from those PDFs:

  A   the deck as delivered, followed by one copy of a slide per text frame with that frame's text made fully
      transparent, so that nothing moves
  B   one page per text frame holding only that frame on a white canvas enlarged by MARGIN_PT on every side: black
      text with no fill, no line and clipping off, its bullets white (bullets and list numbers are not measured)
  FK<n>, FW<n>  for chart n: its slide as delivered with the text of this one chart black (K) and white (W)
  IK<n>, IW<n>  for chart n: the chart alone on the enlarged canvas, its text black (K) and white (W)
  E*  one deck per chart and per table: only that object's slide, with one value of the chart or one cell of the
      table changed (a table: alone on its slide)

A frame is a shape with text, a table, or a chart. Rules, applied to every frame:
  rotated    the frame, a group around it or its text direction is rotated (the tasks say text is not rotated);
             a chart: a text setting with a rotation, an axis title on an upright axis that is not set level, or a
             rendered word that stands upright or slanted
  no-ink     a text frame's own page (B) shows no strokes at all
  coverage   of the frame's strokes, the share that is visible on the delivered slide is below COVER_FRAME, or
             below COVER_WORD inside one matched word box. A text frame: strokes are the pixels of B darker than
             INK_CORE; visible where the slide with and without the frame's text differ by more than VISIBLE in
             some channel. A chart: LibreOffice cannot hide a chart's text but colours it, so strokes are the
             pixels that differ (by INK_CORE or more) between the chart alone with black and with white text;
             visible where the delivered slide also differs between black and white text in this chart (nothing
             lies over the stroke) and the stroke's own colour is more than VISIBLE away from the mean colour of
             the pixels within GROUND_RADIUS that are not strokes
  outside    strokes lie more than OUT_TOL_PT outside the frame (a table may grow downwards, as its rows do)
  off-page   strokes lie outside the page
  unmatched  the frame's text is not found in the words of the rendered page as one run of whole words, in the
             order the page draws them, that no other frame has used (a table: each cell's text). A bullet or a
             list number drawn before a paragraph belongs to the run. A paragraph that holds a field (a slide
             number) is not matched, since only the renderer knows what it shows; its strokes are still measured
  word-out   a matched word box lies more than OUT_TOL_PT outside the frame (a table cell: outside its columns;
             a chart: outside the chart) or outside the page

A deck that opens but cannot be measured is told apart in three steps: is there disk space; does the converter turn
a control deck into a PDF here; does it turn the delivered file, alone, into a PDF. Only a delivered file that fails
where the control deck succeeds does not render and fails. Everything else is this module's or the machine's
failure (`infra`): the run is repeated and never counted against the deck.

The render is LibreOffice's, not PowerPoint's; results say so. Thresholds are frozen with the experiment.
"""
import copy
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

from lxml import etree
from PIL import Image, ImageChops, ImageFilter, ImageMath
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn

EMU_PT = 12700
DPI = 144
PX = DPI / 72.0          # pixels per point
MARGIN_PT = 144          # the canvas of B is larger by this on every side
INK_CORE = 128           # B, grayscale: darker than this is the core of a stroke
VISIBLE = 40             # A: a channel differing by more than this between "with" and "without" is visible
COVER_FRAME = 0.95
COVER_WORD = 0.90
WORD_MIN_INK = 12        # a word box with fewer stroke pixels than this is not judged on its own
OUT_TOL_PT = 2.0
PAGE_TOL_PT = 0.5
EDIT_MIN_SHARE = 0.001   # share of a chart's area outside its text that must change when a value is changed
                         # (a thin line chart changes about 0.3% of its area; 0.5% called such charts not editable)
SIZE_TOL = 1.5           # points: a rendered size this much below the size in the file counts as shrunk
                         # (pdftohtml reports whole points, rounded down: 44 is reported as 43)
PREVIEW_DPI = 50         # the pictures of the delivered slides that are kept as a description
MARK = "ZQ7XK"           # the text written into one cell of a table for the round trip
GROUND_RADIUS = 12       # pixels: a chart stroke is compared with the mean colour of what is not stroke this near
MIN_FREE = 256 * 1024 ** 2   # bytes: with less free space where the check works, a failure is the machine's
TIMED_OUT = "the conversion to PDF timed out"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
FILLS = ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")
NUMBERED = re.compile(r"\(?(?:[0-9]{1,3}|[A-Za-z]|[ivxIVX]{1,4})[.)、]")
THRESHOLDS = {"dpi": DPI, "margin_pt": MARGIN_PT, "ink_core": INK_CORE, "visible": VISIBLE,
              "cover_frame": COVER_FRAME, "cover_word": COVER_WORD, "word_min_ink": WORD_MIN_INK,
              "out_tol_pt": OUT_TOL_PT, "page_tol_pt": PAGE_TOL_PT, "edit_min_share": EDIT_MIN_SHARE,
              "size_tol": SIZE_TOL, "ground_radius": GROUND_RADIUS}


def norm(text):
    """NFKC, every kind of white space and zero-width character removed."""
    text = unicodedata.normalize("NFKC", text or "")
    return "".join(ch for ch in text if not ch.isspace() and unicodedata.category(ch) not in ("Cf", "Cc", "Zs"))


def local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def a(tag):
    return qn("a:" + tag)


# ---------------------------------------------------------------- the deck as the file states it

def xfrm_of(el):
    """(off x, off y, ext cx, ext cy, rotation in degrees, flipV) of a shape element in EMU, or None."""
    kind = local(el)
    holder = el.find(qn("p:xfrm")) if kind == "graphicFrame" else None
    if holder is None:
        props = el.find(qn("p:grpSpPr" if kind == "grpSp" else "p:spPr"))
        holder = props.find(a("xfrm")) if props is not None else None
    if holder is None:
        return None
    off, ext = holder.find(a("off")), holder.find(a("ext"))
    if off is None or ext is None:
        return None
    return (int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy")),
            int(holder.get("rot") or 0) / 60000.0, holder.get("flipV") in ("1", "true"))


def walk(tree, path=(), tf=(0.0, 0.0, 1.0, 1.0), rot=False):
    """(element, index path, transform to slide coordinates, inside a rotated group) for every shape under a shape
    tree, groups opened. The transform (ox, oy, sx, sy) maps a child coordinate c to o + c * s."""
    for index, el in enumerate(tree):
        kind = local(el)
        if kind == "grpSp":
            props = el.find(qn("p:grpSpPr"))
            holder = props.find(a("xfrm")) if props is not None else None
            inner, turned = tf, rot
            if holder is not None and holder.find(a("chExt")) is not None:
                off, ext = holder.find(a("off")), holder.find(a("ext"))
                choff, chext = holder.find(a("chOff")), holder.find(a("chExt"))
                sx = int(ext.get("cx")) / (int(chext.get("cx")) or 1)
                sy = int(ext.get("cy")) / (int(chext.get("cy")) or 1)
                ox = int(off.get("x")) - int(choff.get("x")) * sx
                oy = int(off.get("y")) - int(choff.get("y")) * sy
                inner = (tf[0] + ox * tf[2], tf[1] + oy * tf[3], sx * tf[2], sy * tf[3])
                turned = rot or bool(int(holder.get("rot") or 0)) or holder.get("flipV") in ("1", "true")
            yield from walk(el, path + (index,), inner, turned)
        elif kind in ("sp", "graphicFrame", "pic", "cxnSp"):
            yield el, path + (index,), tf, rot


def all_shapes(shapes):
    """Every shape proxy under a shape collection, groups opened."""
    for shape in shapes:
        yield shape
        if hasattr(shape, "shapes"):
            yield from all_shapes(shape.shapes)


def paragraphs_of(body):
    """The text of each paragraph under a text body: runs only (a field's stored text is not what is rendered)."""
    out = []
    for para in body.findall(a("p")):
        out.append("".join((run.find(a("t")).text or "") for run in para.findall(a("r"))
                           if run.find(a("t")) is not None))
    return out


def pieces_of(body):
    """The paragraphs of a text body as the pieces to find in the rendered words: each piece is a list of
    consecutive paragraphs (normalized, with text). A paragraph that holds a field (a slide number, a date) ends a
    piece and belongs to none: what a field shows is known only to the renderer, so such a paragraph is measured
    with the frame's strokes but not matched word for word."""
    pieces, current = [], []
    for para, text in zip(body.findall(a("p")), paragraphs_of(body)):
        if para.find(a("fld")) is not None:
            if current:
                pieces.append(current)
            current = []
        elif norm(text):
            current.append(norm(text))
    if current:
        pieces.append(current)
    return pieces


def has_field(body):
    return body.find(".//" + a("fld")) is not None


def level_size(style, level):
    """sz of a:lvl<level+1>pPr/a:defRPr under a list-style element, in points, or None."""
    if style is None:
        return None
    lvl = style.find(a(f"lvl{level + 1}pPr"))
    rpr = lvl.find(a("defRPr")) if lvl is not None else None
    return int(rpr.get("sz")) / 100.0 if rpr is not None and rpr.get("sz") else None


class Sizes:
    """Effective font size of a run, nearest setting first: the run, its paragraph's default run properties, the
    shape's list style, the layout and master placeholders it inherits from, the master's text styles, the
    presentation's default text style, then 18 points."""

    def __init__(self, prs):
        self.default = prs.part._element.find(qn("p:defaultTextStyle"))

    def chain(self, shape):
        """List styles to consult for a shape after its own, nearest first."""
        styles, proxy, master = [], shape, None
        if shape is not None and getattr(shape, "is_placeholder", False):
            kind = None
            try:
                kind = shape.placeholder_format.type
            except (AttributeError, ValueError, KeyError):
                pass
            for _depth in range(2):
                try:
                    proxy = proxy._base_placeholder
                except (AttributeError, ValueError, KeyError):
                    proxy = None
                if proxy is None:
                    break
                body = proxy._element.find(qn("p:txBody"))
                if body is not None:
                    styles.append(body.find(a("lstStyle")))
            try:
                master = shape.part.slide_layout.slide_master._element
            except AttributeError:
                master = None
            if master is not None:
                tx = master.find(qn("p:txStyles"))
                name = str(kind).split(".")[-1].split(" ")[0] if kind is not None else ""
                which = ("titleStyle" if name in ("TITLE", "CENTER_TITLE", "VERTICAL_TITLE") else
                         "bodyStyle" if name in ("BODY", "SUBTITLE", "OBJECT", "VERTICAL_BODY", "VERTICAL_OBJECT")
                         else "otherStyle")
                if tx is not None:
                    styles.append(tx.find(qn("p:" + which)))
        styles.append(self.default)
        return styles

    def runs(self, body, shape=None, cell=False):
        """[(text, size in points)] for every run with text under a text body."""
        own = body.find(a("lstStyle"))
        chain = [own] + ([self.default] if cell else self.chain(shape))
        props = body.find(a("bodyPr"))
        fit = props.find(a("normAutofit")) if props is not None else None
        scale = int(fit.get("fontScale")) / 100000.0 if fit is not None and fit.get("fontScale") else 1.0
        out = []
        for para in body.findall(a("p")):
            ppr = para.find(a("pPr"))
            level = int(ppr.get("lvl") or 0) if ppr is not None else 0
            default = ppr.find(a("defRPr")) if ppr is not None else None
            inherited = (int(default.get("sz")) / 100.0 if default is not None and default.get("sz") else
                         next((s for s in (level_size(style, level) for style in chain) if s), 18.0))
            for run in para.findall(a("r")) + para.findall(a("fld")):
                text = run.find(a("t")).text if run.find(a("t")) is not None else ""
                if not norm(text):
                    continue
                rpr = run.find(a("rPr"))
                size = int(rpr.get("sz")) / 100.0 if rpr is not None and rpr.get("sz") else inherited
                out.append((text, round(size * scale, 2)))
        return out


class Frame:
    """One container of text: a shape with text, a table, or a chart."""

    def __init__(self, slide, path, kind, name, rect, rotated):
        self.slide, self.path, self.kind, self.name = slide, path, kind, name
        self.rect = rect                    # (x0, y0, x1, y1) in points on the slide, or None when not stated
        self.rotated = rotated
        self.paragraphs = []                # normalized text of each paragraph that has text (not for a chart)
        self.pieces = []                    # a shape: lists of consecutive paragraphs to match (see pieces_of)
        self.fields = False                 # the frame holds a field
        self.cells = []                     # a table: [(column band rect, [paragraphs])] for each cell with text
        self.grid = []                      # a table: (left, right) of every grid column, in points
        self.runs = []                      # [(text, size)]
        self.is_title = False
        self.placeholder = None             # placeholder type name, or None
        self.rendered_sizes = []            # font sizes of the rendered text of this frame
        self.stated_sizes = []              # a chart: the font sizes its file states for text it shows
        self.metrics = {}
        self.words = []                     # matched word boxes [(x0, y0, x1, y1, bounds rect)]
        self.unmatched = []

    @property
    def text(self):
        return "".join(self.paragraphs)

    @property
    def size_min(self):
        """Smallest effective size of the frame's text: the file's, or the render's (whole points, rounded down)
        when the two differ by more than SIZE_TOL. A chart: the smallest rendered size of its text, or None when
        it shows none."""
        if self.kind == "chart":
            if not self.rendered_sizes:
                return None
            # The render reports whole points, rounded down from just under the true size: 16 is reported as 15,
            # 15 as 14. A stated size within a point above the reported one is the size of that text; when two
            # are, the larger (the smaller would have been reported a point lower). Otherwise the reported size.
            found = []
            for low in self.rendered_sizes:
                exact = [size for size in self.stated_sizes if low <= size <= low + 1.05]
                found.append(max(exact) if exact else low)
            return min(found)
        sizes = [size for _text, size in self.runs]
        low = min(sizes) if sizes else None
        if low is not None and self.rendered_sizes and abs(min(self.rendered_sizes) - low) > SIZE_TOL:
            return min(self.rendered_sizes)     # the file and the render disagree: the render decides
        return low

    @property
    def size_max(self):
        sizes = [size for _text, size in self.runs]
        return max(sizes) if sizes else None


class Table:
    def __init__(self, frame, rows):
        self.frame, self.cells = frame, rows          # rows of normalized cell text
        self.rows, self.cols = len(rows), max((len(r) for r in rows), default=0)
        self.editable, self.edit_note, self.edit_cell = None, "", None    # set by the round trip


class Chart:
    def __init__(self, frame):
        self.frame = frame
        self.slide, self.path, self.rect = frame.slide, frame.path, frame.rect
        self.type = None            # e.g. COLUMN_CLUSTERED
        self.categories, self.series = [], []          # [str], [(name, [values])]
        self.title, self.axis_titles, self.texts = None, {}, []
        self.number_formats = []
        self.editable, self.edit_note, self.edit_share, self.new_value = None, "", None, None

    @property
    def size_min(self):
        return self.frame.size_min


class Slide:
    def __init__(self, index):
        self.index = index
        self.frames, self.tables, self.charts, self.pictures = [], [], [], 0
        self.hidden = False
        self.words = []             # rendered words of the page, in drawing order [(text, x0, y0, x1, y1)]

    @property
    def title(self):
        """Normalized text of the title placeholder, or None."""
        for frame in self.frames:
            if frame.is_title:
                return frame.text
        return None

    @property
    def text(self):
        """All text of the slide's frames and chart texts, normalized and joined."""
        return "".join(f.text for f in self.frames) + "".join(norm(t) for c in self.charts for t in c.texts)

    def has(self, needle):
        return norm(needle) in self.text

    def rendered(self, needle):
        """Whether the normalized text occurs in the words of the rendered page."""
        return norm(needle) in "".join(norm(w[0]) for w in self.words)


class Deck:
    def __init__(self, path):
        self.path, self.slides, self.failures = path, [], []
        self.error, self.width, self.height = "", None, None
        self.stage = ""             # where an error arose: "open" (the deck itself) or "measure"
        self.render = "LibreOffice"

    def fail(self, slide, frame, rule, detail):
        self.failures.append({"slide": slide + 1, "frame": frame, "rule": rule, "detail": detail})

    def find(self, needle):
        """1-based numbers of the slides whose text contains the needle."""
        return [s.index + 1 for s in self.slides if s.has(needle)]


def stated_chart_sizes(root):
    """The font sizes a chart's file states for the text the chart shows: its title, its axis titles, the labels of
    every axis that is not deleted, its legend, and data labels that are switched on. Each takes the nearest
    setting: its own runs or text properties, then the chart space's. Text with no stated size is left out; the
    render speaks for it."""
    def stated(node):
        if node is not None:
            for props in node.iter(a("defRPr")):
                if props.get("sz"):
                    return int(props.get("sz")) / 100.0
        return None

    def on(node, name):
        flag = node.find(qn("c:" + name))
        return flag is not None and flag.get("val", "1") in ("1", "true")

    default = stated(root.find(qn("c:txPr")))
    sizes = set()

    def block(holder):
        rich = holder.find(qn("c:tx") + "/" + qn("c:rich"))
        if rich is None:
            sizes.add(stated(holder.find(qn("c:txPr"))) or default)
            return
        for para in rich.findall(a("p")):
            props = para.find(a("pPr"))
            base = stated(props) if props is not None else None
            for run in para.findall(a("r")):
                own = run.find(a("rPr"))
                sizes.add((int(own.get("sz")) / 100.0 if own is not None and own.get("sz") else base) or default)

    chart = root.find(qn("c:chart"))
    if chart is None:
        return []
    if chart.find(qn("c:title")) is not None:
        block(chart.find(qn("c:title")))
    plot = chart.find(qn("c:plotArea"))
    for axis in list(plot) if plot is not None else []:
        if local(axis) not in ("catAx", "valAx", "dateAx", "serAx") or on(axis, "delete"):
            continue
        labels = axis.find(qn("c:tickLblPos"))
        if labels is None or labels.get("val") != "none":     # an axis whose labels are switched off shows none
            sizes.add(stated(axis.find(qn("c:txPr"))) or default)
        if axis.find(qn("c:title")) is not None:
            block(axis.find(qn("c:title")))
    legend = chart.find(qn("c:legend"))
    if legend is not None:
        sizes.add(stated(legend.find(qn("c:txPr"))) or default)
        for entry in legend.findall(qn("c:legendEntry")):
            if not on(entry, "delete") and entry.find(qn("c:txPr")) is not None:
                sizes.add(stated(entry.find(qn("c:txPr"))) or default)
    for labels in plot.iter(qn("c:dLbls")) if plot is not None else []:
        if not on(labels, "delete") and any(on(labels, name) for name in (
                "showVal", "showCatName", "showSerName", "showPercent", "showLegendKey", "showBubbleSize")):
            sizes.add(stated(labels.find(qn("c:txPr"))) or default)
    return sorted(size for size in sizes if size)


def chart_facts(graphic, frame):
    chart = Chart(frame)
    try:
        obj = graphic.chart
    except Exception as error:  # a chart part that python-pptx cannot read
        chart.edit_note = f"unreadable chart: {type(error).__name__}"
        return chart
    try:
        chart.type = str(obj.chart_type).split(".")[-1].split(" ")[0]
    except Exception:
        chart.type = None
    try:
        plot = obj.plots[0]
        chart.categories = [str(c) for c in plot.categories]
        chart.series = [(s.name, [v for v in s.values]) for s in obj.series]
    except Exception:
        pass
    root = obj._chartSpace
    title = root.find(".//" + qn("c:chart") + "/" + qn("c:title"))
    if title is not None:
        chart.title = "".join(t.text or "" for t in title.iter(a("t")))
    for axis, name in (("catAx", "category"), ("valAx", "value"), ("dateAx", "category")):
        for node in root.iter(qn("c:" + axis)):
            holder = node.find(qn("c:title"))
            if holder is not None:
                chart.axis_titles.setdefault(name, "".join(t.text or "" for t in holder.iter(a("t"))))
    for props in root.iter(a("bodyPr")):
        if props.get("vert") not in (None, "horz") or int(props.get("rot") or 0) % 21600000:
            frame.rotated = True
    for axis in list(root.iter(qn("c:valAx"))) + list(root.iter(qn("c:catAx"))) + list(root.iter(qn("c:dateAx"))):
        side, holder = axis.find(qn("c:axPos")), axis.find(qn("c:title"))
        if holder is not None and side is not None and side.get("val") in ("l", "r"):
            props = holder.find(".//" + a("bodyPr"))
            if props is None or props.get("rot") is None or int(props.get("rot")) % 21600000:
                frame.rotated = True            # a title on an upright axis runs up the side unless set level
    chart.texts = [t.text for t in root.iter(a("t")) if t.text] + chart.categories + [s[0] or "" for s in chart.series]
    chart.number_formats = sorted({n.get("formatCode") for n in root.iter(qn("c:numFmt")) if n.get("formatCode")})
    frame.stated_sizes = stated_chart_sizes(root)
    return chart


def table_frame(el, frame, sizes):
    """Fill a table's frame: its rows of cell text, and for every cell with text the band of its columns."""
    table = el.find(".//" + a("tbl"))
    widths = [int(col.get("w") or 0) for col in table.findall(a("tblGrid") + "/" + a("gridCol"))]
    total = sum(widths) or 1
    if frame.rect is not None and widths:
        width = frame.rect[2] - frame.rect[0]
        frame.grid = [(frame.rect[0] + width * sum(widths[:k]) / total, frame.rect[0] + width * sum(widths[:k + 1]) / total)
                      for k in range(len(widths))]
    rows = []
    for row in table.findall(a("tr")):
        cells = []
        for column, cell in enumerate(row.findall(a("tc"))):   # every grid column has its own tc, merged or not
            span = int(cell.get("gridSpan") or 1)
            body = cell.find(a("txBody"))
            paras = [norm(p) for p in paragraphs_of(body)] if body is not None else []
            paras = [p for p in paras if p]
            cells.append("".join(paras))
            if body is not None and has_field(body):
                frame.fields = True
            if paras:
                frame.paragraphs += paras
                band = None
                if frame.grid:
                    band = (frame.grid[column][0], frame.rect[1], frame.grid[min(column + span, len(widths)) - 1][1],
                            float("inf"))
                for piece in pieces_of(body):
                    frame.cells.append((band, piece))
            if body is not None:
                frame.runs += sizes.runs(body, cell=True)
                props = body.find(a("bodyPr"))
                if props is not None and props.get("vert") not in (None, "horz"):
                    frame.rotated = True
        rows.append(cells)
    return Table(frame, rows)


def read_deck(path):
    """The deck as its file states it (no rendering). Returns (Deck, Presentation or None)."""
    deck = Deck(path)
    try:
        prs = Presentation(path)
    except Exception as error:
        deck.error, deck.stage = f"cannot be opened as a presentation: {type(error).__name__}", "open"
        return deck, None
    deck.width, deck.height = prs.slide_width / EMU_PT, prs.slide_height / EMU_PT
    sizes = Sizes(prs)
    for index, slide in enumerate(prs.slides):
        info = Slide(index)
        info.all_frames = []        # text frames, tables and charts in drawing order
        info.hidden = slide._element.get("show") in ("0", "false")
        proxies = {shape._element: shape for shape in all_shapes(slide.shapes)}
        for el, path_, tf, in_rotated in walk(slide.shapes._spTree):
            kind = local(el)
            if kind == "pic":
                info.pictures += 1
                continue
            geo = xfrm_of(el)
            proxy = proxies.get(el)
            if geo is None and proxy is not None:
                try:
                    if None not in (proxy.left, proxy.top, proxy.width, proxy.height):
                        geo = (proxy.left, proxy.top, proxy.width, proxy.height, proxy.rotation, False)
                except Exception:
                    geo = None
            rect = None
            if geo is not None:
                x0, y0 = tf[0] + geo[0] * tf[2], tf[1] + geo[1] * tf[3]
                rect = (x0 / EMU_PT, y0 / EMU_PT, (x0 + geo[2] * tf[2]) / EMU_PT, (y0 + geo[3] * tf[3]) / EMU_PT)
            turned = in_rotated or (geo is not None and (abs(geo[4]) > 1e-6 or geo[5]))
            name_el = el.find(".//" + qn("p:cNvPr"))
            name = name_el.get("name") if name_el is not None else ""
            if kind == "graphicFrame":
                if el.find(".//" + a("tbl")) is not None:
                    frame = Frame(index, path_, "table", name, rect, turned)
                    info.tables.append(table_frame(el, frame, sizes))
                    if frame.paragraphs or frame.fields:
                        info.frames.append(frame)
                        info.all_frames.append(frame)
                elif proxy is not None and getattr(proxy, "has_chart", False):
                    frame = Frame(index, path_, "chart", name, rect, turned)
                    info.charts.append(chart_facts(proxy, frame))
                    info.all_frames.append(frame)
                continue
            body = el.find(qn("p:txBody"))
            if body is None:
                continue
            paras = [norm(p) for p in paragraphs_of(body)]
            if not any(paras) and not has_field(body):
                continue
            frame = Frame(index, path_, "shape", name, rect, turned)
            frame.paragraphs = [p for p in paras if p]
            frame.pieces, frame.fields = pieces_of(body), has_field(body)
            frame.runs = sizes.runs(body, proxy)
            props = body.find(a("bodyPr"))
            if props is not None and (props.get("vert") not in (None, "horz") or int(props.get("rot") or 0)):
                frame.rotated = True
            holder = el.find(".//" + qn("p:nvPr") + "/" + qn("p:ph"))
            if holder is not None:
                frame.placeholder = holder.get("type") or "body"
                frame.is_title = frame.placeholder in ("title", "ctrTitle")
            info.frames.append(frame)
            info.all_frames.append(frame)
        deck.slides.append(info)
    return deck, prs


# ---------------------------------------------------------------- variant decks

def clone_slide(prs, source):
    """A copy of a slide appended to the presentation: its shapes, background and the parts it relates to."""
    target = prs.slides.add_slide(source.slide_layout)
    tree = target.shapes._spTree
    for el in list(tree):
        if local(el) not in ("nvGrpSpPr", "grpSpPr"):
            tree.remove(el)
    ids = {}
    for rel in source.part.rels.values():
        if rel.reltype in (RT.SLIDE_LAYOUT, RT.NOTES_SLIDE):
            continue
        if rel.is_external:
            ids[rel.rId] = target.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
        else:
            ids[rel.rId] = target.part.relate_to(rel.target_part, rel.reltype)

    def remap(node):
        for item in node.iter():
            if not isinstance(item.tag, str):
                continue
            for key, value in list(item.attrib.items()):
                if key.startswith("{" + R_NS + "}") and value in ids:
                    item.set(key, ids[value])
        return node

    for el in source.shapes._spTree:
        if local(el) not in ("nvGrpSpPr", "grpSpPr"):
            tree.append(remap(copy.deepcopy(el)))
    source_c, target_c = source._element.find(qn("p:cSld")), target._element.find(qn("p:cSld"))
    background = source_c.find(qn("p:bg"))
    if background is not None:
        target_c.insert(0, remap(copy.deepcopy(background)))
    if source._element.get("showMasterSp") is not None:
        target._element.set("showMasterSp", source._element.get("showMasterSp"))
    override = source._element.find(qn("p:clrMapOvr"))
    if override is not None:
        old = target._element.find(qn("p:clrMapOvr"))
        if old is not None:
            target._element.remove(old)
        target_c.addnext(copy.deepcopy(override))
    return target


def pin_numbers(slide, number):
    """Replace every slide-number field of a slide by a plain run that shows `number`. A copy of a slide stands at
    another place in its variant deck, where the field would show another number than on the delivered slide. The
    delivered slides of A are pinned too, so that every rendering that is compared shows the number the same way.
    (LibreOffice sets a line that holds a field slightly differently from one that holds the same digits as text;
    a frame with a slide number is therefore measured as if the number were typed.)"""
    for field in list(slide._element.iter(a("fld"))):
        if field.get("type") != "slidenum":
            continue
        run = etree.Element(a("r"))
        props = field.find(a("rPr"))
        if props is not None:
            run.append(copy.deepcopy(props))
        etree.SubElement(run, a("t")).text = str(number)
        field.getparent().replace(field, run)


def at_path(slide, path):
    node = slide.shapes._spTree
    for index in path:
        node = node[index]
    return node


def drop_slides(prs, keep):
    """Remove every slide of a presentation whose position is not in `keep`."""
    id_list = prs.slides._sldIdLst
    for place, entry in enumerate(list(id_list)):
        if place not in keep:
            prs.part.drop_rel(entry.rId)
            id_list.remove(entry)


def empty_text(el):
    """Take the text out of a frame: every run emptied, every field removed (a field would be drawn again from its
    type)."""
    for node in el.iter(a("t")):
        node.text = ""
    for field in list(el.iter(a("fld"))):
        field.getparent().remove(field)


TEXT_EXTRAS = FILLS + ("ln", "effectLst", "effectDag", "highlight", "hlinkClick", "hlinkMouseOver", "uFill",
                       "uFillTx", "uLn", "uLnTx")


def paint_text(body, fill):
    """Give every run of a text body the same fill and take away its outline, effects, highlight and link colour.
    The text keeps its place: nothing that decides the layout is touched."""
    for para in body.findall(a("p")):
        for item in list(para):
            if local(item) in ("r", "fld", "br") and item.find(a("rPr")) is None:
                item.insert(0, etree.SubElement(item, a("rPr")))
    for props in [n for n in body.iter() if local(n) in ("rPr", "endParaRPr", "defRPr")]:
        for child in list(props):
            if local(child) in TEXT_EXTRAS:
                props.remove(child)
        props.insert(0, etree.fromstring(fill))
        props.insert(0, etree.fromstring('<a:ln xmlns:a="%s"><a:noFill/></a:ln>' % A_NS))


def white_bullets(body):
    """Every bullet and list number of a text body white: on the white page of B they leave no strokes, so only the
    text itself is measured. A bullet stays where it is; switching it off would move the first line."""
    for para in body.findall(a("p")):
        props = para.find(a("pPr"))
        if props is None:
            props = etree.Element(a("pPr"))
            para.insert(0, props)
        for child in list(props):
            if local(child) in ("buClr", "buClrTx"):
                props.remove(child)
        colour = etree.Element(a("buClr"))
        etree.SubElement(colour, a("srgbClr")).set("val", "FFFFFF")
        place = sum(1 for child in props if local(child) in ("lnSpc", "spcBef", "spcAft"))
        props.insert(place, colour)


def black_text(body):
    """The text of a frame as B shows it: black, no outline, effect, highlight or link colour, bullets white,
    clipping off."""
    paint_text(body, '<a:solidFill xmlns:a="%s"><a:srgbClr val="000000"/></a:solidFill>' % A_NS)
    white_bullets(body)
    for props in body.iter(a("bodyPr")):
        props.set("vertOverflow", "overflow")
        props.set("horzOverflow", "overflow")


def hide_text(el):
    """The text of a frame made invisible without moving anything: every run fully transparent. This is the
    "without" page of A. Taking the text out instead would let a table row or a shape that fits its text shrink,
    and what lies below would move."""
    clear = '<a:solidFill xmlns:a="%s"><a:srgbClr val="000000"><a:alpha val="0"/></a:srgbClr></a:solidFill>' % A_NS
    for body in [n for n in el.iter() if local(n) == "txBody"]:
        paint_text(body, clear)


def plain_shape(el):
    """No fill, no line, no effect and no theme style on a shape."""
    props = el.find(qn("p:spPr"))
    if props is None:
        props = etree.SubElement(el, qn("p:spPr"))
        el.remove(props)
        el.insert(1, props)
    for child in list(props):
        if local(child) in FILLS + ("ln", "effectLst", "effectDag", "scene3d", "sp3d"):
            props.remove(child)
    etree.SubElement(props, a("noFill"))
    etree.SubElement(etree.SubElement(props, a("ln")), a("noFill"))
    style = el.find(qn("p:style"))
    if style is not None:
        el.remove(style)


def plain_table(table):
    """No fills and no borders on a table. Its style and the flags that switch on a header row or bands stay, since
    they also decide the weight of the text and so where its strokes fall; every cell overrides the style's fill
    and lines."""
    props = table.find(a("tblPr"))
    if props is not None:
        for child in list(props):
            if local(child) in FILLS + ("effectLst", "effectDag"):
                props.remove(child)
    for cell in table.iter(a("tc")):
        cell_props = cell.find(a("tcPr"))
        if cell_props is None:
            cell_props = etree.SubElement(cell, a("tcPr"))
        for child in list(cell_props):
            cell_props.remove(child)
        for side in ("lnL", "lnR", "lnT", "lnB"):
            etree.SubElement(etree.SubElement(cell_props, a(side)), a("noFill"))
        etree.SubElement(cell_props, a("noFill"))


def shift(el, rect_emu, margin):
    """Move a top-level shape by the margin; a placeholder that inherits its place gets it written out first."""
    kind = local(el)
    holder = el.find(qn("p:xfrm")) if kind == "graphicFrame" else None
    if holder is None:
        props = el.find(qn("p:grpSpPr" if kind == "grpSp" else "p:spPr"))
        if props is None:
            props = etree.SubElement(el, qn("p:spPr"))
            el.remove(props)
            el.insert(1, props)
        holder = props.find(a("xfrm"))
        if holder is None and rect_emu is not None:
            holder = etree.Element(a("xfrm"))
            off, ext = etree.SubElement(holder, a("off")), etree.SubElement(holder, a("ext"))
            off.set("x", str(rect_emu[0]))
            off.set("y", str(rect_emu[1]))
            ext.set("cx", str(rect_emu[2]))
            ext.set("cy", str(rect_emu[3]))
            props.insert(0, holder)
    if holder is None:
        return False
    off = holder.find(a("off"))
    off.set("x", str(int(off.get("x")) + margin))
    off.set("y", str(int(off.get("y")) + margin))
    return True


def isolate(slide, frame, margin, ground="FFFFFF"):
    """Leave only the frame on a cloned slide, on a plain ground with nothing of the master. A text frame becomes
    black text with nothing drawn around it; a chart stays as it is."""
    node = slide.shapes._spTree
    for depth, index in enumerate(frame.path):
        keep = node[index]
        for child in list(node):
            if child is not keep and local(child) not in ("nvGrpSpPr", "grpSpPr"):
                node.remove(child)
        if depth == 0:
            rect = None
            if frame.rect is not None and len(frame.path) == 1:
                rect = [int(round(v * EMU_PT)) for v in
                        (frame.rect[0], frame.rect[1], frame.rect[2] - frame.rect[0], frame.rect[3] - frame.rect[1])]
            shift(keep, rect, margin)
        node = keep
    if frame.kind == "table":
        table = node.find(".//" + a("tbl"))
        plain_table(table)
        for body in table.iter(a("txBody")):
            black_text(body)
    elif frame.kind == "shape":
        plain_shape(node)
        black_text(node.find(qn("p:txBody")))
    root = slide._element
    root.set("showMasterSp", "0")
    shapes = root.find(qn("p:cSld"))
    old = shapes.find(qn("p:bg"))
    if old is not None:
        shapes.remove(old)
    white = etree.fromstring(
        '<p:bg xmlns:p="%s" xmlns:a="%s"><p:bgPr><a:solidFill><a:srgbClr val="%s"/></a:solidFill>'
        '<a:effectLst/></p:bgPr></p:bg>' % (P_NS, A_NS, ground))
    shapes.insert(0, white)


def frames_in_order(deck):
    return [frame for slide in deck.slides for frame in slide.all_frames]


def swallowed(cell):
    """Whether a table cell is the continuation of a merged cell (the flag set to a true value)."""
    return cell.get("hMerge") in ("1", "true") or cell.get("vMerge") in ("1", "true")


def first_cell(table_el):
    """(row, column, columns spanned, cell) of the first cell of a table that is not swallowed by a merge. Takes the
    table or the frame that holds it."""
    table = table_el if local(table_el) == "tbl" else table_el.find(".//" + a("tbl"))
    for r, row in enumerate(table.findall(a("tr")) if table is not None else []):
        for c, cell in enumerate(row.findall(a("tc"))):
            if not swallowed(cell):
                return r, c, int(cell.get("gridSpan") or 1), cell
    return None


def edit_table(table_el):
    """Write MARK into the first cell of a table. Returns (row, column, span) of that cell, or None when the table
    has no cell to write into."""
    found = first_cell(table_el)
    target = found[3] if found else None
    body = target.find(a("txBody")) if target is not None else None
    if body is None:
        return None
    texts = list(body.iter(a("t")))
    if texts:
        empty_text(body)
        texts[0].text = MARK
    else:
        para = body.find(a("p"))
        if para is None:
            para = etree.SubElement(body, a("p"))
        etree.SubElement(etree.SubElement(para, a("r")), a("t")).text = MARK
        end = para.find(a("endParaRPr"))
        if end is not None:  # runs come before the paragraph's end properties
            para.remove(end)
            para.append(end)
    return found[:3]


def edit_chart(element, slide, chart):
    """Change the first value of the first series through python-pptx; returns a note when that is not possible."""
    proxy = next((s for s in all_shapes(slide.shapes) if s._element is element), None)
    if proxy is None or not getattr(proxy, "has_chart", False):
        return "chart object not reachable"
    try:
        obj = proxy.chart
        series = [(s.name, list(s.values)) for s in obj.series]
        if not series or not series[0][1]:
            return "chart has no values"
        numbers = [abs(v) for _n, values in series for v in values if isinstance(v, (int, float))]
        new = round((max(numbers) if numbers else 1.0) * 3 + 7, 2)
        kind = str(obj.chart_type)
        if "XY" in kind or "BUBBLE" in kind:
            return "scatter or bubble chart: the value change is not tried"
        data = CategoryChartData()
        data.categories = [str(c) for c in obj.plots[0].categories]
        for place, (name, values) in enumerate(series):
            values = [0 if v is None else v for v in values]
            if place == 0:
                values[0] = new
            data.add_series(name, values)
        obj.replace_data(data)
        chart.new_value = new
        return ""
    except Exception as error:
        return f"value change failed: {type(error).__name__}"


def write_variants(deck, folder):
    """Write A.pptx, B.pptx, the four chart decks and one E<n>.pptx per chart and table. Returns the pages of every
    frame (1-based), the edit decks as [(file name, 'chart' or 'table', object)] and the names of the chart decks."""
    frames = frames_in_order(deck)
    count = len(deck.slides)
    prs = Presentation(deck.path)
    first = int(prs.part._element.get("firstSlideNum") or 1)      # the number the first slide shows
    originals = list(prs.slides)
    for index, slide in enumerate(originals):
        slide._element.attrib.pop("show", None)
        pin_numbers(slide, first + index)     # the same plain number in every rendering that is compared
    texts = [frame for frame in frames if frame.kind != "chart"]
    charts = [frame for frame in frames if frame.kind == "chart"]
    for frame in texts:
        twin = clone_slide(prs, originals[frame.slide])
        twin._element.attrib.pop("show", None)
        hide_text(at_path(twin, frame.path))
    prs.save(os.path.join(folder, "A.pptx"))

    margin = MARGIN_PT * EMU_PT
    if texts:
        prs = Presentation(deck.path)
        originals = list(prs.slides)
        for index, slide in enumerate(originals):
            pin_numbers(slide, first + index)
        for frame in texts:
            isolate(clone_slide(prs, originals[frame.slide]), frame, margin)
        drop_slides(prs, set(range(count, count + len(texts))))
        prs.slide_width, prs.slide_height = prs.slide_width + 2 * margin, prs.slide_height + 2 * margin
        prs.save(os.path.join(folder, "B.pptx"))

    # Charts, one at a time: its slide as delivered (F) and the chart alone on the enlarged canvas (I), each with
    # the text of this one chart black (K) and white (W). What differs between K and W is this chart's text and
    # nothing else; no other chart is touched, so a chart lying over this one cannot stand in for its text.
    extra = []
    for number, frame in enumerate(charts):
        for letter, colour in (("K", "000000"), ("W", "FFFFFF")):
            prs = Presentation(deck.path)
            slide = prs.slides[frame.slide]
            slide._element.attrib.pop("show", None)
            pin_numbers(slide, first + frame.slide)
            element = at_path(slide, frame.path)
            shape = next((sh for sh in all_shapes(slide.shapes) if sh._element is element), None)
            try:
                paint_chart_text(shape.chart._chartSpace, colour)
            except Exception:
                pass                    # an unreadable chart keeps its text; it then shows no strokes
            drop_slides(prs, {frame.slide})
            prs.save(os.path.join(folder, f"F{letter}{number}.pptx"))
            isolate(prs.slides[0], frame, margin)
            prs.slide_width, prs.slide_height = prs.slide_width + 2 * margin, prs.slide_height + 2 * margin
            prs.save(os.path.join(folder, f"I{letter}{number}.pptx"))
            extra += [f"F{letter}{number}.pptx", f"I{letter}{number}.pptx"]

    edits = []
    for info in deck.slides:
        for kind, items in (("chart", info.charts), ("table", info.tables)):
            for item in items:
                prs = Presentation(deck.path)
                slide = prs.slides[info.index]
                slide._element.attrib.pop("show", None)
                pin_numbers(slide, first + info.index)
                element = at_path(slide, item.frame.path)
                if kind == "chart":
                    item.edit_note = item.edit_note or edit_chart(element, slide, item)
                    if item.edit_note:
                        continue
                else:
                    item.edit_cell = edit_table(element)
                    if item.edit_cell is None:
                        item.edit_note = "no cell to write into"
                        continue
                    tree = slide.shapes._spTree       # the table alone: a mark on the page can only be its own
                    node = tree
                    for index in item.frame.path:
                        keep = node[index]
                        for child in list(node):
                            if child is not keep and local(child) not in ("nvGrpSpPr", "grpSpPr"):
                                node.remove(child)
                        node = keep
                drop_slides(prs, {info.index})
                name = f"E{len(edits)}.pptx"
                prs.save(os.path.join(folder, name))
                edits.append((name, kind, item))
    # a text frame: its "without" page in A and its own page in B; a chart: the number of its four decks
    pages = {id(frame): (count + place + 1, place + 1) for place, frame in enumerate(texts)}
    pages.update({id(frame): (number, number) for number, frame in enumerate(charts)})
    return pages, edits, extra


# ---------------------------------------------------------------- rendering

def convert(folder, names, timeout=1200):
    """LibreOffice, one call for all files; returns an error text or ''. A converter that cannot be started raises."""
    profile = os.path.join(folder, "lo-profile")
    argv = ["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--norestore", "--convert-to", "pdf",
            "--outdir", folder] + [os.path.join(folder, name) for name in names]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env=dict(os.environ, HOME=os.environ.get("HOME", folder)))
    except subprocess.TimeoutExpired:
        return TIMED_OUT
    missing = [n for n in names if not os.path.exists(os.path.join(folder, n[:-5] + ".pdf"))]
    return f"no PDF for {', '.join(missing)}: {done.stderr[-200:]}" if missing else ""


def page_image(pdf, page, gray=False):
    argv = ["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page)] + (["-gray"] if gray else []) + [pdf]
    data = subprocess.run(argv, capture_output=True, timeout=300).stdout
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def page_words(pdf, first, last, folder):
    """Words of pages first..last in the order the page draws them: {page: [(text, x0, y0, x1, y1)]}."""
    out = os.path.join(folder, "words.html")
    subprocess.run(["pdftotext", "-raw", "-bbox", "-f", str(first), "-l", str(last), pdf, out], check=True,
                   timeout=300)
    root = etree.parse(out, etree.XMLParser(recover=True)).getroot()
    words = {}
    for index, page in enumerate(el for el in root.iter() if local(el) == "page"):
        words[first + index] = [(el.text or "", float(el.get("xMin")), float(el.get("yMin")), float(el.get("xMax")),
                                 float(el.get("yMax"))) for el in page.iter() if local(el) == "word" and el.get("xMin")]
    return words


def page_sizes(pdf, first, last):
    """Rendered text with its font size: {page: [(x0, y0, x1, y1, size)]} from pdftohtml."""
    done = subprocess.run(["pdftohtml", "-xml", "-i", "-stdout", "-zoom", "1", "-f", str(first), "-l", str(last), pdf],
                          capture_output=True, timeout=300)
    out = {}
    try:
        root = etree.fromstring(done.stdout, etree.XMLParser(recover=True))
    except etree.XMLSyntaxError:
        return out
    if root is None:
        return out
    fonts = {}
    for page in root.iter("page"):
        number = int(page.get("number"))
        for spec in page.iter("fontspec"):
            fonts[spec.get("id")] = float(spec.get("size"))
        for text in page.iter("text"):
            left, top = float(text.get("left")), float(text.get("top"))
            out.setdefault(number, []).append((left, top, left + float(text.get("width")),
                                               top + float(text.get("height")), fonts.get(text.get("font"))))
    return out


def count(mask):
    return mask.histogram()[255]


def pixel_box(rect, grow=0.0):
    return (int(round((rect[0] - grow) * PX)), int(round((rect[1] - grow) * PX)),
            int(round((rect[2] + grow) * PX)), int(round((rect[3] + grow) * PX)))


def changed_mask(one, two):
    """Pixels where two pages differ by more than VISIBLE in some channel."""
    if two.size != one.size:
        two = two.resize(one.size)
    bands = ImageChops.difference(one.convert("RGB"), two.convert("RGB")).split()
    differ = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
    return differ.point(lambda v: 255 if v > VISIBLE else 0)


def paint_chart_text(root, colour):
    """Give every text of a chart one colour: every text property in the chart gets this fill, and every part that
    carries text without properties of its own (the chart space, a title, an axis, a legend, data labels) gets
    them. Only the colour changes; sizes, fonts and places stay."""
    fill = '<a:solidFill xmlns:a="%s"><a:srgbClr val="%s"/></a:solidFill>' % (A_NS, colour)
    for props in [n for n in root.iter() if local(n) in ("defRPr", "rPr", "endParaRPr")]:
        for child in list(props):
            if local(child) in TEXT_EXTRAS:
                props.remove(child)
        props.insert(0, etree.fromstring(fill))
    plain = ('<c:txPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="%s"><a:bodyPr/>'
             '<a:lstStyle/><a:p><a:pPr><a:defRPr>%s</a:defRPr></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr>'
             % (A_NS, fill))
    before = {"chartSpace": ("externalData", "printSettings", "userShapes", "extLst"),
              "title": ("extLst",), "legend": ("extLst",),
              "catAx": ("crossAx",), "valAx": ("crossAx",), "dateAx": ("crossAx",), "serAx": ("crossAx",),
              "dLbls": ("dLblPos", "showLegendKey", "showVal", "showCatName", "showSerName", "showPercent",
                        "showBubbleSize", "separator", "showLeaderLines", "leaderLines", "extLst")}
    for part in [root] + [n for n in root.iter() if local(n) in before and n is not root]:
        kind = local(part)
        if part.find(qn("c:txPr")) is not None or (kind == "title" and part.find(qn("c:tx")) is not None):
            continue
        if kind == "dLbls" and part.find(qn("c:delete")) is not None:
            continue
        place = next((index for index, child in enumerate(part) if local(child) in before[kind]), len(part))
        part.insert(place, etree.fromstring(plain))


def far_from(image, colour, limit):
    """Mask of the pixels of an RGB image of which some channel is at least `limit` away from a colour."""
    bands = [band.point(lambda v, c=c: 255 if abs(v - c) >= limit else 0) for band, c in zip(image.split(), colour)]
    return ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])


def median_colour(image):
    """The median of each channel of an RGB image."""
    out = []
    for band in image.split():
        histogram = band.histogram()
        half, seen = sum(histogram) / 2.0, 0
        for value, times in enumerate(histogram):
            seen += times
            if seen >= half:
                out.append(value)
                break
    return out


def ground_near(image, strokes):
    """For every pixel of an RGB image, the mean colour of the pixels within GROUND_RADIUS that are not strokes, and
    how much of that neighbourhood is not stroke (0 to 255). This is what a stroke has to stand out from: the
    ground right next to it, not the ground of its whole word."""
    rest = ImageChops.invert(strokes)
    weight = rest.filter(ImageFilter.BoxBlur(GROUND_RADIUS))
    bands = []
    for band in image.split():
        kept = ImageChops.multiply(band, rest).filter(ImageFilter.BoxBlur(GROUND_RADIUS))
        # kept <= weight at every pixel, so the quotient stays within 0..255; where nothing nearby is ground it is 0
        bands.append(ImageMath.eval("convert((float(a) * 255.0) / (float(b) + 0.001), 'L')", a=kept, b=weight))
    return Image.merge("RGB", bands), weight


def differ_mask(one, two, limit):
    """Pixels of which some channel differs by at least `limit` between two RGB images of one size."""
    bands = ImageChops.difference(one, two).split()
    most = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
    return most.point(lambda v: 255 if v >= limit else 0)


def upright(text, x0, y0, x1, y1):
    """Whether a rendered word of a chart stands upright or slanted rather than level."""
    letters, width, height = len(norm(text)), x1 - x0, y1 - y0
    return (letters >= 2 and height > 1.5 * width) or (letters >= 4 and height > 0.9 * width)


def is_bullet(word):
    """A bullet glyph or a list number as LibreOffice draws it before a paragraph."""
    return (len(word) <= 3 and not any(ch.isalnum() for ch in word)) or NUMBERED.fullmatch(word) is not None


def match_run(words, used, text, starts, bounds):
    """The run of whole, unused words, consecutive in drawing order, that spells `text`; a bullet or list number
    may stand before the paragraphs that begin at `starts`. Among several runs the one nearest to `bounds` is
    taken. Returns the word indexes that carry the text, or None."""
    def distance(place):
        _t, x0, y0, x1, y1 = words[place][:5]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if bounds is None:
            return 0.0
        dx = max(bounds[0] - cx, 0, cx - bounds[2])
        dy = max(bounds[1] - cy, 0, cy - bounds[3])
        return (dx * dx + dy * dy) ** 0.5

    best = None
    for first in range(len(words)):
        position, place, taken, claimed = 0, first, [], []
        while position < len(text):
            if place >= len(words) or used[place]:
                taken = None
                break
            word = words[place][5]
            if text.startswith(word, position):
                position += len(word)
                taken.append(place)
            elif position in starts and is_bullet(word):
                pass
            else:
                taken = None
                break
            claimed.append(place)
            place += 1
        if not taken:
            continue
        cost = sum(distance(p) for p in taken) / len(taken)
        if best is None or cost < best[0]:
            best = (cost, taken, claimed)
    if best is None:
        return None
    for place in best[2]:
        used[place] = True
    return best[1]


def match_words(slide):
    """Give the text of every frame (a table: of every cell) its run of rendered words. Frames in drawing order."""
    words = [(*word, norm(word[0])) for word in slide.words]
    words = [word for word in words if word[5]]
    used = [False] * len(words)
    for frame in slide.all_frames:
        if frame.kind == "chart":
            continue
        pieces = frame.cells if frame.kind == "table" else [(frame.rect, piece) for piece in frame.pieces]
        for bounds, paragraphs in pieces:
            text, starts, position = "".join(paragraphs), set(), 0
            for para in paragraphs:
                starts.add(position)
                position += len(para)
            found = match_run(words, used, text, starts, bounds)
            if found is None:
                frame.unmatched.append(text)
                continue
            frame.words += [(*words[place][1:5], bounds) for place in found]


def measure(deck, frame, pdf_a, pdf_b, full, pages, folder):
    """Stroke and visibility figures of one frame; returns (strokes on the page, visible strokes) as images."""
    page_a, page_b = pages[id(frame)]
    width, height = full.size
    margin = int(round(MARGIN_PT * PX))
    page = (margin, margin, margin + width, margin + height)
    if frame.kind == "chart":
        # A chart's text cannot be hidden in LibreOffice, but it can be coloured. The chart alone with all its
        # text black and with all its text white differ exactly in the strokes of the text.
        black_alone = os.path.join(folder, f"IK{page_b}.pdf")
        drawn = [word for word in page_words(black_alone, 1, 1, folder).get(1, []) if norm(word[0])]
        frame.words = [(x0 - MARGIN_PT, y0 - MARGIN_PT, x1 - MARGIN_PT, y1 - MARGIN_PT, frame.rect)
                       for _text, x0, y0, x1, y1 in drawn]
        if any(upright(*word) for word in drawn):
            frame.rotated = True
        frame.rendered_sizes = [size for _x0, _y0, _x1, _y1, size in page_sizes(black_alone, 1, 1).get(1, []) if size]
        ink_all = differ_mask(page_image(black_alone, 1).convert("RGB"),
                              page_image(os.path.join(folder, f"IW{page_b}.pdf"), 1).convert("RGB"), INK_CORE)
        ink = ink_all.crop(page)
        # Visible on the delivered slide: the stroke is really drawn there (the slide with black and with white
        # text in this chart differ at it: nothing lies over it), and its own colour is more than VISIBLE away, in
        # some channel, from the ground right next to it (the mean colour of the nearby pixels that are not
        # strokes). A stroke with no ground nearby at all is judged against the nearest ground there is.
        drawn_there = differ_mask(page_image(os.path.join(folder, f"FK{page_a}.pdf"), 1).convert("RGB"),
                                  page_image(os.path.join(folder, f"FW{page_a}.pdf"), 1).convert("RGB"), INK_CORE)
        ground, weight = ground_near(full, ink)
        bands = ImageChops.difference(full, ground).split()
        apart = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
        stands_out = ImageChops.darker(apart.point(lambda v: 255 if v > VISIBLE else 0),
                                       weight.point(lambda v: 255 if v > 0 else 0))
        seen = ImageChops.darker(ImageChops.darker(ink, drawn_there), stands_out)
    else:
        ink_all = page_image(pdf_b, page_b, gray=True).point(lambda v: 255 if v < INK_CORE else 0)
        ink = ink_all.crop(page)
        seen = ImageChops.darker(ink, changed_mask(full, page_image(pdf_a, page_a)))
    total = count(ink_all)
    outside = None
    if frame.rect is not None:
        box = list(pixel_box(frame.rect, OUT_TOL_PT))
        box[2], box[3] = box[2] + 1, box[3] + 1
        if frame.kind == "table":
            box[3] = max(box[3], height + margin + 1)    # rows grow downwards; the page rule catches the rest
        outside = total - count(ink_all.crop((box[0] + margin, box[1] + margin, box[2] + margin, box[3] + margin)))
    visible = count(seen)
    frame.metrics = {"ink": total, "off_page": total - count(ink), "outside": outside,
                     "coverage_exact": visible / total if total else None,
                     "coverage": round(visible / total, 4) if total else None}
    return ink, seen


def word_coverage(frame, ink, seen):
    """Lowest share of visible strokes among the frame's matched word boxes that have enough strokes to judge.
    A chart's word with no strokes at all (text with no contrast in its own chart) counts as 0."""
    lowest = None
    for x0, y0, x1, y1, _bounds in frame.words:
        box = pixel_box((x0, y0, x1, y1))
        strokes = count(ink.crop(box))
        if strokes < WORD_MIN_INK and not (frame.kind == "chart" and strokes == 0):
            continue
        share = count(seen.crop(box)) / strokes if strokes else 0.0
        if lowest is None or share < lowest:
            lowest = share
    return lowest


def inside(rect, x, y, grow=0.0):
    return rect[0] - grow <= x <= rect[2] + grow and rect[1] - grow <= y <= rect[3] + grow


def round_trip(deck, slide, full, edits, folder):
    """Whether a changed value or cell survives saving and reopening and shows in the rendering of its own object."""
    for name, kind, item in edits:
        if item.frame.slide != slide.index:
            continue
        pdf = os.path.join(folder, name[:-5] + ".pdf")
        try:
            reopened = Presentation(os.path.join(folder, name))
            if kind == "table":     # alone on its slide: the path of the delivered slide no longer applies
                element = next(el for el in reopened.slides[0].shapes._spTree.iter()
                               if local(el) == "graphicFrame" and el.find(".//" + a("tbl")) is not None)
            else:
                element = at_path(reopened.slides[0], item.frame.path)
            after_words = page_words(pdf, 1, 1, folder).get(1, [])
            rect = item.frame.rect
            if kind == "table":
                row, column, span = item.edit_cell
                again = first_cell(element)
                kept = (again is not None and again[:2] == (row, column)
                        and norm("".join(t.text or "" for t in again[3].iter(a("t")))) == MARK)
                grid, band = item.frame.grid, None
                if grid:            # the columns of the cell that was written into
                    band = (grid[column][0], rect[1], grid[min(column + span, len(grid)) - 1][1], float("inf"))
                elif rect is not None:
                    band = (rect[0], rect[1], rect[2], float("inf"))
                # the words inside the cell's columns, in the order they are drawn: the mark may be broken
                # over lines in a narrow cell, so it is looked for in their text joined together
                shown = MARK in "".join(norm(text) for text, x0, y0, x1, y1 in after_words
                                        if band is None or inside(band, (x0 + x1) / 2, (y0 + y1) / 2, OUT_TOL_PT))
                item.editable = bool(kept and shown)
                continue
            proxy = next(s for s in all_shapes(reopened.slides[0].shapes) if s._element is element)
            kept = abs(list(proxy.chart.series)[0].values[0] - item.new_value) < 1e-6
            if rect is None:
                item.editable, item.edit_note = False, "the chart states no place"
                continue
            changed = changed_mask(full, page_image(pdf, 1))
            texts = [word[:4] for word in item.frame.words]
            texts += [(x0, y0, x1, y1) for text, x0, y0, x1, y1 in after_words
                      if inside(rect, (x0 + x1) / 2, (y0 + y1) / 2)]
            for word in texts:                      # the drawing itself must change, not only its labels
                changed.paste(0, pixel_box(word, 1.0))
            box = pixel_box(rect)
            area = max(1, (box[2] - box[0]) * (box[3] - box[1]))
            item.edit_share = round(count(changed.crop(box)) / area, 4)
            item.editable = bool(kept and count(changed.crop(box)) / area >= EDIT_MIN_SHARE)
        except (OSError, subprocess.SubprocessError):
            raise                   # the machine's failure, not the deck's: no verdict (see grade)
        except Exception as error:
            item.editable, item.edit_note = False, f"round trip failed: {type(error).__name__}"


def analyze(path, folder):
    """Read, render and measure a deck. Returns a Deck whose `failures` lists every broken rule."""
    deck, prs = read_deck(path)
    if prs is None:
        return deck
    if not deck.slides:
        deck.error, deck.stage = "the presentation has no slides", "open"
        return deck
    os.makedirs(folder, exist_ok=True)
    try:
        pages, edits, extra = write_variants(deck, folder)
    except Exception as error:
        deck.error = f"the variant decks cannot be written: {type(error).__name__}: {str(error)[:120]}"
        deck.stage = "measure"
        return deck
    frames = frames_in_order(deck)
    names = (["A.pptx"] + (["B.pptx"] if any(f.kind != "chart" for f in frames) else []) + extra
             + [name for name, _kind, _item in edits])
    problem = convert(folder, names)
    if problem:
        deck.error, deck.stage = problem, "measure"
        return deck
    pdf_a, pdf_b = os.path.join(folder, "A.pdf"), os.path.join(folder, "B.pdf")
    total = len(deck.slides)
    words = page_words(pdf_a, 1, total, folder)
    sizes = page_sizes(pdf_a, 1, total)
    previews = os.path.join(os.path.dirname(os.path.abspath(folder)), "render")
    os.makedirs(previews, exist_ok=True)
    subprocess.run(["pdftoppm", "-r", str(PREVIEW_DPI), "-png", "-f", "1", "-l", str(total), pdf_a,
                    os.path.join(previews, "slide")], capture_output=True, timeout=600)
    for slide in deck.slides:
        slide.words = words.get(slide.index + 1, [])
        full = page_image(pdf_a, slide.index + 1).convert("RGB")
        match_words(slide)
        for frame in slide.all_frames:
            label = frame.name or f"#{'.'.join(map(str, frame.path))}"
            ink, seen = measure(deck, frame, pdf_a, pdf_b, full, pages, folder)
            if frame.rotated:
                deck.fail(slide.index, label, "rotated", "the frame or its text is rotated")
            m = frame.metrics
            if not m["ink"]:
                if frame.kind != "chart":
                    deck.fail(slide.index, label, "no-ink", "the frame's text leaves no strokes when rendered")
                    continue
                if not frame.words:
                    continue                       # a chart that shows no text
            m["word_coverage"] = word_coverage(frame, ink, seen)
            if m["ink"] and m["coverage_exact"] < COVER_FRAME:
                deck.fail(slide.index, label, "coverage", f"{m['coverage_exact']:.4f} of the strokes are visible")
            elif m["word_coverage"] is not None and m["word_coverage"] < COVER_WORD:
                deck.fail(slide.index, label, "coverage", f"a word is {m['word_coverage']:.4f} visible")
            if m["outside"]:
                deck.fail(slide.index, label, "outside", f"{m['outside']} stroke pixels outside the frame")
            if m["off_page"]:
                deck.fail(slide.index, label, "off-page", f"{m['off_page']} stroke pixels outside the page")
            for text in frame.unmatched:
                deck.fail(slide.index, label, "unmatched", f"not found in the rendered page: {text[:30]}")
            for x0, y0, x1, y1, bounds in frame.words:
                if bounds is not None and (x0 < bounds[0] - OUT_TOL_PT or y0 < bounds[1] - OUT_TOL_PT
                                           or x1 > bounds[2] + OUT_TOL_PT or y1 > bounds[3] + OUT_TOL_PT):
                    deck.fail(slide.index, label, "word-out", "a rendered word lies outside the frame")
                    break
                if (x0 < -PAGE_TOL_PT or y0 < -PAGE_TOL_PT or x1 > deck.width + PAGE_TOL_PT
                        or y1 > deck.height + PAGE_TOL_PT):
                    deck.fail(slide.index, label, "word-out", "a rendered word lies outside the page")
                    break
            if frame.kind != "chart":
                for x0, y0, x1, y1, size in sizes.get(slide.index + 1, []):
                    if size and any(inside(word[:4], (x0 + x1) / 2, (y0 + y1) / 2, 1.0) for word in frame.words):
                        frame.rendered_sizes.append(size)
        round_trip(deck, slide, full, edits, folder)
    return deck


def summary(deck):
    """What a result row keeps of a deck."""
    return {"error": deck.error, "slides": len(deck.slides), "render": deck.render, "failures": deck.failures,
            "frames": [{"slide": f.slide + 1, "name": f.name, "kind": f.kind, "size_min": f.size_min,
                        **{k: v for k, v in f.metrics.items() if k != "coverage_exact"}}
                       for f in frames_in_order(deck)] if deck.slides and hasattr(deck.slides[0], "all_frames") else [],
            "charts": [{"slide": c.slide + 1, "type": c.type, "editable": c.editable, "note": c.edit_note,
                        "edit_share": c.edit_share, "size_min": c.size_min} for s in deck.slides for c in s.charts],
            "tables": [{"slide": s.index + 1, "rows": t.rows, "cols": t.cols, "editable": t.editable,
                        "note": t.edit_note} for s in deck.slides for t in s.tables]}


def low_space(folder):
    return shutil.disk_usage(folder).free < MIN_FREE


def why_unmeasured(path, folder):
    """Why a deck that opens could not be measured. Returns ("deck", text) when the deck itself does not render,
    ("infra", text) when the failure is the machine's or this module's. Three steps: is there disk space; does the
    converter turn a deck of this module's own making into a PDF here; does it turn the delivered file, alone,
    into a PDF. Only a delivered file for which the converter runs to its end and writes no PDF, where it writes
    one for the control deck, is held against the deck. A timeout, a converter that cannot be started and a full
    disk are never held against it."""
    if low_space(folder):
        return "infra", "no space left on a disk"
    alone = os.path.join(folder, "alone")
    os.makedirs(alone, exist_ok=True)
    try:
        control = Presentation()
        box = control.slides.add_slide(control.slide_layouts[6]).shapes.add_textbox(914400, 914400, 4572000, 914400)
        box.text_frame.text = "control"
        control.save(os.path.join(alone, "control.pptx"))
        problem = convert(alone, ["control.pptx"], timeout=300)
    except (OSError, subprocess.SubprocessError) as error:
        return "infra", f"the converter cannot be run: {type(error).__name__}"
    if problem:
        return "infra", "no space left on a disk" if low_space(folder) else f"the converter fails on a control deck: {problem}"
    try:
        shutil.copyfile(path, os.path.join(alone, "deck.pptx"))
        problem = convert(alone, ["deck.pptx"], timeout=600)
    except (OSError, subprocess.SubprocessError) as error:
        return "infra", f"the converter cannot be run: {type(error).__name__}"
    if low_space(folder):
        return "infra", "no space left on a disk"
    if problem == TIMED_OUT:        # a conversion that did not finish proves nothing about the deck
        return "infra", "the conversion of the delivered file alone timed out"
    if problem:
        return "deck", f"the converter turns a control deck into a PDF but not this one: {problem}"
    return "infra", "the deck renders by itself"


def grade(deck_path, check_path, folder):
    """Grade one deliverable against one task's check. The result passes when the deck opens and renders, no rule
    of this module is broken and the task's own check returns no failure. `infra` is set when the measuring
    failed for a reason that is not the deck's: the result is then no verdict on the deck."""
    result = {"pass": False, "deliverable": os.path.isfile(deck_path), "task_failures": [], "check_error": "",
              "infra": "", "thresholds": THRESHOLDS}
    if not result["deliverable"]:
        return dict(result, error="no deliverable", failures=[])
    deck, trouble = None, ""
    try:
        deck = analyze(deck_path, folder)
        if deck.error and deck.stage == "measure":
            trouble = deck.error
    except Exception as error:
        trouble = f"{type(error).__name__}: {str(error)[:160]}"
    if trouble:
        try:
            whose, why = why_unmeasured(deck_path, folder)
        except Exception as error:      # the classification itself broke: never held against the deck
            whose, why = "infra", f"{type(error).__name__}: {str(error)[:120]}"
        if whose == "deck":
            return dict(result, error=f"the deck does not render: {why} ({trouble})", failures=[])
        return dict(result, error=f"the deck could not be measured: {trouble}", infra=f"{why}; {trouble}",
                    failures=[])
    result.update(summary(deck))
    if deck.error:
        return result
    try:
        spec = importlib.util.spec_from_file_location("task_check", check_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        found = module.check(deck)
        result["task_failures"] = [str(item)[:300] for item in (found or [])]
    except Exception as error:
        result["check_error"] = f"{type(error).__name__}: {str(error)[:200]}"
        return result
    result["pass"] = not deck.failures and not result["task_failures"]
    return result


def main():
    if len(sys.argv) < 5 or sys.argv[1] != "grade":
        raise SystemExit("usage: ppt_check.py grade <deck.pptx> <check.py> <work folder> [<result.json>]")
    sys.dont_write_bytecode = True
    result = grade(sys.argv[2], sys.argv[3], sys.argv[4])
    text = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True)
    if len(sys.argv) > 5:
        with open(sys.argv[5], "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    shutil.rmtree(os.path.join(sys.argv[4], "lo-profile"), ignore_errors=True)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
