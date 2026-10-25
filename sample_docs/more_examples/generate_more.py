#!/usr/bin/env python3
"""Generate four extra SYNTHETIC demo scenarios (PDF only, no test harness).

  a_all_clear/            everything matches -> Muni should stay quiet
  b_overaward_loan/       aid above cost of attendance + a loan offer that disagrees
  c_study_abroad_choice/  two semester-abroad quotes (one in EUR) + a Spring bill
  d_missing_scholarship/  a scholarship that never reached the bill; past-due balance

All people, schools and amounts are fictional. Every page carries a "synthetic" footer.
Requires only reportlab. Totals are asserted, so a typo fails the script.
"""

from __future__ import annotations

from decimal import Decimal as D
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent
UNIVERSITY = "Alder Ridge University"
FOOTER = "SYNTHETIC DOCUMENT - FOR SOFTWARE TESTING ONLY. NOT A REAL FINANCIAL RECORD."

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_styles["Title"], fontSize=17, leading=21, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=_styles["Normal"], fontSize=10, leading=14)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"))


def money(v: D, cur: str = "$") -> str:
    return f"{cur}{v:,.2f}" if cur == "$" else f"{cur} {v:,.2f}"


def paren(v: D) -> str:
    return f"({v:,.2f})"


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(letter[0] / 2, 0.45 * inch, FOOTER)
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def table(rows, widths, header=True, bold_last=False, right_cols=()):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8ECF1")), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    if bold_last:
        style.append(("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"))
    for c in right_cols:
        style.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def build(folder: str, filename: str, title: str, org: str, meta, blocks) -> None:
    out = ROOT / folder
    out.mkdir(exist_ok=True)
    doc = SimpleDocTemplate(str(out / filename), pagesize=letter, title=title, leftMargin=0.75 * inch,
                            rightMargin=0.75 * inch, topMargin=0.7 * inch, bottomMargin=0.8 * inch)
    story = [Paragraph(org, SMALL), Paragraph(title, H1), Spacer(1, 6),
             table([[k, v] for k, v in meta], [1.9 * inch, 4.9 * inch], header=False), Spacer(1, 8), *blocks]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


W2 = [5.0 * inch, 1.8 * inch]

# ============================================================== A. all clear (Priya Nair)
A_AWARDS = [("Alder Ridge Merit Scholarship", D("4000.00")), ("Commonwealth State Grant", D("1500.00")),
            ("Federal Direct Subsidized Loan", D("2750.00"))]
A_AID = sum(a for _, a in A_AWARDS)
A_CH = [("Tuition (full-time rate, 14 credits)", D("9200.00")), ("Technology and Student Fees", D("700.00")),
        ("Residence Hall - Fall 2026", D("3400.00")), ("Meal Plan - Fall 2026", D("1300.00"))]
A_CHARGES = sum(a for _, a in A_CH)
A_PAY = D("6350.00")
assert A_AID == D("8250.00") and A_CHARGES == D("14600.00") and A_AID + A_PAY == A_CHARGES

build("a_all_clear", "01_award_letter_fall_2026.pdf", "Financial Aid Award Letter - Fall 2026", UNIVERSITY,
      [("Issued by", f"{UNIVERSITY} Office of Financial Aid"), ("Letter date", "July 22, 2026"),
       ("Student", "Priya Nair"), ("Term", "Fall 2026")],
      [Paragraph("Your awards and disbursement dates", H2),
       table([["Award", "Disbursement date", "Amount"]] + [[n, "September 8, 2026", money(a)] for n, a in A_AWARDS]
             + [["Total aid", "", money(A_AID)]], [3.2 * inch, 2.0 * inch, 1.6 * inch], bold_last=True, right_cols=(2,)),
       Paragraph("Conditions", H2),
       Paragraph("The Alder Ridge Merit Scholarship requires enrollment in at least 12 credits in Fall 2026.", BODY)])

build("a_all_clear", "02_fall_2026_bill.pdf", "Student Account Statement - Fall 2026", UNIVERSITY,
      [("Issued by", f"{UNIVERSITY} Office of the Bursar"), ("Statement date", "September 12, 2026"),
       ("Student", "Priya Nair"), ("Term", "Fall 2026"), ("Enrolled credits", "14"),
       ("Payment due date", "September 15, 2026")],
      [Paragraph("Charges", H2),
       table([["Description", "Amount"]] + [[n, money(a)] for n, a in A_CH] + [["Total charges", money(A_CHARGES)]],
             W2, bold_last=True, right_cols=(1,)),
       Paragraph("Financial aid and payments applied", H2),
       table([["Description", "Amount"]] + [[f"{n} (disbursed September 8, 2026)", paren(a)] for n, a in A_AWARDS]
             + [["Payment received September 10, 2026", paren(A_PAY)], ["Total credits", paren(A_AID + A_PAY)]],
             W2, bold_last=True, right_cols=(1,)),
       Spacer(1, 10), table([["Balance due", money(A_CHARGES - A_AID - A_PAY)]], W2, header=False, bold_last=True, right_cols=(1,))])

# ============================================================== B. overaward + loan mismatch (Marcus Bell)
B_COA = [("Tuition", D("18400.00")), ("Mandatory fees", D("1300.00")), ("Housing and meals", D("9600.00")),
         ("Books and supplies", D("1200.00")), ("Transportation and personal expenses", D("3000.00"))]
B_COA_TOTAL = sum(a for _, a in B_COA)
B_AID = [("Alder Ridge Merit Scholarship", D("12000.00")), ("Commonwealth State Grant", D("4000.00")),
         ("Alder Ridge Institutional Grant", D("9000.00")), ("Federal Direct Subsidized Loan", D("5500.00")),
         ("Bellwether Community Foundation Scholarship (outside award, reported by student)", D("5000.00"))]
B_AID_TOTAL = sum(a for _, a in B_AID)
B_LOAN_OFFER = D("4500.00")
assert B_COA_TOTAL == D("33500.00") and B_AID_TOTAL == D("35500.00") and B_AID_TOTAL - B_COA_TOTAL == D("2000.00")
assert D("5500.00") - B_LOAN_OFFER == D("1000.00")

build("b_overaward_loan", "01_aid_package_and_cost_of_attendance_2026-27.pdf",
      "Financial Aid Package and Cost of Attendance - 2026-2027", UNIVERSITY,
      [("Issued by", f"{UNIVERSITY} Office of Financial Aid"), ("Package date", "August 3, 2026"),
       ("Student", "Marcus Bell"), ("Academic year", "2026-2027 (Fall 2026 and Spring 2027)")],
      [Paragraph("Estimated cost of attendance", H2),
       table([["Category", "Estimated amount"]] + [[n, money(a)] for n, a in B_COA] + [["Total cost of attendance", money(B_COA_TOTAL)]],
             W2, bold_last=True, right_cols=(1,)),
       Paragraph("Aid in your package", H2),
       table([["Award", "Annual amount"]] + [[n, money(a)] for n, a in B_AID] + [["Total aid", money(B_AID_TOTAL)]],
             W2, bold_last=True, right_cols=(1,))])

build("b_overaward_loan", "02_direct_loan_offer_2026-27.pdf", "Federal Direct Subsidized Loan Offer - 2026-2027", UNIVERSITY,
      [("Issued by", f"{UNIVERSITY} Office of Financial Aid"), ("Offer date", "August 10, 2026"),
       ("Student", "Marcus Bell"), ("Academic year", "2026-2027"), ("Loan type", "Federal Direct Subsidized Loan"),
       ("Interest rate", "5.50% fixed"), ("Accept or decline by", "November 20, 2026")],
      [Paragraph("Loan amount offered", H2),
       table([["Item", "Amount"], ["Annual loan amount offered", money(B_LOAN_OFFER)],
              ["Fall 2026 disbursement", money(B_LOAN_OFFER / 2)], ["Spring 2027 disbursement", money(B_LOAN_OFFER / 2)]],
             W2, right_cols=(1,))])

# ============================================================== C. study abroad choice (Sofia Alvarez)
C_CH = [("Tuition (15 credits)", D("9500.00")), ("Technology and Student Fees", D("650.00")),
        ("Residence Hall - Spring 2027", D("3100.00")), ("Meal Plan - Spring 2027", D("1200.00"))]
C_CHARGES = sum(a for _, a in C_CH)
C_AID = [("Alder Ridge Merit Scholarship", D("3000.00")), ("Commonwealth State Grant", D("1000.00"))]
C_AID_TOTAL = sum(a for _, a in C_AID)
MAD = [("Program Tuition", D("6200.00")), ("Host Family Housing", D("3400.00")), ("Program Fee", D("800.00")),
       ("Estimated Round-Trip Airfare (estimate)", D("900.00"))]
MAD_TOTAL = sum(a for _, a in MAD)
SEO = [("Program Tuition", D("7800.00")), ("Partner Residence (housing)", D("3000.00")), ("Program Fee", D("900.00")),
       ("Estimated Round-Trip Airfare (estimate)", D("1600.00"))]
SEO_TOTAL = sum(a for _, a in SEO)
assert C_CHARGES == D("14450.00") and C_AID_TOTAL == D("4000.00") and C_CHARGES - C_AID_TOTAL == D("10450.00")
assert MAD_TOTAL == D("11300.00") and SEO_TOTAL == D("13300.00")

build("c_study_abroad_choice", "01_spring_2027_bill.pdf", "Student Account Statement - Spring 2027", UNIVERSITY,
      [("Issued by", f"{UNIVERSITY} Office of the Bursar"), ("Statement date", "October 22, 2026"),
       ("Student", "Sofia Alvarez"), ("Term", "Spring 2027"), ("Enrolled credits", "15"),
       ("Payment due date", "January 15, 2027")],
      [Paragraph("Charges", H2),
       table([["Description", "Amount"]] + [[n, money(a)] for n, a in C_CH] + [["Total charges", money(C_CHARGES)]],
             W2, bold_last=True, right_cols=(1,)),
       Paragraph("Anticipated financial aid (pending disbursement)", H2),
       table([["Description", "Amount"]] + [[n, paren(a)] for n, a in C_AID] + [["Total anticipated aid", paren(C_AID_TOTAL)]],
             W2, bold_last=True, right_cols=(1,)),
       Spacer(1, 10),
       table([["Payments received", money(D("0.00"))], ["Balance due after anticipated aid", money(C_CHARGES - C_AID_TOTAL)]],
             W2, header=False, bold_last=True, right_cols=(1,))])

build("c_study_abroad_choice", "02_madrid_program_quote_EUR.pdf", "Semester Abroad Cost Estimate - Madrid, Spring 2027",
      "Iberia Study Programs",
      [("Provider", "Iberia Study Programs"), ("Quote date", "October 12, 2026"), ("Prepared for", "Sofia Alvarez"),
       ("Term", "Spring 2027"), ("Program dates", "January 19, 2027 to May 22, 2027"),
       ("Currency", "EUR (euros)"), ("Application deadline", "November 20, 2026"), ("Quote valid through", "November 30, 2026")],
      [Paragraph("Estimated program costs", H2),
       table([["Item", "Amount"]] + [[n, money(a, "EUR")] for n, a in MAD] + [["Total estimated cost", money(MAD_TOTAL, "EUR")]],
             W2, bold_last=True, right_cols=(1,)),
       Spacer(1, 8), Paragraph("All amounts are in euros. This document is an estimate, not an invoice.", SMALL)])

build("c_study_abroad_choice", "03_seoul_program_quote_USD.pdf", "Semester Abroad Cost Estimate - Seoul, Spring 2027",
      "Pacific Exchange Network",
      [("Provider", "Pacific Exchange Network"), ("Quote date", "October 14, 2026"), ("Prepared for", "Sofia Alvarez"),
       ("Term", "Spring 2027"), ("Program dates", "February 22, 2027 to June 19, 2027"),
       ("Currency", "USD"), ("Application deadline", "November 6, 2026"), ("Quote valid through", "November 30, 2026")],
      [Paragraph("Estimated program costs", H2),
       table([["Item", "Amount"]] + [[n, money(a)] for n, a in SEO] + [["Total estimated cost", money(SEO_TOTAL)]],
             W2, bold_last=True, right_cols=(1,)),
       Spacer(1, 8), Paragraph("All amounts are in US dollars. This document is an estimate, not an invoice.", SMALL)])

# ============================================================== D. missing scholarship (Devon Park)
D_AWARDS = [("Alder Ridge Merit Scholarship", D("5000.00")), ("Commonwealth State Grant", D("2000.00"))]
D_AID = sum(a for _, a in D_AWARDS)
D_CH = [("Tuition (15 credits)", D("10200.00")), ("Technology and Student Fees", D("700.00")),
        ("Residence Hall - Fall 2026", D("3500.00")), ("Meal Plan - Fall 2026", D("1400.00"))]
D_CHARGES = sum(a for _, a in D_CH)
D_WAIVER, D_GRANT, D_PAY = D("1200.00"), D("2000.00"), D("6000.00")
D_BALANCE = D_CHARGES - D_GRANT - D_WAIVER - D_PAY
assert D_AID == D("7000.00") and D_CHARGES == D("15800.00") and D_BALANCE == D("6600.00")
assert D_BALANCE - D("5000.00") == D("1600.00")

build("d_missing_scholarship", "01_award_letter_fall_2026.pdf", "Financial Aid Award Letter - Fall 2026", UNIVERSITY,
      [("Issued by", f"{UNIVERSITY} Office of Financial Aid"), ("Letter date", "July 25, 2026"),
       ("Student", "Devon Park"), ("Term", "Fall 2026")],
      [Paragraph("Your awards and disbursement dates", H2),
       table([["Award", "Disbursement date", "Amount"]] + [[n, "September 8, 2026", money(a)] for n, a in D_AWARDS]
             + [["Total aid", "", money(D_AID)]], [3.2 * inch, 2.0 * inch, 1.6 * inch], bold_last=True, right_cols=(2,)),
       Paragraph("Conditions", H2),
       Paragraph("The Alder Ridge Merit Scholarship requires enrollment in at least 12 credits in Fall 2026.", BODY)])

build("d_missing_scholarship", "02_fall_2026_bill.pdf", "Student Account Statement - Fall 2026", UNIVERSITY,
      [("Issued by", f"{UNIVERSITY} Office of the Bursar"), ("Statement date", "October 1, 2026"),
       ("Student", "Devon Park"), ("Term", "Fall 2026"), ("Enrolled credits", "15"),
       ("Payment due date", "September 15, 2026")],
      [Paragraph("Charges", H2),
       table([["Description", "Amount"]] + [[n, money(a)] for n, a in D_CH] + [["Total charges", money(D_CHARGES)]],
             W2, bold_last=True, right_cols=(1,)),
       Paragraph("Financial aid and payments applied", H2),
       table([["Description", "Amount"],
              ["Commonwealth State Grant (disbursed September 8, 2026)", paren(D_GRANT)],
              ["Departmental Tuition Waiver", paren(D_WAIVER)],
              ["Payment received September 14, 2026", paren(D_PAY)],
              ["Total credits", paren(D_GRANT + D_WAIVER + D_PAY)]], W2, bold_last=True, right_cols=(1,)),
       Spacer(1, 10), table([["Balance due", money(D_BALANCE)]], W2, header=False, bold_last=True, right_cols=(1,))])

print("Generated PDFs in", ROOT)
