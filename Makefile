.PHONY: format lint test frontend-lint frontend-build check

format:
	uv --directory backend run ruff format .

lint:
	uv --directory backend run ruff check .

test:
	POSTGRES_DB=finanzas_test uv --directory backend run --env-file ../.env pytest

frontend-lint:
	npm --prefix frontend run lint

frontend-build:
	npm --prefix frontend run build

check: lint test frontend-lint frontend-build
