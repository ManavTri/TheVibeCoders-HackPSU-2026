from typing import Protocol

from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding


class Rule(Protocol):
    id: str

    def check(self, docs: list[FinancialDocument]) -> list[Finding]: ...
