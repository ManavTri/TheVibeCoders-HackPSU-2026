from collections.abc import Callable

from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding

Rule = Callable[[list[FinancialDocument]], list[Finding]]
