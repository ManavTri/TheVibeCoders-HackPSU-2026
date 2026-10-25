# Academic term model

Validation parses academic periods into canonical `Term(season, year)` values
while preserving the original wording in the extracted document. Canonical
ordering is chronological: Fall 2026 < Spring 2027 < Summer 2027. Parsing is a
pure operation; quarter/trimester labels and unrecognized text become
`Term.unknown` rather than raising or being guessed.

## Accepted forms

The parser recognizes season names with full or two-digit years, including:

- `Fall 2026`, `Fall 26`, `Fall Semester 2026`, and `2026 Fall`
- `FA26` (`SP26` and `SU26` are accepted similarly)
- Academic-year forms `Academic Year 2026-2027`, `AY 26-27`, and `2026-27`
- Multi-season year ranges such as `Spring/Fall 2026-27`

An academic year expands to Fall of the first year and Spring of the next year.
Summer is included only when the source explicitly names summer. The parser
does not guess a summer session from dates or from a school's calendar.

`Winter 2026`, quarter/trimester labels such as `Q1 2026`, and malformed year
ranges remain unknown. No institution-specific academic calendar is inferred
from a term label.

## Date inference

When a line item/disbursement has no explicit term, a date can be mapped using
the configurable default calendar:

| Months | Inferred term |
|---|---|
| August–December | Fall of that calendar year |
| January–May | Spring of that calendar year |
| June–July | Summer of that calendar year |

Date-inferred terms carry `inferred=True` and lower confidence. An explicit
term always takes precedence. This default is only an approximation; unusual
academic calendars should supply a custom `AcademicCalendar`.

## Assigning line items and disbursements

Assignment priority:

1. Explicit item/disbursement term.
2. A single explicit document-level term.
3. A date-derived term if neither explicit term applies.
4. Unassigned if none is available.

If a document covers several terms and an item has no term of its own, the
amount is not split evenly or copied across terms. It is stored under
`annual_unallocated` for that academic year. Per-term rules do not treat that
amount as belonging to any single term. An explicitly multi-term item term is
also not allocated to one term.

An item-level term is authoritative even when the document-level term is
unparseable or describes an entire academic year. Rules that compare separate
documents use those assigned item terms; they do not require the document-level
labels to match.

## Ledger and currency semantics

The same rules apply to expected aid disbursements. Explicit per-term
disbursements are attached to that term with their dates; an annual schedule
without per-term information stays unallocated. Provenance is retained for
each amount.

Money uses `Decimal`, quantized to cents. Each document's currency is
preserved. The ledger never sums amounts in different currencies. An
`exchange_rate` is accepted only when the document states it; it is recorded
as source data but this rule-engine version does not perform conversion.

Only tuition-bill entries contribute billed charges, posted aid, and received
payments in net balances. Award-letter and aid-package entries are retained as
cross-check references. Unmatched or under-posted award amounts appear in
`expected_not_yet_billed`, outside net balance. Unbilled housing commitments
appear in `committed_not_yet_billed`; payment-plan installments are recorded
as `scheduled_coverage` and are not treated as received payments. Study-abroad
quotes remain estimates. These extra buckets retain their own source provenance.

Existing documents may lack term or item metadata. Those documents continue
to load; missing/unparseable essentials are grouped into one
`quality.data_gaps` finding per document. Term-dependent rules skip unknown
terms instead of generating generic term/date conflicts.
