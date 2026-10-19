.PHONY: test backend-test frontend-build run-miroind

backend-test:
	uv run --project backend python -m pytest backend/tests tests

frontend-build:
	npm run build

test: backend-test frontend-build

run-miroind:
	MIROIND_OFFLINE_ONLY=true npm run dev
