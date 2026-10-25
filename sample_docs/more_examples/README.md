# More demo documents (4 scenarios, 9 PDFs)

All fictional and synthetic (every page says so), so they are safe to upload to Gemini even on a free-tier key. `generate_more.py` rebuilds them (`pip install reportlab`) if you want to change a number.

## One rule before you upload anything

Muni cross-checks **every active document in an account**. If you upload scenarios A and D into the same account, their Fall 2026 bills get mixed together and the results are meaningless. Use a **separate account per scenario**, or archive or delete the previous scenario's documents first. (Scenario 3, the Jordan Rivera set from before, is your flagship, so keep it in its own account too.)

## The scenarios

| Folder | Student | Story | What Muni *should* say (intended, hand-computed) |
|---|---|---|---|
| `a_all_clear` | Priya Nair | A clean semester: aid letter and bill agree, aid arrives before the due date, 14 credits against a 12-credit minimum | **Nothing wrong.** Fall balance is $0.00 ($14,600 charges, $8,250 aid, $6,350 paid). Use it to show Muni doesn't cry wolf |
| `d_missing_scholarship` | Devon Park | A $5,000 merit scholarship in the award letter never reached the bill, and the bill is past due | Merit scholarship missing from the bill ($5,000, its disbursement date has passed). An unexplained $1,200 "Departmental Tuition Waiver" credit with no award behind it. Fall 2026 balance **$6,600.00 unpaid and past due** (error). Insight: if the scholarship were applied, the balance would be $1,600 |
| `b_overaward_loan` | Marcus Bell | Aid package totals $35,500 against a $33,500 cost of attendance, and the loan offer disagrees with the package | Aid exceeds cost of attendance by **$2,000.00**. Loan: $5,500 in the package vs **$4,500** in the offer, a $1,000 mismatch |
| `c_study_abroad_choice` | Sofia Alvarez | A Spring bill ($14,450 charges, $4,000 anticipated aid, $10,450 balance) and two semester-abroad quotes: Madrid in **euros** (EUR 11,300) and Seoul in dollars ($13,300) | A **mixed-currency** finding: Muni won't add euros to dollars without a stated exchange rate. Seoul quote also shows a likely double tuition charge against the home bill. Seoul application deadline (Nov 6) approaching |

## Suggested demo order

1. **Scenario A** first, quickly: "here's what a healthy semester looks like: nothing to flag."
2. **Scenario D**: the most dramatic and easiest to explain ("a $5,000 scholarship went missing and Devon owes $6,600").
3. **Scenario B** or **C** if you have time. C pairs well with the chat: ask "Which semester abroad is cheaper, Madrid or Seoul?" The right answer is that Muni can't compare euros and dollars without an exchange rate, and shows Seoul's $13,300 total.
4. **Scenario 3 (Jordan Rivera)** is the full two-term flagship.

## Caveats (read these before you demo)

- **These expected results are my hand calculations, not engine output.** I haven't run the documents through your engine or through real Gemini extraction. Upload each set once and read the findings before you present them.
- Scenario A should produce **no error or warning findings**. If it does, that's a real bug (or a bad extraction) worth finding now, not on stage.
- In scenario C, how the double-charge rule treats the euro quote depends on how the rule handles mixed currencies. Expect the currency finding for sure, and the Seoul double charge probably.
- Several dates are relative to **today = Oct 25, 2026**: Devon's bill is past due, and Seoul's Nov 6 deadline is "near". If you demo after those dates pass, the severities shift, and a passed deadline becomes an overdue error.
- Real extraction may misread something, such as a credit's direction or the term. That's what the "correct a field" flow is for, so don't hide it.
