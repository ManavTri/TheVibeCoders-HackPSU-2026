
from app.schemas.documents import DocumentType, FinancialDocument
from app.schemas.validation import Finding, Severity


def check_amounts(documents: list[FinancialDocument]) -> list[Finding]:
    awards = [doc for doc in documents if doc.document_type == DocumentType.AWARD_LETTER and doc.amount is not None]
    bills = [doc for doc in documents if doc.document_type == DocumentType.TUITION_BILL and doc.amount is not None]
    findings: list[Finding] = []
    for award in awards:
        for bill in bills:
            if award.currency != bill.currency:
                continue
            if award.amount is not None and bill.amount is not None and award.amount > bill.amount:
                findings.append(
                    Finding(
                        rule_id="amount.award_exceeds_bill",
                        severity=Severity.WARNING,
                        title="Award exceeds tuition bill",
                        explanation="The listed award is larger than the tuition bill. Confirm whether the award covers other costs or is paid as a refund.",
                        document_ids=[award.id, bill.id],
                        fields={"award_amount": str(award.amount), "bill_amount": str(bill.amount)},
                        suggested_action="Ask the financial-aid office how any remaining award balance is disbursed.",
                    )
                )
    return findings


class AmountMismatchRule:
    id = "amount.award_exceeds_bill"

    def check(self, docs: list[FinancialDocument]) -> list[Finding]:
        return check_amounts(docs)
