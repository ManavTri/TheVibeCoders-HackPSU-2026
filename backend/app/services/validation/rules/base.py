from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from app.schemas.documents import FinancialDocument
from app.services.validation.ledger import Ledger
from app.services.validation.normalize import AcademicCalendar


class RuleAssist(Protocol):
    def suggest_award_matches(
        self, unmatched_a: list[dict[str, Any]], unmatched_b: list[dict[str, Any]]
    ) -> list[tuple[int, int]]: ...

    def classify_line_item(self, label: str) -> str | None: ...


class NullAssist:
    def suggest_award_matches(
        self, unmatched_a: list[dict[str, Any]], unmatched_b: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        return []

    def classify_line_item(self, label: str) -> str | None:
        return None


@dataclass(frozen=True)
class ValidationConfig:
    money_tolerance: Decimal = Decimal("0.01")
    near_deadline_warning_days: int = 7
    near_deadline_info_days: int = 14
    fuzzy_match_threshold: float = 0.85
    calendar: AcademicCalendar = field(default_factory=AcademicCalendar)
    llm_enabled: bool = False
    rule_assist_enabled: bool = False
    assist: RuleAssist = field(default_factory=NullAssist)


@dataclass(frozen=True)
class RuleContext:
    ledger: Ledger
    documents: list[FinancialDocument]
    today: date
    config: ValidationConfig
