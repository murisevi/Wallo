# Budgets Screen Redesign — Design Spec
**Date:** 2026-04-27
**Status:** Approved

## Overview

Rediseño de la pantalla `/budgets` para mejorar la UX, añadir nuevas funcionalidades y refactorizar el código actual en componentes mantenibles. El backend ya tiene el dominio de presupuestos completo (CRUD + resumen mensual). Esta spec cubre los cambios de frontend y el único endpoint nuevo de backend necesario.

---

## Features a implementar

### 1. Copiar presupuesto del mes anterior (con banner de confirmación)

Cuando el usuario navega a un mes sin presupuestos, el sistema detecta si el mes anterior tiene presupuestos configurados. Si es así, muestra un banner de confirmación en lugar del empty state vacío:

> *"No tienes presupuestos para noviembre. ¿Copiar los de octubre (4 categorías, 2.200 € en total)?"*
> **[Copiar]** · **[Empezar desde cero]**

- Al pulsar **Copiar**: llama a `POST /api/v1/budgets/copy-previous?month=M&year=Y`, invalida la cache React Query y los presupuestos aparecen al instante.
- Al pulsar **Empezar desde cero**: descarta el banner y muestra el empty state normal con botón "Crear primer presupuesto".
- Si el mes anterior también está vacío: no se muestra el banner, directamente empty state normal.

### 2. Gráfico de donut por categorías

En la sección de resumen global, junto a la barra de progreso lineal, se añade un donut chart (Recharts `PieChart` con `innerRadius`) que muestra el peso de cada categoría sobre el total gastado.

- Cada sector = `amount_spent` de una categoría, coloreado con la paleta `CATEGORY_COLORS` existente.
- Centro del donut: total gastado en grande.
- Tooltip al hover: nombre de categoría + importe + porcentaje.
- Se renderiza solo cuando hay ≥ 2 categorías con `amount_spent > 0`. Si no, solo se muestra la barra lineal.

### 3. Tarjetas de categoría clickables → filtro en transacciones

Al hacer clic en una `BudgetCategoryCard`, se navega a:
```
/transactions?category=<category_name>&month=<M>&year=<Y>
```
La página de transacciones inicializa sus filtros desde `useSearchParams()` en lugar de siempre vacíos, y sincroniza la URL cuando el usuario cambia filtros manualmente.

### 4. Corrección del layout de tarjetas (alineado al mockup)

Cambio en `BudgetCategoryCard`:
- Icono + nombre a la izquierda
- `Gastado X € / Y €` alineado a la derecha en la misma línea que el nombre
- Barra de progreso a ancho completo debajo
- Toda la tarjeta es clickable (`cursor-pointer`, hover sutil)

### 5. Fix: `total_available` negativo

Cuando el gasto supera el límite total, `total_available` es negativo. Actualmente se muestra siempre en verde con prefijo `+`. Se corrige para mostrar en rojo cuando es negativo.

---

## Arquitectura

### Backend — 1 endpoint nuevo

**`POST /api/v1/budgets/copy-previous`**
- Query params: `month: int`, `year: int`
- Auth: JWT Bearer (igual que el resto del dominio)
- Lógica en `service.py`:
  1. Calcula el mes anterior (M-1, Y) o (12, Y-1) si M=1.
  2. Busca todos los `Budget` del usuario para ese mes anterior.
  3. Para cada budget, intenta crear uno nuevo para (M, Y) con el mismo `category_id` y `amount_limit`. Ignora duplicados (si ya existe, lo salta silenciosamente).
  4. Devuelve `BudgetSummaryResponse` del mes nuevo.
- No requiere cambios en el modelo ni en la DB schema.

### Frontend — estructura de archivos

```
frontend/src/
├── components/features/budgets/
│   ├── BudgetSummaryCard.tsx      # Resumen global (totales + barra lineal + disponible)
│   ├── BudgetDonutChart.tsx       # Gráfico donut con Recharts
│   ├── BudgetCategoryCard.tsx     # Tarjeta individual (clickable → /transactions)
│   ├── CopyBudgetBanner.tsx       # Banner "Copiar del mes anterior"
│   ├── NewBudgetModal.tsx         # Modal crear presupuesto
│   └── EditBudgetsModal.tsx       # Modal editar/eliminar presupuestos
├── hooks/
│   └── useBudgets.ts              # +useCopyPreviousBudgets() mutation
├── lib/
│   └── api.ts                     # +budgetApi.copyPrevious(month, year)
└── app/(dashboard)/budgets/
    └── page.tsx                   # Orquestador delgado: estado month/year + modales
```

El `page.tsx` queda sin lógica de negocio inline: solo gestiona `month/year`, los booleanos de modales, y compone los subcomponentes.

---

## Detalles técnicos

### Recharts (nueva dependencia)

```bash
npm install recharts
```

`BudgetDonutChart` usa `PieChart > Pie` con `innerRadius={60} outerRadius={90}`. El total en el centro se renderiza con posicionamiento CSS absoluto sobre el SVG. Los colores se mapean desde `CATEGORY_COLORS` (paleta ya existente en el código).

### useCopyPreviousBudgets

```ts
useMutation({
  mutationFn: ({ month, year }: { month: number; year: number }) =>
    budgetApi.copyPrevious(month, year),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['budgets'] });
  },
})
```

### CopyBudgetBanner — detección del mes anterior

El `page.tsx` ejecuta una segunda query `useBudgetSummary(prevMonth, prevYear)` que se activa únicamente cuando el mes actual está vacío (`enabled: data?.budgets.length === 0`). El resultado se pasa al banner como `previousMonthBudgets` para mostrar el conteo y el total en el texto.

### Transacciones — inicialización desde query params

En la página `/transactions`, `useSearchParams()` lee `category`, `month` y `year` al montar. Se inicializan los filtros con estos valores. Cuando el usuario cambia filtros manualmente, se actualiza la URL con `router.replace()` para mantener la sincronización.

---

## Casos edge

| Caso | Comportamiento |
|------|---------------|
| Mes anterior también vacío | No muestra banner, empty state directo |
| `total_available` negativo | Muestra en rojo en lugar de verde |
| Solo 1 categoría con gasto | No se renderiza el donut, solo barra lineal |
| Copia parcial (algunos budgets ya existen) | Backend ignora duplicados, crea solo los nuevos |
| Mes futuro sin datos | No muestra banner (no hay mes anterior con datos relevantes) |
| Usuario pulsa "Empezar desde cero" | Se descarta el banner permanentemente hasta cambiar de mes |

---

## Lo que NO cambia

- Modelo `Budget` en base de datos — sin migraciones.
- Endpoints existentes (GET summary, POST, PUT, DELETE).
- Hook `useBudgets.ts` existente — solo se añade `useCopyPreviousBudgets`.
- Tipos en `types/budget.ts` — solo se añade `BudgetCopyResponse` si es necesario.
- Lógica de cálculo de gasto por categoría en el backend.

---

## Dependencias externas

- `recharts` — nueva dependencia npm para el donut chart.
