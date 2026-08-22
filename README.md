# Finanzas

This is a personal, local-first finance application that I am building to use in
my daily life and to learn backend development properly.

The application keeps financial data on my machine by default. The current goal
is deliberately small: import real bank transactions, normalize them, store them
in PostgreSQL, and inspect them through a small local web application.

## Current version: V0.1

What works now:

- create and list financial accounts;
- import an Ibercaja XLSX export into an account;
- normalize and store transactions in PostgreSQL;
- skip transactions that were already imported into the same account;
- list transactions and filter them by account, date, description, or amount;
- select an account, import an Ibercaja XLSX file, and read its transactions in
  a React and TypeScript interface;
- import duplicate-safe Revolut investment activity from CSV and inspect it in
  a separate Investments tab;
- calculate FIFO positions, realized results, dividends, and unrealized results
  from on-demand USD market prices or manually entered fallback prices;
- run the frontend, API, and database with Docker Compose;
- validate the backend with automated tests and both applications with lint and
  build checks.

## Requirements

- Docker with Docker Compose;
- WSL2 when running the project from Windows;
- `uv` and Node.js when running development commands outside Docker.

Keep the repository in the WSL Linux filesystem, not under `/mnt/c`, to avoid
unnecessary filesystem and Docker performance problems.

## Configuration

Create a `.env` file in the repository root:

```dotenv
POSTGRES_DB=finanzas
POSTGRES_USER=finanzas
POSTGRES_PASSWORD=replace-with-a-private-password
TWELVE_DATA_API_KEY=replace-with-your-private-api-key
```

The `.env` file is ignored by Git. Never commit it or put its values in the
Dockerfile. Copy `.env.example` when setting up a new local installation, but
keep the real values only in `.env`.

## First setup

Start PostgreSQL:

```bash
docker compose up -d db
```

Apply the database migrations from the API image:

```bash
docker compose run --rm api /app/.venv/bin/alembic upgrade head
```

Build and start the complete application:

```bash
docker compose up -d --build
```

Check the containers:

```bash
docker compose ps
```

The application is available only from the local machine:

- web interface: <http://127.0.0.1:5173>
- health check: <http://127.0.0.1:8000/health>
- interactive API documentation: <http://127.0.0.1:8000/docs>

## Daily use

Start the application:

```bash
docker compose up -d
```

Use `docker compose up -d --build` instead after changing application source,
dependencies, or a Dockerfile.

Open <http://127.0.0.1:5173>, select an account, and upload an Ibercaja `.xlsx`
export. The transaction list refreshes after the import. Importing the same
workbook again should report `0` new transactions because duplicate detection
is performed per account.

The Investments tab accepts Revolut's investment activity CSV export. Select a
dedicated Revolut account before importing it. The first version preserves
trades, dividends, cash movements, currencies, and FX rates as reported.

After importing, use **Refresh market prices** to retrieve supported USD prices
from Twelve Data. Only ticker symbols are sent to the provider; account names,
quantities, trades, balances, and calculated results remain local. Unsupported,
unavailable, and non-USD positions keep their manual price input as a fallback.

The application calculates remaining FIFO cost, market value, unrealized
profit/loss, realized profit/loss, dividends, and total result. EUR and USD
remain separate because the meaning of Revolut's exported FX rate has not yet
been verified. These figures are for personal analysis, not tax filing.

Account creation is not in the web interface yet. To create the first account,
open <http://127.0.0.1:8000/docs> and use `POST /accounts` with a body such as:

```json
{
  "name": "savings",
  "bank_name": "Ibercaja",
  "currency": "EUR"
}
```

The API remains available for inspection and supports these optional filters on
`GET /transactions`:

- `account_id`;
- `date_from` and `date_to`;
- `description`;
- `amount_min` and `amount_max`.

## Database migrations

Run migrations whenever the image contains new Alembic migrations:

```bash
docker compose run --rm api /app/.venv/bin/alembic upgrade head
```

Migrations are explicit on purpose. Starting the API does not silently change
the database schema.

## Development checks

The test suite uses a separate PostgreSQL database named `finanzas_test`.
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

Run backend linting and tests plus frontend linting and a production build:

```bash
make check
```

For local frontend development, start its Vite server in another terminal while
the API and database are running:

```bash
npm --prefix frontend run dev
```

The Vite development server proxies `/api` requests to the backend. The
containerized frontend uses Nginx for the same purpose.

The tests use synthetic workbook and transaction data. Do not add real bank
exports or real financial details to tests.

## Data and privacy

- The frontend, API, and PostgreSQL ports are bound to `127.0.0.1`, not exposed
  publicly.
- PostgreSQL data persists in the `postgres_data` Docker volume.
- The frontend proxy rejects uploads larger than 10 MB.
- Bank credentials are not needed and must not be stored.
- Real CSV/XLSX exports and financial data must not be committed.
- Do not paste real balances, account identifiers, or complete transaction
  histories into issues, commits, logs, or chats. Use redacted or synthetic data.

Stop the containers without deleting the database volume:

```bash
docker compose down
```

Do not run `docker compose down -v` unless you intentionally want to delete the
stored PostgreSQL data.

## Scope

V0.1 is a usable local foundation, not the final product. The Revolut activity
import and manual-price performance view are the first small investment slice;
on-demand USD quotes are supported, while scheduled quotes, tax reporting,
categories, dashboards, budgets, and additional banks should still be
introduced one real use case at a time. Redis, Celery, ML, LLMs, cloud
infrastructure, microservices, and Kubernetes are not needed for the current
version.
