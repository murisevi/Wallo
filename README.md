# Wallo

Wallo is a personal finance web application developed as a Final Degree Project
(TFG). It lets users create an account, connect bank accounts through
PSD2/Open Banking with Enable Banking, synchronize balances and transactions,
categorize transactions, manage budgets, detect recurring charges, view
reports, and virtually allocate money to savings goals.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, TanStack Query |
| Backend | FastAPI, Python 3.12, SQLAlchemy async, Pydantic v2, Alembic |
| Database | PostgreSQL 16 |
| Cache | Redis 7, optional but included in Docker |
| Open Banking | Enable Banking |
| Local development/deployment | Docker Compose, nginx, pgAdmin |

## Requirements

To run the full application with Docker:

- Docker Desktop or Docker Engine with Docker Compose.
- An Enable Banking sandbox application if you want to test an actual banking
  connection.

For development without Docker, you will also need:

- Python 3.12 or later.
- Node.js 20 or later.
- npm.

## Initial Setup

Clone the repository and create your environment file:

```bash
git clone https://github.com/murisevi/Wallo.git
cd Wallo
cp .env.example .env
```

On Windows PowerShell, if `cp` is not available:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and review these values:

```env
JWT_SECRET_KEY=put-a-long-random-secret-here
ENABLE_BANKING_APP_ID=your-application-id
ENABLE_BANKING_PRIVATE_KEY_PATH=keys/private.pem
ENABLE_BANKING_ENVIRONMENT=sandbox
ENABLE_BANKING_REDIRECT_URL=https://localhost:3000/banking/callback
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
CORS_ORIGINS=http://localhost:3000,https://localhost:3000
```

The Enable Banking `.pem` private key must be stored at:

```text
Backend/keys/private.pem
```

The path in `.env` is relative to the backend, so the recommended value is
`keys/private.pem`. Never commit this key to the repository.

## Configure Enable Banking

1. Open the Enable Banking dashboard and create an application in sandbox mode.
2. Copy the Application ID into `ENABLE_BANKING_APP_ID`.
3. Download the `.pem` private key and save it as `Backend/keys/private.pem`.
4. Register this redirect URL for the Docker setup:

```text
https://localhost:3000/banking/callback
```

The nginx container uses HTTPS with a self-signed certificate for localhost. The
browser will show a security warning the first time; accept it only for local
development.

## Recommended Docker Setup

On the first run, start the infrastructure first, apply migrations, and then
start the full application:

```bash
docker compose build
docker compose up -d db redis
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

On later runs, this is usually enough:

```bash
docker compose up -d
```

The application will be available at:

- Frontend: https://localhost:3000
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- pgAdmin: http://localhost:5050

Default pgAdmin credentials:

```text
Email: admin@wallo.com
Password: admin
```

To view logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

To stop the services without deleting data:

```bash
docker compose down
```

To stop the services and also delete the PostgreSQL volume:

```bash
docker compose down -v
```

## First Use

1. Open https://localhost:3000.
2. Accept the local certificate if the browser asks you to.
3. Register a user.
4. Sign in.
5. Go to the bank connection option.
6. Select a sandbox bank, usually BBVA or Mock ASPSP depending on your Enable
   Banking account.
7. Complete the authorization flow.
8. When you return to Wallo, the backend will synchronize accounts, balances,
   and transactions.

## Local Development Without Running the Full App in Docker

You can use Docker only for PostgreSQL and Redis, and run the backend/frontend
on your machine.

### 1. Start PostgreSQL and Redis

```bash
docker compose up -d db redis
```

### 2. Backend

From another terminal:

```bash
cd Backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov ruff
```

Apply migrations and start FastAPI:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

From another terminal:

```bash
cd frontend
npm install
npm run dev
```

The local Next.js frontend listens on:

```text
http://localhost:3001
```

If you use this mode without nginx, adjust `.env` so the backend accepts the
frontend origin and Enable Banking redirects back to the correct port:

```env
ENABLE_BANKING_REDIRECT_URL=http://localhost:3001/banking/callback
CORS_ORIGINS=http://localhost:3001,http://localhost:3000,https://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

You must also register `http://localhost:3001/banking/callback` as a redirect
URL in Enable Banking if you are going to test the bank connection in this mode.

## Useful Commands

Backend:

```bash
cd Backend
pytest tests/ -v --cov=app
ruff check app/ tests/
ruff format app/ tests/
alembic upgrade head
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Docker:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose run --rm backend alembic current
docker compose run --rm backend alembic upgrade head
```

## Main Environment Variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy async connection to PostgreSQL. Docker overrides it to use `db`. |
| `REDIS_URL` | Redis connection. Docker overrides it to use `redis`. |
| `JWT_SECRET_KEY` | Secret used to sign JWT tokens. Always change it outside demos. |
| `ENABLE_BANKING_APP_ID` | Application ID in Enable Banking. |
| `ENABLE_BANKING_PRIVATE_KEY_PATH` | Path to the `.pem` key, relative to `Backend/`. |
| `ENABLE_BANKING_ENVIRONMENT` | Usually `sandbox` during development. |
| `ENABLE_BANKING_REDIRECT_URL` | URL where Enable Banking returns the `code`. |
| `NEXT_PUBLIC_API_URL` | Public backend URL used by the frontend. |
| `CORS_ORIGINS` | Origins allowed by FastAPI, separated by commas. |

## Troubleshooting

If the backend starts but cannot connect to Enable Banking:

- Check that `ENABLE_BANKING_APP_ID` exists in `.env`.
- Check that `Backend/keys/private.pem` exists.
- Check that `ENABLE_BANKING_PRIVATE_KEY_PATH=keys/private.pem`.
- Review `docker compose logs -f backend`.

If the banking flow returns with an error:

- Confirm that the redirect URL registered in Enable Banking exactly matches
  `ENABLE_BANKING_REDIRECT_URL`.
- In Docker, use `https://localhost:3000/banking/callback`.
- In development without nginx, use `http://localhost:3001/banking/callback`.

If the frontend cannot call the backend:

- Check `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.
- Check that `CORS_ORIGINS` includes the origin where you open the frontend.
- Review the browser console and backend logs.

If the database is empty or tables are missing:

```bash
docker compose run --rm backend alembic upgrade head
```

If you want to completely reset the local database:

```bash
docker compose down -v
docker compose build
docker compose up -d db redis
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

## Security

Do not commit:

- `.env`
- `.pem` keys
- tokens
- bank credentials
- database dumps containing real data

The `.gitignore` file already excludes sensitive files and local project
planning documents.

## License

This project was developed as a Final Degree Project. It does not include a
license for external use by default.
