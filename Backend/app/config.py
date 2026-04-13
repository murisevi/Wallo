import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Try backend/.env first, then repo-root .env (for running uvicorn from /backend)
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://wallo:wallo@localhost:5432/wallo"

    # ── Auth ──────────────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ── Enable Banking ────────────────────────────────────────────────────────
    enable_banking_app_id: str = ""
    enable_banking_private_key_path: str = "keys/private.pem"
    enable_banking_environment: str = "sandbox"
    enable_banking_redirect_url: str = "https://localhost:3000/banking/callback"

    # ── Frontend ──────────────────────────────────────────────────────────────
    next_public_api_url: str = "http://localhost:8000/api/v1"
    # Comma-separated list of allowed CORS origins.
    # Both http and https localhost are included so the app works with or without nginx.
    cors_origins: str = "http://localhost:3000,https://localhost:3000"

    # ── Redis (optional for MVP) ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    def check_enable_banking(self) -> None:
        """Log warnings if Enable Banking credentials look misconfigured."""
        if not self.enable_banking_app_id:
            logger.warning(
                "ENABLE_BANKING_APP_ID is not set. "
                "Add it to your .env file (find it in the Enable Banking control panel)."
            )
        key_path = Path(self.enable_banking_private_key_path)
        if not key_path.is_absolute():
            # Resolve relative to the backend root (two levels above app/)
            key_path = Path(__file__).resolve().parents[1] / key_path
        if not key_path.exists():
            logger.warning(
                "Enable Banking private key not found at '%s'. "
                "Download the .pem file from the Enable Banking control panel and "
                "set ENABLE_BANKING_PRIVATE_KEY_PATH in your .env to its path "
                "(relative to the backend directory, e.g. keys/your-app-id.pem).",
                key_path,
            )


settings = Settings()
