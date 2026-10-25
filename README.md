# Muni — Student Financial Cross-Check

**Documents look funi? Save your muni!**

Manage scholarships, tuition bills, and study-abroad costs in one place. Catch details worth double-checking and leave with a clearer next step.

Muni extracts labeled fields from student financial PDFs, compares them with explainable validation rules, and helps students prepare questions for their school or award provider. Findings are prompts to verify—not financial advice or eligibility decisions.

## Architecture

```mermaid
flowchart LR
  Student --> Web[Vercel: React + Vite]
  Web -->|Auth0 access token + PDF| API[Render: FastAPI]
  Web --> Auth[Auth0]
  API --> Verify[Verify Auth0 JWT]
  Verify --> Repo[Repository boundary]
  Repo --> DB[(Supabase Postgres)]
  Repo --> Storage[Private Supabase Storage]
  API --> Extract[Gemini extraction with parser fallback]
  Extract --> Rules[Validation rule engine]
  Rules --> DB
  API --> Web
```

The React app prefers Auth0 and sends its access token to the FastAPI API. If Auth0 is not fully configured, it falls back to Supabase Auth. The API selects the verifier from the token issuer, uses a deterministic UUID mapping for Auth0 subjects to preserve the existing Supabase UUID foreign keys, and accesses Postgres/private Storage with a server-only service key. Supabase is used for persistence in every deployment and can also provide fallback authentication. **Every database and object-storage operation belongs in [`backend/app/db/repositories.py`](backend/app/db/repositories.py).**

The frontend-to-backend feature mapping and pending API work are tracked in [`docs/api-gaps.md`](docs/api-gaps.md).

## Final submission snapshot

Muni is a student-finance document review workspace. Students can upload financial PDFs, review extracted fields, correct them, compare active documents, inspect explainable findings, and ask the Muni assistant questions grounded in their document library. The interface is intentionally focused on clarity: it surfaces details worth verifying without presenting results as financial advice or eligibility decisions.

- **Authentication:** Auth0 is preferred for the deployed frontend and API. Supabase Auth remains a supported fallback when Auth0 is not fully configured.
- **Persistence:** Supabase Postgres and private Storage, accessed only through the FastAPI backend.
- **Extraction:** Local PDF text extraction by default, with optional Gemini-assisted classification and extraction when backend model settings are configured.
- **Deployment:** Vercel hosts the Vite frontend; Render hosts the FastAPI service. Required provider setup is documented in [`docs/deployment.md`](docs/deployment.md).
- **Demo flow:** The prepared synthetic scenarios and presentation script are documented in [`docs/demo-script.md`](docs/demo-script.md).

## Deployment

- Backend: Render blueprint in [`render.yaml`](render.yaml).
- Frontend: Vercel project rooted at `frontend/`, with SPA rewrites in [`frontend/vercel.json`](frontend/vercel.json).
- Database and private document storage: apply the Supabase migrations in [`backend/supabase/migrations/`](backend/supabase/migrations/) in timestamp order. Configure Auth0 separately for authentication.
- Step-by-step provider setup, secrets, and smoke checks: [deployment guide](docs/deployment.md).
- **Live demo:** not published yet. Deploy the Render Blueprint and Vercel project using the deployment guide, then add their public URLs here.

Provider accounts and secrets are not available in this workspace, so the deployment configuration is prepared but no live Render or Vercel deployment has been created from this checkout.

## Local development

Requirements: Python 3.11+, Node.js 22+ and npm installed inside Ubuntu/WSL. Keep the checkout and `node_modules` on the Ubuntu filesystem (for example, `~/Code/TheVibeCoders-HackPSU-2026`), not under `/mnt/c`; Windows-mounted folders can lock Windows-native packages and make even Linux `npm ci` fail. The Make targets reject Windows Node/npm inherited through WSL's PATH. Local API mode uses in-memory repositories if Supabase credentials are absent. For authenticated local development, configure an Auth0 SPA application/API and copy the app-specific env examples.

```bash
# Terminal 1 — backend (WSL/Linux)
cd backend
python -m pip install -e ".[test]"
python -m uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm ci
npm run dev
```

Alternatively, from the repository root run `make frontend-install` once, then
`make frontend` to start the dev server. `make frontend` does not reinstall
dependencies. Stop the frontend server before running `make frontend-install`
again after dependency changes because `npm ci` removes and recreates
`node_modules`.

Open `http://localhost:5173`; backend health is at `http://localhost:8000/health`, and API docs are at `http://localhost:8000/docs`.

For authenticated local development, apply all migrations in timestamp order to your Supabase project, copy `backend/.env.example` to `backend/.env`, set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`, and set `REQUIRE_AUTH=true`. For the preferred Auth0 path, also set `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` on the backend, and set `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, and `VITE_AUTH0_AUDIENCE` in `frontend/.env.local`. If Auth0 is not configured, set the frontend Supabase URL and anon key instead. Always set `VITE_API_URL` to the backend origin. Never put service-role keys, Auth0 client secrets, or LLM secrets in frontend variables.

## API

All API paths are prefixed by `/api`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/documents` | Upload a PDF to private Storage, optionally accept a `document_type_hint`, and classify/extract fields; Gemini's classification is authoritative |
| `GET` | `/documents?state=active\|archived\|deleted` | List documents in the selected state (defaults to active) |
| `GET` | `/documents/{id}` | Read document fields and extraction status |
| `PATCH` | `/documents/{id}` | Correct extracted fields |
| `POST` | `/documents/{id}/reextract` | Re-run extraction while retaining user-corrected fields |
| `POST` | `/documents/{id}/archive` | Archive a document without removing its file |
| `POST` | `/documents/{id}/restore` | Restore an archived or soft-deleted document |
| `POST` | `/documents/{id}/delete` | Soft-delete a document without removing its file |
| `DELETE` | `/documents/{id}` | Permanently delete the private file and document row |
| `GET` | `/findings?term=&severity=&category=&include=all` | Compute and filter findings from active, successfully extracted documents; the default limits informational findings |
| `GET` | `/findings/report` | Return current findings and a severity/at-risk/deadline/per-term summary |
| `GET` | `/ledger` | Return per-term and total charges, aid, payments, balances, estimates, and provenance |
| `POST` | `/validations` | Validate all extracted user documents or the supplied `document_ids` |
| `GET` | `/validations/{run_id}` | Load a saved validation report |
| `POST` | `/insights` | Create a student-oriented summary from `{ "run_id": "..." }` |
| `POST` | `/ai/chat` | Ask the authenticated user's financial planning assistant; returns reply, suggestions, sources, and pending write actions |
| `POST` | `/ai/actions/{id}/confirm` | Explicitly confirm a pending archive, restore, correction, re-extraction, or recheck action |
| `POST` | `/ai/actions/{id}/cancel` | Cancel a pending AI-proposed write action |

Validation normalizes academic terms and builds a deterministic ledger before applying the rules. Study-abroad quotes and cost estimates are kept separate from billed charges, and totals are never combined across currencies. See [`docs/term-model.md`](docs/term-model.md) and [`docs/validation-rules.md`](docs/validation-rules.md).

The upload UI accepts an optional document-type hint, then shows the extracted classification and fields for review and correction before validation. Gemini determines the saved type; a user's hint only informs classification and never overrides it. The comparison uses the newly uploaded, successfully extracted documents. After a student corrects a field on a report, the app calls `PATCH /documents/{id}`, starts a new validation run, and opens the refreshed report.
The chat assistant does not persist conversation history. Common document lists, findings, deadlines, summaries, and help responses use local templates without Gemini; only open-ended questions require backend-only `LLM_API_KEY` and `LLM_MODEL`. Single-tool answers also avoid an extra model round trip. Edits, re-extraction, and validation rechecks require explicit confirmation. Chat requests are limited to 20 per user per 10 minutes, and action confirmations/cancellations to 10 per 10 minutes; the backend also caps pending actions. See [`docs/agent-design.md`](docs/agent-design.md) for details.

## Project commands

- `make dev` — start the backend API.
- `make test` — run backend tests.
- `make seed` — locate the synthetic sample files.
- `cd frontend && npm run build` — type-check and build the frontend.
- `cd backend && ruff check app tests` — lint the backend.
- `cd backend && python scripts/eval_extraction.py` — optionally compare Gemini extraction against synthetic scenario rules; exits with a skip message if `LLM_API_KEY` or `LLM_MODEL` is unset.

## Synthetic demo data

Use only PDFs under `sample_docs/`. Scenario 1 deliberately puts an award and bill in different terms; the ledger analyzes them separately rather than flagging a term difference by itself. Scenario 2 pairs a scholarship with a study-abroad estimate. Each scenario's `expected.json` lists expected findings and findings that should not appear. The PDFs are synthetic and contain no real student data.

## Data, safety, and limitations

- Supabase Postgres and private Storage are the production persistence path; local development falls back to in-memory repositories only when backend Supabase credentials are absent.
- Uploaded PDFs are stored in a private bucket, scoped under the authenticated user's ID. The backend checks ownership and deletes the Storage object as part of document deletion.
- Auth0 is the preferred authentication provider. The frontend obtains Auth0 access tokens when configured, otherwise it uses Supabase Auth; the API verifies the selected token issuer, audience, and signature server-side. The Supabase service key is used for persistence, and production requires at least one configured authentication provider.
- When `LLM_API_KEY` and `LLM_MODEL` are configured, the backend sends the PDF bytes to Gemini for one structured classification-and-extraction call. Gemini failures, timeouts, rate limits, server errors, and invalid responses fall back to the local PDF text parser. Without an API key/model, the parser is used directly. Image-only PDFs fail extraction; OCR is not implemented.
- The term-aware ledger uses explicitly extracted line items and schedule details. Amount-only legacy documents are supported with low confidence; unknown terms are not silently assigned to a term, and unitemized multi-term figures are kept in `annual_unallocated`.
- Gemini receives PDF bytes separately from its instructions; PDF text is treated as untrusted data. Prompts prohibit extracting SSNs, bank/card numbers, government IDs, student IDs, and home addresses. The application does not store extracted PDF text or log the model output. Review Google's API data-handling terms before sending real financial documents.
- Insight summaries are deterministic rules-based prompts; no document text is sent to an LLM.
- Use synthetic data for demos and development. Real financial records need a reviewed retention, deletion, backup, incident-response, and compliance policy before launch.

See the [three-minute demo script](docs/demo-script.md), [architecture](docs/architecture.md), [data model](docs/data-model.md), and [validation rules](docs/validation-rules.md).
