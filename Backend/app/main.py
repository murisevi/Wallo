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

    try:
        app.state.eb_client = EnableBankingClient()
        logger.info("Enable Banking client initialised")
    except EnableBankingAuthError as exc:
        logger.warning("Enable Banking client unavailable at startup: %s", exc)
        app.state.eb_client = None

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.auth.router import router as auth_router  # noqa: E402
from app.banking.router import router as banking_router  # noqa: E402
from app.dashboard.router import router as dashboard_router  # noqa: E402
from app.transactions.router import router as transactions_router  # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(banking_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
