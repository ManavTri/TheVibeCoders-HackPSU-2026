from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding, Severity


def check_deadlines(documents: list[FinancialDocument]) -> list[Finding]:
    dated = [doc for doc in documents if doc.deadline is not None]
    findings: list[Finding] = []
    for index, first in enumerate(dated):
        for second in dated[index + 1 :]:
            if first.deadline == second.deadline:
                continue
            findings.append(
                Finding(
                    rule_id="deadline.different_dates",
                    severity=Severity.INFO,
                    title="Multiple payment or response dates",
                    explanation=f"{first.filename} and {second.filename} list different dates. Verify which date applies to each action.",
                    document_ids=[first.id, second.id],
                    fields={
                        "first_deadline": first.deadline.isoformat(),
                        "second_deadline": second.deadline.isoformat(),
                    },
                    suggested_action="Confirm which action each date applies to and add the relevant dates to your calendar.",
                )
            )
    return findings


class DeadlineConflictRule:
    id = "deadline.different_dates"

    def check(self, docs: list[FinancialDocument]) -> list[Finding]:
        return check_deadlines(docs)
