# Finanzas

This is a personal, local-first finance application that I am building to use in
my daily life and to learn backend development properly.

The application keeps financial data on my machine by default. The current goal
is deliberately small: import real bank transactions, normalize them, store them
in PostgreSQL, and inspect them through a small local web application.

## Current version: V0.2

What works now:

- create and list financial accounts;
- import an Ibercaja XLSX export into an account;
- normalize and store transactions in PostgreSQL;
- skip transactions that were already imported into the same account;
- list transactions and filter them by account, date, description, amount, or
  category, including uncategorized transactions;
- assign categories manually and suggest categories from a small set of
  explicit merchant rules during import;
- select an account, import an Ibercaja XLSX file, and read its transactions in
  a React and TypeScript interface;
- inspect money in, money out, monthly cash flow, and spending by category;
- search, filter, categorize, and paginate transactions in the web interface;
- import duplicate-safe Revolut investment activity from CSV and inspect it in
  a separate Investments tab;
- import IBKR stock and ETF executions from XML through the API, with duplicate
  detection, and download reports using the optional Flex Web Service script;
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
EODHD_API_KEY=replace-with-your-private-api-key
```

The `.env` file is ignored by Git. Never commit it or put its values in the
Dockerfile. Copy `.env.example` when setting up a new local installation, but
keep the real values only in `.env`.

Compose does not load `.env.example` automatically. Missing or empty PostgreSQL
settings stop startup with an error pointing to `.env`.

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

Imported bank transactions receive a category only when an explicit rule
matches confidently. Categories can be corrected manually from the transaction
table. Existing records were backfilled once with the same rules without
overwriting categories that had already been assigned manually.

After importing, use **Refresh market prices** to retrieve end-of-day prices
from EODHD. Only ticker symbols are sent to the provider; account names,
quantities, trades, balances, and calculated results remain local. USD tickers
and verified international listings are refreshed automatically. Unsupported
or unavailable listings keep their manual price input as a fallback.

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
- `amount_min` and `amount_max`;
- `category`, using `uncategorized` to select transactions without a category.

## IBKR investment imports

Create a dedicated IBKR account with `POST /accounts`. Configure an Activity
Flex Query in XML format with Trades at the Executions level and these fields:
`accountId`, `assetCategory`, `buySell`, `conid`, `currency`, `dateTime`,
`fxRateToBase`, `ibCommission`, `ibCommissionCurrency`, `netCash`, `quantity`,
`symbol`, `tradeID`, and `tradePrice`.

Upload a manually exported report through
`POST /accounts/{account_id}/imports/ibkr-investments` in
<http://127.0.0.1:8000/docs>. For example, from the repository root, replacing
`ACCOUNT_ID` with your local IBKR account's ID:

```bash
curl --fail-with-body \
  -F 'file=@ibkr_report.xml;type=application/xml' \
  http://127.0.0.1:8000/accounts/ACCOUNT_ID/imports/ibkr-investments
```

The response reports the number of new activities. Re-importing the same trades
into the same local account returns `{"imported": 0}`. Inspect imported records
with `GET /investment-activities?account_id=ACCOUNT_ID` and FIFO results with
`GET /investment-summary?account_id=ACCOUNT_ID`.

Imports accept stock and ETF executions marked `STK`, one broker account per
report, and XML up to 10 MB. Trades are identified by broker account and trade
ID. Quantities are normalized to positive values; net cash already includes
fees. Execution times are interpreted as Eastern time and stored in UTC. FX
rates are retained, but summaries stay separate by trade currency. Import the
purchase history needed to calculate subsequent sales; short positions,
derivatives, dividends, corporate actions, and cash movements are not supported
by this IBKR importer.

To download XML using the Flex Web Service, set `IBKR_FLEX_TOKEN` and
`IBKR_FLEX_QUERY_ID` in your private root `.env`, then run from the repository
root:

```bash
uv --directory backend run --env-file ../.env python -m investments.ibkr_importer
```

The downloader waits for generation, retries transient errors a limited number
of times, and validates the report before replacing `backend/ibkr_report.xml`.
The saved file has permissions `0600`. A failed download preserves the previous
file. To import this downloaded report with curl, use
`file=@backend/ibkr_report.xml;type=application/xml`. The frontend's upload
control currently accepts Revolut CSV; IBKR imports use the API.

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

## Version guide

The roadmap is provisional. Each version should solve a real daily-use problem;
it is not permission to build future architecture in advance.

### V0.1 — Local foundation

- FastAPI and PostgreSQL persistence;
- accounts and normalized transactions;
- Ibercaja XLSX import with duplicate detection;
- a small React interface;
- Docker Compose development and local deployment;
- the first Revolut investment import and performance view.

### V0.2 — Transactions and categories

- manual categories and conservative automatic categorization rules;
- category and uncategorized filters;
- description search, date filters, and transaction pagination;
- monthly cash-flow and category-spending summaries;
- a one-time category backfill that preserves manual choices.

### V0.3 — Daily-use overview (provisional)

- make account creation and management available in the web interface;
- improve account balances and the unified money overview;
- make import results and history clearer;
- refine monthly income, spending, and savings summaries from real usage.

### V0.4 — Investment expansion (provisional)

- expand IBKR imports beyond stock and ETF executions when real reports require it;
- combine investment positions across Revolut and IBKR accounts;
- show portfolio allocation;
- verify FX semantics before combining EUR and USD results.

Budgets, goals, net worth, simulations, ML, and a local AI assistant remain
later possibilities. Scheduled quotes, tax reporting, and support for another
bank should be added only for a concrete need. Redis, Celery, cloud
infrastructure, microservices, and Kubernetes are not required.
