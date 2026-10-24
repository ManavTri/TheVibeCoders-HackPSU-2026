.PHONY: dev test seed

dev:
	cd backend && python -m uvicorn app.main:app --reload

test:
	cd backend && python -m pytest

seed:
	@echo "Open sample_docs/scenario_1_mismatch and upload both PDFs in the app."
