from fpdf import FPDF
def clean(s):
    s = s.replace("\u2014", "-").replace("\u2013", "-").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2026", "...")
    out = []
    for w in s.split(" "):
        while len(w) > 50:
            out.append(w[:50])
            w = w[50:]
        out.append(w)
    return " ".join(out)
def cell(pdf, h, text, style=None):
    if style:
        pdf.set_font("Helvetica", style, h)
    pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
pdf = FPDF(format="A4", unit="mm")
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()
pdf.set_font("Helvetica", "B", 16)
pdf.multi_cell(0, 8, "CS3081 Mini Project - Report", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
pdf.set_font("Helvetica", "", 10)
for line in open("report/report.md", encoding="utf-8"):
    line = clean(line.rstrip("\n"))
    if line.startswith("# "):
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, line[2:], new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
    elif line.startswith("## "):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, line[3:], new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
    elif line.startswith("- ") or line.startswith("* "):
        pdf.multi_cell(0, 6, "- " + line[2:], new_x="LMARGIN", new_y="NEXT")
    elif line.strip() == "":
        pdf.ln(2)
    else:
        pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
pdf.output("report/report.pdf")
print("pages:", pdf.pages_count)
