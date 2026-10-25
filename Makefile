.PHONY: backend test_no_auth test_auth seed frontend

backend:
	cd backend && python -m uvicorn app.main:app --reload

test_no_auth:
	cd backend && python -m pytest

test:
	cd backend && pytest -q tests/test_auth_asymmetric.py && pytest -q

seed:
	@echo "Open sample_docs/scenario_1_mismatch and upload both PDFs in the app."

frontend:
	cd frontend && npm ci && npm run dev