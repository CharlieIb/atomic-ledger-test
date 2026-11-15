# LedgerLock

A concurrent-safe double-entry transfer API built with FastAPI, PostgreSQL,
SQLAlchemy, Pydantic, and pytest. Transfers are atomic, idempotent, and recorded
as immutable debit/credit ledger entries.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d db
alembic upgrade head
uvicorn ledgerlock.main:app --reload
```

Set `DATABASE_URL` in the environment (or export the value from `.env`) before
starting the API. Create accounts by inserting rows into the `accounts` table;
the transfer endpoint does not expose account administration.

## API

`POST /transfers` accepts `Idempotency-Key` and a JSON body such as:

```json
{
  "source_account_id": 1,
  "destination_account_id": 2,
  "amount": "12.50"
}
```

The request moves funds between existing accounts and records matching signed
ledger entries. Reusing the same key and payload returns the original transfer;
reusing a key with a different payload returns `409 Conflict`.

Run tests with `pytest`.
