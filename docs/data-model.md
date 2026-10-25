# Data model

The Supabase Postgres schema starts with
[`backend/supabase/migrations/20261024000000_initial_schema.sql`](../backend/supabase/migrations/20261024000000_initial_schema.sql),
adds duplicate detection and lifecycle timestamps in
[`backend/supabase/migrations/20261024000100_dedupe_and_soft_delete.sql`](../backend/supabase/migrations/20261024000100_dedupe_and_soft_delete.sql),
extends the document-type constraint in
[`backend/supabase/migrations/20261024000200_document_types.sql`](../backend/supabase/migrations/20261024000200_document_types.sql),
and adds validation finding details in
[`backend/supabase/migrations/20261024000300_term_ledger_findings.sql`](../backend/supabase/migrations/20261024000300_term_ledger_findings.sql).
Apply migrations in timestamp order. The final migration adds only nullable
`findings.details jsonb`; it does not change existing findings columns.

| Table | Columns and purpose |
|---|---|
| `profiles` | `id` (UUID references `auth.users.id`), `name`, `university`, and `created_at`. An Auth trigger creates a profile when a new user signs up. |
| `documents` | `id`, `user_id`, `type`, `filename`, `storage_path`, `status` (`uploaded` / `extracted` / `failed`), `extracted_json` (`jsonb`), `content_sha256`, `archived_at`, `deleted_at`, and `created_at`. `type` accepts `award_letter`, `tuition_bill`, `financial_aid_package`, `study_abroad_quote`, `loan_offer`, `payment_plan`, `housing_contract`, or `other`. |
| `validation_runs` | `id`, `user_id`, `created_at`, and `document_ids` (UUID array). Each run stores the documents it compared. |
| `findings` | Existing columns `id`, `run_id`, `rule_id`, `severity`, `title`, `explanation`, `document_ids`, `fields`, `suggested_action`, and `created_at`, plus nullable `details` (`jsonb`) for additive fields such as deterministic finding ID, category, term, impact, confidence, evidence, group key, and assist provenance. |

## Private document objects and lifecycle

PDF bytes live in the private Supabase Storage bucket `student-documents`,
not in Postgres. Object paths use `{user_id}/{document_id}.pdf`. Database rows
store the path; API document responses omit `storage_path` and `user_id`.
`content_sha256` is unique per user when present, so identical content cannot
be uploaded twice by the same user; filenames alone are not unique.

Document state is derived from timestamps: `deleted_at` set means `deleted`,
otherwise `archived_at` set means `archived`, otherwise `active`. Archive and
soft-delete retain the file and metadata. `DELETE /documents/{id}` remains a
permanent deletion. Current findings, ledger totals, and default validation
runs use active, successfully extracted documents only.

## Extracted document contract

`FinancialDocument` retains the backward-compatible fields used by current
routes and consumers:

| Field | Type | Meaning |
|---|---|---|
| `id`, `filename` | string | Document row ID and original filename |
| `document_type` | enum | One of the eight supported document types |
| `amount` | decimal or null | Explicit document total (legacy-compatible) |
| `currency` | string | Currency stated by the document or `USD` fallback |
| `term` | string or null | Explicit document term |
| `deadline` | date or null | Earliest explicit due/response date in the legacy contract |
| `required_credits` | integer or null | Explicit award minimum credit requirement |

The extraction envelope is stored under `documents.extracted_json.envelope`
alongside legacy fields and extraction metadata. Existing rows may have only
the earlier fields; all new fields below are optional and treated as absent
when not present.

| Envelope field | Type | Meaning |
|---|---|---|
| `document_type`, `type_confidence` | enum, number (0–1) | Detected type and confidence |
| `issuer`, `currency`, `term`, `document_date` | string/date or null | Explicit issuer, currency, term, and document date |
| `total_amount`, `required_credits`, `min_gpa` | decimal/integer or null | Explicit total and eligibility values |
| `deadlines[]` | `{label, date}` | Explicit labeled response/enrollment/payment/submission or renewal dates |
| `line_items[]` | `{label, amount, category, date?, direction?, term?, kind?}` | Amounts with optional stated economic direction, canonicalizable term, and kind |
| `disbursements[]` | `{date, amount, term?, award_label?}` | Explicit aid schedule details |
| `enrollment_credits` | integer or null | Explicit student enrollment credits |
| `academic_year`, `terms[]` | string or null/list | Explicit academic year and all terms covered |
| `payment_due_dates[]` | `{label, date, term?}` | Explicitly labeled payment due dates, optionally term-scoped |
| `exchange_rate` | decimal or null | An exchange rate stated in the document; never calculated |
| `conditions`, `summary`, `action_required`, `action_reason` | list/string/boolean/string or null | Explicit conditions and factual summary/action metadata |

Line-item `direction` is `charge`, `credit`, or `unknown`; `kind` is one of
`tuition`, `fees`, `housing`, `meals`, `books`, `travel`, `program_fee`,
`insurance`, `other_charge`, `scholarship`, `grant`, `loan`, `work_study`,
`waiver`, `payment`, `refund`, or `other`. If these are absent, the validation
normalizer applies deterministic label keywords; unknown direction is not
guessed from a negative sign.

`extracted_json` also records `extraction_source` (`gemini` / `fallback`),
`type_detected`, `type_confidence`, `needs_review`, `user_edited_fields`, and
optional failure details. A provided upload type remains the user override;
`type_detected` retains the classified type.

## Term-aware ledger and findings

The ledger is a pure read model, not a persisted table. Its `terms`, `total`,
`annual_unallocated`, and `estimates` sections are generated from active
extracted records. Each money entry carries document/filename, label, amount,
currency, term, source, and confidence provenance. Term totals contain
charges by kind, aid by kind, payments, expected disbursements, net balance,
coverage ratio, gap, and surplus. Values remain separated by currency.
Program quotes and cost-of-attendance estimates do not become billed charges.
Amounts from multi-term documents without per-item terms remain in the
academic-year `annual_unallocated` bucket.

Each `Finding` retains its legacy fields and adds optional `category`, `term`,
`impact_amount`, `confidence`, `evidence[]`, `group_key`, and `via`. New saved
run details live in `findings.details`; reads of older rows without `details`
continue to construct findings from the legacy columns. IDs are deterministic
hashes over the rule, term, sorted document IDs, and stable subject key.

See [`docs/term-model.md`](./term-model.md) for term parsing and allocation,
and [`docs/validation-rules.md`](./validation-rules.md) for all rule inputs,
thresholds, severity, and examples.

## Ownership and deletion

The API derives `user_id` only from the verified access-token subject; request
bodies cannot choose an owner. All repository selects, updates, and deletes
include that owner. Findings are readable only when their run belongs to the
current user. Storage is private and row-level policies apply to direct client
access. Real financial documents should not be used for development or demos.
