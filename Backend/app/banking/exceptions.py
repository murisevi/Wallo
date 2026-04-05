class EnableBankingError(Exception):
    """Base exception for all Enable Banking errors."""


class EnableBankingAuthError(EnableBankingError):
    """JWT generation or authentication failure (401/403)."""


class EnableBankingAPIError(EnableBankingError):
    """Non-retryable API error (4xx other than 401/403/429)."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Enable Banking API error {status_code}: {detail}")


class EnableBankingRateLimitError(EnableBankingError):
    """429 Too Many Requests — caller should wait and retry."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limited by Enable Banking"
        if retry_after is not None:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)
