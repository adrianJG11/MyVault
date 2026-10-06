.PHONY: format lint test frontend-lint frontend-test frontend-build ibkr-download check

format:
	uv --directory backend run ruff format .

lint:
	uv --directory backend run ruff check .

test:
	POSTGRES_DB=finanzas_test uv --directory backend run --env-file ../.env pytest

frontend-lint:
	npm --prefix frontend run lint

frontend-test:
	npm --prefix frontend test

frontend-build:
	npm --prefix frontend run build

ibkr-download:
	uv --directory backend run --env-file ../.env python -m investments.ibkr_importer

check: lint test frontend-lint frontend-test frontend-build
