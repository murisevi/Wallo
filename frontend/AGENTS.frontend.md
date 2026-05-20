# frontend/AGENTS.md — Wallo Frontend Instructions

## Scope

These instructions apply to the Wallo Next.js frontend.

The frontend uses Next.js App Router, React, TypeScript strict mode, Tailwind CSS, TanStack React Query, Recharts, D3/d3-sankey, lucide-react icons and a typed API layer.

## Core commands

Run from this frontend directory:

```bash
npm run dev
npm run lint
npm run build
```

Use `npm run lint` for most frontend changes and `npm run build` when changing routing, data loading, types or shared components.

## Architecture

Expected source layout:

```text
src/
├── app/           # App Router pages and layouts
├── components/    # ui primitives and feature components
├── hooks/         # React Query hooks
├── lib/           # api.ts and auth.ts
├── providers/     # AuthProvider and QueryProvider
└── types/         # shared TypeScript interfaces
```

## Rendering rules

- Use Server Components by default.
- Add `"use client"` only when a file needs hooks, browser APIs, local state, React Query or event handlers.
- Do not convert large route trees to client components unnecessarily.
- Keep client components focused and composable.

## Data fetching and API rules

All backend calls must go through `src/lib/api.ts` or typed API helpers exported from it.

Do not use raw `fetch` inside components unless there is already a clear project pattern for that exact case.

Rules:

- Keep `NEXT_PUBLIC_API_URL` as the source of the backend base URL.
- Ensure auth headers are injected through the existing API wrapper.
- Preserve 401 handling: API layer dispatches the `401` event and `AuthProvider` logs the user out.
- If a backend response schema changes, update `src/types/` and all affected hooks/components.
- Prefer typed API helper functions over ad-hoc request construction.

## React Query rules

- Use TanStack React Query for server state.
- Do not introduce Redux, Zustand or another global server-state layer.
- Keep query keys stable and explicit.
- Invalidate affected queries after mutations.
- Respect existing query keys such as:
  - `['accounts']`
  - `['connections']`
  - `['dashboard']`
  - `['transactions', filters]`
  - `['categories']`
  - `['budgets', month, year]`
  - `['recurring-charges']`
  - `['reports', type, period, date]`
  - `['profile']`

## Auth rules

- JWT is stored using the existing auth helpers in `src/lib/auth.ts`.
- `AuthProvider` owns login/logout/auth state.
- Protected dashboard pages should rely on the existing provider behavior.
- On 401, preserve automatic logout and redirect to `/login`.
- Do not duplicate token parsing/storage logic in components.

## TypeScript rules

- Keep TypeScript strict.
- Do not use `any` unless there is a strong reason and it is explained.
- Prefer explicit backend-facing types under `src/types/`.
- Keep names aligned with backend Pydantic schemas when practical.
- Use narrow types for enums such as report periods, transaction methods and recurring charge statuses.

## Styling and UI rules

- Use Tailwind CSS and existing UI primitives.
- Prefer existing components under `src/components/ui/` and `src/components/features/` before creating new primitives.
- Use lucide-react icons already present in the project style.
- Keep visual language consistent with the current dashboard.
- Avoid large UI rewrites unless explicitly requested.
- For charts, follow existing Recharts/D3 patterns in feature chart components.

## Pages and routing

Current route groups:

- `(auth)` for login/register.
- `(dashboard)` for the protected application.

Dashboard features include:

- dashboard overview;
- transactions with pagination/search/category/date filters;
- budgets;
- reports and analytics charts;
- bank connection/callback flow;
- settings/profile;
- recurring charge actions.

When adding a new page:

1. Use the existing route group conventions.
2. Add loading/error states if comparable pages have them.
3. Reuse layout/sidebar/navigation patterns.
4. Update navigation only if the product flow requires it.

## Forms and mutations

- Validate inputs client-side where existing patterns do.
- Keep server validation as the source of truth.
- Show loading and error states for mutations.
- After successful mutations, invalidate the relevant React Query keys.
- Avoid optimistic updates unless the current hook already supports them or the task requires them.

## Backend contract synchronization

When backend API changes affect frontend:

1. Update `src/types/`.
2. Update `src/lib/api.ts` typed helper if needed.
3. Update hooks in `src/hooks/`.
4. Update affected components/pages.
5. Run `npm run lint` and preferably `npm run build`.

## Code style

- Prettier conventions: 2-space indentation, single quotes and approximately 100-character width.
- Keep components small enough to read.
- Extract feature components only when reuse or readability improves.
- Do not create generic abstractions prematurely.

## Do not do

- Do not use raw `fetch` in components.
- Do not duplicate auth/token logic.
- Do not introduce new global state libraries.
- Do not use `any` as an easy escape hatch.
- Do not change backend route paths locally in the frontend without coordinating backend changes.
- Do not rewrite large pages only for style cleanup during unrelated tasks.
