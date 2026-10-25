# Scenario 3: two-term demo (Alder Ridge University / "Jordan Rivera")

Everything here is **fictional and synthetic** (every PDF carries a "for software testing only" footer), so it is safe to upload to Gemini even on a free-tier key.

## Drop it into the repo

Copy this whole folder to `sample_docs/scenario_3_two_term_demo/` and commit it. The six PDFs are already generated; `generate.py` (needs `pip install reportlab`) only matters if you want to change numbers.

## Upload these six PDFs, in any order

| File | What it is |
|---|---|
| `01_award_letter_AY2026-27.pdf` | $11,500 annual aid ($5,750 per term), per-term disbursement dates, a 12-credit and 3.00 GPA condition on the merit scholarship, and a loan acceptance deadline |
| `02_fall_2026_bill.pdf` | Fully covered. Balance $0.00. **The quiet baseline: nothing should be flagged for Fall.** |
| `03_spring_2027_bill.pdf` | 9 credits, merit scholarship credited at $2,500 (letter says $3,000), $6,450 balance, due Jan 15, $50 late fee |
| `04_study_abroad_quote_spring_2027.pdf` | $14,300 estimate for Spring 2027 abroad, including its own $8,400 program tuition |
| `05_housing_contract_2026-27.pdf` | Spring rate $3,300, but the bill charges $3,100 |
| `06_payment_plan_spring_2027.pdf` | 4 x $1,500 = $6,000 against a $6,450 plan balance |

Term spellings are deliberately inconsistent (Fall 2026 / FA26, Spring 2027 / Spring Semester 2027 / SP27). Terms that are written differently but mean the same thing must **not** produce findings.

## Hand-computed numbers (check these against `GET /api/ledger`)

| | Fall 2026 | Spring 2027 |
|---|---|---|
| Billed charges | $13,950.00 | $11,700.00 |
| Aid credited on the bill | $5,750.00 | $5,250.00 |
| Payments | $8,200.00 | $0.00 |
| Net balance | **$0.00** | **$6,450.00** |

The study-abroad total ($14,300.00) is an estimate and should **not** be mixed into Spring's billed charges.

## What the engine should find (intended, as of 2026-10-25)

| | Rule | Severity | Why |
|---|---|---|---|
| E1 | `award.amount_mismatch` (Spring) | error | Merit scholarship $3,000 vs $2,500, $500 difference |
| E2 | `timing.disbursement_after_due` (Spring) | warning | Merit scholarship pays Feb 1, due date Jan 15, $50 late fee. The grant and loan pay Jan 11 and must not be flagged |
| E3 | `eligibility.credit_requirement` (Spring) | error | Needs 12 credits, bill shows 9 |
| E4 | `coverage.term_gap` (Spring) | warning | $6,450 unpaid (could read $450 if installments count as coverage) |
| E5 | `plan.installment_total` (Spring) | warning | Installments $6,000 vs balance $6,450, $450 short |
| E6 | `housing.contract_vs_bill` (Spring) | warning | $3,300 contract vs $3,100 billed, $200 |
| E7 | `program.double_charge` (Spring) | warning | Program tuition and home tuition both present for the same term |
| E8 | `timing.deadline_status` | warning | Loan acceptance deadline Oct 30 is 5 days away |
| E9 | one grouped `eligibility.*` | info | Verify the 3.00 GPA condition |

It must **not** produce: any Fall 2026 coverage finding, any "terms differ" or "dates differ" finding, `award.missing_on_bill`, `duplicate.*`, `quality.*`, `currency.*`, a Fall housing mismatch, more than 3 info findings, or deadline findings for the quote (Nov 15, Nov 30), housing cancellation (Dec 1) or plan enrollment (Dec 15).

**These are my calculations from the documents, not engine output.** `expected.json` lists alternative impact amounts where a rule's semantics are ambiguous. If the engine disagrees, decide whether the engine or the expectation is wrong before changing either.

## Check it automatically

Open the app, upload the six PDFs, then save the response of `GET /api/findings` (DevTools, Network tab, Response, copy) as `findings.json`:

```bash
python check_expected.py findings.json
```

It prints PASS, WARN (wrong severity or impact outside the listed alternatives) or FAIL for every expectation and absence, and exits non-zero on any FAIL.

## Date sensitivity

Findings were computed for **today = 2026-10-25**. The loan deadline (Oct 30) turns from a warning into an **overdue error** after that date. To keep the demo stable, change `LOAN_ACCEPT_BY` and `LOAN_ACCEPT_ISO` at the top of `generate.py`, rerun it, and re-upload.

## Offline envelopes (best effort)

`envelopes/*.json` are hand-built extraction envelopes, one per PDF, for tests that must not call Gemini. Their field names follow the extraction schema as described when it was designed (`line_items[].direction/kind/term`, `payment_due_dates`, `enrollment_credits`, `disbursements[].term/award_label`, ...). I haven't seen the final `ExtractionEnvelope` class, so validate them against it first (`ExtractionEnvelope.model_validate(json)`) and fix any field-name drift before wiring them into a test.

## Live extraction check

Before trusting the rules, upload the PDFs with a real key and compare what Gemini extracted against `envelopes/*.json`: line-item directions and kinds, per-term assignment, the 9 vs 12 credits, and each date. Wrong extraction is the most likely reason for a wrong finding.
