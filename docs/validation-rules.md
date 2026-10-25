# Validation rules

The deterministic validation path is `normalize -> term-aware ledger -> rules ->
deduplicate/sort/cap`. Rules receive a `RuleContext` containing the active
extracted documents, an immutable-by-convention ledger read model, an injected
`today`, and a `ValidationConfig`. They perform no I/O, make no LLM calls, and
do not use the wall clock. Dates and amounts not present in source documents
are not invented. Cross-currency totals are never added together.

All money comparisons use `Decimal` quantized to cents. The default tolerance
is `$0.01`. A finding includes stable IDs, source evidence (document, filename,
field, label, and extracted value), a concrete next step, and where applicable
the term, impact amount, confidence, and group key.

## Rule catalogue

| Rule ID | Category | Inputs and logic | Severity and tolerance | Example produced by a fixture |
|---|---|---|---|---|
| `coverage.term_gap` | coverage | Per-term billed charges less aid and payments; reports largest charge lines, due date, and whether expected disbursements could close the gap. | `error` when its payment due date has passed; otherwise `warning`. Ignore balances at or below `$0.01`. | “Fall 2026 has a `$500.00` unpaid balance” (`term gap` scenario). |
| `coverage.term_surplus` | coverage | Per-term aid and payments above billed charges; identifies possible refund/account credit and another term's gap when present. | `info` only; requires surplus above `$0.01`. | “Fall 2026 shows a `$1,200.00` surplus” (`term surplus` scenario). |
| `award.missing_on_bill` | amount | An explicitly named award credit for a term has no matching credit on an uploaded tuition bill for that term. A future listed disbursement changes the finding to `info`; otherwise it is `warning`. | `info` for a future scheduled disbursement, `warning` if none is future. Award match must be high/medium confidence. | “North Grant is not shown as a Fall 2026 bill credit” (`award missing on bill` scenario). |
| `bill.unsupported_credit` | data_quality | Groups bill scholarship/grant/waiver credits that cannot be matched to an award or aid-package entry of the same term and currency. | `warning` for confidently classified credits; `info` when classification confidence is low. Amounts are not compared across currencies. | “unmatched-bill.pdf lists 1 credit without a matching award document” (`unsupported bill credit` scenario). |
| `award.amount_mismatch` | amount | Matches award entries by normalized name and canonical term, then compares the amounts from award letters/aid packages in the same currency. Low-confidence amount-only matches do not trigger it. | `error` when the difference exceeds `$0.01`; high/medium name match required. | “North Scholarship differs by `$200.00` for Fall 2026” (`award amount mismatch` scenario). |
| `award.disbursement_split` | amount | Compares the sum of explicit scheduled disbursements with the explicitly stated total award amount. Does not infer missing installments. | `warning` when the difference exceeds `$0.01`. | “split-award.pdf disbursements differ from the stated award by `$100.00`” (`disbursement split` scenario). |
| `timing.disbursement_after_due` | timing | Compares an explicit aid disbursement date only with an explicit payment-due date for the same term. It never compares arbitrary document dates. | `warning` when the disbursement is after the due date. | “late-award.pdf disburses `$1,000.00` 32 days after the Fall 2026 payment deadline” (`disbursement after payment due date` scenario). |
| `timing.deadline_status` | timing | Evaluates labeled response, enrollment, payment, submission, FAFSA, and renewal dates. The same labeled date across documents is deduplicated. | `error` when overdue; `warning` within 7 days; `info` within 14 days. | “Renewal response on 2026-06-30 was overdue by 1 day” (`overdue labeled deadline` scenario). |
| `eligibility.credit_requirement` | eligibility | Compares an award's minimum credits with explicitly stated enrollment credits for the same term. Groups GPA and other unverifiable award conditions into one informational finding per award. | `error` when reported enrollment is below the minimum; `info` when enrollment or award conditions cannot be verified. | “credit-bill.pdf reports 9 credits, below the 12-credit award requirement” (`credit eligibility` scenario). |
| `duplicate.award` | duplicate | Detects repeated normalized award names with identical amounts and terms, including repeated entries within one document. Bill credits are not treated as a second award document. | `warning`; exact amount/term/name match required. | “Promise Scholarship appears 2 times for Fall 2026” (`duplicate award` scenario). |
| `coverage.over_cost_of_attendance` | coverage | Compares listed aid for an academic year to an explicitly labeled cost-of-attendance estimate. The estimate stays outside billed charges. | `warning` when aid exceeds the estimate by more than `$0.01`; no currency conversion. | “Aid exceeds the stated 2025-2026 cost estimate by `$2,000.00`” (`aid exceeds cost estimate` scenario). |
| `program.double_charge` | amount | Compares a study-abroad/program tuition estimate with a home tuition bill for the same term and currency. | `warning`; estimate and bill remain separate ledger sections. | “Fall 2026 has tuition in both a program estimate and a home bill” (`program tuition double charge and aid gap` scenario). |
| `program.aid_gap` | opportunity | A term-specific program estimate has no uploaded award/aid document covering that term. | `info`; only emitted when the quote has a parseable term and explicit cost. | “No aid document covers the Fall 2026 program estimate” (same program scenario). |
| `loan.offer_mismatch` | amount / data_quality | Compares similarly named loan amounts in loan offers and aid packages for the same term/currency; separately calls out explicitly listed origination fees/rates without computing net proceeds. | `warning` for differing matched amounts beyond `$0.01`; `info` for gross/net or fee details requiring confirmation. | “Federal Direct Loan differs by `$500.00` for Fall 2026” (`loan offer mismatch` scenario). |
| `plan.installment_total` | amount / timing | Compares the sum of dated/installment amounts plus separately listed fees with the stated plan balance, and flags an installment due before matching aid arrives. | `warning` when the balance differs by more than `$0.01`, or the installment precedes aid. | “plan.pdf installments differ from the plan balance by `$200.00`” (`installments differ from plan balance` scenario). |
| `housing.contract_vs_bill` | amount | Compares housing charges in a housing contract and tuition bill for the same term and currency. | `warning` when amounts differ by more than `$0.01`. | “Fall 2026 housing differs by `$500.00`” (`housing contract differs from bill` scenario). |
| `currency.mismatch` | data_quality | Reports multiple currencies in one term. It never sums those currencies. A stated rate is recorded but does not trigger conversion by this rule engine. | One `warning` per affected term unless an exchange rate is explicitly stated. | “Fall 2026 contains amounts in multiple currencies” (`multiple currencies are not summed` scenario). |
| `quality.data_gaps` | data_quality | One grouped finding per document for missing/unparseable term, amount, dates, or low-confidence type. A term gap explicitly says that term-dependent checks were skipped. | `info`; repeated missing fields are grouped by document. | “unknown-0.pdf is missing 4 validation detail(s)” (`unknown terms` noise test). |

The examples above are generated from JSON-envelope fixtures in
`backend/tests/fixtures/term_ledger_scenarios.json` and
`backend/tests/test_validation_engine.py`; they do not require Gemini or PDFs.
The sample PDFs in `sample_docs/` remain synthetic and also exercise the
fallback extractor.

## Noise control and limitations

The default response displays at most 3 `info` findings and 20 findings total.
`GET /findings?include=all` retrieves the uncapped result. Findings are sorted
by severity, impact amount, nearest action deadline, then deterministic ID.
Equivalent group keys are merged and evidence is combined. Unknown terms
suppress term-dependent comparisons; they do not create generic “terms differ”
or “dates differ” findings.

The `RuleAssist` protocol and `RULE_ASSIST_ENABLED` flag exist as an optional
extension point. The default is `NullAssist`; no Gemini-backed classification
or award matching is implemented. Any future assist must require both the LLM
and feature flags and have every candidate verified by deterministic same-term
and amount-tolerance checks before use.

These findings identify items to verify, not adjudications or financial,
legal, or tax advice. Check the original statement and confirm with the issuer.
