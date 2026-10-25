# Frontend/backend API gaps

The current frontend uses the existing backend contract for PDF upload and extraction, document listing and correction, saved validation reports, insights, and current findings. Document archive, restore, soft-delete, and permanent-delete actions are wired to the corresponding lifecycle routes. This list tracks functionality that would require additional backend API work; it is not a list of broken current flows.

| Priority | API functionality to add | Why it is not covered today | Current workaround / status |
|---|---|---|---|
| Medium | `GET /profiles/me` and `PATCH /profiles/me` | Sign-up collects a name in Supabase Auth metadata, but the frontend cannot retrieve or edit the `profiles` row or university. | The dashboard uses generic welcome copy. |
| Medium | `GET /validations` with pagination | The API can fetch a report only when the frontend already has its run ID; it cannot list prior report history. | A newly created report is opened directly after upload or correction. |
| Medium | `POST /documents/batch` with per-file results | The upload screen sends one request per PDF. If a later upload fails (including a duplicate), earlier successful uploads remain in the library. | The frontend reports the failed request; already-created documents remain available in the library. |
| Medium | Add supported schemas and extraction rules for FAFSA, bank statements, and other financial records | The backend contract currently accepts only award letters, tuition bills, and study-abroad quotes. | The upload UI requires a user-selected supported type rather than silently misclassifying unsupported files. |
| Low | Pagination and query filters for `GET /documents` | State filtering exists, but large libraries cannot request a bounded page or search filenames/types. | The frontend loads all documents in one state; acceptable for the current hackathon scale. |
| Low | `POST /insights/chat` or equivalent conversation endpoint | There is no conversational assistant API; saved-report insights are generated as a fixed summary. | The AI Chat page explains the limitation and directs users to validated insight summaries. |

Already available and now integrated: `GET /findings`, `GET /documents?state=...`, `POST /documents/{id}/archive`, `POST /documents/{id}/restore`, `POST /documents/{id}/delete`, and `DELETE /documents/{id}`. `GET /documents/{id}/file` also exists; the current side-by-side report intentionally renders extracted fields rather than embedding PDF previews.
