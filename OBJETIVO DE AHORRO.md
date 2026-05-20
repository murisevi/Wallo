# Prompt: Implementar pantalla de Objetivos de Ahorro — Wallo

## Contexto del proyecto

Wallo es una aplicación web de gestión de finanzas personales (TFG — Universidad de Sevilla). Es un monorepo con backend Python (FastAPI) y frontend TypeScript (Next.js). El proyecto ya tiene implementados: autenticación JWT, conexión bancaria PSD2 via Enable Banking, transacciones con categorización ML, presupuestos mensuales, gastos recurrentes, dashboard y reports.

La feature "Objetivos de ahorro" está documentada en la memoria del TFG como implementada, pero **no existe en el código**. Hay que implementarla desde cero para que coincida con lo documentado y además incorporar mejoras inspiradas en competidores (Monarch Money, Copilot Money, YNAB, Rocket Money).

Lee CLAUDE.md y PROJECT_STATUS.md antes de empezar. Contienen la arquitectura exacta, convenciones y patrones que DEBES seguir.

---

## Stack técnico exacto

- **Backend**: Python 3.12, FastAPI ≥0.115, SQLAlchemy 2.0 (async con asyncpg), Alembic, Pydantic v2
- **Frontend**: Next.js 16+ (App Router), TypeScript strict, Tailwind CSS v4, React Query (TanStack v5), Recharts, lucide-react para iconos
- **Base de datos**: PostgreSQL 16
- **Cache**: Redis 7 (opcional, degrada gracefully)

---

## Arquitectura obligatoria

### Backend — patrón por dominio

Cada dominio sigue esta estructura estricta (igual que `app/budgets/`, `app/transactions/`, etc.):

```
app/goals/
├── __init__.py
├── router.py    ← Solo HTTP: path params, query params, request/response bodies
├── service.py   ← TODA la lógica de negocio: queries, cálculos, orquestación
├── models.py    ← SQLAlchemy table definitions (Mapped[] + mapped_column())
└── schemas.py   ← Pydantic v2 models para API I/O (separar Create / Update / Response)
```

**Dirección de dependencias (obligatorio)**: Router importa Service. Service importa Models. Nunca al revés.

### Frontend — convenciones existentes

- Server Components por defecto. `"use client"` solo para interactividad/hooks.
- Estado del servidor: React Query (TanStack). No Redux ni Zustand.
- Hooks en `frontend/src/hooks/`. Cada hook wrappea `useQuery` o `useMutation`.
- Tipos en `frontend/src/types/`.
- API layer en `frontend/src/lib/api.ts` — nunca raw fetch en componentes.
- Componentes feature en `frontend/src/components/features/goals/`.
- Páginas en `frontend/src/app/(dashboard)/goals/`.

---

## 1. MODELO DE BASE DE DATOS

### Tabla `savings_goals`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | UUID | PK, default gen_random_uuid() |
| `user_id` | UUID | FK → users.id CASCADE DELETE, indexed, NOT NULL |
| `name` | VARCHAR(100) | NOT NULL |
| `icon` | VARCHAR(50) | NOT NULL, default `'piggy-bank'` (nombre de icono lucide-react) |
| `color` | VARCHAR(7) | NOT NULL, default `'#3B82F6'` (hex) |
| `target_amount` | NUMERIC(12,2) | NOT NULL, CHECK > 0 |
| `current_amount` | NUMERIC(12,2) | NOT NULL, default 0, CHECK >= 0 |
| `monthly_contribution` | NUMERIC(12,2) | nullable (campo opcional — si se define, habilita cálculos predictivos) |
| `deadline` | DATE | nullable (fecha límite opcional) |
| `priority` | INTEGER | NOT NULL, default 0 (mayor número = mayor prioridad, para ordenar) |
| `status` | VARCHAR(20) | NOT NULL, default `'active'`. Valores: `'active'`, `'completed'`, `'cancelled'` |
| `completed_at` | TIMESTAMPTZ | nullable (se rellena automáticamente al marcar como completado) |
| `created_at` | TIMESTAMPTZ | server_default now() |
| `updated_at` | TIMESTAMPTZ | server_default now(), onupdate now() |

### Tabla `goal_contributions`

Registra cada aportación o retirada individual del usuario. Sin esta tabla, el progreso sería un número opaco sin historial.

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | UUID | PK, default gen_random_uuid() |
| `goal_id` | UUID | FK → savings_goals.id CASCADE DELETE, indexed, NOT NULL |
| `user_id` | UUID | FK → users.id CASCADE DELETE, indexed, NOT NULL |
| `amount` | NUMERIC(12,2) | NOT NULL (positivo = aportación, negativo = retirada) |
| `note` | VARCHAR(200) | nullable (nota opcional, ej: "Paga extra de junio") |
| `created_at` | TIMESTAMPTZ | server_default now() |

### Convenciones DB (respetar las del proyecto)

- Todos los IDs: UUID con `func.gen_random_uuid()` (PostgreSQL native)
- Todos los timestamps: `TIMESTAMP WITH TIME ZONE` (`DateTime(timezone=True)`)
- Valores monetarios: `NUMERIC(12, 2)`, NUNCA Float
- Naming convention: `ix_`, `uq_`, `ck_`, `fk_`, `pk_` prefixes enforced en `Base.metadata`
- Session: async via asyncpg, `expire_on_commit=False`
- Usar `Mapped[]` + `mapped_column()` style (SQLAlchemy 2.0), nunca `Column()`

### Migración Alembic

Crear migración con: `alembic revision --autogenerate -m "add_savings_goals_and_contributions"`

Asegurarse de importar los nuevos modelos en `alembic/env.py`.

---

## 2. BACKEND — SCHEMAS (Pydantic v2)

```python
# Schemas a crear en app/goals/schemas.py

class GoalCreate:
    name: str                          # max 100 chars
    target_amount: Decimal             # > 0
    icon: str = "piggy-bank"           # nombre icono lucide-react
    color: str = "#3B82F6"             # hex color
    monthly_contribution: Decimal | None = None  # opcional
    deadline: date | None = None       # opcional
    priority: int = 0

class GoalUpdate:
    name: str | None = None
    target_amount: Decimal | None = None
    icon: str | None = None
    color: str | None = None
    monthly_contribution: Decimal | None = None
    deadline: date | None = None
    priority: int | None = None
    status: str | None = None          # solo permite 'active', 'completed', 'cancelled'

class ContributionCreate:
    amount: Decimal                    # positivo = aportar, negativo = retirar
    note: str | None = None            # max 200 chars

class ContributionResponse:
    id: UUID
    goal_id: UUID
    amount: Decimal
    note: str | None
    created_at: datetime

class GoalResponse:
    id: UUID
    name: str
    icon: str
    color: str
    target_amount: Decimal
    current_amount: Decimal
    monthly_contribution: Decimal | None
    deadline: date | None
    priority: int
    status: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Campos calculados dinámicamente por el service:
    percentage: float                  # (current_amount / target_amount) * 100
    days_remaining: int | None         # días hasta deadline (None si no hay deadline)
    estimated_completion_date: date | None  # basado en monthly_contribution
    pace_status: str | None            # 'on_track' | 'ahead' | 'at_risk' | None
    motivational_message: str          # frase según porcentaje
    recent_contributions: list[ContributionResponse]  # últimas 5 contribuciones

class GoalSummaryResponse:
    goals: list[GoalResponse]
    total_saved: Decimal               # suma current_amount de todos los activos
    total_target: Decimal              # suma target_amount de todos los activos
    active_count: int
    completed_count: int
```

---

## 3. BACKEND — ENDPOINTS

Registrar el router en `app/main.py` con prefijo `/api/v1/goals` y tags `["goals"]`.

| Método | Path | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/goals/` | JWT | Lista todos los objetivos del usuario con campos calculados. Query param opcional `status` para filtrar (`active`, `completed`, `cancelled`, `all`). Default: `all`. Ordenados por `priority DESC, created_at DESC`. Devuelve `GoalSummaryResponse`. |
| `POST` | `/api/v1/goals/` | JWT | Crear nuevo objetivo. Devuelve `GoalResponse` con status 201. |
| `GET` | `/api/v1/goals/{id}` | JWT | Detalle de un objetivo con todas sus contribuciones (no solo las últimas 5). |
| `PATCH` | `/api/v1/goals/{id}` | JWT | Actualizar campos del objetivo. Si `status` cambia a `'completed'`, setear `completed_at = now()`. Verificar ownership. |
| `DELETE` | `/api/v1/goals/{id}` | JWT | Eliminar objetivo. Verificar ownership. Status 204. |
| `POST` | `/api/v1/goals/{id}/contributions` | JWT | Añadir contribución (aportación o retirada). Actualiza `current_amount` del objetivo sumando el `amount`. Si `current_amount` resultante < 0, devolver 400. Devuelve `GoalResponse` actualizado. |
| `GET` | `/api/v1/goals/{id}/contributions` | JWT | Listar todas las contribuciones de un objetivo, ordenadas por `created_at DESC`. |

---

## 4. BACKEND — SERVICE LOGIC

### Campos calculados (calcular en el service, no almacenar en DB)

```python
# percentage
percentage = (current_amount / target_amount) * 100 if target_amount > 0 else 0

# days_remaining (solo si hay deadline)
days_remaining = (deadline - date.today()).days if deadline else None

# estimated_completion_date (solo si hay monthly_contribution > 0)
if monthly_contribution and monthly_contribution > 0:
    remaining = target_amount - current_amount
    if remaining <= 0:
        estimated_completion_date = None  # ya completado
    else:
        months_needed = math.ceil(remaining / monthly_contribution)
        estimated_completion_date = date.today() + timedelta(days=months_needed * 30)

# pace_status (solo si hay monthly_contribution Y deadline)
if monthly_contribution and deadline:
    months_until_deadline = max((deadline - date.today()).days / 30, 0.1)
    required_monthly = (target_amount - current_amount) / months_until_deadline
    if current_amount >= target_amount:
        pace_status = 'on_track'
    elif monthly_contribution >= required_monthly * 1.1:
        pace_status = 'ahead'
    elif monthly_contribution >= required_monthly * 0.9:
        pace_status = 'on_track'
    else:
        pace_status = 'at_risk'

# motivational_message (basado en porcentaje)
if percentage >= 100:
    message = "¡Objetivo cumplido! 🎉"
elif percentage >= 75:
    message = "¡Ya casi lo tienes!"
elif percentage >= 50:
    message = "¡Más de la mitad! Sigue así"
elif percentage >= 25:
    message = "Vas por buen camino"
elif percentage > 0:
    message = "¡Buen comienzo!"
else:
    message = "¡Empieza a ahorrar hoy!"
```

### Lógica de contribuciones

Al recibir `POST /goals/{id}/contributions`:
1. Verificar ownership del goal
2. Verificar que goal.status == 'active' (no permitir contribuciones a goals completados/cancelados)
3. Calcular nuevo `current_amount = goal.current_amount + contribution.amount`
4. Si `current_amount < 0`, devolver 400 con mensaje "El importe acumulado no puede ser negativo"
5. Insertar registro en `goal_contributions`
6. Actualizar `goal.current_amount = current_amount`
7. Si `current_amount >= target_amount` y status era 'active': NO cambiar automáticamente a completed (dejar que el usuario lo haga manualmente, porque puede querer sobrepasar la meta)
8. Devolver GoalResponse actualizado

### Lógica de eliminación

Al eliminar un goal, las contribuciones se eliminan en cascada (FK con CASCADE DELETE).

---

## 5. FRONTEND — TIPOS TypeScript

Crear `frontend/src/types/goals.ts`:

```typescript
export interface SavingsGoal {
  id: string;
  name: string;
  icon: string;
  color: string;
  target_amount: number;
  current_amount: number;
  monthly_contribution: number | null;
  deadline: string | null;       // ISO date string
  priority: number;
  status: 'active' | 'completed' | 'cancelled';
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  percentage: number;
  days_remaining: number | null;
  estimated_completion_date: string | null;
  pace_status: 'on_track' | 'ahead' | 'at_risk' | null;
  motivational_message: string;
  recent_contributions: GoalContribution[];
}

export interface GoalContribution {
  id: string;
  goal_id: string;
  amount: number;
  note: string | null;
  created_at: string;
}

export interface GoalSummary {
  goals: SavingsGoal[];
  total_saved: number;
  total_target: number;
  active_count: number;
  completed_count: number;
}

export interface GoalCreate {
  name: string;
  target_amount: number;
  icon?: string;
  color?: string;
  monthly_contribution?: number | null;
  deadline?: string | null;
  priority?: number;
}

export interface GoalUpdate {
  name?: string;
  target_amount?: number;
  icon?: string;
  color?: string;
  monthly_contribution?: number | null;
  deadline?: string | null;
  priority?: number;
  status?: 'active' | 'completed' | 'cancelled';
}

export interface ContributionCreate {
  amount: number;
  note?: string | null;
}
```

---

## 6. FRONTEND — API LAYER

Añadir a `frontend/src/lib/api.ts` un objeto `goalsApi`:

```typescript
export const goalsApi = {
  list: (status?: string) =>
    api.get<GoalSummary>(`/goals/${status ? `?status=${status}` : ''}`),
  get: (id: string) =>
    api.get<SavingsGoal>(`/goals/${id}`),
  create: (data: GoalCreate) =>
    api.post<SavingsGoal>('/goals/', data),
  update: (id: string, data: GoalUpdate) =>
    api.patch<SavingsGoal>(`/goals/${id}`, data),
  delete: (id: string) =>
    api.delete(`/goals/${id}`),
  addContribution: (id: string, data: ContributionCreate) =>
    api.post<SavingsGoal>(`/goals/${id}/contributions`, data),
  getContributions: (id: string) =>
    api.get<GoalContribution[]>(`/goals/${id}/contributions`),
};
```

---

## 7. FRONTEND — HOOK `useGoals`

Crear `frontend/src/hooks/useGoals.ts`. Seguir el mismo patrón que `useBudgets`:

```typescript
// Query key: ['goals']
// Debe exponer:
// - summary: GoalSummary (data del GET /goals/)
// - isLoading, error
// - createGoal: useMutation que invalida ['goals'] on success
// - updateGoal: useMutation que invalida ['goals'] on success
// - deleteGoal: useMutation que invalida ['goals'] on success
// - addContribution: useMutation que invalida ['goals'] on success
// Invalidar también ['dashboard'] en cada mutación para refrescar el widget del dashboard
```

---

## 8. FRONTEND — PANTALLA `/goals`

### Estructura de archivos

```
frontend/src/app/(dashboard)/goals/
├── page.tsx              ← Página principal (client component)
└── loading.tsx           ← Skeleton loading

frontend/src/components/features/goals/
├── GoalSummaryCard.tsx   ← Tarjeta resumen arriba
├── GoalCard.tsx          ← Tarjeta individual de objetivo
├── GoalProgressBar.tsx   ← Barra de progreso con milestones
├── NewGoalModal.tsx      ← Modal de creación con presets
├── EditGoalModal.tsx     ← Modal de edición
├── ContributionPanel.tsx ← Panel inline para añadir/retirar dinero
├── DeleteGoalDialog.tsx  ← Diálogo de confirmación de eliminación
└── GoalEmptyState.tsx    ← Estado vacío
```

### 8.1 Tarjeta resumen (GoalSummaryCard)

Ubicación: parte superior de la pantalla, ANTES del grid de tarjetas.

Inspirada en `BudgetSummaryCard` existente. Muestra:
- **Total ahorrado** (suma de `current_amount` de todos los objetivos activos)
- **Total objetivo** (suma de `target_amount` de todos los activos)
- **Barra de progreso global** (total_saved / total_target * 100)
- **Contador**: "X objetivos activos"
- Si hay objetivos completados, un texto clicable "Y completados" que despliega/colapsa la sección de completados

### 8.2 Tarjeta individual de objetivo (GoalCard)

Cada tarjeta representa un SavingsGoal. Diseño:

- **Acento de color**: borde izquierdo de 4px con el `color` del objetivo, o header con fondo suave del color
- **Icono**: icono de lucide-react grande (24px) con el `color` del objetivo, en la esquina superior izquierda junto al nombre
- **Nombre**: título principal del objetivo
- **Badge de pace_status** (si existe): chip coloreado al lado del nombre
  - `ahead` → chip verde "Adelantado"
  - `on_track` → chip azul "En ritmo"
  - `at_risk` → chip rojo/naranja "En riesgo"
- **Barra de progreso (GoalProgressBar)**:
  - Marcadores de milestones en 25%, 50%, 75% (líneas verticales sutiles sobre la barra)
  - Colores de la barra según porcentaje:
    - 0% → gris (barra vacía)
    - 1-49% → azul (`#3B82F6`)
    - 50-79% → indigo (`#6366F1`)
    - 80-99% → verde (`#10B981`)
    - ≥100% → verde brillante (`#059669`) con efecto sutil (shimmer o gradient)
  - Porcentaje numérico mostrado al final de la barra o encima
- **Importes**: "325,00 € de 1.000,00 €" debajo de la barra
- **Frase motivacional**: texto pequeño gris/muted debajo de los importes (`motivational_message`)
- **Deadline info** (si existe):
  - Si faltan >0 días: "Quedan X días" en texto neutro
  - Si faltan ≤7 días: "Quedan X días" en naranja/warning
  - Si la fecha ya pasó y no está completado: "Vencido hace X días" en rojo con badge "Vencido"
- **Fecha estimada** (si existe `estimated_completion_date`): "Estimado: 14 ago 2026" en texto pequeño
- **Botón "+ Añadir"**: botón en la parte inferior de la tarjeta que abre el `ContributionPanel` inline

### 8.3 Panel de contribución inline (ContributionPanel)

Se abre dentro de la tarjeta al pulsar "+ Añadir" (no un modal aparte). Inspirado en cómo el dashboard maneja acciones de recurring charges inline.

Contiene:
- **Botones rápidos**: +10€, +50€, +100€, +500€ (botones pequeños con click directo)
- **Campo personalizado**: input numérico + botón "Añadir" para cantidades custom
- **Toggle "Retirar"**: al activarlo, los botones rápidos restan en vez de sumar y el input cambia visualmente (borde rojo/naranja)
- **Campo nota**: input de texto pequeño opcional (placeholder: "Nota opcional...")
- **Botón cancelar**: cierra el panel

Al añadir, se ejecuta la mutation `addContribution`, se invalida la query y se cierra el panel con una microanimación de la barra de progreso actualizándose.

### 8.4 Modal de creación (NewGoalModal)

Al abrirse, muestra primero una selección de **presets** (objetivo sugerido) para reducir fricción:

```
Presets sugeridos (array estático en el frontend):
[
  { name: "Fondo de emergencia", icon: "shield", color: "#EF4444" },
  { name: "Vacaciones", icon: "plane", color: "#F59E0B" },
  { name: "Entrada de piso", icon: "home", color: "#8B5CF6" },
  { name: "Coche nuevo", icon: "car", color: "#3B82F6" },
  { name: "Tecnología", icon: "laptop", color: "#6366F1" },
  { name: "Educación", icon: "graduation-cap", color: "#10B981" },
  { name: "Boda", icon: "heart", color: "#EC4899" },
  { name: "Otro...", icon: "plus-circle", color: "#6B7280" }
]
```

- Si el usuario selecciona un preset: se pre-rellena nombre, icono y color, y se pasa al formulario
- Si selecciona "Otro...": formulario vacío

El formulario tiene:
- **Nombre** (text input, required, max 100 chars)
- **Importe objetivo** (number input, required, > 0, formateado como moneda)
- **Contribución mensual** (number input, opcional, placeholder: "Ej: 100 €/mes")
- **Fecha límite** (date picker, opcional)
- **Icono** (grid visual de iconos de lucide-react — al menos 20 opciones comunes, mostrar el icono renderizado, no texto)
- **Color** (paleta de 10-12 colores predefinidos como círculos clicables, similar a cómo categorías custom usan color picker)
- **Botones**: "Crear objetivo" (submit) + "Cancelar"

Iconos sugeridos para el selector (todos de lucide-react): `piggy-bank`, `wallet`, `home`, `car`, `plane`, `heart`, `star`, `shield`, `graduation-cap`, `laptop`, `gift`, `music`, `camera`, `book`, `coffee`, `sun`, `umbrella`, `anchor`, `target`, `trophy`

Colores sugeridos para la paleta: `#EF4444`, `#F59E0B`, `#F97316`, `#10B981`, `#3B82F6`, `#6366F1`, `#8B5CF6`, `#EC4899`, `#14B8A6`, `#6B7280`, `#84CC16`, `#06B6D4`

### 8.5 Modal de edición (EditGoalModal)

Mismo formulario que creación pero pre-rellenado con los datos actuales. Sin la pantalla de presets.

Además incluye un botón secundario "Marcar como completado" (si status es 'active') que pide confirmación:
- Diálogo: "¿Marcar [nombre] como completado? El objetivo quedará registrado en tu historial."
- Al confirmar: `PATCH /goals/{id}` con `{ status: 'completed' }`

### 8.6 Confirmación de eliminación (DeleteGoalDialog)

Diálogo de confirmación antes de eliminar:
- Si `current_amount > 0`: "¿Eliminar [nombre]? Tienes X € acumulados en este objetivo. Esta acción no se puede deshacer."
- Si `current_amount == 0`: "¿Eliminar [nombre]? Esta acción no se puede deshacer."
- Botones: "Eliminar" (rojo) + "Cancelar"

### 8.7 Empty state (GoalEmptyState)

Cuando no hay ningún objetivo:
- Icono grande centrado: `target` o `piggy-bank` de lucide-react, en gris suave
- Título: "Aún no tienes objetivos de ahorro"
- Subtítulo: "Crea tu primer objetivo y empieza a ahorrar para lo que más te importa"
- Botón CTA: "Crear mi primer objetivo" → abre NewGoalModal

### 8.8 Skeleton loading (loading.tsx)

Crear `frontend/src/app/(dashboard)/goals/loading.tsx` con skeletons que repliquen la estructura:
- Skeleton de summary card (rectángulo ancho con barra de progreso)
- Grid de 3-4 skeleton cards (rectángulos con líneas simulando texto y barra)

Seguir el mismo patrón de los loading.tsx existentes en `/budgets/loading.tsx`, `/transactions/loading.tsx`.

### 8.9 Layout de la página

```
┌─────────────────────────────────────────────────┐
│  Objetivos de ahorro          [+ Nuevo objetivo] │  ← Header con título y botón
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐│
│  │  GoalSummaryCard                            ││  ← Resumen global
│  │  Total ahorrado: 2.450€ de 8.500€ (28,8%)  ││
│  │  ████████░░░░░░░░░░░░░░  3 objetivos activos││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  ── Objetivos activos ──────────────────────────│
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ GoalCard │ │ GoalCard │ │ GoalCard │        │  ← Grid responsive:
│  │          │ │          │ │          │        │     3 cols desktop,
│  │          │ │          │ │          │        │     2 cols tablet,
│  └──────────┘ └──────────┘ └──────────┘        │     1 col mobile
│                                                 │
│  ── Completados (2) ───────────────── [▼ / ▲] ──│  ← Sección colapsable
│  ┌──────────┐ ┌──────────┐                      │
│  │ GoalCard │ │ GoalCard │                      │  ← Tarjetas con estilo
│  │ (muted)  │ │ (muted)  │                      │     visual atenuado
│  └──────────┘ └──────────┘                      │
└─────────────────────────────────────────────────┘
```

Grid responsive: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4`

Los objetivos completados se muestran con opacidad reducida (`opacity-75`) y la barra de progreso en verde sólido. El icono puede tener un check overlay.

---

## 9. INTEGRACIÓN CON SIDEBAR

Añadir el enlace "Objetivos" a la sidebar de navegación del dashboard layout (`frontend/src/app/(dashboard)/layout.tsx`).

Buscar dónde están definidos los enlaces de navegación actuales (Dashboard, Transacciones, Presupuestos, Informes, Configuración) y añadir "Objetivos" entre Presupuestos e Informes:

```typescript
{ name: 'Objetivos', href: '/goals', icon: Target }  // import { Target } from 'lucide-react'
```

---

## 10. INTEGRACIÓN CON DASHBOARD

El documento de diseño especifica que el dashboard debe mostrar "objetivo de ahorro activo con progreso".

Modificar el dashboard para mostrar el objetivo activo prioritario (el de mayor `priority`, o si no hay prioridades, el más cercano a su deadline, o el más reciente):

1. **Backend**: Añadir al `DashboardResponse` un campo opcional `active_goal: GoalResponse | None`. En el service del dashboard, hacer query del objetivo activo con mayor prioridad del usuario.

2. **Frontend**: En la página del dashboard, si `active_goal` existe, mostrar un widget compacto debajo de los cobros recurrentes (o donde mejor encaje en el layout existente):
   - Mini-card con: icono + nombre + barra de progreso + "325€ / 1.000€"
   - Click lleva a `/goals`

Si no hay objetivos activos, no mostrar nada (no mostrar empty state en el dashboard).

---

## 11. ACTUALIZACIÓN DE PROJECT_STATUS.md

Después de implementar, actualizar `PROJECT_STATUS.md`:

1. En la tabla "Implementation Status" de la sección 1, añadir: `| Savings goals | Complete |`
2. En la sección 8 "Not Implemented", eliminar la fila: `| Goals / savings goals | Not implemented | No model, no endpoints, no UI |`
3. Añadir nueva sección `4.X Goals` con la documentación del dominio (endpoints, schemas, service logic) siguiendo el formato exacto de las secciones existentes (4.5 Budgets es el modelo).
4. En la sección 5.1 "Route Map", añadir: `| /goals | app/(dashboard)/goals/page.tsx | Client | Savings goals grid with progress tracking |`
5. En la sección 5.2 "Feature Components", añadir los componentes de goals.
6. En la sección 5.3 "Hooks", añadir: `| useGoals | ['goals'] | GET /goals/, POST, PATCH, DELETE, POST contributions | Returns summary + mutation functions |`
7. En la sección 5.4 "Types", añadir: `| goals.ts | SavingsGoal, GoalContribution, GoalSummary, GoalCreate, GoalUpdate, ContributionCreate |`
8. En "All Registered Routers", añadir: `| goals | /goals | ["goals"] |`
9. Actualizar Codebase Metrics: incrementar Backend API endpoints, Database tables (+2), Frontend pages (+1), Frontend feature components, Frontend hooks (+1).

---

## 12. ACTUALIZACIÓN DE CLAUDE.md

Añadir el dominio `goals` a la estructura del proyecto en CLAUDE.md:

```
│   │   ├── goals/               # Savings goals domain
│   │   │   ├── router.py        # CRUD endpoints for goals + contributions
│   │   │   ├── schemas.py       # GoalCreate, GoalUpdate, GoalResponse, etc.
│   │   │   ├── models.py        # SavingsGoal, GoalContribution SQLAlchemy models
│   │   │   ├── service.py       # Goal management + computed fields
│   │   │   └── __init__.py
```

En la sección "NOT in MVP", mover goals de "not in MVP" a implementado (si aún dice eso).

Añadir la ruta de frontend:
```
│   │   │       └── goals/page.tsx
```

---

## 13. TESTS

Crear tests en `Backend/tests/goals/`:

### `test_goals_crud.py`
- Test crear objetivo con todos los campos
- Test crear objetivo con solo campos obligatorios
- Test listar objetivos del usuario (verificar que no devuelve goals de otro usuario)
- Test obtener detalle de un objetivo
- Test actualizar nombre, target_amount, status
- Test marcar como completado (verificar que completed_at se setea)
- Test eliminar objetivo (verificar cascade delete de contribuciones)
- Test que no se puede crear con target_amount <= 0

### `test_contributions.py`
- Test añadir contribución positiva (aportación)
- Test añadir contribución negativa (retirada)
- Test que la retirada no puede dejar current_amount < 0
- Test que no se puede contribuir a un goal con status != 'active'
- Test listar contribuciones ordenadas por fecha DESC

### `test_computed_fields.py`
- Test cálculo de percentage
- Test cálculo de days_remaining
- Test cálculo de estimated_completion_date
- Test pace_status: ahead, on_track, at_risk
- Test motivational_message para cada rango de porcentaje

---

## 14. ORDEN DE IMPLEMENTACIÓN

Ejecutar en este orden estricto:

1. **Modelos** (`app/goals/models.py`) — SavingsGoal + GoalContribution
2. **Migración Alembic** — crear y ejecutar migración
3. **Schemas** (`app/goals/schemas.py`)
4. **Service** (`app/goals/service.py`)
5. **Router** (`app/goals/router.py`)
6. **Registrar router** en `app/main.py`
7. **Tests backend** — ejecutar y verificar que pasan
8. **Types frontend** (`types/goals.ts`)
9. **API layer** — añadir `goalsApi` a `lib/api.ts`
10. **Hook** (`hooks/useGoals.ts`)
11. **Componentes feature** (`components/features/goals/`)
12. **Página** (`app/(dashboard)/goals/page.tsx` + `loading.tsx`)
13. **Sidebar** — añadir enlace "Objetivos"
14. **Dashboard integration** — widget de objetivo activo
15. **Actualizar PROJECT_STATUS.md**
16. **Actualizar CLAUDE.md**

---

## 15. CRITERIOS DE CALIDAD

- [ ] `ruff check app/goals/ --fix && ruff format app/goals/` sin errores
- [ ] `npm run lint` sin errores
- [ ] `npm run build` sin errores
- [ ] Todos los tests pasan
- [ ] La pantalla es responsive (mobile, tablet, desktop)
- [ ] Empty state funciona cuando no hay objetivos
- [ ] Skeleton loading aparece mientras carga
- [ ] Las barras de progreso cambian de color según porcentaje
- [ ] Los presets funcionan en el modal de creación
- [ ] Los botones rápidos de contribución funcionan
- [ ] La retirada de fondos funciona
- [ ] La confirmación de eliminación aparece
- [ ] El objetivo activo aparece en el dashboard
- [ ] El enlace "Objetivos" aparece en la sidebar
- [ ] Las frases motivacionales cambian según porcentaje
- [ ] El badge de pace_status se muestra cuando hay monthly_contribution + deadline
- [ ] Los días restantes se muestran correctamente (incluido "Vencido")
- [ ] La sección de completados es colapsable
- [ ] PROJECT_STATUS.md está actualizado
- [ ] CLAUDE.md está actualizado