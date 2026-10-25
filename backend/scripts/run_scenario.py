"""Run a synthetic document scenario through the local upload and validation APIs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, get_args, get_origin

from fastapi.testclient import TestClient
from pydantic import BaseModel

for _name, _value in {
    "REQUIRE_AUTH": "false",
    "SUPABASE_URL": "",
    "SUPABASE_SERVICE_KEY": "",
    "SUPABASE_JWT_SECRET": "",
    "LLM_API_KEY": "",
    "LLM_MODEL": "",
}.items():
    os.environ[_name] = _value

from app.db.repositories import list_documents
from app.main import app
from app.schemas.documents import ExtractionEnvelope, FinancialDocument
from app.services.extraction.extractor import ExtractionResult
from app.services.validation.ledger import build_ledger
from app.services.validation.normalize import (
    assign_item_term,
    match_awards,
    parse_terms,
)
from app.services.validation.rules.common import document_entries, document_lines

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORY = BACKEND.parent
DEFAULT_OUTPUT = BACKEND / ".scenario3-out"
TODAY = date(2026, 10, 25)


class ScenarioExtractor:
    def __init__(self, scenario_dir: Path) -> None:
        self.scenario_dir = scenario_dir
        self.envelopes: dict[str, ExtractionEnvelope] = {}
        self.validation_issues: list[str] = []

    def extract(
        self,
        *,
        document_id: str,
        filename: str,
        pdf_bytes: bytes,
        document_type_override=None,
    ) -> ExtractionResult:
        del pdf_bytes
        aliases = {
            "01_award_letter_AY2026-27": "01_award_letter",
            "02_fall_2026_bill": "02_fall_2026_bill",
            "03_spring_2027_bill": "03_spring_2027_bill",
            "04_study_abroad_quote_spring_2027": "04_study_abroad_quote",
            "05_housing_contract_2026-27": "05_housing_contract",
            "06_payment_plan_spring_2027": "06_payment_plan",
        }
        envelope_path = self.scenario_dir / "envelopes" / f"{aliases[Path(filename).stem]}.json"
        raw = json.loads(envelope_path.read_text(encoding="utf-8"))
        envelope = ExtractionEnvelope.model_validate(raw)
        self.validation_issues.extend(_unknown_fields(raw, ExtractionEnvelope, f"{filename}."))
        self.envelopes[filename] = envelope
        document = FinancialDocument(
            id=document_id,
            filename=filename,
            document_type=document_type_override or envelope.document_type,
            amount=envelope.total_amount,
            currency=envelope.currency or "USD",
            term=envelope.term,
            deadline=min((item.date for item in envelope.deadlines), default=None),
            required_credits=envelope.required_credits,
            extraction_envelope=envelope.model_dump(mode="json"),
            type_confidence=envelope.type_confidence,
        )
        return ExtractionResult(
            document=document,
            envelope=envelope,
            extraction_source="fallback",
            type_detected=envelope.document_type,
            type_confidence=envelope.type_confidence,
            needs_review=envelope.type_confidence < 0.6,
        )


def _unknown_fields(value: Any, model: type, path: str = "") -> list[str]:
    if not isinstance(value, dict):
        return []
    known = model.model_fields
    errors = [f"{path}{key}" for key in value if key not in known]
    for name, field in known.items():
        if name not in value:
            continue
        annotation = field.annotation
        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin is list and args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
            for index, item in enumerate(value[name]):
                errors.extend(_unknown_fields(item, args[0], f"{path}{name}[{index}]."))
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            errors.extend(_unknown_fields(value[name], annotation, f"{path}{name}."))
    return errors


def _patch_today(monkeypatch) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls) -> date:
            return TODAY

    from app.api.routes import findings, ledger

    monkeypatch.setattr(findings, "date", FixedDate)
    monkeypatch.setattr(ledger, "date", FixedDate)


class _Patch:
    def __init__(self) -> None:
        self._restore: list[tuple[object, str, object]] = []

    def setattr(self, target: object, name: str, value: object) -> None:
        self._restore.append((target, name, getattr(target, name)))
        setattr(target, name, value)

    def undo(self) -> None:
        for target, name, value in reversed(self._restore):
            setattr(target, name, value)
        self._restore.clear()


def run_scenario(
    scenario_dir: Path,
    output_dir: Path,
    client: TestClient,
    monkeypatch,
) -> tuple[int, str]:
    scenario_dir = scenario_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    extractor = ScenarioExtractor(scenario_dir)
    from app.services.extraction.extractor import get_document_extractor

    app.dependency_overrides[get_document_extractor] = lambda: extractor
    _patch_today(monkeypatch)
    try:
        for pdf_path in sorted(scenario_dir.glob("*.pdf")):
            response = client.post(
                "/api/documents",
                files={"file": (pdf_path.name, pdf_path.read_bytes(), "application/pdf")},
            )
            if response.status_code != 201:
                raise RuntimeError(
                    f"Upload failed for {pdf_path.name}: {response.status_code} {response.text}"
                )

        if len(extractor.envelopes) != 6:
            raise RuntimeError(f"Expected six validated envelopes, got {len(extractor.envelopes)}.")
        if extractor.validation_issues:
            raise RuntimeError(
                "ExtractionEnvelope silently dropped fields: "
                + ", ".join(extractor.validation_issues)
            )
        findings_route = client.get("/api/findings?include=all")
        ledger_route = client.get("/api/ledger")
        report_route = client.get("/api/findings/report")
        for label, response in (
            ("findings", findings_route),
            ("ledger", ledger_route),
            ("findings report", report_route),
        ):
            if response.status_code != 200:
                raise RuntimeError(f"{label} failed: {response.status_code} {response.text}")

        documents = [
            FinancialDocument.model_validate(record)
            for record in list_documents("local-demo", state="active")
            if record["status"] == "extracted"
        ]
        ledger = build_ledger(documents, today=TODAY)
        payloads = {
            "ledger.json": ledger_route.json(),
            "findings.json": findings_route.json(),
            "findings-report.json": report_route.json(),
        }
        for filename, payload in payloads.items():
            (output_dir / filename).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        term_rows = []
        for filename, envelope in extractor.envelopes.items():
            term_rows.append((filename, "document", envelope.term))
            for index, item in enumerate(envelope.line_items):
                if item.term:
                    term_rows.append((filename, f"line_items[{index}]", item.term))
            for index, item in enumerate(envelope.disbursements):
                if item.term:
                    term_rows.append((filename, f"disbursements[{index}]", item.term))
            for index, item in enumerate(envelope.payment_due_dates):
                if item.term:
                    term_rows.append((filename, f"payment_due_dates[{index}]", item.term))

        from app.services.validation.normalize import parse_terms

        table = [
            "| Document / field | Term string | Season | Year | Inferred |",
            "|---|---|---|---:|---|",
        ]
        for filename, field, term_string in term_rows:
            term = parse_terms(term_string).terms
            if len(term) == 1:
                table.append(
                    f"| {filename} · {field} | {term_string} | {term[0].season or 'unknown'} | "
                    f"{term[0].year or '—'} | {term[0].inferred} |"
                )
            else:
                for parsed in term:
                    table.append(
                        f"| {filename} · {field} | {term_string} | {parsed.season or 'unknown'} | "
                        f"{parsed.year or '—'} | {parsed.inferred} |"
                    )
        term_table = "\n".join(table) + "\n"
        (output_dir / "terms.md").write_text(term_table, encoding="utf-8")
        diagnostics = _matching_diagnostics(documents, ledger)
        (output_dir / "matching-decisions.md").write_text(diagnostics, encoding="utf-8")

        checker = subprocess.run(
            [
                sys.executable,
                str(scenario_dir / "check_expected.py"),
                str(output_dir / "findings.json"),
                str(scenario_dir / "expected.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        checker_output = checker.stdout + checker.stderr
        (output_dir / "check_expected.txt").write_text(checker_output, encoding="utf-8")
        print(
            "ENVELOPE VALIDATION: all six passed; no silently dropped fields; "
            "no field renames applied."
        )
        print("TERM PARSING")
        print(term_table)
        print("LEDGER WITH PROVENANCE")
        print(json.dumps(payloads["ledger.json"], indent=2, sort_keys=True))
        print("MATCHING DECISIONS")
        print(diagnostics)
        print("FINDINGS")
        for finding in payloads["findings.json"]:
            print(
                json.dumps(
                    {
                        key: finding.get(key)
                        for key in ("rule_id", "term", "severity", "impact_amount", "title", "explanation", "evidence")
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        print("CHECK EXPECTED")
        print(checker_output)
        return checker.returncode, checker_output
    finally:
        app.dependency_overrides.pop(get_document_extractor, None)


def _matching_diagnostics(documents, ledger) -> str:
    awards = [
        doc for doc in documents if doc.document_type.value in {"award_letter", "financial_aid_package"}
    ]
    bills = [doc for doc in documents if doc.document_type.value == "tuition_bill"]
    contracts = [doc for doc in documents if doc.document_type.value == "housing_contract"]
    output = ["# Rule matching diagnostics", ""]
    for award in awards:
        for bill in bills:
            for award_entry in document_entries(ledger, award.id):
                for bill_entry in document_entries(ledger, bill.id):
                    if (
                        award_entry.direction != "credit"
                        or bill_entry.direction != "credit"
                        or award_entry.kind not in {"scholarship", "grant", "loan", "waiver"}
                        or bill_entry.kind not in {"scholarship", "grant", "loan", "waiver"}
                    ):
                        continue
                    match = match_awards(
                        name_a=award_entry.label,
                        term_a=award_entry.term,
                        amount_a=award_entry.amount,
                        name_b=bill_entry.label,
                        term_b=bill_entry.term,
                        amount_b=bill_entry.amount,
                    )
                    if award_entry.currency != bill_entry.currency:
                        reason = "skipped: currencies differ"
                    elif award_entry.term != bill_entry.term:
                        reason = "skipped: canonical item terms differ"
                    elif match.tier not in {"high", "medium"}:
                        reason = "skipped: normalized-name confidence below high/medium"
                    else:
                        reason = "compared"
                    output.append(
                        f"- Award/bill `{award.filename}` / `{bill.filename}`: "
                        f"{award_entry.label} ({award_entry.term}, {award_entry.amount}) vs "
                        f"{bill_entry.label} ({bill_entry.term}, {bill_entry.amount}); "
                        f"tier={match.tier}, similarity={match.similarity:.3f}; {reason}."
                    )
    for contract in contracts:
        for bill in bills:
            contract_entries = [
                entry for entry in document_entries(ledger, contract.id)
                if entry.kind == "housing" and entry.direction == "charge"
            ]
            bill_entries = [
                entry for entry in document_entries(ledger, bill.id)
                if entry.kind == "housing" and entry.direction == "charge"
            ]
            for contract_entry in contract_entries:
                for bill_entry in bill_entries:
                    if contract_entry.term == bill_entry.term and contract_entry.currency == bill_entry.currency:
                        reason = "compared"
                    else:
                        reason = "skipped: canonical item term or currency differs"
                    output.append(
                        f"- Housing `{contract.filename}` / `{bill.filename}`: "
                        f"{contract_entry.term} {contract_entry.amount} vs "
                        f"{bill_entry.term} {bill_entry.amount}; tier=n/a; {reason}."
                    )
    for award in awards:
        required = (award.extraction_envelope or {}).get("required_credits")
        if required is None:
            continue
        award_terms = sorted({
            entry.term for entry in document_entries(ledger, award.id)
            if entry.direction == "credit" and entry.term
        })
        for bill in bills:
            bill_terms = {
                str(assignment.term)
                for item in document_lines(bill)
                if (
                    assignment := assign_item_term(
                        item_term=item.term,
                        document_term=bill.term,
                        document_terms=(bill.extraction_envelope or {}).get("terms", []),
                        item_date=item.date,
                    )
                ).term
                and assignment.term.is_known
            }
            if not bill_terms:
                bill_terms = {
                    str(term) for term in parse_terms(bill.term).terms if term.is_known
                }
            for award_term in award_terms:
                if award_term in bill_terms:
                    decision = (
                        f"required={required}, enrollment="
                        f"{(bill.extraction_envelope or {}).get('enrollment_credits')}; compared."
                    )
                else:
                    decision = (
                        f"bill terms={sorted(bill_terms)}; skipped: canonical terms differ."
                    )
                output.append(
                    f"- Eligibility `{award.filename}` / `{bill.filename}`: "
                    f"award term={award_term}, tier=n/a; {decision}"
                )
    return "\n".join(output) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_scenario.py <scenario_dir>", file=sys.stderr)
        return 2
    from app.db.repositories import clear_repositories

    scenario_dir = Path(sys.argv[1])
    if not scenario_dir.is_absolute():
        scenario_dir = (Path.cwd() / scenario_dir).resolve()
    clear_repositories()
    with TestClient(app) as client:
        monkeypatch = _Patch()
        try:
            result, _ = run_scenario(scenario_dir, DEFAULT_OUTPUT, client, monkeypatch)
        finally:
            monkeypatch.undo()
            clear_repositories()
    print(f"Saved scenario outputs to {DEFAULT_OUTPUT}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
