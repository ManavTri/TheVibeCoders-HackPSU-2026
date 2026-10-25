.PHONY: backend test_no_auth test_auth seed frontend frontend-install frontend-runtime

backend:
	cd backend && python -m uvicorn app.main:app --reload

test_no_auth:
	cd backend && python -m pytest

test:
	cd backend && pytest -q tests/test_auth_asymmetric.py && pytest -q

seed:
	@echo "Open sample_docs/scenario_1_mismatch and upload both PDFs in the app."

frontend-runtime:
	@project_root="$$(pwd -P)"; \
	case "$$project_root" in \
		/mnt/[A-Za-z]/*) \
			echo "Frontend dependencies must live in the Ubuntu filesystem, not on a Windows-mounted drive." >&2; \
			echo "Use a checkout under your Linux home directory (for example, ~/Code/TheVibeCoders-HackPSU-2026)." >&2; \
			exit 1 ;; \
	esac
	@node_path="$$(command -v node 2>/dev/null || true)"; \
	npm_path="$$(command -v npm 2>/dev/null || true)"; \
	if [ -z "$$node_path" ] || [ -z "$$npm_path" ]; then \
		echo "Install Node.js 22+ and npm inside Ubuntu/WSL; refusing Windows Node/npm." >&2; \
		echo "Detected node: $${node_path:-not found}; npm: $${npm_path:-not found}" >&2; \
		exit 1; \
	fi; \
	for runtime_path in "$$node_path" "$$npm_path"; do \
		case "$$runtime_path" in \
			/mnt/[A-Za-z]/*|*.exe|*.cmd|*.CMD) \
				echo "Refusing Windows Node/npm from WSL PATH: $$runtime_path" >&2; \
				echo "Install Node.js inside Ubuntu and ensure its bin directory is first in PATH." >&2; \
				exit 1 ;; \
		esac; \
	done; \
	node_major="$$(node -p 'process.versions.node.split(".")[0]')"; \
	if [ "$$node_major" -lt 22 ]; then \
		echo "Node.js 22+ required; found $$(node --version) at $$node_path." >&2; \
		exit 1; \
	fi

frontend-install: frontend-runtime
	cd frontend && npm ci

frontend: frontend-runtime
	@if [ ! -f frontend/node_modules/vite/bin/vite.js ]; then \
		echo "Frontend dependencies are missing. Run 'make frontend-install' first."; \
		exit 1; \
	fi
	cd frontend && npm run dev