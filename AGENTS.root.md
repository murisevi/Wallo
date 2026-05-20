# AGENTS.md — Wallo Codex Operating Guide

## Purpose

These instructions define how Codex should work in the Wallo repository.

Wallo is a TFG personal finance platform for PSD2 Open Banking. It connects European bank accounts through Enable Banking, stores accounts, balances and transactions, and provides ML-powered transaction categorization, budgets, recurring charge detection, reports and dashboard analytics.

## Source-of-truth order

When context conflicts, use this priority:

1. The actual code in the repository.
2. `PROJECT_STATUS.md` for the current implemented state of the product.
3. `CLAUDE.md` for architectural conventions, domain knowledge and operational notes.
4. Older comments, plans or TODOs.

Important: `CLAUDE.md` may contain older phase information. Do not assume a feature is missing just because older notes say it is not implemented. Verify in the code and in `PROJECT_STATUS.md` first.

## Repository shape

Expected monorepo layout:

```text
Wallo/
├── Backend/ or backend/       # FastAPI backend
├── frontend/                  # Next.js frontend
├── nginx/                     # reverse proxy
├── docker-compose.yml
├── Makefile
├── PROJECT_STATUS.md
├── CLAUDE.md
└── AGENTS.md
```

If the backend directory is named `backend/` instead of `Backend/`, use the actual directory name from the repo.

## Working mode

For non-trivial tasks, follow this process:

1. Inspect the relevant files before editing.
2. Summarize the current implementation briefly.
3. Propose a small implementation plan.
4. Identify the files likely to change.
5. Make the smallest safe change.
6. Run the most relevant tests, lint, type checks or build commands.
7. Summarize the diff, validation result and remaining risks.

Do not make broad unrelated refactors while implementing a feature or fixing a bug.

## Change size and reviewability

Prefer changes that could be reviewed comfortably in a pull request.

- Keep edits localized to the affected domain.
- Avoid touching formatting-only changes in unrelated files.
- Do not rename public APIs, database columns, route paths or frontend types unless the task requires it.
- If a change crosses backend and frontend, update both sides in the same task: schema, endpoint, API client, TypeScript types, hooks and UI.
- If a behavioral change is made, add or update tests when the codebase has a suitable test location.

## Security and secrets

Never commit, print, move or modify real secrets.

Forbidden:

- `.env` contents
- `.pem` private key files
- bank credentials
- access tokens or JWT secrets
- production credentials

Enable Banking authentication is handled by redirect flow and RS256 application JWTs. Never implement storage of real bank credentials.

Private keys belong under the backend `keys/` directory and must remain gitignored.

## Product and domain rules

- All backend API routes must be under `/api/v1/`.
- Use JWT Bearer authentication for protected endpoints.
- Money must be represented with `Decimal`/`NUMERIC(12, 2)`, never binary floating point for persisted monetary values.
- Enable Banking amount values arrive as strings and must be parsed safely.
- Enable Banking pagination uses `continuation_key`; keep fetching until the key is null, even if an intermediate response has an empty transaction list.
- Bank fields vary by institution; handle optional/missing values gracefully.
- Balance preference is `ITAV` first, then `XPCD`, then `CLBD`.
- Redis is optional in development; the app should degrade gracefully if unavailable.

## Backend architecture summary

Backend domains follow this layered pattern:

```text
router.py   -> HTTP layer only
service.py  -> business logic and orchestration
models.py   -> SQLAlchemy models
schemas.py  -> Pydantic request/response schemas
```

Dependency direction:

```text
router -> service -> models/schemas
```

Never reverse this direction.

## Frontend architecture summary

Frontend uses Next.js App Router with TypeScript strict mode.

- Server Components by default.
- Use `"use client"` only for interactivity, hooks, browser APIs or client state.
- Use TanStack React Query for server state.
- Do not introduce Redux or Zustand.
- Route API calls through `src/lib/api.ts`; do not use raw `fetch` in components.
- Keep shared backend-facing interfaces in `src/types/`.

## Validation commands

Use the most relevant commands for the changed area.

Backend, from the backend directory:

```bash
pytest tests/ -v --cov=app
ruff check app/ --fix && ruff format app/
alembic upgrade head
```

Frontend, from `frontend/`:

```bash
npm run lint
npm run build
```

Docker, from repo root:

```bash
docker compose up -d
docker compose logs -f backend
docker compose down -v
```

Only run broad commands when useful. For small changes, prefer targeted tests first.

## Database and migration policy

When changing SQLAlchemy models:

1. Check whether an Alembic migration is required.
2. Ensure Alembic imports all relevant models for autogenerate.
3. Generate migrations only when the schema actually changes.
4. Inspect generated migrations before accepting them.
5. Preserve naming conventions for indexes, unique constraints, checks, foreign keys and primary keys.

## Definition of done

A task is done only when:

- the implementation is minimal and fits existing architecture;
- backend/frontend contracts are synchronized when applicable;
- relevant tests, lint or build checks have been run or a clear reason is given;
- secrets and generated artifacts were not committed;
- the final response includes changed files, validation performed and known risks.

## Commit style

Use Conventional Commits when asked to propose or create commits:

```text
feat(api): add endpoint for monthly report
fix(frontend): handle empty recurring charge state
docs: update setup instructions
refactor(categories): simplify cascade lookup
```

Use branches like:

```text
feature/<short-name>
fix/<short-name>
```
