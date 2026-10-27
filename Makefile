.PHONY: ci auth-ci game-ci client-ci

ci: auth-ci game-ci client-ci

auth-ci:
	cd services/auth && python -m ruff check .
	cd services/auth && python -m ruff format --check .
	cd services/auth && python -m mypy app tests
	cd services/auth && python -m pytest

game-ci:
	cd services/game && python -m ruff check .
	cd services/game && python -m ruff format --check .
	cd services/game && python -m mypy app tests
	cd services/game && python -m pytest

client-ci:
	cd client && npm run lint
	cd client && npm run format:check
	cd client && npm run typecheck
	cd client && npm test
	cd client && npm run build


.PHONY: db-reset
db-reset:
	python scripts/db_reset.py
