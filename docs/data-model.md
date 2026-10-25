# Data model

The Supabase Postgres schema starts with [`backend/supabase/migrations/20261024000000_initial_schema.sql`](../backend/supabase/migrations/20261024000000_initial_schema.sql) and adds duplicate detection and lifecycle timestamps in [`backend/supabase/migrations/20261024000100_dedupe_and_soft_delete.sql`](../backend/supabase/migrations/20261024000100_dedupe_and_soft_delete.sql). RLS is enabled on each public table.

| Table | Columns and purpose |
|---|---|
| `profiles` | `id` (UUID references `auth.users.id`), `name`, `university`, and `created_at`. An Auth trigger creates a profile when a new user signs up. |
| `documents` | `id`, `user_id`, `type`, `filename`, `storage_path`, `status` (`uploaded` / `extracted` / `failed`), `extracted_json` (`jsonb`), `content_sha256`, `archived_at`, `deleted_at`, and `created_at`. The JSON object stores changing extracted fields and optional extraction failure details without requiring a schema migration for every extraction tweak. |
| `validation_runs` | `id`, `user_id`, `created_at`, and `document_ids` (UUID array). Each run stores the documents it compared. |
| `findings` | `id`, `run_id`, `rule_id`, `severity` (`error` / `warning` / `info`), `title`, `explanation`, `document_ids`, `fields` (`jsonb`), `suggested_action`, and `created_at`. |

## Private document objects

PDF bytes live in the private Supabase Storage bucket `student-documents`, not in Postgres. Object paths use `{user_id}/{document_id}.pdf`. Database rows store the path; API document responses intentionally omit both `storage_path` and `user_id`. The authenticated user can delete the document through the backend, which removes the object and row.

`content_sha256` is unique per user when present, so identical content cannot be uploaded twice by the same user; filenames alone are not unique. Document state is derived from the timestamps: `deleted_at` set means `deleted`, otherwise `archived_at` set means `archived`, otherwise `active`. Archive and soft-delete retain the file and metadata. `DELETE /documents/{id}` remains a permanent deletion.

## Extracted document contract

`FinancialDocument` mirrors the JSON payload used in `documents.extracted_json`:

| Field | Type | Meaning |
|---|---|---|
| `id` | UUID string | Document row ID |
| `filename` | string | Original uploaded filename |
| `document_type` | enum | `award_letter`, `tuition_bill`, `study_abroad_quote` |
| `amount` | decimal or null | Explicit amount read from the document |
| `currency` | ISO-4217 string | Defaults to `USD` when not extracted |
| `term` | string or null | Explicit academic term |
| `deadline` | date or null | Explicit due or response date |
| `required_credits` | integer or null | Explicit minimum credit requirement |

Extracted PDF text is processed transiently and is not stored in `extracted_json` or returned by the API.

## Validation and insights

A `ValidationReport` is a read model assembled from a `validation_runs` row, owned documents, and related `findings`. Every `Finding` has `rule_id`, severity, title, explanation, document IDs, compared `fields`, and a `suggested_action`. An insight response derives from the saved report and does not make an eligibility determination.

## Ownership and deletion

The API derives `user_id` only from the verified access-token subject; request bodies cannot choose an owner. All repository selects, updates, and deletes include that owner. Findings are readable only when their run belongs to the current user. Storage is private and row-level policies apply to direct client access.
