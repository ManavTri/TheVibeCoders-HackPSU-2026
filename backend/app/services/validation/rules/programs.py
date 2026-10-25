from datetime import date
from decimal import Decimal

from app.schemas.documents import DocumentType, FinancialDocument
from app.schemas.validation import Finding, Severity
from app.services.validation.rules.base import RuleContext
from app.services.validation.rules.common import (
    build_finding,
    document_entries,
    document_lines,
    evidence_for_document,
    evidence_for_entry,
    format_money,
    term_matches,
)


def program_and_plan_findings(context: RuleContext) -> list[Finding]:
    return (
        _program_double_charge(context)
        + _program_aid_gap(context)
        + _payment_plan_findings(context)
        + _housing_comparison(context)
    )


def program_double_charge_findings(context: RuleContext) -> list[Finding]:
    return _program_double_charge(context)


def program_aid_gap_findings(context: RuleContext) -> list[Finding]:
    return _program_aid_gap(context)


def payment_plan_findings(context: RuleContext) -> list[Finding]:
    return _payment_plan_findings(context)


def housing_comparison_findings(context: RuleContext) -> list[Finding]:
    return _housing_comparison(context)


def _program_double_charge(context: RuleContext) -> list[Finding]:
    quotes = [
        document
        for document in context.documents
        if document.document_type == DocumentType.STUDY_ABROAD_QUOTE
    ]
    bills = [
        document
        for document in context.documents
        if document.document_type == DocumentType.TUITION_BILL
    ]
    findings: list[Finding] = []
    for quote in quotes:
        quote_entries = [
            entry
            for entry in context.ledger.estimates
            if entry.document_id == quote.id
            if entry.kind in {"tuition", "program_fee"}
        ]
        for bill in bills:
            if not term_matches(quote.term, bill.term) or quote.currency != bill.currency:
                continue
            bill_entries = [
                entry
                for entry in document_entries(context.ledger, bill.id)
                if entry.kind == "tuition" and entry.direction == "charge"
            ]
            if not quote_entries or not bill_entries:
                continue
            quote_total = sum((entry.amount for entry in quote_entries), Decimal(0))
            bill_total = sum((entry.amount for entry in bill_entries), Decimal(0))
            findings.append(
                build_finding(
                    rule_id="program.double_charge",
                    severity=Severity.WARNING,
                    category="amount",
                    title=f"{quote.term} has tuition in both a program estimate and a home bill",
                    explanation=(
                        f"{quote.filename} estimates {format_money(quote_total, quote_entries[0].currency)} "
                        f"for program tuition, while {bill.filename} bills "
                        f"{format_money(bill_total, bill_entries[0].currency)} for home tuition in {quote.term}. "
                        "The estimate may not represent an additional billed charge."
                    ),
                    evidence=[
                        *(evidence_for_entry(entry) for entry in quote_entries),
                        *(evidence_for_entry(entry) for entry in bill_entries),
                    ],
                    suggested_action=(
                        f"Ask the study-abroad office and billing office whether the {quote.term} program tuition "
                        "replaces or is added to home-campus tuition."
                    ),
                    document_ids=[quote.id, bill.id],
                    term=quote.term,
                    impact_amount=quote_total,
                    confidence="medium",
                    group_key=f"{quote.term}:{quote.id}:{bill.id}",
                    fields={"program_estimate": quote_total, "home_tuition_bill": bill_total},
                )
            )
    return findings


def _program_aid_gap(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    awards = [
        document
        for document in context.documents
        if document.document_type
        in {DocumentType.AWARD_LETTER, DocumentType.FINANCIAL_AID_PACKAGE}
    ]
    for quote in (
        doc
        for doc in context.documents
        if doc.document_type == DocumentType.STUDY_ABROAD_QUOTE
    ):
        entries = [
            entry
            for entry in context.ledger.estimates
            if entry.document_id == quote.id and entry.direction == "charge"
        ]
        if not entries or not quote.term:
            continue
        covering_awards = [
            award
            for award in awards
            if term_matches(award.term, quote.term)
            and any(
                entry.direction == "credit"
                for entry in document_entries(context.ledger, award.id)
            )
        ]
        if covering_awards:
            continue
        total = sum((entry.amount for entry in entries), Decimal(0))
        findings.append(
            build_finding(
                rule_id="program.aid_gap",
                severity=Severity.INFO,
                category="opportunity",
                title=f"No aid document covers the {quote.term} program estimate",
                explanation=(
                    f"{quote.filename} lists program costs totaling "
                    f"{format_money(total, entries[0].currency)} for {quote.term}, but no uploaded award or "
                    "aid-package document lists aid for that term."
                ),
                evidence=[evidence_for_entry(entry) for entry in entries],
                suggested_action=(
                    f"Ask the study-abroad financial-aid contact whether existing grants can be applied to {quote.term} "
                    "and whether a separate aid application is required."
                ),
                document_ids=[quote.id],
                term=quote.term,
                impact_amount=total,
                confidence="medium",
                group_key=f"{quote.id}:{quote.term}",
            )
        )
    return findings


def _payment_plan_findings(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    award_docs = [
        document
        for document in context.documents
        if document.document_type
        in {
            DocumentType.AWARD_LETTER,
            DocumentType.FINANCIAL_AID_PACKAGE,
            DocumentType.LOAN_OFFER,
        }
    ]
    for plan in (
        doc
        for doc in context.documents
        if doc.document_type == DocumentType.PAYMENT_PLAN
    ):
        installments = [
            item
            for item in document_lines(plan)
            if item.date or "installment" in item.label.casefold()
        ]
        if not installments:
            continue
        fees = [
            item
            for item in document_lines(plan)
            if item not in installments
            and (
                item.kind == "fees"
                or "fee" in f"{item.label} {item.category}".casefold()
            )
        ]
        installment_total = sum((item.amount for item in installments), Decimal(0)) + sum(
            (item.amount for item in fees), Decimal(0)
        )
        stated_total = plan.amount or (plan.extraction_envelope or {}).get("total_amount")
        if stated_total is not None:
            expected_total = Decimal(str(stated_total))
            difference = abs(installment_total - expected_total)
            if difference > context.config.money_tolerance:
                findings.append(
                    build_finding(
                        rule_id="plan.installment_total",
                        severity=Severity.WARNING,
                        category="amount",
                        title=f"{plan.filename} installments differ from the plan balance by {format_money(difference, plan.currency)}",
                        explanation=(
                            f"{plan.filename} lists a plan balance of {format_money(expected_total, plan.currency)}, "
                            f"but the dated/installment entries total {format_money(installment_total, plan.currency)}. "
                            f"The difference is {format_money(difference, plan.currency)}."
                        ),
                        evidence=[
                            evidence_for_document(plan, "amount", "Payment plan balance", expected_total),
                            *(
                                evidence_for_document(plan, "line_items", item.label, item.amount)
                                for item in [*installments, *fees]
                            ),
                        ],
                        suggested_action="Ask the payment-plan administrator to reconcile the installment schedule and stated balance.",
                        document_ids=[plan.id],
                        term=plan.term,
                        impact_amount=difference,
                        confidence="high",
                        group_key=plan.id + ":installment-total",
                        fields={"stated_balance": expected_total, "installment_total": installment_total},
                    )
                )
        dated_installments = [item for item in installments if item.date]
        for installment in dated_installments:
            aid_dates = [
                parsed_date
                for award in award_docs
                if not plan.term or term_matches(plan.term, award.term)
                for parsed_date in _disbursement_dates(award)
            ]
            if not aid_dates:
                continue
            next_aid = min(aid_dates)
            if installment.date >= next_aid:
                continue
            findings.append(
                build_finding(
                    rule_id="plan.installment_total",
                    severity=Severity.WARNING,
                    category="timing",
                    title=f"{installment.label} is due before aid arrives",
                    explanation=(
                        f"{plan.filename} lists {installment.label} of "
                        f"{format_money(installment.amount, plan.currency)} due {installment.date.isoformat()}, "
                        f"before the earliest matching aid disbursement on {next_aid.isoformat()}."
                    ),
                    evidence=[
                        evidence_for_document(
                            plan,
                            "line_items",
                            installment.label,
                            {"amount": installment.amount, "date": installment.date.isoformat()},
                        ),
                        *[
                            evidence_for_document(
                                award,
                                "disbursements",
                                "Aid disbursement",
                                disbursement,
                            )
                            for award in award_docs
                            for disbursement in (award.extraction_envelope or {}).get("disbursements", [])
                            if isinstance(disbursement, dict)
                            and disbursement.get("date") == next_aid.isoformat()
                        ],
                    ],
                    suggested_action=(
                        f"Ask the payment-plan office whether this installment can be deferred until after "
                        f"{next_aid.isoformat()}."
                    ),
                    document_ids=[plan.id, *(award.id for award in award_docs)],
                    term=plan.term,
                    impact_amount=installment.amount,
                    confidence="high",
                    group_key=f"{plan.id}:{installment.label}:{installment.date.isoformat()}",
                    nearest_deadline=installment.date,
                )
            )
    return findings


def _housing_comparison(context: RuleContext) -> list[Finding]:
    contracts = [
        doc for doc in context.documents if doc.document_type == DocumentType.HOUSING_CONTRACT
    ]
    bills = [doc for doc in context.documents if doc.document_type == DocumentType.TUITION_BILL]
    findings: list[Finding] = []
    for contract in contracts:
        contract_entries = [
            entry
            for entry in document_entries(context.ledger, contract.id)
            if entry.kind == "housing" and entry.direction == "charge"
        ]
        for bill in bills:
            bill_entries = [
                entry
                for entry in document_entries(context.ledger, bill.id)
                if entry.kind == "housing" and entry.direction == "charge"
            ]
            if (
                not contract_entries
                or not bill_entries
                or not term_matches(contract.term, bill.term)
                or contract.currency != bill.currency
            ):
                continue
            contract_total = sum((item.amount for item in contract_entries), Decimal(0))
            bill_total = sum((item.amount for item in bill_entries), Decimal(0))
            difference = abs(contract_total - bill_total)
            if difference <= context.config.money_tolerance:
                continue
            findings.append(
                build_finding(
                    rule_id="housing.contract_vs_bill",
                    severity=Severity.WARNING,
                    category="amount",
                    title=f"{contract.term} housing differs by {format_money(difference, contract_entries[0].currency)}",
                    explanation=(
                        f"{contract.filename} lists {format_money(contract_total, contract_entries[0].currency)} "
                        f"for housing, while {bill.filename} lists "
                        f"{format_money(bill_total, bill_entries[0].currency)} in housing charges for {contract.term}. "
                        f"The difference is {format_money(difference, contract_entries[0].currency)}."
                    ),
                    evidence=[
                        *(evidence_for_entry(entry) for entry in contract_entries),
                        *(evidence_for_entry(entry) for entry in bill_entries),
                    ],
                    suggested_action=f"Ask housing and billing offices to reconcile the {contract.term} housing charge.",
                    document_ids=[contract.id, bill.id],
                    term=contract.term,
                    impact_amount=difference,
                    confidence="high",
                    group_key=f"{contract.term}:{contract.id}:{bill.id}",
                    fields={"contract_total": contract_total, "bill_total": bill_total},
                )
            )
    return findings


def _disbursement_dates(document: FinancialDocument) -> list[date]:
    values = (document.extraction_envelope or {}).get("disbursements", [])
    result = []
    if not isinstance(values, list):
        return result
    for item in values:
        if not isinstance(item, dict) or not item.get("date"):
            continue
        try:
            result.append(date.fromisoformat(str(item["date"])))
        except ValueError:
            continue
    return result
