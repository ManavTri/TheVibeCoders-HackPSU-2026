# Three-minute judge demo

Use the provided synthetic PDFs only. For a local demo, leave backend Supabase settings unset (development uses an in-memory repository and local-demo identity) and use the synthetic files. For a deployed demo, sign in with a dedicated test account and upload the same synthetic files.

## Before the demo

1. Start the API from `backend/`: `python -m uvicorn app.main:app --reload`.
2. Install frontend dependencies once from the repo root with `make frontend-install`, then start it with `make frontend` (or run `npm ci` then `npm run dev` from `frontend/`). Do not rerun `npm ci` while a Vite server is running; stop it first.
3. Open `http://localhost:5173` (or the deployed Vercel demo URL).
4. If using the deployed demo, sign in with the prepared test account. Never use real student financial data.

## Script (3 minutes)

**0:00–0:30 — Problem.** “Students coordinate award letters, tuition bills, and program quotes from different sources. ClearLedger puts those documents together and surfaces questions worth asking.”

**0:30–1:00 — Upload.** Click **Check my documents**. Add `sample_docs/scenario_1_mismatch/award_letter.pdf` as **Award letter**, and `tuition_bill.pdf` as **Tuition bill**. Click **Analyze documents**.

**1:00–1:35 — Explain the report.** Show the mismatched academic terms, due dates, and credit requirements. Point to the finding IDs, severity levels, compared fields, and suggested follow-up actions. Explain that the app prompts verification; it does not determine eligibility.

**1:35–2:15 — Correction is part of the workflow.** Expand **Correct extracted fields** for one document, correct its term or credits to match the other statement, and save. The app persists the correction, runs validation again, and opens the new report.

**2:15–2:40 — Manage documents.** Return to the overview to show the per-user document library and delete control. Explain that documents are stored in a private bucket, protected by user-scoped access, and can be deleted.

**2:40–3:00 — Responsible scope.** “Only synthetic documents in this demo. When configured, Gemini classifies and extracts explicitly stated fields; otherwise the local parser is used. Image-only PDFs need OCR. The insight summary is deterministic, not financial or eligibility advice.”

## Study-abroad scenario

Upload the synthetic scholarship letter and study-abroad quote in `sample_docs/scenario_2_study_abroad/`. The expected JSON records the date and credit-rule prompts. Amounts for study-abroad quotes are not currently compared as tuition bills.
