# Finance App — Agent Guidelines

## Product context

This repository is both a real personal product and a learning project. Build a useful local-first, privacy-first personal finance application for daily use, not merely a portfolio demonstration.

The product should centralize personal finances and help the developer understand:

- how much money is available and where it is distributed;
- income, spending, categories, savings, and savings rate;
- net-worth evolution and investment performance;
- budget and financial-goal progress;
- how hypothetical decisions could affect personal finances.

The product vision provides direction and prevents clearly limiting decisions. It does not authorize implementing future features or infrastructure ahead of need.

## Current scope — V0.1

Build only:

1. a FastAPI backend;
2. basic financial accounts;
3. a normalized transaction model;
4. import of one real bank CSV format;
5. persistence in PostgreSQL;
6. transaction queries through an API.

V0.1 does not need Redis, Celery, ML, an LLM, automatic bank connections, stock quotes, cloud services, microservices, Kubernetes, Terraform, or Helm.

## Learning mode

The developer must write, understand, and be able to explain the code and technical decisions.

Unless explicitly asked to implement something:

1. Inspect the current code first.
2. Explain the problem or concept, including any missing fundamental concept.
3. Propose the next small, verifiable step.
4. Give hints rather than a complete implementation.
5. Let the developer implement it when reasonable.
6. Review the implementation afterward.
7. Explain mistakes, trade-offs, and alternatives.

Do not modify files unless explicitly requested. Do not dump a complete feature implementation when a smaller hint is sufficient. When something fails, explain its cause before proposing a fix.

## Development philosophy

Prefer the simplest explicit, readable solution that meets the current requirement. Apply YAGNI and do not over-engineer.

- Inspect and reuse existing code and framework functionality before creating new code.
- Do not duplicate existing functionality.
- Do not design for hypothetical future requirements or create empty modules and layers for later.
- Do not introduce repositories, factories, interfaces, managers, generic helpers, additional services, or infrastructure components until they solve a concrete current problem.
- Do not add dependencies without explaining why existing language, framework, or project capabilities are insufficient.
- Do not refactor unrelated code while implementing or reviewing a feature.
- Keep functions small when that improves readability, but do not fragment them artificially.
- Avoid comments that only restate evident code.
- Before considering a change complete, remove any newly introduced code or configuration that is unnecessary without losing required functionality.

When proposing more complex architecture or tooling, identify the concrete current problem it solves.

## Architecture

Start as a modular monolith. Do not create microservices.

Prefer feature-oriented organization as the application grows. A possible direction is:

```text
app/
├── main.py
├── core/
├── transactions/
├── accounts/
├── imports/
└── investments/
```

A feature may eventually contain `router.py`, `schemas.py`, `models.py`, `service.py`, or `repository.py`, but create each file or layer only when current code justifies it. Do not create the full architecture in advance or design around a hypothetical migration to cloud infrastructure or Kubernetes.

## Product roadmap — not current scope

Treat the following as future capabilities to introduce incrementally, not as current implementation requirements.

### Accounts and transactions

- Support multiple banks and accounts with a unified view of available money.
- Import, store, and query transactions.
- Filter by date, account, bank, category, description, and amount.

### Bank importers

Transform differing bank CSV/XLSX formats into the normalized internal model and avoid duplicate transactions where reasonably possible. Start with the first real bank format; do not create a generic importer or plugin architecture until multiple real cases demonstrate the need.

### Categories and dashboard

- Categorize transactions initially through manual classification or simple rules, such as housing, food, transport, leisure, utilities, subscriptions, income, and investments.
- Show income, expenses, savings, savings rate, category spending, monthly comparisons, and financial evolution.
- Explore ML classification only after sufficient data exists and it provides concrete value.

### Budgets, goals, and net worth

- Compare monthly category budgets with actual spending.
- Track goals such as an emergency fund, travel, a home deposit, or investment targets, including progress and contribution-based estimates.
- Calculate net worth from accounts, investments, relevant assets, and debts, preserving history for trend views.

### Investments

In a later phase, support stocks, ETFs/funds, contributions, average price, returns, dividends, and portfolio allocation. External market quotes are not part of V0.1.

### Financial simulator

Allow deterministic hypothetical scenarios such as comparing locations or salaries, changing expenses or monthly savings, simulating periodic investments, estimating when a target net worth could be reached, and studying major purchases. Present results as scenarios, never guaranteed predictions.

### Machine learning and local AI

Introduce ML only for a concrete problem; the first candidate is transaction classification. Do not add ML merely to advertise its use.

A later local LLM experiment may answer questions about spending, savings, averages, and recurring costs. The application must perform important financial queries and calculations deterministically and provide structured results to the model. Do not grant the LLM arbitrary PostgreSQL access. Prefer local models to preserve privacy.

## Technical direction

The planned stack is Python, uv, FastAPI, Pydantic, PostgreSQL, SQLAlchemy, Alembic, pytest, Ruff, React, TypeScript, Docker, and Docker Compose. A technology's presence in this list does not justify introducing it before the current phase needs it.

Redis, Celery, observability, CI/CD, ML, and a local LLM may be introduced only when a concrete learning objective or operational requirement exists.

### Backend

- Use modern, readable Python and type hints.
- Use uv for dependency management and execution; maintain `pyproject.toml` and `uv.lock` rather than adding `requirements.txt` without an explicit compatibility need.
- Use Pydantic for API input and output validation.
- Use FastAPI `APIRouter` as endpoints grow.
- Use correct HTTP status codes, explicit response models when appropriate, and coherent exception handling.
- Keep significant business logic outside HTTP handlers, but do not introduce a service layer for trivial logic.
- Use FastAPI dependency injection only when it provides a concrete benefit.
- Use `async` only for genuinely asynchronous work or another clear technical reason; do not block the event loop with expensive synchronous operations.
- Avoid mutable global state and keep code testable.
- Do not introduce Celery or Redis until background or asynchronous processing is actually needed.

### Frontend

The frontend will use React and TypeScript when it enters scope. Keep its architecture simple, prefer explicit API contracts and TypeScript types, and do not introduce large state-management libraries until demonstrated complexity requires them.

### Database

PostgreSQL is the primary database. Introduce SQLAlchemy with persistence and Alembic with migrations.

- Prefer correct, simple schemas and use database constraints where appropriate.
- Use parameterized queries or the ORM correctly.
- Do not add indexes without a concrete query or measured use case.
- Avoid unnecessary denormalization.
- Do not hide inefficient database access behind abstractions.

## Local-first and privacy-first security

Financial data must remain local by default, and the application must work without cloud services.

- Minimize stored personal and financial data.
- Never store banking passwords or credentials.
- Do not store complete IBANs or account identifiers when partial identifiers are sufficient.
- Never commit secrets, bake them into images, or expose them in logs.
- Do not log passwords, tokens, credentials, complete account numbers, or unnecessary financial data.
- Do not add unnecessary telemetry.
- Do not send financial information to external services without an explicit decision and security review.
- Treat CSV, XLSX, and all imported or uploaded data as untrusted input; validate it and prevent path traversal or unexpected file uploads.
- Do not expose stack traces, internal details, or sensitive data to clients.
- Apply least privilege to users and services.
- Do not implement custom cryptography. Use established libraries only for a defined threat and explain what that protection mitigates.
- Review dependencies and keep them reasonably current.
- Explicitly identify any change that increases the attack surface.

Bank transactions will initially enter the application through CSV/XLSX files manually exported from each bank. There must be no automatic bank connection in V0.1.

Bind local applications to `127.0.0.1` when external access is unnecessary. Keep PostgreSQL, Redis, and similar internal services on private Docker networks and do not publish them to the host without a concrete need.

Any future external access requires an explicit security review. Warn about the implications before recommending Internet exposure and consider private alternatives such as a VPN.

## Docker and DevOps

The development environment is Windows 11, WSL2, the Linux filesystem, Docker, and Docker Compose. Docker and Docker Compose are the infrastructure target for this project and a deliberate learning area.

- Keep Dockerfiles simple and builds reproducible, using multi-stage builds only when they provide value.
- Keep images reasonably small, use `.dockerignore`, and run as a non-root user where practical.
- Never copy secrets into images; use appropriate runtime configuration and secret handling.
- Use explicit volumes for persistence, private networks for internal communication, and healthchecks when operationally useful.
- Avoid publishing internal services and bind local application ports to `127.0.0.1` when sufficient.
- Avoid complex shell scripts when Docker or Compose already solves the problem.
- Understand and document relevant configuration, persistence, logs, container communication, and network behavior.
- Introduce CI/CD gradually; include format/lint, tests, image builds, and security scanning when appropriate.

Do not use Kubernetes, Helm, or Terraform in this project, and do not design for a future Kubernetes migration. Studying Kubernetes or cloud infrastructure must be a separate exercise or an explicit future decision, not a current architectural requirement.

For a possible future deployment, prefer Docker Compose on a Linux server, VPS, or mini-PC with a reverse proxy before introducing an orchestrator.

## Testing and quality

Use pytest and test observable behavior rather than unnecessary implementation details.

- Prefer small, clear tests whose names describe the behavior under test.
- Use unit tests for isolated logic and integration tests when interactions among FastAPI, PostgreSQL, or other components matter.
- Cover the happy path and relevant errors.
- Add regression tests for meaningful bugs.
- Avoid excessive mocking and implementation-coupled tests.
- Use fixtures only when they reduce real duplication; do not build a large fixture system prematurely.
- Do not create placeholder tests or pursue 100% coverage solely for the metric.
- If a test fails, investigate the cause instead of changing the test merely to make it pass.

Before considering code complete, run the relevant commands already supported by the current project:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

## Agent behavior when reviewing code

Separate findings into:

1. actual bugs or correctness issues;
2. security or reliability concerns;
3. maintainability improvements;
4. optional style suggestions.

Prioritize the first two. Distinguish errors from possible improvements and personal preferences; do not present preferences as mandatory rules.

Do not overwhelm the developer with cosmetic changes while important issues exist. Explain why each suggested change matters. If the implementation is already sufficiently good, say so instead of inventing improvements.
