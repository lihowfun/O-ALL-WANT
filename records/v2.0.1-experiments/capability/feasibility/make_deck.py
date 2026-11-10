from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
s = prs.slides.add_slide(prs.slide_layouts[6])
ok = s.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(6), Inches(1)); ok.text_frame.text = "季度營收摘要"
ok.text_frame.paragraphs[0].runs[0].font.size = Pt(28)
over = s.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(3), Inches(0.6)); over.text_frame.word_wrap = True
over.text_frame.text = "這是一段刻意塞太多字的說明文字，用來測試文字是否會超出文字框的範圍，讓檢查程式能夠抓到溢出的情況。" * 2
over.text_frame.paragraphs[0].runs[0].font.size = Pt(18)
rows = 6; t = s.shapes.add_table(rows, 3, Inches(7), Inches(1.5), Inches(5.5), Inches(3)).table
for r in range(rows):
    for c in range(3): t.cell(r, c).text = f"r{r}c{c}" if r else ["地區", "營收", "成長"][c]
cd = CategoryChartData(); cd.categories = ["Q1", "Q2", "Q3", "Q4"]; cd.add_series("營收", (12.5, 14.0, 13.2, 15.8))
s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(3), Inches(6), Inches(4), cd)
prs.save("deck.pptx")
# edit-reopen
p2 = Presentation("deck.pptx"); sl = p2.slides[0]
tbl = [sh for sh in sl.shapes if sh.has_table][0].table; tbl.cell(1, 1).text = "EDITED-777"
ch = [sh for sh in sl.shapes if sh.has_chart][0].chart
print("chart type", ch.chart_type, "values", list(ch.plots[0].series[0].values), "cats", list(ch.plots[0].categories))
p2.save("deck_edited.pptx"); print("saved")
