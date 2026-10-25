#!/usr/bin/env python3
"""Generate the synthetic 'two-term demo' scenario (scenario_3_two_term_demo).

Writes, next to this script:
  01_award_letter_AY2026-27.pdf ... 06_payment_plan_spring_2027.pdf   (text-layer PDFs)
  envelopes/*.json   best-effort offline extraction envelopes (no Gemini needed)
  expected.json      hand-computed ledger numbers + intended findings + intended absences

Everything is FICTIONAL. Every PDF carries a "synthetic / for testing only" footer.
Only reportlab is needed (pip install reportlab). All totals are asserted below, so a
typo in any number fails the script instead of producing inconsistent documents.

Usage:  python generate.py
"""

from __future__ import annotations

import json
from decimal import Decimal as D
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent
ENV = OUT / "envelopes"
ENV.mkdir(exist_ok=True)

TODAY = "2026-10-25"  # the date the intended findings were computed for
UNIVERSITY = "Alder Ridge University"
STUDENT = "Jordan Rivera"  # fictional
# If you demo after this date, the loan-acceptance deadline becomes OVERDUE (an error
# instead of a warning). Edit this constant (and the matching ISO date below) to shift it.
LOAN_ACCEPT_BY = "October 30, 2026"
LOAN_ACCEPT_ISO = "2026-10-30"

FOOTER = "SYNTHETIC DOCUMENT - FOR SOFTWARE TESTING ONLY. NOT A REAL FINANCIAL RECORD."


def money(v: D) -> str:
    return f"${v:,.2f}"


def paren(v: D) -> str:
    return f"({v:,.2f})"


# --------------------------------------------------------------------------- numbers
# Award letter (annual, split by term)
MERIT, GRANT, LOAN = D("6000.00"), D("2000.00"), D("3500.00")
MERIT_T, GRANT_T, LOAN_T = D("3000.00"), D("1000.00"), D("1750.00")
AID_ANNUAL = MERIT + GRANT + LOAN
AID_TERM = MERIT_T + GRANT_T + LOAN_T
assert MERIT == 2 * MERIT_T and GRANT == 2 * GRANT_T and LOAN == 2 * LOAN_T
assert AID_ANNUAL == D("11500.00") and AID_TERM == D("5750.00")

# Fall 2026 bill (fully covered, balance 0.00)
FALL_TUITION, FALL_FEES, FALL_HOUSING, FALL_MEALS = D("9000.00"), D("650.00"), D("3100.00"), D("1200.00")
FALL_CHARGES = FALL_TUITION + FALL_FEES + FALL_HOUSING + FALL_MEALS
FALL_PAYMENT = D("8200.00")
assert FALL_CHARGES == D("13950.00")
assert AID_TERM + FALL_PAYMENT == FALL_CHARGES  # balance exactly 0.00

# Spring 2027 bill (planted: scholarship credit 2,500 vs 3,000 in award letter; 9 credits)
SP_TUITION, SP_FEES, SP_HOUSING, SP_MEALS = D("6750.00"), D("650.00"), D("3100.00"), D("1200.00")
SP_CHARGES = SP_TUITION + SP_FEES + SP_HOUSING + SP_MEALS
SP_MERIT_CREDIT = D("2500.00")
SP_AID = SP_MERIT_CREDIT + GRANT_T + LOAN_T
SP_BALANCE = SP_CHARGES - SP_AID
assert SP_TUITION == 9 * D("750.00")
assert SP_CHARGES == D("11700.00") and SP_AID == D("5250.00") and SP_BALANCE == D("6450.00")

# Study-abroad quote (an estimate, Spring 2027)
Q_TUITION, Q_HOUSING, Q_FEE, Q_AIR = D("8400.00"), D("3600.00"), D("950.00"), D("1350.00")
Q_TOTAL = Q_TUITION + Q_HOUSING + Q_FEE + Q_AIR
assert Q_TOTAL == D("14300.00")

# Housing contract (planted: Spring contract rate 3,300 vs 3,100 billed)
H_FALL, H_SPRING = D("3100.00"), D("3300.00")
H_TOTAL = H_FALL + H_SPRING
assert H_TOTAL == D("6400.00") and H_FALL == FALL_HOUSING and H_SPRING != SP_HOUSING

# Payment plan (planted: installments sum to 6,000, plan balance is 6,450)
INSTALL = D("1500.00")
INSTALLMENTS = [
    ("January 15, 2027", "2027-01-15"),
    ("February 15, 2027", "2027-02-15"),
    ("March 15, 2027", "2027-03-15"),
    ("April 15, 2027", "2027-04-15"),
]
PLAN_TOTAL = INSTALL * len(INSTALLMENTS)
assert PLAN_TOTAL == D("6000.00") and SP_BALANCE - PLAN_TOTAL == D("450.00")

# --------------------------------------------------------------------------- PDF helpers
_styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_styles["Title"], fontSize=17, leading=21, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=_styles["Normal"], fontSize=10, leading=14)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(letter[0] / 2, 0.45 * inch, FOOTER)
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def table(rows, col_widths, header=True, bold_last=False, right_cols=()):
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8ECF1")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    if bold_last:
        style += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]
    for c in right_cols:
        style.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def build(filename: str, title: str, meta: list[tuple[str, str]], blocks: list) -> None:
    doc = SimpleDocTemplate(
        str(OUT / filename), pagesize=letter, title=title,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.7 * inch, bottomMargin=0.8 * inch,
    )
    story = [Paragraph(UNIVERSITY if "Program" not in title else "", SMALL), Paragraph(title, H1), Spacer(1, 6)]
    story.append(table([[k, v] for k, v in meta], [1.9 * inch, 4.9 * inch], header=False))
    story.append(Spacer(1, 8))
    story.extend(blocks)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def item(label, amount, direction, kind, term, category, date=None):
    d = {"label": label, "amount": str(amount), "category": category, "direction": direction, "kind": kind, "term": term}
    if date:
        d["date"] = date
    return d


# =========================================================================== 1. Award letter
build(
    "01_award_letter_AY2026-27.pdf",
    "Financial Aid Award Letter - Academic Year 2026-2027",
    [
        ("Issued by", f"{UNIVERSITY} Office of Financial Aid"),
        ("Letter date", "July 20, 2026"),
        ("Student", STUDENT),
        ("Academic year", "2026-2027 (Fall 2026 and Spring 2027)"),
    ],
    [
        Paragraph("Your awards", H2),
        table(
            [
                ["Award", "Annual amount", "Fall 2026", "Spring 2027"],
                ["Alder Ridge Merit Scholarship", money(MERIT), money(MERIT_T), money(MERIT_T)],
                ["Commonwealth State Grant", money(GRANT), money(GRANT_T), money(GRANT_T)],
                ["Federal Direct Subsidized Loan", money(LOAN), money(LOAN_T), money(LOAN_T)],
                ["Total aid", money(AID_ANNUAL), money(AID_TERM), money(AID_TERM)],
            ],
            [2.7 * inch, 1.4 * inch, 1.3 * inch, 1.4 * inch], bold_last=True, right_cols=(1, 2, 3),
        ),
        Paragraph("Disbursement schedule", H2),
        table(
            [
                ["Award", "Term", "Disbursement date", "Amount"],
                ["Alder Ridge Merit Scholarship", "FA26", "September 8, 2026", money(MERIT_T)],
                ["Commonwealth State Grant", "FA26", "September 8, 2026", money(GRANT_T)],
                ["Federal Direct Subsidized Loan", "FA26", "September 8, 2026", money(LOAN_T)],
                ["Alder Ridge Merit Scholarship", "SP27", "February 1, 2027", money(MERIT_T)],
                ["Commonwealth State Grant", "SP27", "January 11, 2027", money(GRANT_T)],
                ["Federal Direct Subsidized Loan", "SP27", "January 11, 2027", money(LOAN_T)],
            ],
            [2.7 * inch, 0.8 * inch, 1.8 * inch, 1.5 * inch], right_cols=(3,),
        ),
        Paragraph("Conditions of your awards", H2),
        Paragraph("1. The Alder Ridge Merit Scholarship requires enrollment in at least 12 credits each term.", BODY),
        Paragraph("2. The Alder Ridge Merit Scholarship requires a cumulative GPA of at least 3.00 at the end of each term.", BODY),
        Paragraph("Deadlines", H2),
        Paragraph(f"Accept or decline the Spring 2027 Federal Direct Subsidized Loan disbursement by {LOAN_ACCEPT_BY}.", BODY),
        Spacer(1, 8),
        Paragraph("Amounts are subject to change if your enrollment or eligibility changes.", SMALL),
    ],
)

def _award_envelope():
    items, disb = [], []
    for term, merit_date in (("Fall 2026", "2026-09-08"), ("Spring 2027", "2027-02-01")):
        other_date = "2026-09-08" if term == "Fall 2026" else "2027-01-11"
        items += [
            item("Alder Ridge Merit Scholarship", MERIT_T, "credit", "scholarship", term, "scholarship", merit_date),
            item("Commonwealth State Grant", GRANT_T, "credit", "grant", term, "grant", other_date),
            item("Federal Direct Subsidized Loan", LOAN_T, "credit", "loan", term, "loan", other_date),
        ]
        disb += [
            {"date": merit_date, "amount": str(MERIT_T), "term": term, "award_label": "Alder Ridge Merit Scholarship"},
            {"date": other_date, "amount": str(GRANT_T), "term": term, "award_label": "Commonwealth State Grant"},
            {"date": other_date, "amount": str(LOAN_T), "term": term, "award_label": "Federal Direct Subsidized Loan"},
        ]
    return {
        "document_type": "award_letter", "type_confidence": 0.98,
        "issuer": f"{UNIVERSITY} Office of Financial Aid", "currency": "USD",
        "term": "Academic Year 2026-2027", "academic_year": "2026-2027", "terms": ["Fall 2026", "Spring 2027"],
        "document_date": "2026-07-20", "total_amount": str(AID_ANNUAL),
        "required_credits": 12, "min_gpa": "3.00", "enrollment_credits": None,
        "deadlines": [{"label": "Accept or decline Spring 2027 Direct Loan disbursement", "date": LOAN_ACCEPT_ISO}],
        "payment_due_dates": [], "exchange_rate": None,
        "line_items": items, "disbursements": disb,
        "conditions": [
            "Merit Scholarship requires enrollment in at least 12 credits each term",
            "Merit Scholarship requires a cumulative GPA of at least 3.00 at the end of each term",
        ],
        "summary": "2026-27 aid: $11,500 total ($5,750 per term) across a merit scholarship, a state grant and a subsidized loan.",
        "action_required": True, "action_reason": f"Spring loan disbursement must be accepted or declined by {LOAN_ACCEPT_BY}.",
    }

write_json(ENV / "01_award_letter.json", _award_envelope())

# =========================================================================== 2. Fall 2026 bill
build(
    "02_fall_2026_bill.pdf",
    "Student Account Statement - Fall 2026",
    [
        ("Issued by", f"{UNIVERSITY} Office of the Bursar"),
        ("Statement date", "September 14, 2026"),
        ("Student", STUDENT),
        ("Term", "Fall 2026"),
        ("Enrolled credits", "12"),
        ("Payment due date", "September 15, 2026"),
    ],
    [
        Paragraph("Charges", H2),
        table(
            [
                ["Description", "Amount"],
                ["Tuition (12 credits)", money(FALL_TUITION)],
                ["Technology and Student Fees", money(FALL_FEES)],
                ["Residence Hall - Fall 2026", money(FALL_HOUSING)],
                ["Meal Plan - Fall 2026", money(FALL_MEALS)],
                ["Total charges", money(FALL_CHARGES)],
            ],
            [5.0 * inch, 1.8 * inch], bold_last=True, right_cols=(1,),
        ),
        Paragraph("Financial aid and payments applied", H2),
        table(
            [
                ["Description", "Amount"],
                ["Alder Ridge Merit Scholarship (disbursed September 8, 2026)", paren(MERIT_T)],
                ["Commonwealth State Grant (disbursed September 8, 2026)", paren(GRANT_T)],
                ["Federal Direct Subsidized Loan (disbursed September 8, 2026)", paren(LOAN_T)],
                ["Payment received September 12, 2026", paren(FALL_PAYMENT)],
                ["Total credits", paren(AID_TERM + FALL_PAYMENT)],
            ],
            [5.0 * inch, 1.8 * inch], bold_last=True, right_cols=(1,),
        ),
        Spacer(1, 10),
        table([["Balance due", money(FALL_CHARGES - AID_TERM - FALL_PAYMENT)]], [5.0 * inch, 1.8 * inch], header=False, bold_last=True, right_cols=(1,)),
    ],
)

write_json(ENV / "02_fall_2026_bill.json", {
    "document_type": "tuition_bill", "type_confidence": 0.98,
    "issuer": f"{UNIVERSITY} Office of the Bursar", "currency": "USD",
    "term": "Fall 2026", "terms": ["Fall 2026"], "academic_year": None,
    "document_date": "2026-09-14", "total_amount": str(FALL_CHARGES),
    "required_credits": None, "min_gpa": None, "enrollment_credits": 12,
    "deadlines": [], "payment_due_dates": [{"label": "Payment due", "date": "2026-09-15", "term": "Fall 2026"}],
    "exchange_rate": None,
    "line_items": [
        item("Tuition (12 credits)", FALL_TUITION, "charge", "tuition", "Fall 2026", "tuition"),
        item("Technology and Student Fees", FALL_FEES, "charge", "fees", "Fall 2026", "fees"),
        item("Residence Hall - Fall 2026", FALL_HOUSING, "charge", "housing", "Fall 2026", "housing"),
        item("Meal Plan - Fall 2026", FALL_MEALS, "charge", "meals", "Fall 2026", "meals"),
        item("Alder Ridge Merit Scholarship", MERIT_T, "credit", "scholarship", "Fall 2026", "scholarship", "2026-09-08"),
        item("Commonwealth State Grant", GRANT_T, "credit", "grant", "Fall 2026", "grant", "2026-09-08"),
        item("Federal Direct Subsidized Loan", LOAN_T, "credit", "loan", "Fall 2026", "loan", "2026-09-08"),
        item("Payment received", FALL_PAYMENT, "credit", "payment", "Fall 2026", "payment", "2026-09-12"),
    ],
    "disbursements": [], "conditions": [],
    "summary": "Fall 2026 charges of $13,950.00 are fully covered by aid and a payment; balance is $0.00.",
    "action_required": False, "action_reason": None,
})

# =========================================================================== 3. Spring 2027 bill
build(
    "03_spring_2027_bill.pdf",
    "Student Account Statement - Spring Semester 2027",
    [
        ("Issued by", f"{UNIVERSITY} Office of the Bursar"),
        ("Statement date", "October 20, 2026 (pre-registration statement)"),
        ("Student", STUDENT),
        ("Term", "Spring Semester 2027"),
        ("Enrolled credits", "9"),
        ("Payment due date", "January 15, 2027"),
        ("Late fee", "$50.00 is assessed on any unpaid balance after the due date"),
    ],
    [
        Paragraph("Charges", H2),
        table(
            [
                ["Description", "Amount"],
                ["Tuition (9 credits at $750.00 per credit)", money(SP_TUITION)],
                ["Technology and Student Fees", money(SP_FEES)],
                ["Residence Hall - Spring 2027", money(SP_HOUSING)],
                ["Meal Plan - Spring 2027", money(SP_MEALS)],
                ["Total charges", money(SP_CHARGES)],
            ],
            [5.0 * inch, 1.8 * inch], bold_last=True, right_cols=(1,),
        ),
        Paragraph("Anticipated financial aid (pending disbursement)", H2),
        table(
            [
                ["Description", "Amount"],
                ["Alder Ridge Merit Scholarship", paren(SP_MERIT_CREDIT)],
                ["Commonwealth State Grant", paren(GRANT_T)],
                ["Federal Direct Subsidized Loan", paren(LOAN_T)],
                ["Total anticipated aid", paren(SP_AID)],
            ],
            [5.0 * inch, 1.8 * inch], bold_last=True, right_cols=(1,),
        ),
        Spacer(1, 10),
        table(
            [["Payments received", money(D("0.00"))], ["Balance due after anticipated aid", money(SP_BALANCE)]],
            [5.0 * inch, 1.8 * inch], header=False, bold_last=True, right_cols=(1,),
        ),
    ],
)

write_json(ENV / "03_spring_2027_bill.json", {
    "document_type": "tuition_bill", "type_confidence": 0.98,
    "issuer": f"{UNIVERSITY} Office of the Bursar", "currency": "USD",
    "term": "Spring Semester 2027", "terms": ["Spring Semester 2027"], "academic_year": None,
    "document_date": "2026-10-20", "total_amount": str(SP_CHARGES),
    "required_credits": None, "min_gpa": None, "enrollment_credits": 9,
    "deadlines": [], "payment_due_dates": [{"label": "Payment due", "date": "2027-01-15", "term": "Spring Semester 2027"}],
    "exchange_rate": None,
    "line_items": [
        item("Tuition (9 credits at $750.00 per credit)", SP_TUITION, "charge", "tuition", "Spring Semester 2027", "tuition"),
        item("Technology and Student Fees", SP_FEES, "charge", "fees", "Spring Semester 2027", "fees"),
        item("Residence Hall - Spring 2027", SP_HOUSING, "charge", "housing", "Spring Semester 2027", "housing"),
        item("Meal Plan - Spring 2027", SP_MEALS, "charge", "meals", "Spring Semester 2027", "meals"),
        item("Alder Ridge Merit Scholarship", SP_MERIT_CREDIT, "credit", "scholarship", "Spring Semester 2027", "scholarship"),
        item("Commonwealth State Grant", GRANT_T, "credit", "grant", "Spring Semester 2027", "grant"),
        item("Federal Direct Subsidized Loan", LOAN_T, "credit", "loan", "Spring Semester 2027", "loan"),
    ],
    "disbursements": [], "conditions": ["$50.00 late fee on unpaid balance after the due date"],
    "summary": "Spring 2027 charges of $11,700.00 with $5,250.00 of anticipated aid; $6,450.00 due January 15, 2027.",
    "action_required": True, "action_reason": "Balance of $6,450.00 is due January 15, 2027.",
})

# =========================================================================== 4. Study-abroad quote
build(
    "04_study_abroad_quote_spring_2027.pdf",
    "Semester Abroad Cost Estimate - Lisbon, Spring 2027",
    [
        ("Provider", "Atlantic Exchange Programs"),
        ("Quote date", "October 10, 2026"),
        ("Prepared for", STUDENT),
        ("Term", "Spring 2027"),
        ("Program dates", "January 18, 2027 to May 21, 2027"),
        ("Currency", "USD"),
        ("Quote valid through", "November 30, 2026"),
        ("Application deadline", "November 15, 2026"),
    ],
    [
        Paragraph("Estimated program costs", H2),
        table(
            [
                ["Item", "Amount"],
                ["Program Tuition (billed by the provider)", money(Q_TUITION)],
                ["Partner Residence (housing)", money(Q_HOUSING)],
                ["Program and Insurance Fee", money(Q_FEE)],
                ["Estimated Round-Trip Airfare (estimate)", money(Q_AIR)],
                ["Total estimated cost", money(Q_TOTAL)],
            ],
            [5.0 * inch, 1.8 * inch], bold_last=True, right_cols=(1,),
        ),
        Spacer(1, 8),
        Paragraph("Program tuition is billed by the provider and is separate from any tuition billed by your home institution. "
                  "This document is an estimate, not an invoice.", SMALL),
    ],
)

write_json(ENV / "04_study_abroad_quote.json", {
    "document_type": "study_abroad_quote", "type_confidence": 0.97,
    "issuer": "Atlantic Exchange Programs", "currency": "USD",
    "term": "Spring 2027", "terms": ["Spring 2027"], "academic_year": None,
    "document_date": "2026-10-10", "total_amount": str(Q_TOTAL),
    "required_credits": None, "min_gpa": None, "enrollment_credits": None,
    "deadlines": [
        {"label": "Application deadline", "date": "2026-11-15"},
        {"label": "Quote valid through", "date": "2026-11-30"},
    ],
    "payment_due_dates": [], "exchange_rate": None,
    "line_items": [
        item("Program Tuition (billed by the provider)", Q_TUITION, "charge", "tuition", "Spring 2027", "tuition"),
        item("Partner Residence (housing)", Q_HOUSING, "charge", "housing", "Spring 2027", "housing"),
        item("Program and Insurance Fee", Q_FEE, "charge", "program_fee", "Spring 2027", "program_fee"),
        item("Estimated Round-Trip Airfare (estimate)", Q_AIR, "charge", "travel", "Spring 2027", "travel"),
    ],
    "disbursements": [], "conditions": ["Estimate only; program tuition is separate from home-institution tuition"],
    "summary": "Estimated $14,300.00 for a Spring 2027 semester abroad in Lisbon.",
    "action_required": False, "action_reason": None,
})

# =========================================================================== 5. Housing contract
build(
    "05_housing_contract_2026-27.pdf",
    "Residence Hall Agreement - 2026-2027 Academic Year",
    [
        ("Issued by", f"{UNIVERSITY} Residence Life"),
        ("Agreement date", "March 2, 2026"),
        ("Resident", STUDENT),
        ("Covered terms", "Fall 2026 and Spring 2027"),
    ],
    [
        Paragraph("Room rates", H2),
        table(
            [
                ["Term", "Room rate"],
                ["Fall 2026", money(H_FALL)],
                ["Spring 2027", money(H_SPRING)],
                ["Total 2026-2027", money(H_TOTAL)],
            ],
            [5.0 * inch, 1.8 * inch], bold_last=True, right_cols=(1,),
        ),
        Paragraph("Billing and cancellation", H2),
        Paragraph("Room rates are billed each term on your student account statement.", BODY),
        Paragraph("Spring 2027 housing may be cancelled without penalty before December 1, 2026.", BODY),
    ],
)

write_json(ENV / "05_housing_contract.json", {
    "document_type": "housing_contract", "type_confidence": 0.97,
    "issuer": f"{UNIVERSITY} Residence Life", "currency": "USD",
    "term": "2026-2027 Academic Year", "terms": ["Fall 2026", "Spring 2027"], "academic_year": "2026-2027",
    "document_date": "2026-03-02", "total_amount": str(H_TOTAL),
    "required_credits": None, "min_gpa": None, "enrollment_credits": None,
    "deadlines": [{"label": "Spring 2027 housing cancellation without penalty", "date": "2026-12-01"}],
    "payment_due_dates": [], "exchange_rate": None,
    "line_items": [
        item("Room rate - Fall 2026", H_FALL, "charge", "housing", "Fall 2026", "housing"),
        item("Room rate - Spring 2027", H_SPRING, "charge", "housing", "Spring 2027", "housing"),
    ],
    "disbursements": [], "conditions": [],
    "summary": "Residence hall agreement: $3,100.00 for Fall 2026 and $3,300.00 for Spring 2027.",
    "action_required": False, "action_reason": None,
})

# =========================================================================== 6. Payment plan
build(
    "06_payment_plan_spring_2027.pdf",
    "Payment Plan Agreement - Spring 2027 (SP27)",
    [
        ("Issued by", f"{UNIVERSITY} Office of the Bursar"),
        ("Agreement date", "October 21, 2026"),
        ("Student", STUDENT),
        ("Term", "Spring 2027 (SP27)"),
        ("Plan balance", money(SP_BALANCE)),
        ("Enrollment fee", "None"),
        ("Enrollment deadline", "December 15, 2026"),
    ],
    [
        Paragraph("Installment schedule", H2),
        table(
            [["Installment", "Due date", "Amount"]]
            + [[str(i + 1), label, money(INSTALL)] for i, (label, _) in enumerate(INSTALLMENTS)]
            + [["Total installments", "", money(PLAN_TOTAL)]],
            [2.4 * inch, 2.6 * inch, 1.8 * inch], bold_last=True, right_cols=(2,),
        ),
        Spacer(1, 8),
        Paragraph(f"The plan balance reflects anticipated financial aid of {money(SP_AID)} shown on your Spring 2027 statement.", SMALL),
    ],
)

write_json(ENV / "06_payment_plan.json", {
    "document_type": "payment_plan", "type_confidence": 0.97,
    "issuer": f"{UNIVERSITY} Office of the Bursar", "currency": "USD",
    "term": "Spring 2027 (SP27)", "terms": ["Spring 2027"], "academic_year": None,
    "document_date": "2026-10-21", "total_amount": str(SP_BALANCE),
    "required_credits": None, "min_gpa": None, "enrollment_credits": None,
    "deadlines": [{"label": "Payment plan enrollment deadline", "date": "2026-12-15"}],
    "payment_due_dates": [
        {"label": f"Installment {i + 1}", "date": iso, "term": "Spring 2027"} for i, (_, iso) in enumerate(INSTALLMENTS)
    ],
    "exchange_rate": None,
    "line_items": [
        item(f"Installment {i + 1}", INSTALL, "unknown", "payment", "Spring 2027", "installment", iso)
        for i, (_, iso) in enumerate(INSTALLMENTS)
    ],
    "disbursements": [], "conditions": ["Plan balance reflects anticipated aid of $5,250.00"],
    "summary": "Four $1,500.00 installments (total $6,000.00) against a plan balance of $6,450.00.",
    "action_required": True, "action_reason": "Enroll in the plan by December 15, 2026; first installment due January 15, 2027.",
})

# =========================================================================== expected.json
EXPECTED = {
    "scenario": "scenario_3_two_term_demo",
    "today": TODAY,
    "status_note": (
        "HAND-COMPUTED from the documents, not produced by the engine. Where a rule's exact semantics are ambiguous, "
        "impact_amount_any_of lists every defensible value. A mismatch means either an engine bug or a wrong "
        "expectation here: investigate before changing either."
    ),
    "documents": [
        {"file": "01_award_letter_AY2026-27.pdf", "type": "award_letter", "term_as_written": "Academic Year 2026-2027 (FA26 / SP27 in schedule)"},
        {"file": "02_fall_2026_bill.pdf", "type": "tuition_bill", "term_as_written": "Fall 2026"},
        {"file": "03_spring_2027_bill.pdf", "type": "tuition_bill", "term_as_written": "Spring Semester 2027"},
        {"file": "04_study_abroad_quote_spring_2027.pdf", "type": "study_abroad_quote", "term_as_written": "Spring 2027"},
        {"file": "05_housing_contract_2026-27.pdf", "type": "housing_contract", "term_as_written": "Fall 2026 / Spring 2027"},
        {"file": "06_payment_plan_spring_2027.pdf", "type": "payment_plan", "term_as_written": "Spring 2027 (SP27)"},
    ],
    "ledger": {
        "Fall 2026": {
            "billed_charges": str(FALL_CHARGES), "aid_credits": str(AID_TERM), "payments": str(FALL_PAYMENT),
            "net_balance": str(FALL_CHARGES - AID_TERM - FALL_PAYMENT),
        },
        "Spring 2027": {
            "billed_charges": str(SP_CHARGES), "aid_credits_on_bill": str(SP_AID), "payments": "0.00",
            "net_balance_after_listed_aid": str(SP_BALANCE),
            "estimates_not_in_billed_charges": {"study_abroad_quote_total": str(Q_TOTAL)},
        },
        "award_letter": {"annual_aid": str(AID_ANNUAL), "per_term_aid": str(AID_TERM)},
        "housing_contract_total": str(H_TOTAL),
    },
    "expected_findings": [
        {"id": "E1", "rule_id": "award.amount_mismatch", "term": "Spring 2027", "severity": "error",
         "impact_amount_any_of": ["500.00"], "why": "Merit Scholarship: $3,000.00 in the award letter vs $2,500.00 credited on the Spring bill."},
        {"id": "E2", "rule_id": "timing.disbursement_after_due", "term": "Spring 2027", "severity": "warning",
         "impact_amount_any_of": ["3000.00", "2500.00"], "why": "Merit Scholarship disburses Feb 1, 2027, 17 days after the Jan 15 due date; the bill states a $50.00 late fee. Grant and loan disburse Jan 11 (before due) and must NOT be flagged."},
        {"id": "E3", "rule_id": "eligibility.credit_requirement", "term": "Spring 2027", "severity": "error",
         "impact_amount_any_of": ["3000.00", "2500.00"], "why": "Merit Scholarship requires 12 credits; the Spring bill shows 9."},
        {"id": "E4", "rule_id": "coverage.term_gap", "term": "Spring 2027", "severity": "warning",
         "impact_amount_any_of": ["6450.00", "450.00"], "why": "11,700.00 charges - 5,250.00 listed aid = 6,450.00 unpaid. Could show 450.00 if the engine counts the plan's $6,000.00 of scheduled installments as covering it. Not an error: due date is in the future."},
        {"id": "E5", "rule_id": "plan.installment_total", "term": "Spring 2027", "severity": "warning",
         "impact_amount_any_of": ["450.00"], "why": "4 x 1,500.00 = 6,000.00 vs plan balance 6,450.00."},
        {"id": "E6", "rule_id": "housing.contract_vs_bill", "term": "Spring 2027", "severity": "warning",
         "impact_amount_any_of": ["200.00"], "why": "Contract Spring rate 3,300.00 vs 3,100.00 billed. Fall matches and must NOT be flagged."},
        {"id": "E7", "rule_id": "program.double_charge", "term": "Spring 2027", "severity": "warning",
         "impact_amount_any_of": ["6750.00", "8400.00"], "why": "Provider program tuition (8,400.00) and home tuition (6,750.00) both appear for Spring 2027."},
        {"id": "E8", "rule_id": "timing.deadline_status", "term": None, "severity": "warning",
         "impact_amount_any_of": [], "why": f"Spring loan acceptance deadline {LOAN_ACCEPT_BY} is 5 days after the intended 'today' (becomes an error once overdue)."},
        {"id": "E9", "rule_id": "eligibility.*", "term": None, "severity": "info",
         "impact_amount_any_of": [], "why": "ONE grouped info telling the student the 3.00 GPA condition must be verified after each term (not one info per condition)."},
    ],
    "expected_absent": [
        {"id": "A1", "description": "No Fall 2026 coverage finding (term_gap or term_surplus): the balance is exactly 0.00.", "rule_prefix": "coverage.", "term": "Fall 2026"},
        {"id": "A2", "description": "No generic 'terms differ' or 'dates differ' findings; spellings Fall 2026 / FA26 and Spring 2027 / Spring Semester 2027 / SP27 are the same terms.", "rule_ids": ["term.mismatch", "deadline.different_dates", "term_mismatch", "deadline_conflict"]},
        {"id": "A3", "description": "No award.missing_on_bill: all three awards appear on both bills.", "rule_prefix": "award.missing_on_bill"},
        {"id": "A4", "description": "No amount mismatch for Fall 2026, the State Grant or the Direct Loan.", "rule_prefix": "award.amount_mismatch", "term": "Fall 2026"},
        {"id": "A5", "description": "No duplicate.award finding.", "rule_prefix": "duplicate."},
        {"id": "A6", "description": "No quality.data_gaps finding: every document has a parseable term, amounts and dates.", "rule_prefix": "quality."},
        {"id": "A7", "description": "No currency.mismatch finding: everything is USD.", "rule_prefix": "currency."},
        {"id": "A8", "description": "No housing mismatch for Fall 2026.", "rule_prefix": "housing.", "term": "Fall 2026"},
        {"id": "A9", "description": "No disbursement_after_due finding for the State Grant or Direct Loan (they disburse before the due date).", "rule_prefix": "timing.disbursement_after_due", "max_count_for_term": {"Spring 2027": 1}},
        {"id": "A10", "description": "No deadline findings for the quote deadlines (Nov 15 / Nov 30), the housing cancellation (Dec 1) or the plan enrollment (Dec 15): all are more than 14 days away.", "rule_prefix": "timing.deadline_status", "max_count": 1},
    ],
    "limits": {"max_default_info_findings": 3},
}
write_json(OUT / "expected.json", EXPECTED)
print("Generated 6 PDFs, 6 envelopes and expected.json in", OUT)
