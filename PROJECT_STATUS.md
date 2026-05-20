# Wallo - Project Status

> **Purpose:** authoritative snapshot of the current workspace state. This file
> reflects what is present in the codebase, including modified and untracked
> files, not only what is committed. Updated: 2026-05-19.

---

## 1. Executive Summary

Wallo is a personal finance management platform for a TFG at Universidad de
Sevilla. It is a monorepo with a FastAPI backend and a Next.js frontend. Users
connect bank accounts through Enable Banking, sync balances and transactions,
categorize spending with deterministic and ML-assisted logic, manage budgets,
review reports, detect recurring charges, and reserve money virtually for
savings goals.

### Current Implementation Status

| Feature Area | Status | Notes |
|---|---|---|
| User registration and JWT auth | Implemented | Register, login, current user and profile update endpoints exist. |
| Enable Banking PSD2 flow | Implemented | Institutions, connect, callback, accounts, sync and soft-disconnect endpoints exist. |
| Transaction sync and storage | Implemented | Sync stores transactions and balances, then runs categorization and recurring charge detection. |
| Categorization and active learning | Implemented | Deterministic rules, merchant mappings, MCC, global dictionary, keyword rules, ML, suggestions and manual correction flow exist. |
| Monthly budgets | Implemented | Monthly summary, CRUD, copy-source and copy-previous are present. |
| Recurring charges | Implemented | Detection, confirm, dismiss, installment and delete flows exist. |
| Reports and analytics | Implemented | Spending, income, income-vs-expenses, Sankey, balance evolution and CSV export exist. |
| Savings goals | Implemented | CRUD, contributions, computed fields and virtual reserve summary exist. |
| Redis dashboard cache | Implemented, optional | App degrades if Redis is unavailable. |
| Docker/Nginx/pgAdmin dev stack | Implemented | Compose defines db, redis, backend, frontend, nginx and pgadmin. |

### Current Validation Status

| Check | Result | Status |
|---|---|---|
| `pytest tests -q` from `Backend` | 251 passed, 5 failed, 1 warning | Not green |
| `npm run lint` from `frontend` | 4 ESLint errors | Not green |

Backend failures are currently concentrated in banking tests that appear
outdated against the current implementation: institution fallback count,
`get_account_balances(..., psu_ip=None, psu_user_agent=None)`, an extra session
lookup during callback, and soft-disconnect replacing hard delete.

Frontend lint currently fails in:

- `frontend/src/app/(dashboard)/settings/loading.tsx`: component declared during render.
- `frontend/src/components/features/budgets/BudgetDonutChart.tsx`: reassignment of `cumulativeArc` after render.

### Codebase Metrics

| Metric | Current Value |
|---|---:|
| Backend domains with routers | 9 |
| Backend route decorators | 46 |
| Alembic migration files | 13 |
| Backend test files | 17 |
| Frontend `page.tsx` files | 12 |
| Frontend feature components | 28 |
| Default system categories | 19 |
| `Backend/data/training_data.csv` lines | 757 |
| `Backend/app/categories/merchant_dictionary.py` lines | 422 |

### Main Versions

| Layer | Technology | Version / Constraint |
|---|---|---|
| Backend runtime | Python | 3.12+ |
| Backend framework | FastAPI | >=0.115 |
| ORM | SQLAlchemy async | >=2.0 |
| Validation | Pydantic | v2 |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| ML | scikit-learn / joblib | >=1.5.2 / >=1.4.2 |
| Frontend framework | Next.js App Router | 16.2.2 |
| React | React / React DOM | 19.2.4 |
| Server state | TanStack React Query | ^5.96.1 |
| Charts | Recharts, D3, d3-sankey | ^3.8.1, ^7.9.0, ^0.12.3 |
| Styling | Tailwind CSS | ^4 |
| Icons | lucide-react | ^1.7.0 |

---

## 2. Architecture

### Monorepo Layout

```text
Wallo/
+-- Backend/
|   +-- app/
|   |   +-- auth/
|   |   +-- banking/
|   |   +-- budgets/
|   |   +-- categories/
|   |   +-- core/
|   |   +-- dashboard/
|   |   +-- goals/
|   |   +-- recurring_charges/
|   |   +-- reports/
|   |   +-- transactions/
|   |   +-- config.py
|   |   +-- database.py
|   |   +-- dependencies.py
|   |   +-- main.py
|   +-- alembic/
|   +-- data/
|   +-- scripts/
|   +-- tests/
|   +-- Dockerfile
+-- frontend/
|   +-- src/
|   |   +-- app/
|   |   +-- components/
|   |   +-- hooks/
|   |   +-- lib/
|   |   +-- providers/
|   |   +-- types/
|   +-- package.json
|   +-- Dockerfile
+-- nginx/
+-- docker-compose.yml
+-- Makefile
+-- AGENTS.root.md
+-- CLAUDE.md
+-- PROJECT_STATUS.md
```

`.env.example` is not present in the current workspace and should not be listed
as an existing file.

### Backend Startup

`Backend/app/main.py` creates the FastAPI app and registers all routers under
`/api/v1`. During lifespan startup it:

- Checks Enable Banking settings.
- Initializes one shared `EnableBankingClient` on `app.state.eb_client`; if
  credentials/key setup fail, banking falls back where supported.
- Seeds the 19 default categories idempotently.
- Connects to Redis and stores it on `app.state.redis`; if Redis is unavailable,
  caching is disabled and the app continues.

On shutdown, it closes the Enable Banking client, Redis connection and database
engine.

### Registered Backend Routers

| Domain | Prefix | Main Capability |
|---|---|---|
| `auth` | `/api/v1/auth` | Register, login, user/profile. |
| `banking` | `/api/v1/banking` | Institutions, connection lifecycle, account listing, sync. |
| `transactions` | `/api/v1/transactions` | Paginated transaction listing and category update. |
| `dashboard` | `/api/v1/dashboard` | Aggregated balances, recent transactions, goals and upcoming charges. |
| `budgets` | `/api/v1/budgets` | Monthly budgets and copy previous month flows. |
| `categories` | `/api/v1/categories` | Category listing/creation, corrections, suggestions, recategorization, retrain trigger. |
| `reports` | `/api/v1/reports` | Analytics and CSV export. |
| `recurring_charges` | `/api/v1/recurring-charges` | Recurring charge review actions. |
| `goals` | `/api/v1/goals` | Savings goals and contributions. |

Additionally, `GET /health` returns `{"status": "ok"}`.

---

## 3. Database And Migrations

### Main Tables

| Table | Purpose |
|---|---|
| `users` | User account, email, name, hashed password, currency and timestamps. |
| `bank_connections` | Per-user bank connection/session metadata and status. |
| `bank_accounts` | Connected bank accounts, balances and sync timestamps. |
| `transactions` | Synced transactions with confirmed category and separate suggestion fields. |
| `categories` | System and custom categories, with icon, color, type and ownership. |
| `category_corrections` | Manual correction history used for active learning. |
| `merchant_mappings` | Per-user learned merchant-to-category mappings, including ambiguity marker. |
| `budgets` | Monthly category limits per user. |
| `recurring_charges` | Detected subscriptions/recurring expenses and review state. |
| `savings_goals` | Virtual savings goals and computed progress inputs. |
| `goal_contributions` | Positive reserve and negative release events for savings goals. |

### Important Schema Details

- Monetary persisted values use `NUMERIC(12, 2)` and Python `Decimal`.
- Timestamps use timezone-aware SQLAlchemy `DateTime(timezone=True)`.
- IDs are UUIDs, mostly generated through PostgreSQL `gen_random_uuid()`.
- `transactions.category` remains as a legacy string column mapped as
  `category_text`.
- `transactions.merchant_category_code` exists and feeds MCC categorization.
- Confirmed categorization uses `category_id`, `categorization_method` and
  `confidence_score`.
- Suggested categorization is separate:
  `suggested_category_id`, `suggested_confidence_score`,
  `suggested_categorization_method`.
- Suggested categories do not count as confirmed category assignment for
  budgets/reports until the user accepts or corrects them.
- `merchant_mappings` has a unique `(user_id, merchant_name)` constraint and
  `is_ambiguous` to avoid unsafe propagation when user corrections conflict.

### Alembic Migrations

Current migration files under `Backend/alembic/versions/`:

| File | Main Change |
|---|---|
| `001_create_users_table.py` | Create `users`. |
| `002_create_banking_tables.py` | Create `bank_connections`, `bank_accounts`. |
| `003_create_transactions_table.py` | Create `transactions`. |
| `004_timestamps_with_timezone.py` | Convert timestamps to timezone-aware. |
| `005_add_categories_and_budgets.py` | Create categories, corrections and budgets. |
| `006_add_category_id_to_transactions.py` | Add transaction category FK. |
| `479f64e97a2f_add_categorization_fields.py` | Add categorization metadata to transactions. |
| `008_add_performance_indexes.py` | Add performance indexes. |
| `ba4c21f3d2d9_add_recurring_charges.py` | Create recurring charges. |
| `7a216d32206a_add_savings_goals_and_contributions.py` | Create savings goals and contributions. |
| `9c1f2a3b4d5e_add_transaction_suggestions.py` | Add transaction suggestion fields and merchant mapping uniqueness. |
| `2b7c8d9e0f1a_backfill_legacy_ml_suggestions.py` | Backfill legacy `ml_suggested` data into suggestion fields. |
| `3c4d5e6f7a8b_add_mcc_and_ambiguous_mappings.py` | Add MCC support and ambiguous merchant mappings. |

---

## 4. Backend Domains

### Auth

Files: `app/auth/router.py`, `service.py`, `models.py`, `schemas.py`.

Endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/profile`
- `PATCH /api/v1/auth/profile`

Auth uses bcrypt/passlib for password hashing and HS256 JWT access tokens. There
is no refresh token endpoint.

### Banking

Files: `app/banking/router.py`, `service.py`, `models.py`, `schemas.py`,
`client.py`, `exceptions.py`.

Endpoints:

- `GET /api/v1/banking/institutions`
- `GET /api/v1/banking/connections`
- `POST /api/v1/banking/connect`
- `POST /api/v1/banking/callback`
- `GET /api/v1/banking/accounts`
- `POST /api/v1/banking/sync`
- `DELETE /api/v1/banking/connections/{connection_id}`

Current behavior:

- `ConnectBankRequest.redirect_url` is optional and can override the configured
  redirect URL, for example for settings callback flows.
- Sandbox mapping can route display banks such as Banco Santander through Mock
  ASPSP while storing the user-facing bank name.
- Sync forwards PSU IP/user-agent headers when available.
- Disconnect is a soft-disconnect: connection status is set to `disconnected`
  while transaction history is preserved.
- Balance priority remains `ITAV > XPCD > CLBD`.

### Transactions

Files: `app/transactions/router.py`, `service.py`, `models.py`, `schemas.py`.

Endpoints:

- `GET /api/v1/transactions/`
- `PATCH /api/v1/transactions/{transaction_id}`

The list endpoint supports pagination and filters including account, category,
uncategorized, search and date range. Responses include confirmed category
details plus suggestion details. `PATCH /transactions/{id}` updates the category
field directly through the transaction endpoint.

Transaction sync:

- Fetches transactions through Enable Banking pagination.
- Parses amounts with `Decimal`.
- Preserves optional bank fields safely.
- Runs categorization for new transactions.
- Updates account balances and sync timestamps.
- Triggers recurring charge detection after sync.
- Invalidates dashboard cache for the user.

### Categories And ML Categorization

Files: `app/categories/router.py`, `service.py`, `models.py`,
`merchant_mapping.py`, `text_cleaner.py`, `keyword_rules.py`,
`merchant_dictionary.py`, `mcc_mapping.py`, `ml_categorizer.py`, `tasks.py`.

Endpoints:

- `GET /api/v1/categories/`
- `POST /api/v1/categories/`
- `PATCH /api/v1/categories/transactions/{transaction_id}/category`
- `POST /api/v1/categories/suggestions/accept`
- `POST /api/v1/categories/recategorize`
- `POST /api/v1/categories/admin/retrain` hidden from OpenAPI

Current categorization cascade:

1. Deterministic income/type rules such as payroll, refunds, transfers, Bizum
   and cash.
2. User merchant mapping, skipped if the merchant key is blocked or ambiguous.
3. MCC mapping using `merchant_category_code`.
4. Global merchant dictionary.
5. Keyword rules.
6. ML model prediction.
7. Threshold handling:
   - `confidence >= 0.70` and enough margin: confirmed category.
   - `0.40 <= confidence < 0.70`: suggestion only.
   - `< 0.40`: uncategorized.

Confirmed methods include values such as `rule_based`, `merchant_map`, `mcc`,
`global_dict`, `keyword_rule`, `ml_auto` and `manual`. Suggested methods include
`keyword_suggested` and `ml_suggested`.

Manual correction:

- Creates a `CategoryCorrection`.
- Updates the transaction as manual with confidence 1.0.
- Upserts the user merchant mapping.
- Marks mappings ambiguous when conflicting corrections exist.
- Propagates same-merchant updates only when the merchant key is safe and not
  ambiguous.

`app/categories/tasks.py` provides synchronous retraining logic. A real Celery
task queue is not configured.

### Budgets

Files: `app/budgets/router.py`, `service.py`, `models.py`, `schemas.py`.

Endpoints:

- `GET /api/v1/budgets/categories`
- `GET /api/v1/budgets/`
- `GET /api/v1/budgets/copy-source`
- `POST /api/v1/budgets/copy-previous`
- `POST /api/v1/budgets/`
- `PUT /api/v1/budgets/{budget_id}`
- `DELETE /api/v1/budgets/{budget_id}`

Budgets are monthly category limits. The summary endpoint includes category
spending, limits and progress. Copy flows find a previous month with budgets and
copy missing category limits into the target month.

### Recurring Charges

Files: `app/recurring_charges/router.py`, `service.py`, `models.py`,
`schemas.py`, `detector.py`.

Endpoints:

- `GET /api/v1/recurring-charges/`
- `PATCH /api/v1/recurring-charges/{charge_id}/confirm`
- `PATCH /api/v1/recurring-charges/{charge_id}/dismiss`
- `PATCH /api/v1/recurring-charges/{charge_id}/installment`
- `DELETE /api/v1/recurring-charges/{charge_id}`

Recurring charge detection groups debit transactions by merchant key, estimates
periodicity, and upserts possible charges. Dismissed charges are respected and
not automatically recreated.

### Dashboard

Files: `app/dashboard/router.py`, `service.py`, `schemas.py`.

Endpoint:

- `GET /api/v1/dashboard/`

Dashboard response includes:

- `total_balance`
- `reserved_for_goals`
- `available_balance`
- `currency`
- `accounts`
- `recent_transactions`
- `last_synced_at`
- `upcoming_charges`
- `active_goal`

The dashboard uses Redis cache when available and falls back to direct DB
aggregation when Redis is unavailable.

### Reports

Files: `app/reports/router.py`, `service.py`, `schemas.py`.

Endpoints:

- `GET /api/v1/reports/spending-by-category`
- `GET /api/v1/reports/income-vs-expenses`
- `GET /api/v1/reports/cashflow-sankey`
- `GET /api/v1/reports/balance-evolution`
- `GET /api/v1/reports/income-by-category`
- `GET /api/v1/reports/export-csv`

Reports support `week`, `month`, `quarter` and `year` periods. CSV export is
implemented in the backend and wired in the frontend reports page through
`ExportCSVButton` and `useExportCSV`.

### Savings Goals

Files: `app/goals/router.py`, `service.py`, `models.py`, `schemas.py`.

Endpoints:

- `GET /api/v1/goals/`
- `POST /api/v1/goals/`
- `GET /api/v1/goals/{goal_id}`
- `PATCH /api/v1/goals/{goal_id}`
- `DELETE /api/v1/goals/{goal_id}`
- `POST /api/v1/goals/{goal_id}/contributions`
- `GET /api/v1/goals/{goal_id}/contributions`

Savings goals are virtual reserves. Positive contributions reserve available
balance, negative contributions release it, and the service prevents reserving
more than the available connected balance.

---

## 5. Frontend

### Routes

Current App Router pages:

| Route | File |
|---|---|
| `/` | `src/app/page.tsx` |
| `/login` | `src/app/(auth)/login/page.tsx` |
| `/register` | `src/app/(auth)/register/page.tsx` |
| `/dashboard` | `src/app/(dashboard)/dashboard/page.tsx` |
| `/transactions` | `src/app/(dashboard)/transactions/page.tsx` |
| `/banking/connect` | `src/app/(dashboard)/banking/connect/page.tsx` |
| `/banking/callback` | `src/app/(dashboard)/banking/callback/page.tsx` |
| `/budgets` | `src/app/(dashboard)/budgets/page.tsx` |
| `/reports` | `src/app/(dashboard)/reports/page.tsx` and `ReportsClient.tsx` |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` |
| `/settings/callback` | `src/app/(dashboard)/settings/callback/page.tsx` |
| `/goals` | `src/app/(dashboard)/goals/page.tsx` |

Several dashboard routes have `loading.tsx` skeleton states, and the dashboard
route group has an `error.tsx`.

### Hooks And Query Keys

| Hook | Key(s) | Backend Areas |
|---|---|---|
| `useAccounts` | `['accounts']` | Banking accounts. |
| `useConnections` | `['connections']` | Banking connections and disconnect. |
| `useDashboard` | `['dashboard']` | Dashboard summary. |
| `useTransactions` | `['transactions', filters]` | Transaction list. |
| `useCategories`, correction mutation | `['categories']`, invalidates `['transactions']` | Categories and corrections. |
| Budget hooks | `['budget-categories']`, `['budgets', month, year]`, `['budget-copy-source', month, year]` | Budget summary, CRUD and copy. |
| `useRecurringCharges` | `['recurring-charges']` | Recurring charge actions. |
| Report hooks | `['reports', reportType, period, date]` | Analytics and CSV export. |
| `useProfile` | `['profile']` | Auth profile. |
| Goal hooks | `['goals', status ?? 'all']`, `['goals', id]`, `['goals', id, 'contributions']` | Goals and contributions. |

### API Layer

`frontend/src/lib/api.ts` contains:

- `ApiError`
- `request<T>()`
- `api.get/post/patch/delete`
- `api.getBlob`
- `budgetApi`
- `categoryApi`
- `recurringApi`
- `goalsApi`

The API wrapper injects JWT auth headers, uses `NEXT_PUBLIC_API_URL`, parses
errors and dispatches a custom `401` event that `AuthProvider` uses for logout.

### Providers And Auth

- `QueryProvider` wraps the app with TanStack React Query.
- `AuthProvider` stores JWT in localStorage through `src/lib/auth.ts`, fetches
  `/auth/me` to validate existing sessions, exposes login/logout state, and
  redirects to `/login` on 401.

### Feature Components

Important components currently present:

- General finance UI: `AccountCard`, `BalanceDisplay`, `TransactionRow`,
  `CategoryBadge`.
- Reports/charts: `SpendingDonutChart`, `IncomeDonutChart`,
  `IncomeExpensesLineChart`, `BalanceEvolutionChart`, `CashflowSankeyChart`,
  `DateNavigator`, `PeriodSelector`, `ExportCSVButton`.
- Budgets: `BudgetCategoryCard`, `BudgetDonutChart`, `BudgetSummaryCard`,
  `NewBudgetModal`, `EditBudgetsModal`, `CopyBudgetBanner`.
- Goals: `GoalSummaryCard`, `GoalCard`, `GoalProgressBar`, `GoalEmptyState`,
  `ContributionPanel`, `ContributionHistory`, `NewGoalModal`, `EditGoalModal`,
  `DeleteGoalDialog`.

---

## 6. Cross-Cutting Flows

### Bank Connection

1. Frontend calls `GET /banking/institutions`.
2. User selects a bank.
3. Frontend calls `POST /banking/connect` with bank name/country and optional
   `redirect_url`.
4. Backend starts Enable Banking authorization, stores a pending connection, and
   returns the redirect URL.
5. User authorizes at the bank.
6. Frontend callback calls `POST /banking/callback`.
7. Backend creates the session, activates/upserts the connection, upserts
   accounts, fetches balances and attempts initial transaction sync.

### Transaction Sync

1. Frontend triggers `POST /banking/sync`.
2. Backend fetches balances and paginated transactions for active accounts.
3. New transactions are categorized.
4. Recurring charge detection runs.
5. Dashboard cache is invalidated.

### Category Suggestion And Correction

Medium-confidence ML or keyword results are stored as suggestions, not confirmed
categories. User actions can:

- Correct one transaction through
  `PATCH /categories/transactions/{transaction_id}/category`.
- Accept suggestions in bulk through `POST /categories/suggestions/accept`.
- Re-run categorization for all non-manual transactions through
  `POST /categories/recategorize`.

Manual corrections preserve user intent, feed merchant mappings and are used as
active-learning data for retraining.

### Savings Goal Reserve Flow

1. Goal is created with a target and optional monthly contribution/deadline.
2. Positive contribution reserves available connected balance.
3. Negative contribution releases money from the goal.
4. Dashboard and goals summary expose total balance, reserved amount and
   available balance.

---

## 7. Configuration And Infrastructure

### Environment Variables Used By Backend

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async PostgreSQL URL. |
| `JWT_SECRET_KEY` | HS256 token secret. |
| `JWT_ALGORITHM` | Defaults to `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Defaults to 30. |
| `ENABLE_BANKING_APP_ID` | Enable Banking application ID. |
| `ENABLE_BANKING_PRIVATE_KEY_PATH` | `.pem` private key path, usually under `Backend/keys/`. |
| `ENABLE_BANKING_ENVIRONMENT` | Defaults to `sandbox`. |
| `ENABLE_BANKING_REDIRECT_URL` | Default banking callback URL. |
| `REDIS_URL` | Redis cache URL. |
| `CORS_ORIGINS` | Comma-separated CORS origins. |
| `NEXT_PUBLIC_API_URL` | Frontend-visible API base URL. |

### Docker Compose Services

| Service | Image / Build | Ports |
|---|---|---|
| `db` | `postgres:16-alpine` | `5432:5432` |
| `redis` | `redis:7-alpine` | `6379:6379` |
| `backend` | `./Backend/Dockerfile` | `8000:8000` |
| `frontend` | `./frontend/Dockerfile` | internal `3001` exposed to Docker network |
| `nginx` | `./nginx/Dockerfile` | `3000:3000` |
| `pgadmin` | `dpage/pgadmin4:8` | `5050:80` |

The frontend dev/server process runs on port `3001` inside the container.
Nginx exposes the external app entrypoint on port `3000`.

---

## 8. Known Gaps And Not Implemented

| Item | Status |
|---|---|
| Celery / real task queue | Not implemented. Retraining is synchronous/threaded, not queued. |
| Automatic background sync scheduler | Not implemented. Sync is user-triggered. |
| Push notifications | Not implemented. |
| Email notifications | Not implemented. |
| Refresh tokens | Not implemented. Only access tokens are issued. |
| Multi-currency FX conversion | Not implemented. No currency conversion service exists. |
| Frontend tests | Not implemented. No frontend test suite is present. |
| Mobile app | Not implemented. Web app only. |
| Dark mode toggle | Not implemented. |
| ML model artifact | Not tracked. `data/models/` artifacts must be trained locally. |
| Nginx certificates | Not tracked. Certificate material is expected to remain outside git. |

---

## 9. Verification Notes

Last verification performed for this update:

- `pytest tests -q` from `Backend`: 251 passed, 5 failed, 1 warning.
- `npm run lint` from `frontend`: failed with 4 ESLint errors.
- CSV export wiring verified in `ReportsClient.tsx`,
  `ExportCSVButton.tsx` and `useReports.ts`.

The failing checks are documented here intentionally. This status file should
not imply that all tests and lint are green until those failures are fixed.
