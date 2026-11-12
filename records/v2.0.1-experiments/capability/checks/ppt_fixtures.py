#!/usr/bin/env python3
"""Hand-made decks that the rules of ppt_check.py must pass or fail (PLAN.md sections 5 and 12). No model is called.

usage: ppt_fixtures.py <work folder>     exits 0 when every expectation holds
"""
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

import ppt_check as pc

LONG = "這段說明文字刻意塞得太多，會超出文字框的下緣。"
# frame name -> the rules it must break (an empty set: it must break none)
EXPECT = {
    "ok": set(), "overflow": {"outside"}, "covered": {"coverage"}, "white": {"coverage"}, "clip": {"outside"},
    # onechar: one character of a 15-character line half covered. The frozen rule is 0.95 per frame and 0.9 per
    # matched word; a Chinese line is one word, so this case passes. It is kept here as a stated limit.
    "darkbox": set(), "onechar": set(), "rotated": {"rotated"}, "nowrap": {"outside"},
    "offpage": {"off-page"}, "transparent": set(), "dup1": set(), "dup2": set(), "dup-hidden": {"coverage"},
    "rot-overflow": {"rotated"}, "Title 1": set(), "Content Placeholder 2": set(), "shrunk": set(),
    "long-table": {"off-page"}, "good-table": set(), "grouped": set(), "vertical": {"rotated"},
    "wide-cell": set(), "strip": {"coverage"}, "cell-covered": {"coverage"}, "cell-white": {"coverage"},
    "picture-over": {"coverage"}, "veil": set(), "chart": set(), "para-big": set(), "para-small": set(),
    "chart-covered": {"coverage"}, "chart-small": set(), "chart-edge": {"off-page"}, "short-word": {"coverage"},
    "twin-a": set(), "twin-b": set(), "merged": set(), "dark-chart": set(), "chart-turned": {"rotated"},
    "chart-axis": {"rotated"}, "Title 9": set(), "corner-table": set(), "false-flags": set(), "colour-chart": set(),
    "page-number": set(), "page-mixed": set(), "page-covered": {"coverage"}, "card-chart": set(),
    "card-covered": {"coverage"}, "latin-table": set(), "narrow-table": set(), "chart-halfdark": {"coverage"},
    "chart-under": {"coverage"}, "chart-over": set(), "chart-idle": set(), "thin-line": set(), "thin-markers": set(),
}


def box(slide, name, x, y, w, h, text, size=20, color=None, wrap=True):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    shape.name = name
    shape.text_frame.word_wrap = wrap
    shape.text_frame.text = text
    run = shape.text_frame.paragraphs[0].runs[0]
    run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    return shape


def block(slide, name, x, y, w, h, rgb):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.name = name
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(*rgb)
    shape.line.fill.background()
    return shape


def build(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    s = prs.slides.add_slide(blank)                       # 1: the cases of the first prototype
    box(s, "ok", 0.5, 0.3, 6, 0.8, "正常的標題文字")
    box(s, "overflow", 0.5, 1.4, 3, 0.6, LONG * 2, 16)
    box(s, "covered", 7, 0.3, 5, 0.8, "下半部被色塊蓋住的文字", 28)
    block(s, "cover", 7, 0.62, 5, 0.6, (0x20, 0x40, 0x80))
    box(s, "white", 7, 2, 5, 0.8, "白字白底看不見", 24, RGBColor(0xFF, 0xFF, 0xFF))
    clip = box(s, "clip", 0.5, 4.5, 3, 0.6, LONG * 2, 16)
    clip.text_frame._txBody.find(qn("a:bodyPr")).set("vertOverflow", "clip")
    dark = block(s, "darkbox", 7, 4.5, 5, 1, (0x10, 0x10, 0x10))
    dark.text_frame.text = "深色底白字是正常的"
    run = dark.text_frame.paragraphs[0].runs[0]
    run.font.size, run.font.color.rgb = Pt(24), RGBColor(0xFF, 0xFF, 0xFF)

    s = prs.slides.add_slide(blank)                       # 2: one character, rotation, wrapping, page edge
    box(s, "onechar", 0.5, 0.3, 8, 0.7, "一行裡只有一個字的下半部被遮住", 24)
    block(s, "dot", 2.52, 0.62, 0.3, 0.25, (0xC0, 0x30, 0x30))
    box(s, "rotated", 9.5, 0.6, 3, 0.6, "旋轉的中文", 20).rotation = 30
    box(s, "nowrap", 0.5, 1.6, 2, 0.5, "沒有設定換行的長句子會一路往右邊跑出文字框", 18, wrap=False)
    box(s, "offpage", 11.3, 2.6, 3.5, 0.6, "這行字會超出頁面右邊的邊界被裁掉", 20, wrap=False)
    block(s, "tint", 0.5, 3.4, 5, 1, (0xDD, 0xEE, 0xFF))
    box(s, "transparent", 0.7, 3.6, 4.6, 0.6, "透明背景的文字框", 20)
    box(s, "dup1", 0.5, 5.0, 3, 0.6, "重複的文字", 20)
    box(s, "dup2", 4.5, 5.0, 3, 0.6, "重複的文字", 20)
    box(s, "dup-hidden", 8.5, 5.0, 3, 0.6, "重複的文字", 20)
    block(s, "lid", 8.4, 4.9, 3.2, 0.8, (0x33, 0x66, 0x33))
    box(s, "rot-overflow", 9.5, 6.0, 1.2, 0.5, "旋轉之後又塞太多字的文字框", 18).rotation = 90
    vertical = box(s, "vertical", 12.3, 3.6, 0.6, 3, "直排文字", 18)
    vertical.text_frame._txBody.find(qn("a:bodyPr")).set("vert", "eaVert")

    s = prs.slides.add_slide(prs.slide_layouts[1])        # 3: sizes inherited from the layout and the master
    s.shapes.title.text = "標題的字級來自母片"
    body = s.placeholders[1]
    body.text_frame.text = "第一點沒有自己設字級"
    body.text_frame.add_paragraph().text = "第二點也沒有"

    s = prs.slides.add_slide(prs.slide_layouts[1])        # 4: a placeholder the renderer shrinks to fit
    s.shapes.title.text = "自動縮小的內文"
    body = s.placeholders[1]
    body.name = "shrunk"
    body.text_frame.text = LONG * 3
    for _ in range(9):
        body.text_frame.add_paragraph().text = LONG * 3
    body.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    s = prs.slides.add_slide(blank)                       # 5: a table with too many rows for the page
    frame = s.shapes.add_table(34, 3, Inches(0.5), Inches(0.5), Inches(9), Inches(6))
    frame.name = "long-table"
    for r in range(34):
        for c in range(3):
            frame.table.cell(r, c).text = f"第{r + 1}列第{c + 1}欄"

    s = prs.slides.add_slide(blank)                       # 6: a table that fits, and a chart
    frame = s.shapes.add_table(4, 3, Inches(0.5), Inches(0.5), Inches(6), Inches(2))
    frame.name = "good-table"
    for r in range(4):
        for c in range(3):
            frame.table.cell(r, c).text = ("項目", "去年", "今年")[c] if r == 0 else f"{r}{c}0"
    data = CategoryChartData()
    data.categories = ["第一季", "第二季", "第三季", "第四季"]
    data.add_series("營收（百萬元）", (120, 135, 150, 180))
    chart = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(7), Inches(0.5), Inches(6), Inches(4), data)
    chart.name = "chart"
    chart.chart.has_title = True
    chart.chart.chart_title.text_frame.text = "各季營收"
    wide = s.shapes.add_table(2, 2, Inches(0.5), Inches(3.2), Inches(6), Inches(1))
    wide.name = "wide-cell"
    wide.table.cell(0, 0).text = "欄位"
    wide.table.cell(0, 1).text = "說明"
    wide.table.cell(1, 0).text = "備註"
    wide.table.cell(1, 1).text = "儲存格裡的字比較多的時候列會自己長高，這是正常的"

    s = prs.slides.add_slide(blank)                       # 7: text inside a group that is moved and scaled
    one = box(s, "grouped", 1, 1, 4, 0.8, "群組裡的文字", 20)
    two = block(s, "panel", 1, 2, 4, 1, (0xEE, 0xEE, 0xEE))
    group = s.shapes.add_group_shape([one, two])
    group.left, group.top = Inches(6), Inches(3)

    s = prs.slides.add_slide(blank)                       # 8: partly hidden strokes; text inside tables
    box(s, "strip", 0.5, 0.3, 8, 0.7, "每個字都被一條細線遮掉一部分筆畫", 24)
    block(s, "line", 0.5, 0.56, 8, 0.09, (0x20, 0x20, 0x90))
    frame = s.shapes.add_table(3, 3, Inches(0.5), Inches(1.5), Inches(6), Inches(1.5))
    frame.name = "cell-covered"
    for r in range(3):
        for c in range(3):
            frame.table.cell(r, c).text = f"儲存格{r + 1}{c + 1}"
    block(s, "patch", 2.5, 2.0, 2, 0.5, (0x90, 0x20, 0x20))
    frame = s.shapes.add_table(2, 2, Inches(7), Inches(1.5), Inches(5), Inches(1))
    frame.name = "cell-white"
    for r in range(2):
        for c in range(2):
            frame.table.cell(r, c).text = f"表格{r + 1}{c + 1}"
    cell = frame.table.cell(1, 1)
    cell.fill.solid()
    cell.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    cell.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    box(s, "picture-over", 0.5, 4, 5, 0.7, "被圖片蓋住的文字", 24)
    from PIL import Image as _Image
    import io as _io
    data = _io.BytesIO()
    _Image.new("RGB", (200, 60), (0x40, 0x80, 0x40)).save(data, "PNG")
    data.seek(0)
    s.shapes.add_picture(data, Inches(0.4), Inches(3.9), Inches(5.2), Inches(0.9))
    box(s, "veil", 7, 4, 5, 0.7, "半透明色塊底下的文字還看得見", 20)
    veil = block(s, "glass", 7, 4, 5, 0.7, (0xFF, 0xFF, 0xFF))
    fill = veil._element.find(".//" + qn("a:solidFill") + "/" + qn("a:srgbClr"))
    fill.append(fill.makeelement(qn("a:alpha"), {"val": "40000"}))

    s = prs.slides.add_slide(blank)                       # 9: sizes set on the paragraph; text inside charts
    big = box(s, "para-big", 0.5, 0.3, 6, 0.9, "段落層設定的大字級")
    big.text_frame.paragraphs[0].runs[0].font.size = None
    big.text_frame.paragraphs[0].font.size = Pt(36)
    small = box(s, "para-small", 0.5, 1.4, 6, 0.5, "段落層設定的小字級")
    small.text_frame.paragraphs[0].runs[0].font.size = None
    small.text_frame.paragraphs[0].font.size = Pt(9)
    data = CategoryChartData()
    data.categories = ["甲", "乙", "丙"]
    data.add_series("數量", (3, 5, 4))
    covered = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(2.2), Inches(5), Inches(3), data)
    covered.name = "chart-covered"
    covered.chart.has_title = True
    covered.chart.chart_title.text_frame.text = "被蓋住標題的圖表"
    block(s, "chart-lid", 0.5, 2.2, 5, 0.6, (0x30, 0x30, 0x70))
    tiny = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(6.5), Inches(0.3), Inches(5), Inches(3), data)
    tiny.name = "chart-small"
    tiny.chart.has_title = True
    tiny.chart.chart_title.text_frame.text = "字很小的圖表"
    tiny.chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(6)
    edge = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(10.5), Inches(4), Inches(5), Inches(3), data)
    edge.name = "chart-edge"
    box(s, "short-word", 0.5, 5.6, 4, 0.6, "短 詞 被遮住", 24)
    block(s, "short-lid", 0.5, 5.9, 0.42, 0.3, (0x70, 0x30, 0x30))

    s = prs.slides.add_slide(blank)                       # 10: two charts on one slide are edited one at a time
    for place, name in enumerate(("twin-a", "twin-b")):
        twin = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5 + 6.4 * place), Inches(1), Inches(6),
                                  Inches(4), data)
        twin.name = name

    s = prs.slides.add_slide(blank)                       # 11: merged cells; charts on dark ground and with turned text
    frame = s.shapes.add_table(3, 3, Inches(0.5), Inches(0.4), Inches(6), Inches(1.5))
    frame.name = "merged"
    frame.table.cell(0, 0).merge(frame.table.cell(0, 1))
    frame.table.cell(0, 0).text = "合併的兩欄"
    frame.table.cell(0, 2).text = "第三欄"
    for r in (1, 2):
        for c in range(3):
            frame.table.cell(r, c).text = f"格{r}{c}"
    block(s, "night", 0.3, 2.3, 6.4, 3.4, (0x10, 0x18, 0x30))
    dark = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(2.4), Inches(6), Inches(3.2), data)
    dark.name = "dark-chart"
    dark.chart.has_title = True
    dark.chart.chart_title.text_frame.text = "深色底上的白字圖表"
    dark.chart.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    dark.chart.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    turned = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(7), Inches(0.3), Inches(5.5), Inches(3), data)
    turned.name = "chart-turned"
    turned.chart.has_title = True
    turned.chart.chart_title.text_frame.text = "標題被轉了角度"
    turned.chart.chart_title.text_frame._txBody.find(qn("a:bodyPr")).set("rot", "1800000")
    axis = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(7), Inches(3.6), Inches(5.5), Inches(3), data)
    axis.name = "chart-axis"
    axis.chart.value_axis.has_title = True
    axis.chart.value_axis.axis_title.text_frame.text = "數量單位"

    s = prs.slides.add_slide(blank)                       # 12: empty corner cell, false merge flags, colour, fields
    frame = s.shapes.add_table(3, 3, Inches(0.5), Inches(0.4), Inches(6), Inches(1.5))
    frame.name = "corner-table"
    for r in range(3):
        for c in range(3):
            if (r, c) != (0, 0):
                frame.table.cell(r, c).text = f"值{r}{c}"
    frame = s.shapes.add_table(2, 2, Inches(7), Inches(0.4), Inches(5), Inches(1))
    frame.name = "false-flags"
    for r in range(2):
        for c in range(2):
            frame.table.cell(r, c).text = f"旗{r}{c}"
            frame.table.cell(r, c)._tc.set("hMerge", "0")
            frame.table.cell(r, c)._tc.set("vMerge", "0")
    colour = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(2.3), Inches(6), Inches(3.2), data)
    colour.name = "colour-chart"
    colour.chart.has_title = True
    colour.chart.chart_title.text_frame.text = "灰底上的紅字圖表"
    colour.chart.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
    colour.chart.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
    space = colour.chart._chartSpace
    from lxml import etree as _etree
    ground = _etree.fromstring('<c:spPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                               'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill>'
                               '<a:srgbClr val="808080"/></a:solidFill></c:spPr>')
    space.find(qn("c:chart")).addnext(ground)

    def field_box(name, x, y, before="", after="", tall=0.5):
        shape = box(s, name, x, y, 3, tall, "暫", 18)
        para = shape.text_frame.paragraphs[0]._p
        run = para.find(qn("a:r"))
        fld = _etree.fromstring('<a:fld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                                'id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr lang="en-US" '
                                'sz="1800"/><a:t>‹#›</a:t></a:fld>')
        run.addnext(fld)
        if before:
            run.find(qn("a:t")).text = before
        else:
            para.remove(run)
        if after:
            extra = _etree.SubElement(para, qn("a:r"))
            _etree.SubElement(extra, qn("a:rPr")).set("sz", "1800")
            _etree.SubElement(extra, qn("a:t")).text = after
            fld.addnext(extra)
        return shape

    field_box("page-number", 7, 2.3)
    mixed = field_box("page-mixed", 7, 3.1, "第", "頁", tall=1.1)
    mixed.text_frame.add_paragraph().text = "下一段是一般文字"
    field_box("page-covered", 7, 4.6, "第", "頁")
    block(s, "page-lid", 6.9, 4.5, 3.2, 0.7, (0x50, 0x20, 0x60))

    s = prs.slides.add_slide(blank)                       # 13: charts with a dark ground of their own; Latin headers
    def card(name, x, y):
        shape = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(5.5), Inches(3), data)
        shape.name = name
        shape.chart.has_title = True
        shape.chart.chart_title.text_frame.text = "深色卡片上的白字圖表"
        shape.chart.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shape.chart.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        fill = _etree.fromstring('<c:spPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                                 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill>'
                                 '<a:srgbClr val="202840"/></a:solidFill></c:spPr>')
        shape.chart._chartSpace.find(qn("c:chart")).addnext(fill)
        return shape
    card("card-chart", 0.5, 0.3)
    card("card-covered", 7, 0.3)
    block(s, "card-lid", 7, 0.3, 5.5, 0.7, (0xA0, 0x40, 0x20))
    frame = s.shapes.add_table(3, 3, Inches(0.5), Inches(3.8), Inches(8), Inches(1.5))
    frame.name = "latin-table"
    for c, head in enumerate(("Revenue 2024Q1 (NT$ thousand)", "Year-over-year growth %", "Gross margin 2023-2024")):
        frame.table.cell(0, c).text = head
        frame.table.cell(1, c).text = f"1,234,56{c}"
        frame.table.cell(2, c).text = f"Segment {c + 1} total"
    frame = s.shapes.add_table(3, 2, Inches(9), Inches(3.8), Inches(3.5), Inches(1.5))
    frame.name = "narrow-table"
    frame.table.columns[0].width, frame.table.columns[1].width = Inches(0.5), Inches(3)
    for r in range(3):
        frame.table.cell(r, 0).text = "#" if r == 0 else str(r)
        frame.table.cell(r, 1).text = "項目名稱" if r == 0 else f"第 {r} 項的內容"

    s = prs.slides.add_slide(blank)                       # 14: chart text against what lies right behind it
    block(s, "half-night", 0.5, 0.3, 2.75, 0.9, (0x00, 0x00, 0x00))        # behind the left half of the title
    half = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(0.3), Inches(5.5), Inches(3), data)
    half.name = "chart-halfdark"
    half.chart.has_title = True
    half.chart.chart_title.text_frame.text = "左半邊黑字落在黑底上的標題"
    under = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(7), Inches(0.3), Inches(5.5), Inches(3), data)
    under.name = "chart-under"
    under.chart.has_title = True
    under.chart.chart_title.text_frame.text = "被另一張圖表蓋住的標題"
    over = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(7), Inches(0.1), Inches(5.5), Inches(1.6), data)
    over.name = "chart-over"
    over.chart.has_title = True
    over.chart.chart_title.text_frame.text = "蓋在上面的圖表"
    lid = _etree.fromstring('<c:spPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill>'
                            '<a:srgbClr val="F4F4F4"/></a:solidFill></c:spPr>')
    over.chart._chartSpace.find(qn("c:chart")).addnext(lid)
    for place, (name, kind) in enumerate((("thin-line", XL_CHART_TYPE.LINE), ("thin-markers", XL_CHART_TYPE.LINE_MARKERS))):
        line = s.shapes.add_chart(kind, Inches(6.5 + 3.3 * place), Inches(3.8), Inches(3.2), Inches(3), data)
        line.name = name
        line.chart.has_legend = False
    idle = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(3.8), Inches(5.5), Inches(3), data)
    idle.name = "chart-idle"
    idle.chart.has_title = True
    idle.chart.chart_title.text_frame.text = "圖表文字都是十六點"
    idle.chart.font.size = Pt(16)
    idle.chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(16)
    idle.chart.has_legend = False
    # a size no shown text uses: the text properties of a deleted axis
    ghost = _etree.fromstring('<c:txPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                              'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:bodyPr/><a:lstStyle/>'
                              '<a:p><a:pPr><a:defRPr sz="1500"/></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr>')
    spare = idle.chart._chartSpace.find(".//" + qn("c:valAx"))
    spare.find(qn("c:delete")).set("val", "1")
    spare.find(qn("c:crossAx")).addprevious(ghost)

    layout = prs.slide_layouts[5]                         # 15: a size on the layout placeholder's own paragraph
    holder = [sh for sh in layout.placeholders if sh.placeholder_format.idx == 0][0]
    para = holder.text_frame.paragraphs[0]
    para._p.get_or_add_pPr().append(para._p.makeelement(qn("a:defRPr"), {"sz": "6000"}))
    s = prs.slides.add_slide(layout)
    s.shapes.title.text = "版面配置段落寫 60"
    s.shapes.title.name = "Title 9"
    prs.save(path)


def main():
    folder = os.path.abspath(sys.argv[1])
    os.makedirs(folder, exist_ok=True)
    deck_path = os.path.join(folder, "fixtures.pptx")
    build(deck_path)
    started = time.time()
    deck = pc.analyze(deck_path, os.path.join(folder, "work"))
    seconds = time.time() - started
    bad = []
    if deck.error:
        print("ERROR", deck.error)
        return 1
    broken = {}
    for failure in deck.failures:
        broken.setdefault(failure["frame"], set()).add(failure["rule"])
    frames = {f.name: f for f in pc.frames_in_order(deck)}
    for name, rules in EXPECT.items():
        frame = frames.get(name)
        if frame is None:
            bad.append(f"{name}: frame not found")
            continue
        got = broken.get(name, set())
        m = frame.metrics
        ok = (got == rules) if not rules else rules <= got
        print(f"{name:22s} ink={m.get('ink'):6} cov={m.get('coverage')} word={m.get('word_coverage')} "
              f"outside={m.get('outside')} off={m.get('off_page')} size={frame.size_min} "
              f"-> {sorted(got) or 'pass'} {'OK' if ok else 'WRONG, expected ' + str(sorted(rules) or 'pass')}")
        if not ok:
            bad.append(name)
    extra = set(broken) - set(EXPECT)
    if extra:
        bad.append(f"unexpected failures on {sorted(extra)}")
    sizes = {name: frames[name].size_min for name in ("Title 1", "Content Placeholder 2", "shrunk") if name in frames}
    print("sizes", sizes, "shrunk rendered", sorted(set(frames["shrunk"].rendered_sizes))[:3])
    if sizes.get("Title 1") != 44.0 or sizes.get("Content Placeholder 2") != 32.0:
        bad.append("inherited sizes are not 44 and 32")
    if not sizes.get("shrunk") or sizes["shrunk"] >= 31.5:
        bad.append("the shrunk placeholder is not reported below its nominal size")
    grouped = frames["grouped"].rect
    if grouped is None or abs(grouped[0] - 6 * 72) > 1 or abs(grouped[1] - 3 * 72) > 1:
        bad.append(f"group transform: {grouped}")
    slide6 = deck.slides[5]
    chart = slide6.charts[0]
    print("chart", chart.type, chart.categories, chart.series, chart.title, "editable", chart.editable,
          chart.edit_share, chart.edit_note, "size", chart.size_min)
    print("para sizes", frames["para-big"].size_min, frames["para-small"].size_min, "chart-small",
          frames["chart-small"].size_min, "twins", [(c.frame.name, c.editable, c.edit_share) for c in deck.slides[9].charts])
    if frames["para-big"].size_min != 36.0 or frames["para-small"].size_min != 9.0:
        bad.append("sizes set on the paragraph are not 36 and 9")
    if not frames["chart-small"].size_min or frames["chart-small"].size_min > 6.5:
        bad.append("the small chart title is not reported")
    if not all(c.editable for c in deck.slides[9].charts):
        bad.append("two charts on one slide are not both editable")
    print("layout paragraph 60:", frames["Title 9"].size_min, "rendered", sorted(set(frames["Title 9"].rendered_sizes)),
          "merged cells", [(round(b[0]), round(b[2])) for b, _p in frames["merged"].cells[:2]])
    if frames["Title 9"].size_min != 44.0:
        bad.append("a size on the layout placeholder's paragraph is not inherited by LibreOffice: 44 expected")
    if [(round(b[0]), round(b[2])) for b, _p in frames["merged"].cells[:2]] != [(36, 324), (324, 468)]:
        bad.append("column bands of merged cells")
    print("a chart with an unused 15-point setting and 16-point text:", frames["chart-idle"].size_min,
          frames["chart-idle"].stated_sizes, sorted(set(frames["chart-idle"].rendered_sizes)))
    thin = {c.frame.name: (c.editable, c.edit_share) for c in deck.slides[13].charts if c.frame.name.startswith("thin")}
    print("thin line charts, one value changed:", thin)
    if not all(found[0] for found in thin.values()) or len(thin) != 2:
        bad.append("a thin line chart is called not editable")
    if frames["chart-idle"].size_min != 16.0:
        bad.append("an unused size setting in a chart is taken for the size of its text")
    narrow = {t.frame.name: t.editable for t in deck.slides[12].tables}
    print("latin headers and a narrow first column:", narrow)
    if narrow != {"latin-table": True, "narrow-table": True}:
        bad.append("a table with Latin headers or a narrow first column is not editable")
    late = {t.frame.name: t.editable for t in deck.slides[11].tables}
    print("tables with an empty corner and with false merge flags:", late, "field frames:",
          [(n, frames[n].fields, frames[n].pieces) for n in ("page-number", "page-mixed")])
    if not all(late.values()) or len(late) != 2:
        bad.append("a table with an empty corner cell or false merge flags is not editable")
    if not frames["page-number"].fields or frames["page-mixed"].pieces != [["下一段是一般文字"]]:
        bad.append("fields")
    print("tables", [(t.frame.name, t.rows, t.cols, t.editable) for s in deck.slides for t in s.tables])
    if chart.type != "COLUMN_CLUSTERED" or chart.editable is not True or norm_title(chart) != "各季營收":
        bad.append("chart facts or round trip")
    if not all(t.editable for t in slide6.tables):
        bad.append("table round trip")
    if not slide6.has("各季營收") or not slide6.has("營收(百萬元)"):
        bad.append("chart text is not part of the slide text")
    for name, text in (("garbage.pptx", b"not a presentation"),):
        with open(os.path.join(folder, name), "wb") as handle:
            handle.write(text)
        if not pc.analyze(os.path.join(folder, name), os.path.join(folder, "work2")).error:
            bad.append("a file that is not a presentation was accepted")
    # a failure of the measuring is the machine's, not the deck's
    real_convert, check = pc.convert, os.path.join(folder, "check_ok.py")
    with open(check, "w", encoding="utf-8") as handle:
        handle.write("def check(deck):\n    return []\n")
    small = os.path.join(folder, "small.pptx")
    one = Presentation()
    box(one.slides.add_slide(one.slide_layouts[6]), "only", 0.5, 0.5, 5, 0.8, "一個文字框")
    one.save(small)
    pc.convert = lambda where, names, timeout=1200: ("no PDF for A.pptx" if "A.pptx" in names
                                                     else real_convert(where, names, timeout))
    variants_fail = pc.grade(small, check, os.path.join(folder, "infra1"))
    pc.convert = lambda where, names, timeout=1200: "the conversion to PDF timed out"
    all_fail = pc.grade(small, check, os.path.join(folder, "infra2"))
    def no_converter(where, names, timeout=1200):
        raise FileNotFoundError("soffice")
    pc.convert = no_converter
    missing = pc.grade(small, check, os.path.join(folder, "infra3"))
    pc.convert = lambda where, names, timeout=1200: ("no PDF for deck.pptx" if names != ["control.pptx"]
                                                     else real_convert(where, names, timeout))
    deck_fails = pc.grade(small, check, os.path.join(folder, "infra4"))
    pc.convert = lambda where, names, timeout=1200: (pc.TIMED_OUT if names != ["control.pptx"]
                                                     else real_convert(where, names, timeout))
    deck_times_out = pc.grade(small, check, os.path.join(folder, "infra6"))
    pc.convert = real_convert
    fine = pc.grade(small, check, os.path.join(folder, "infra5"))
    print("only the deck times out:", bool(deck_times_out["infra"]))
    if not deck_times_out["infra"]:
        bad.append("a timeout on the delivered file alone is held against the deck")
    print("measuring fails, deck converts alone:", bool(variants_fail["infra"]), "| every conversion fails:",
          bool(all_fail["infra"]), "| no converter:", bool(missing["infra"]), "| only the deck fails:",
          bool(deck_fails["infra"]), deck_fails["error"][:40], "| untouched:", fine["pass"], fine["infra"])
    if not (variants_fail["infra"] and all_fail["infra"] and missing["infra"]) or deck_fails["infra"] \
            or deck_fails["pass"] or variants_fail["pass"] or not fine["pass"]:
        bad.append("telling a machine failure from a deck that does not render")
    print(f"{len(pc.frames_in_order(deck))} frames, {len(deck.slides)} slides, {seconds:.1f}s")
    print("FAILED: " + "; ".join(bad) if bad else "all fixtures behave as expected")
    return 1 if bad else 0


def norm_title(chart):
    return pc.norm(chart.title or "")


if __name__ == "__main__":
    sys.exit(main())
