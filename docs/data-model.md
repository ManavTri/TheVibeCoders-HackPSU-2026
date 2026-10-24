# Data model

## FinancialDocument

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Upload-batch document identifier |
| `filename` | string | Original client filename |
| `document_type` | enum | `award_letter`, `tuition_bill`, or `study_abroad_quote` |
| `amount` | decimal, optional | Explicitly extracted USD amount |
| `currency` | string | Currently defaults to USD |
| `term` | string, optional | Academic term such as `Fall 2026` |
| `deadline` | date, optional | Explicit deadline/payment date |
| `required_credits` | integer, optional | Explicit credit-hour requirement |
| `extracted_text` | string | Extracted selectable PDF text; do not persist in production without consent/retention controls |

## ValidationReport

A report has an opaque ID, UTC creation timestamp, document summaries, findings, and a human-readable summary. Each finding includes a stable `rule_id`, severity, explanation, relevant document IDs, and comparison details. The prototype's repository is process-local memory; IDs are not durable across restarts.

## Insights

Insights are recommendations derived from report findings, not a separate financial product or eligibility decision. They include a disclaimer directing students to confirm details with the institution or award provider.
