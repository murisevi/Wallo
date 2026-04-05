---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---
# TypeScript/Next.js Code Style

- ESLint: next/core-web-vitals + prettier. No @typescript-eslint/no-explicit-any.
- Prettier: single quotes, trailing commas, 100 char width, 2-space indent.
- TypeScript strict mode. Never use `as any` or `@ts-ignore`.
- Server Components by default. Only add "use client" for interactivity/hooks/browser APIs.
- Route groups with parentheses: (auth), (dashboard) for layout sharing without URL impact.
- loading.tsx and error.tsx per route segment for streaming/error boundaries.
- All API calls via lib/api.ts typed wrapper. Never raw fetch in components.
- State: React Query for server state. No Redux/Zustand needed for MVP.
- Component naming: PascalCase files (Button.tsx). Hook files: camelCase (useAccounts.ts).
- Currency formatting: Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).
