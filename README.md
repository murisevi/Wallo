# Wallo — Personal Finance Management Platform

Wallo is a PSD2 Open Banking personal finance web application built as a TFG (Trabajo de Fin de Grado) at the Universidad de Sevilla. Users connect their European bank accounts via Enable Banking, view unified balances across all accounts, track spending with paginated transaction lists, and benefit from a clean, mobile-friendly dashboard — all without sharing bank credentials with the application.

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌────────────────────┐
│             │ HTTP │                  │ HTTP │                    │
│  Next.js    │─────▸│  FastAPI         │─────▸│  Enable Banking    │
│  Frontend   │◂─────│  Backend         │◂─────│  PSD2 API          │
│  :3000      │      │  :8000           │      │  (sandbox / prod)  │
└─────────────┘      └───────┬──────────┘      └────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
               ┌────▾────┐     ┌─────▾────┐
               │ Postgres │     │  Redis   │
               │  :5432   │     │  :6379   │
               └──────────┘     └──────────┘
```

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript strict, Tailwind CSS, React Query |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Database | PostgreSQL 16 via asyncpg |
| Cache | Redis 7 (optional for MVP) |
| Banking | Enable Banking API — PSD2 Open Banking |
| Infra | Docker Compose |

## Quick Start

### Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [Node.js 18+](https://nodejs.org/) (for local frontend dev)
- [Python 3.12+](https://www.python.org/) (for local backend dev)

### 1. Clone and configure

```bash
git clone <repo-url> wallo && cd wallo
cp .env.example .env
```

Edit `.env` and set at minimum:
- `JWT_SECRET_KEY` — a strong random string
- `ENABLE_BANKING_APP_ID` — from the Enable Banking control panel
- `ENABLE_BANKING_PRIVATE_KEY_PATH` — relative path to your `.pem` key

### 2. Register an Enable Banking application

1. Go to [https://enablebanking.com/cp/applications](https://enablebanking.com/cp/applications)
2. Create a **Sandbox** application (auto-activates, no contract needed)
3. Copy the **Application ID** into `ENABLE_BANKING_APP_ID` in `.env`
4. Download the generated `.pem` private key and save it to `Backend/keys/private.pem`
5. In the application settings, add the redirect URL: `http://localhost:3000/banking/callback`

> See the [Enable Banking sandbox docs](https://enablebanking.com/docs/api/sandbox/) for test bank credentials (Mock ASPSP or BBVA sandbox).

### 3. Start all services

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, the FastAPI backend (`:8000`), and the Next.js frontend (`:3000`).

### 4. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 5. Use the app

Open [http://localhost:3000](http://localhost:3000) in your browser:

1. **Register** a new account
2. **Login** with your credentials
3. Click **Añadir banco** to connect a sandbox bank
4. Complete the bank authentication (use Mock ASPSP for instant testing)
5. View your **dashboard** with balances and transactions

### Local development (without Docker)

```bash
# Backend
cd Backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## API Documentation

FastAPI auto-generates interactive API docs:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Testing

```bash
# Backend unit tests
cd Backend
pytest tests/ -v --cov=app

# Python linting
ruff check app/ --fix && ruff format app/

# Frontend linting
cd frontend
npm run lint
```

## Screenshots

> *Screenshots will be added after the first demo deployment.*

## License

This project is part of a university thesis (TFG) and is not currently licensed for external use.
