from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    enable_banking_redirect_url: str = "http://localhost:3000/banking/callback"

    # ── Frontend ──────────────────────────────────────────────────────────────
    next_public_api_url: str = "http://localhost:8000/api/v1"

    # ── Redis (optional for MVP) ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
