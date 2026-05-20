# Objetivos de Ahorro — Documentación de Implementación

## Resumen

Pantalla completa de gestión de objetivos de ahorro (savings goals) integrada en Wallo. Permite al usuario crear metas económicas (vacaciones, fondo de emergencia, coche nuevo, etc.), registrar aportaciones o retiradas parciales, y hacer seguimiento del progreso con métricas calculadas automáticamente. El objetivo de mayor prioridad aparece también en el dashboard principal.

---

## Base de datos

### Tabla `savings_goals`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador |
| `user_id` | UUID FK → `users` | Propietario (CASCADE DELETE) |
| `name` | VARCHAR(100) | Nombre del objetivo |
| `icon` | VARCHAR(50) | Clave del icono (ej. `plane`, `piggy-bank`) |
| `color` | VARCHAR(7) | Color hex (ej. `#F59E0B`) |
| `target_amount` | NUMERIC(12,2) | Importe objetivo |
| `current_amount` | NUMERIC(12,2) | Importe acumulado |
| `monthly_contribution` | NUMERIC(12,2) NULL | Aportación mensual prevista |
| `deadline` | DATE NULL | Fecha límite |
| `priority` | INTEGER | Orden de prioridad (mayor = primero) |
| `status` | VARCHAR(20) | `active` / `completed` / `cancelled` |
| `completed_at` | TIMESTAMPTZ NULL | Fecha de compleción |
| `created_at` | TIMESTAMPTZ | Creación (server default) |
| `updated_at` | TIMESTAMPTZ | Última modificación |

Check constraints: `target_amount > 0`, `current_amount >= 0`, `status IN (...)`.

### Tabla `goal_contributions`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador |
| `goal_id` | UUID FK → `savings_goals` | Objetivo (CASCADE DELETE) |
| `user_id` | UUID FK → `users` | Usuario |
| `amount` | NUMERIC(12,2) | Importe (negativo = retirada) |
| `note` | VARCHAR(200) NULL | Nota libre |
| `created_at` | TIMESTAMPTZ | Timestamp |

Migración: `Backend/alembic/versions/7a216d32206a_add_savings_goals_and_contributions.py`

---

## Backend

### Archivos creados / modificados

| Archivo | Acción |
|---|---|
| `Backend/app/goals/__init__.py` | Creado (package) |
| `Backend/app/goals/models.py` | Creado — modelos SQLAlchemy 2.0 |
| `Backend/app/goals/schemas.py` | Creado — schemas Pydantic v2 |
| `Backend/app/goals/service.py` | Creado — lógica de negocio |
| `Backend/app/goals/router.py` | Creado — endpoints FastAPI |
| `Backend/app/main.py` | Modificado — registro del router |
| `Backend/app/dashboard/schemas.py` | Modificado — campo `active_goal` |
| `Backend/app/dashboard/service.py` | Modificado — fetching del objetivo activo |
| `Backend/alembic/env.py` | Modificado — importación de modelos |

### Endpoints REST (`/api/v1/goals`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/goals/` | Lista objetivos del usuario con resumen agregado. Query param `?status=active\|completed\|cancelled\|all` |
| `POST` | `/goals/` | Crea un objetivo nuevo |
| `GET` | `/goals/{id}` | Detalle de un objetivo con todas las contribuciones |
| `PATCH` | `/goals/{id}` | Actualiza campos parcialmente (nombre, importe, estado, etc.) |
| `DELETE` | `/goals/{id}` | Elimina objetivo y sus contribuciones (204) |
| `POST` | `/goals/{id}/contributions` | Registra una aportación o retirada |
| `GET` | `/goals/{id}/contributions` | Historial completo de contribuciones ordenado DESC |

Todos los endpoints requieren autenticación JWT. La validación de ownership (`user_id`) se realiza en cada operación — acceder a un objetivo ajeno devuelve 404.

### Schemas Pydantic

- **`GoalCreate`**: `name`, `target_amount` (> 0), `icon`, `color`, `monthly_contribution`, `deadline`, `priority`. Validadores: nombre no vacío, importe positivo.
- **`GoalUpdate`**: todos los campos opcionales; valida `status` y `target_amount`.
- **`ContributionCreate`**: `amount` (puede ser negativo para retiradas), `note` (máx 200 chars).
- **`GoalResponse`**: incluye campos calculados (ver sección de campos computados).
- **`GoalSummaryResponse`**: lista de `GoalResponse` + `total_saved`, `total_target`, `active_count`, `completed_count`.

### Campos computados (calculados en cada respuesta)

Calculados en `service.py` a partir de los datos del modelo, sin columnas extra en BD:

| Campo | Lógica |
|---|---|
| `percentage` | `(current / target) × 100`, redondeado a 2 decimales |
| `days_remaining` | Días hasta `deadline` (negativo si vencido). `null` si no hay deadline |
| `estimated_completion_date` | `today + ceil(remaining / monthly_contribution) × 30 días`. `null` si no hay aportación mensual o ya está completado |
| `pace_status` | Compara `monthly_contribution` con el ritmo necesario para llegar a tiempo: `ahead` (≥110%), `on_track` (≥90%), `at_risk` (<90%). `null` si falta deadline o aportación mensual |
| `motivational_message` | Mensaje en español según porcentaje: `≥100%` → "¡Objetivo cumplido!", `≥75%` → "¡Ya casi lo tienes!", `≥50%` → "¡Más de la mitad! Sigue así", `≥25%` → "Vas por buen camino", `>0%` → "¡Buen comienzo!", `=0%` → "¡Empieza a ahorrar hoy!" |
| `recent_contributions` | Últimas 5 contribuciones ordenadas DESC |

### Integración con Dashboard

`DashboardResponse` incluye ahora `active_goal: GoalResponse | None` — el objetivo activo de mayor prioridad del usuario. Se obtiene en paralelo con el resto de datos del dashboard mediante `asyncio.gather`.

### Tests (39 tests, todos passing)

| Archivo | Tests | Qué cubre |
|---|---|---|
| `tests/goals/test_goals_crud.py` | 8 | Crear, listar, obtener, actualizar, marcar como completado, eliminar, validación de importe |
| `tests/goals/test_contributions.py` | 5 | Depósito, retirada, retirada que deja saldo negativo (rechazada), contribución a objetivo no activo (rechazada), listado ordenado |
| `tests/goals/test_computed_fields.py` | 26 | Todas las funciones privadas del servicio con casos límite (0%, 24.9%, 25%, 75%, 100%, 120%) |

---

## Frontend

### Archivos creados / modificados

| Archivo | Acción |
|---|---|
| `frontend/src/types/goals.ts` | Creado — interfaces TypeScript |
| `frontend/src/lib/api.ts` | Modificado — `goalsApi` con 7 métodos |
| `frontend/src/hooks/useGoals.ts` | Creado — hooks React Query v5 |
| `frontend/src/components/features/goals/GoalProgressBar.tsx` | Creado |
| `frontend/src/components/features/goals/GoalEmptyState.tsx` | Creado |
| `frontend/src/components/features/goals/DeleteGoalDialog.tsx` | Creado |
| `frontend/src/components/features/goals/ContributionPanel.tsx` | Creado |
| `frontend/src/components/features/goals/GoalCard.tsx` | Creado |
| `frontend/src/components/features/goals/GoalSummaryCard.tsx` | Creado |
| `frontend/src/components/features/goals/NewGoalModal.tsx` | Creado |
| `frontend/src/components/features/goals/EditGoalModal.tsx` | Creado |
| `frontend/src/app/(dashboard)/goals/page.tsx` | Creado |
| `frontend/src/app/(dashboard)/goals/loading.tsx` | Creado |
| `frontend/src/app/(dashboard)/layout.tsx` | Modificado — enlace "Objetivos" en sidebar |
| `frontend/src/app/(dashboard)/dashboard/page.tsx` | Modificado — widget de objetivo activo |
| `frontend/src/types/index.ts` | Modificado — campo `active_goal` en `Dashboard` |

### Tipos TypeScript (`types/goals.ts`)

```typescript
export type GoalStatus = 'active' | 'completed' | 'cancelled';

export interface SavingsGoal {
  id: string;
  target_amount: string;      // Decimal serializado como string por FastAPI
  current_amount: string;
  monthly_contribution: string | null;
  status: GoalStatus;
  pace_status: 'on_track' | 'ahead' | 'at_risk' | null;
  percentage: number;
  motivational_message: string;
  recent_contributions: GoalContribution[];
  // ... resto de campos
}

export interface GoalCreate {
  name: string;
  target_amount: number;      // número en inputs del usuario
  // ...
}
```

Los campos monetarios en respuestas del backend son `string` (FastAPI serializa `Decimal` como string). Los campos de creación/actualización son `number` (input del usuario).

### API Layer (`goalsApi`)

```typescript
goalsApi.list(status?)            // GET /goals/?status=X
goalsApi.get(id)                  // GET /goals/{id}
goalsApi.create(data)             // POST /goals/
goalsApi.update(id, data)         // PATCH /goals/{id}
goalsApi.delete(id)               // DELETE /goals/{id}
goalsApi.addContribution(id, data) // POST /goals/{id}/contributions
goalsApi.getContributions(id)     // GET /goals/{id}/contributions
```

### Hooks React Query (`useGoals.ts`)

| Hook | Tipo | Query key | Descripción |
|---|---|---|---|
| `useGoals(status?)` | Query | `['goals', status]` | Lista con resumen. `staleTime: 60s` |
| `useGoal(id)` | Query | `['goals', id]` | Detalle individual |
| `useGoalContributions(id)` | Query | `['goals', id, 'contributions']` | Historial completo |
| `useCreateGoal()` | Mutation | — | Invalida `['goals']` + `['dashboard']` |
| `useUpdateGoal()` | Mutation | — | Invalida `['goals']` + `['dashboard']` |
| `useDeleteGoal()` | Mutation | — | Invalida `['goals']` + `['dashboard']` |
| `useAddContribution()` | Mutation | — | Invalida `['goals']`, `['goals', id]` y `['dashboard']` |

### Componentes

#### `GoalProgressBar`
Barra de progreso con colores adaptativos según porcentaje (gris → azul → índigo → verde), marcadores de hito en 25%/50%/75%, prop `height` configurable. Sin estado propio.

#### `GoalEmptyState`
Pantalla vacía cuando el usuario no tiene ningún objetivo. Icono Target de lucide-react, texto en español, botón "Crear mi primer objetivo".

#### `GoalSummaryCard`
Tarjeta resumen en la parte superior de la página. Muestra total ahorrado vs total objetivo, barra de progreso global, contador de objetivos activos y completados. El contador de completados actúa como botón para desplegar la sección correspondiente.

#### `GoalCard`
Tarjeta individual por objetivo. Incluye:
- Icono dinámico (20 iconos de lucide-react) con color personalizado y borde lateral izquierdo
- Badge de estado de ritmo: Adelantado / En ritmo / En riesgo
- Barra de progreso + porcentaje
- Mensaje motivacional
- Texto de días restantes (rojo si vencido, naranja si ≤7 días)
- Fecha estimada de compleción
- Botón "Añadir" que despliega `ContributionPanel` inline
- Banner "¡Objetivo cumplido!" para objetivos completados
- Botones de editar y eliminar

#### `ContributionPanel`
Panel inline dentro de `GoalCard`. Dos modos (depositar / retirar) con toggle. Botones rápidos (10€, 50€, 100€, 500€) y campo de cantidad personalizada. Campo de nota opcional. Las retiradas se envían como importe negativo.

#### `DeleteGoalDialog`
Modal de confirmación. Si el objetivo tiene saldo acumulado, muestra el importe en el mensaje de advertencia.

#### `NewGoalModal`
Modal en dos pasos:
1. **Selector de preset**: 8 categorías predefinidas (Fondo de emergencia, Vacaciones, Entrada de piso, Coche nuevo, Tecnología, Educación, Boda, Otro…) con icono y color preconfigurados.
2. **Formulario**: nombre, importe objetivo, aportación mensual (opcional), fecha límite (opcional), selector de icono (20 opciones), selector de color (12 opciones).

#### `EditGoalModal`
Igual que `NewGoalModal` pero con campos pre-rellenos. Incluye sección adicional para marcar el objetivo como completado (con confirmación de dos pasos).

### Página de Objetivos (`/goals`)

Página cliente (`'use client'`). Flujo principal:

1. Carga con skeleton animado mientras `useGoals` resuelve.
2. Si no hay objetivos → `GoalEmptyState` centrado.
3. Con objetivos → `GoalSummaryCard` + grid responsive de `GoalCard` (1 col en móvil, 2 en tablet, 3 en desktop).
4. Sección "Completados" colapsable con chevron.
5. Modales: `NewGoalModal`, `EditGoalModal`, `DeleteGoalDialog` controlados por estado local.

### Widget en Dashboard

Sección "Objetivo activo" en el dashboard principal, visible solo si el usuario tiene al menos un objetivo activo. Muestra nombre, porcentaje, barra de progreso compacta (`h-2`) e importes. Es un enlace que navega a `/goals`.

---

## Commits (24 commits)

```
c85b243 docs: update CLAUDE.md to reflect goals feature completion
81a68f4 feat(goals): add active goal widget to dashboard page
b58e0c9 feat(goals): add active_goal to DashboardResponse and service
57cb2f9 feat(goals): add Objetivos link to navigation sidebar
9d24aa1 fix(goals): fix completedGoals filter, loading skeleton, unused goalId prop, String() casts
1f721d3 feat(goals): add goals page and loading skeleton
66af8c1 feat(goals): add NewGoalModal and EditGoalModal components
cfdfc45 feat(goals): add GoalCard and GoalSummaryCard components
77a60c9 feat(goals): add DeleteGoalDialog and ContributionPanel components
273efc1 feat(goals): add GoalProgressBar and GoalEmptyState components
4532d6b fix(goals): add GoalStatus type, fix query hook, add detail hooks
ac0979e feat(goals): add useGoals hook with mutations
6fee530 feat(goals): add goalsApi to frontend API layer
1acfa73 feat(goals): add TypeScript types for goals domain
37b7395 test(goals): add computed field unit tests
abf46bb test(goals): add contribution tests
311ffe0 test(goals): add CRUD tests for savings goals
5ad05e4 feat(goals): register goals router in FastAPI app
bd28625 feat(goals): add goals FastAPI router with 7 endpoints
119fafd feat(goals): add goals service with CRUD, computed fields, and contribution logic
fa8059a feat(goals): add Pydantic v2 schemas for goals domain
a8b7224 feat(goals): add Alembic migration for savings_goals and goal_contributions tables
1a5cb10 fix(goals): use short descriptor names for CheckConstraints
3bfbc1a feat(goals): add SavingsGoal and GoalContribution SQLAlchemy models
```

---

## Decisiones técnicas relevantes

**Campos monetarios como `Decimal` (backend) y `string` (frontend).** FastAPI serializa `Decimal` de Python como string en JSON. Los tipos TypeScript de respuesta usan `string`; los de entrada (`GoalCreate`, `GoalUpdate`) usan `number`. Se parsean con `parseFloat()` antes de mostrarlos.

**Campos computados calculados en servicio, no en BD.** `percentage`, `pace_status`, `estimated_completion_date` y `motivational_message` se calculan en cada respuesta a partir de `current_amount`, `target_amount`, `monthly_contribution` y `deadline`. No requieren columnas adicionales.

**Contribuciones como registros contables.** Cada aportación o retirada genera una fila en `goal_contributions` con el importe (positivo o negativo). El servicio actualiza `current_amount` del objetivo en la misma transacción. Esto mantiene el historial completo para auditoría futura.

**Ownership en cada operación.** `_get_goal_or_404` filtra siempre por `goal_id AND user_id`. Acceder a un objetivo de otro usuario devuelve 404, no 403, para no revelar su existencia.

**CheckConstraints con nombres cortos.** La convención de Alembic en este proyecto antepone `ck_<tabla>_` automáticamente. Los nombres en el código son solo el descriptor corto (`target_positive`, `current_nonnegative`, `status`) para evitar el prefijo duplicado.

**Invalidación de caché coordinada.** Todas las mutaciones invalidan `['goals']` y `['dashboard']` para mantener sincronizado el widget del dashboard. `useAddContribution` invalida adicionalmente `['goals', id]` para refrescar el detalle del objetivo específico sin recargar la lista completa.
