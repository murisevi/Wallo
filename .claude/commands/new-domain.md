Create a new backend domain module at backend/app/$ARGUMENTS/ with these files:

- __init__.py (empty)
- router.py — FastAPI APIRouter with tags=["$ARGUMENTS"], ready to register in main.py
- schemas.py — Pydantic BaseModel stubs: Create, Update, Response with model_config from_attributes
- models.py — SQLAlchemy model with Mapped[] annotations, UUID id + created_at + updated_at
- service.py — Service class with async CRUD methods accepting AsyncSession

Follow all conventions from CLAUDE.md and .claude/rules/python-style.md.
Register the router in app/main.py with prefix /api/v1/$ARGUMENTS.
Import the model in alembic/env.py target_metadata.
