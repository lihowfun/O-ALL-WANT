"""Prototype of PLAN v5 section 5 'visible in full': isolated-frame ink mask vs full-slide visible mask."""
import copy, os, subprocess, sys
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

W = os.path.dirname(os.path.abspath(__file__))
MARGIN = Inches(2)

def fixture(path):
    prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    s = prs.slides.add_slide(prs.slide_layouts[6])
    def box(name, x, y, w, h, text, size=20, color=None):
        b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); b.name = name
        b.text_frame.word_wrap = True; b.text_frame.text = text
        r = b.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(size)
        if color: r.font.color.rgb = color
        return b
    box("ok", 0.5, 0.3, 6, 0.8, "正常的標題文字")
    box("overflow", 0.5, 1.4, 3, 0.6, "這段說明文字刻意塞得太多，會超出文字框的下緣。" * 2, 16)
    box("covered", 7, 0.3, 5, 0.8, "下半部被色塊蓋住的文字", 28)
    rect = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(7), Inches(0.62), Inches(5), Inches(0.6)); rect.name = "cover"
    rect.fill.solid(); rect.fill.fore_color.rgb = RGBColor(0x20, 0x40, 0x80); rect.line.fill.background()
    box("white", 7, 2, 5, 0.8, "白字白底看不見", 24, RGBColor(0xFF, 0xFF, 0xFF))
    c = box("clip", 0.5, 4.5, 3, 0.6, "設成裁切又塞太多字的文字框，下面幾行會被切掉。" * 2, 16)
    c.text_frame._txBody.find(qn("a:bodyPr")).set("vertOverflow", "clip")
    dark = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(7), Inches(4.5), Inches(5), Inches(1)); dark.name = "darkbox"
    dark.fill.solid(); dark.fill.fore_color.rgb = RGBColor(0x10, 0x10, 0x10); dark.line.fill.background()
    dark.text_frame.text = "深色底白字是正常的"; dr = dark.text_frame.paragraphs[0].runs[0]; dr.font.size = Pt(24); dr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    prs.save(path)

def text_shapes(slide):
    return [sh for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text.strip()]

def variant(src, out, idx, kind):
    prs = Presentation(src)
    prs.slide_width += 2 * MARGIN; prs.slide_height += 2 * MARGIN
    slide = prs.slides[0]
    for sh in slide.shapes:
        sh.left += MARGIN; sh.top += MARGIN
    target = text_shapes(slide)[idx]
    if kind.startswith("iso"):
        for sh in list(slide.shapes):
            if sh.shape_id != target.shape_id:
                sh._element.getparent().remove(sh._element)
        body = target.text_frame._txBody.find(qn("a:bodyPr"))
        body.set("vertOverflow", "overflow"); body.set("horzOverflow", "overflow")
        sp = target._element.spPr if hasattr(target._element, "spPr") else None
        if hasattr(target, "fill"):
            target.fill.background()
        if hasattr(target, "line"):
            target.line.fill.background()
        for p in target.text_frame.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0, 0, 0)
        slide.background.fill.solid(); slide.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    if kind.endswith("minus"):
        for p in target.text_frame.paragraphs:
            for r in p.runs:
                r.text = ""
    prs.save(out)
    return target

def pgm(path):
    data = open(path, "rb").read()
    parts = data.split(b"\n", 3)
    w, h = map(int, parts[1].split()); return w, h, parts[3]

def main():
    src = os.path.join(W, "fixture.pptx"); fixture(src)
    prs = Presentation(src); shapes = text_shapes(prs.slides[0])
    files, meta = [], []
    for i, sh in enumerate(shapes):
        for kind in ("full", "full_minus", "iso", "iso_minus"):
            out = os.path.join(W, f"v_{i}_{kind}.pptx"); variant(src, out, i, kind); files.append(out)
        meta.append(sh)
    subprocess.run(["soffice", f"-env:UserInstallation=file://{W}/lo-profile", "--headless", "--convert-to", "pdf", "--outdir", W] + files,
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in files:
        base = f[:-5]
        subprocess.run(["pdftoppm", "-r", "72", "-gray", "-singlefile", base + ".pdf", base], check=True)
    m = int(MARGIN / 12700)
    for i, sh in enumerate(meta):
        img = {k: pgm(os.path.join(W, f"v_{i}_{k}.pgm")) for k in ("full", "full_minus", "iso", "iso_minus")}
        w, h, _ = img["full"]
        ink = [j for j, (a, b) in enumerate(zip(img["iso"][2], img["iso_minus"][2])) if b - a >= 128]  # stroke core: glyph covers half the pixel or more
        vis = set(j for j, (a, b) in enumerate(zip(img["full"][2], img["full_minus"][2])) if abs(a - b) > 40)
        cov = sum(1 for j in ink if j in vis) / len(ink) if ink else float("nan")
        x0, y0 = int(sh.left / 12700) + m - 2, int(sh.top / 12700) + m - 2
        x1, y1 = x0 + int(sh.width / 12700) + 4, y0 + int(sh.height / 12700) + 4
        outside = sum(1 for j in ink if not (x0 <= j % w <= x1 and y0 <= j // w <= y1))
        offpage = sum(1 for j in ink if not (m <= j % w < w - m and m <= j // w < h - m))
        verdict = "PASS" if ink and cov >= 0.95 and outside == 0 and offpage == 0 else "FAIL"
        print(f"{sh.name:9s} ink={len(ink):6d} coverage={cov:5.3f} outside_frame={outside:5d} off_page={offpage:4d} -> {verdict}")

main()
