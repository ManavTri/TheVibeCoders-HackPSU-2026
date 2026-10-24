# Validation rules

Rules only compare fields that the parser can read explicitly. Missing or ambiguous values are omitted, not guessed. A finding is a prompt for the student to verify source documents, not a conclusion that a financial error occurred.

| Rule ID | What it checks | Why it matters | Severity |
|---|---|---|---|
| `amount.award_exceeds_bill` | Same-currency award-letter amount is greater than tuition-bill amount | An apparent overage may mean the award covers other costs or that the student should ask about a refund/disbursement | Medium |
| `deadline.different_dates` | Any two extracted payment/response dates differ | Helps students spot multiple dates and confirm which action each date controls; differing dates are not necessarily contradictory | Low |
| `term.documents_disagree` | Two or more documents state different academic terms | An award may be term-specific, so the student should confirm applicability | High |
| `credits.requirements_disagree` | Two or more documents state different credit-hour requirements | Enrollment level may affect award eligibility | Medium |

Severity indicates the order in which a student may want to review a prompt; it is not an estimate of financial harm. The current parser handles common explicit labels and dates. It can miss values, and it does not perform OCR, currency conversion, eligibility determination, or financial advice.
