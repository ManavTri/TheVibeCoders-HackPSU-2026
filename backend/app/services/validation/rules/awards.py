from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.schemas.documents import DocumentType, FinancialDocument
from app.schemas.validation import Finding, Severity
from app.services.validation.normalize import match_awards, normalize_award_name
from app.services.validation.rules.base import RuleContext
from app.services.validation.rules.common import (
    build_finding,
    document_entries,
    document_lines,
    evidence_for_document,
    evidence_for_entry,
    format_money,
    is_award_type,
    term_matches,
)

_AID_KINDS = {"scholarship", "grant", "loan", "work_study", "waiver"}


def award_findings(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_missing_on_bill(context))
    findings.extend(_unsupported_bill_credit(context))
    findings.extend(_amount_mismatches(context))
    findings.extend(_disbursement_splits(context))
    findings.extend(_duplicate_awards(context))
    findings.extend(_loan_offer_mismatches(context))
    return findings


def _missing_on_bill(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    awards = [doc for doc in context.documents if is_award_type(doc)]
    bills = [doc for doc in context.documents if doc.document_type == DocumentType.TUITION_BILL]
    for award in awards:
        for award_entry in document_entries(context.ledger, award.id):
            if award_entry.kind not in {"scholarship", "grant", "waiver"}:
                continue
            if not award_entry.term:
                continue
            matching_bills = [
                bill
                for bill in bills
                if any(
                    term_matches(award_entry.term, credit.term)
                    for credit in document_entries(context.ledger, bill.id)
                )
            ]
            if not matching_bills:
                continue
            supported = False
            for bill in matching_bills:
                for credit in document_entries(context.ledger, bill.id):
                    if credit.direction != "credit":
                        continue
                    if credit.currency != award_entry.currency:
                        continue
                    match = match_awards(
                        name_a=award_entry.label,
                        term_a=award_entry.term,
                        amount_a=award_entry.amount,
                        name_b=credit.label,
                        term_b=credit.term,
                        amount_b=credit.amount,
                        fuzzy_threshold=context.config.fuzzy_match_threshold,
                    )
                    if match.tier in {"high", "medium"}:
                        supported = True
                        break
                if supported:
                    break
            if supported:
                continue
            disbursements = _disbursements_for_term(award, award_entry.term)
            future = [item for item in disbursements if item[0] and item[0] > context.today]
            upcoming = min(future, default=(None, None), key=lambda pair: pair[0] or date.max)
            severity = Severity.INFO if upcoming[0] else Severity.WARNING
            expectation = (
                f" A listed disbursement is expected on {upcoming[0].isoformat()}."
                if upcoming[0]
                else " No future disbursement date was found."
            )
            findings.append(
                build_finding(
                    rule_id="award.missing_on_bill",
                    severity=severity,
                    category="amount",
                    title=f"{award_entry.label} is not shown as a {award_entry.term} bill credit",
                    explanation=(
                        f"{award.filename} lists {format_money(award_entry.amount, award_entry.currency)} "
                        f"for {award_entry.term}, but no matching credit was found on a tuition bill for that term."
                        + expectation
                    ),
                    evidence=[evidence_for_entry(award_entry)],
                    suggested_action=(
                        f"Check with the financial-aid office whether {award_entry.label} will post to the "
                        f"{award_entry.term} bill"
                        + (f" after {upcoming[0].isoformat()}." if upcoming[0] else " before paying the balance.")
                    ),
                    document_ids=[award.id, *(bill.id for bill in matching_bills)],
                    term=award_entry.term,
                    impact_amount=award_entry.amount,
                    confidence="medium",
                    group_key=f"{award_entry.term}:{award_entry.label.casefold()}",
                    fields={
                        "award_amount": award_entry.amount,
                        "expected_disbursement_date": upcoming[0].isoformat() if upcoming[0] else None,
                    },
                    nearest_deadline=upcoming[0],
                )
            )
    return findings


def _unsupported_bill_credit(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    awards = [doc for doc in context.documents if is_award_type(doc)]
    bills = [doc for doc in context.documents if doc.document_type == DocumentType.TUITION_BILL]
    for bill in bills:
        unmatched = []
        for credit in document_entries(context.ledger, bill.id):
            if credit.direction != "credit" or credit.kind not in {"scholarship", "grant", "waiver"}:
                continue
            if not credit.term:
                continue
            supported = False
            for award in awards:
                for award_entry in document_entries(context.ledger, award.id):
                    if credit.currency != award_entry.currency:
                        continue
                    match = match_awards(
                        name_a=credit.label,
                        term_a=credit.term,
                        amount_a=credit.amount,
                        name_b=award_entry.label,
                        term_b=award_entry.term,
                        amount_b=award_entry.amount,
                        fuzzy_threshold=context.config.fuzzy_match_threshold,
                    )
                    if match.tier in {"high", "medium"}:
                        supported = True
                        break
                if supported:
                    break
            if not supported:
                unmatched.append(credit)
        if not unmatched:
            continue
        confidence = "high" if all(entry.confidence == "high" for entry in unmatched) else "low"
        findings.append(
            build_finding(
                rule_id="bill.unsupported_credit",
                severity=Severity.WARNING if confidence == "high" else Severity.INFO,
                category="data_quality",
                title=f"{bill.filename} lists {len(unmatched)} credit(s) without a matching award document",
                explanation=(
                    "The listed bill credits could not be matched to an award or financial-aid package: "
                    + "; ".join(
                        f"{entry.label} ({format_money(entry.amount, entry.currency)})"
                        for entry in unmatched
                    )
                    + ". The credit may be valid, but its source is not represented in the uploaded set."
                ),
                evidence=[evidence_for_entry(entry) for entry in unmatched],
                suggested_action=(
                    "Check the source of each listed credit with the billing office and upload its award notice if available."
                ),
                document_ids=[bill.id],
                term=unmatched[0].term if len({entry.term for entry in unmatched}) == 1 else None,
                impact_amount=sum((entry.amount for entry in unmatched), Decimal(0)),
                confidence=confidence,
                group_key=bill.id,
                fields={"unmatched_credits": [entry.label for entry in unmatched]},
            )
        )
    return findings


def _amount_mismatches(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    awards = [doc for doc in context.documents if is_award_type(doc)]
    bills = [
        doc for doc in context.documents if doc.document_type == DocumentType.TUITION_BILL
    ]
    for index, first in enumerate(awards):
        for second in awards[index + 1 :]:
            for first_entry in document_entries(context.ledger, first.id):
                if first_entry.kind not in _AID_KINDS or not first_entry.term:
                    continue
                for second_entry in document_entries(context.ledger, second.id):
                    if second_entry.kind not in _AID_KINDS:
                        continue
                    if first_entry.currency != second_entry.currency:
                        continue
                    match = match_awards(
                        name_a=first_entry.label,
                        term_a=first_entry.term,
                        amount_a=first_entry.amount,
                        name_b=second_entry.label,
                        term_b=second_entry.term,
                        amount_b=second_entry.amount,
                        fuzzy_threshold=context.config.fuzzy_match_threshold,
                    )
                    difference = abs(first_entry.amount - second_entry.amount)
                    if match.tier not in {"high", "medium"} or difference <= context.config.money_tolerance:
                        continue
                    findings.append(
                        build_finding(
                            rule_id="award.amount_mismatch",
                            severity=Severity.ERROR,
                            category="amount",
                            title=f"{first_entry.label} differs by {format_money(difference, first_entry.currency)} for {first_entry.term}",
                            explanation=(
                                f"{first.filename} lists {format_money(first_entry.amount, first_entry.currency)} "
                                f"for {first_entry.term}; {second.filename} lists "
                                f"{format_money(second_entry.amount, second_entry.currency)} for the same award and term. "
                                f"The difference is {format_money(difference, first_entry.currency)}."
                            ),
                            evidence=[
                                evidence_for_entry(first_entry),
                                evidence_for_entry(second_entry),
                            ],
                            suggested_action=(
                                f"Ask the award provider to confirm the {first_entry.term} amount and request a corrected notice if needed."
                            ),
                            document_ids=[first.id, second.id],
                            term=first_entry.term,
                            impact_amount=difference,
                            confidence=match.tier,
                            group_key=f"{first_entry.term}:{first_entry.label.casefold()}",
                            fields={
                                "first_amount": first_entry.amount,
                                "second_amount": second_entry.amount,
                                "difference": difference,
                            },
                        )
                    )
    for award in awards:
        for bill in bills:
            for award_entry in document_entries(context.ledger, award.id):
                if award_entry.kind not in _AID_KINDS or not award_entry.term:
                    continue
                for credit in document_entries(context.ledger, bill.id):
                    if credit.direction != "credit" or credit.kind not in _AID_KINDS:
                        continue
                    if credit.currency != award_entry.currency:
                        continue
                    match = match_awards(
                        name_a=award_entry.label,
                        term_a=award_entry.term,
                        amount_a=award_entry.amount,
                        name_b=credit.label,
                        term_b=credit.term,
                        amount_b=credit.amount,
                        fuzzy_threshold=context.config.fuzzy_match_threshold,
                    )
                    difference = abs(award_entry.amount - credit.amount)
                    if (
                        match.tier not in {"high", "medium"}
                        or difference <= context.config.money_tolerance
                    ):
                        continue
                    findings.append(
                        build_finding(
                            rule_id="award.amount_mismatch",
                            severity=Severity.ERROR,
                            category="amount",
                            title=f"{award_entry.label} differs by {format_money(difference, award_entry.currency)} for {award_entry.term}",
                            explanation=(
                                f"{award.filename} lists {format_money(award_entry.amount, award_entry.currency)} "
                                f"for {award_entry.term}; {bill.filename} credits "
                                f"{format_money(credit.amount, credit.currency)} for the same award and term. "
                                f"The difference is {format_money(difference, award_entry.currency)}."
                            ),
                            evidence=[
                                evidence_for_entry(award_entry),
                                evidence_for_entry(credit),
                            ],
                            suggested_action=(
                                f"Ask the award provider to confirm the {award_entry.term} amount and request a corrected notice if needed."
                            ),
                            document_ids=[award.id, bill.id],
                            term=award_entry.term,
                            impact_amount=difference,
                            confidence=match.tier,
                            group_key=f"{award_entry.term}:{award_entry.label.casefold()}:{bill.id}",
                            fields={
                                "award_amount": award_entry.amount,
                                "bill_credit": credit.amount,
                                "difference": difference,
                            },
                        )
                    )
    return findings


def _disbursement_splits(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for document in context.documents:
        envelope = document.extraction_envelope or {}
        raw_disbursements = envelope.get("disbursements", [])
        stated_total = envelope.get("total_amount", document.amount)
        if not isinstance(raw_disbursements, list) or not raw_disbursements or stated_total is None:
            continue
        amounts = [
            Decimal(str(item["amount"]))
            for item in raw_disbursements
            if isinstance(item, dict) and item.get("amount") is not None
        ]
        if not amounts:
            continue
        difference = abs(Decimal(str(stated_total)) - sum(amounts, Decimal(0)))
        if difference <= context.config.money_tolerance:
            continue
        evidence = [
            evidence_for_document(
                document,
                "total_amount",
                "Stated total",
                str(stated_total),
            )
        ]
        evidence.extend(
            evidence_for_document(
                document,
                "disbursements",
                str(item.get("award_label") or "Disbursement"),
                item.get("amount"),
            )
            for item in raw_disbursements
            if isinstance(item, dict) and item.get("amount") is not None
        )
        findings.append(
            build_finding(
                rule_id="award.disbursement_split",
                severity=Severity.WARNING,
                category="amount",
                title=f"{document.filename} disbursements differ from the stated award by {format_money(difference, document.currency)}",
                explanation=(
                    f"{document.filename} states a total of {format_money(Decimal(str(stated_total)), document.currency)}, "
                    f"but its listed disbursements sum to {format_money(sum(amounts, Decimal(0)), document.currency)}. "
                    f"The difference is {format_money(difference, document.currency)}."
                ),
                evidence=evidence,
                suggested_action="Ask the award provider to reconcile the listed installments with the stated award total.",
                document_ids=[document.id],
                term=document.term,
                impact_amount=difference,
                confidence="high",
                group_key=document.id,
                fields={"stated_total": str(stated_total), "disbursement_total": str(sum(amounts, Decimal(0)))},
            )
        )
    return findings


def _duplicate_awards(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    award_entries = [
        entry
        for document in context.documents
        if is_award_type(document)
        for entry in document_entries(context.ledger, document.id)
        if entry.kind in _AID_KINDS and entry.term
    ]
    grouped: dict[tuple[str, str, Decimal, str], list] = defaultdict(list)
    for entry in award_entries:
        name = " ".join(sorted(normalize_award_name(entry.label)))
        if name:
            grouped[(name, entry.term or "", entry.amount, entry.currency)].append(entry)
    for (name, term, amount, currency), entries in grouped.items():
        if len(entries) < 2:
            continue
        findings.append(
            build_finding(
                rule_id="duplicate.award",
                severity=Severity.WARNING,
                category="duplicate",
                title=f"{name.title()} appears {len(entries)} times for {term}",
                explanation=(
                    f"{len(entries)} award entries use the same normalized name, amount "
                    f"({format_money(amount, currency)}), and term ({term}). They may be duplicate records."
                ),
                evidence=[evidence_for_entry(entry) for entry in entries],
                suggested_action="Confirm with the financial-aid office whether these entries represent one award or separate awards.",
                document_ids=[entry.document_id for entry in entries],
                term=term,
                impact_amount=amount,
                confidence="medium",
                group_key=f"{name}:{term}:{amount}:{currency}",
                fields={"award_name": name, "amount": amount, "occurrences": len(entries)},
            )
        )
    return findings


def _loan_offer_mismatches(context: RuleContext) -> list[Finding]:
    offers = [doc for doc in context.documents if doc.document_type == DocumentType.LOAN_OFFER]
    packages = [
        doc
        for doc in context.documents
        if doc.document_type == DocumentType.FINANCIAL_AID_PACKAGE
    ]
    findings: list[Finding] = []
    for offer in offers:
        for package in packages:
            for offer_entry in document_entries(context.ledger, offer.id):
                if offer_entry.kind != "loan":
                    continue
                for package_entry in document_entries(context.ledger, package.id):
                    if package_entry.kind != "loan":
                        continue
                    if offer_entry.currency != package_entry.currency:
                        continue
                    match = match_awards(
                        name_a=offer_entry.label,
                        term_a=offer_entry.term,
                        amount_a=offer_entry.amount,
                        name_b=package_entry.label,
                        term_b=package_entry.term,
                        amount_b=package_entry.amount,
                        fuzzy_threshold=context.config.fuzzy_match_threshold,
                    )
                    difference = abs(offer_entry.amount - package_entry.amount)
                    if match.tier not in {"high", "medium"} or difference <= context.config.money_tolerance:
                        continue
                    findings.append(
                        build_finding(
                            rule_id="loan.offer_mismatch",
                            severity=Severity.WARNING,
                            category="amount",
                            title=f"{offer_entry.label} differs by {format_money(difference, offer_entry.currency)} for {offer_entry.term or 'the stated period'}",
                            explanation=(
                                f"{offer.filename} lists {format_money(offer_entry.amount, offer_entry.currency)}; "
                                f"{package.filename} lists {format_money(package_entry.amount, package_entry.currency)} "
                                f"for a similarly labeled loan. The difference is {format_money(difference, offer_entry.currency)}."
                            ),
                            evidence=[
                                evidence_for_entry(offer_entry),
                                evidence_for_entry(package_entry),
                            ],
                            suggested_action="Ask the lender and financial-aid office whether both figures are gross loan amounts or net proceeds after fees.",
                            document_ids=[offer.id, package.id],
                            term=offer_entry.term,
                            impact_amount=difference,
                            confidence=match.tier,
                            group_key=f"{offer_entry.term}:{offer_entry.label.casefold()}",
                            fields={"offer_amount": offer_entry.amount, "package_amount": package_entry.amount},
                        )
                    )
        if any(
            any(token in item.label.casefold() for token in ("origination fee", "interest rate", "apr"))
            for item in document_lines(offer)
        ):
            evidence = [
                evidence_for_document(offer, "line_items", item.label, item.amount)
                for item in document_lines(offer)
                if any(token in item.label.casefold() for token in ("origination fee", "interest rate", "apr"))
            ]
            findings.append(
                build_finding(
                    rule_id="loan.offer_mismatch",
                    severity=Severity.INFO,
                    category="data_quality",
                    title=f"Confirm whether {offer.filename} shows gross or net loan proceeds",
                    explanation=(
                        f"{offer.filename} includes a listed loan fee or rate. The displayed offer amount may differ "
                        "from the amount deposited after fees; no net amount was calculated."
                    ),
                    evidence=evidence,
                    suggested_action="Ask the lender for the net disbursement amount, APR, and fee schedule before accepting the offer.",
                    document_ids=[offer.id],
                    term=offer.term,
                    confidence="medium",
                    group_key=offer.id + ":net-vs-gross",
                )
            )
    return findings


def _disbursements_for_term(document: FinancialDocument, term: str):
    raw = (document.extraction_envelope or {}).get("disbursements", [])
    matches = []
    if not isinstance(raw, list):
        return matches
    for item in raw:
        if not isinstance(item, dict) or not item.get("date"):
            continue
        item_term = item.get("term") or document.term
        if not term_matches(str(item_term) if item_term else None, term):
            continue
        try:
            due = date.fromisoformat(str(item["date"]))
        except ValueError:
            continue
        matches.append((due, item))
    return matches
