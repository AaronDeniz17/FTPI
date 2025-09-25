# Full-Stack Finance Dashboard

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r fullstack-dashboard/requirements.txt
```

## Run Backend (FastAPI)

```bash
uvicorn backend.app.main:app --app-dir fullstack-dashboard --reload --host 0.0.0.0 --port 8000
```

This creates `finance.db` (SQLite) in the project root on first run.

## Run Frontend (Dash)

In a second shell with the same venv:

```bash
python fullstack-dashboard/frontend/dash_app.py
```

The Dash app will call the API at `http://127.0.0.1:8000` by default. To change it:

```bash
BACKEND_URL=http://localhost:8000 python fullstack-dashboard/frontend/dash_app.py
```

## Seeding Data

Use the API to create a user and transactions. Example with `curl`:

```bash
curl -X POST http://127.0.0.1:8000/api/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alice","email":"alice@example.com"}'

# Add income and expense
curl -X POST http://127.0.0.1:8000/api/transactions \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"date":"2025-01-05","type":"income","category":"salary","amount":5000}'

curl -X POST http://127.0.0.1:8000/api/transactions \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"date":"2025-01-10","type":"expense","category":"rent","amount":2000}'

# Add trade (buy 10 AAPL at $150)
curl -X POST http://127.0.0.1:8000/api/transactions \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"date":"2025-01-15","type":"trade","category":"buy","amount":1500,"asset_symbol":"AAPL","shares":10,"price_at_trade":150}'
```

Open `http://127.0.0.1:8050` for the dashboard.
