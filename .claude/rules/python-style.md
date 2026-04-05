---
paths:
  - "backend/**/*.py"
---
# Python Code Style

- Formatter/linter: ruff (replaces black + flake8 + isort). Run `ruff check --fix && ruff format`.
- Type checker: mypy strict mode with pydantic plugin.
- Line length: 88 characters.
- Use `typing.Annotated` for all FastAPI Depends(), Query(), Path().
- Ignore ruff B008 (function call in defaults) — required for Depends().
- All functions must have type annotations. No `Any` except in test overrides.
- Async def for all I/O-bound routes (DB queries, HTTP calls). Sync def only for CPU-bound.
- Imports sorted: stdlib → third-party → local. Enforced by ruff isort.
- Tests use pytest + pytest-asyncio with asyncio_mode = "auto".
- Test files mirror app/ structure. Fixtures in conftest.py.
- Security: ruff S (bandit) rules enabled. No hardcoded secrets. No eval/exec.
- Monetary values: always use Decimal, never float.
- SQLAlchemy: Mapped[] + mapped_column() style (2.0). Never legacy Column().
