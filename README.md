# MyVault

A local-first personal finance application and learning project. Import your
bank and investment activity, explore your finances, and keep your records on
your own machine.

## Features

- Create accounts and view their last known balances.
- Import Ibercaja XLSX, Revolut investment CSV, and IBKR Flex XML reports.
- Filter and categorize transactions; explore cash flow and category spending.
- Review investment holdings, allocation, FIFO cost, dividends, and results.
- Refresh supported market prices or save prices manually.
- Record dated share adjustments while preserving original trades and cost.

Built with FastAPI, PostgreSQL, React, TypeScript, and Docker Compose.

## Run locally

You need Docker with Compose. On Windows, use Docker Desktop with WSL2 and
Linux containers. Python and Node.js are only needed for development outside
Docker.

Clone the repository or [download the source](https://github.com/adrianJG11/MyVault/archive/refs/heads/main.zip).
From the project directory, create your local configuration on first setup:

```bash
cp -n .env.example .env
```

Set `POSTGRES_PASSWORD` to a private password in `.env`. Keep your existing
configuration when updating.

Build the application, start PostgreSQL, apply migrations, and start the app:

```bash
docker compose build
docker compose up -d --wait db
docker compose run --rm --no-deps api /app/.venv/bin/alembic upgrade head
docker compose up -d
```

Open **[MyVault](http://127.0.0.1:5173)**. The [API documentation](http://127.0.0.1:8000/docs)
is available locally too.

For daily use:

```bash
docker compose up -d
```

After updating the source, repeat the build and migration steps above. To stop
without deleting your records:

```bash
docker compose stop
```

## Imports and investments

Select an account, then use **Import transactions** or **Import investment
activity**. See the [import guide](docs/imports.md) for supported formats,
IBKR report fields, optional Flex downloads, and share adjustments.

Market values use saved-price snapshots. Supported Yahoo quotes may be delayed;
manual prices and imported IBKR closing prices remain available. EUR and USD
are shown separately. IBKR duplicate detection requires consistent broker
account and trade IDs across reports.

## Development

See the [development guide](docs/development.md) for tooling, the separate test
database, quality checks, and pre-commit setup.

## Data and privacy

- Services bind to `127.0.0.1`; financial records persist in a local Docker volume.
- On-demand quotes send public ticker symbols to Yahoo Finance.
- Keep `.env`, bank exports, and database backups private. Banking passwords
  are never needed.
- Avoid `docker compose down -v`: it deletes the database volume.

Investment results are for personal analysis, not tax filing. Automatic bank
connections and automatic corporate-action imports are outside the current scope.
