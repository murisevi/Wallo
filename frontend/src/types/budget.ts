// Budget domain TypeScript interfaces — mirrors backend Pydantic schemas.

// Category is defined in categories.ts (canonical) — re-exported here for
// backward compatibility with existing budget-related imports.
export type { Category } from '@/types/categories';

export interface Budget {
  id: string;
  category_id: string;
  category_name: string;
  category_icon: string;
  /** Decimal serialised as string by FastAPI */
  amount_limit: string;
  /** Decimal serialised as string by FastAPI */
  amount_spent: string;
  percentage: number;
  month: number;
  year: number;
}

export interface BudgetSummary {
  month: number;
  year: number;
  /** Decimal serialised as string */
  total_limit: string;
  /** Decimal serialised as string */
  total_spent: string;
  /** Decimal serialised as string */
  total_available: string;
  percentage: number;
  status: 'DENTRO DEL LÍMITE' | 'CERCA DEL LÍMITE' | 'SUPERADO';
  budgets: Budget[];
  comparison_message: string;
}

export interface BudgetCreate {
  category_id: string;
  amount_limit: number;
  month: number;
  year: number;
}

export interface BudgetUpdate {
  amount_limit: number;
}

export interface CopySource {
  month: number;
  year: number;
  budget_count: number;
  /** Decimal serialised as string */
  total_limit: string;
}
