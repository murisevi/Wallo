// Report types — match backend reports/schemas.py

/**
 * Full period enum — includes 'week', which is derived when the user drills
 * into a specific week within a month view. Not selectable from PeriodSelector.
 */
export type PeriodEnum = 'month' | 'quarter' | 'year' | 'week';

/**
 * The three user-selectable view periods (what PeriodSelector renders).
 * 'week' is computed internally from a month + week-filter combination.
 */
export type ViewPeriod = 'month' | 'quarter' | 'year';

export interface CategorySpending {
  name: string;
  /** Decimal serialised as string */
  amount: string;
  percentage: number;
  color: string;
}

export interface SpendingByCategoryResponse {
  /** Decimal serialised as string */
  total_spending: string;
  categories: CategorySpending[];
}

export interface TimeDataPoint {
  label: string;
  /** Decimal serialised as string */
  income: string;
  /** Decimal serialised as string */
  expenses: string;
}

export interface IncomeVsExpensesResponse {
  data_points: TimeDataPoint[];
}

export interface SankeyNode {
  id: string;
  label: string;
}

export interface SankeyLink {
  source: string;
  target: string;
  /** Decimal serialised as string */
  value: string;
}

export interface SankeyResponse {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export interface BalanceEvolutionPoint {
  date: string;
  label: string;
  /** Decimal serialised as string */
  balance: string;
  change_percent: number;
}

export interface BalanceEvolutionResponse {
  period: string;
  data_points: BalanceEvolutionPoint[];
  /** Decimal serialised as string */
  start_balance: string;
  /** Decimal serialised as string */
  end_balance: string;
  /** Decimal serialised as string */
  total_change: string;
  total_change_percent: number;
}

export interface IncomeByCategoryResponse {
  period: string;
  /** Decimal serialised as string */
  total_income: string;
  categories: CategorySpending[];
}
