# Validation rules

The deterministic validation path is `normalize -> term-aware ledger -> rules ->
deduplicate/sort/cap`. Rules receive a `RuleContext` containing the active
extracted documents, an immutable-by-convention ledger read model, an injected
`today`, and a `ValidationConfig`. They perform no I/O, make no LLM calls, and
do not use the wall clock. Dates and amounts not present in source documents
are not invented. Cross-currency totals are never added together.

For billed balances, tuition bills are authoritative: only their charges,
posted aid credits, and received payments affect term net balances. Award
letters and aid packages are references used for comparisons; a missing award
amount is listed under `expected_not_yet_billed`, not subtracted from the bill.
Housing contracts without a billed housing line are listed under
`committed_not_yet_billed`. Payment-plan installments are listed as scheduled
coverage, never as received payments. Quotes remain estimates.

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
| `award.amount_mismatch` | amount | Matches award-letter/aid-package entries to other award entries and posted bill credits by normalized name, canonical per-item term, and currency. Billing remains the balance source; reference awards never add aid to the ledger. Low-confidence amount-only matches do not trigger it. | `error` when the difference exceeds `$0.01`; high/medium name match required. | “Alder Ridge Merit Scholarship differs by `$500.00` for Spring 2027” (scenario 3). |
| `award.disbursement_split` | amount | Compares the sum of explicit scheduled disbursements with the explicitly stated total award amount. Does not infer missing installments. | `warning` when the difference exceeds `$0.01`. | “split-award.pdf disbursements differ from the stated award by `$100.00`” (`disbursement split` scenario). |
| `timing.disbursement_after_due` | timing | Compares an explicit aid disbursement date only with an explicit payment-due date for the same term. It never compares arbitrary document dates. | `warning` when the disbursement is after the due date. | “late-award.pdf disburses `$1,000.00` 32 days after the Fall 2026 payment deadline” (`disbursement after payment due date` scenario). |
| `timing.deadline_status` | timing | Evaluates labeled response, enrollment, payment, submission, FAFSA, and renewal dates. Explicit payment due dates are reported only while the canonical term has a positive billed net balance after posted aid and received payments. Expected aid does not reduce that balance; when it can cover the balance it can only downgrade the timing severity. The same labeled date across documents is deduplicated. | Non-payment deadlines: `error` when overdue, `warning` within 7 days, `info` within 14 days. Payment deadlines are skipped at a net balance of `$0.01` or less. | “Payment due on 2026-09-15” is suppressed for a fully paid Fall term; a nearby loan-acceptance deadline remains actionable. |
| `eligibility.credit_requirement` | eligibility | Compares an award's minimum credits with explicitly stated enrollment credits for the same canonical term. Per-item terms take precedence over multi-term or unparseable document-level terms. Groups GPA and other unverifiable award conditions into one informational finding per award. | `error` when reported enrollment is below the minimum; `info` when enrollment or award conditions cannot be verified. | “Spring bill reports 9 credits, below the 12-credit award requirement” (scenario 3). |
| `duplicate.award` | duplicate | Detects repeated normalized award names with identical amounts and terms, including repeated entries within one document. Bill credits are not treated as a second award document. | `warning`; exact amount/term/name match required. | “Promise Scholarship appears 2 times for Fall 2026” (`duplicate award` scenario). |
| `coverage.over_cost_of_attendance` | coverage | Compares listed aid for an academic year to an explicitly labeled cost-of-attendance estimate. The estimate stays outside billed charges. | `warning` when aid exceeds the estimate by more than `$0.01`; no currency conversion. | “Aid exceeds the stated 2025-2026 cost estimate by `$2,000.00`” (`aid exceeds cost estimate` scenario). |
| `program.double_charge` | amount | Compares only tuition-kind program estimate lines with home-bill tuition lines for the same canonical per-item term and currency. Other estimate lines remain in evidence but are excluded from tuition impact. | `warning`; impact is the smaller of the two tuition totals; estimate and bill remain separate ledger sections. | Scenario 3 includes `$8,400.00` program tuition and `$6,750.00` home tuition; impact is `$6,750.00`, with fees still shown as evidence. |
| `program.aid_gap` | opportunity | A term-specific program estimate has no uploaded award/aid document covering that term. | `info`; only emitted when the quote has a parseable term and explicit cost. | “No aid document covers the Fall 2026 program estimate” (same program scenario). |
| `loan.offer_mismatch` | amount / data_quality | Compares similarly named loan amounts in loan offers and aid packages for the same term/currency; separately calls out explicitly listed origination fees/rates without computing net proceeds. | `warning` for differing matched amounts beyond `$0.01`; `info` for gross/net or fee details requiring confirmation. | “Federal Direct Loan differs by `$500.00` for Fall 2026” (`loan offer mismatch` scenario). |
| `plan.installment_total` | amount / timing | Compares the sum of dated/installment amounts plus separately listed fees with the stated plan balance, and flags an installment due before matching aid arrives. | `warning` when the balance differs by more than `$0.01`, or the installment precedes aid. | “plan.pdf installments differ from the plan balance by `$200.00`” (`installments differ from plan balance` scenario). |
| `housing.contract_vs_bill` | amount | Compares housing charges in a housing contract and tuition bill by canonical per-item term and currency, even when the contract's document-level term is an academic year. | `warning` when amounts differ by more than `$0.01`; equal terms are not reported. | Scenario 3 reports the Spring 2027 contract/bill difference of `$200.00`; Fall matches. |
| `currency.mismatch` | data_quality | Reports multiple currencies in one term. It never sums those currencies. A stated rate is recorded but does not trigger conversion by this rule engine. | One `warning` per affected term unless an exchange rate is explicitly stated. | “Fall 2026 contains amounts in multiple currencies” (`multiple currencies are not summed` scenario). |
| `quality.data_gaps` | data_quality | One grouped finding per document for missing/unparseable term, amount, dates, or low-confidence type. A parseable per-item term or explicit envelope term satisfies the term requirement even when the document-level label is unparseable or multi-term. | `info`; repeated missing fields are grouped by document. | Scenario 3's multi-term housing contract is not reported as missing a term. |

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
