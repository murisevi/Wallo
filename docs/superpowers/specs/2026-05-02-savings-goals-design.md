# Savings Goals (Objetivos de Ahorro) — Design Spec

**Date:** 2026-05-02
**Author:** murisevi
**Status:** Approved — ready for implementation

---

## 1. Overview

Feature "Savings Goals" (Objetivos de Ahorro) exists in the TFG memory as implemented but is absent from the codebase. This spec defines a full implementation from scratch, following the existing Wallo architecture patterns and incorporating UX patterns from Monarch Money, Copilot Money, YNAB, and Rocket Money.

The feature lets users create savings goals (e.g., emergency fund, vacation, new car), track progress via contributions and withdrawals, see predictive analytics (estimated completion date, pace status), and get motivational feedback.

---

## 2. Data Model

### Table: `savings_goals`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK, gen_random_uuid() |
| `user_id` | UUID | FK → users.id CASCADE DELETE, indexed, NOT NULL |
| `name` | VARCHAR(100) | NOT NULL |
| `icon` | VARCHAR(50) | NOT NULL, default `'piggy-bank'` |
| `color` | VARCHAR(7) | NOT NULL, default `'#3B82F6'` |
| `target_amount` | NUMERIC(12,2) | NOT NULL, CHECK > 0 |
| `current_amount` | NUMERIC(12,2) | NOT NULL, default 0, CHECK >= 0 |
| `monthly_contribution` | NUMERIC(12,2) | nullable |
| `deadline` | DATE | nullable |
| `priority` | INTEGER | NOT NULL, default 0 |
| `status` | VARCHAR(20) | NOT NULL, default `'active'` (`active`/`completed`/`cancelled`) |
| `completed_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | server_default now() |
| `updated_at` | TIMESTAMPTZ | server_default now(), onupdate now() |

### Table: `goal_contributions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK, gen_random_uuid() |
| `goal_id` | UUID | FK → savings_goals.id CASCADE DELETE, indexed, NOT NULL |
| `user_id` | UUID | FK → users.id CASCADE DELETE, indexed, NOT NULL |
| `amount` | NUMERIC(12,2) | NOT NULL (positive = deposit, negative = withdrawal) |
| `note` | VARCHAR(200) | nullable |
| `created_at` | TIMESTAMPTZ | server_default now() |

---

## 3. Backend — Domain Structure

```
app/goals/
├── __init__.py
├── router.py    ← HTTP only
├── service.py   ← all business logic + computed fields
├── models.py    ← SQLAlchemy 2.0 (Mapped[] + mapped_column())
└── schemas.py   ← Pydantic v2 (GoalCreate / GoalUpdate / GoalResponse / ...)
```

### 3.1 Schemas

- **`GoalCreate`**: `name`, `target_amount` (> 0), `icon` (default `piggy-bank`), `color` (default `#3B82F6`), `monthly_contribution?`, `deadline?`, `priority` (default 0)
- **`GoalUpdate`**: all fields optional; `status` restricted to `active`/`completed`/`cancelled`
- **`ContributionCreate`**: `amount` (positive or negative), `note?`
- **`ContributionResponse`**: `id`, `goal_id`, `amount`, `note`, `created_at`
- **`GoalResponse`**: all DB fields + computed: `percentage`, `days_remaining`, `estimated_completion_date`, `pace_status`, `motivational_message`, `recent_contributions` (last 5)
- **`GoalSummaryResponse`**: `goals[]`, `total_saved`, `total_target`, `active_count`, `completed_count`

### 3.2 Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/goals/` | JWT | List all goals with computed fields. `?status=active\|completed\|cancelled\|all` (default `all`). Ordered by `priority DESC, created_at DESC`. Returns `GoalSummaryResponse`. |
| `POST` | `/api/v1/goals/` | JWT | Create goal. Returns `GoalResponse` (201). |
| `GET` | `/api/v1/goals/{id}` | JWT | Detail with ALL contributions (not just 5). |
| `PATCH` | `/api/v1/goals/{id}` | JWT | Update fields. Sets `completed_at = now()` when `status → completed`. Verifies ownership. |
| `DELETE` | `/api/v1/goals/{id}` | JWT | Delete goal + cascade contributions. Returns 204. |
| `POST` | `/api/v1/goals/{id}/contributions` | JWT | Add deposit or withdrawal. Updates `current_amount`. Returns 400 if result < 0. Returns updated `GoalResponse`. |
| `GET` | `/api/v1/goals/{id}/contributions` | JWT | All contributions, ordered `created_at DESC`. |

### 3.3 Computed Fields (service logic, not stored)

```python
percentage = (current_amount / target_amount) * 100  # capped display, not stored

days_remaining = (deadline - date.today()).days if deadline else None

# estimated_completion_date: only if monthly_contribution > 0 and remaining > 0
months_needed = math.ceil((target_amount - current_amount) / monthly_contribution)
estimated_completion_date = date.today() + timedelta(days=months_needed * 30)

# pace_status: only if both monthly_contribution AND deadline are set
months_until_deadline = max((deadline - date.today()).days / 30, 0.1)
required_monthly = (target_amount - current_amount) / months_until_deadline
# ahead: monthly_contribution >= required_monthly * 1.1
# on_track: monthly_contribution >= required_monthly * 0.9
# at_risk: otherwise

# motivational_message
# >= 100% → "¡Objetivo cumplido! 🎉"
# >= 75%  → "¡Ya casi lo tienes!"
# >= 50%  → "¡Más de la mitad! Sigue así"
# >= 25%  → "Vas por buen camino"
# > 0%   → "¡Buen comienzo!"
# = 0%   → "¡Empieza a ahorrar hoy!"
```

### 3.4 Contribution Logic

1. Verify ownership
2. Verify `goal.status == 'active'` (reject 400 if not)
3. `new_amount = goal.current_amount + contribution.amount`
4. Reject 400 if `new_amount < 0` ("El importe acumulado no puede ser negativo")
5. Insert `GoalContribution`, update `goal.current_amount`
6. Do NOT auto-complete — user marks as completed manually
7. Return updated `GoalResponse`

---

## 4. Frontend

### 4.1 Types (`types/goals.ts`)

```typescript
SavingsGoal, GoalContribution, GoalSummary, GoalCreate, GoalUpdate, ContributionCreate
```

All matching the backend schemas exactly (amounts as `number`, dates as ISO strings).

### 4.2 API Layer (`lib/api.ts`)

New `goalsApi` object with: `list(status?)`, `get(id)`, `create(data)`, `update(id, data)`, `delete(id)`, `addContribution(id, data)`, `getContributions(id)`.

### 4.3 Hook (`hooks/useGoals.ts`)

Query key `['goals']`. Exposes: `summary`, `isLoading`, `error`, `createGoal`, `updateGoal`, `deleteGoal`, `addContribution`. Each mutation invalidates `['goals']` AND `['dashboard']`.

### 4.4 Components (`components/features/goals/`)

| Component | Purpose |
|---|---|
| `GoalSummaryCard` | Top summary: total saved, total target, global progress bar, active count, completed count (clickable to expand) |
| `GoalCard` | Individual goal: color accent, icon, name, pace badge, progress bar with milestone marks, amounts, motivational message, deadline info, estimated date, "+ Añadir" button |
| `GoalProgressBar` | Bar with milestone markers at 25%/50%/75%; color changes by range (gray → blue → indigo → green → bright green) |
| `ContributionPanel` | Inline panel (not modal): quick buttons +10/+50/+100/+500€, custom input, withdraw toggle, note field, cancel |
| `NewGoalModal` | Preset selector first, then form: name, target amount, monthly contribution, deadline, icon grid, color palette |
| `EditGoalModal` | Same form pre-filled + "Marcar como completado" action |
| `DeleteGoalDialog` | Confirmation with amount warning if `current_amount > 0` |
| `GoalEmptyState` | Centered icon, title, subtitle, CTA button |

### 4.5 Page (`app/(dashboard)/goals/`)

- `page.tsx`: client component with header + "Nuevo objetivo" button, `GoalSummaryCard`, active goals grid, collapsible completed section
- `loading.tsx`: skeleton replicating layout structure

Grid: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4`

Completed goals: `opacity-75`, collapsible via state toggle.

---

## 5. Integrations

### 5.1 Sidebar

Add "Objetivos" link (icon: `Target` from lucide-react) in `app/(dashboard)/layout.tsx`, between Presupuestos and Informes.

### 5.2 Dashboard Widget

- **Backend**: add `active_goal: GoalResponse | None` to `DashboardResponse`. Query: highest-priority active goal for the user (by `priority DESC, created_at DESC`).
- **Frontend**: if `active_goal` exists, show compact widget (icon + name + progress bar + "X€ / Y€") below recurring charges. Click → `/goals`. No empty state if no goals.

---

## 6. Tests

`Backend/tests/goals/`:
- `test_goals_crud.py`: create (full + minimal), list (ownership isolation), get, update, mark completed (`completed_at` set), delete cascade, reject `target_amount <= 0`
- `test_contributions.py`: deposit, withdrawal, withdrawal below zero (400), contribute to non-active goal (400), list ordered DESC
- `test_computed_fields.py`: percentage, days_remaining, estimated_completion_date, pace_status (ahead/on_track/at_risk), motivational_message for each range

---

## 7. Documentation Updates

After implementation:
- **PROJECT_STATUS.md**: add Goals to implementation status table, remove from "Not implemented", add section 4.9, update route map, components, hooks, types, routers, metrics
- **CLAUDE.md**: add `goals/` to project structure tree

---

## 8. Implementation Order

1. `app/goals/models.py` — SavingsGoal + GoalContribution
2. Alembic migration — create and run
3. `app/goals/schemas.py`
4. `app/goals/service.py`
5. `app/goals/router.py`
6. Register router in `app/main.py`
7. Backend tests — run and verify
8. `types/goals.ts`
9. `goalsApi` in `lib/api.ts`
10. `hooks/useGoals.ts`
11. Feature components (`components/features/goals/`)
12. Page (`app/(dashboard)/goals/page.tsx` + `loading.tsx`)
13. Sidebar link
14. Dashboard integration (backend + frontend)
15. Update `PROJECT_STATUS.md`
16. Update `CLAUDE.md`
