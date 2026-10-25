import json
from pathlib import Path

from app.core.config import get_settings
from app.services.extraction.extractor import GeminiExtractor
from app.services.validation.engine import validate_documents

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = BACKEND_ROOT.parent / "sample_docs"


def main() -> int:
    settings = get_settings()
    if not settings.llm_enabled or not settings.llm_model:
        print("SKIP: configure LLM_API_KEY and LLM_MODEL to run extraction evaluation.")
        return 0

    extractor = GeminiExtractor(settings)
    passed = True
    for expected_path in sorted(SAMPLE_ROOT.glob("scenario_*/expected.json")):
        scenario = expected_path.parent
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        documents = [
            extractor.extract(
                document_id=f"{scenario.name}-{pdf_path.stem}",
                filename=pdf_path.name,
                pdf_bytes=pdf_path.read_bytes(),
            ).document
            for pdf_path in sorted(scenario.glob("*.pdf"))
        ]
        actual_rules = {finding.rule_id for finding in validate_documents(documents)}
        expected_rules = set(expected["expected_rule_ids"])
        scenario_passed = expected_rules == actual_rules
        passed &= scenario_passed
        print(
            f"{scenario.name}: {'PASS' if scenario_passed else 'FAIL'} "
            f"(expected={sorted(expected_rules)}, actual={sorted(actual_rules)})"
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
