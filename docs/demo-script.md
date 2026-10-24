# Three-minute judge demo

Use only the provided synthetic documents. The app does not need API keys or real student data.

## Before the demo

1. Start the API: `make dev`.
2. In another terminal, start the web app: `cd frontend && npm install && npm run dev`.
3. Open the URL printed by Vite (normally `http://localhost:5173`).

## Script (3 minutes)

**0:00–0:30 — Problem.** “Students receive award letters, bills, and program quotes from different sources. Important details can disagree, and it is easy to miss the mismatch.”

**0:30–1:00 — Add documents.** Click **Check my documents**. Add `sample_docs/scenario_1_mismatch/award_letter.pdf` as **Award letter**, and `tuition_bill.pdf` as **Tuition bill**. Click **Analyze documents**.

**1:00–2:10 — Explain the report.** Show the amount, term, deadline, and credit requirement prompts. Explain that each prompt names the source files and that extracted values are not treated as a definitive eligibility decision.

**2:10–2:40 — Next steps.** Show the recommendations panel and emphasize that students should confirm details with their financial-aid office or award provider before acting.

**2:40–3:00 — Responsible scope.** Mention that the demo uses synthetic PDFs, does not send files to an LLM, and currently keeps reports in backend memory only.

## Study-abroad scenario

Upload the synthetic study-abroad quote alongside the synthetic award letter from scenario 2 and explain that term/date/credit prompts can help students prepare questions before committing to costs.
