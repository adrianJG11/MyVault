# Development

GitHub Actions runs backend formatting, linting, migrations, and pytest on pull
requests and pushes to `main`. Each run uses a fresh PostgreSQL 17 test database
with disposable credentials; it does not load the local `.env` file.

Enable the local pre-commit hook once per checkout:

```bash
git config --local core.hooksPath .githooks
```

Before each commit, the hook checks backend formatting and lint using uv and the
locked dependencies. It checks the whole backend working tree, including
unstaged changes, and does not modify files. uv must be available in the Git
process's PATH.

If formatting fails, run `make format`, review and stage the changes, then retry
the commit. Fix reported lint errors before retrying. Database migrations and
the full test suite run in CI.

Backend tests live in `backend/tests/`. Run them from the repository root with
`make test`. The suite uses a separate PostgreSQL database named `finanzas_test`.
Create it once:

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" finanzas_test'
```

Apply the migrations to it:

```bash
cd backend
POSTGRES_DB=finanzas_test uv run --env-file ../.env alembic upgrade head
cd ..
```

Format the backend:

```bash
make format
```

Run backend linting and tests plus frontend linting, tests, and a production build:

```bash
make check
```

The frontend import-feedback tests use Node.js 24's built-in test runner and
mocked responses. Run them separately with `make frontend-test`; they require
no database or additional testing dependency.

For local frontend development, start its Vite server in another terminal while
the API and database are running:

```bash
npm --prefix frontend run dev
```

The Vite development server proxies `/api` requests to the backend. The
containerized frontend uses Nginx for the same purpose.

The tests use synthetic workbook and transaction data. Do not add real bank
exports or real financial details to tests.

