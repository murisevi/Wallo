# Wallo — Personal Finance Management Platform

Wallo is a PSD2 Open Banking personal finance web app (TFG — Universidad de Sevilla).
Users connect European bank accounts via Enable Banking, view unified balances, track spending,
and get ML-powered categorization and predictions. Solo-developer monorepo: Python backend + TypeScript frontend.

## Current Phase: MVP + ML Categorization

Core MVP (Open Banking) is complete. ML transaction categorization has been implemented on top:
1. User registration/login (JWT auth)
2. Connect bank via Enable Banking Sandbox (Mock ASPSP or BBVA sandbox)
3. Fetch and store accounts + balances + transactions
4. Dashboard showing total balance across all connected accounts
5. Transaction list with pagination, search, and category filters
6. Automatic ML categorization on sync (3-layer cascade: merchant map → ML → threshold)
7. User corrections with active learning (CategoryCorrection + MerchantMapping upsert)
8. Category management API (list, create custom, PATCH for corrections)

NOT implemented yet: budgets, goals, reports, Celery workers, Sankey charts.

## Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **Frontend**: Next.js 14+ (App Router), TypeScript strict, Tailwind CSS, React Query (TanStack)
- **Database**: PostgreSQL 16 via asyncpg
- **Cache**: Redis 7 (MVP: optional, for session caching)
- **Banking**: Enable Banking API (PSD2 Open Banking) — base URL: https://api.enablebanking.com
- **ML**: scikit-learn 1.5.2 (TF-IDF + GradientBoosting), joblib 1.4.2 (model persistence)
- **Infra**: Docker Compose (dev), single docker-compose.yml at repo root

## Commands
```bash
# Backend (from /backend)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest tests/ -v --cov=app
ruff check app/ --fix && ruff format app/
alembic revision --autogenerate -m "description"
alembic upgrade head

# ML model (from /backend)
python -m scripts.train_base_model      # Train base model from data/training_data.csv
python -m app.categories.tasks          # Retrain with base data + user corrections from DB

# Frontend (from /frontend)
npm run dev          # Dev server on :3000
npm run lint         # ESLint + Prettier check
npm run build        # Production build

# Docker (from repo root)
docker compose up -d
docker compose down -v
docker compose logs -f backend
```

## Project Structure
```
wallo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, router includes
│   │   ├── config.py            # Pydantic BaseSettings (reads .env)
│   │   ├── database.py          # Async engine, sessionmaker, Base
│   │   ├── dependencies.py      # get_db, get_current_user
│   │   ├── auth/                # Auth domain
│   │   │   ├── router.py        # POST /register, /login, /me
│   │   │   ├── schemas.py       # UserCreate, UserLogin, UserResponse, TokenResponse
│   │   │   ├── models.py        # User SQLAlchemy model
│   │   │   ├── service.py       # hash_password, verify, create_token
│   │   │   └── __init__.py
│   │   ├── banking/             # Enable Banking integration domain
│   │   │   ├── router.py        # Bank connection endpoints
│   │   │   ├── schemas.py       # ASPSP, Session, Connection schemas
│   │   │   ├── models.py        # BankConnection, BankAccount SQLAlchemy models
│   │   │   ├── service.py       # Enable Banking orchestration logic
│   │   │   ├── client.py        # Enable Banking HTTP client (httpx + JWT RS256)
│   │   │   └── __init__.py
│   │   ├── transactions/        # Transactions domain
│   │   │   ├── router.py        # GET /transactions with pagination + filters
│   │   │   ├── schemas.py       # TransactionResponse, TransactionList
│   │   │   ├── models.py        # Transaction SQLAlchemy model
│   │   │   ├── service.py       # Sync + query + auto-categorization on sync
│   │   │   └── __init__.py
│   │   ├── categories/          # ML categorization domain
│   │   │   ├── router.py        # GET/POST /categories, PATCH correction, POST retrain
│   │   │   ├── schemas.py       # CategoryResponse, CategoryCreate, CorrectionResponse
│   │   │   ├── models.py        # Category, CategoryCorrection SQLAlchemy models
│   │   │   ├── merchant_mapping.py  # MerchantMapping model (learned merchant→category)
│   │   │   ├── service.py       # 3-layer cascade: merchant_map → ML → threshold
│   │   │   ├── seed.py          # 19 default system categories (idempotent)
│   │   │   ├── text_cleaner.py  # Bank description normalizer + merchant key extractor
│   │   │   ├── ml_categorizer.py    # TF-IDF + GradientBoosting pipeline
│   │   │   ├── tasks.py         # retrain_model() sync fn (Celery wrapper commented out)
│   │   │   └── __init__.py
│   │   └── dashboard/           # Dashboard aggregation domain
│   │       ├── router.py        # GET /dashboard (aggregated view)
│   │       ├── schemas.py       # DashboardResponse
│   │       ├── service.py       # Balance aggregation logic
│   │       └── __init__.py
│   ├── alembic/
│   │   ├── env.py               # MUST import ALL models for autogenerate
│   │   └── versions/
│   ├── data/
│   │   ├── training_data.csv    # 340-row base training dataset (19 categories)
│   │   └── models/              # Trained joblib artefacts (gitignored)
│   ├── scripts/
│   │   └── train_base_model.py  # One-shot training script
│   ├── keys/                    # Enable Banking .pem private keys (gitignored!)
│   ├── tests/                   # Mirrors app/ structure
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   │   ├── layout.tsx       # Root layout with providers
│   │   │   ├── page.tsx         # Landing/redirect
│   │   │   ├── (auth)/          # Route group: login, register
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   └── (dashboard)/     # Route group: main app
│   │   │       ├── layout.tsx   # Dashboard layout with sidebar
│   │   │       ├── page.tsx     # Dashboard home (balances)
│   │   │       └── transactions/page.tsx
│   │   ├── components/
│   │   │   ├── ui/              # Primitives: Button, Input, Card, Skeleton
│   │   │   └── features/        # Domain: AccountCard, TransactionRow, CategoryBadge
│   │   ├── lib/
│   │   │   ├── api.ts           # Typed fetch wrapper (api, budgetApi, categoryApi)
│   │   │   └── auth.ts          # Token storage, auth helpers
│   │   ├── hooks/               # useAccounts, useTransactions, useCategories
│   │   ├── providers/           # QueryClientProvider, AuthProvider
│   │   └── types/               # Shared TypeScript interfaces matching backend schemas
│   │       ├── index.ts         # Transaction, User, Dashboard, etc.
│   │       └── categories.ts    # Category, TransactionWithCategory (canonical)
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── docker-compose.yml
├── .env.example
├── Makefile
└── CLAUDE.md
```

## Architecture Rules
- **Backend layers**: router.py → service.py → models.py + schemas.py. Routers handle HTTP only.
  Services contain ALL business logic. Models define DB schema. Schemas define API I/O.
- **Dependency direction**: Routers import services. Services import models. Never reverse.
- **Frontend**: Server Components by default. "use client" only for interactivity/hooks.
- **API prefix**: ALL routes under /api/v1/. All routers use tags for OpenAPI grouping.
- **Auth**: JWT Bearer tokens. Access token (30min) + Refresh token (30d). bcrypt for passwords.

## Enable Banking API — Integration Guide
Base URL: https://api.enablebanking.com
Sandbox: Mock ASPSP (control panel) + BBVA sandbox for Spain
Docs: https://enablebanking.com/docs/api/reference/
Samples: https://github.com/enablebanking/enablebanking-api-samples

### Authentication — JWT with RS256 private key
1. Register app at https://enablebanking.com/cp/applications (sandbox auto-activates)
2. Browser generates a .pem private key file — save to backend/keys/ (gitignored!)
3. For each API call, generate JWT signed with RS256:
   - Header: {"typ": "JWT", "alg": "RS256", "kid": "<application-id>"}
   - Body: {"iss": "enablebanking.com", "aud": "api.enablebanking.com", "iat": <now>, "exp": <now+3600>}
4. Send as: Authorization: Bearer <jwt>
5. Use PyJWT library: pyjwt.encode(body, private_key, algorithm="RS256", headers={"kid": app_id})

### API Flow (5 steps)
1. GET /aspsps?country=es → list Spanish banks (name + country pairs)
2. POST /auth → {aspsp: {name, country}, redirect_url, psu_type: "personal", access: {valid_until}, state} → {url, authorization_id}
3. Redirect user to url → user authenticates at bank → redirected to callback with ?code=xxx
4. POST /sessions → {code} → {session_id, accounts: [{uid, iban, name, currency, ...}]}
5. Per account: GET /accounts/{uid}/balances, GET /accounts/{uid}/transactions

### Key constraints
- Session validity: up to 180 days, set via access.valid_until in POST /auth
- Rate limits: 4 background fetches/day per account (unlimited with PSU headers)
- Balance types: ITAV (interim available, best), XPCD (expected), CLBD (closing booked)
- Amounts are strings: {amount: "45.00", currency: "EUR"} — parse with Decimal
- Transactions paginate via continuation_key — keep fetching until key is null
- Banks identified by name+country pair (not a single ID)
- Some banks return empty list + continuation_key — must keep fetching anyway
- Bank fields vary — always handle Optional types gracefully

### Backend client pattern (app/banking/client.py)
- Use httpx.AsyncClient with base_url="https://api.enablebanking.com"
- JWT: load .pem key at startup, generate token with PyJWT RS256 per request
- Store ENABLE_BANKING_APP_ID and ENABLE_BANKING_PRIVATE_KEY_PATH in config
- All Enable Banking calls go through this client — never raw httpx elsewhere

### Redirect flow (OAuth-like)
1. Frontend calls POST /api/v1/banking/connect with {bank_name, bank_country}
2. Backend calls POST /auth at Enable Banking, stores authorization_id in DB
3. Backend returns {url} to frontend
4. Frontend redirects user to url (Enable Banking terms → bank auth page)
5. User authenticates, Enable Banking redirects to callback URL with ?code=xxx
6. Frontend callback page calls POST /api/v1/banking/callback with {code}
7. Backend calls POST /sessions, gets session_id + accounts
8. Backend stores accounts, fetches balances per account

## Database Conventions
- SQLAlchemy 2.0: Mapped[] + mapped_column(), never Column()
- Monetary values: Numeric(12, 2), never Float
- All tables: id (UUID), created_at (server_default=func.now()), updated_at
- Naming convention on Base.metadata for all constraints (ix_, uq_, ck_, fk_, pk_)
- Async sessions via asyncpg, expire_on_commit=False

## Code Style
- Python: ruff (lint+format), mypy strict, pytest, line-length 88
- TypeScript: ESLint next/core-web-vitals, Prettier, strict mode
- Commits: Conventional Commits — feat(api):, fix(frontend):, docs:
- Branch: main → feature/<n>, fix/<n>

## Critical Rules
- NEVER commit .env files or .pem private key files. Both are gitignored.
- NEVER store bank credentials — Enable Banking handles all bank auth via redirect.
- Private key .pem file in backend/keys/ (gitignored). App ID in .env.
- Frontend API calls go through lib/api.ts — never raw fetch in components.
- All async I/O functions use async def. Sync def only for CPU-bound work.
- Use Annotated[type, Depends()] for all FastAPI dependencies.
- Pydantic schemas: separate Create, Update, Response per domain.

## Environment Variables (.env.example)
```
# Database
DATABASE_URL=postgresql+asyncpg://wallo:wallo@localhost:5432/wallo

# Auth
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Enable Banking
ENABLE_BANKING_APP_ID=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
ENABLE_BANKING_PRIVATE_KEY_PATH=keys/your-app-id.pem
ENABLE_BANKING_ENVIRONMENT=sandbox

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Redis (optional for MVP)
REDIS_URL=redis://localhost:6379/0
```
