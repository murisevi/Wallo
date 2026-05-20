# Budgets Screen Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir `POST /budgets/copy-previous` en el backend y refactorizar el frontend de presupuestos con donut chart, banner de copia, tarjetas clickables y layout alineado al mockup.

**Architecture:** Nuevo endpoint de backend copia presupuestos del mes anterior saltando duplicados. En el frontend, el `page.tsx` se convierte en un orquestador delgado que compone 6 subcomponentes extraídos a `components/features/budgets/`. El click en tarjeta navega a `/transactions?category_id=<uuid>&date_from=...&date_to=...`, que la página de transacciones ya soporta vía `useSearchParams`.

**Tech Stack:** Python/FastAPI (backend), Next.js 14 App Router, React Query, Recharts (nuevo), Tailwind CSS.

---

## Mapa de archivos

| Acción | Archivo |
|--------|---------|
| Modificar | `Backend/app/budgets/service.py` — añadir `copy_previous_month()` |
| Modificar | `Backend/app/budgets/router.py` — añadir endpoint `POST /copy-previous` |
| Crear | `Backend/tests/budgets/__init__.py` |
| Crear | `Backend/tests/budgets/test_copy_previous.py` |
| Modificar | `frontend/src/lib/api.ts` — añadir `budgetApi.copyPrevious()` |
| Modificar | `frontend/src/hooks/useBudgets.ts` — añadir `useCopyPreviousBudgets()` |
| Crear | `frontend/src/components/features/budgets/BudgetCategoryCard.tsx` |
| Crear | `frontend/src/components/features/budgets/BudgetDonutChart.tsx` |
| Crear | `frontend/src/components/features/budgets/BudgetSummaryCard.tsx` |
| Crear | `frontend/src/components/features/budgets/CopyBudgetBanner.tsx` |
| Crear | `frontend/src/components/features/budgets/NewBudgetModal.tsx` |
| Crear | `frontend/src/components/features/budgets/EditBudgetsModal.tsx` |
| Modificar | `frontend/src/app/(dashboard)/budgets/page.tsx` — orquestador delgado |

---

## Task 1: Backend — service `copy_previous_month`

**Files:**
- Modify: `Backend/app/budgets/service.py`
- Create: `Backend/tests/budgets/__init__.py`
- Create: `Backend/tests/budgets/test_copy_previous.py`

- [ ] **Step 1: Crear directorio de tests de budgets**

```bash
# Desde Backend/
touch tests/budgets/__init__.py
```

- [ ] **Step 2: Escribir el test que falla**

Crear `Backend/tests/budgets/test_copy_previous.py`:

```python
"""Tests for copy_previous_month service function."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.budgets.service import copy_previous_month, create_budget
from app.budgets.schemas import BudgetCreate
from app.categories.models import Category
from app.auth.models import User


async def _seed_user_and_category(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a test user and a test category, return (user_id, category_id)."""
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed",
        name="Test User",
    )
    db.add(user)
    await db.flush()

    category = Category(
        name="Alimentación",
        icon="shopping-cart",
        color="#16a34a",
        type="expense",
        user_id=None,  # system category
    )
    db.add(category)
    await db.flush()

    return user.id, category.id


@pytest.mark.asyncio
async def test_copy_previous_month_creates_budgets(client, setup_db):
    """copy_previous_month should clone budgets from M-1 into M."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, category_id = await _seed_user_and_category(db)

        # Create a budget in month 3/2025
        await create_budget(
            db=db,
            user_id=user_id,
            data=BudgetCreate(
                category_id=category_id,
                amount_limit=500,
                month=3,
                year=2025,
            ),
        )

        # Copy to month 4/2025
        summary = await copy_previous_month(db=db, user_id=user_id, month=4, year=2025)

    assert len(summary.budgets) == 1
    assert summary.month == 4
    assert summary.year == 2025
    assert summary.budgets[0].amount_limit == 500


@pytest.mark.asyncio
async def test_copy_previous_month_skips_duplicates(client, setup_db):
    """copy_previous_month must not fail if some budgets already exist for the target month."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, category_id = await _seed_user_and_category(db)

        # Create budget in month 3 and also in month 4 (duplicate)
        for m in (3, 4):
            await create_budget(
                db=db,
                user_id=user_id,
                data=BudgetCreate(
                    category_id=category_id,
                    amount_limit=500,
                    month=m,
                    year=2025,
                ),
            )

        # Copying again to month 4 should not raise
        summary = await copy_previous_month(db=db, user_id=user_id, month=4, year=2025)

    assert len(summary.budgets) == 1


@pytest.mark.asyncio
async def test_copy_previous_month_returns_empty_when_previous_empty(client, setup_db):
    """If M-1 has no budgets, the result for M is also empty."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, _ = await _seed_user_and_category(db)
        summary = await copy_previous_month(db=db, user_id=user_id, month=4, year=2025)

    assert summary.budgets == []


@pytest.mark.asyncio
async def test_copy_previous_month_wraps_january_to_december(client, setup_db):
    """Copying from January should look at December of the previous year."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, category_id = await _seed_user_and_category(db)

        await create_budget(
            db=db,
            user_id=user_id,
            data=BudgetCreate(
                category_id=category_id,
                amount_limit=300,
                month=12,
                year=2024,
            ),
        )

        # Copy to January 2025
        summary = await copy_previous_month(db=db, user_id=user_id, month=1, year=2025)

    assert len(summary.budgets) == 1
    assert summary.month == 1
    assert summary.year == 2025
```

- [ ] **Step 3: Ejecutar tests para verificar que fallan**

```bash
# Desde Backend/
pytest tests/budgets/test_copy_previous.py -v
```
Esperado: ERROR — `ImportError: cannot import name 'copy_previous_month' from 'app.budgets.service'`

- [ ] **Step 4: Implementar `copy_previous_month` en `service.py`**

Añadir al final de `Backend/app/budgets/service.py` (después de `delete_budget`):

```python
async def copy_previous_month(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: int,
    year: int,
) -> BudgetSummaryResponse:
    """Clone budgets from the previous month into month/year.

    Silently skips categories that already have a budget for the target month.
    Returns the full monthly summary after the copy.
    """
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    # Fetch all budgets from the previous month
    stmt = select(Budget).where(
        Budget.user_id == user_id,
        Budget.month == prev_month,
        Budget.year == prev_year,
    )
    prev_budgets = (await db.execute(stmt)).scalars().all()

    for prev in prev_budgets:
        # Skip if already exists in the target month
        dup_stmt = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == prev.category_id,
            Budget.month == month,
            Budget.year == year,
        )
        existing = (await db.execute(dup_stmt)).scalar_one_or_none()
        if existing is not None:
            continue

        db.add(
            Budget(
                user_id=user_id,
                category_id=prev.category_id,
                amount_limit=prev.amount_limit,
                month=month,
                year=year,
            )
        )

    await db.flush()
    return await get_monthly_summary(db=db, user_id=user_id, month=month, year=year)
```

- [ ] **Step 5: Añadir import en `service.py`**

El import de `copy_previous_month` en `service.py` no requiere cambios — ya tiene `select`, `Budget`, `get_monthly_summary` disponibles en el mismo archivo.

Verificar que las importaciones del archivo incluyen todo lo necesario (ya están: `select`, `Budget`, `AsyncSession`, `uuid`, `BudgetSummaryResponse`, `get_monthly_summary`).

- [ ] **Step 6: Ejecutar tests para verificar que pasan**

```bash
pytest tests/budgets/test_copy_previous.py -v
```
Esperado: 4 PASSED

---

## Task 2: Backend — endpoint `POST /budgets/copy-previous`

**Files:**
- Modify: `Backend/app/budgets/router.py`

- [ ] **Step 1: Añadir el endpoint al router**

En `Backend/app/budgets/router.py`, añadir el import de `copy_previous_month` y el endpoint. El bloque de imports queda:

```python
from app.budgets.service import (
    copy_previous_month,
    create_budget,
    delete_budget,
    get_categories,
    get_monthly_summary,
    update_budget,
)
```

Añadir el endpoint después del `GET /`:

```python
@router.post("/copy-previous", response_model=BudgetSummaryResponse)
async def copy_previous_month_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    month: Annotated[int, Query(ge=1, le=12, description="Target month (1-12)")] = 1,
    year: Annotated[int, Query(ge=2000, description="Target year")] = 2024,
) -> BudgetSummaryResponse:
    """Copy budgets from the previous month into the given month.

    Silently skips categories that already have a budget for the target month.
    """
    return await copy_previous_month(
        db=db,
        user_id=current_user.id,
        month=month,
        year=year,
    )
```

- [ ] **Step 2: Verificar que el servidor arranca sin errores**

```bash
# Desde Backend/
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Esperado: servidor arranca sin errores de importación. Verificar en `http://localhost:8000/docs` que aparece `POST /api/v1/budgets/copy-previous`.

- [ ] **Step 3: Ejecutar la suite completa de tests**

```bash
pytest tests/ -v
```
Esperado: todos los tests anteriores siguen pasando + 4 nuevos de budgets.

---

## Task 3: Frontend — instalar Recharts y añadir `budgetApi.copyPrevious`

**Files:**
- Modify: `frontend/package.json` (vía npm)
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Instalar recharts**

```bash
# Desde frontend/
npm install recharts
```
Esperado: `recharts` aparece en `package.json` dependencies.

- [ ] **Step 2: Añadir `copyPrevious` a `budgetApi` en `lib/api.ts`**

Localizar el bloque `export const budgetApi = { ... }` y añadir el método al final del objeto (antes del cierre `}`):

```ts
  copyPrevious(month: number, year: number): Promise<BudgetSummary> {
    return api.post<BudgetSummary>(`/budgets/copy-previous?month=${month}&year=${year}`);
  },
```

El bloque completo queda:

```ts
export const budgetApi = {
  getCategories(): Promise<Category[]> {
    return api.get<Category[]>('/budgets/categories');
  },

  getSummary(month: number, year: number): Promise<BudgetSummary> {
    return api.get<BudgetSummary>(`/budgets/?month=${month}&year=${year}`);
  },

  createBudget(data: BudgetCreate): Promise<Budget> {
    return api.post<Budget>('/budgets/', data);
  },

  updateBudget(id: string, data: BudgetUpdate): Promise<Budget> {
    return api.put<Budget>(`/budgets/${id}`, data);
  },

  deleteBudget(id: string): Promise<void> {
    return api.delete<void>(`/budgets/${id}`);
  },

  copyPrevious(month: number, year: number): Promise<BudgetSummary> {
    return api.post<BudgetSummary>(`/budgets/copy-previous?month=${month}&year=${year}`);
  },
};
```

- [ ] **Step 3: Verificar TypeScript**

```bash
# Desde frontend/
npm run lint
```
Esperado: sin errores nuevos.

---

## Task 4: Frontend — `useCopyPreviousBudgets` en `useBudgets.ts`

**Files:**
- Modify: `frontend/src/hooks/useBudgets.ts`

- [ ] **Step 1: Añadir el hook al final de `useBudgets.ts`**

```ts
export function useCopyPreviousBudgets() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ month, year }: { month: number; year: number }) =>
      budgetApi.copyPrevious(month, year),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}
```

El archivo completo de `frontend/src/hooks/useBudgets.ts` queda:

```ts
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { budgetApi } from '@/lib/api';
import type { BudgetCreate, BudgetUpdate } from '@/types/budget';

export function useBudgetCategories() {
  return useQuery({
    queryKey: ['budget-categories'],
    queryFn: () => budgetApi.getCategories(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBudgetSummary(month: number, year: number) {
  return useQuery({
    queryKey: ['budgets', month, year],
    queryFn: () => budgetApi.getSummary(month, year),
  });
}

export function useCreateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BudgetCreate) => budgetApi.createBudget(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}

export function useUpdateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BudgetUpdate }) =>
      budgetApi.updateBudget(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}

export function useDeleteBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => budgetApi.deleteBudget(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}

export function useCopyPreviousBudgets() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ month, year }: { month: number; year: number }) =>
      budgetApi.copyPrevious(month, year),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
npm run lint
```
Esperado: sin errores.

---

## Task 5: Frontend — componente `BudgetCategoryCard`

**Files:**
- Create: `frontend/src/components/features/budgets/BudgetCategoryCard.tsx`

Este componente muestra una tarjeta de categoría con el layout del mockup (nombre+importe a la derecha, barra a ancho completo) y navega a `/transactions` al hacer clic.

- [ ] **Step 1: Crear el componente**

Crear `frontend/src/components/features/budgets/BudgetCategoryCard.tsx`:

```tsx
'use client';

import { useRouter } from 'next/navigation';
import {
  ShoppingCart, Utensils, Car, Home, Heart, Shirt, BookOpen, Repeat, HelpCircle,
} from 'lucide-react';
import type { Budget } from '@/types/budget';

// ─── Helpers (locales a este componente) ─────────────────────────────────────

const ICON_MAP: Record<string, React.ElementType> = {
  'shopping-cart': ShoppingCart,
  utensils: Utensils,
  car: Car,
  home: Home,
  heart: Heart,
  shirt: Shirt,
  book: BookOpen,
  repeat: Repeat,
};

const CATEGORY_COLORS: Record<string, { bg: string; icon: string }> = {
  'shopping-cart': { bg: 'bg-green-100',  icon: 'text-green-600' },
  utensils:        { bg: 'bg-amber-100',  icon: 'text-amber-600' },
  car:             { bg: 'bg-red-100',    icon: 'text-red-500' },
  home:            { bg: 'bg-blue-100',   icon: 'text-blue-600' },
  heart:           { bg: 'bg-pink-100',   icon: 'text-pink-500' },
  shirt:           { bg: 'bg-purple-100', icon: 'text-purple-600' },
  book:            { bg: 'bg-indigo-100', icon: 'text-indigo-600' },
  repeat:          { bg: 'bg-violet-100', icon: 'text-violet-600' },
};

function formatEur(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(num);
}

function progressBarColor(pct: number): string {
  if (pct >= 100) return 'bg-red-500';
  if (pct >= 80) return 'bg-yellow-500';
  return 'bg-green-500';
}

function lastDayOfMonth(year: number, month: number): string {
  return new Date(year, month, 0).toISOString().slice(0, 10);
}

// ─── Component ───────────────────────────────────────────────────────────────

interface BudgetCategoryCardProps {
  budget: Budget;
}

export function BudgetCategoryCard({ budget }: BudgetCategoryCardProps) {
  const router = useRouter();
  const pct = Math.min(budget.percentage, 100);
  const colors = CATEGORY_COLORS[budget.category_icon] ?? { bg: 'bg-gray-100', icon: 'text-gray-500' };
  const Icon = ICON_MAP[budget.category_icon] ?? HelpCircle;

  const dateFrom = `${budget.year}-${String(budget.month).padStart(2, '0')}-01`;
  const dateTo = lastDayOfMonth(budget.year, budget.month);

  function handleClick() {
    const params = new URLSearchParams({
      category_id: budget.category_id,
      date_from: dateFrom,
      date_to: dateTo,
    });
    router.push(`/transactions?${params.toString()}`);
  }

  return (
    <div
      onClick={handleClick}
      className="cursor-pointer rounded-2xl bg-white p-4 shadow-[0_2px_8px_rgba(48,51,51,0.06)] hover:shadow-[0_4px_16px_rgba(48,51,51,0.1)] transition-shadow"
    >
      {/* Top row: icon + name + amounts */}
      <div className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${colors.bg}`}
        >
          <Icon size={18} className={colors.icon} />
        </div>

        <p className="flex-1 text-sm font-bold text-[#303333]">{budget.category_name}</p>

        <p className="shrink-0 text-xs text-[#5d605f]">
          Gastado{' '}
          <span className="font-semibold text-[#303333]">{formatEur(budget.amount_spent)}</span>
          {' / '}
          {formatEur(budget.amount_limit)}
        </p>
      </div>

      {/* Progress bar */}
      <div className="mt-3 flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full transition-all ${progressBarColor(budget.percentage)}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="w-10 shrink-0 text-right text-xs font-semibold text-[#5d605f]">
          {budget.percentage.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
npm run lint
```
Esperado: sin errores.

---

## Task 6: Frontend — componente `BudgetDonutChart`

**Files:**
- Create: `frontend/src/components/features/budgets/BudgetDonutChart.tsx`

- [ ] **Step 1: Crear el componente**

Crear `frontend/src/components/features/budgets/BudgetDonutChart.tsx`:

```tsx
'use client';

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import type { Budget } from '@/types/budget';

// Hex colors para Recharts (no acepta clases Tailwind)
const DONUT_COLORS: Record<string, string> = {
  'shopping-cart': '#16a34a', // green-600
  utensils:        '#d97706', // amber-600
  car:             '#ef4444', // red-500
  home:            '#2563eb', // blue-600
  heart:           '#ec4899', // pink-500
  shirt:           '#9333ea', // purple-600
  book:            '#4f46e5', // indigo-600
  repeat:          '#7c3aed', // violet-600
};
const DEFAULT_COLOR = '#94a3b8'; // slate-400

function formatEur(value: number): string {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(value);
}

interface BudgetDonutChartProps {
  budgets: Budget[];
  totalSpent: string;
}

export function BudgetDonutChart({ budgets, totalSpent }: BudgetDonutChartProps) {
  const chartData = budgets
    .filter((b) => parseFloat(b.amount_spent) > 0)
    .map((b) => ({
      name: b.category_name,
      value: parseFloat(b.amount_spent),
      color: DONUT_COLORS[b.category_icon] ?? DEFAULT_COLOR,
    }));

  // No renderizar si hay menos de 2 categorías con gasto
  if (chartData.length < 2) return null;

  return (
    <div className="relative flex items-center justify-center">
      <ResponsiveContainer width={180} height={180}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            innerRadius={52}
            outerRadius={80}
            paddingAngle={2}
            strokeWidth={0}
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [formatEur(value), 'Gastado']}
            contentStyle={{
              borderRadius: '12px',
              border: 'none',
              boxShadow: '0 4px 16px rgba(48,51,51,0.12)',
              fontSize: '12px',
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Total en el centro */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
          Total
        </span>
        <span className="text-base font-extrabold text-[#303333]">
          {formatEur(parseFloat(totalSpent))}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
npm run lint
```
Esperado: sin errores.

---

## Task 7: Frontend — componente `BudgetSummaryCard`

**Files:**
- Create: `frontend/src/components/features/budgets/BudgetSummaryCard.tsx`

- [ ] **Step 1: Crear el componente**

Crear `frontend/src/components/features/budgets/BudgetSummaryCard.tsx`:

```tsx
'use client';

import { BudgetDonutChart } from './BudgetDonutChart';
import type { BudgetSummary } from '@/types/budget';

function formatEur(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(num);
}

function statusBadgeClass(status: string): string {
  if (status === 'SUPERADO') return 'bg-red-100 text-red-700';
  if (status === 'CERCA DEL LÍMITE') return 'bg-yellow-100 text-yellow-700';
  return 'bg-green-100 text-green-700';
}

interface BudgetSummaryCardProps {
  data: BudgetSummary;
}

export function BudgetSummaryCard({ data }: BudgetSummaryCardProps) {
  const availableNum = parseFloat(data.total_available);
  const isOverBudget = availableNum < 0;

  return (
    <div className="rounded-2xl bg-gray-50 p-5 shadow-[0_2px_12px_rgba(48,51,51,0.06)]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-stretch">

        {/* Left: gasto total + barra + donut */}
        <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
          {/* Donut chart */}
          <BudgetDonutChart budgets={data.budgets} totalSpent={data.total_spent} />

          {/* Texto */}
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-xs font-semibold text-[#5d605f]">Gasto Total</p>
              <div className="mt-0.5 flex items-center gap-3">
                <span className="text-3xl font-extrabold tracking-tight text-[#303333]">
                  {formatEur(data.total_spent)}
                </span>
                <span
                  className={`rounded-full px-3 py-0.5 text-xs font-bold ${statusBadgeClass(data.status)}`}
                >
                  {data.status}
                </span>
              </div>
            </div>

            {parseFloat(data.total_limit) > 0 && (
              <div>
                <div className="mb-1 flex items-center justify-between text-xs text-[#5d605f]">
                  <span>Progreso mensual</span>
                  <span className="font-semibold">
                    {data.percentage.toFixed(0)}% de {formatEur(data.total_limit)}
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] transition-all"
                    style={{ width: `${Math.min(data.percentage, 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: disponible + mensaje */}
        <div className="shrink-0 rounded-xl border border-[#e8e9e8] bg-white p-4 sm:w-64">
          <p className="text-xs font-semibold text-[#5d605f]">Disponible</p>
          <p className={`mt-0.5 text-2xl font-extrabold ${isOverBudget ? 'text-red-600' : 'text-green-600'}`}>
            {isOverBudget ? '' : '+'}{formatEur(data.total_available)}
          </p>
          <p className="mt-2 text-xs leading-relaxed text-[#5d605f]">
            {data.comparison_message}
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
npm run lint
```
Esperado: sin errores.

---

## Task 8: Frontend — componente `CopyBudgetBanner`

**Files:**
- Create: `frontend/src/components/features/budgets/CopyBudgetBanner.tsx`

- [ ] **Step 1: Crear el componente**

Crear `frontend/src/components/features/budgets/CopyBudgetBanner.tsx`:

```tsx
'use client';

import { Copy, X } from 'lucide-react';
import type { BudgetSummary } from '@/types/budget';

const MONTH_NAMES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

function formatEur(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(num);
}

interface CopyBudgetBannerProps {
  /** El mes de destino (1-12) */
  month: number;
  /** El año de destino */
  year: number;
  /** Datos del mes anterior (source) */
  previousSummary: BudgetSummary;
  /** Indica si la mutación copy está en curso */
  isCopying: boolean;
  /** Callback al confirmar la copia */
  onCopy: () => void;
  /** Callback al descartar el banner */
  onDismiss: () => void;
}

export function CopyBudgetBanner({
  month,
  previousSummary,
  isCopying,
  onCopy,
  onDismiss,
}: CopyBudgetBannerProps) {
  const prevMonthName = MONTH_NAMES[previousSummary.month - 1];
  const currentMonthName = MONTH_NAMES[month - 1];
  const count = previousSummary.budgets.length;
  const total = previousSummary.total_limit;

  return (
    <div className="flex items-start gap-4 rounded-2xl border border-[#0060ad]/20 bg-[#e8f0f8] p-5">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#0060ad]/10">
        <Copy size={18} className="text-[#0060ad]" />
      </div>

      <div className="flex-1">
        <p className="text-sm font-bold text-[#303333]">
          No tienes presupuestos para {currentMonthName}.
        </p>
        <p className="mt-0.5 text-xs text-[#5d605f]">
          ¿Copiar los de {prevMonthName}?{' '}
          <span className="font-semibold">
            {count} {count === 1 ? 'categoría' : 'categorías'},{' '}
            {formatEur(total)} en total.
          </span>
        </p>

        <div className="mt-3 flex gap-2">
          <button
            onClick={onCopy}
            disabled={isCopying}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#0060ad] px-4 py-2 text-xs font-bold text-white hover:opacity-90 disabled:opacity-50 transition-all"
          >
            <Copy size={12} />
            {isCopying ? 'Copiando…' : 'Copiar'}
          </button>
          <button
            onClick={onDismiss}
            className="rounded-xl bg-white px-4 py-2 text-xs font-semibold text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            Empezar desde cero
          </button>
        </div>
      </div>

      <button
        onClick={onDismiss}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[#5d605f] hover:bg-[#0060ad]/10 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
npm run lint
```
Esperado: sin errores.

---

## Task 9: Frontend — extraer `NewBudgetModal` y `EditBudgetsModal`

**Files:**
- Create: `frontend/src/components/features/budgets/NewBudgetModal.tsx`
- Create: `frontend/src/components/features/budgets/EditBudgetsModal.tsx`

Estos componentes son extracciones directas del código existente en `page.tsx`.

- [ ] **Step 1: Crear `NewBudgetModal.tsx`**

Crear `frontend/src/components/features/budgets/NewBudgetModal.tsx` con el contenido del componente `NewBudgetModal` actualmente en `page.tsx` (líneas 154-270). Añadir los imports necesarios en la cabecera:

```tsx
'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import { useBudgetCategories, useCreateBudget } from '@/hooks/useBudgets';
import type { Category } from '@/types/budget';

interface NewBudgetModalProps {
  month: number;
  year: number;
  usedCategoryIds: Set<string>;
  onClose: () => void;
}

export function NewBudgetModal({ month, year, usedCategoryIds, onClose }: NewBudgetModalProps) {
  const { data: categories = [] } = useBudgetCategories();
  const createMutation = useCreateBudget();

  const [categoryId, setCategoryId] = useState('');
  const [limit, setLimit] = useState('');
  const [error, setError] = useState('');

  const availableCategories = categories.filter(
    (c: Category) => !usedCategoryIds.has(c.id),
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const parsedLimit = parseFloat(limit.replace(',', '.'));
    if (!categoryId) { setError('Selecciona una categoría.'); return; }
    if (isNaN(parsedLimit) || parsedLimit <= 0) { setError('Introduce un límite válido mayor que 0.'); return; }

    try {
      await createMutation.mutateAsync({
        category_id: categoryId,
        amount_limit: parsedLimit,
        month,
        year,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear el presupuesto.');
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-extrabold text-[#303333]">Nuevo Presupuesto</h2>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-bold uppercase tracking-widest text-[#5d605f]">
              Categoría
            </label>
            {availableCategories.length === 0 ? (
              <p className="rounded-xl bg-[#f3f4f3] px-4 py-3 text-sm text-[#5d605f]">
                Ya tienes presupuesto en todas las categorías para este mes.
              </p>
            ) : (
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full rounded-xl border border-[#e8e9e8] bg-[#f3f4f3] px-4 py-2.5 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
              >
                <option value="">Selecciona una categoría…</option>
                {availableCategories.map((c: Category) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-bold uppercase tracking-widest text-[#5d605f]">
              Límite mensual (€)
            </label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder="0,00"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              className="w-full rounded-xl border border-[#e8e9e8] bg-[#f3f4f3] px-4 py-2.5 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
            />
          </div>

          {error && <p className="text-xs font-medium text-red-600">{error}</p>}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl bg-[#f3f4f3] py-2.5 text-sm font-semibold text-[#303333] hover:bg-[#edeeed] transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || availableCategories.length === 0}
              className="flex-1 rounded-xl bg-gradient-to-r from-[#0060ad] to-[#68abff] py-2.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50 transition-all"
            >
              {createMutation.isPending ? 'Creando…' : 'Crear Presupuesto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Crear `EditBudgetsModal.tsx`**

Crear `frontend/src/components/features/budgets/EditBudgetsModal.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { X, Trash2 } from 'lucide-react';
import {
  ShoppingCart, Utensils, Car, Home, Heart, Shirt, BookOpen, Repeat, HelpCircle,
} from 'lucide-react';
import { useUpdateBudget, useDeleteBudget } from '@/hooks/useBudgets';
import type { Budget, BudgetUpdate } from '@/types/budget';

const ICON_MAP: Record<string, React.ElementType> = {
  'shopping-cart': ShoppingCart,
  utensils: Utensils,
  car: Car,
  home: Home,
  heart: Heart,
  shirt: Shirt,
  book: BookOpen,
  repeat: Repeat,
};

const CATEGORY_COLORS: Record<string, { bg: string; icon: string }> = {
  'shopping-cart': { bg: 'bg-green-100',  icon: 'text-green-600' },
  utensils:        { bg: 'bg-amber-100',  icon: 'text-amber-600' },
  car:             { bg: 'bg-red-100',    icon: 'text-red-500' },
  home:            { bg: 'bg-blue-100',   icon: 'text-blue-600' },
  heart:           { bg: 'bg-pink-100',   icon: 'text-pink-500' },
  shirt:           { bg: 'bg-purple-100', icon: 'text-purple-600' },
  book:            { bg: 'bg-indigo-100', icon: 'text-indigo-600' },
  repeat:          { bg: 'bg-violet-100', icon: 'text-violet-600' },
};

interface EditBudgetsModalProps {
  budgets: Budget[];
  onClose: () => void;
}

export function EditBudgetsModal({ budgets, onClose }: EditBudgetsModalProps) {
  const updateMutation = useUpdateBudget();
  const deleteMutation = useDeleteBudget();

  const [limits, setLimits] = useState<Record<string, string>>(
    Object.fromEntries(budgets.map((b) => [b.id, parseFloat(b.amount_limit).toFixed(2)])),
  );
  const [error, setError] = useState('');

  async function handleSave() {
    setError('');
    const updates = budgets
      .map((b) => {
        const parsed = parseFloat((limits[b.id] ?? '').replace(',', '.'));
        return { id: b.id, value: parsed };
      })
      .filter((u) => !isNaN(u.value) && u.value > 0);

    try {
      await Promise.all(
        updates.map(({ id, value }) =>
          updateMutation.mutateAsync({ id, data: { amount_limit: value } as BudgetUpdate }),
        ),
      );
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar cambios.');
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteMutation.mutateAsync(id);
    } catch {
      // ignore individual delete errors silently
    }
  }

  const isPending = updateMutation.isPending || deleteMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-extrabold text-[#303333]">Editar Presupuestos</h2>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          {budgets.length === 0 && (
            <p className="py-4 text-center text-sm text-[#5d605f]">
              No hay presupuestos para editar.
            </p>
          )}
          {budgets.map((b) => {
            const colors = CATEGORY_COLORS[b.category_icon] ?? { bg: 'bg-gray-100', icon: 'text-gray-500' };
            const Icon = ICON_MAP[b.category_icon] ?? HelpCircle;
            return (
              <div
                key={b.id}
                className="flex items-center gap-3 rounded-xl border border-[#f3f4f3] p-3"
              >
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${colors.bg}`}>
                  <Icon size={15} className={colors.icon} />
                </div>
                <span className="min-w-0 flex-1 truncate text-sm font-semibold text-[#303333]">
                  {b.category_name}
                </span>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={limits[b.id] ?? ''}
                  onChange={(e) => setLimits((prev) => ({ ...prev, [b.id]: e.target.value }))}
                  className="w-24 rounded-lg border border-[#e8e9e8] bg-[#f3f4f3] px-3 py-1.5 text-right text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20"
                />
                <span className="text-xs text-[#5d605f]">€</span>
                <button
                  onClick={() => handleDelete(b.id)}
                  disabled={isPending}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 transition-colors"
                  title="Eliminar presupuesto"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
        </div>

        {error && <p className="mt-3 text-xs font-medium text-red-600">{error}</p>}

        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl bg-[#f3f4f3] py-2.5 text-sm font-semibold text-[#303333] hover:bg-[#edeeed] transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isPending || budgets.length === 0}
            className="flex-1 rounded-xl bg-gradient-to-r from-[#0060ad] to-[#68abff] py-2.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50 transition-all"
          >
            {updateMutation.isPending ? 'Guardando…' : 'Guardar Cambios'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verificar TypeScript**

```bash
npm run lint
```
Esperado: sin errores.

---

## Task 10: Frontend — refactorizar `budgets/page.tsx`

**Files:**
- Modify: `frontend/src/app/(dashboard)/budgets/page.tsx`

Reemplazar todo el contenido de `page.tsx` con el orquestador delgado. La lógica del banner requiere una segunda query al mes anterior, activada solo cuando el mes actual está vacío.

- [ ] **Step 1: Reemplazar el contenido de `page.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Plus, Pencil } from 'lucide-react';
import {
  useBudgetSummary,
  useCopyPreviousBudgets,
} from '@/hooks/useBudgets';
import { BudgetSummaryCard } from '@/components/features/budgets/BudgetSummaryCard';
import { BudgetCategoryCard } from '@/components/features/budgets/BudgetCategoryCard';
import { CopyBudgetBanner } from '@/components/features/budgets/CopyBudgetBanner';
import { NewBudgetModal } from '@/components/features/budgets/NewBudgetModal';
import { EditBudgetsModal } from '@/components/features/budgets/EditBudgetsModal';

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-gray-200 ${className ?? ''}`} />;
}

function BudgetSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-36 w-full" />
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
      </div>
    </div>
  );
}

export default function BudgetsPage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [dismissedCopy, setDismissedCopy] = useState(false);

  const { data, isLoading, isError, refetch } = useBudgetSummary(month, year);

  // Calcular mes anterior
  const prevMonth = month === 1 ? 12 : month - 1;
  const prevYear = month === 1 ? year - 1 : year;

  // Query al mes anterior: solo se activa cuando el mes actual está vacío y el banner no fue descartado
  const currentIsEmpty = !isLoading && !isError && (data?.budgets.length ?? 0) === 0;
  const { data: prevData } = useBudgetSummary(
    prevMonth,
    prevYear,
  );
  const showCopyBanner =
    currentIsEmpty &&
    !dismissedCopy &&
    (prevData?.budgets.length ?? 0) > 0;

  const copyMutation = useCopyPreviousBudgets();

  function prevMonthNav() {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
    setDismissedCopy(false);
  }

  function nextMonthNav() {
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
    setDismissedCopy(false);
  }

  async function handleCopy() {
    await copyMutation.mutateAsync({ month, year });
  }

  const usedCategoryIds = new Set(data?.budgets.map((b) => b.category_id) ?? []);

  return (
    <div className="relative space-y-6 pb-32">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
            Resumen Mensual
          </p>
          <h1 className="mt-0.5 text-3xl font-extrabold tracking-tight text-[#303333]">
            Presupuestos
          </h1>
        </div>

        {/* Month selector */}
        <div className="flex shrink-0 items-center gap-2 rounded-full border border-[#e8e9e8] bg-white px-3 py-2 shadow-sm">
          <button
            onClick={prevMonthNav}
            className="flex h-7 w-7 items-center justify-center rounded-full text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="min-w-[130px] text-center text-sm font-semibold text-[#303333]">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={nextMonthNav}
            className="flex h-7 w-7 items-center justify-center rounded-full text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-2xl bg-white px-6 py-8 text-center shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
          <p className="text-sm font-medium text-red-600">
            No se pudieron cargar los presupuestos.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-3 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 transition-all"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading && !isError && <BudgetSkeleton />}

      {/* Content */}
      {!isLoading && !isError && data && (
        <>
          {/* Resumen global */}
          {data.budgets.length > 0 && <BudgetSummaryCard data={data} />}

          {/* Banner copiar mes anterior */}
          {showCopyBanner && prevData && (
            <CopyBudgetBanner
              month={month}
              year={year}
              previousSummary={prevData}
              isCopying={copyMutation.isPending}
              onCopy={handleCopy}
              onDismiss={() => setDismissedCopy(true)}
            />
          )}

          {/* Lista de categorías */}
          <div>
            <h2 className="mb-3 text-base font-extrabold text-[#303333]">Categorías</h2>

            {data.budgets.length === 0 && !showCopyBanner ? (
              <div className="rounded-2xl bg-white px-6 py-14 text-center shadow-[0_2px_8px_rgba(48,51,51,0.06)]">
                <p className="text-sm text-[#5d605f]">
                  No tienes presupuestos para este mes.
                </p>
                <button
                  onClick={() => setShowNewModal(true)}
                  className="mt-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 transition-all"
                >
                  <Plus size={14} />
                  Crear tu primer presupuesto
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {data.budgets.map((b) => (
                  <BudgetCategoryCard key={b.id} budget={b} />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* FABs */}
      <div className="fixed bottom-8 right-6 flex flex-col items-end gap-3">
        <button
          onClick={() => setShowEditModal(true)}
          className="flex items-center gap-2 rounded-full border border-[#e8e9e8] bg-white px-5 py-3 text-sm font-semibold text-[#303333] shadow-lg hover:bg-[#f3f4f3] transition-colors"
        >
          <Pencil size={15} />
          Editar Presupuestos
        </button>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-3 text-sm font-bold text-white shadow-lg hover:opacity-90 transition-all"
        >
          <Plus size={15} />
          Nuevo Presupuesto
        </button>
      </div>

      {/* Modales */}
      {showNewModal && (
        <NewBudgetModal
          month={month}
          year={year}
          usedCategoryIds={usedCategoryIds}
          onClose={() => setShowNewModal(false)}
        />
      )}
      {showEditModal && data && (
        <EditBudgetsModal
          budgets={data.budgets}
          onClose={() => setShowEditModal(false)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verificar TypeScript y build**

```bash
npm run lint && npm run build
```
Esperado: sin errores de TypeScript ni de build.

---

## Verificación final

- [ ] **Arrancar el entorno completo**

```bash
# Terminal 1 — Backend
cd Backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

- [ ] **Smoke test manual**

1. Navegar a `/budgets` — verificar que carga el mes actual correctamente.
2. Navegar a un mes anterior con presupuestos existentes — verificar que se muestran las tarjetas con el layout correcto (nombre + importe a la derecha).
3. Navegar a un mes sin presupuestos donde el mes anterior sí los tiene — verificar que aparece el `CopyBudgetBanner` con el nombre del mes y el total correcto.
4. Pulsar "Copiar" — verificar que los presupuestos aparecen instantáneamente sin recargar.
5. Navegar a un mes sin presupuestos y mes anterior también vacío — verificar que aparece el empty state sin banner.
6. Con ≥ 2 categorías con gasto > 0, verificar que aparece el donut chart en la tarjeta de resumen. Con 1 o 0 categorías con gasto, verificar que no aparece.
7. Hacer clic en una tarjeta de categoría — verificar que navega a `/transactions` con el filtro de esa categoría y rango de fechas del mes aplicados.
8. Verificar que `total_available` negativo (gasto > límite) se muestra en rojo.
