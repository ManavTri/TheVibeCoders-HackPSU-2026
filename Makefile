.PHONY: backend test seed frontend

backend:
	cd backend && python -m uvicorn app.main:app --reload

test:
	cd backend && python -m pytest

seed:
	@echo "Open sample_docs/scenario_1_mismatch and upload both PDFs in the app."

frontend:
	cd frontend && npm ci && npm run dev