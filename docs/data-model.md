# Data model

The Supabase Postgres schema starts with [`backend/supabase/migrations/20261024000000_initial_schema.sql`](../backend/supabase/migrations/20261024000000_initial_schema.sql), adds duplicate detection and lifecycle timestamps in [`backend/supabase/migrations/20261024000100_dedupe_and_soft_delete.sql`](../backend/supabase/migrations/20261024000100_dedupe_and_soft_delete.sql), and extends the document-type constraint in [`backend/supabase/migrations/20261024000200_document_types.sql`](../backend/supabase/migrations/20261024000200_document_types.sql). Apply migrations in timestamp order. RLS is enabled on each public table.

| Table | Columns and purpose |
|---|---|
| `profiles` | `id` (UUID references `auth.users.id`), `name`, `university`, and `created_at`. An Auth trigger creates a profile when a new user signs up. |
| `documents` | `id`, `user_id`, `type`, `filename`, `storage_path`, `status` (`uploaded` / `extracted` / `failed`), `extracted_json` (`jsonb`), `content_sha256`, `archived_at`, `deleted_at`, and `created_at`. `type` accepts `award_letter`, `tuition_bill`, `financial_aid_package`, `study_abroad_quote`, `loan_offer`, `payment_plan`, `housing_contract`, or `other`. The JSON object stores the full typed extraction envelope, backward-compatible fields, extraction source/confidence, user edits, and optional failure details without requiring a schema migration for every extraction change. |
| `validation_runs` | `id`, `user_id`, `created_at`, and `document_ids` (UUID array). Each run stores the documents it compared. |
| `findings` | `id`, `run_id`, `rule_id`, `severity` (`error` / `warning` / `info`), `title`, `explanation`, `document_ids`, `fields` (`jsonb`), `suggested_action`, and `created_at`. |

## Private document objects

PDF bytes live in the private Supabase Storage bucket `student-documents`, not in Postgres. Object paths use `{user_id}/{document_id}.pdf`. Database rows store the path; API document responses intentionally omit both `storage_path` and `user_id`. The authenticated user can delete the document through the backend, which removes the object and row.

`content_sha256` is unique per user when present, so identical content cannot be uploaded twice by the same user; filenames alone are not unique. Document state is derived from the timestamps: `deleted_at` set means `deleted`, otherwise `archived_at` set means `archived`, otherwise `active`. Archive and soft-delete retain the file and metadata. `DELETE /documents/{id}` remains a permanent deletion.

## Extracted document contract

`FinancialDocument` contains the backward-compatible fields used by the validation rules and existing API consumers:

| Field | Type | Meaning |
|---|---|---|
| `id` | UUID string | Document row ID |
| `filename` | string | Original uploaded filename |
| `document_type` | enum | `award_letter`, `tuition_bill`, `financial_aid_package`, `study_abroad_quote`, `loan_offer`, `payment_plan`, `housing_contract`, `other` |
| `amount` | decimal or null | Explicit amount read from the document |
| `currency` | ISO-4217 string | Defaults to `USD` when not extracted |
| `term` | string or null | Explicit academic term |
| `deadline` | date or null | Explicit due or response date |
| `required_credits` | integer or null | Explicit minimum credit requirement |

The `envelope` member stored alongside those fields in `extracted_json` contains:

| Field | Type | Meaning |
|---|---|---|
| `document_type`, `type_confidence` | enum, number (0-1) | Detected document class and classifier confidence |
| `issuer`, `currency`, `term`, `document_date` | string/date or null | Explicitly stated issuer, currency, term, and date |
| `total_amount`, `required_credits`, `min_gpa` | number or null | Explicitly stated financial/eligibility values |
| `deadlines` | array of `{label, date}` | Explicitly labeled deadlines |
| `line_items` | array of `{label, amount, category, date?}` | Explicit line-item values |
| `disbursements` | array of `{date, amount}` | Explicit payment/disbursement schedule |
| `conditions` | string array | Explicitly stated conditions |
| `summary`, `action_required`, `action_reason` | string, boolean, string or null | Short factual summary and explicit required-action indicator |

Additional JSON keys record `extraction_source` (`gemini` / `fallback`), `type_detected`, `needs_review`, and `user_edited_fields`. The API response adds `category`, `type_confidence`, `type_detected`, review/edit metadata, and the envelope while retaining all legacy fields. A provided upload type is treated as a user override; it remains the effective type while `type_detected` records the model classification.

Gemini is used only when both `LLM_API_KEY` and `LLM_MODEL` are configured. The model receives the PDF as a PDF part, with instructions kept separate; it must treat document content as untrusted data and must not extract SSNs, bank/card numbers, government IDs, student IDs, or home addresses. Every extracted value must be explicitly present; the model and parser do not compute totals or infer missing values. Timeouts, 429/5xx errors, and invalid model output fall back to the existing PDF text parser. Image-only PDFs fail because OCR is not implemented. Extracted PDF text is processed transiently and is not stored or returned.

## Validation and insights

A `ValidationReport` is a read model assembled from a `validation_runs` row, owned documents, and related `findings`. Every `Finding` has `rule_id`, severity, title, explanation, document IDs, compared `fields`, and a `suggested_action`. An insight response derives from the saved report and does not make an eligibility determination.

## Ownership and deletion

The API derives `user_id` only from the verified access-token subject; request bodies cannot choose an owner. All repository selects, updates, and deletes include that owner. Findings are readable only when their run belongs to the current user. Storage is private and row-level policies apply to direct client access.
