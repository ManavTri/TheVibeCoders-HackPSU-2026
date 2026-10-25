# Three-minute judge demo

Use only the synthetic PDFs in `sample_docs/`. The live demo is available at [makemuni.us](https://www.makemuni.us). Sign in with the prepared test account if prompted.

## Demo flow

**0:00 to 0:30: The problem.**

“Documents look funi? Save your muni! Students coordinate award letters, tuition bills, and program quotes from different sources. Muni puts those documents together and surfaces questions worth asking.”

**0:30 to 1:00: Upload.**

Upload `sample_docs/scenario_1_mismatch/award_letter.pdf` and `tuition_bill.pdf`. Leave the type hints blank to show automatic classification. Review the extracted types and fields, then continue to the check.

**1:00 to 1:35: Explain the report.**

Show the mismatched terms, due dates, and credit requirements. Point out the evidence, severity, and suggested next step for each finding. Emphasize that Muni helps students verify details and does not decide eligibility.

**1:35 to 2:15: Correct a field.**

Change an extracted term or credit value, save it, and run the check again. Show that the correction is retained and the report refreshes.

**2:15 to 2:40: Ask the assistant.**

Ask Muni to summarize the current findings or explain one of them. Show that the response cites the student's documents. If the assistant proposes a change, the user must confirm it.

**2:40 to 3:00: Close.**

Show the private document library and the delete control. Mention that the demo uses synthetic data, Gemini is optional, and the insight summary is deterministic.
