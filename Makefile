.PHONY: ci auth-ci game-ci client-ci

ci: auth-ci game-ci client-ci scripts-ci content-lint

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

.PHONY: scripts-ci
scripts-ci:
	python -m ruff check --config services/game/pyproject.toml scripts
	python -m ruff format --check --config services/game/pyproject.toml scripts
	python -m mypy --config-file services/game/pyproject.toml scripts

.PHONY: content-lint
content-lint:
	cd services/game && python -m app.content.lint

.PHONY: world-create
world-create:
	cd services/game && python -m app.services.world

.PHONY: seed-check
seed-check:
	cd services/game && python -m app.services.seed_check
