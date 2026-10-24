# Validation rules

Each rule is a small independent object implementing `Rule.check(docs) -> list[Finding]`. The engine registers rule instances and concatenates their findings. Rules compare only fields the parser can read explicitly; missing and ambiguous values are omitted rather than guessed.

| Rule ID | What it checks | Why it matters | Severity |
|---|---|---|---|
| `amount.award_exceeds_bill` | Same-currency award-letter amount exceeds the tuition-bill amount | An apparent overage may mean the award also covers other costs or that the student should ask about refund/disbursement | `warning` |
| `deadline.different_dates` | Two documents contain different explicit due or response dates | Prompts the student to verify what action each date applies to; different dates are not necessarily contradictory | `info` |
| `term.documents_disagree` | At least two documents state different academic terms | Award eligibility may depend on the term, so applicability should be confirmed | `error` |
| `credits.requirements_disagree` | At least two documents state different minimum credit requirements | Enrollment level may affect award eligibility | `warning` |

Severity is a review priority, not an estimate of financial harm. A finding explains what was compared and suggests a question to ask; it is not a conclusion that a financial error occurred or financial advice. The parser handles common labeled values/dates, does not perform OCR or currency conversion, and can miss or misread details. Students should compare findings with the original documents and confirm them with the issuer.
