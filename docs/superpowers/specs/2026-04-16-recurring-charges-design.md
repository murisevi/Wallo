# Recurring Charges Detection — Design Spec

**Date:** 2026-04-16  
**Status:** Approved  
**Scope:** Backend domain + Dashboard integration + Frontend widget

---

## Overview

Detect recurring charges (subscriptions, installments, etc.) from the user's transaction history and display them in the "Próximos cobros" widget on the dashboard. Users can confirm, dismiss, or manage installment progress for each detected charge.

---

## Data Model

New table: `recurring_charges`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | — |
| `user_id` | UUID FK → users | — |
| `merchant_key` | String(100) | Normalized merchant key (from text_cleaner.py) |
| `display_name` | String(200) | Human-readable name (e.g. "Netflix") |
| `amount` | Numeric(12,2) | Typical detected amount |
| `currency` | String(3) | — |
| `periodicity` | String(10) | `WEEKLY`, `MONTHLY`, `ANNUAL` |
| `status` | String(20) | `possible`, `confirmed`, `dismissed` |
| `user_confirmed` | Boolean | True if user manually confirmed |
| `occurrence_count` | Integer | Times detected in transaction history |
| `next_predicted_date` | Date | Estimated next charge date |
| `last_seen_date` | Date | Date of last matching transaction |
| `is_installment` | Boolean | Whether this is a fixed-term payment |
| `installment_total` | Integer? | Total number of installments |
| `installment_paid` | Integer? | Installments paid so far |
| `created_at` | DateTime | server_default=func.now() |
| `updated_at` | DateTime | server_default=func.now(), onupdate=func.now() |

**Unique constraint:** `(user_id, merchant_key)`

### Status Rules

| Condition | Status |
|---|---|
| `occurrence_count` 2–3, no subscription category | `possible` |
| `occurrence_count` 2+ AND category = "Suscripciones" | `confirmed` |
| `occurrence_count` ≥ 3 + category = "Suscripciones" | `confirmed` (high confidence) |
| `occurrence_count` ≥ 4 | `confirmed` (automatic) |
| User confirms manually | `user_confirmed = True`, `status = confirmed` |
| User denies | Row deleted |
| User dismisses (unsubscribed) | `status = dismissed` |
| `installment_paid >= installment_total` | Row deleted |

---

## Detection Algorithm

Runs at the end of every sync, after categorization, inside `transactions/service.py`.

### Steps

1. **Group** the user's debit transactions (`DBIT`) that have a non-null `creditor_name` or `description`, grouped by `merchant_key` using the existing `text_cleaner.py` extractor.

2. **Filter** groups with ≥ 2 transactions, sorted by date ascending.

3. **Detect periodicity** by computing intervals between consecutive dates:
   - ~7 days (±2) → `WEEKLY`
   - ~28–31 days → `MONTHLY`
   - ~365 days (±15) → `ANNUAL`
   - Irregular intervals → skip group (not recurring)

4. **Classify confidence:**
   - 2–3 occurrences → `possible`
   - ≥ 4 occurrences → `confirmed`
   - Subscription category boost: 2+ occurrences + `category = "Suscripciones"` → `confirmed`

5. **Predict next date:** `last_seen_date + periodicity_in_days` (7, 30, or 365)

6. **Upsert in DB:**
   - Existing row with `status != dismissed` → update `occurrence_count`, `next_predicted_date`, `last_seen_date`, re-evaluate status
   - No existing row → create new
   - Existing row with `status = dismissed` → leave untouched

7. **Update installment progress:** If `is_installment = True`, compare `last_seen_date` with previous sync to detect new payment and increment `installment_paid`. If `installment_paid >= installment_total` → delete the row.

---

## API

New domain: `Backend/app/recurring_charges/`  
All routes under `/api/v1/recurring-charges/`

| Method | Route | Description |
|---|---|---|
| `GET` | `/recurring-charges/` | List active charges (`possible` + `confirmed`), ordered by `next_predicted_date` |
| `PATCH` | `/recurring-charges/{id}/confirm` | User confirms a `possible` charge |
| `PATCH` | `/recurring-charges/{id}/dismiss` | User dismisses (unsubscribed) → `status = dismissed` |
| `PATCH` | `/recurring-charges/{id}/installment` | Mark as installment: body `{installment_total: int}` |
| `DELETE` | `/recurring-charges/{id}` | Fully delete (deny) |

### Dashboard Integration

`GET /dashboard` response extended with:
```json
"upcoming_charges": [RecurringChargeResponse]
```
Same data as `GET /recurring-charges/` but embedded to avoid a second request from the frontend.

### RecurringChargeResponse Schema

```python
id: UUID
display_name: str
amount: Decimal
currency: str
periodicity: str          # WEEKLY | MONTHLY | ANNUAL
status: str               # possible | confirmed | dismissed
user_confirmed: bool
occurrence_count: int
next_predicted_date: date
is_installment: bool
installment_total: int | None
installment_paid: int | None
```

---

## Frontend

### Widget: "Próximos cobros" (dashboard/page.tsx)

Filled from `upcoming_charges` in the existing `useDashboard` hook. No new hook needed for the dashboard widget.

**Each row displays:**
- `display_name` (merchant name)
- `next_predicted_date` (chronological order)
- `amount` + `currency`
- Status badge: `Posible` (yellow) or `Confirmado` (green)
- If installment: progress indicator `3 / 12 pagos`

**Actions by status:**

| Status | Available actions |
|---|---|
| `possible` | "Confirmar" (PATCH confirm) + "No es recurrente" (DELETE) |
| `confirmed` | "Descartar" (PATCH dismiss) + "Marcar como plazos" (PATCH installment) |
| `is_installment = true` | Shows progress only, no action buttons |

### New Types (`types/index.ts` or `types/recurring.ts`)

```ts
interface RecurringCharge {
  id: string;
  display_name: string;
  amount: string;
  currency: string;
  periodicity: 'WEEKLY' | 'MONTHLY' | 'ANNUAL';
  status: 'possible' | 'confirmed' | 'dismissed';
  user_confirmed: boolean;
  occurrence_count: number;
  next_predicted_date: string;   // ISO date
  is_installment: boolean;
  installment_total: number | null;
  installment_paid: number | null;
}
```

### DashboardResponse extension (`types/index.ts`)

```ts
upcoming_charges: RecurringCharge[];
```

---

## Out of Scope (Future)

- Email reminders before a predicted charge date
- Push notifications
- Manual creation of recurring charges by the user
