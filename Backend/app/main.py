import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup — initialise the Enable Banking client once and share via app.state
    from app.banking.client import EnableBankingClient
    from app.banking.exceptions import EnableBankingAuthError
    from app.categories.seed import seed_default_categories
    from app.config import settings
    from app.database import AsyncSessionLocal

    settings.check_enable_banking()

    try:
        app.state.eb_client = EnableBankingClient()
        logger.info("Enable Banking client initialised successfully")
    except EnableBankingAuthError as exc:
        logger.error(
            "Enable Banking client failed to initialise: %s\n"
            "  → Verify ENABLE_BANKING_PRIVATE_KEY_PATH points to your .pem file "
            "(currently: '%s') and that ENABLE_BANKING_APP_ID is set.\n"
            "  → The /banking/institutions endpoint will return sandbox fallback banks "
            "until this is fixed.",
            exc,
            settings.enable_banking_private_key_path,
        )
        app.state.eb_client = None

    # Seed system categories (idempotent — no-op if already present)
    async with AsyncSessionLocal() as db:
        mapping = await seed_default_categories(db)
        logger.info("Default categories ready (%d categories)", len(mapping))

    yield

    # Shutdown
    if getattr(app.state, "eb_client", None) is not None:
        await app.state.eb_client.close()
    await engine.dispose()


app = FastAPI(
    title="Wallo API",
    description="Personal Finance Management — PSD2 Open Banking",
    version="0.1.0",
    lifespan=lifespan,
)

from app.config import settings as _settings  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.auth.router import router as auth_router  # noqa: E402
from app.banking.router import router as banking_router  # noqa: E402
from app.budgets.router import router as budgets_router  # noqa: E402
from app.categories.router import router as categories_router  # noqa: E402
from app.dashboard.router import router as dashboard_router  # noqa: E402
from app.reports.router import router as reports_router  # noqa: E402
from app.transactions.router import router as transactions_router  # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(banking_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(budgets_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
