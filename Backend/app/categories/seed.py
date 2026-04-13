"""Seed default system categories on first startup."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category

DEFAULT_CATEGORIES: list[dict] = [
    # --- GASTOS (14) -------------------------------------------------------
    {
        "name": "Alimentación",
        "icon": "shopping-cart",
        "color": "#22C55E",
        "type": "expense",
    },  # noqa: E501
    {
        "name": "Restaurantes y Bares",
        "icon": "utensils",
        "color": "#F97316",
        "type": "expense",
    },  # noqa: E501
    {"name": "Transporte", "icon": "car", "color": "#3B82F6", "type": "expense"},  # noqa: E501
    {"name": "Vivienda", "icon": "home", "color": "#8B5CF6", "type": "expense"},  # noqa: E501
    {"name": "Suministros", "icon": "zap", "color": "#EAB308", "type": "expense"},  # noqa: E501
    {"name": "Salud", "icon": "heart-pulse", "color": "#EF4444", "type": "expense"},  # noqa: E501
    {"name": "Ocio", "icon": "gamepad-2", "color": "#EC4899", "type": "expense"},  # noqa: E501
    {"name": "Ropa", "icon": "shirt", "color": "#A855F7", "type": "expense"},  # noqa: E501
    {
        "name": "Educación",
        "icon": "graduation-cap",
        "color": "#06B6D4",
        "type": "expense",
    },  # noqa: E501
    {"name": "Suscripciones", "icon": "repeat", "color": "#F59E0B", "type": "expense"},  # noqa: E501
    {"name": "Seguros", "icon": "shield", "color": "#64748B", "type": "expense"},  # noqa: E501
    {"name": "Mascotas", "icon": "dog", "color": "#D946EF", "type": "expense"},  # noqa: E501
    {"name": "Regalos", "icon": "gift", "color": "#F43F5E", "type": "expense"},  # noqa: E501
    {
        "name": "Otros gastos",
        "icon": "circle-dot",
        "color": "#6B7280",
        "type": "expense",
    },  # noqa: E501
    # --- INGRESOS (5) ------------------------------------------------------
    {"name": "Nómina", "icon": "banknote", "color": "#10B981", "type": "income"},  # noqa: E501
    {"name": "Freelance", "icon": "laptop", "color": "#14B8A6", "type": "income"},  # noqa: E501
    {
        "name": "Transferencias recibidas",
        "icon": "arrow-down-left",
        "color": "#0EA5E9",
        "type": "income",
    },  # noqa: E501
    {
        "name": "Devoluciones",
        "icon": "rotate-ccw",
        "color": "#84CC16",
        "type": "income",
    },  # noqa: E501
    {
        "name": "Otros ingresos",
        "icon": "plus-circle",
        "color": "#6B7280",
        "type": "income",
    },  # noqa: E501
]


async def seed_default_categories(db: AsyncSession) -> dict[str, uuid.UUID]:
    """Insert the default system categories if they don't exist yet.

    Idempotent: if any system category (is_custom=False, user_id=NULL) is
    already present we assume the seed has already run and return the existing
    mapping without writing anything.

    Returns a mapping of category name → UUID so callers can reference IDs.
    """
    existing_rows = (
        (
            await db.execute(
                select(Category).where(
                    Category.is_custom.is_(False),
                    Category.user_id.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    existing_by_name: dict[str, Category] = {c.name: c for c in existing_rows}
    changed = False

    for cat_data in DEFAULT_CATEGORIES:
        name = cat_data["name"]
        if name not in existing_by_name:
            # Insert missing category
            cat = Category(**cat_data, is_custom=False, user_id=None)
            db.add(cat)
            await db.flush()
            existing_by_name[name] = cat
            changed = True
        else:
            # Backfill color/icon for categories that got the generic default
            # when the color column was added via migration
            existing = existing_by_name[name]
            if existing.color == "#6B7280" and cat_data["color"] != "#6B7280":
                existing.color = cat_data["color"]
                changed = True
            if existing.icon != cat_data["icon"]:
                existing.icon = cat_data["icon"]
                changed = True

    if changed:
        await db.commit()

    return {name: cat.id for name, cat in existing_by_name.items()}
